from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from second_brain.config import Settings
from second_brain.controller import Commands
from second_brain.dashboard import snapshot
from second_brain.hub import Hub
from second_brain.planner import Planner, validate_tasks
from second_brain.providers import ProviderError
from second_brain.search_index import search
from second_brain.workspace import active_root, archives, process_lock, reset, restore

TASKS = [{'id': 'T01', 'title': 'Audit inputs', 'done_when': 'Input list recorded', 'depends_on': []}, {'id': 'T02', 'title': 'Build report', 'done_when': 'Report checked against source', 'depends_on': ['T01']}]
PROPOSAL = {'recommendation': 'Start with one local report', 'framework': 'Audit, draft, verify', 'scope': 'Local Markdown only', 'risks': 'Input access is unconfirmed', 'review_questions': 'Approve T01 and T02?'}


class V3Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.settings = Settings(self.root, allowed_user=42)

    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
        return path

    def ai(self):
        ai = Mock()
        ai.text.side_effect = [(json.dumps(TASKS), 'fake/agent1'), (json.dumps(PROPOSAL), 'fake/agent2')]
        return ai

    def test_reset_archives_bytes_and_selects_empty_workspace_without_deleting_legacy(self):
        note = self.write('wiki/work/topics/original.md', '# Original user note')
        env = self.write('.env', 'SECRET=untouched')
        ledger = self.write('data/telegram-state.sqlite', 'fixture ledger bytes')
        result = reset(self.root)
        self.assertEqual(note.read_text(), '# Original user note')
        self.assertEqual(env.read_text(), 'SECRET=untouched')
        self.assertEqual(ledger.read_text(), 'fixture ledger bytes')
        self.assertEqual((Path(result['archive']) / 'vault/wiki/work/topics/original.md').read_text(), '# Original user note')
        self.assertNotEqual(active_root(self.root), self.root)
        self.assertEqual(snapshot(Settings.load(self.root, {}))['notes'], [])

    def test_reset_blocked_while_runner_lock_held(self):
        self.write('wiki/old.md', '# Original')
        with process_lock(self.root):
            with self.assertRaises(RuntimeError):
                reset(self.root)
        self.assertFalse((self.root / '.brain/active.json').exists())

    def test_restore_keeps_current_workspace_and_verifies_archive(self):
        self.write('wiki/original.md', '# Original')
        item = reset(self.root)
        current = active_root(self.root)
        (current / 'inbox_raw/new.md').write_text('# New', encoding='utf-8')
        restored = restore(self.root, item['id'])
        self.assertEqual((restored / 'wiki/original.md').read_text(), '# Original')
        self.assertTrue((current / 'inbox_raw/new.md').exists())
        archive_file = Path(item['archive']) / 'vault/wiki/original.md'
        archive_file.write_text('tampered', encoding='utf-8')
        with self.assertRaises(ValueError):
            restore(self.root, item['id'])

    def test_workspace_manifest_rejects_traversal(self):
        self.write('.brain/active.json', json.dumps({'workspace': '../escape'}))
        with self.assertRaises(ValueError):
            active_root(self.root)

    def test_import_archive_from_old_checkout_preserves_delivery_ledger(self):
        import sqlite3
        old = self.root / 'old'
        new = self.root / 'new'
        self.write('old/wiki/note.md', '# VPS-only note')
        new.mkdir()
        (old / 'data').mkdir()
        db = sqlite3.connect(old / 'data/telegram-state.sqlite')
        db.execute('CREATE TABLE marker(value TEXT)')
        db.execute("INSERT INTO marker VALUES ('keep-offset')")
        db.commit()
        db.close()
        result = reset(new, old)
        self.assertTrue((Path(result['archive']) / 'vault/wiki/note.md').exists())
        copied = sqlite3.connect(new / 'data/telegram-state.sqlite')
        try:
            self.assertEqual(copied.execute('SELECT value FROM marker').fetchone()[0], 'keep-offset')
        finally:
            copied.close()

    def test_stale_approval_button_cannot_approve_revised_proposal(self):
        commands = Commands(self.settings)
        identifier = commands.hub.new_plan('Idea')
        planner = Planner(self.settings, self.ai())
        planner.generate(identifier)
        commands.dispatch('/revise ' + identifier + ' Limit to local files')
        Planner(self.settings, self.ai()).generate(identifier)
        self.assertEqual(commands.hub.plan(identifier)['version'], 2)
        with self.assertRaises(ValueError):
            commands.callback('plan:approve:' + identifier + ':1')
        self.assertEqual(commands.hub.tasks(), [])

    def test_two_roles_handoff_review_and_idempotent_approval(self):
        hub, ai = Hub(self.root), self.ai()
        identifier = hub.new_plan('Local report idea')
        planner = Planner(self.settings, ai)
        plan = planner.generate(identifier)
        self.assertEqual(plan['state'], 'ready_for_review')
        self.assertEqual(hub.tasks(), [])
        self.assertIn('Audit inputs', ai.text.call_args_list[1].args[0])
        hub.approve(identifier)
        hub.approve(identifier)
        self.assertEqual(len(hub.tasks()), 2)
        planner.generate(identifier)
        self.assertEqual(ai.text.call_count, 2)

    def test_agent2_failure_resumes_without_rerunning_agent1(self):
        hub, ai = Hub(self.root), self.ai()
        identifier = hub.new_plan('Idea')
        ai.text.side_effect = [(json.dumps(TASKS), 'first'), ProviderError('offline')]
        planner = Planner(self.settings, ai)
        with self.assertRaises(ProviderError):
            planner.generate(identifier)
        self.assertEqual(hub.plan(identifier)['state'], 'agent1_done')
        self.assertEqual(hub.tasks(), [])
        ai.text.side_effect = [(json.dumps(PROPOSAL), 'second')]
        planner.generate(identifier)
        self.assertEqual(ai.text.call_count, 3)

    def test_unreviewed_and_malformed_plans_cannot_activate_tasks(self):
        hub = Hub(self.root)
        identifier = hub.new_plan('Idea')
        with self.assertRaises(ValueError):
            hub.approve(identifier)
        for value in ([{'id': 'T01', 'title': 'A', 'done_when': 'B', 'depends_on': ['T01']}], [{'id': 'T01', 'title': 'A', 'done_when': '', 'depends_on': []}]):
            with self.assertRaises(ValueError):
                validate_tasks(value)
        self.assertEqual(hub.tasks(), [])

    def test_task_done_persists_between_instances(self):
        hub = Hub(self.root)
        identifier = hub.add_task('Finish audit')
        Hub(self.root).set_task(identifier, 'done')
        self.assertEqual(Hub(self.root).tasks()[0]['state'], 'done')

    def test_navigation_buttons_and_conversation_survive_restart(self):
        first = Commands(self.settings)
        welcome = first.dispatch('/start')
        self.assertIn('keyboard', welcome.markup)
        first.dispatch('✍️ Catat')
        result = Commands(self.settings).dispatch('Original idea')
        self.assertIn('Tersimpan', result)
        saved = next((self.root / 'inbox_raw').glob('*.md')).read_text(encoding='utf-8')
        self.assertIn('Original idea', saved)

    def test_menu_switch_cancels_pending_input(self):
        commands = Commands(self.settings)
        commands.dispatch('✍️ Catat')
        commands.dispatch('📋 Tugas')
        self.assertIsNone(commands.hub.session(42))
        self.assertFalse((self.root / 'inbox_raw').exists())

    def test_plan_is_draft_until_ai_called_and_review_approved(self):
        commands = Commands(self.settings)
        commands.dispatch('/plan A small dashboard')
        plan = commands.hub.plans()[0]
        self.assertEqual(plan['state'], 'draft')
        self.assertEqual(commands.hub.tasks(), [])
        self.assertIn('Analisis dua agen', str(commands.plan_reply(plan['id']).markup))

    def test_search_supports_partial_terms_and_refreshes_deleted_documents(self):
        a = self.write('wiki/scoring.md', '# Scoring model\nSeasonal drift and calibration')
        self.write('wiki/private/hidden.md', '# Scoring secret')
        hits = search(self.root, 'bagaimana scoring baru')
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]['path'], 'wiki/scoring.md')
        a.unlink()
        self.assertEqual(search(self.root, 'scoring'), [])

    def test_dashboard_snapshot_omits_keys_and_private_notes(self):
        self.write('wiki/private/private.md', '# Never expose')
        self.write('wiki/public.md', '# Public')
        settings = replace(self.settings, env={'GEMINI_API_KEY': 'SUPERSECRET', 'GEMINI_MODEL': 'configured'})
        data = json.dumps(snapshot(settings))
        self.assertNotIn('SUPERSECRET', data)
        self.assertNotIn('Never expose', data)
        self.assertIn('Public', data)


if __name__ == '__main__':
    unittest.main()
