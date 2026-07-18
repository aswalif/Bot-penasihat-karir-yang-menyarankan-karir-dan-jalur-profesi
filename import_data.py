"""
import_data.py
Jalankan ini setiap kali mau import/update data profesi dari file JSON ke database.

Cara pakai:
    python import_data.py data_profesi_contoh.json

Atau edit DEFAULT_FILE di bawah dan jalankan tanpa argumen:
    python import_data.py
"""

import sys
import database as db

DEFAULT_FILE = "data_profesi_contoh.json"

if __name__ == "__main__":
    db.init_db()
    file_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_FILE
    db.import_professions_from_json(file_path)
    print(f"✅ Data profesi dari '{file_path}' berhasil diimport ke database.")
