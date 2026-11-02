"""Synchronous Telegram Bot API transport with bounded I/O and plain text."""
import json
import re
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


class TelegramError(RuntimeError):
    pass


def chunks(text, limit=3800):
    # Telegram counts UTF-16 units; astral emoji consume two units.
    chunk, length = [], 0
    for character in str(text):
        size = 2 if ord(character) > 0xffff else 1
        if length + size > limit:
            yield ''.join(chunk)
            chunk, length = [], 0
        chunk.append(character)
        length += size
    if chunk:
        yield ''.join(chunk)


class Telegram:
    def __init__(self, settings, opener=urlopen):
        self.settings, self.opener = settings, opener

    def call(self, method, payload=None):
        if not re.fullmatch(r'[A-Za-z]+', method):
            raise ValueError('Invalid Telegram method')
        request = Request(f'https://api.telegram.org/bot{self.settings.token}/{method}',
                          data=json.dumps(payload or {}).encode('utf-8'),
                          headers={'Content-Type': 'application/json'}, method='POST')
        try:
            with self.opener(request, timeout=45) as response:
                data = json.loads(response.read(4 * 1024 * 1024).decode('utf-8'))
        except HTTPError as error:
            # Do not include raw provider responses/URLs containing credentials.
            raise TelegramError(f'Telegram HTTP {error.code}; delivery may be uncertain.') from None
        except (URLError, TimeoutError, OSError, ValueError):
            raise TelegramError('Telegram connection/response failed; delivery may be uncertain.') from None
        if not data.get('ok'):
            raise TelegramError(f'Telegram rejected request (code {data.get("error_code", "unknown")}).')
        return data['result']

    def send(self, chat_id, text):
        pieces = list(chunks(text or '(kosong)'))
        for index, chunk in enumerate(pieces):
            payload = {'chat_id': chat_id, 'text': chunk}
            markup = getattr(text, 'markup', None)
            if markup and index == len(pieces) - 1:
                payload['reply_markup'] = markup
            self.call('sendMessage', payload)

    def download(self, file_id):
        item = self.call('getFile', {'file_id': file_id})
        if item.get('file_size', 0) > self.settings.max_download:
            raise ValueError('File terlalu besar untuk batas download bot.')
        path = item.get('file_path', '')
        if not path or path.startswith('/') or '..' in path.split('/'):
            raise ValueError('Invalid Telegram file path')
        request = Request(f'https://api.telegram.org/file/bot{self.settings.token}/{quote(path, safe="/")}')
        try:
            with self.opener(request, timeout=45) as response:
                content = response.read(self.settings.max_download + 1)
        except (URLError, TimeoutError, OSError):
            raise TelegramError('Download Telegram gagal.') from None
        if len(content) > self.settings.max_download:
            raise ValueError('File melebihi batas download.')
        return content
