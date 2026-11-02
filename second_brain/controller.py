"""Task-first navigation, persistent conversations, and reviewed planning."""
import json
from pathlib import Path
from . import __version__, vault
from .hub import Hub
from .interface import Reply
from .legacy_commands import Commands as LegacyCommands
from .planner import Planner
from .search_index import search
from .storage import read_note, audit
from .workspace import archives, process_lock

LABELS = {'🏠 Beranda': '/home', '✍️ Catat': '/capture', '🔎 Cari': '/search', '📋 Tugas': '/tasks', '💡 Rencanakan': '/plan', '📥 Inbox': '/inbox', '📚 Pengetahuan': '/knowledge', '⚙️ Sistem': '/system'}
HELP = '''🧠 SECOND BRAIN — MULAI DARI MENU

✍️ Catat → tulis ide, catatan, atau kirim audio.
🔎 Cari → temukan catatan dengan kata kunci; tidak harus cocok semua kata.
📥 Inbox → lihat catatan yang belum diolah.
📋 Tugas → tambah tugas dan tandai selesai.
💡 Rencanakan → simpan ide, jalankan dua peran AI, lalu review proposal.

ALUR IDE → EKSEKUSI
1. Tulis ide pada menu Rencanakan.
2. Tekan Analisis dua agen jika ingin menggunakan provider AI.
3. Agen 1 membuat task dan dependensi; Agen 2 menyusun framework proposal.
4. Review, minta revisi, atau setujui. Persetujuan mengaktifkan tugas; tidak menjalankan kode otomatis.
5. Salin Prompt Codex untuk implementasi setelah Tio memberi scope persetujuan di chat Codex.

PERINTAH CEPAT
/home — dashboard ringkas
/capture — tulis catatan
/search — pencarian
/task Judul tugas — tambah tugas
/tasks — daftar tugas
/done ID — tandai selesai
/plan Ide — buat draft proposal
/plans — daftar proposal
/proposal ID — baca proposal
/prompt ID — prompt Codex
/cancel — batalkan alur input

FITUR LANJUTAN
/ask pertanyaan · /brief · /ingest · /weekly
/warroom rencana · /weave A x B · /sparring A vs B
/journal refleksi · /crm Nama - konteks
/list · /read nama/path · /system

Data aktif berada di workspace terpisah dari kode Git. Arsip lama tidak ikut pencarian. Capture, search, tugas, dan draft bisa dipakai tanpa provider AI; analisis/transkripsi cloud perlu key dan model yang valid.'''


