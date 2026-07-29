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

# ======================================================================
# WEB SUNUCUSU
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
AUTHORIZED_USER_ID = 1006507336426340364
VOICE_CHANNEL_ID = 1531981051646181468  # 🔥 Working kanalı

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
intents.voice_states = True
bot = commands.Bot(command_prefix='!', intents=intents)

# ======================================================================
# SES KANALINA KATIL (GELİŞMİŞ)
# ======================================================================
async def join_voice_channel():
    await bot.wait_until_ready()
    
    try:
        print(f"🔍 Ses kanalı aranıyor: {VOICE_CHANNEL_ID}")
        
        # Kanalı bul
        channel = bot.get_channel(VOICE_CHANNEL_ID)
        if not channel:
            print(f"❌ Ses kanalı bulunamadi! ID: {VOICE_CHANNEL_ID}")
            print(f"📌 Mevcut kanallar:")
            for guild in bot.guilds:
                for ch in guild.channels:
                    if ch.type == discord.ChannelType.voice:
                        print(f"   - {ch.name} (ID: {ch.id})")
            return
        
        print(f"✅ Ses kanalı bulundu: {channel.name}")
        
        # Zaten bağlı mı kontrol et
        for guild in bot.guilds:
            if guild.voice_client:
                if guild.voice_client.channel.id == VOICE_CHANNEL_ID:
                    print(f"✅ Bot zaten ses kanalında: {channel.name}")
                    return
                else:
                    print(f"❌ Eski kanaldan ayrılıyor: {guild.voice_client.channel.name}")
                    await guild.voice_client.disconnect()
                    await asyncio.sleep(1)
        
        # Bağlan
        print(f"🔗 Ses kanalına bağlanılıyor: {channel.name}")
        vc = await channel.connect(timeout=30)
        
        if vc:
            print(f"✅ Bot ses kanalına katıldı: {channel.name}")
            # Mikrofonu kapat, sağır ol
            await vc.guild.change_voice_state(
                channel=channel, 
                self_mute=True, 
                self_deaf=True
            )
            print(f"🔇 Bot mikrofon kapalı, sağır modda")
        else:
            print(f"❌ Bağlantı başarısız!")
            
    except discord.Forbidden:
        print(f"❌ Yetki hatası! Bot'un ses kanalına bağlanma izni yok!")
        print(f"📌 Bot'a şu yetkileri ver:")
        print(f"   - Connect (Bağlanma)")
        print(f"   - Speak (Konuşma)")
        print(f"   - Use Voice Activity")
    except discord.NotFound:
        print(f"❌ Ses kanalı bulunamadi! ID: {VOICE_CHANNEL_ID}")
    except Exception as e:
        print(f"❌ Ses kanalına katılma hatasi: {e}")
        print(f"📌 Hata tipi: {type(e).__name__}")

# ======================================================================
# DURUM DÖNGÜSÜ
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
# KOMUTLAR
# ======================================================================
@bot.event
async def on_ready():
    print(f'✅ Bot hazir! {bot.user}')
    print(f'📊 {len(bot.guilds)} sunucuda aktif')
    
    for guild in bot.guilds:
        print(f'📌 {guild.name} - {guild.member_count} üye')
        # Ses kanallarını listele
        for ch in guild.channels:
            if ch.type == discord.ChannelType.voice:
                print(f"   🔊 {ch.name} (ID: {ch.id})")
    
    bot.loop.create_task(status_loop())
    
    # Ses kanalına katıl (5 saniye sonra)
    await asyncio.sleep(5)
    await join_voice_channel()

# ======================================================================
# !KNIFE-DUEL KOMUTU
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
# SLASH KOMUTLARI SENKRONİZE ET
# ======================================================================
@bot.event
async def on_connect():
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
