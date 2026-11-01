"""Transport-independent command routing, callable from tests and Telegram."""
from datetime import datetime
from pathlib import Path
import re
from uuid import uuid4
from . import vault
from .analysis import Analysis
from .execution import prepare
from .providers import AI, ProviderError
from .storage import append_index, audit, read_note, safe_path, save_note, slug

HELP = '''🧠 SECOND BRAIN — PANDUAN TIO
Simpan ide, temukan kembali pengetahuan, lalu ubah ide menjadi rencana kerja.

🚀 MULAI DARI SINI
1. Simpan ide:
/capture Ide membuat monitoring drift bulanan
2. Cari kembali:
/search drift
3. Siapkan rencana dua agen:
/plan Buat monitoring drift scoring bulanan

📥 SIMPAN CATATAN
• Teks biasa → catatan baru di inbox.
• URL + catatan tambahan → sumber mentah untuk diproses.
• Voice/audio → audio asli disimpan, lalu dicoba transkripsi.
• Dokumen → file asli disimpan; Markdown dapat diproses lewat /ingest.

/capture Catatan meeting hari ini
Menyimpan teks tanpa analisis AI.

/journal Refleksi pekerjaan minggu ini
Menyimpan jurnal pribadi; dikecualikan dari pencarian default.

/crm Budi - Rekan diskusi data engineering
Menyimpan profil kontak dan konteks relasi.

🔎 CARI & BACA
/list
Lihat 10 catatan terbaru beserta perintah untuk membacanya.

/search scoring drift
Cari kata pada isi catatan terbaru. Semua kata harus ditemukan dalam catatan yang sama; coba satu kata jika hasil kosong.

/read nama-catatan
Baca isi catatan. Gunakan path dari /list atau /search jika namanya mirip.

/ask Apa strategi mitigasi drift yang ada di catatan saya?
Jawaban AI berdasarkan sumber vault yang relevan.

✅ DARI IDE MENJADI TASK
/plan Buat dashboard monitoring portofolio
Menyiapkan paket berisi brief, format tugas, proposal, dan prompt untuk disalin ke Codex.
• Agen 1: pecah ide menjadi tugas, dependensi, dan kriteria selesai.
• Agen 2: susun framework proposal, skill, serta prompt eksekusi.
• Tio: review proposal sebelum implementasi.
Agen mulai bekerja saat prompt dijalankan di Codex. Simpan/sinkronkan paket ke checkout Codex bila berasal dari VPS.

📊 FOKUS & OLAH PENGETAHUAN
/brief
Ringkasan proyek aktif, tugas terbuka, dan jumlah inbox; tanpa AI. Urutan tampilan bukan peringkat prioritas.

/ingest
AI mengolah maksimal 10 sumber Markdown dari raw/inbox menjadi catatan terstruktur. Sumber asli diarsipkan.

/weekly
AI mereview catatan yang diperbarui dalam 7 hari terakhir: progres, hambatan, dan rekomendasi.

🧩 UJI & HUBUNGKAN IDE
/warroom Migrasi pipeline data ke platform baru
Pre-mortem: skenario kegagalan, asumsi, dan mitigasi.

/weave Credit risk x Behavioral economics
Hubungkan dua domain dan cari transfer ilmu yang dapat dicoba.

/sparring Streamlit vs React
Bandingkan opsi, trade-off, dan kondisi pemilihan.

⚙️ STATUS & SINKRONISASI
/status
Jumlah catatan, proyek aktif, tugas, dan inbox. Status ini tidak menguji koneksi AI atau GitHub.

/sync
Lihat status perubahan Git di VPS.

/sync push
Push commit yang sudah direview; perlu diaktifkan pada VPS dan working tree bersih. Bot tidak membuat commit otomatis.

ℹ️ YANG PERLU DIKETAHUI
Capture, cari, baca, brief, dan persiapan /plan dapat dipakai tanpa AI. Analisis AI dan transkripsi cloud memerlukan provider/model yang valid. URL disimpan sebagai sumber; isi halaman tidak dirangkum otomatis. Domain private dikecualikan dari konteks analisis AI.

Ketik /help untuk membuka panduan ini kembali.'''


