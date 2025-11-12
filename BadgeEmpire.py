import sys
import os
import argparse
import sqlite3
import requests
import base64
import time
import traceback
from datetime import datetime
from functools import partial
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

import subprocess

# VERSIONE DELL'APP (cambia ad ogni release)
APP_VERSION = "1.0.0"
UPDATE_CHECK_URL = "https://raw.githubusercontent.com/tuousername/timbracart/main/version.json"

# --- Configurazione Globale ---
SERVER_HOST = "100.64.205.34"
SERVER_PORT = 5000
SERVER_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "timbracart.db")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

# Crea le directory necessarie
os.makedirs(ASSETS_DIR, exist_ok=True)
os.makedirs(os.path.join(ASSETS_DIR, 'bacheca'), exist_ok=True)

# --- PyQt5 Imports ---
try:
    from PyQt5 import QtWidgets, QtCore, QtGui
    from PyQt5.QtWidgets import (
        QDialog, QMessageBox, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
        QLabel, QLineEdit, QPushButton, QTableWidget, QTextEdit, QFileDialog,
        QComboBox, QGroupBox, QMainWindow, QTabWidget, QTableWidgetItem
    )
    from PyQt5.QtCore import Qt
    PYQT_AVAILABLE = True
except ImportError:
    print("PyQt5 non è installato. Esegui: pip install PyQt5")
    PYQT_AVAILABLE = False

# --- Flask Server Imports ---
try:
    from flask import Flask, jsonify, request, send_file
    from flask_cors import CORS
    app = Flask(__name__)
    CORS(app)  # Abilita CORS per tutti i metodi HTTP
    FLASK_AVAILABLE = True
except ImportError:
    try:
        from flask import Flask, jsonify, request, send_file
        app = Flask(__name__)
        FLASK_AVAILABLE = True
    except ImportError:
        class DummyFlask:
            def __init__(self):
                print("AVVISO: Flask non trovato. Le funzioni server non funzioneranno.")
            def route(self, rule, **options):
                def decorator(f): return f
                return decorator
        app = DummyFlask()
        request = None
        def send_file(path, as_attachment=False): return path
        FLASK_AVAILABLE = False

# Stile QSS
QSS = """
QWidget {
    font-family: Arial, sans-serif;
    background-color: #F5F5F0;
}
QPushButton {
    background-color: #D3D3D3;
    border: 1px solid #A9A9A9;
    padding: 8px;
    border-radius: 4px;
}
QPushButton:hover {
    background-color: #C0C0C0;
}
QLineEdit, QTableWidget, QTextEdit, QListWidget, QComboBox {
    padding: 6px;
    border: 1px solid #A9A9A9;
    border-radius: 4px;
}
#welcome {
    font-size: 24px;
    font-weight: 600;
    color: #4CAF50;
}
#totalHours {
    font-size: 18px;
    font-weight: 700;
    color: #333333;
    padding: 10px;
    border: 1px dashed #A9A9A9;
    border-radius: 4px;
}
#plusButton {
    background-color: #4CAF50;
    color: white;
    font-size: 16px;
    font-weight: bold;
    max-width: 40px;
}
"""

# --- Funzioni Helper ---
def compare_versions(v1, v2):
    """
    Confronta due versioni in formato X.Y.Z
    Ritorna True se v2 è più recente di v1
    
    Esempi:
    compare_versions("1.0.0", "1.0.1") → True
    compare_versions("1.0.1", "1.0.0") → False
    compare_versions("1.0.0", "1.0.0") → False
    """
    try:
        # Converti stringhe in liste di numeri
        v1_parts = [int(x) for x in v1.split('.')]
        v2_parts = [int(x) for x in v2.split('.')]
        
        # Aggiungi zeri mancanti (es: "1.0" → "1.0.0")
        while len(v1_parts) < 3:
            v1_parts.append(0)
        while len(v2_parts) < 3:
            v2_parts.append(0)
        
        # Confronta numero per numero
        for i in range(3):
            if v2_parts[i] > v1_parts[i]:
                return True
            elif v2_parts[i] < v1_parts[i]:
                return False
        
        return False  # Versioni uguali
    except Exception as e:
        print(f"[VERSION] Errore confronto versioni: {e}")
        return False
    
def check_for_updates():
    """Controlla se ci sono aggiornamenti disponibili"""
    try:
        print(f"[UPDATE] Controllo aggiornamenti... (versione: {APP_VERSION})")
        response = requests.get(UPDATE_CHECK_URL, timeout=10)
        
        if response.status_code == 200:
            update_info = response.json()
            latest_version = update_info.get('version')
            
            print(f"[UPDATE] Ultima versione disponibile: {latest_version}")
            
            # USA LA FUNZIONE SEMPLICE invece di pkg_version
            if compare_versions(APP_VERSION, latest_version):
                print("[UPDATE] ✅ Aggiornamento disponibile!")
                return update_info
            
            print("[UPDATE] App già aggiornata")
        return None
    except Exception as e:
        print(f"[UPDATE] Errore: {e}")
        return None


def show_update_dialog(parent, update_info):
    """Mostra dialog aggiornamento"""
    if not PYQT_AVAILABLE:
        return
    
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Information)
    msg.setWindowTitle("🎉 Aggiornamento Disponibile!")
    
    changelog = update_info.get('changelog', 'Nessuna informazione')
    is_mandatory = update_info.get('mandatory', False)
    
    msg.setText(f"<h3>Nuova versione: {update_info['version']}</h3>")
    msg.setInformativeText(
        f"<b>Versione corrente:</b> {APP_VERSION}<br>"
        f"<b>Nuova versione:</b> {update_info['version']}<br><br>"
        f"<b>Novità:</b><pre>{changelog}</pre>"
    )
    
    if is_mandatory:
        msg.setStandardButtons(QMessageBox.Ok)
        msg.button(QMessageBox.Ok).setText("⬇️ Scarica e Installa")
        msg.setInformativeText(
            msg.informativeText() + 
            "<br><br><b style='color:red;'>⚠️ Aggiornamento obbligatorio</b>"
        )
    else:
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.button(QMessageBox.Yes).setText("⬇️ Scarica Ora")
        msg.button(QMessageBox.No).setText("⏭️ Più Tardi")
    
    result = msg.exec_()
    
    if result == QMessageBox.Yes or result == QMessageBox.Ok:
        start_updater()
        sys.exit(0)  # Chiudi l'app
    elif is_mandatory:
        sys.exit(0)  # Se obbligatorio, chiudi comunque


def start_updater():
    """Avvia updater.py"""
    try:
        # Trova il path di updater.py
        if getattr(sys, 'frozen', False):
            # Se siamo in un eseguibile
            base_dir = os.path.dirname(sys.executable)
        else:
            # Se siamo in sviluppo
            base_dir = os.path.dirname(os.path.abspath(__file__))
        
        updater_path = os.path.join(base_dir, "updater.py")
        
        if not os.path.exists(updater_path):
            QMessageBox.warning(None, "Errore", f"File updater.py non trovato in:\n{updater_path}")
            return
        
        print(f"[UPDATE] Avvio updater: {updater_path}")
        
        # Avvia updater.py in una nuova finestra
        if sys.platform == 'win32':
            # Windows: nuova finestra cmd
            subprocess.Popen([
                'cmd', '/c', 'start', 
                'python', updater_path, 
                APP_VERSION,  # Passa versione corrente
                'yes'  # Aspetta che l'app si chiuda
            ])
        else:
            # Linux/Mac
            subprocess.Popen([
                sys.executable, updater_path,
                APP_VERSION,
                'yes'
            ])
        
        print("[UPDATE] Updater avviato. Chiusura app...")
        
    except Exception as e:
        print(f"[UPDATE] Errore avvio updater: {e}")
        QMessageBox.critical(None, "Errore", f"Impossibile avviare l'updater:\n{e}")

