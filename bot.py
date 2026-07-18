"""
bot.py
File utama. Jalankan dengan: python bot.py

Command yang tersedia:
  !mulai          -> intro + pilih mode (remaja / career switch) lewat tombol
  !profil         -> lihat profil tersimpan
  !editprofil     -> isi/update profil (minat, skill, pendidikan) lewat menu & modal
  !reset          -> hapus profil & histori chat
  !bantuan        -> daftar command
  !listprofesi    -> lihat semua profesi di database (ringkas)
  !detail <id>    -> detail lengkap satu profesi

Selain command di atas, SEMUA pesan biasa (bukan diawali "!") otomatis
diproses oleh AI dengan konteks profil + histori chat user.
"""

import os
import json
import discord
from discord.ext import commands
from dotenv import load_dotenv

import importlib

db = importlib.import_module('database')
from ai_client import tanya_ai

load_dotenv(override=True)

# Ambil token dari .env (bukan dari value statis)
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
NAMA_BOT = "Sugeng"  # ganti sesuai nama startup/bot kalian nanti

intents = discord.Intents.default()
intents.message_content = True
intents.members = False  # matikan privileged intents agar bot bisa login (aktifkan lagi bila diperlukan)

bot = commands.Bot(command_prefix="!", intents=intents, enable_debug_events=False)

WARNA_EMBED = 0x5865F2  # blurple, ganti sesuai branding kalian

KATEGORI_MINAT = [
    "Teknologi", "Seni & Desain", "Bisnis & Keuangan",
    "Sains", "Sosial & Komunikasi", "Kesehatan"
]


# =========================================================
# EVENTS
# =========================================================

@bot.event
async def on_ready():
    db.init_db()
    print(f"✅ {bot.user} sudah online!")


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Kalau diawali prefix command, biarkan sistem command yang tangani
    if message.content.startswith("!"):
        await bot.process_commands(message)
        return

    # Selain itu, semua diproses AI
    await proses_pesan_ke_ai(message.author.id, message.content, message.channel)


# =========================================================
# FUNGSI INTI: kirim pesan ke AI lalu balas
# =========================================================

async def proses_pesan_ke_ai(discord_id, pesan_text, channel):
    async with channel.typing():
        profil_text = db.profil_untuk_ai(discord_id)
        daftar_profesi_text = db.ringkasan_profesi_untuk_ai()
        histori = db.ambil_histori_chat(discord_id, limit=10)

        jawaban = await tanya_ai(
            profil_user_text=profil_text,
            daftar_profesi_text=daftar_profesi_text,
            histori_chat=histori,
            pesan_baru=pesan_text,
            nama_bot=NAMA_BOT
        )

    db.simpan_chat(discord_id, "user", pesan_text)
    db.simpan_chat(discord_id, "assistant", jawaban)

    # Discord batas 2000 karakter per pesan, potong kalau kepanjangan
    if len(jawaban) <= 2000:
        await channel.send(jawaban)
    else:
        for i in range(0, len(jawaban), 2000):
            await channel.send(jawaban[i:i + 2000])


# =========================================================
# COMMAND: !mulai
# =========================================================

class PilihanModeView(discord.ui.View):
    def __init__(self, discord_id):
        super().__init__(timeout=120)
        self.discord_id = discord_id

    @discord.ui.button(label="Aku masih remaja / pelajar 🎓", style=discord.ButtonStyle.primary)
    async def remaja(self, interaction: discord.Interaction, button: discord.ui.Button):
        db.buat_atau_update_profil(self.discord_id, mode="remaja")
        await interaction.response.send_message(
            "Sip! Mode diatur ke **Remaja**. Ceritain dong, kamu lagi tertarik sama bidang apa? "
            "Atau kalau masih bingung juga gapapa, bilang aja 'aku masih bingung mau kemana'.",
            ephemeral=False
        )

    @discord.ui.button(label="Aku dewasa & mau ganti karir 💼", style=discord.ButtonStyle.secondary)
    async def dewasa(self, interaction: discord.Interaction, button: discord.ui.Button):
        db.buat_atau_update_profil(self.discord_id, mode="career_switch")
        await interaction.response.send_message(
            "Oke, mode diatur ke **Ganti Karir**. Boleh cerita dikit, sekarang kerja di bidang apa "
            "dan apa yang bikin kamu pengen pindah?",
            ephemeral=False
        )