class Commands(LegacyCommands):
    def __init__(self, settings, analysis=None):
        super().__init__(settings, analysis)
        self.hub = Hub(settings.root)
        self.planner = Planner(settings, self.analysis.ai)
        self.owner = settings.allowed_user or 'local'

    def ask_input(self, action, text):
        self.hub.session(self.owner, action)
        return Reply(text + '\n\nKetik /cancel untuk batal.', [[('Batal', 'cancel')]])

    def home(self):
        notes, streams, pending, inbox = vault.snapshot(self.root, False)
        tasks = self.hub.tasks()
        open_tasks = [task for task in tasks if task['state'] != 'done']
        waiting = [p for p in self.hub.plans() if p['state'] == 'ready_for_review']
        lines = ['🏠 SECOND BRAIN', 'Workspace aktif • mulai dari satu langkah kecil', '', f'📥 {len(inbox)} inbox  ·  📚 {len(notes)} catatan', f'📋 {len(open_tasks)} tugas terbuka  ·  📝 {len(waiting)} proposal menunggu review', '', 'TUGAS BERIKUTNYA']
        lines += [f'• {task["title"]} ({task["id"]})' for task in open_tasks[:3]] or ['Belum ada tugas. Tambahkan tugas atau rencanakan satu ide.']
        if waiting:
            lines += ['', 'PERLU KEPUTUSAN'] + [f'• {p["id"]}: {p["idea"][:90]}' for p in waiting[:3]]
        lines += ['', 'Pilih menu di bawah. Teks biasa langsung tersimpan sebagai catatan.']
        return Reply('\n'.join(lines), menu=True)

    def task_reply(self):
        tasks = self.hub.tasks()
        active = [task for task in tasks if task['state'] != 'done']
        if not active:
            return Reply('📋 TUGAS\nBelum ada tugas terbuka.\n\nSimpan satu task yang bisa selesai hari ini.', [[('＋ Tambah tugas', 'task:add'), ('💡 Rencanakan ide', 'menu:plan')]])
        lines = ['📋 TUGAS AKTIF', 'Urutan terbaru; pilih task untuk ditandai selesai.', '']
        buttons = []
        for task in active[:10]:
            lines.append(f'{task["id"]} · {task["title"]}')
            buttons.append([('✓ ' + task['title'][:35], 'task:done:' + task['id'])])
        buttons.append([('＋ Tambah tugas', 'task:add')])
        return Reply('\n'.join(lines) + f'\n\n{len(active)} terbuka · {len(tasks) - len(active)} selesai', buttons)

    def plan_reply(self, identifier):
        plan = self.hub.plan(identifier)
        labels = {'draft': 'Draft · AI belum dijalankan', 'agent1_done': 'Agen 1 selesai · lanjutkan Agen 2', 'ready_for_review': 'Menunggu review Tio', 'approved': 'Disetujui · tugas aktif'}
        lines = [f'💡 {identifier} · Proposal v{plan["version"]}', labels[plan['state']], '', plan['idea']]
        if plan['proposal']:
            proposal = json.loads(plan['proposal'])
            lines += ['', 'REKOMENDASI', proposal['recommendation'], '', 'FRAMEWORK', proposal['framework'], '', 'SCOPE', proposal['scope'], '', 'RISIKO & ASUMSI', proposal['risks'], '', 'KEPUTUSAN REVIEW', proposal['review_questions']]
        if plan['tasks']:
            lines += ['', 'TUGAS AGEN 1'] + [f'{t["id"]}. {t["title"]}\nSelesai jika: {t["done_when"]}' for t in json.loads(plan['tasks'])]
        buttons = []
        if plan['state'] in ('draft', 'agent1_done'):
            buttons.append([('🧠 Analisis dua agen (AI)', 'plan:run:' + identifier)])
        if plan['state'] == 'ready_for_review':
            buttons.append([('✓ Setujui dan aktifkan tugas', 'plan:approve:' + identifier + ':' + str(plan['version']))])
            buttons.append([('✎ Minta revisi', 'plan:revise:' + identifier)])
        buttons.append([('📋 Salin prompt Codex', 'plan:prompt:' + identifier)])
        return Reply('\n'.join(lines), buttons)

    def callback(self, action):
        if action == 'cancel':
            return self.dispatch('/cancel')
        if action == 'task:add':
            return self.dispatch('/task')
        if action.startswith('task:done:'):
            return self.dispatch('/done ' + action.split(':', 2)[2])
        if action.startswith('menu:'):
            return self.dispatch('/' + action[5:])
        parts = action.split(':')
        if len(parts) in (3, 4) and parts[0] == 'plan':
            operation, identifier = parts[1:3]
            if operation == 'run':
                self.planner.generate(identifier)
                return self.plan_reply(identifier)
            if operation == 'approve':
                if len(parts) != 4 or not parts[3].isdigit() or self.hub.plan(identifier)['version'] != int(parts[3]):
                    raise ValueError('Versi proposal berubah atau tidak disebutkan. Buka proposal terbaru sebelum menyetujui.')
                self.hub.approve(identifier)
                self.planner.export(identifier)
                audit(self.root, 'REVIEW_APPROVED', identifier + ' v' + parts[3])
                return Reply('✓ Proposal disetujui dan tugas diaktifkan.\nImplementasi belum dijalankan. Buka Tugas atau salin prompt Codex.', [[('📋 Tugas', 'menu:tasks'), ('Prompt Codex', 'plan:prompt:' + identifier)]])
            if operation == 'prompt':
                return Reply('📋 PROMPT CODEX\nSalin teks berikut. Jika bekerja di komputer lain, salin juga dokumen proposal.\n\n' + self.planner.codex_prompt(identifier))
            if operation == 'revise':
                if self.hub.plan(identifier)['state'] == 'approved':
                    raise ValueError('Proposal sudah disetujui. Buat draft baru untuk perubahan scope.')
                return self.ask_input('revise:' + identifier, 'Apa yang ingin Tio ubah pada proposal ini?')
        raise ValueError('Tombol tidak dikenal atau sudah tidak berlaku. Buka /home.')

    def dispatch(self, text):
        text = text.strip()
        if text in LABELS:
            self.hub.clear_session(self.owner)
            text = LABELS[text]
        if text.startswith('/'):
            self.hub.clear_session(self.owner)
        else:
            action = self.hub.session(self.owner)
            if action:
                self.hub.clear_session(self.owner)
                if action.startswith('revise:'):
                    identifier = action.split(':', 1)[1]
                    plan = self.hub.plan(identifier)
                    if plan['state'] == 'approved':
                        raise ValueError('Proposal sudah disetujui; buat draft baru untuk revisi.')
                    with process_lock(self.settings.project, 'plan-' + identifier), self.hub.connection() as db:
                        db.execute('UPDATE plans SET idea=?,version=version+1,state=?,tasks=NULL,proposal=NULL,engine=NULL WHERE id=?', (plan['idea'] + '\n\nRevisi Tio: ' + text, 'draft', identifier))
                    self.planner.export(identifier)
                    return self.plan_reply(identifier)
                text = '/' + action + ' ' + text
        parts = text.split(maxsplit=1)
        command = parts[0].split('@')[0].lower() if parts else ''
        argument = parts[1] if len(parts) > 1 else ''
        if command in ('/start', '/home', '/menu'):
            return self.home()
        if command == '/help':
            return Reply(HELP, menu=True)
        if command == '/cancel':
            return Reply('Alur input dibatalkan. Pilih menu untuk mulai lagi.', menu=True)
        if command in ('/capture', '/search', '/plan', '/task', '/ask') and not argument:
            questions = {'/capture': '✍️ Apa yang ingin Tio simpan?', '/search': '🔎 Catatan apa yang ingin dicari?', '/plan': '💡 Ceritakan ide, hasil yang diinginkan, dan batasannya.', '/task': '📋 Tulis satu tugas yang ingin dikerjakan.', '/ask': 'Apa pertanyaan Tio tentang catatan yang tersimpan?'}
            return self.ask_input(command[1:], questions[command])
        if command == '/search':
            hits = search(self.root, argument)
            return Reply('🔎 HASIL PENCARIAN\n\n' + ('\n\n'.join(f'{n["title"]}\n/read {n["path"]}\n{n["excerpt"]}' for n in hits) or 'Belum ditemukan. Coba satu kata kunci atau simpan catatan pertama.'))
        if command in ('/tasks', '/todo'):
            return self.task_reply()
        if command == '/task':
            identifier = self.hub.add_task(argument)
            return Reply(f'✓ Tugas tersimpan\n{argument}\n{identifier}', [[('Tandai selesai', 'task:done:' + identifier), ('Lihat tugas', 'menu:tasks')]])
        if command == '/done':
            self.hub.set_task(argument.strip(), 'done')
            task = next(t for t in self.hub.tasks() if t['id'] == argument.strip())
            if task['plan_id']:
                self.planner.export(task['plan_id'])
            return self.task_reply()
        if command == '/plan':
            identifier = self.hub.new_plan(argument)
            self.planner.export(identifier)
            audit(self.root, 'PLAN_DRAFT', identifier)
            return self.plan_reply(identifier)
        if command == '/plans':
            plans = self.hub.plans()[:10]
            return Reply('💡 PROPOSAL\n' + ('\n'.join(f'{p["id"]} · {p["state"]}\n/proposal {p["id"]}' for p in plans) or 'Belum ada proposal. Tekan Rencanakan.'), [[('Buat draft', 'menu:plan')]])
        if command == '/proposal':
            return self.plan_reply(argument.strip())
        if command == '/revise':
            identifier, _, instruction = argument.partition(' ')
            if not instruction.strip():
                raise ValueError('Format: /revise ID perubahan yang diminta')
            self.callback('plan:revise:' + identifier)
            return self.dispatch(instruction)
        if command in ('/planrun', '/approve', '/prompt'):
            if command == '/approve':
                values = argument.split()
                if len(values) != 2:
                    raise ValueError('Format: /approve ID versi; buka proposal untuk melihat versi terbaru.')
                return self.callback('plan:approve:' + values[0] + ':' + values[1])
            return self.callback('plan:' + {'/planrun': 'run', '/approve': 'approve', '/prompt': 'prompt'}[command] + ':' + argument.strip())
        if command in ('/inbox', '/knowledge'):
            prefixes = ('inbox_raw/', 'raw/') if command == '/inbox' else ('wiki/', 'lattices/')
            items = [n for n in vault.notes(self.root, False) if n['path'].startswith(prefixes) and '/processed/' not in n['path']]
            items.sort(key=lambda n: n['mtime'], reverse=True)
            return Reply(('📥 INBOX' if command == '/inbox' else '📚 PENGETAHUAN') + f'\n{len(items)} catatan\n\n' + ('\n\n'.join(f'{n["title"]}\n/read {n["path"]}' for n in items[:10]) or 'Masih kosong. Simpan catatan pertama lewat Catat.'))
        if command in ('/system', '/status'):
            return Reply(f'⚙️ SECOND BRAIN {__version__}\nWorkspace: {self.root.name}\nCatatan aktif: {len(vault.notes(self.root, False))}\nTugas: {len(self.hub.tasks())}\nProposal: {len(self.hub.plans())}\nArsip: {len(archives(self.settings.project))}\n\nCapture, task, dan search berjalan lokal. Status ini belum menguji provider AI atau pengiriman Telegram.', menu=True)
        if command == '/brief':
            return self.home()
        if command == '/sync':
            from .sync import sync
            from dataclasses import replace
            return sync(replace(self.settings, root=self.settings.project), push=argument == 'push')
        return super().dispatch(text)
