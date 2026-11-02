"""Cross-platform command line interface."""
import argparse
import json
from pathlib import Path
import sys
from .vault import ROOT, home, capture, doctor, search, show_status, show_results

def menu(root):
    while True:
        print('\nSECOND BRAIN\n1. Ringkasan\n2. Catat ide\n3. Cari catatan\n4. Perbarui HOME.md\n5. Periksa sistem\n6. Task eksekusi (Agen 1 + Agen 2)\n0. Keluar')
        choice = input('Pilih: ').strip()
        if choice == '0':
            return 0
        if choice == '1':
            show_status(root)
        elif choice == '2':
            print('Isi catatan (satu baris; teks panjang bisa lewat capture --file):')
            text = input('> ')
            if text.strip():
                print(f'Tersimpan: {capture(root, text)}')
        elif choice == '3':
            show_results(search(root, input('Kata kunci: ')))
        elif choice == '4':
            print(f'Diperbarui: {home(root)}. Buka HOME di Obsidian.')
        elif choice == '5':
            doctor(root)
        elif choice == '6':
            idea = input('Ide yang ingin direncanakan: ')
            domain = input('Domain work / engineering / private [work]: ').strip() or 'work'
            if idea.strip():
                create_plan(root, idea, domain=domain)
        else:
            print('Pilih angka 0–6.')

def create_plan(root, idea, title=None, domain='work'):
    from .execution import prepare
    paths, prompt = prepare(root, idea, title, domain)
    try:
        home(root)
    except (OSError, ValueError) as error:
        print(f'Paket tersimpan; HOME belum diperbarui: {error}', file=sys.stderr)
    print(f'Paket disiapkan: {paths["brief"]}\nAgen belum dijalankan. Salin prompt berikut ke Codex:\n\n{prompt}')
    return paths