@bot.command(name="mulai")
async def mulai(ctx):
    embed = discord.Embed(
        title=f"👋 Halo, aku {NAMA_BOT}!",
        description=(
            "Aku bakal bantu kamu nemuin arah karir yang cocok buat kamu.\n\n"
            "Kamu bisa ngobrol bebas sama aku kapan aja (nggak perlu command), "
            "atau pilih dulu mode di bawah biar aku ngerti kondisi kamu:"
        ),
        color=WARNA_EMBED
    )
    embed.add_field(name="📌 Command berguna", value="Ketik `!bantuan` buat lihat semua command", inline=False)
    await ctx.send(embed=embed, view=PilihanModeView(ctx.author.id))


# =========================================================
# COMMAND: !profil & !editprofil
# =========================================================

@bot.command(name="profil")
async def profil(ctx):
    p = db.ambil_profil(ctx.author.id)
    if not p:
        await ctx.send("Kamu belum punya profil nih. Ketik `!mulai` dulu yuk!")
        return

    minat = ", ".join(json.loads(p["minat"])) if p["minat"] else "-"
    skill = ", ".join(json.loads(p["skill_dimiliki"])) if p["skill_dimiliki"] else "-"

    embed = discord.Embed(title=f"📋 Profil {ctx.author.display_name}", color=WARNA_EMBED)
    embed.add_field(name="Mode", value=p["mode"], inline=True)
    embed.add_field(name="Pendidikan", value=p["pendidikan"] or "-", inline=True)
    embed.add_field(name="Minat", value=minat, inline=False)
    embed.add_field(name="Skill dimiliki", value=skill, inline=False)
    if p["catatan_tambahan"]:
        embed.add_field(name="Catatan", value=p["catatan_tambahan"], inline=False)

    await ctx.send(embed=embed)


class MinatSelect(discord.ui.Select):
    def __init__(self, discord_id):
        self.discord_id = discord_id
        options = [discord.SelectOption(label=k) for k in KATEGORI_MINAT]
        super().__init__(placeholder="Pilih minat kamu (bisa lebih dari satu)",
                          min_values=1, max_values=len(options), options=options)

    async def callback(self, interaction: discord.Interaction):
        db.buat_atau_update_profil(self.discord_id, minat=self.values)
        await interaction.response.send_message(
            f"✅ Minat disimpan: {', '.join(self.values)}", ephemeral=True
        )