def make_icon(name, size=24):
    """Crea un'icona"""
    icon_path = os.path.join(ASSETS_DIR, f"{name}.png")
    if not PYQT_AVAILABLE: return None
    if not os.path.exists(icon_path):
        pixmap = QtGui.QPixmap(size, size)
        pixmap.fill(QtGui.QColor("#AAAAAA"))
        return QtGui.QIcon(pixmap)
    pixmap = QtGui.QPixmap(icon_path).scaled(size, size, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
    return QtGui.QIcon(pixmap)

def audit(user_id, action, details):
    """Funzione di audit"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[AUDIT] {timestamp} - User {user_id} - {action}: {details}")

# ---------------- SERVER SIDE ----------------
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db_bacheca(conn):
    """Inizializzazione tabella Bacheca"""
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS bacheca_characters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        series_title TEXT,
        character_name TEXT,
        role TEXT,
        image_path TEXT,
        script_text TEXT,
        script_path TEXT,
        expiry_date TEXT,
        mov_path TEXT,
        created_by INTEGER,
        last_modified TEXT
    )
    ''')
    conn.commit()

def init_db():
    """Inizializzazione database"""
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        name TEXT,
        surname TEXT,
        username TEXT UNIQUE,
        password TEXT NOT NULL,
        email TEXT,
        role TEXT DEFAULT 'user',
        code TEXT UNIQUE
    )
    ''')
    
    c.execute('''
    CREATE TABLE IF NOT EXISTS work_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        date TEXT,
        hours REAL,
        reason TEXT
    )
    ''')
    
    c.execute('''
    CREATE TABLE IF NOT EXISTS removal_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        work_log_id INTEGER,
        requester_id INTEGER,
        reason TEXT,
        status TEXT DEFAULT 'pending',
        admin_id INTEGER,
        admin_reason TEXT,
        request_date TEXT,
        decision_date TEXT
    )
    ''')
    
    c.execute('''
    CREATE TABLE IF NOT EXISTS user_profiles (
        user_id INTEGER PRIMARY KEY,
        nickname TEXT,
        image_path TEXT
    )
    ''')

    conn.commit()
    
    # Admin predefinito
    admin_code = "ADMIN001"
    admin_pass = "Angelo282008"
    c.execute("SELECT id FROM users WHERE code = ?", (admin_code,))
    if c.fetchone() is None:
        print(f"[DB] Inserimento utente Admin: {admin_code}")
        c.execute("INSERT INTO users (name, surname, email, password, role, code) VALUES (?, ?, ?, ?, ?, ?)",
                  ("Angelo", "Admin", "admin@empire.it", admin_pass, "admin", admin_code))
        conn.commit()

    init_db_bacheca(conn)
    conn.close()

def _save_uploaded_file(fileobj, subdir, filename_prefix):
    if not fileobj:
        return None
    _, ext = os.path.splitext(fileobj.filename)
    ts = int(time.time())
    name = f"{filename_prefix}_{ts}{ext}"
    dest_dir = os.path.join(ASSETS_DIR, 'bacheca', secure_filename(subdir))
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, name)
    fileobj.save(dest_path)
    return os.path.relpath(dest_path, BASE_DIR)

# --- ENDPOINTS FLASK ---
@app.route('/bacheca/character', methods=['POST'])
def api_bacheca_create_character():
    if request is None: return jsonify({'status':'error','message':'Server not configured'}), 500
    try:
        series = request.form.get('series_title', 'After School')
        name = request.form.get('character_name')
        role = request.form.get('role','')
        expiry = request.form.get('expiry_date')
        script_text = request.form.get('script_text', '')
        created_by = request.form.get('created_by')

        if not name or not role:
            return jsonify({'status':'error', 'message':'Nome e Ruolo obbligatori'}), 400

        image_file = request.files.get('image_file')
        img_rel = _save_uploaded_file(image_file, series, f"img_{secure_filename(name)}") if image_file else None
        
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("INSERT INTO bacheca_characters (series_title, character_name, role, image_path, script_text, expiry_date, created_by, last_modified) VALUES (?,?,?,?,?,?,?,?)",
                  (series, name, role, img_rel, script_text, expiry, created_by, now))
        conn.commit()
        conn.close()
        
        audit(created_by, 'bacheca_create', f"Character: {series}:{name}")
        return jsonify({'status':'ok', 'message':f'Personaggio {name} creato', 'last_modified':now})
    except Exception as e:
        traceback.print_exc()
        return jsonify({'status':'error','message':str(e)}), 500

@app.route('/bacheca/last_update', methods=['GET'])
def api_bacheca_last_update():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT MAX(last_modified) FROM bacheca_characters")
    row = c.fetchone()
    conn.close()
    last = row[0] if row and row[0] else ''
    return jsonify({'last_update': last})

@app.route('/bacheca/characters', methods=['GET'])
def api_bacheca_characters():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM bacheca_characters ORDER BY series_title, character_name")
    rows = c.fetchall()
    conn.close()
    out = []
    for r in rows:
        r = dict(r)
        v_ts = int(datetime.strptime(r['last_modified'], '%Y-%m-%d %H:%M:%S').timestamp()) if r.get('last_modified') else int(time.time())
        img_url = f"{SERVER_URL}/profile_image/{r['image_path']}?v={v_ts}" if r['image_path'] else None
        mov_url = f"{SERVER_URL}/profile_image/{r['mov_path']}?v={v_ts}" if r['mov_path'] else None
        script_url = f"{SERVER_URL}/profile_image/{r['script_path']}?v={v_ts}" if r['script_path'] else None
        out.append({
            'id': r['id'],
            'series_title': r['series_title'],
            'character_name': r['character_name'],
            'role': r['role'],
            'image_url': img_url,
            'script_text': r['script_text'],
            'script_url': script_url,
            'expiry_date': r['expiry_date'],
            'mov_url': mov_url,
            'last_modified': r['last_modified']
        })
    return jsonify(out)

@app.route('/bacheca/character/<int:cid>/delete', methods=['POST'])
def api_bacheca_delete_character(cid):
    """Endpoint dedicato per eliminare un personaggio"""
    if request is None: return jsonify({'status':'error','message':'Server not configured'}), 500
    
    try:
        print(f"[SERVER] Richiesta DELETE per personaggio ID: {cid}")
        conn = get_db_connection()
        c = conn.cursor()
        # Recupera i file da eliminare
        c.execute('SELECT image_path, script_path, mov_path FROM bacheca_characters WHERE id=?', (cid,))
        r = c.fetchone()
        
        if not r:
            conn.close()
            print(f"[SERVER] Personaggio {cid} non trovato")
            return jsonify({'status':'error','message':'Personaggio non trovato'}), 404
        
        print(f"[SERVER] Personaggio trovato, eliminazione file...")
        # Elimina i file fisici
        for file_path in [r[0], r[1], r[2]]:
            if file_path:
                full_path = os.path.join(BASE_DIR, file_path)
                if os.path.exists(full_path):
                    try:
                        os.remove(full_path)
                        print(f"[SERVER] File eliminato: {full_path}")
                    except Exception as e:
                        print(f"[SERVER] Errore eliminazione file {full_path}: {e}")
        
        # Elimina il record dal database
        c.execute('DELETE FROM bacheca_characters WHERE id=?', (cid,))
        conn.commit()
        rows_affected = c.rowcount
        conn.close()
        
        print(f"[SERVER] Righe eliminate: {rows_affected}")
        
        if rows_affected > 0:
            audit(None, 'bacheca_delete', f"Character ID {cid} deleted")
            return jsonify({'status':'ok', 'message':'Personaggio eliminato con successo'})
        else:
            return jsonify({'status':'error','message':'Nessun personaggio eliminato'}), 404
            
    except Exception as e:
        print(f"[SERVER] Errore DELETE: {e}")
        traceback.print_exc()
        return jsonify({'status':'error','message':str(e)}), 500

@app.route('/bacheca/character/<int:cid>', methods=['PUT', 'DELETE'])
def api_bacheca_update_or_delete_character(cid):
    if request is None: return jsonify({'status':'error','message':'Server not configured'}), 500
    
    # DELETE - Elimina personaggio
    if request.method == 'DELETE':
        try:
            print(f"[SERVER] Richiesta DELETE per personaggio ID: {cid}")
            conn = get_db_connection()
            c = conn.cursor()
            # Recupera i file da eliminare
            c.execute('SELECT image_path, script_path, mov_path FROM bacheca_characters WHERE id=?', (cid,))
            r = c.fetchone()
            
            if not r:
                conn.close()
                print(f"[SERVER] Personaggio {cid} non trovato")
                return jsonify({'status':'error','message':'Personaggio non trovato'}), 404
            
            print(f"[SERVER] Personaggio trovato, eliminazione file...")
            # Elimina i file fisici
            for file_path in [r[0], r[1], r[2]]:
                if file_path:
                    full_path = os.path.join(BASE_DIR, file_path)
                    if os.path.exists(full_path):
                        try:
                            os.remove(full_path)
                            print(f"[SERVER] File eliminato: {full_path}")
                        except Exception as e:
                            print(f"[SERVER] Errore eliminazione file {full_path}: {e}")
            
            # Elimina il record dal database
            c.execute('DELETE FROM bacheca_characters WHERE id=?', (cid,))
            conn.commit()
            rows_affected = c.rowcount
            conn.close()
            
            print(f"[SERVER] Righe eliminate: {rows_affected}")
            
            if rows_affected > 0:
                audit(None, 'bacheca_delete', f"Character ID {cid} deleted")
                return jsonify({'status':'ok', 'message':'Personaggio eliminato con successo'})
            else:
                return jsonify({'status':'error','message':'Nessun personaggio eliminato'}), 404
                
        except Exception as e:
            print(f"[SERVER] Errore DELETE: {e}")
            traceback.print_exc()
            return jsonify({'status':'error','message':str(e)}), 500
    
    # PUT - Aggiorna personaggio
    elif request.method == 'PUT':
        try:
            data = request.get_json(force=True, silent=True)
            if not data:
                return jsonify({'status':'error','message':'JSON non valido'}), 400
            fields = []
            params = []
            for key in ('series_title','character_name','role','expiry_date','script_text'):
                if key in data:
                    fields.append(f"{key}=?")
                    params.append(data[key])
            if not fields:
                return jsonify({'status':'error','message':'Nessun campo da aggiornare'}), 400
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            params.append(now)
            params.append(cid)
            conn = get_db_connection()
            c = conn.cursor()
            c.execute(f"UPDATE bacheca_characters SET {', '.join(fields)}, last_modified=? WHERE id=?", params)
            conn.commit()
            conn.close()
            return jsonify({'status':'ok', 'last_modified':now})
        except Exception as e:
            traceback.print_exc()
            return jsonify({'status':'error','message':str(e)}), 500
    
    return jsonify({'status':'error','message':'Metodo non supportato'}), 405

@app.route('/bacheca/character/<int:cid>/upload_script', methods=['POST'])
def api_bacheca_upload_script(cid):
    """Endpoint per caricare file .docx del copione"""
    if request is None: return jsonify({'status':'error'}), 500
    try:
        script_file = request.files.get('script')
        if not script_file:
            return jsonify({'status':'error','message':'Nessun file'}), 400
        
        # Verifica che sia un .docx
        if not script_file.filename.endswith('.docx'):
            return jsonify({'status':'error','message':'Solo file .docx sono permessi'}), 400
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT series_title, character_name FROM bacheca_characters WHERE id=?', (cid,))
        r = c.fetchone()
        if not r:
            conn.close()
            return jsonify({'status':'error','message':'Character non trovato'}), 404
        
        series, name = r
        script_rel = _save_uploaded_file(script_file, series, f"script_{secure_filename(name)}")
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        c.execute('UPDATE bacheca_characters SET script_path=?, last_modified=? WHERE id=?', (script_rel, now, cid))
        conn.commit()
        conn.close()
        
        return jsonify({'status':'ok', 'script_url': f"{SERVER_URL}/profile_image/{script_rel}", 'last_modified': now})
    except Exception as e:
        traceback.print_exc()
        return jsonify({'status':'error','message':str(e)}), 500

@app.route('/bacheca/character/<int:cid>/download_script', methods=['GET'])
def api_bacheca_download_script(cid):
    """Endpoint per scaricare il copione .docx"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT script_path, character_name FROM bacheca_characters WHERE id=?', (cid,))
    r = c.fetchone()
    conn.close()
    if not r or not r[0]:
        return jsonify({'status':'error','message':'No script available'}), 404
    script_rel = r[0]
    char_name = r[1]
    script_path = os.path.join(BASE_DIR, script_rel)
    if os.path.exists(script_path):
        return send_file(script_path, as_attachment=True, download_name=f"Copione_{char_name}.docx")
    return jsonify({'status':'error','message':'File not found'}), 404

@app.route('/bacheca/character/<int:cid>/upload_image', methods=['POST'])
def api_bacheca_upload_image(cid):
    """Endpoint per aggiornare solo l'immagine di un personaggio"""
    if request is None: return jsonify({'status':'error'}), 500
    try:
        image_file = request.files.get('image_file')
        if not image_file:
            return jsonify({'status':'error','message':'Nessun file'}), 400
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT series_title, character_name FROM bacheca_characters WHERE id=?', (cid,))
        r = c.fetchone()
        if not r:
            conn.close()
            return jsonify({'status':'error','message':'Character non trovato'}), 404
        
        series, name = r
        img_rel = _save_uploaded_file(image_file, series, f"img_{secure_filename(name)}")
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        c.execute('UPDATE bacheca_characters SET image_path=?, last_modified=? WHERE id=?', (img_rel, now, cid))
        conn.commit()
        conn.close()
        
        return jsonify({'status':'ok', 'image_url': f"{SERVER_URL}/profile_image/{img_rel}", 'last_modified': now})
    except Exception as e:
        traceback.print_exc()
        return jsonify({'status':'error','message':str(e)}), 500

@app.route('/bacheca/character/<int:cid>/upload_mov', methods=['POST'])
def api_bacheca_upload_mov(cid):
    if request is None: return jsonify({'status':'error'}), 500
    try:
        mov_file = request.files.get('mov')
        uploader = request.form.get('uploader')
        if not mov_file:
            return jsonify({'status':'error','message':'Nessun file'}), 400
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT series_title, character_name FROM bacheca_characters WHERE id=?', (cid,))
        r = c.fetchone()
        if not r:
            conn.close()
            return jsonify({'status':'error','message':'Character non trovato'}), 404
        series, name = r
        mov_rel = _save_uploaded_file(mov_file, series, f"mov_{secure_filename(name)}")
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        c.execute('UPDATE bacheca_characters SET mov_path=?, last_modified=? WHERE id=?', (mov_rel, now, cid))
        conn.commit()
        conn.close()
        audit(uploader, 'bacheca_upload_mov', f"cid={cid}")
        return jsonify({'status':'ok', 'mov_url': f"{SERVER_URL}/profile_image/{mov_rel}", 'last_modified': now})
    except Exception as e:
        traceback.print_exc()
        return jsonify({'status':'error','message':str(e)}), 500

@app.route('/bacheca/character/<int:cid>/download_mov', methods=['GET'])
def api_bacheca_download_mov(cid):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT mov_path FROM bacheca_characters WHERE id=?', (cid,))
    r = c.fetchone()
    conn.close()
    if not r or not r[0]:
        return jsonify({'status':'error','message':'No mov'}), 404
    mov_rel = r[0]
    mov_path = os.path.join(BASE_DIR, mov_rel)
    if os.path.exists(mov_path):
        return send_file(mov_path, as_attachment=True, download_name=os.path.basename(mov_path))
    return jsonify({'status':'error','message':'File not found'}), 404

@app.route('/profile_image/<path:filename>')
def serve_asset(filename):
    full_path = os.path.join(BASE_DIR, filename)
    if os.path.exists(full_path):
        return send_file(full_path)
    return jsonify({'status':'error'}), 404

@app.route('/login', methods=['POST'])
def api_login():
    if request is None: return jsonify({'status':'error'}), 500
    data = request.get_json()
    identifier = data.get('code')
    password = data.get('password')
    if not identifier or not password:
        return jsonify({"status":"error", "message":"Inserisci credenziali"}), 400
    conn = get_db_connection()
    c = conn.cursor()
    query = "SELECT id, name, surname, email, role FROM users WHERE (code = ? OR email = ?) AND password = ?"
    c.execute(query, (identifier, identifier, password))
    user_data = c.fetchone()
    conn.close()
    if user_data:
        user_data = dict(user_data)
        return jsonify({"status": "ok", **user_data, "code": identifier})
    else:
        return jsonify({"status":"error", "message":"Credenziali non valide"}), 401

@app.route('/add_hours', methods=['POST'])
def api_add_hours():
    if request is None: return jsonify({'status':'error'}), 500
    data = request.get_json()
    user_id = data.get('user_id')
    hours = data.get('hours')
    reason = data.get('reason')
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("INSERT INTO work_logs (user_id, date, hours, reason) VALUES (?, ?, ?, ?)",
                  (user_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), hours, reason))
        conn.commit()
        conn.close()
        return jsonify({'status':'ok'})
    except Exception as e:
        return jsonify({'status':'error', 'message':str(e)}), 500

