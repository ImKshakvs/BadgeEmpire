#!/usr/bin/env python3
# add_admin.py
# Aggiunge un nuovo admin al database esistente SENZA cancellare nulla

import os
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "timbracart.db")

def add_admin():
    print("=" * 50)
    print("    AGGIUNGI NUOVO ADMIN A TIMBRACART")
    print("=" * 50)
    print()
    
    # Chiedi i dati
    name = input("Nome: ").strip()
    surname = input("Cognome: ").strip()
    email = input("Email: ").strip()
    password = input("Password: ").strip()
    code = input("Codice Admin (es. ADMIN002): ").strip()
    
    # Validazione base
    if not all([name, surname, email, password, code]):
        print("\n❌ ERRORE: Tutti i campi sono obbligatori!")
        return
    
    # Connessione al database
    if not os.path.exists(DB_PATH):
        print(f"\n❌ ERRORE: Database non trovato in {DB_PATH}")
        print("Esegui prima il server per creare il database.")
        return
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    try:
        # Verifica se il codice esiste già
        c.execute('SELECT id, name, surname FROM users WHERE code = ?', (code,))
        existing = c.fetchone()
        if existing:
            print(f'\n❌ ERRORE: Il codice {code} è già usato da {existing[1]} {existing[2]} (ID: {existing[0]})')
            conn.close()
            return
        
        # Verifica se l'email esiste già
        c.execute('SELECT id, name, surname FROM users WHERE email = ?', (email,))
        existing = c.fetchone()
        if existing:
            print(f'\n❌ ERRORE: L\'email {email} è già usata da {existing[1]} {existing[2]} (ID: {existing[0]})')
            conn.close()
            return
        
        # Inserisci il nuovo admin (password in chiaro per compatibilità con il tuo sistema)
        c.execute('''INSERT INTO users (name, surname, email, password, code, role) 
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (name, surname, email, password, code, 'admin'))
        
        user_id = c.lastrowid
        conn.commit()
        
        print("\n" + "=" * 50)
        print("✅ ADMIN CREATO CON SUCCESSO!")
        print("=" * 50)
        print(f"ID:       {user_id}")
        print(f"Nome:     {name} {surname}")
        print(f"Email:    {email}")
        print(f"Codice:   {code}")
        print(f"Password: {password}")
        print(f"Ruolo:    admin")
        print("=" * 50)
        print("\n⚠️  Conserva queste credenziali in modo sicuro!")
        print(f"Per fare login usa: Codice '{code}' o Email '{email}' con password '{password}'")
        
    except sqlite3.IntegrityError as e:
        print(f'\n❌ ERRORE Database: {e}')
    except Exception as e:
        print(f'\n❌ ERRORE: {e}')
    finally:
        conn.close()

def list_admins():
    """Mostra tutti gli admin esistenti"""
    if not os.path.exists(DB_PATH):
        print(f"\n❌ Database non trovato in {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    try:
        c.execute('SELECT id, name, surname, email, code FROM users WHERE role = "admin"')
        admins = c.fetchall()
        
        print("\n" + "=" * 70)
        print("    ADMIN ESISTENTI")
        print("=" * 70)
        
        if not admins:
            print("Nessun admin trovato nel database.")
        else:
            print(f"{'ID':<5} {'Nome':<15} {'Cognome':<15} {'Email':<25} {'Codice':<10}")
            print("-" * 70)
            for admin in admins:
                print(f"{admin[0]:<5} {admin[1]:<15} {admin[2]:<15} {admin[3]:<25} {admin[4]:<10}")
        
        print("=" * 70)
        
    except Exception as e:
        print(f'\n❌ ERRORE: {e}')
    finally:
        conn.close()

def main():
    print("\n")
    print("1. Aggiungi nuovo admin")
    print("2. Visualizza admin esistenti")
    print("3. Esci")
    print()
    
    choice = input("Scegli un'opzione (1-3): ").strip()
    
    if choice == "1":
        add_admin()
    elif choice == "2":
        list_admins()
    elif choice == "3":
        print("Uscita.")
    else:
        print("Opzione non valida.")

if __name__ == '__main__':
    main()