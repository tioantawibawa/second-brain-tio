from dataclasses import replace
from io import BytesIO
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import Mock, patch

from second_brain.analysis import Analysis
from second_brain.bot import process_update
from second_brain.commands import Commands
from second_brain.config import Settings, read_env
from second_brain.providers import AI, ProviderError
from second_brain.state import State
from second_brain.storage import read_note, safe_path
from second_brain.sync import sync
from second_brain.transport import Telegram, TelegramError, chunks


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.settings = Settings(self.root, '123:testtoken', 42, env={})

    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
        return path

    def state(self):
        state = State(self.root / 'state.sqlite')
        self.addCleanup(state.close)
        return state

    def update(self, identifier=1, user=42, chat_type='private', chat=42, text='Hi'):
        return {'update_id': identifier, 'message': {'from': {'id': user}, 'chat': {'type': chat_type, 'id': chat}, 'text': text}}

    def test_config_preserves_equals_and_environment_precedence(self):
        self.write('.env', 'A="one=two"\nTELEGRAM_ALLOWED_USER_ID=12\n# test\n')
        settings = Settings.load(self.root, {'TELEGRAM_ALLOWED_USER_ID': '42'})
        self.assertEqual(settings.allowed_user, 42)
        self.assertEqual(settings.env['A'], 'one=two')

    def test_config_invalid_id_and_download_limit(self):
        for values in ({'TELEGRAM_ALLOWED_USER_ID': 'abc'}, {'SECOND_BRAIN_MAX_DOWNLOAD_MB': '500'}):
            with self.assertRaises(ValueError):
                Settings.load(self.root, values)

    def test_config_repr_and_redaction_never_reveal_keys(self):
        settings = replace(self.settings, env={'GEMINI_API_KEY': 'SUPERSECRET'})
        self.assertNotIn('testtoken', repr(settings))
        self.assertNotIn('SUPERSECRET', settings.redact('URL ?key=SUPERSECRET&x=1'))
        self.assertNotIn('testtoken', settings.redact('https://api.telegram.org/bot123:testtoken/getMe'))

    def test_unauthorized_and_group_messages_have_no_side_effects(self):
        state, transport, commands = self.state(), Mock(), Mock()
        for i, update in enumerate((self.update(user=99), self.update(chat_type='group'), self.update(chat=900)), 1):
            update['update_id'] = i
            process_update(update, self.settings, transport, commands, state)
        commands.dispatch.assert_not_called()
        transport.send.assert_not_called()
        self.assertEqual(state.counts(), {'ignored': 3})

    def test_update_duplicate_is_not_replayed(self):
        state, transport, commands = self.state(), Mock(), Mock()
        commands.dispatch.return_value = 'Saved'
        for _ in range(2):
            process_update(self.update(), self.settings, transport, commands, state)
        self.assertEqual(commands.dispatch.call_count, 1)
        self.assertEqual(state.counts(), {'done': 1})

    def test_uncertain_delivery_not_replayed(self):
        state, transport, commands = self.state(), Mock(), Mock()
        transport.send.side_effect = TelegramError('timeout')
        process_update(self.update(), self.settings, transport, commands, state)
        process_update(self.update(), self.settings, transport, commands, state)
        self.assertEqual(commands.dispatch.call_count, 1)
        self.assertEqual(state.counts(), {'uncertain': 1})

    def test_ledger_survives_restart_and_tracks_processing(self):
        path = self.root / 'ledger.sqlite'
        state = State(path)
        self.assertTrue(state.reserve(31))
        state.close()
        reopened = State(path)
        self.addCleanup(reopened.close)
        self.assertEqual(reopened.offset, 32)
        self.assertFalse(reopened.reserve(31))
        self.assertEqual(reopened.counts(), {'processing': 1})

    def test_chunks_preserve_emoji_and_respect_utf16_limit(self):
        text = 'a😀' * 5000
        parts = list(chunks(text))
        self.assertEqual(''.join(parts), text)
        self.assertTrue(all(len(p.encode('utf-16-le')) // 2 <= 3800 for p in parts))

    def test_telegram_sends_plain_text_not_markdown(self):
        body = BytesIO(json.dumps({'ok': True, 'result': {'message_id': 1}}).encode())
        opener = Mock(return_value=body)
        Telegram(self.settings, opener).send(42, '_[]* special')
        payload = json.loads(opener.call_args.args[0].data)
        self.assertNotIn('parse_mode', payload)
        self.assertEqual(payload['text'], '_[]* special')

    def test_download_stops_oversized_file_before_network_read(self):
        transport = Telegram(self.settings, Mock())
        transport.call = Mock(return_value={'file_size': self.settings.max_download + 1})
        with self.assertRaises(ValueError):
            transport.download('id')
        transport.opener.assert_not_called()

    def test_read_ambiguous_names_and_private_filter(self):
        self.write('wiki/a/n.md', '# A')
        self.write('wiki/b/n.md', '# B')
        self.write('wiki/private/secret.md', '# Secret')
        self.assertIn('beberapa catatan', read_note(self.root, 'n'))
        self.assertIn('# A', read_note(self.root, 'wiki/a/n.md'))
        self.assertNotIn('# Secret', read_note(self.root, 'secret'))

    def test_read_cannot_escape_vault_or_read_env(self):
        self.write('.env', 'VERY_SECRET_VALUE')
        self.assertNotIn('VERY_SECRET_VALUE', read_note(self.root, '../.env'))
        with self.assertRaises(ValueError):
            safe_path(self.root, '../outside.md')

    def test_commands_capture_and_unknown_command(self):
        commands = Commands(self.settings)
        self.assertIn('Tersimpan', commands.dispatch('Original thought'))
        self.assertEqual(len(list((self.root / 'inbox_raw').glob('*.md'))), 1)
        self.assertIn('tidak dikenal', commands.dispatch('/unknown'))

    def test_attachment_filename_traversal_and_duplicate_names(self):
        commands = Commands(self.settings)
        for _ in range(2):
            commands.attachment(b'Original', {'file_name': '../../escape.txt'}, 'document')
        self.assertFalse((self.root / 'escape.txt').exists())
        self.assertEqual(len(list((self.root / 'raw').glob('*.txt'))), 2)

    def test_audio_failure_retains_audio_without_fake_transcript(self):
        analysis = Mock()
        analysis.ai.transcribe.side_effect = ProviderError('no provider')
        reply = Commands(self.settings, analysis).attachment(b'bytes', {}, 'voice')
        self.assertIn('Audio asli tersimpan', reply)
        self.assertEqual(len(list((self.root / 'raw/audio_dumps').glob('*'))), 1)
        self.assertEqual(len(list((self.root / 'raw').glob('*.md'))), 0)

    def test_journal_private_not_exposed_in_shared_log(self):
        Commands(self.settings).dispatch('/journal Sensitive reflection')
        self.assertEqual(len(list((self.root / 'wiki/private/projects').glob('*.md'))), 1)
        self.assertNotIn('Sensitive', (self.root / 'log.md').read_text(encoding='utf-8'))

    def test_analysis_no_provider_no_fabricated_success(self):
        self.write('wiki/topic.md', '# topic\nscoring')
        analysis = Analysis(self.settings)
        with self.assertRaises(ProviderError):
            analysis.run('ask', 'scoring')
        self.assertEqual(list((self.root / 'wiki').rglob('*.md')), [self.root / 'wiki/topic.md'])

    def test_analysis_never_sends_private_context_to_provider(self):
        self.write('wiki/private/secret.md', '# scoring secret')
        self.write('wiki/a.md', '# scoring public')
        ai = Mock()
        ai.text.return_value = ('Grounded answer', 'test')
        Analysis(self.settings, ai).run('ask', 'scoring')
        self.assertNotIn('scoring secret', ai.text.call_args.args[0])

    def test_ingest_failure_preserves_raw_source(self):
        source = self.write('raw/idea.md', '# Original')
        ai = Mock()
        ai.text.side_effect = ProviderError('fail')
        result = Analysis(self.settings, ai).ingest()
        self.assertIn('Gagal', result)
        self.assertTrue(source.exists())

    def test_ingest_preserves_original_in_archive_and_provenance(self):
        source = self.write('raw/idea.md', '# Original')
        ai = Mock()
        ai.text.return_value = ('Summary', 'test')
        result = Analysis(self.settings, ai).ingest()
        self.assertIn('OK', result)
        archived = list((self.root / 'raw/processed').glob('*.md'))
        self.assertEqual(archived[0].read_text(), '# Original')
        output = next((self.root / 'wiki/engineering/sources').glob('*.md')).read_text(encoding='utf-8')
        self.assertIn(archived[0].name, output)
        self.assertFalse(source.exists())

    def test_ingest_resumes_after_archive_move_failure_without_second_ai_call(self):
        self.write('raw/idea.md', '# Original')
        ai = Mock()
        ai.text.return_value = ('Summary', 'test')
        analysis = Analysis(self.settings, ai)
        with patch.object(Path, 'rename', side_effect=OSError('simulated move failure')):
            analysis.ingest()
        analysis.ingest()
        self.assertEqual(ai.text.call_count, 1)
        self.assertEqual(len(list((self.root / 'wiki/engineering/sources').glob('*.md'))), 1)

    def test_provider_uses_explicit_model_and_header_not_key_in_url(self):
        response = BytesIO(json.dumps({'candidates': [{'content': {'parts': [{'text': 'Answer'}]}}]}).encode())
        opener = Mock(return_value=response)
        settings = replace(self.settings, env={'GEMINI_API_KEY': 'secret', 'GEMINI_MODEL': 'custom-model'})
        answer, engine = AI(settings, opener).text('Prompt')
        request = opener.call_args.args[0]
        self.assertNotIn('secret', request.full_url)
        self.assertIn('custom-model', request.full_url)
        self.assertEqual(answer, 'Answer')

    def test_ingest_creates_only_people_with_source_evidence(self):
        self.write('raw/meeting.md', 'Budi adalah analis di Tim Data.')
        ai = Mock()
        ai.text.return_value = (json.dumps({'summary': 'Meeting summary', 'people': [
            {'name': 'Budi', 'role': 'analis', 'organization': 'Bank yang tidak disebut', 'evidence_quote': 'Budi adalah analis di Tim Data.'},
            {'name': 'Tokoh Fiktif', 'role': 'CEO', 'evidence_quote': 'Tokoh Fiktif CEO'},
        ]}), 'test')
        Analysis(self.settings, ai).ingest()
        people = list((self.root / 'crm').glob('person-*.md'))
        self.assertEqual(len(people), 1)
        content = people[0].read_text(encoding='utf-8')
        self.assertIn('Budi', content)
        self.assertNotIn('Bank yang tidak disebut', content)

    def test_multiline_command_capture(self):
        reply = Commands(self.settings).dispatch('/capture\nFirst line\nSecond line')
        self.assertIn('Tersimpan', reply)
        stored = next((self.root / 'inbox_raw').glob('*.md')).read_text(encoding='utf-8')
        self.assertIn('First line\nSecond line', stored)

    def test_plan_prompt_supports_vps_to_local_checkout(self):
        reply = Commands(self.settings).dispatch('/plan Test idea')
        self.assertIn('checkout lokal', reply)
        self.assertIn('path relatif wiki/work/projects/', reply)

    def test_sync_default_only_status_and_disabled_push_never_stages(self):
        with patch('second_brain.sync.git', return_value=' M file') as git:
            sync(self.settings)
            self.assertEqual(git.call_args.args[1:], ('status', '--short'))
            result = sync(self.settings, True)
            self.assertIn('belum diaktifkan', result)
            self.assertTrue(all(c.args[1] == 'status' for c in git.call_args_list))


if __name__ == '__main__':
    unittest.main()
