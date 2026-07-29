import discord
from discord.ext import commands
import json
import random
import string
import os
from datetime import datetime, timedelta
import asyncio
from flask import Flask
import threading
import psutil
import time

# ======================================================================
# WEB SUNUCUSU (Render için)
# ======================================================================
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Yigit Bot çalışıyor!"

@app.route('/health')
def health():
    return "OK", 200

def run_web():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_web, daemon=True).start()
print("🌐 Web sunucusu başlatıldı!")

# ======================================================================
# TOKEN
# ======================================================================
TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    print("❌ BOT_TOKEN bulunamadi!")
    exit(1)

# ======================================================================
# AYARLAR
# ======================================================================
AUTHORIZED_USER_ID = 1006507336426340364  # 🔥 Senin Discord ID'n
STATUS_CHANNEL_ID = 1531992520547106930   # 🔥 Durum mesajlarının gönderileceği kanal

# ======================================================================
# VERİTABANI
# ======================================================================
DB_FILE = "keys.json"

def load_db():
    try:
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    except:
        return {"keys": {}, "users": {}, "last_key_time": {}}

def save_db(db):
    with open(DB_FILE, 'w') as f:
        json.dump(db, f, indent=4)

def generate_key():
    parts = ['YIGIT']
    for _ in range(3):
        part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        parts.append(part)
    return '-'.join(parts)