class EditProfilView(discord.ui.View):
    def __init__(self, discord_id):
        super().__init__(timeout=120)
        self.add_item(MinatSelect(discord_id))
        self.discord_id = discord_id

    @discord.ui.button(label="Isi skill / pendidikan / catatan lainnya", style=discord.ButtonStyle.secondary)
    async def isi_lainnya(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(DetailProfilModal(self.discord_id))


class DetailProfilModal(discord.ui.Modal, title="Lengkapi Profil"):
    skill = discord.ui.TextInput(
        label="Skill yang sudah dimiliki (pisahkan koma)",
        required=False, placeholder="misal: excel, desain poster, public speaking"
    )
    pendidikan = discord.ui.TextInput(
        label="Pendidikan terakhir / sedang ditempuh",
        required=False, placeholder="misal: SMA kelas 11, S1 Akuntansi"
    )
    catatan = discord.ui.TextInput(
        label="Cerita singkat / situasi kamu sekarang",
        required=False, style=discord.TextStyle.paragraph,
        placeholder="misal: aku kerja kantoran 3 tahun tapi ngerasa bosan..."
    )

    def __init__(self, discord_id):
        super().__init__()
        self.discord_id = discord_id

    async def on_submit(self, interaction: discord.Interaction):
        skill_list = [s.strip() for s in self.skill.value.split(",")] if self.skill.value else []
        db.buat_atau_update_profil(
            self.discord_id,
            skill_dimiliki=skill_list,
            pendidikan=self.pendidikan.value,
            catatan_tambahan=self.catatan.value
        )
        await interaction.response.send_message("✅ Profil kamu sudah diperbarui!", ephemeral=True)


@bot.command(name="editprofil")
async def editprofil(ctx):
    await ctx.send(
        "Yuk lengkapi profil kamu:",
        view=EditProfilView(ctx.author.id)
    )


# =========================================================
# COMMAND: !reset
# =========================================================

class KonfirmasiResetView(discord.ui.View):
    def __init__(self, discord_id):
        super().__init__(timeout=30)
        self.discord_id = discord_id

    @discord.ui.button(label="Ya, hapus semua", style=discord.ButtonStyle.danger)
    async def konfirmasi(self, interaction: discord.Interaction, button: discord.ui.Button):
        db.hapus_profil(self.discord_id)
        db.hapus_histori_chat(self.discord_id)
        await interaction.response.send_message("🗑️ Profil & histori chat kamu sudah dihapus.", ephemeral=True)

    @discord.ui.button(label="Batal", style=discord.ButtonStyle.secondary)
    async def batal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Oke, dibatalkan.", ephemeral=True)


@bot.command(name="reset")
async def reset(ctx):
    await ctx.send(
        "⚠️ Yakin mau hapus semua profil & histori chat kamu?",
        view=KonfirmasiResetView(ctx.author.id)
    )


# =========================================================
# COMMAND: !listprofesi & !detail
# =========================================================

@bot.command(name="listprofesi")
async def listprofesi(ctx):
    profesi = db.ambil_semua_profesi()
    if not profesi:
        await ctx.send("Database profesi masih kosong. Admin perlu import data dulu.")
        return

    embed = discord.Embed(title="📚 Daftar Profesi", color=WARNA_EMBED)
    for p in profesi[:25]:  # batas embed field
        kategori = ", ".join(json.loads(p["kategori"])) if p["kategori"] else "-"
        embed.add_field(
            name=f"{p['nama']}  (`{p['id']}`)",
            value=f"Kategori: {kategori}\nKetik `!detail {p['id']}` untuk info lengkap",
            inline=False
        )
    await ctx.send(embed=embed)


@bot.command(name="detail")
async def detail(ctx, profession_id: str = None):
    if not profession_id:
        await ctx.send("Pakai format: `!detail <id_profesi>`. Contoh: `!detail data-analyst`\n"
                        "Lihat semua id dengan `!listprofesi`")
        return

    p = db.ambil_profesi_by_id(profession_id)
    if not p:
        await ctx.send(f"Profesi dengan id `{profession_id}` tidak ditemukan. Cek `!listprofesi` untuk daftar id yang valid.")
        return

    embed = discord.Embed(title=f"💼 {p['nama']}", description=p["deskripsi_singkat"], color=WARNA_EMBED)
    embed.add_field(name="Tugas harian", value="\n".join(f"• {t}" for t in json.loads(p["tugas_harian"])) or "-", inline=False)
    embed.add_field(name="Skill dibutuhkan", value=", ".join(json.loads(p["skill_dibutuhkan"])) or "-", inline=False)
    embed.add_field(name="Estimasi gaji", value=p["estimasi_gaji_indonesia"] or "-", inline=True)
    embed.add_field(name="Pendidikan minimal", value=p["jenjang_pendidikan_minimal"] or "-", inline=True)
    embed.add_field(name="Sertifikasi rekomendasi", value=", ".join(json.loads(p["sertifikasi_rekomendasi"])) or "-", inline=False)
    embed.add_field(name="Langkah awal", value="\n".join(f"{i+1}. {s}" for i, s in enumerate(json.loads(p["langkah_awal"]))) or "-", inline=False)

    await ctx.send(embed=embed)


# =========================================================
# COMMAND: !bantuan
# =========================================================

@bot.command(name="bantuan")
async def bantuan(ctx):
    embed = discord.Embed(title=f"🧭 Bantuan {NAMA_BOT}", color=WARNA_EMBED)
    embed.add_field(name="!mulai", value="Mulai dari awal, pilih mode (remaja/ganti karir)", inline=False)
    embed.add_field(name="!profil", value="Lihat profil kamu yang tersimpan", inline=False)
    embed.add_field(name="!editprofil", value="Isi/update minat, skill, pendidikan", inline=False)
    embed.add_field(name="!listprofesi", value="Lihat semua profesi yang ada di database", inline=False)
    embed.add_field(name="!detail <id>", value="Lihat detail lengkap satu profesi", inline=False)
    embed.add_field(name="!reset", value="Hapus profil & histori chat kamu", inline=False)
    embed.add_field(name="💬 Ngobrol bebas", value="Selain command di atas, kamu bisa chat bebas kapan aja — aku bakal jawab pakai AI!", inline=False)
    await ctx.send(embed=embed)


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        raise ValueError("DISCORD_TOKEN belum diatur di file .env")
    bot.run(DISCORD_TOKEN)
