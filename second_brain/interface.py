"""Small rich replies shared by Telegram and the local dashboard."""
MENU = {'keyboard': [[{'text': '🏠 Beranda'}, {'text': '✍️ Catat'}], [{'text': '🔎 Cari'}, {'text': '📋 Tugas'}], [{'text': '💡 Rencanakan'}, {'text': '📥 Inbox'}], [{'text': '📚 Pengetahuan'}, {'text': '⚙️ Sistem'}]], 'resize_keyboard': True, 'is_persistent': True, 'input_field_placeholder': 'Pilih menu atau tulis catatan…'}


class Reply(str):
    def __new__(cls, text, buttons=None, menu=False):
        obj = super().__new__(cls, text)
        obj.markup = {'inline_keyboard': [[{'text': label, 'callback_data': action} for label, action in row] for row in buttons]} if buttons else MENU if menu else None
        return obj
