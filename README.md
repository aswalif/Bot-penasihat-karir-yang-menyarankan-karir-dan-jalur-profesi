# Bot Penasihat Karir

Bot Discord yang bantu remaja & orang dewasa yang mau ganti karir menemukan jalur
profesional yang cocok, dengan otak AI (lewat OpenRouter) supaya jawabannya adaptif
dan tidak template.

## Struktur File

```
career_bot/
├── bot.py                     # File utama, semua command & UI (button/menu/modal)
├── database.py                # Setup & fungsi akses SQLite
├── ai_client.py                # Fungsi manggil OpenRouter API
├── import_data.py             # Script buat import data profesi dari JSON
├── data_profesi_contoh.json   # Contoh 5 data profesi, edit/tambah sesuka kalian
├── requirements.txt
└── .env.example                # Contoh isi file .env
```

## Cara Setup

1. **Install dependency**
   ```
   pip install -r requirements.txt
   ```

2. **Bikin bot Discord** di https://discord.com/developers/applications
   - Bikin New Application → Bot → Copy token
   - Di tab "Bot", aktifkan **MESSAGE CONTENT INTENT** (wajib biar bot bisa baca chat biasa)
   - Invite bot ke server pakai OAuth2 URL Generator (centang `bot`, permission minimal: Send Messages, Read Message History, Embed Links, Use Slash Commands)

3. **Ambil API key OpenRouter** di https://openrouter.ai/keys

4. **Siapkan file `.env`**
   ```
   cp .env.example .env
   ```
   Lalu isi `DISCORD_TOKEN` dan `OPENROUTER_API_KEY` di dalamnya.

5. **Import data profesi ke database**
   ```
   python import_data.py data_profesi_contoh.json
   ```
   Ini bakal bikin file `career_bot.db` otomatis.

6. **Jalankan bot**
   ```
   python bot.py
   ```

## Cara Menambah/Update Data Profesi

Edit atau bikin file JSON baru dengan format seperti `data_profesi_contoh.json`,
lalu jalankan lagi:
```
python import_data.py nama_file_kalian.json
```
Data dengan `id` yang sama otomatis akan di-replace (update), jadi aman dijalankan berkali-kali.

**Format satu entri profesi:**
```json
{
  "id": "id-unik-tanpa-spasi",
  "nama": "Nama Profesi",
  "kategori": ["Teknologi", "Bisnis & Keuangan"],
  "deskripsi_singkat": "1-2 kalimat deskripsi",
  "tugas_harian": ["tugas 1", "tugas 2"],
  "skill_dibutuhkan": ["skill 1", "skill 2"],
  "cocok_untuk_kepribadian": ["analitis", "kreatif"],
  "jenjang_pendidikan_minimal": "SMA/sederajat",
  "estimasi_gaji_indonesia": "Rp5-10 juta/bulan",
  "sertifikasi_rekomendasi": ["nama kursus/sertifikasi"],
  "langkah_awal": ["langkah 1", "langkah 2", "langkah 3"],
  "cocok_untuk_remaja": true,
  "cocok_untuk_career_switch": true,
  "tingkat_kompetisi": "sedang"
}
```

## Command yang Tersedia

| Command | Fungsi |
|---|---|
| `!mulai` | Intro bot + pilih mode (remaja/ganti karir) lewat tombol |
| `!profil` | Lihat profil yang tersimpan |
| `!editprofil` | Isi/update minat (dropdown), skill/pendidikan/catatan (form pop-up) |
| `!listprofesi` | Lihat semua profesi di database |
| `!detail <id>` | Detail lengkap satu profesi, misal `!detail data-analyst` |
| `!reset` | Hapus profil & histori chat (dengan konfirmasi tombol) |
| `!bantuan` | Daftar semua command |
| *(chat bebas)* | Semua pesan yang bukan command otomatis dijawab AI dengan konteks profil user |

## Catatan Penting

- Ganti `MODEL` di `ai_client.py` kalau mau pakai model lain (lebih murah/lebih pintar), lihat daftar model di https://openrouter.ai/models
- `NAMA_BOT` di `bot.py` masih placeholder ("Sugeng
- ") — ganti sesuai nama startup kalian nanti
- Database pakai SQLite (`career_bot.db`), cukup untuk awal. Kalau user sudah banyak, bisa migrasi ke PostgreSQL
- Jangan commit file `.env` ke Git (sudah seharusnya masuk `.gitignore`)
