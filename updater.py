#!/usr/bin/env python3
# updater.py - Sistema di auto-aggiornamento per Timbracart

import os
import sys
import time
import json
import requests
import shutil
import subprocess
from pathlib import Path

# Configurazione
UPDATE_CHECK_URL = "https://raw.githubusercontent.com/ImKshakvs/BadgeEmpire/main/version.json"
APP_NAME = "BadgeEmpire.exe"

def download_file(url, destination):
    """Scarica un file con barra di progresso"""
    print(f"\n[DOWNLOAD] Scaricamento da: {url}")
    
    response = requests.get(url, stream=True, timeout=30)
    total_size = int(response.headers.get('content-length', 0))
    
    downloaded = 0
    with open(destination, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    progress = (downloaded / total_size) * 100
                    bar_length = 50
                    filled = int(bar_length * downloaded / total_size)
                    bar = '█' * filled + '░' * (bar_length - filled)
                    print(f"\r[DOWNLOAD] [{bar}] {progress:.1f}%", end='')
    
    print(f"\n[DOWNLOAD] Completato! ({downloaded / 1024 / 1024:.1f} MB)")
    return True

def get_app_directory():
    """Ottieni la directory dell'applicazione"""
    if getattr(sys, 'frozen', False):
        # Eseguibile PyInstaller
        return os.path.dirname(sys.executable)
    else:
        # Script Python
        return os.path.dirname(os.path.abspath(__file__))

def apply_update(new_exe_path, current_exe_path):
    """Applica l'aggiornamento sostituendo l'eseguibile"""
    print("\n[UPDATE] Applicazione aggiornamento...")
    
    backup_path = current_exe_path + ".old"
    
    try:
        # 1. Rimuovi vecchio backup se esiste
        if os.path.exists(backup_path):
            print("[UPDATE] Rimozione vecchio backup...")
            os.remove(backup_path)
        
        # 2. Rinomina l'eseguibile corrente come backup
        if os.path.exists(current_exe_path):
            print("[UPDATE] Backup eseguibile corrente...")
            os.rename(current_exe_path, backup_path)
        
        # 3. Sposta il nuovo eseguibile
        print("[UPDATE] Installazione nuova versione...")
        shutil.move(new_exe_path, current_exe_path)
        
        print("[UPDATE] ✅ Aggiornamento applicato con successo!")
        return True
        
    except Exception as e:
        print(f"[UPDATE] ❌ ERRORE: {e}")
        
        # Ripristina il backup in caso di errore
        if os.path.exists(backup_path) and not os.path.exists(current_exe_path):
            print("[UPDATE] Ripristino backup...")
            os.rename(backup_path, current_exe_path)
        
        return False

def check_and_update():
    """Controlla e applica aggiornamenti"""
    print("=" * 60)
    print("   TIMBRACART AUTO-UPDATER")
    print("=" * 60)
    
    try:
        # Leggi argomenti: versione corrente e se aspettare la chiusura dell'app
        current_version = sys.argv[1] if len(sys.argv) > 1 else "0.0.0"
        wait_for_close = sys.argv[2] if len(sys.argv) > 2 else "no"
        
        print(f"\n[INFO] Versione corrente: {current_version}")
        
        # Se richiesto, aspetta che l'app si chiuda
        if wait_for_close == "yes":
            print("[INFO] Attesa chiusura applicazione...")
            time.sleep(3)
        
        # Controlla aggiornamenti
        print(f"\n[CHECK] Controllo aggiornamenti da: {UPDATE_CHECK_URL}")
        response = requests.get(UPDATE_CHECK_URL, timeout=10)
        
        if response.status_code != 200:
            print(f"[CHECK] ❌ Errore HTTP {response.status_code}")
            return False
        
        update_info = response.json()
        latest_version = update_info['version']
        download_url = update_info['download_url']
        
        print(f"[CHECK] Ultima versione disponibile: {latest_version}")
        
        # Confronto versioni semplice (funziona con formato X.Y.Z)
        if latest_version <= current_version:
            print("[CHECK] ✅ App già aggiornata!")
            return False
        
        print(f"\n[CHECK] ⬇️  Nuova versione disponibile: {latest_version}")
        print(f"[CHECK] Changelog:\n{update_info.get('changelog', 'N/A')}")
        
        # Determina path dell'applicazione
        app_dir = get_app_directory()
        current_exe = os.path.join(app_dir, APP_NAME)
        temp_exe = os.path.join(app_dir, "Timbracart_new.exe")
        
        print(f"\n[INFO] Directory app: {app_dir}")
        print(f"[INFO] Eseguibile corrente: {current_exe}")
        
        # Scarica la nuova versione
        if download_file(download_url, temp_exe):
            # Applica l'aggiornamento
            if apply_update(temp_exe, current_exe):
                print("\n[SUCCESS] ✅ Aggiornamento completato!")
                print("[SUCCESS] Riavvio applicazione...")
                time.sleep(2)
                
                # Riavvia l'applicazione
                subprocess.Popen([current_exe])
                
                print("[SUCCESS] Applicazione riavviata. Chiusura updater...")
                return True
        
        return False
        
    except Exception as e:
        print(f"\n[ERROR] ❌ Errore durante l'aggiornamento: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Pausa prima di chiudere
        time.sleep(3)

if __name__ == "__main__":
    success = check_and_update()
    
    if not success:
        print("\nPremi INVIO per chiudere...")
        input()
    
    sys.exit(0 if success else 1)