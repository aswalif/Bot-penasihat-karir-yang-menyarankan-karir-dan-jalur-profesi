"""
database.py
Semua fungsi buat baca/tulis ke database SQLite.
Database dibagi 3 tabel:
1. professions   -> data profesi (diisi manual/lewat import_data.py)
2. users         -> profil singkat tiap user Discord
3. chat_history  -> histori percakapan user dgn AI (biar AI "inget" konteks)
"""

import sqlite3
import json
from datetime import datetime

DB_PATH = "career_bot.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Bikin tabel kalau belum ada. Panggil sekali waktu bot start."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS professions (
            id TEXT PRIMARY KEY,
            nama TEXT NOT NULL,
            kategori TEXT,                  -- JSON list, mis. ["teknologi","bisnis"]
            deskripsi_singkat TEXT,
            tugas_harian TEXT,               -- JSON list
            skill_dibutuhkan TEXT,           -- JSON list
            cocok_untuk_kepribadian TEXT,    -- JSON list
            jenjang_pendidikan_minimal TEXT,
            estimasi_gaji_indonesia TEXT,
            sertifikasi_rekomendasi TEXT,    -- JSON list
            langkah_awal TEXT,               -- JSON list
            cocok_untuk_remaja INTEGER DEFAULT 1,
            cocok_untuk_career_switch INTEGER DEFAULT 1,
            tingkat_kompetisi TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            discord_id TEXT PRIMARY KEY,
            mode TEXT DEFAULT 'belum_dipilih',   -- 'remaja' / 'career_switch'
            nama_panggilan TEXT,
            minat TEXT,              -- JSON list
            skill_dimiliki TEXT,     -- JSON list
            pendidikan TEXT,
            catatan_tambahan TEXT,   -- freeform, misal cerita latar belakang
            dibuat_pada TEXT,
            diupdate_pada TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            discord_id TEXT,
            role TEXT,          -- 'user' atau 'assistant'
            content TEXT,
            waktu TEXT
        )
    """)

    conn.commit()
    conn.close()


# ---------- PROFESSIONS ----------

def import_professions_from_json(json_path):
    """Import/replace data profesi dari file JSON (list of objects)."""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    conn = get_connection()
    cur = conn.cursor()
    for p in data:
        cur.execute("""
            INSERT OR REPLACE INTO professions
            (id, nama, kategori, deskripsi_singkat, tugas_harian, skill_dibutuhkan,
             cocok_untuk_kepribadian, jenjang_pendidikan_minimal, estimasi_gaji_indonesia,
             sertifikasi_rekomendasi, langkah_awal, cocok_untuk_remaja,
             cocok_untuk_career_switch, tingkat_kompetisi)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            p["id"], p["nama"], json.dumps(p.get("kategori", [])),
            p.get("deskripsi_singkat", ""), json.dumps(p.get("tugas_harian", [])),
            json.dumps(p.get("skill_dibutuhkan", [])),
            json.dumps(p.get("cocok_untuk_kepribadian", [])),
            p.get("jenjang_pendidikan_minimal", ""),
            p.get("estimasi_gaji_indonesia", ""),
            json.dumps(p.get("sertifikasi_rekomendasi", [])),
            json.dumps(p.get("langkah_awal", [])),
            int(p.get("cocok_untuk_remaja", True)),
            int(p.get("cocok_untuk_career_switch", True)),
            p.get("tingkat_kompetisi", "")
        ))
    conn.commit()
    conn.close()


