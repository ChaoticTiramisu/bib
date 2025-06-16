from pathlib import Path
import subprocess
import sys
import os
import shutil
import zipfile
import datetime
import glob
import signal
import platform

# Probeer psutil te importeren, installeer indien nodig automatisch
try:
    import psutil
except ImportError:
    print("psutil niet gevonden. Installeren...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "psutil"])
    import psutil

def is_wsl():
    """Detecteer of het script draait in Windows Subsystem for Linux (WSL)."""
    return 'microsoft' in platform.uname().release.lower()

def create_venv(venv_name):
    """
    Maak een virtuele omgeving aan met de opgegeven naam.
    Indien de map al bestaat, vraag of deze verwijderd moet worden.
    """
    if os.path.exists(venv_name):
        antwoord = input(f"De map '{venv_name}' bestaat al. Wil je deze verwijderen en opnieuw aanmaken? (j/n): ").strip().lower()
        if antwoord == 'j':
            try:
                shutil.rmtree(venv_name)
                print(f"Map '{venv_name}' verwijderd.")
            except Exception as e:
                print(f"Kon map '{venv_name}' niet verwijderen: {e}")
                sys.exit(1)
        else:
            print(f"Gebruik bestaande virtuele omgeving '{venv_name}'.")
            return
    try:
        subprocess.check_call([sys.executable, '-m', 'venv', venv_name])
        print(f"Virtuele omgeving '{venv_name}' succesvol aangemaakt.")
    except subprocess.CalledProcessError as e:
        print(f"Fout bij aanmaken virtuele omgeving '{venv_name}': {e}")
        sys.exit(1)

def get_venv_dir():
    # Bepaal de submap voor executables in de virtuele omgeving
    return "Scripts" if platform.system() == "Windows" else "bin"

def get_python_path():
    # Geef het pad naar de python executable in de virtuele omgeving terug
    venv_dir = get_venv_dir()
    python_name = "python.exe" if platform.system() == "Windows" else "python"
    return str(Path("env") / venv_dir / python_name)

def get_pip_path():
    # Geef het pad naar de pip executable in de virtuele omgeving terug
    venv_dir = get_venv_dir()
    pip_name = "pip.exe" if platform.system() == "Windows" else "pip"
    return str(Path("env") / venv_dir / pip_name)

def install_dependencies(venv_name, requirements_file):
    """
    Installeer dependencies uit het requirements.txt bestand in de virtuele omgeving.
    """
    python_path = get_python_path()
    pip_path = get_pip_path()

    # Controleer of pip aanwezig is, installeer indien nodig
    if not Path(pip_path).exists():
        print(f"Pip niet gevonden in virtuele omgeving: {pip_path}")
        print("Probeer pip te installeren...")
        try:
            subprocess.check_call([python_path, '-m', 'ensurepip'])
            subprocess.check_call([python_path, '-m', 'pip', 'install', '--upgrade', 'pip'])
            print("Pip succesvol geïnstalleerd.")
        except subprocess.CalledProcessError as e:
            print(f"Fout bij installeren van pip: {e}")
            sys.exit(1)

    # Controleer of requirements.txt aanwezig is
    if not Path(requirements_file).exists():
        print(f"Requirements-bestand niet gevonden: {requirements_file}")
        sys.exit(1)

    # Installeer de dependencies
    try:
        subprocess.check_call([pip_path, 'install', '-r', requirements_file])
        print("Dependencies succesvol geïnstalleerd.")
    except subprocess.CalledProcessError as e:
        print(f"Fout bij installeren dependencies: {e}")
        sys.exit(1)

def backup_database_and_uploads():
    """
    Maak een backup van de database en alle uploads naar een zip-bestand.
    """
    backup_dir = 'backups'
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    zip_filename = os.path.join(backup_dir, f'backup_{timestamp}.zip')
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as backup_zip:
        # Voeg database toe aan de backup
        db_path = os.path.join('instance', 'bib.db')
        if os.path.exists(db_path):
            backup_zip.write(db_path, arcname='bib.db')
            print(f"Database toegevoegd aan backup: {db_path}")
        else:
            print(f"Database niet gevonden: {db_path}")
        # Voeg uploads toe aan de backup
        upload_dir = os.path.join('static', 'upload')
        if os.path.exists(upload_dir):
            for root, _, files in os.walk(upload_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, start=upload_dir)
                    backup_zip.write(file_path, arcname=os.path.join('upload', arcname))
            print(f"Uploads toegevoegd aan backup: {upload_dir}")
        else:
            print(f"Uploadmap niet gevonden: {upload_dir}")
    print(f"Backup succesvol aangemaakt: {zip_filename}")

def restore_backup():
    """
    Herstel de database en uploads vanuit een geselecteerd backup-zipbestand.
    """
    backup_dir = 'backups'
    if not os.path.exists(backup_dir):
        print(f"Backupmap niet gevonden: {backup_dir}")
        return
    backups = sorted(glob.glob(os.path.join(backup_dir, 'backup_*.zip')))
    if not backups:
        print("Geen backup-bestanden gevonden.")
        return
    print("Beschikbare backups:")
    for idx, b in enumerate(backups, 1):
        print(f"{idx}. {os.path.basename(b)}")
    # Vraag de gebruiker om een backup te kiezen of een pad op te geven
    keuze = input(f"Kies een backup om te herstellen (1-{len(backups)}) of geef een pad op: ").strip()
    keuze = keuze.strip('"').strip("'")
    # Bepaal het pad naar het te herstellen zip-bestand
    if keuze.isdigit() and 1 <= int(keuze) <= len(backups):
        zip_path = backups[int(keuze)-1]
    else:
        zip_path = keuze
    # Controleer of het gekozen backup-bestand bestaat
    if not os.path.exists(zip_path):
        print(f"Backup-bestand niet gevonden: {zip_path}")
        return
    # Vraag bevestiging aan de gebruiker voordat bestaande data wordt overschreven
    confirm = input("Weet je zeker dat je de huidige database en uploads wilt overschrijven? (j/n): ").strip().lower()
    if confirm != 'j':
        print("Herstellen geannuleerd.")
        return
    # Open het geselecteerde zip-bestand
    with zipfile.ZipFile(zip_path, 'r') as z:
        # Herstel databasebestand indien aanwezig in de backup
        if 'bib.db' in z.namelist():
            os.makedirs('instance', exist_ok=True)
            z.extract('bib.db', 'instance')
            print("Database hersteld.")
        else:
            print("bib.db niet gevonden in backup.")
        # Zoek alle upload-bestanden in de backup
        upload_members = [m for m in z.namelist() if m.startswith('upload/')]
        upload_dir = os.path.join('static', 'upload')
        if upload_members:
            # Verwijder bestaande uploadmap indien aanwezig
            if os.path.exists(upload_dir):
                try:
                    shutil.rmtree(upload_dir)
                except Exception as e:
                    print(f"Kon uploadmap niet verwijderen: {e}")
                    return
            # Maak uploadmap opnieuw aan
            os.makedirs(upload_dir, exist_ok=True)
            # Extraheer alle upload-bestanden naar de juiste locatie
            for member in upload_members:
                z.extract(member, os.path.join('static'))
            print("Uploads hersteld.")
        else:
            print("Geen uploads gevonden in backup.")
    print(f"Backup {os.path.basename(zip_path)} succesvol teruggezet.")

GUNICORN_PID_FILE = 'gunicorn.pid'

def find_gunicorn_process():
    """
    Zoek het gunicorn-proces dat draait voor deze app.
    Retourneert een lijst van psutil.Process instanties.
    """
    result = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info['cmdline']
            if not cmdline:
                continue
            # Controleer of 'gunicorn' in het commando zit en 'app:app' als target
            if any('gunicorn' in os.path.basename(str(arg)).lower() for arg in cmdline) and 'app:app' in ' '.join(cmdline):
                result.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return result

def start_server():
    """
    Start de server in een nieuwe terminal of command prompt, afhankelijk van het platform.
    Op Windows wordt waitress gebruikt, op Linux gunicorn.
    """
    if platform.system() == "Windows":
        venv_activate = str(Path('env') / 'Scripts' / 'activate.bat')
        waitress_cmd = f"python -m waitress --port=5000 app:app"
        cmd = f'start "waitress_server" cmd.exe /K "call {venv_activate} && {waitress_cmd}"'
        subprocess.Popen(cmd, shell=True)
        print("Waitress gestart in een nieuw venster met geactiveerde virtuele omgeving.")
    else:
        if is_wsl():
            print("Je draait in WSL. Automatisch openen van een Linux-terminal werkt hier niet. Start de server handmatig:")
            print(f"source env/bin/activate && gunicorn -w 2 -b 0.0.0.0:5000 app:app")
            return
        venv_activate = str(Path('env') / 'bin' / 'activate')
        gunicorn_cmd = f"gunicorn -w 2 -b 0.0.0.0:5000 app:app"
        # Probeer verschillende terminals te openen, afhankelijk van wat beschikbaar is
        terminals = [
            ['gnome-terminal', '--', 'bash', '-c', f"source {venv_activate}; {gunicorn_cmd}; exec bash"],
            ['konsole', '-e', f"bash -c 'source {venv_activate}; {gunicorn_cmd}; exec bash'"],
            ['xfce4-terminal', '-e', f"bash -c 'source {venv_activate}; {gunicorn_cmd}; exec bash'"],
            ['xterm', '-e', f"bash -c 'source {venv_activate}; {gunicorn_cmd}; exec bash'"],
            ['x-terminal-emulator', '-e', f"bash -c 'source {venv_activate}; {gunicorn_cmd}; exec bash'"],
        ]
        opened = False
        for term in terminals:
            try:
                subprocess.Popen(term)
                print(f"Gunicorn gestart in een nieuwe terminal: {' '.join(term)}")
                opened = True
                break
            except Exception:
                continue
        if not opened:
            print("Kon geen geschikte terminal openen. Start de server handmatig:")
            print(f"source env/bin/activate && gunicorn -w 2 -b 0.0.0.0:5000 app:app")

def stop_server():
    """
    Stop de serverprocessen (waitress op Windows, gunicorn op Linux).
    """
    if platform.system() == "Windows":
        found = False
        cwd = str(Path('.').resolve())
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cwd']):
            try:
                cmdline = proc.info['cmdline']
                proc_cwd = proc.info.get('cwd', None)
                # Zoek waitress-processen in de huidige directory
                if cmdline and any('waitress' in str(arg).lower() for arg in cmdline):
                    if proc_cwd and str(Path(proc_cwd).resolve()) == cwd:
                        proc.terminate()
                        found = True
                        print(f"Waitress-proces (PID: {proc.pid}) gestopt.")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        if not found:
            print("Geen actieve waitress-processen gevonden in deze workspace.")
        # Probeer eventueel openstaande vensters te sluiten
        try:
            subprocess.call('taskkill /FI "WINDOWTITLE eq waitress_server*" /T /F', shell=True)
        except Exception:
            pass
    else:
        running = find_gunicorn_process()
        for proc in running:
            try:
                proc.terminate()
                proc.wait(timeout=5)
                print(f"Gunicorn-proces (PID: {proc.pid}) netjes gestopt.")
            except Exception as e:
                print(f"Kon gunicorn-proces (PID: {proc.pid}) niet stoppen: {e}")

def restart_server():
    """
    Herstart de server door eerst te stoppen en daarna opnieuw te starten.
    """
    stop_server()
    import time
    time.sleep(2)
    start_server()

def start_app():
    """
    Start app.py in een nieuwe terminal of command prompt met geactiveerde virtuele omgeving.
    """
    if os.name == 'nt':
        venv_activate = os.path.abspath(os.path.join('env', 'Scripts', 'activate.bat'))
        cmd = f'start "app_server" cmd.exe /K "call {venv_activate} && python app.py"'
        subprocess.Popen(cmd, shell=True)
        print("app.py gestart in een nieuw venster met geactiveerde virtuele omgeving.")
    else:
        venv_activate = os.path.abspath(os.path.join('env', 'bin', 'activate'))
        terminals = [
            ['gnome-terminal', '--', 'bash', '-c', f"source {venv_activate}; python app.py; exec bash"],
            ['konsole', '-e', f"bash -c 'source {venv_activate}; python app.py; exec bash'"],
            ['xfce4-terminal', '-e', f"bash -c 'source {venv_activate}; python app.py; exec bash'"],
            ['xterm', '-e', f"bash -c 'source {venv_activate}; python app.py; exec bash'"],
            ['x-terminal-emulator', '-e', f"bash -c 'source {venv_activate}; python app.py; exec bash'"],
        ]
        opened = False
        for term in terminals:
            try:
                subprocess.Popen(term)
                print(f"app.py gestart in een nieuwe terminal: {' '.join(term)}")
                opened = True
                break
            except Exception:
                continue
        if not opened:
            print("Kon geen geschikte terminal openen.")

def add_admin_account():
    """
    Voegt admin@example.com toe via database.py als deze nog niet bestaat.
    """
    try:
        python_path = get_python_path()
        subprocess.check_call([python_path, 'database.py', 'create-admin'])
    except Exception as e:
        print(f"Kon admin account niet toevoegen: {e}")

if __name__ == '__main__':
    # Zorg dat benodigde mappen bestaan
    os.makedirs("instance", exist_ok=True)
    os.makedirs("static/upload", exist_ok=True)
    # Toon het setup-menu en verwerk gebruikerskeuzes
    while True:
        print("\nSetup Menu:")
        print("1. Virtuele omgeving en dependencies installeren")
        print("2. Backup maken van database en uploads")
        print("3. Backup terugzetten (upload)")
        print("4. Start server op poort 5000 (in virtuele omgeving)")
        print("5. Herstart server (in virtuele omgeving)")
        print("6. Stop server")
        print("7. Afsluiten")
        keuze = input("Maak een keuze (1-7): ").strip()
        if keuze == '1':
            venv_name = 'env'
            requirements_file = 'requirements.txt'
            create_venv(venv_name)
            install_dependencies(venv_name, requirements_file)
            if os.name == 'nt':
                print(f"\nKlaar! Activeer de omgeving met:\n    {venv_name}\\Scripts\\activate.bat")
            else:
                print(f"\nKlaar! Activeer de omgeving met:\n    source {venv_name}/bin/activate")
            input("\nDruk op Enter om terug te keren naar het menu...")
        elif keuze == '2':
            backup_database_and_uploads()
            input("\nDruk op Enter om terug te keren naar het menu...")
        elif keuze == '3':
            restore_backup()
            input("\nDruk op Enter om terug te keren naar het menu...")
        elif keuze == '4':
            admin_vraag = input("Wil je de gebruiker admin@example.com toevoegen? (j/n): ").strip().lower()
            if admin_vraag == 'j':
                add_admin_account()
            start_server()
            input("\nDruk op Enter om terug te keren naar het menu...")
        elif keuze == '5':
            admin_vraag = input("Wil je de gebruiker admin@example.com toevoegen? (j/n): ").strip().lower()
            if admin_vraag == 'j':
                add_admin_account()
            restart_server()
            input("\nDruk op Enter om terug te keren naar het menu...")
        elif keuze == '6':
            stop_server()
            input("\nDruk op Enter om terug te keren naar het menu...")
        elif keuze == '7':
            print("Setup afgesloten.")
            break
        else:
            print("Ongeldige keuze. Probeer opnieuw.")