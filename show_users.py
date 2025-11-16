import sqlite3
import os

DB_PATH = "timbracart.db"

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

print("\n" + "="*80)
print("CREDENZIALI UTENTI TIMBRACART".center(80))
print("="*80 + "\n")

c.execute("SELECT id, name, surname, email, password, role, code FROM users ORDER BY role DESC, name")

for user in c.fetchall():
    uid, name, surname, email, password, role, code = user
    print(f"{'ID:':<15} {uid}")
    print(f"{'Nome:':<15} {name} {surname}")
    print(f"{'Email:':<15} {email}")
    print(f"{'Codice:':<15} {code or 'N/A'}")
    print(f"{'Password:':<15} {password}")
    print(f"{'Ruolo:':<15} {role}")
    print("-"*80 + "\n")

conn.close()