def ambil_semua_profesi():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM professions")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def ambil_profesi_by_id(profession_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM professions WHERE id = ?", (profession_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def ringkasan_profesi_untuk_ai():
    """
    Bikin ringkasan singkat semua profesi buat dimasukkan ke system prompt AI.
    Diringkas biar hemat token, tapi tetap cukup info buat AI mikir.
    """
    profesi = ambil_semua_profesi()
    if not profesi:
        return "(Belum ada data profesi di database. Gunakan pengetahuan umummu.)"

    lines = []
    for p in profesi:
        kategori = ", ".join(json.loads(p["kategori"])) if p["kategori"] else "-"
        skill = ", ".join(json.loads(p["skill_dibutuhkan"])) if p["skill_dibutuhkan"] else "-"
        lines.append(
            f"- {p['nama']} (id: {p['id']}) | Kategori: {kategori} | "
            f"Skill: {skill} | Gaji: {p['estimasi_gaji_indonesia']} | "
            f"Cocok remaja: {'ya' if p['cocok_untuk_remaja'] else 'tidak'}, "
            f"Cocok career switch: {'ya' if p['cocok_untuk_career_switch'] else 'tidak'}"
        )
    return "\n".join(lines)


# ---------- USERS ----------

def ambil_profil(discord_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE discord_id = ?", (str(discord_id),))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def buat_atau_update_profil(discord_id, **fields):
    """
    fields yang bisa diisi: mode, nama_panggilan, minat (list), skill_dimiliki (list),
    pendidikan, catatan_tambahan
    """
    existing = ambil_profil(discord_id)
    now = datetime.utcnow().isoformat()

    conn = get_connection()
    cur = conn.cursor()

    if existing is None:
        cur.execute("""
            INSERT INTO users (discord_id, mode, nama_panggilan, minat, skill_dimiliki,
                                pendidikan, catatan_tambahan, dibuat_pada, diupdate_pada)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(discord_id),
            fields.get("mode", "belum_dipilih"),
            fields.get("nama_panggilan", ""),
            json.dumps(fields.get("minat", [])),
            json.dumps(fields.get("skill_dimiliki", [])),
            fields.get("pendidikan", ""),
            fields.get("catatan_tambahan", ""),
            now, now
        ))
    else:
        merged = dict(existing)
        for k, v in fields.items():
            if k in ("minat", "skill_dimiliki"):
                merged[k] = json.dumps(v)
            else:
                merged[k] = v
        merged["diupdate_pada"] = now
        cur.execute("""
            UPDATE users SET mode=?, nama_panggilan=?, minat=?, skill_dimiliki=?,
                              pendidikan=?, catatan_tambahan=?, diupdate_pada=?
            WHERE discord_id=?
        """, (
            merged["mode"], merged["nama_panggilan"], merged["minat"],
            merged["skill_dimiliki"], merged["pendidikan"],
            merged["catatan_tambahan"], merged["diupdate_pada"], str(discord_id)
        ))

    conn.commit()
    conn.close()


def hapus_profil(discord_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE discord_id = ?", (str(discord_id),))
    cur.execute("DELETE FROM chat_history WHERE discord_id = ?", (str(discord_id),))
    conn.commit()
    conn.close()


def profil_untuk_ai(discord_id):
    """Format profil user jadi teks buat dimasukkan ke system prompt AI."""
    p = ambil_profil(discord_id)
    if not p:
        return "User belum mengisi profil apapun. Gali informasi dasar dulu (usia kira-kira, minat, situasi saat ini)."

    minat = ", ".join(json.loads(p["minat"])) if p["minat"] else "belum diketahui"
    skill = ", ".join(json.loads(p["skill_dimiliki"])) if p["skill_dimiliki"] else "belum diketahui"

    return (
        f"Mode: {p['mode']}\n"
        f"Nama panggilan: {p['nama_panggilan'] or 'belum diketahui'}\n"
        f"Minat: {minat}\n"
        f"Skill dimiliki: {skill}\n"
        f"Pendidikan: {p['pendidikan'] or 'belum diketahui'}\n"
        f"Catatan tambahan: {p['catatan_tambahan'] or '-'}"
    )


# ---------- CHAT HISTORY ----------

def simpan_chat(discord_id, role, content):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO chat_history (discord_id, role, content, waktu)
        VALUES (?, ?, ?, ?)
    """, (str(discord_id), role, content, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()


def ambil_histori_chat(discord_id, limit=10):
    """
    Ambil N chat terakhir, dikembalikan dalam format list of dict
    siap dipakai di parameter 'messages' API AI.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT role, content FROM chat_history
        WHERE discord_id = ?
        ORDER BY id DESC LIMIT ?
    """, (str(discord_id), limit))
    rows = cur.fetchall()
    conn.close()
    rows = list(reversed(rows))
    return [{"role": r["role"], "content": r["content"]} for r in rows]


def hapus_histori_chat(discord_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM chat_history WHERE discord_id = ?", (str(discord_id),))
    conn.commit()
    conn.close()