@app.route('/get_logs/<int:user_id>', methods=['GET'])
def api_get_logs(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM work_logs WHERE user_id=? ORDER BY date DESC", (user_id,))
    rows = c.fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/register', methods=['POST'])
def api_register():
    if request is None: return jsonify({'status':'error'}), 500
    data = request.get_json()
    name = data.get('name')
    surname = data.get('surname')
    email = data.get('email')
    password = data.get('password')
    if not all([name, surname, email, password]):
        return jsonify({'status':'error','message':'Dati incompleti'}), 400
    conn = get_db_connection()
    c = conn.cursor()
    try:
        code = f"USR{int(time.time())}"
        c.execute("INSERT INTO users (name, surname, email, password, code, role) VALUES (?,?,?,?,?,?)",
                  (name, surname, email, password, code, 'user'))
        conn.commit()
        conn.close()
        return jsonify({'status':'ok','code':code})
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'status':'error','message':'Email già esistente'}), 400

@app.route('/user_profile/<int:user_id>', methods=['GET', 'POST'])
def api_user_profile(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    if request.method == 'GET':
        c.execute("SELECT * FROM user_profiles WHERE user_id=?", (user_id,))
        row = c.fetchone()
        conn.close()
        if row:
            return jsonify(dict(row))
        return jsonify({})
    else:
        data = request.get_json()
        nickname = data.get('nickname')
        image_b64 = data.get('image_b64')
        c.execute("INSERT OR REPLACE INTO user_profiles (user_id, nickname, image_path) VALUES (?,?,?)",
                  (user_id, nickname, image_b64))
        conn.commit()
        conn.close()
        return jsonify({'status':'ok'})

@app.route('/request_removal', methods=['POST'])
def api_request_removal():
    if request is None: return jsonify({'status':'error'}), 500
    data = request.get_json()
    work_log_id = data.get('work_log_id')
    requester_id = data.get('requester_id')
    reason = data.get('reason')
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO removal_requests (work_log_id, requester_id, reason, request_date) VALUES (?,?,?,?)",
              (work_log_id, requester_id, reason, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()
    return jsonify({'status':'ok'})

@app.route('/admin/removal_requests', methods=['GET'])
def api_admin_removal_requests():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""SELECT r.*, w.date as work_date, w.hours 
                 FROM removal_requests r 
                 JOIN work_logs w ON r.work_log_id = w.id 
                 WHERE r.status='pending'""")
    rows = c.fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/admin/handle_removal', methods=['POST'])
def api_admin_handle_removal():
    if request is None: return jsonify({'status':'error'}), 500
    data = request.get_json()
    req_id = data.get('request_id')
    action = data.get('action')
    admin_id = data.get('admin_id')
    admin_reason = data.get('admin_reason')
    conn = get_db_connection()
    c = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute("UPDATE removal_requests SET status=?, admin_id=?, admin_reason=?, decision_date=? WHERE id=?",
              (action, admin_id, admin_reason, now, req_id))
    if action == 'accepted':
        c.execute("SELECT work_log_id FROM removal_requests WHERE id=?", (req_id,))
        wl_id = c.fetchone()[0]
        c.execute("DELETE FROM work_logs WHERE id=?", (wl_id,))
    conn.commit()
    conn.close()
    return jsonify({'status':'ok'})

@app.route('/admin/users_hours', methods=['GET'])
def api_admin_users_hours():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""SELECT u.id, u.name, u.surname, u.email, 
                 COALESCE(SUM(w.hours), 0) as total_hours
                 FROM users u
                 LEFT JOIN work_logs w ON u.id = w.user_id
                 GROUP BY u.id""")
    rows = c.fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

# ---------------- CLIENT SIDE ----------------
if PYQT_AVAILABLE:
    
    class BachecaWindow(QDialog):
        def __init__(self, server_url, user, parent=None):
            super().__init__(parent)
            self.server_url = server_url
            self.user = user
            self.setWindowTitle('Bacheca')
            self.resize(900,600)
            self.setStyleSheet(QSS)

            self.tabs = QTabWidget()
            self.tab_after = QWidget()
            self.tab_empire = QWidget()
            self.tabs.addTab(self.tab_after, 'After School')
            self.tabs.addTab(self.tab_empire, 'Empire Office')

            main_layout = QVBoxLayout()
            main_layout.addWidget(self.tabs)
            self.setLayout(main_layout)

            self.characters = { 'After School': [], 'Empire Office': [] }
            self.current_index = { 'After School': 0, 'Empire Office': 0 }
            self.last_update = None

            self._build_tab_ui(self.tab_after, 'After School')
            self._build_tab_ui(self.tab_empire, 'Empire Office')

            self.poll_timer = QtCore.QTimer(self)
            self.poll_timer.timeout.connect(self.check_updates)
            self.poll_timer.start(25000)

            self.load_characters()

        def _build_tab_ui(self, widget, series_title):
            layout = QHBoxLayout()
            left = QVBoxLayout()
            right = QVBoxLayout()

            self_img = QLabel()
            self_img.setFixedSize(320,320)
            self_img.setAlignment(QtCore.Qt.AlignCenter)
            self_img.setObjectName(f'img_label_{series_title}')
            name_lbl = QLabel('')
            name_lbl.setObjectName(f'name_{series_title}')
            name_lbl.setAlignment(QtCore.Qt.AlignCenter)
            name_lbl.setStyleSheet('font-size:20px; font-weight:bold;')

            left.addWidget(name_lbl)
            left.addWidget(self_img)

            btn_script = QPushButton('Apri/Scarica Copione')
            btn_script.clicked.connect(lambda _, s=series_title: self.download_script(s))
            
            expiry = QLabel('Scadenza: -')
            expiry.setObjectName(f'expiry_{series_title}')
            role = QLabel('Ruolo: -')
            role.setObjectName(f'role_{series_title}')

            btn_upload_mov = QPushButton('Carica .mov')
            btn_upload_mov.clicked.connect(lambda _, s=series_title: self.upload_mov(s))
            btn_download_mov = QPushButton('Scarica .mov')
            btn_download_mov.clicked.connect(lambda _, s=series_title: self.download_mov(s))

            nav = QHBoxLayout()
            btn_prev = QPushButton('\u25C0')
            btn_next = QPushButton('\u25B6')
            btn_prev.clicked.connect(lambda _, s=series_title: self.change_index(s, -1))
            btn_next.clicked.connect(lambda _, s=series_title: self.change_index(s, 1))
            nav.addWidget(btn_prev)
            nav.addWidget(btn_next)

            btn_refresh = QPushButton('Aggiorna')
            btn_refresh.clicked.connect(self.load_characters)

            right.addWidget(btn_script)
            right.addWidget(expiry)
            right.addWidget(role)
            right.addWidget(btn_upload_mov)
            right.addWidget(btn_download_mov)
            right.addLayout(nav)
            right.addWidget(btn_refresh)
            right.addStretch()

            layout.addLayout(left, 3)
            layout.addLayout(right, 2)
            widget.setLayout(layout)

        def load_characters(self):
            try:
                r = requests.get(f"{self.server_url}/bacheca/characters", timeout=8)
                if r.status_code == 200:
                    items = r.json()
                    groups = {}
                    for it in items:
                        groups.setdefault(it['series_title'], []).append(it)
                    self.characters['After School'] = groups.get('After School', [])
                    self.characters['Empire Office'] = groups.get('Empire Office', [])
                    
                    self.last_update = max([item.get('last_modified') for item in items if item.get('last_modified')] or [''], default=None)

                    self.refresh_current_view('After School')
                    self.refresh_current_view('Empire Office')
            except Exception as e:
                QMessageBox.warning(self, 'Errore', f'Errore caricamento: {e}')

        def check_updates(self):
            try:
                r = requests.get(f"{self.server_url}/bacheca/last_update", timeout=6)
                if r.status_code==200:
                    lu = r.json().get('last_update')
                    if lu and lu != self.last_update:
                        self.last_update = lu
                        self.load_characters()
            except Exception:
                pass

        def refresh_current_view(self, series):
            lst = self.characters.get(series, [])
            idx = self.current_index.get(series, 0)
            if not lst:
                self._set_tab_display(series, None)
                return
            idx = max(0, min(idx, len(lst)-1))
            self.current_index[series] = idx
            item = lst[idx]
            self._set_tab_display(series, item)

        def _set_tab_display(self, series, item):
            name_lbl = self.findChild(QLabel, f'name_{series}')
            expiry_lbl = self.findChild(QLabel, f'expiry_{series}')
            role_lbl = self.findChild(QLabel, f'role_{series}')
            img_label = self.findChild(QLabel, f'img_label_{series}')
            
            if not item:
                if name_lbl: name_lbl.setText('')
                if expiry_lbl: expiry_lbl.setText('Scadenza: -')
                if role_lbl: role_lbl.setText('Ruolo: -')
                if img_label: img_label.clear()
                return
            
            if name_lbl: name_lbl.setText(item['character_name'])
            if expiry_lbl: expiry_lbl.setText('Scadenza: ' + (item.get('expiry_date') or '-'))
            if role_lbl: role_lbl.setText('Ruolo: ' + (item.get('role') or '-'))
            
            if img_label and item.get('image_url'):
                try:
                    data = requests.get(item['image_url'], timeout=6).content
                    pix = QtGui.QPixmap()
                    pix.loadFromData(data)
                    pix = pix.scaled(img_label.width(), img_label.height(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                    img_label.setPixmap(pix)
                except Exception:
                    img_label.clear()
            else:
                if img_label: img_label.clear()

        def change_index(self, series, delta):
            if not self.characters.get(series): return
            self.current_index[series] = (self.current_index[series] + delta) % len(self.characters[series])
            self.refresh_current_view(series)

        def download_script(self, series):
            """Scarica il copione .docx del personaggio corrente"""
            idx = self.current_index.get(series,0)
            lst = self.characters.get(series, [])
            if not lst: return
            item = lst[idx]
            
            if not item.get('script_url'):
                QMessageBox.information(self, 'Info', 'Nessun copione disponibile per questo personaggio')
                return
            
            try:
                r = requests.get(f"{self.server_url}/bacheca/character/{item['id']}/download_script", timeout=30)
                if r.status_code == 200:
                    fn, _ = QFileDialog.getSaveFileName(self, 'Salva Copione', 
                                                       f"Copione_{item['character_name']}.docx", 
                                                       'Word Documents (*.docx)')
                    if fn:
                        with open(fn, 'wb') as f:
                            f.write(r.content)
                        QMessageBox.information(self, 'OK', 'Copione scaricato con successo')
                else:
                    QMessageBox.warning(self, 'Errore', 'Nessun copione disponibile')
            except Exception as e:
                QMessageBox.warning(self, 'Errore', f'Errore download: {e}')

        def open_script(self, series):
            """Metodo deprecato - ora si usa download_script"""
            self.download_script(series)

        def upload_mov(self, series):
            idx = self.current_index.get(series,0)
            lst = self.characters.get(series, [])
            if not lst: return
            item = lst[idx]
            path, _ = QFileDialog.getOpenFileName(self, 'Scegli .mov', '', 'Movies (*.mov *.mp4)')
            if not path: return
            
            files = {'mov': open(path, 'rb')}
            try:
                r = requests.post(f"{self.server_url}/bacheca/character/{item['id']}/upload_mov", 
                                files=files, data={'uploader': self.user.get('id')}, timeout=30)
                if r.status_code==200 and r.json().get('status')=='ok':
                    QMessageBox.information(self, 'OK', 'File caricato')
                    self.load_characters()
                else:
                    QMessageBox.warning(self, 'Errore', 'Upload fallito')
            except Exception as e:
                QMessageBox.warning(self, 'Errore', f'Errore rete: {e}')

        def download_mov(self, series):
            idx = self.current_index.get(series,0)
            lst = self.characters.get(series, [])
            if not lst: return
            item = lst[idx]
            if not item.get('mov_url'):
                QMessageBox.information(self, 'Info', 'Nessun mov disponibile')
                return
            try:
                r = requests.get(f"{self.server_url}/bacheca/character/{item['id']}/download_mov", timeout=30)
                if r.status_code==200:
                    fn, _ = QFileDialog.getSaveFileName(self, 'Salva .mov', item['character_name'] + '.mov', 'Movies (*.mov *.mp4)')
                    if fn:
                        with open(fn, 'wb') as f:
                            f.write(r.content)
                        QMessageBox.information(self, 'OK', 'File salvato')
                else:
                    QMessageBox.warning(self, 'Errore', 'Download fallito')
            except Exception as e:
                QMessageBox.warning(self, 'Errore', f'Errore rete: {e}')

    class SplashWidget(QWidget):
        def __init__(self):
            super().__init__()
            self.setWindowFlags(QtCore.Qt.SplashScreen | QtCore.Qt.FramelessWindowHint)
            self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
            self.opacity_effect = QtWidgets.QGraphicsOpacityEffect(self)
            self.setGraphicsEffect(self.opacity_effect)
            self.resize(400, 300)
            v = QVBoxLayout()
            v.setContentsMargins(40, 40, 40, 40)
            
            logo_lbl = QLabel()
            logo_lbl.setAlignment(QtCore.Qt.AlignCenter)
            logo_path = os.path.join(ASSETS_DIR, "logo.png")
            if os.path.exists(logo_path):
                pix = QtGui.QPixmap(logo_path).scaled(120, 120, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
            else:
                pix = QtGui.QPixmap(120, 120)
                pix.fill(QtGui.QColor("#4CAF50"))
            logo_lbl.setPixmap(pix)

            title = QLabel("BadgeEmpire")
            title.setAlignment(QtCore.Qt.AlignCenter)
            title.setStyleSheet("font-size:22px; font-weight:800; color:#333333; background:none;")

            subtitle = QLabel("Avvio in corso...")
            subtitle.setAlignment(QtCore.Qt.AlignCenter)
            subtitle.setStyleSheet("color:#333333; background:none;")

            v.addStretch()
            v.addWidget(logo_lbl)
            v.addWidget(title)
            v.addWidget(subtitle)
            v.addStretch()
            self.setLayout(v)

        def start(self, timeout=1200, finished_callback=None):
            self.show()
            self.anim_in = QtCore.QPropertyAnimation(self.opacity_effect, b"opacity")
            self.anim_in.setDuration(300)
            self.anim_in.setStartValue(0.0)
            self.anim_in.setEndValue(1.0)
            self.anim_in.start()
            QtCore.QTimer.singleShot(timeout, lambda: self.fade_out(finished_callback))

        def fade_out(self, finished_callback=None):
            self.anim = QtCore.QPropertyAnimation(self.opacity_effect, b"opacity")
            self.anim.setDuration(600)
            self.anim.setStartValue(1.0)
            self.anim.setEndValue(0.0)
            def on_end():
                self.close()
                if finished_callback:
                    finished_callback()
            self.anim.finished.connect(on_end)
            self.anim.start()

    class ProfileDialog(QDialog):
        def __init__(self, user_id, server_url, parent=None):
            super().__init__(parent)
            self.user_id = user_id
            self.server_url = server_url
            self.setWindowTitle("Personalizza profilo")
            self.resize(480,260)
            self.setStyleSheet(QSS)
            layout = QFormLayout()
            self.nickname = QLineEdit()
            self.img_label = QLabel("Nessuna immagine scelta")
            btn_img = QPushButton("Seleziona immagine")
            btn_img.setIcon(make_icon("user", size=18))
            btn_save = QPushButton("Salva")
            btn_img.clicked.connect(self.select_image)
            btn_save.clicked.connect(self.save)
            layout.addRow("Nickname", self.nickname)
            layout.addRow(self.img_label, btn_img)
            layout.addRow(btn_save)
            self.setLayout(layout)
            self.selected_b64 = None

        def select_image(self):
            path, _ = QFileDialog.getOpenFileName(self, "Scegli immagine", "", "Images (*.png *.jpg *.jpeg)")
            if path:
                try:
                    with open(path, "rb") as f:
                        self.selected_b64 = "data:image/png;base64," + base64.b64encode(f.read()).decode('utf-8')
                    self.img_label.setText(os.path.basename(path))
                except Exception as e:
                    QMessageBox.warning(self, "Errore File", f"Impossibile leggere: {e}")

        def save(self):
            data = {"nickname": self.nickname.text(), "image_b64": self.selected_b64}
            try:
                r = requests.post(f"{self.server_url}/user_profile/{self.user_id}", json=data, timeout=8)
                if r.status_code==200 and r.json().get("status")=="ok":
                    QMessageBox.information(self, "OK", "Profilo aggiornato")
                    self.accept()
                else:
                    QMessageBox.warning(self, "Errore", "Impossibile aggiornare")
            except Exception as e:
                QMessageBox.warning(self, "Errore", f"Errore rete: {e}")

    class RegisterDialog(QDialog):
        def __init__(self, server_url, parent=None):
            super().__init__(parent)
            self.server_url = server_url
            self.setWindowTitle("Registrazione")
            self.resize(420,360)
            self.setStyleSheet(QSS)
            layout = QFormLayout()
            self.name = QLineEdit()
            self.surname = QLineEdit()
            self.email = QLineEdit()
            self.pw = QLineEdit()
            self.pw2 = QLineEdit()
            self.pw.setEchoMode(QLineEdit.Password)
            self.pw2.setEchoMode(QLineEdit.Password)
            btn = QPushButton("Crea account")
            btn.setIcon(make_icon("plus", size=16))
            btn.clicked.connect(self.register)
            self.msg = QLabel("")
            layout.addRow("Nome", self.name)
            layout.addRow("Cognome", self.surname)
            layout.addRow("Email", self.email)
            layout.addRow("Password", self.pw)
            layout.addRow("Conferma Password", self.pw2)
            layout.addRow(btn)
            layout.addRow(self.msg)
            self.setLayout(layout)

        def register(self):
            if self.pw.text() != self.pw2.text():
                QMessageBox.warning(self, "Errore", "Le password non coincidono")
                return
            data = {"name": self.name.text(), "surname": self.surname.text(), 
                   "email": self.email.text(), "password": self.pw.text()}
            try:
                r = requests.post(f"{self.server_url}/register", json=data, timeout=10)
                if r.status_code==200:
                    resp = r.json()
                    if resp.get("status")=="ok":
                        QMessageBox.information(self, "Benvenuto", f"Registrato! Codice: {resp.get('code')}")
                        self.accept()
                    else:
                        QMessageBox.warning(self, "Errore", resp.get("message","Errore"))
                else:
                    QMessageBox.warning(self, "Errore", f"Registrazione fallita ({r.status_code})")
            except Exception as e:
                QMessageBox.warning(self, "Errore", f"Errore rete: {e}")

    class LoginWindow(QWidget):
        def __init__(self, server_url):
            super().__init__()
            self.server_url = server_url
            self.setWindowTitle("Timbracart - Login")
            self.resize(400, 500)
            self.setStyleSheet(QSS)

            layout = QVBoxLayout()
            layout.setAlignment(QtCore.Qt.AlignTop)
            layout.setContentsMargins(40,40,40,40)
            layout.setSpacing(20)

            logo_lbl = QLabel()
            logo_lbl.setAlignment(QtCore.Qt.AlignCenter)
            logo_path = os.path.join(ASSETS_DIR, "logo.png")
            if os.path.exists(logo_path):
                pix = QtGui.QPixmap(logo_path).scaled(150, 150, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
            else:
                pix = QtGui.QPixmap(150, 150)
                pix.fill(QtGui.QColor("#F5F5F0"))
            logo_lbl.setPixmap(pix)
            layout.addWidget(logo_lbl)

            self.code_input = QLineEdit()
            self.code_input.setPlaceholderText("Email o codice dipendente")
            self.pw_input = QLineEdit()
            self.pw_input.setPlaceholderText("Password")
            self.pw_input.setEchoMode(QLineEdit.Password)
            layout.addWidget(self.code_input)
            layout.addWidget(self.pw_input)

            btn_login = QPushButton("Accedi")
            btn_login.clicked.connect(self.login)
            btn_register = QPushButton("Registrati")
            btn_register.clicked.connect(self.register)
            layout.addWidget(btn_login)
            layout.addWidget(btn_register)
            self.setLayout(layout)
            QtCore.QTimer.singleShot(2000, self.check_updates)

        def check_updates(self):
            update_info = check_for_updates()
            if update_info:
                show_update_dialog(self, update_info)

        def login(self):
            code = self.code_input.text()
            pw = self.pw_input.text()
            if not code or not pw:
                QMessageBox.warning(self, "Errore", "Inserisci credenziali")
                return
            data = {"code": code, "password": pw}
            try:
                r = requests.post(f"{self.server_url}/login", json=data, timeout=8)
                if r.status_code==200 and r.json().get("status")=="ok":
                    user = r.json()
                    self.close()
                    self.main_win = MainWindow(user, self.server_url)
                    self.main_win.show()
                else:
                    QMessageBox.warning(self, "Errore", "Credenziali non valide")
            except Exception as e:
                QMessageBox.warning(self, "Errore", f"Errore di rete: {e}")

        def register(self):
            dlg = RegisterDialog(self.server_url, parent=self)
            dlg.exec_()

    class MainWindow(QMainWindow):
        def __init__(self, user, server_url):
            super().__init__()
            self.user = user
            self.server_url = server_url
            self.setWindowTitle(f"Timbracart - {self.user.get('name')} {self.user.get('surname')}")
            self.resize(1100,700)
            self.setStyleSheet(QSS)
            self.setWindowIcon(make_icon("clock", size=48))
            self._bacheca_win = None

            central = QWidget()
            v_main = QVBoxLayout()
            central.setLayout(v_main)
            self.setCentralWidget(central)

            top = QWidget()
            th = QHBoxLayout()
            th.setContentsMargins(8,8,8,8)
            self.lbl_welcome = QLabel(f"Benvenuto/a {self.user.get('name')}")
            self.lbl_welcome.setObjectName("welcome")
            self.lbl_welcome.setFixedHeight(56)
            th.addWidget(self.lbl_welcome)
            th.addStretch()
            self.profile_btn = QPushButton()
            self.profile_btn.setIcon(make_icon("user", size=28))
            self.profile_btn.setText(self.user.get('name'))
            self.profile_btn.clicked.connect(self.open_profile)
            th.addWidget(self.profile_btn)
            top.setLayout(th)
            v_main.addWidget(top)

            body = QHBoxLayout()
            self.tabs = QTabWidget()
            self.tabs.setTabPosition(QTabWidget.North)
            self.tab_home = QWidget()
            self.tab_analytics = QWidget()
            self.tabs.addTab(self.tab_home, "Home")
            self.tabs.addTab(self.tab_analytics, "Analitica")
            body.addWidget(self.tabs, 4)

            right = QWidget()
            rlayout = QVBoxLayout(right)
            self.lbl_total = QLabel("Totale ore mese: 0")
            self.lbl_total.setObjectName("totalHours")
            self.lbl_total.setAlignment(QtCore.Qt.AlignCenter)
            rlayout.addWidget(self.lbl_total)
            
            btn_bacheca = QPushButton('Bacheca')
            btn_bacheca.clicked.connect(lambda: self.open_bacheca())
            btn_bacheca.setFixedWidth(140)
            btn_refresh_bacheca = QPushButton('Aggiorna Bacheca')
            btn_refresh_bacheca.clicked.connect(lambda: self.bacheca_refresh())
            btn_refresh_bacheca.setFixedWidth(140)
            
            rlayout.addWidget(btn_bacheca)
            rlayout.addWidget(btn_refresh_bacheca)
            rlayout.addStretch()
            body.addWidget(right, 1)
            v_main.addLayout(body)
            
            self.build_home()
            self.build_analytics()

            if self.user.get('role') == 'admin':
                self.tab_admin = QWidget()
                self.tabs.addTab(self.tab_admin, "Admin")
                self.tabs_admin = QTabWidget()
                self.tab_admin.setLayout(QVBoxLayout())
                self.tab_admin.layout().addWidget(self.tabs_admin)
                
                self.tab_admin_users = QWidget()
                self.tab_admin_bacheca = QWidget()
                self.tabs_admin.addTab(self.tab_admin_users, "Utenti & Log")
                self.tabs_admin.addTab(self.tab_admin_bacheca, "Bacheca (Personaggi)")
                
                self.build_admin_users()
                self.build_admin_bacheca()
                
                self.poll = QtCore.QTimer(self)
                self.poll.timeout.connect(self.load_removal_requests)
                self.poll.start(20000)
                self.load_removal_requests()
                self.load_users_hours()

            self.load_profile()
            self.load_months()

        def open_bacheca(self):
            if self._bacheca_win is None:
                self._bacheca_win = BachecaWindow(self.server_url, self.user, parent=self)
            self._bacheca_win.show()
            self._bacheca_win.raise_()

        def bacheca_refresh(self):
            if self._bacheca_win:
                self._bacheca_win.load_characters()

        def open_profile(self):
            dlg = ProfileDialog(self.user['id'], self.server_url, parent=self)
            if dlg.exec_():
                self.load_profile()

        def load_profile(self):
            try:
                r = requests.get(f"{self.server_url}/user_profile/{self.user['id']}", timeout=6)
                if r.status_code==200:
                    p = r.json()
                    nickname = p.get("nickname") or ""
                    name_display = nickname or self.user.get('name')
                    self.lbl_welcome.setText(f"Benvenuto/a {name_display}")
                    self.profile_btn.setText(name_display)
            except Exception:
                pass

        def build_home(self):
            layout = QVBoxLayout()
            card = QWidget()
            card_layout = QFormLayout()
            card.setLayout(card_layout)

            hlayout = QHBoxLayout()
            self.hours = QLineEdit()
            self.hours.setPlaceholderText("Es. 1.5")
            self.reason = QLineEdit()
            self.reason.setPlaceholderText("Motivo inserimento ore")

            btn_add = QPushButton("+")
            btn_add.setObjectName("plusButton")
            btn_add.setToolTip("Aggiungi ore")
            btn_add.clicked.connect(self.add_hours)

            hlayout.addWidget(self.hours)
            hlayout.addWidget(self.reason)
            hlayout.addWidget(btn_add)
            card_layout.addRow("Inserisci ore:", hlayout)
            layout.addWidget(card)

            self.recent_logs = QtWidgets.QListWidget()
            layout.addWidget(QLabel("Recenti:"))
            layout.addWidget(self.recent_logs)
            self.tab_home.setLayout(layout)

        def add_hours(self):
            try:
                h = float(self.hours.text())
            except Exception:
                QMessageBox.warning(self, "Errore", "Inserisci un valore numerico valido")
                return
            data = {"user_id": self.user['id'], "hours": h, "reason": self.reason.text()}
            try:
                r = requests.post(f"{self.server_url}/add_hours", json=data, timeout=8)
                if r.status_code == 200 and r.json().get("status") == "ok":
                    QMessageBox.information(self, "OK", "Ore aggiunte correttamente")
                    self.hours.clear()
                    self.reason.clear()
                    self.load_months()
                    self.load_recent_logs()
                else:
                    QMessageBox.warning(self, "Errore", "Errore inserimento")
            except Exception as e:
                QMessageBox.warning(self, "Errore", f"Errore rete: {e}")

        def load_recent_logs(self):
            try:
                r = requests.get(f"{self.server_url}/get_logs/{self.user['id']}", timeout=8)
                if r.status_code == 200:
                    logs = r.json()
                    self.recent_logs.clear()
                    for log in logs[:10]:
                        item_text = f"{log['date']}: {log['hours']}h - {log['reason']}"
                        self.recent_logs.addItem(item_text)
            except Exception as e:
                print(f"Errore caricamento log recenti: {e}")

        def build_analytics(self):
            layout = QVBoxLayout()
            month_layout = QHBoxLayout()
            month_layout.addWidget(QLabel("Seleziona mese:"))
            self.month_combo = QComboBox()
            self.month_combo.currentIndexChanged.connect(self.on_month_selected)
            month_layout.addWidget(self.month_combo)
            month_layout.addStretch()
            layout.addLayout(month_layout)
            
            self.month_table = QTableWidget(0, 5)
            self.month_table.setHorizontalHeaderLabels(["ID", "Data", "Ore", "Motivo", "Azioni"])
            layout.addWidget(QLabel("Log del mese:"))
            layout.addWidget(self.month_table)
            self.tab_analytics.setLayout(layout)

        def load_months(self):
            try:
                r = requests.get(f"{self.server_url}/get_logs/{self.user['id']}", timeout=8)
                if r.status_code == 200:
                    logs = r.json()
                    months = set()
                    for log in logs:
                        try:
                            dt = datetime.strptime(log['date'], '%Y-%m-%d %H:%M:%S')
                            months.add(dt.strftime('%Y-%m'))
                        except Exception:
                            pass
                    
                    self.month_combo.clear()
                    for month in sorted(months, reverse=True):
                        self.month_combo.addItem(month)
                    
                    current_month = datetime.now().strftime('%Y-%m')
                    total = sum(log['hours'] for log in logs if log['date'].startswith(current_month))
                    self.lbl_total.setText(f"Totale ore mese: {total:.1f}")
                    self.load_recent_logs()
            except Exception as e:
                print(f"Errore caricamento mesi: {e}")

        def on_month_selected(self):
            selected_month = self.month_combo.currentText()
            if not selected_month:
                return
            try:
                r = requests.get(f"{self.server_url}/get_logs/{self.user['id']}", timeout=8)
                if r.status_code == 200:
                    logs = r.json()
                    month_logs = [log for log in logs if log['date'].startswith(selected_month)]
                    
                    self.month_table.setRowCount(0)
                    for log in month_logs:
                        row = self.month_table.rowCount()
                        self.month_table.insertRow(row)
                        self.month_table.setItem(row, 0, QTableWidgetItem(str(log['id'])))
                        self.month_table.setItem(row, 1, QTableWidgetItem(log['date']))
                        self.month_table.setItem(row, 2, QTableWidgetItem(str(log['hours'])))
                        self.month_table.setItem(row, 3, QTableWidgetItem(log['reason']))
                        
                        btn_remove = QPushButton("Richiedi Rimozione")
                        btn_remove.clicked.connect(partial(self.request_removal, log['id']))
                        self.month_table.setCellWidget(row, 4, btn_remove)
            except Exception as e:
                QMessageBox.warning(self, "Errore", f"Errore caricamento log: {e}")

        def request_removal(self, log_id):
            reason, ok = QtWidgets.QInputDialog.getText(self, "Richiesta Rimozione", "Inserisci motivo:")
            if ok and reason:
                data = {"work_log_id": log_id, "requester_id": self.user['id'], "reason": reason}
                try:
                    r = requests.post(f"{self.server_url}/request_removal", json=data, timeout=8)
                    if r.status_code == 200 and r.json().get("status") == "ok":
                        QMessageBox.information(self, "OK", "Richiesta inviata")
                        self.on_month_selected()
                    else:
                        QMessageBox.warning(self, "Errore", "Errore invio richiesta")
                except Exception as e:
                    QMessageBox.warning(self, "Errore", f"Errore rete: {e}")

        def build_admin_users(self):
            layout = QVBoxLayout()
            htop = QHBoxLayout()
            self.admin_refresh_btn = QPushButton('Aggiorna Utenti')
            self.admin_refresh_btn.clicked.connect(self.load_users_hours)
            htop.addWidget(self.admin_refresh_btn)
            htop.addStretch()
            layout.addLayout(htop)

            self.admin_users_table = QTableWidget(0,6)
            self.admin_users_table.setHorizontalHeaderLabels(["ID","Nome","Cognome","Email","Ore totali","Dettaglio"])
            layout.addWidget(QLabel("Utenti e ore totali:"))
            layout.addWidget(self.admin_users_table)

            self.removal_table = QTableWidget(0,6)
            self.removal_table.setHorizontalHeaderLabels(["ReqID","Utente","Data","Ore","Motivo","Azioni"])
            layout.addWidget(QLabel("Richieste di rimozione"))
            layout.addWidget(self.removal_table)
            self.tab_admin_users.setLayout(layout)

        def load_users_hours(self):
            try:
                r = requests.get(f"{self.server_url}/admin/users_hours", timeout=8)
                if r.status_code == 200:
                    users = r.json()
                    self.admin_users_table.setRowCount(0)
                    for u in users:
                        row = self.admin_users_table.rowCount()
                        self.admin_users_table.insertRow(row)
                        self.admin_users_table.setItem(row, 0, QTableWidgetItem(str(u['id'])))
                        self.admin_users_table.setItem(row, 1, QTableWidgetItem(u.get('name', '')))
                        self.admin_users_table.setItem(row, 2, QTableWidgetItem(u.get('surname', '')))
                        self.admin_users_table.setItem(row, 3, QTableWidgetItem(u.get('email', '')))
                        self.admin_users_table.setItem(row, 4, QTableWidgetItem(str(u.get('total_hours', 0))))
                        
                        btn_detail = QPushButton("Vedi Dettaglio")
                        btn_detail.clicked.connect(partial(self.show_user_logs, u['id']))
                        self.admin_users_table.setCellWidget(row, 5, btn_detail)
            except Exception as e:
                print(f"Errore caricamento utenti: {e}")

        def show_user_logs(self, user_id):
            try:
                r = requests.get(f"{self.server_url}/get_logs/{user_id}", timeout=8)
                if r.status_code == 200:
                    logs = r.json()
                    dlg = QDialog(self)
                    dlg.setWindowTitle(f"Log Utente ID: {user_id}")
                    dlg.resize(700, 400)
                    layout = QVBoxLayout()
                    
                    table = QTableWidget(0, 4)
                    table.setHorizontalHeaderLabels(["ID", "Data", "Ore", "Motivo"])
                    for log in logs:
                        row = table.rowCount()
                        table.insertRow(row)
                        table.setItem(row, 0, QTableWidgetItem(str(log['id'])))
                        table.setItem(row, 1, QTableWidgetItem(log['date']))
                        table.setItem(row, 2, QTableWidgetItem(str(log['hours'])))
                        table.setItem(row, 3, QTableWidgetItem(log['reason']))
                    
                    layout.addWidget(table)
                    dlg.setLayout(layout)
                    dlg.exec_()
            except Exception as e:
                QMessageBox.warning(self, "Errore", f"Errore caricamento log: {e}")

        def load_removal_requests(self):
            try:
                r = requests.get(f"{self.server_url}/admin/removal_requests", timeout=8)
                if r.status_code == 200:
                    requests_list = r.json()
                    self.removal_table.setRowCount(0)
                    for req in requests_list:
                        if req.get('status') != 'pending':
                            continue
                        row = self.removal_table.rowCount()
                        self.removal_table.insertRow(row)
                        self.removal_table.setItem(row, 0, QTableWidgetItem(str(req['id'])))
                        self.removal_table.setItem(row, 1, QTableWidgetItem(f"User {req['requester_id']}"))
                        self.removal_table.setItem(row, 2, QTableWidgetItem(req.get('work_date', '')))
                        self.removal_table.setItem(row, 3, QTableWidgetItem(str(req.get('hours', ''))))
                        self.removal_table.setItem(row, 4, QTableWidgetItem(req.get('reason', '')))
                        
                        btn_layout = QHBoxLayout()
                        btn_accept = QPushButton("Accetta")
                        btn_reject = QPushButton("Rifiuta")
                        btn_accept.clicked.connect(partial(self.handle_request, req['id'], 'accepted'))
                        btn_reject.clicked.connect(partial(self.handle_request, req['id'], 'rejected'))
                        btn_layout.addWidget(btn_accept)
                        btn_layout.addWidget(btn_reject)
                        
                        widget = QWidget()
                        widget.setLayout(btn_layout)
                        self.removal_table.setCellWidget(row, 5, widget)
            except Exception as e:
                print(f"Errore caricamento richieste: {e}")

        def handle_request(self, req_id, action):
            reason, ok = QtWidgets.QInputDialog.getText(self, "Motivo Decisione", f"Inserisci motivo per {action}:")
            if ok:
                data = {"request_id": req_id, "action": action, "admin_id": self.user['id'], "admin_reason": reason}
                try:
                    r = requests.post(f"{self.server_url}/admin/handle_removal", json=data, timeout=8)
                    if r.status_code == 200 and r.json().get("status") == "ok":
                        QMessageBox.information(self, "OK", f"Richiesta {action}")
                        self.load_removal_requests()
                        self.load_users_hours()
                    else:
                        QMessageBox.warning(self, "Errore", "Errore elaborazione richiesta")
                except Exception as e:
                    QMessageBox.warning(self, "Errore", f"Errore rete: {e}")

        def build_admin_bacheca(self):
            layout = QVBoxLayout()
            
            # Sezione 1: Aggiungi Nuovo Personaggio
            group_add = QGroupBox("Aggiungi Nuovo Personaggio")
            form_add = QFormLayout()
            
            self.char_series = QComboBox()
            self.char_series.addItems(['After School', 'Empire Office'])
            self.char_name = QLineEdit()
            self.char_role = QLineEdit()
            self.char_expiry = QLineEdit(datetime.now().strftime('%Y-%m-%d'))
            self.char_script_path = QLineEdit()
            self.char_script_path.setReadOnly(True)
            self.char_script_path.setPlaceholderText("Carica un file .docx del copione...")
            self.char_script_btn = QPushButton("Scegli Copione (.docx)")
            self.char_script_btn.clicked.connect(self.select_script_file)
            
            self.char_img_path = QLineEdit()
            self.char_img_path.setReadOnly(True)
            self.char_img_btn = QPushButton("Scegli Immagine")
            self.char_img_btn.clicked.connect(self.select_character_image)
            
            form_add.addRow("Serie:", self.char_series)
            form_add.addRow("Nome Personaggio:", self.char_name)
            form_add.addRow("Ruolo (Doppiatore):", self.char_role)
            form_add.addRow("Scadenza (YYYY-MM-DD):", self.char_expiry)
            
            h_img = QHBoxLayout()
            h_img.addWidget(self.char_img_path)
            h_img.addWidget(self.char_img_btn)
            form_add.addRow("Immagine:", h_img)
            
            h_script = QHBoxLayout()
            h_script.addWidget(self.char_script_path)
            h_script.addWidget(self.char_script_btn)
            form_add.addRow("Copione (.docx):", h_script)
            
            self.btn_add_char = QPushButton("Crea Personaggio")
            self.btn_add_char.clicked.connect(self.add_character)
            form_add.addRow(self.btn_add_char)
            
            group_add.setLayout(form_add)
            layout.addWidget(group_add)
            
            # Sezione 2: Gestisci Personaggi Esistenti
            group_manage = QGroupBox("Gestisci Personaggi Esistenti")
            manage_layout = QVBoxLayout()
            
            h_refresh = QHBoxLayout()
            btn_refresh_chars = QPushButton("Aggiorna Lista")
            btn_refresh_chars.clicked.connect(self.load_admin_characters)
            h_refresh.addWidget(btn_refresh_chars)
            h_refresh.addStretch()
            manage_layout.addLayout(h_refresh)
            
            self.admin_chars_table = QTableWidget(0, 6)
            self.admin_chars_table.setHorizontalHeaderLabels(["ID", "Serie", "Nome", "Ruolo", "Scadenza", "Azioni"])
            manage_layout.addWidget(self.admin_chars_table)
            
            group_manage.setLayout(manage_layout)
            layout.addWidget(group_manage)
            
            self.tab_admin_bacheca.setLayout(layout)
            
            # Carica i personaggi esistenti
            self.load_admin_characters()
            
        def select_script_file(self):
            """Seleziona file .docx del copione"""
            path, _ = QFileDialog.getOpenFileName(self, "Scegli Copione", "", "Word Documents (*.docx)")
            if path:
                self.char_script_path.setText(path)
            
        def load_admin_characters(self):
            """Carica tutti i personaggi nella tabella admin"""
            try:
                r = requests.get(f"{self.server_url}/bacheca/characters", timeout=8)
                if r.status_code == 200:
                    chars = r.json()
                    self.admin_chars_table.setRowCount(0)
                    
                    for char in chars:
                        row = self.admin_chars_table.rowCount()
                        self.admin_chars_table.insertRow(row)
                        self.admin_chars_table.setItem(row, 0, QTableWidgetItem(str(char['id'])))
                        self.admin_chars_table.setItem(row, 1, QTableWidgetItem(char['series_title']))
                        self.admin_chars_table.setItem(row, 2, QTableWidgetItem(char['character_name']))
                        self.admin_chars_table.setItem(row, 3, QTableWidgetItem(char.get('role', '')))
                        self.admin_chars_table.setItem(row, 4, QTableWidgetItem(char.get('expiry_date', '')))
                        
                        # Bottoni azioni
                        btn_widget = QWidget()
                        btn_layout = QHBoxLayout()
                        btn_layout.setContentsMargins(2, 2, 2, 2)
                        
                        btn_edit = QPushButton("Modifica")
                        btn_edit.clicked.connect(partial(self.edit_character, char))
                        btn_layout.addWidget(btn_edit)
                        
                        btn_delete = QPushButton("Elimina")
                        btn_delete.setStyleSheet("background-color: #ff4444; color: white;")
                        btn_delete.clicked.connect(partial(self.delete_character, char))
                        btn_layout.addWidget(btn_delete)
                        
                        btn_widget.setLayout(btn_layout)
                        self.admin_chars_table.setCellWidget(row, 5, btn_widget)
                        
            except Exception as e:
                QMessageBox.warning(self, "Errore", f"Errore caricamento personaggi: {e}")
        
        def delete_character(self, char):
            """Elimina un personaggio dopo conferma"""
            reply = QMessageBox.question(self, 'Conferma Eliminazione',
                                        f"Sei sicuro di voler eliminare il personaggio '{char['character_name']}'?\n\n"
                                        f"Questa azione eliminerà anche tutti i file associati (immagine, copione, video).",
                                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                try:
                    print(f"[DEBUG] Tentativo eliminazione personaggio ID: {char['id']}")
                    # Usa POST invece di DELETE per evitare problemi con alcuni server
                    r = requests.post(f"{self.server_url}/bacheca/character/{char['id']}/delete", timeout=10)
                    print(f"[DEBUG] Status code: {r.status_code}")
                    print(f"[DEBUG] Response: {r.text}")
                    
                    if r.status_code == 200:
                        response_data = r.json()
                        if response_data.get('status') == 'ok':
                            QMessageBox.information(self, "OK", "Personaggio eliminato con successo")
                            self.load_admin_characters()
                            if self._bacheca_win:
                                self._bacheca_win.load_characters()
                        else:
                            QMessageBox.warning(self, "Errore", f"Errore server: {response_data.get('message', 'Sconosciuto')}")
                    else:
                        QMessageBox.warning(self, "Errore", f"Errore HTTP {r.status_code}: {r.text}")
                except Exception as e:
                    print(f"[DEBUG] Eccezione: {e}")
                    import traceback
                    traceback.print_exc()
                    QMessageBox.warning(self, "Errore", f"Errore eliminazione: {e}")
        
        def edit_character(self, char):
            """Apre dialog per modificare personaggio esistente"""
            dlg = QDialog(self)
            dlg.setWindowTitle(f"Modifica Personaggio - {char['character_name']}")
            dlg.resize(700, 600)
            dlg.setStyleSheet(QSS)
            
            layout = QVBoxLayout()
            form = QFormLayout()
            
            # Campi modificabili
            edit_series = QComboBox()
            edit_series.addItems(['After School', 'Empire Office'])
            edit_series.setCurrentText(char['series_title'])
            
            edit_name = QLineEdit(char['character_name'])
            edit_role = QLineEdit(char.get('role', ''))
            edit_expiry = QLineEdit(char.get('expiry_date', ''))
            
            # Copione attuale
            current_script_label = QLabel()
            if char.get('script_url'):
                current_script_label.setText("✓ Copione presente")
                current_script_label.setStyleSheet("color: green; font-weight: bold;")
            else:
                current_script_label.setText("Nessun copione")
                current_script_label.setStyleSheet("color: red;")
            
            # Nuovo copione
            new_script_path = QLineEdit()
            new_script_path.setReadOnly(True)
            new_script_path.setPlaceholderText("Lascia vuoto per mantenere il copione attuale")
            btn_new_script = QPushButton("Cambia Copione (.docx)")
            
            def select_new_script():
                path, _ = QFileDialog.getOpenFileName(dlg, "Scegli Nuovo Copione", "", "Word Documents (*.docx)")
                if path:
                    new_script_path.setText(path)
            
            btn_new_script.clicked.connect(select_new_script)
            
            # Immagine attuale
            current_img_label = QLabel()
            if char.get('image_url'):
                try:
                    img_data = requests.get(char['image_url'], timeout=6).content
                    pix = QtGui.QPixmap()
                    pix.loadFromData(img_data)
                    pix = pix.scaled(150, 150, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                    current_img_label.setPixmap(pix)
                except:
                    current_img_label.setText("Immagine non disponibile")
            else:
                current_img_label.setText("Nessuna immagine")
            
            # Nuova immagine
            new_img_path = QLineEdit()
            new_img_path.setReadOnly(True)
            new_img_path.setPlaceholderText("Lascia vuoto per mantenere l'immagine attuale")
            btn_new_img = QPushButton("Cambia Immagine")
            
            def select_new_image():
                path, _ = QFileDialog.getOpenFileName(dlg, "Scegli Nuova Immagine", "", "Images (*.png *.jpg *.jpeg)")
                if path:
                    new_img_path.setText(path)
            
            btn_new_img.clicked.connect(select_new_image)
            
            form.addRow("Serie:", edit_series)
            form.addRow("Nome Personaggio:", edit_name)
            form.addRow("Ruolo (Doppiatore):", edit_role)
            form.addRow("Scadenza:", edit_expiry)
            
            form.addRow("Copione Attuale:", current_script_label)
            h_script = QHBoxLayout()
            h_script.addWidget(new_script_path)
            h_script.addWidget(btn_new_script)
            form.addRow("Nuovo Copione:", h_script)
            
            form.addRow("Immagine Attuale:", current_img_label)
            
            h_img = QHBoxLayout()
            h_img.addWidget(new_img_path)
            h_img.addWidget(btn_new_img)
            form.addRow("Nuova Immagine:", h_img)
            
            layout.addLayout(form)
            
            # Bottoni salva/annulla
            btn_layout = QHBoxLayout()
            btn_save = QPushButton("Salva Modifiche")
            btn_cancel = QPushButton("Annulla")
            btn_layout.addStretch()
            btn_layout.addWidget(btn_cancel)
            btn_layout.addWidget(btn_save)
            
            layout.addLayout(btn_layout)
            dlg.setLayout(layout)
            
            def save_changes():
                # Prepara i dati da aggiornare
                update_data = {
                    'series_title': edit_series.currentText(),
                    'character_name': edit_name.text(),
                    'role': edit_role.text(),
                    'expiry_date': edit_expiry.text()
                }
                
                # Se c'è un nuovo copione, caricalo
                new_script = new_script_path.text()
                if new_script and os.path.exists(new_script):
                    try:
                        files = {'script': open(new_script, 'rb')}
                        r = requests.post(f"{self.server_url}/bacheca/character/{char['id']}/upload_script",
                                        files=files, timeout=15)
                        files['script'].close()
                        if r.status_code != 200:
                            QMessageBox.warning(dlg, "Attenzione", "Errore caricamento copione")
                    except Exception as e:
                        QMessageBox.warning(dlg, "Errore", f"Errore caricamento copione: {e}")
                
                # Se c'è una nuova immagine, caricala
                new_img = new_img_path.text()
                if new_img and os.path.exists(new_img):
                    try:
                        files = {'image_file': open(new_img, 'rb')}
                        r = requests.post(f"{self.server_url}/bacheca/character/{char['id']}/upload_image",
                                        files=files, timeout=15)
                        files['image_file'].close()
                        if r.status_code != 200:
                            QMessageBox.warning(dlg, "Attenzione", "Errore caricamento immagine")
                    except Exception as e:
                        QMessageBox.warning(dlg, "Errore", f"Errore caricamento immagine: {e}")
                
                # Aggiorna i dati testuali
                try:
                    r = requests.put(f"{self.server_url}/bacheca/character/{char['id']}", 
                                   json=update_data, timeout=8)
                    if r.status_code == 200 and r.json().get('status') == 'ok':
                        QMessageBox.information(dlg, "OK", "Personaggio aggiornato con successo")
                        dlg.accept()
                        self.load_admin_characters()
                        if self._bacheca_win:
                            self._bacheca_win.load_characters()
                    else:
                        QMessageBox.warning(dlg, "Errore", "Impossibile aggiornare il personaggio")
                except Exception as e:
                    QMessageBox.warning(dlg, "Errore", f"Errore aggiornamento: {e}")
            
            btn_save.clicked.connect(save_changes)
            btn_cancel.clicked.connect(dlg.reject)
            
            dlg.exec_()
            
        def select_character_image(self):
            path, _ = QFileDialog.getOpenFileName(self, "Scegli Immagine Personaggio", "", "Images (*.png *.jpg *.jpeg)")
            if path:
                self.char_img_path.setText(path)
                
        def add_character(self):
            series = self.char_series.currentText()
            name = self.char_name.text()
            role = self.char_role.text()
            expiry = self.char_expiry.text()
            script_path = self.char_script_path.text()
            img_path = self.char_img_path.text()

            if not name or not role:
                QMessageBox.warning(self, "Errore", "Nome e Ruolo sono obbligatori")
                return

            self.btn_add_char.setEnabled(False)
            
            data = {
                'series_title': series,
                'character_name': name,
                'role': role,
                'expiry_date': expiry,
                'created_by': self.user.get('id')
            }
            
            files = {}
            if os.path.exists(img_path):
                try:
                    files['image_file'] = open(img_path, 'rb')
                except Exception as e:
                    QMessageBox.critical(self, "Errore File", f"Impossibile aprire l'immagine: {e}")
                    self.btn_add_char.setEnabled(True)
                    return

            try:
                # Crea il personaggio
                r = requests.post(f"{self.server_url}/bacheca/character", data=data, files=files, timeout=15)
                
                if r.status_code == 200 and r.json().get('status') == 'ok':
                    char_id = None
                    
                    # Se c'è un copione, caricalo separatamente
                    if script_path and os.path.exists(script_path):
                        # Recupera l'ID del personaggio appena creato
                        chars_response = requests.get(f"{self.server_url}/bacheca/characters", timeout=8)
                        if chars_response.status_code == 200:
                            chars = chars_response.json()
                            # Trova il personaggio con questo nome
                            for ch in chars:
                                if ch['character_name'] == name and ch['series_title'] == series:
                                    char_id = ch['id']
                                    break
                        
                        if char_id:
                            try:
                                script_files = {'script': open(script_path, 'rb')}
                                script_r = requests.post(f"{self.server_url}/bacheca/character/{char_id}/upload_script",
                                                        files=script_files, timeout=15)
                                script_files['script'].close()
                                if script_r.status_code != 200:
                                    QMessageBox.warning(self, "Attenzione", "Personaggio creato ma errore nel caricamento del copione")
                            except Exception as e:
                                QMessageBox.warning(self, "Attenzione", f"Personaggio creato ma errore copione: {e}")
                    
                    QMessageBox.information(self, "OK", f"Personaggio '{name}' aggiunto con successo")
                    self.char_name.clear()
                    self.char_role.clear()
                    self.char_script_path.clear()
                    self.char_img_path.clear()
                    if self._bacheca_win:
                        self._bacheca_win.load_characters()
                    self.load_admin_characters()
                else:
                    QMessageBox.warning(self, "Errore", r.json().get('message', 'Errore nella creazione'))
            except Exception as e:
                QMessageBox.warning(self, "Errore", f"Errore di rete: {e}")
            finally:
                for f in files.values():
                    f.close()
                self.btn_add_char.setEnabled(True)

# ---------------- MAIN ----------------
def run_server():
    if not FLASK_AVAILABLE:
        print("Impossibile avviare il server: Flask non installato")
        return
    try:
        init_db()
        print(f"[server] Avvio Flask su http://{SERVER_HOST}:{SERVER_PORT}")
        app.run(host=SERVER_HOST, port=SERVER_PORT, debug=False)
    except Exception as e:
        print(f"ERRORE AVVIO SERVER: {e}")

def run_client():
    if not PYQT_AVAILABLE:
        print("Impossibile avviare il client: PyQt5 non installato")
        return
    qt_app = QtWidgets.QApplication(sys.argv)
    qt_app.setStyleSheet(QSS)
    splash = SplashWidget()
    def after():
        global login_window
        login_window = LoginWindow(SERVER_URL)
        login_window.show()
    splash.start(timeout=1200, finished_callback=after)
    sys.exit(qt_app.exec_())

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", action="store_true", help="Avvia server Flask")
    parser.add_argument("--url", type=str, help="Server URL override")
    args = parser.parse_args()

    if args.url:
        SERVER_URL = args.url if args.url.startswith("http") else f"http://{args.url}"

    if args.server:
        run_server()
    else:
        run_client()