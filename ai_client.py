"""
ai_client.py
Fungsi buat manggil OpenRouter API. Semua "kepintaran" bot ada di sini.
"""

import os
import aiohttp
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Model AI yang dipakai. Default pakai model GRATIS supaya bisa langsung jalan
# dengan API key gratisan OpenRouter.
#
# "openrouter/free"  -> router otomatis, pilih model gratis yang lagi tersedia (paling aman dipakai)
# "meta-llama/llama-3.3-70b-instruct:free" -> model gratis spesifik, stabil, cocok buat chat
#
# Kalau nanti udah topup credit OpenRouter dan mau kualitas lebih tinggi, ganti ke model berbayar, misal:
# "anthropic/claude-3.5-sonnet"
#
# Catatan: daftar model gratis di OpenRouter berubah-ubah, cek https://openrouter.ai/models?q=free
# kalau muncul error 404 "No endpoints found" lagi.
MODEL = "google/gemma-4-26b-a4b-it:free"


SYSTEM_PROMPT_TEMPLATE = """Kamu adalah penasihat karir bernama {nama_bot}. Kamu ramah, suportif, dan tidak menggurui.

TARGET PENGGUNA:
- Remaja yang masih bingung mau lanjut jurusan/karir apa
- Orang dewasa yang bosan/jenuh dengan pekerjaan sekarang dan mau eksplorasi pilihan lain

GAYA BICARA:
- Kalau user terdengar seperti remaja (bahasa santai, nyebut sekolah/kuliah): pakai bahasa santai, semangat, jangan kaku
- Kalau user terdengar dewasa/profesional: sedikit lebih formal tapi tetap hangat, empati ke rasa capek/bosan mereka
- Jangan kasih jawaban generik template. Gali dulu kalau info user belum cukup (tanya balik 1-2 pertanyaan ringan)
- Jawaban terstruktur, pakai poin-poin/emoji secukupnya, jangan bertele-tele
- Selalu akhiri dengan langkah kecil yang bisa langsung dicoba user (actionable)

ATURAN PENTING:
- HANYA rekomendasikan profesi dari DATA PROFESI di bawah ini. Kalau tidak ada yang cocok, boleh kasih ide umum tapi bilang jujur itu di luar database kami
- Jangan pernah bikin klaim gaji/prospek yang tidak ada di data
- Kalau user curhat soal stres/burnout, tanggapi dengan empati dulu sebelum kasih saran karir

DATA PROFESI YANG TERSEDIA:
{daftar_profesi}

PROFIL USER INI:
{profil_user}
"""


async def tanya_ai(profil_user_text, daftar_profesi_text, histori_chat, pesan_baru, nama_bot="Kompas"):
    """
    histori_chat: list of {"role": "user"/"assistant", "content": "..."}
    """
    if not OPENROUTER_API_KEY:
        return "⚠️ API key belum diatur. Hubungi admin bot untuk setup OPENROUTER_API_KEY."

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        nama_bot=nama_bot,
        daftar_profesi=daftar_profesi_text,
        profil_user=profil_user_text
    )

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(histori_chat)
    messages.append({"role": "user", "content": pesan_baru})

    payload = {
        "model": MODEL,
        "messages": messages,
        "max_tokens": 800,
        "temperature": 0.8,
    }

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(OPENROUTER_URL, headers=headers, json=payload, timeout=60) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    print(f"[AI ERROR] Status {resp.status}: {error_text}")
                    return "Maaf, aku lagi ada gangguan teknis. Coba lagi sebentar ya 🙏"

                data = await resp.json()
                return data["choices"][0]["message"]["content"]

    except Exception as e:
        print(f"[AI EXCEPTION] {e}")
        return "Maaf, aku lagi ada gangguan teknis. Coba lagi sebentar ya 🙏"