# ======================================================================
# BUTON
# ======================================================================
class KeyClaimButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="🎯 CLAIM KEY", style=discord.ButtonStyle.primary, custom_id="claim_key")
    async def claim_key(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        
        db = load_db()
        user_id = str(interaction.user.id)
        now = datetime.now()
        
        if user_id in db["last_key_time"]:
            last_time = datetime.fromisoformat(db["last_key_time"][user_id])
            if now - last_time < timedelta(hours=24):
                remaining = timedelta(hours=24) - (now - last_time)
                hours = int(remaining.total_seconds() // 3600)
                minutes = int((remaining.total_seconds() % 3600) // 60)
                embed = discord.Embed(
                    title="⏳ WAIT!",
                    description=f"Next key in **{hours}h {minutes}m**!",
                    color=discord.Color.orange()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
        
        if user_id in db["users"]:
            key_data = db["users"][user_id]
            if datetime.fromisoformat(key_data["expires"]) > now:
                embed = discord.Embed(
                    title="❌ Already Have a License!",
                    description=f"Your key: `{key_data['key']}`\nExpires: {datetime.fromisoformat(key_data['expires']).strftime('%d.%m.%Y %H:%M')}",
                    color=discord.Color.orange()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
        
        new_key = generate_key()
        expires = now + timedelta(days=1)
        
        db["keys"][new_key] = {
            "user": user_id,
            "created": now.isoformat(),
            "expires": expires.isoformat(),
            "used": False
        }
        db["users"][user_id] = {
            "key": new_key,
            "expires": expires.isoformat()
        }
        db["last_key_time"][user_id] = now.isoformat()
        save_db(db)
        
        embed = discord.Embed(
            title="🔑 YOUR KNIFE DUELS LICENSE",
            description=f"```\n{new_key}\n```",
            color=discord.Color.green()
        )
        embed.add_field(
            name="📅 Valid Until",
            value=f"**24 hours** (Expires: {expires.strftime('%d.%m.%Y %H:%M')})",
            inline=False
        )
        embed.add_field(
            name="📝 How to Use",
            value="Enter this key when the Knife Duels script asks for a license.",
            inline=False
        )
        embed.set_footer(text="yigit script | Knife Duels")
        
        await interaction.followup.send(embed=embed, ephemeral=True)

# ======================================================================
# BOT
# ======================================================================
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix='!', intents=intents)

# ======================================================================
# DURUM DÖNGÜSÜ (5 DAKİKADA BİR MESAJ GÖNDER)
# ======================================================================
async def status_message_loop():
    """Her 5 dakikada bir durum kanalına mesaj gönderir"""
    await bot.wait_until_ready()
    
    while not bot.is_closed():
        try:
            # Kanalı bul
            channel = bot.get_channel(STATUS_CHANNEL_ID)
            if not channel:
                print(f"❌ Durum kanalı bulunamadi! ID: {STATUS_CHANNEL_ID}")
                await asyncio.sleep(60)
                continue
            
            # Veritabanından bilgileri al
            db = load_db()
            total_keys = len(db["keys"])
            
            # Aktif key sayısı
            active_keys = 0
            now = datetime.now()
            for key, data in db["keys"].items():
                if datetime.fromisoformat(data["expires"]) > now:
                    active_keys += 1
            
            # Süresi dolan key sayısı
            expired_keys = total_keys - active_keys
            
            # Toplam üye sayısı
            total_members = 0
            for guild in bot.guilds:
                total_members += guild.member_count or 0
            
            # Bot'un ping'i
            ping = round(bot.latency * 1000)
            
            # Çalışma süresi
            uptime = time.time() - bot.uptime if hasattr(bot, 'uptime') else 0
            uptime_str = str(timedelta(seconds=int(uptime)))
            
            # Embed mesajı oluştur
            embed = discord.Embed(
                title="⚡ YIGIT SCRIPT v5.0 | KNIFE DUELS",
                description="**Bot Durumu:** 🟢 Çalışıyor",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="📊 Sunucu Bilgileri",
                value=f"├─ 👥 Toplam Üye: **{total_members}**\n"
                      f"├─ 🔑 Oluşturulan Key: **{total_keys}**\n"
                      f"├─ ✅ Aktif Key: **{active_keys}**\n"
                      f"└─ ⏰ Süresi Dolan: **{expired_keys}**",
                inline=False
            )
            
            embed.add_field(
                name="💾 Sistem Bilgileri",
                value=f"├─ 📡 Ping: **{ping}ms**\n"
                      f"├─ ⏱️ Çalışma Süresi: **{uptime_str}**\n"
                      f"├─ 💻 CPU: **%{psutil.cpu_percent()}**\n"
                      f"└─ 🧠 RAM: **{psutil.virtual_memory().used // (1024**3)}GB / {psutil.virtual_memory().total // (1024**3)}GB**",
                inline=False
            )
            
            embed.add_field(
                name="✨ Premium Features",
                value="• Auto Aim\n"
                      "• ESP & Glow\n"
                      "• Rage Mode\n"
                      "• Visual Effects\n"
                      "• Triggerbot\n"
                      "• 24h Keys",
                inline=True
            )
            
            embed.add_field(
                name="🔗 Nasıl Key Alınır?",
                value="**CLAIM KEY** butonuna tıkla veya `/keyinfo` yaz.",
                inline=True
            )
            
            embed.set_footer(
                text="yigit script | Knife Duels | 24h keys",
                icon_url="https://cdn.discordapp.com/attachments/..."  # İkon ekleyebilirsin
            )
            
            # Mesajı gönder
            await channel.send(embed=embed)
            print(f"✅ Durum mesajı gönderildi: {datetime.now().strftime('%H:%M:%S')}")
            
        except Exception as e:
            print(f"❌ Durum mesajı hatasi: {e}")
        
        # 5 dakika bekle (300 saniye)
        await asyncio.sleep(300)

# ======================================================================
# DURUM DÖNGÜSÜ (Bot'un status'u için)
# ======================================================================
async def status_loop():
    await bot.wait_until_ready()
    index = 0
    while not bot.is_closed():
        try:
            db = load_db()
            total_keys = len(db["keys"])
            active_keys = 0
            now = datetime.now()
            for key, data in db["keys"].items():
                if datetime.fromisoformat(data["expires"]) > now:
                    active_keys += 1
            total_members = 0
            for guild in bot.guilds:
                total_members += guild.member_count or 0
            
            messages = [
                f"yigitscript | {total_keys} keys",
                f"Knife Duels | {active_keys} active",
                f"yigitscript | {total_members} users",
                "yigitscript | new scripts"
            ]
            status = messages[index % len(messages)]
            await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=status))
            index += 1
            await asyncio.sleep(12)
        except Exception as e:
            print(f"❌ Durum güncelleme hatasi: {e}")
            await asyncio.sleep(30)

# ======================================================================
# KOMUT: !knife-duel
# ======================================================================
@bot.command(name='knife-duel')
async def send_knife_duel_key(ctx):
    if ctx.author.id != AUTHORIZED_USER_ID:
        await ctx.send("❌ Bu komutu kullanma yetkin yok!")
        return
    
    embed = discord.Embed(
        title="🔪 KNIFE DUELS LICENSE KEY",
        description=(
            "Click **CLAIM KEY** to get your **Knife Duels** license key!\n\n"
            "⚡ **1 key per 24 hours**\n"
            "⏰ **24 hours validity**\n"
            "🔒 **Your key is sent privately**\n\n"
            "**✨ Premium Features:**\n"
            "• Auto Aim\n"
            "• ESP & Glow\n"
            "• Rage Mode\n"
            "• Visual Effects\n"
            "• Triggerbot\n"
            "• And much more!"
        ),
        color=discord.Color.blue()
    )
    embed.set_footer(text="yigit script | Knife Duels | 24h keys")
    view = KeyClaimButton()
    await ctx.send(embed=embed, view=view)
    await ctx.send(f"✅ Knife Duels key mesajı bu kanala gönderildi!")

# ======================================================================
# /KEYINFO KOMUTU
# ======================================================================
@bot.tree.command(name="keyinfo", description="Check your Knife Duels license info")
async def slash_keyinfo(interaction: discord.Interaction):
    db = load_db()
    user_id = str(interaction.user.id)
    
    if user_id not in db["users"]:
        embed = discord.Embed(
            title="❌ No License Found!",
            description="Click the **CLAIM KEY** button in the key channel to get your Knife Duels license!",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    key_data = db["users"][user_id]
    expires = datetime.fromisoformat(key_data["expires"])
    is_expired = expires < datetime.now()
    
    if not is_expired:
        remaining = expires - datetime.now()
        hours = int(remaining.total_seconds() // 3600)
        minutes = int((remaining.total_seconds() % 3600) // 60)
        time_left = f"{hours}h {minutes}m"
    else:
        time_left = "EXPIRED"
    
    embed = discord.Embed(
        title="🔑 Your Knife Duels License",
        color=discord.Color.red() if is_expired else discord.Color.green()
    )
    embed.add_field(name="Key", value=f"`{key_data['key']}`", inline=False)
    embed.add_field(name="Status", value="❌ Expired" if is_expired else "✅ Active", inline=True)
    embed.add_field(name="Time Left", value=time_left, inline=True)
    embed.add_field(name="Expires", value=expires.strftime('%d.%m.%Y %H:%M'), inline=True)
    embed.set_footer(text="yigit script | Knife Duels")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ======================================================================
# KOMUTLARI SENKRONİZE ET
# ======================================================================
@bot.event
async def on_ready():
    print(f'✅ Bot hazir! {bot.user}')
    print(f'📊 {len(bot.guilds)} sunucuda aktif')
    for guild in bot.guilds:
        print(f'📌 {guild.name} - {guild.member_count} üye')
    
    # Bot'un başlangıç zamanını kaydet
    bot.uptime = time.time()
    
    # Durum döngülerini başlat
    bot.loop.create_task(status_loop())
    bot.loop.create_task(status_message_loop())
    
    try:
        await bot.tree.sync()
        print("✅ Slash komutlar senkronize edildi!")
    except Exception as e:
        print(f"❌ Senkronizasyon hatasi: {e}")

# ======================================================================
# BOT ÇALIŞTIR
# ======================================================================
if __name__ == "__main__":
    print("🔪 Knife Duels Bot başlatılıyor...")
    bot.run(TOKEN)