class Commands:
    def __init__(self, settings, analysis=None):
        self.settings, self.root = settings, settings.root
        self.analysis = analysis or Analysis(settings)

    def dispatch(self, text):
        text = text.strip()
        if not text:
            return 'Kirim teks atau /help.'
        if not text.startswith('/'):
            for prefix, command in [('tanya:', 'ask'), ('ask:', 'ask'), ('war room:', 'warroom'), ('warroom:', 'warroom'), ('pre-mortem:', 'warroom'), ('premortem:', 'warroom'), ('uji keputusan:', 'warroom')]:
                if text.casefold().startswith(prefix):
                    return self.dispatch('/' + command + ' ' + text[len(prefix):].strip())
            if re.search(r'https?://\S+', text):
                path = save_note(self.root, text, 'Web link capture', 'raw')
            else:
                path = vault.capture(self.root, text)
            return f'Tersimpan: {path.relative_to(self.root)}'
        parts = text.split(maxsplit=1)
        head, argument = parts[0], parts[1] if len(parts) > 1 else ''
        command = head[1:].split('@', 1)[0].lower()
        argument = argument.strip()
        if command.startswith('read_'):
            argument, command = command[5:], 'read'
        aliases = {'start': 'help', 'recent': 'list', 'baca': 'read', 'query': 'ask', 'premortem': 'warroom', 'audit': 'weekly', 'morning': 'brief', 'pulse': 'brief'}
        command = aliases.get(command, command)
        if command == 'help':
            return HELP
        if command == 'status':
            notes, active, tasks, inbox = vault.snapshot(self.root, self.settings.include_private)
            return f'{len(notes)} catatan · {len(active)} proyek aktif · {len(tasks)} tugas terbuka · {len(inbox)} inbox\nVersi 2.0.0. Status ini bukan bukti provider AI atau GitHub terhubung.'
        if command == 'list':
            notes = sorted(vault.notes(self.root, self.settings.include_private), key=lambda n: n['mtime'], reverse=True)[:10]
            return '\n\n'.join(f'{n["title"]}\n/read {n["path"]}' for n in notes) or 'Vault kosong.'
        if command == 'search':
            if not argument:
                return 'Format: /search <kata kunci>'
            hits = vault.search(self.root, argument, self.settings.include_private)
            return '\n\n'.join(f'{h["title"]}\n{h["path"]}:{h["line"]}\n{h["excerpt"]}' for h in hits) or 'Tidak ditemukan. Gunakan kata yang lebih singkat; semua kata harus ditemukan.'
        if command == 'read':
            return read_note(self.root, argument, self.settings.include_private) if argument else 'Format: /read <path atau nama>'
        if command == 'capture':
            path = vault.capture(self.root, argument)
            return f'Tersimpan: {path.relative_to(self.root)}'
        if command in ('journal', 'crm'):
            if not argument or (command == 'crm' and ' - ' not in argument):
                return 'Format: /journal <refleksi> atau /crm <nama> - <konteks>'
            name, _, bio = argument.partition(' - ')
            private = command == 'journal'
            title = f'Jurnal {datetime.now():%Y-%m-%d}' if private else name
            folder = 'wiki/private/projects' if private else 'crm'
            path = save_note(self.root, argument if private else bio, title, folder, 'journal' if private else 'person', 'private' if private else 'work')
            append_index(self.root, 'journal' if private else 'crm', path, title, private)
            return f'Tersimpan: {path.relative_to(self.root)}\n' + ('Jurnal private; /read memerlukan SECOND_BRAIN_INCLUDE_PRIVATE=1.' if private else 'Profil baru tersimpan; profil lama tidak ditimpa.')
        if command == 'brief':
            _, streams, tasks, inbox = vault.snapshot(self.root, self.settings.include_private)
            return 'Fokus (status active):\n' + ('\n'.join(n['title'] for n in streams[:5]) or 'Belum ada.') + '\n\nTugas sumber:\n' + ('\n'.join(f'{task} — {n["path"]}:{line}' for n, line, task in tasks[:8]) or 'Belum ada.') + f'\n\nInbox: {len(inbox)}. Urutan bukan penilaian prioritas.'
        if command == 'plan':
            paths, prompt = prepare(self.root, argument)
            try:
                vault.home(self.root)
            except (ValueError, OSError):
                pass
            return f'Paket disiapkan: {paths["brief"].relative_to(self.root)}\nAgen belum dijalankan. Salin prompt berikut ke Codex:\n\n{prompt}'
        if command in ('ask', 'warroom', 'weave', 'sparring', 'weekly'):
            if command in ('weave', 'sparring'):
                delimiter = r'\s+(?:x|dan|&)\s+' if command == 'weave' else r'\s+(?:vs|versus)\s+'
                if len(re.split(delimiter, argument, maxsplit=1, flags=re.I)) != 2:
                    return f'Format: /{command} <A> {"x" if command == "weave" else "vs"} <B>'
            return self.analysis.run(command, argument)
        if command == 'ingest':
            return self.analysis.ingest()
        if command == 'sync':
            from .sync import sync
            return sync(self.settings, push=argument == 'push')
        return 'Perintah tidak dikenal. Gunakan /help.'

    def attachment(self, data, info, kind):
        name = info.get('file_name', 'voice.ogg' if kind == 'voice' else 'attachment.bin')
        # Remote filenames are data, never filesystem paths or shell arguments.
        name = re.split(r'[/\\]', name)[-1]
        extension = Path(name).suffix.lower()
        if not re.fullmatch(r'\.[a-z0-9]{1,8}', extension):
            extension = '.bin'
        path = safe_path(self.root, f'raw/audio_dumps/{datetime.now():%Y%m%d-%H%M%S}-{uuid4().hex}{extension}' if kind in ('voice', 'audio') else f'raw/{datetime.now():%Y%m%d-%H%M%S}-{slug(Path(name).stem)}-{uuid4().hex[:8]}{extension}')
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as handle:
            handle.write(data)
        audit(self.root, 'ATTACHMENT', path.relative_to(self.root))
        if kind not in ('voice', 'audio'):
            return f'Dokumen asli tersimpan: {path.relative_to(self.root)}. Markdown bisa diproses lewat /ingest; format biner disimpan tanpa ekstraksi.'
        mime = info.get('mime_type', 'audio/ogg')
        if not re.fullmatch(r'audio/[a-zA-Z0-9.+-]+', mime):
            mime = 'audio/ogg'
        try:
            text, engine = self.analysis.ai.transcribe(data, mime, path.name, source_path=path)
            note = save_note(self.root, f'{text}\n\nAudio asli: {path.relative_to(self.root)}\nEngine: {engine}', 'Voice transcript', 'raw', sources=[path.relative_to(self.root).as_posix()])
            return f'Transkripsi tersimpan: {note.relative_to(self.root)}\n\n{text}'
        except ProviderError:
            return f'Audio asli tersimpan: {path.relative_to(self.root)}. Transkripsi gagal/belum dikonfigurasi; tidak ada teks transkripsi yang dibuat.'
