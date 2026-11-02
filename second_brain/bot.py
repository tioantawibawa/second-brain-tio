"""One long-polling runner shared by all historical entry points."""
import logging
import signal
import time
from .controller import Commands
from .providers import ProviderError
from .state import State
from .storage import safe_path
from .transport import Telegram, TelegramError

LOG = logging.getLogger('second_brain')


def process_update(update, settings, transport, commands, state):
    identifier = update.get('update_id')
    if not isinstance(identifier, int):
        return
    if not state.reserve(identifier):
        return
    callback = update.get('callback_query')
    message = callback.get('message', {}) if callback else update.get('message') or {}
    user = callback.get('from', {}) if callback else message.get('from', {})
    chat = message.get('chat', {})
    if user.get('id') != settings.allowed_user or chat.get('type') != 'private' or chat.get('id') != settings.allowed_user:
        state.finish(identifier, 'ignored')
        return
    try:
        # A failure after a write or send is uncertain; the ID is not replayed.
        if callback:
            transport.call('answerCallbackQuery', {'callback_query_id': callback['id']})
            result = commands.callback(callback.get('data', ''))
        elif message.get('text'):
            result = commands.dispatch(message['text'])
        else:
            kind = next((k for k in ('voice', 'audio', 'document') if k in message), None)
            if not kind:
                result = 'Jenis pesan belum didukung. Kirim teks, voice, audio, atau dokumen.'
            else:
                info = message[kind]
                if info.get('file_size', 0) > settings.max_download:
                    raise ValueError('File melebihi batas download yang dikonfigurasi.')
                result = commands.attachment(transport.download(info['file_id']), info, kind)
        transport.send(chat['id'], result)
        state.finish(identifier)
    except (ValueError, ProviderError) as error:
        try:
            transport.send(chat['id'], settings.redact(f'Perintah belum selesai: {error}'))
        finally:
            state.finish(identifier, 'uncertain')
    except Exception as error:
        state.finish(identifier, 'uncertain')
        LOG.error('Update %s uncertain: %s', identifier, settings.redact(type(error).__name__))


def run(settings):
    settings.validate_bot()
    directory = safe_path(settings.project, 'data')
    directory.mkdir(parents=True, exist_ok=True)
    lock = safe_path(settings.project, 'data/telegram.lock').open('a+b')
    try:
        if __import__('os').name == 'nt':
            import msvcrt
            lock.seek(0)
            lock.write(b'0')
            lock.flush()
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        lock.close()
        raise RuntimeError('Runner Telegram lain masih aktif pada vault ini.') from None
    state = State(safe_path(settings.project, 'data/telegram-state.sqlite'))
    transport, commands = Telegram(settings), Commands(settings)
    running = True

    def stop(signum, frame):
        nonlocal running
        running = False

    old = {}
    for signum in (signal.SIGINT, signal.SIGTERM):
        old[signum] = signal.signal(signum, stop)
    try:
        webhook = transport.call('getWebhookInfo')
        if webhook.get('url'):
            raise RuntimeError('Webhook masih aktif. Hapus webhook secara eksplisit sebelum memakai polling.')
        LOG.info('Second Brain v3 runner started; outstanding states: %s', state.counts())
        delay = 1
        while running:
            try:
                updates = transport.call('getUpdates', {'offset': state.offset, 'timeout': 25, 'allowed_updates': ['message', 'callback_query']})
                for update in sorted(updates, key=lambda u: u['update_id']):
                    if not running:
                        break
                    process_update(update, settings, transport, commands, state)
                delay = 1
            except TelegramError as error:
                LOG.warning('%s; retrying poll in %ss', settings.redact(error), delay)
                # Wait in small increments so SIGTERM does not wait a full backoff.
                for _ in range(delay):
                    if not running:
                        break
                    time.sleep(1)
                delay = min(delay * 2, 30)
    finally:
        for signum, handler in old.items():
            signal.signal(signum, handler)
        state.close()
        lock.close()