def main(argv=None):
    parser = argparse.ArgumentParser(description='Second Brain: catat, cari, dan tinjau vault lokal tanpa API.')
    from . import __version__
    parser.add_argument('--version', action='version', version=__version__)
    parser.add_argument('--vault', type=Path, default=ROOT, help='Folder vault (default: lokasi tools/brain.py)')
    commands = parser.add_subparsers(dest='command')
    commands.add_parser('menu', help='Menu interaktif')
    status = commands.add_parser('status', help='Ringkasan vault')
    status.add_argument('--include-private', action='store_true')
    finder = commands.add_parser('search', help='Cari semua kata di Markdown terbaru')
    finder.add_argument('query')
    finder.add_argument('--include-private', action='store_true')
    finder.add_argument('--limit', type=int, default=8)
    finder.add_argument('--json', action='store_true')
    writer = commands.add_parser('capture', help='Simpan teks pengguna ke inbox (tanpa AI)')
    writer.add_argument('text', nargs='?')
    writer.add_argument('--file', type=Path, help='Baca teks UTF-8 dari file')
    writer.add_argument('--title')
    planner = commands.add_parser('plan', help='Siapkan paket ide dan prompt dua agen untuk review')
    planner.add_argument('idea', nargs='?')
    planner.add_argument('--file', type=Path, help='Baca ide dari file UTF-8')
    planner.add_argument('--title')
    planner.add_argument('--domain', choices=['work', 'engineering', 'private'], default='work')
    planner.add_argument('--legacy-packet', action='store_true', help='Compatibilitas: buat paket Markdown lima file')
    commands.add_parser('home', help='Perbarui HOME.md untuk Obsidian')
    commands.add_parser('doctor', help='Pemeriksaan lokal baca saja')
    commands.add_parser('health', help='Pemeriksaan konfigurasi lokal tanpa koneksi jaringan')
    bot = commands.add_parser('bot', help='Jalankan satu runner Telegram')
    bot.add_argument('--check', action='store_true', help='Validasi konfigurasi saja, jangan hubungi Telegram')
    syncer = commands.add_parser('sync', help='Status Git; push harus eksplisit')
    syncer.add_argument('--push', action='store_true')
    for operation in ('ask', 'brief', 'weave', 'warroom', 'sparring', 'weekly', 'ingest'):
        command = commands.add_parser(operation, help=f'Jalankan {operation} melalui service yang sama dengan Telegram')
        command.add_argument('text', nargs='*')
    for operation in ('tasks', 'task', 'done', 'plans', 'proposal', 'planrun', 'approve', 'revise', 'prompt'):
        command = commands.add_parser(operation, help=f'Workspace v3: {operation}')
        command.add_argument('text', nargs='*')
    dashboard = commands.add_parser('serve', help='Dashboard lokal di browser')
    dashboard.add_argument('--port', type=int, default=8765)
    dashboard.add_argument('--no-open', action='store_true')
    reset = commands.add_parser('reset', help='Arsipkan workspace aktif dan mulai bersih')
    reset.add_argument('--archive', action='store_true', required=True, help='Wajib: verifikasi arsip sebelum reset')
    reset.add_argument('--source', type=Path, help='Opsional: arsipkan workspace dari checkout lama sebelum mulai bersih')
    commands.add_parser('archives', help='Daftar snapshot arsip')
    restore = commands.add_parser('restore', help='Pulihkan arsip ke workspace baru')
    restore.add_argument('identifier')
    args = parser.parse_args(argv)
    project = args.vault.resolve()
    if not project.is_dir():
        parser.error('Folder vault tidak ditemukan.')
    try:
        from .config import Settings
        settings = Settings.load(project)
        root = settings.root
        if args.command in (None, 'serve'):
            from .dashboard import run
            return run(settings, args.port if args.command else 8765, not args.no_open if args.command else True)
        if args.command == 'menu':
            return menu(root)
        if args.command == 'reset':
            from .workspace import reset
            print(json.dumps(reset(project, args.source), ensure_ascii=False, indent=2))
        elif args.command == 'archives':
            from .workspace import archives
            print(json.dumps(archives(project), ensure_ascii=False, indent=2))
        elif args.command == 'restore':
            from .workspace import restore
            print('Workspace dipulihkan:', restore(project, args.identifier))
        elif args.command == 'status':
            if args.include_private:
                show_status(root, True)
            else:
                from .controller import Commands
                print(Commands(settings).dispatch('/status'))
        elif args.command == 'search':
            if not 1 <= args.limit <= 100:
                parser.error('--limit harus antara 1 dan 100.')
            if args.include_private:
                results = search(root, args.query, True, args.limit)
            else:
                from .search_index import search as indexed_search
                results = indexed_search(root, args.query, args.limit)
            print(json.dumps(results, ensure_ascii=False, indent=2)) if args.json else show_results(results)
        elif args.command == 'capture':
            if (args.text is None) == (args.file is None):
                parser.error('Pilih teks atau --file, tepat salah satu.')
            print(f'Tersimpan: {capture(root, args.file.read_text(encoding="utf-8-sig") if args.file else args.text, args.title)}')
        elif args.command == 'home':
            print(f'Diperbarui: {home(root)}')
        elif args.command == 'plan':
            if (args.idea is None) == (args.file is None):
                parser.error('Pilih ide atau --file, tepat salah satu.')
            idea = args.file.read_text(encoding='utf-8-sig') if args.file else args.idea
            if args.legacy_packet or args.domain != 'work':
                create_plan(root, idea, args.title, args.domain)
            else:
                from .controller import Commands
                print(Commands(settings).dispatch('/plan ' + idea))
        elif args.command == 'doctor':
            doctor(root)
        elif args.command in ('ask', 'brief', 'weave', 'warroom', 'sparring', 'weekly', 'ingest', 'tasks', 'task', 'done', 'plans', 'proposal', 'planrun', 'approve', 'revise', 'prompt'):
            from .commands import Commands
            print(Commands(settings).dispatch('/' + args.command + ' ' + ' '.join(args.text)))
        elif args.command in ('bot', 'health', 'sync'):
            from .config import Settings
            if args.command == 'bot':
                settings.validate_bot()
                if args.check:
                    print('Konfigurasi bot valid secara lokal. Tidak menghubungi Telegram/provider.')
                else:
                    import logging
                    from .bot import run
                    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
                    run(settings)
            elif args.command == 'sync':
                from .sync import sync
                from dataclasses import replace
                print(sync(replace(settings, root=project), args.push))
            else:
                doctor(root)
                print('Health: modul core berhasil dimuat. Untuk validasi konfigurasi bot gunakan bot --check.')
                database = project / 'data/telegram-state.sqlite'
                if database.exists():
                    import sqlite3
                    with sqlite3.connect(f'{database.as_uri()}?mode=ro', uri=True) as connection:
                        states = dict(connection.execute('SELECT status, COUNT(*) FROM updates GROUP BY status'))
                        print(f'Telegram ledger: {states}; processing/uncertain perlu rekonsiliasi manual, bukan replay otomatis.')
    except (OSError, UnicodeError, ValueError, RuntimeError) as error:
        print(f'Gagal: {error}', file=sys.stderr)
        return 1
    except (KeyboardInterrupt, EOFError):
        print('\nSelesai.')
    return 0
