import discord
from discord.ext import commands
import json
import random
import string
import os
from datetime import datetime, timedelta
import asyncio

# ======================================================================
# TOKEN
# ======================================================================
TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    print("❌ BOT_TOKEN bulunamadi!")
    exit(1)

# ======================================================================
# KANAL VE YETKİLİ ID
# ======================================================================
TARGET_CHANNEL_ID = 1006507336426340364  # Mesajın gönderileceği kanal
AUTHORIZED_USER_ID = 1006507336426340364  # Yetkili kullanıcı ID

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
        
        # 24 saat kontrolü
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
                await interaction.followup.send(embed=embed)
                return
        
        # Aktif lisans kontrolü
        if user_id in db["users"]:
            key_data = db["users"][user_id]
            if datetime.fromisoformat(key_data["expires"]) > now:
                embed = discord.Embed(
                    title="❌ Already Have a License!",
                    description=f"Your key: `{key_data['key']}`",
                    color=discord.Color.orange()
                )
                await interaction.followup.send(embed=embed)
                return
        
        # Yeni key (1 GÜN GEÇERLİ)
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
        await interaction.followup.send(embed=embed)

# ======================================================================
# BOT
# ======================================================================
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix='!', intents=intents)

# ======================================================================
# DURUM DÖNGÜSÜ
# ======================================================================
async def status_loop():
    """Bot durumunu döngüyle günceller"""
    await bot.wait_until_ready()
    
    status_messages = [
        "yigitscript | new scripts",
        "Knife Duels | 24h keys",
        f"yigitscript | {len(bot.guilds)} servers",
        "yigitscript | premium cheats"
    ]
    
    index = 0
    while not bot.is_closed():
        try:
            # Sunucu üye sayısını al
            total_members = 0
            for guild in bot.guilds:
                total_members += guild.member_count or 0
            
            # Mesajı güncelle
            if index % 2 == 0:
                status = f"yigitscript | {total_members} users"
            else:
                status = status_messages[index % len(status_messages)]
            
            await bot.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.watching,
                    name=status
                )
            )
            
            index += 1
            await asyncio.sleep(10)  # 10 saniyede bir değişir
            
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
    
    # Sunucu bilgilerini göster
    for guild in bot.guilds:
        print(f'📌 {guild.name} - {guild.member_count} üye')
    
    # Durum döngüsünü başlat
    bot.loop.create_task(status_loop())

# ======================================================================
# !KNIFE-DUEL KOMUTU
# ======================================================================
@bot.command(name='knife-duel')
async def send_knife_duel_key(ctx):
    """Knife Duels key claim mesajını kanala gönderir - Sadece yetkili"""
    
    # YETKİ KONTROLÜ
    if ctx.author.id != AUTHORIZED_USER_ID:
        await ctx.send("❌ Bu komutu kullanma yetkin yok!")
        return
    
    # KANAL KONTROLÜ
    channel = bot.get_channel(TARGET_CHANNEL_ID)
    if not channel:
        await ctx.send(f"❌ Kanal bulunamadi! ID: {TARGET_CHANNEL_ID}")
        return
    
    # MESAJI OLUŞTUR
    embed = discord.Embed(
        title="🔪 KNIFE DUELS LICENSE KEY",
        description=(
            "Click **CLAIM KEY** to get your **Knife Duels** license key!\n\n"
            "⚡ **1 key per 24 hours**\n"
            "⏰ **24 hours validity**\n"
            "🔒 **Private message**\n\n"
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
    embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/...")  # İkon ekleyebilirsin
    
    view = KeyClaimButton()
    
    # GÖNDER
    await channel.send(embed=embed, view=view)
    await ctx.send(f"✅ Knife Duels key mesajı <#{TARGET_CHANNEL_ID}> kanalına gönderildi!")

# ======================================================================
# SLASH KOMUTLAR
# ======================================================================
@bot.tree.command(name="key", description="Get your 24h Knife Duels license key")
async def slash_key(interaction: discord.Interaction):
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
            await interaction.followup.send(embed=embed)
            return
    
    if user_id in db["users"]:
        key_data = db["users"][user_id]
        if datetime.fromisoformat(key_data["expires"]) > now:
            embed = discord.Embed(
                title="❌ Already Have a License!",
                description=f"Your key: `{key_data['key']}`",
                color=discord.Color.orange()
            )
            await interaction.followup.send(embed=embed)
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
    embed.set_footer(text="yigit script | Knife Duels")
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="keyinfo", description="Check your Knife Duels license info")
async def slash_keyinfo(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    db = load_db()
    user_id = str(interaction.user.id)
    
    if user_id not in db["users"]:
        embed = discord.Embed(
            title="❌ No License Found!",
            description="Use `/key` or click the button to get your Knife Duels license!",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
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
    await interaction.followup.send(embed=embed)

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
