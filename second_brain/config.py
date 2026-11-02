"""Explicit configuration. Importing modules never loads credentials or connects."""
from dataclasses import dataclass, field
import os
from pathlib import Path
import re


def read_env(path):
    values = {}
    if path.is_file():
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            key, sep, value = line.removeprefix('export ').partition('=')
            if sep and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', key.strip()):
                value = value.strip()
                if value[:1] in ('"', "'") and value[-1:] == value[:1]:
                    value = value[1:-1]
                values[key.strip()] = value
    return values


@dataclass(frozen=True)
class Settings:
    root: Path
    token: str = field(default='', repr=False)
    allowed_user: int = 0
    include_private: bool = False
    max_download: int = 20 * 1024 * 1024
    env: dict = field(default_factory=dict, repr=False)
    project_root: Path | None = None

    @property
    def project(self):
        return self.project_root or self.root

    @classmethod
    def load(cls, root, environ=None):
        root = Path(root).resolve()
        values = read_env(root / '.env')
        values.update(os.environ if environ is None else environ)
        try:
            user = int(values.get('TELEGRAM_ALLOWED_USER_ID', '0') or '0')
            limit = int(values.get('SECOND_BRAIN_MAX_DOWNLOAD_MB', '20'))
        except ValueError:
            raise ValueError('User ID dan batas download harus berupa angka.') from None
        if not 1 <= limit <= 20:
            raise ValueError('SECOND_BRAIN_MAX_DOWNLOAD_MB harus 1–20.')
        from .workspace import active_root
        return cls(active_root(root), values.get('TELEGRAM_BOT_TOKEN', '').strip(), user,
                   values.get('SECOND_BRAIN_INCLUDE_PRIVATE', '0') == '1', limit * 1024 * 1024, values, root)

    def validate_bot(self):
        if not re.fullmatch(r'\d+:[A-Za-z0-9_-]+', self.token) or self.allowed_user <= 0:
            raise ValueError('Isi TELEGRAM_BOT_TOKEN dan TELEGRAM_ALLOWED_USER_ID pada .env VPS.')

    def redact(self, text):
        text = str(text)
        if self.token:
            text = text.replace(self.token, '[REDACTED]')
        for key, value in self.env.items():
            if any(word in key for word in ('KEY', 'TOKEN', 'SECRET', 'PASSWORD')) and value:
                text = text.replace(str(value), '[REDACTED]')
        text = re.sub(r'bot\d+:[A-Za-z0-9_-]+', 'bot[REDACTED]', text)
        return re.sub(r'([?&]key=)[^&\s]+', r'\1[REDACTED]', text)
