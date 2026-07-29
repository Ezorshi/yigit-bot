import discord
from discord.ext import commands
from discord import app_commands
import json
import random
import string
import os
from datetime import datetime, timedelta

# ======================================================================
# TOKEN - RENDER ENV'DEN AL
# ======================================================================
TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    print("❌ BOT_TOKEN environment variable bulunamadi!")
    exit(1)

# ======================================================================
# VERITABANI
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

# ======================================================================
# KEY URETME
# ======================================================================
def generate_key():
    parts = ['YIGIT']
    for _ in range(3):
        part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        parts.append(part)
    return '-'.join(parts)

# ======================================================================
# KEY CLAIM BUTONU
# ======================================================================
class KeyClaimButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="🎯 CLAIM KEY", style=discord.ButtonStyle.primary, custom_id="claim_key")
    async def claim_key(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Key claim butonu - Sadece tıklayan kişi görür"""
        
        await interaction.response.defer(ephemeral=True)
        
        db = load_db()
        user_id = str(interaction.user.id)
        now = datetime.now()
        
        # ===== 24 SAAT KONTROLÜ (Key alma aralığı) =====
        if user_id in db["last_key_time"]:
            last_time = datetime.fromisoformat(db["last_key_time"][user_id])
            time_diff = now - last_time
            
            if time_diff < timedelta(hours=24):
                remaining = timedelta(hours=24) - time_diff
                hours = int(remaining.total_seconds() // 3600)
                minutes = int((remaining.total_seconds() % 3600) // 60)
                
                embed = discord.Embed(
                    title="⏳ WAIT!",
                    description=f"You can get a new key in **{hours}h {minutes}m**!",
                    color=discord.Color.orange()
                )
                await interaction.followup.send(embed=embed)
                return
        
        # ===== AKTIF LISANS KONTROLÜ (24 saat geçerli) =====
        if user_id in db["users"]:
            key_data = db["users"][user_id]
            expires = datetime.fromisoformat(key_data["expires"])
            if expires > now:
                embed = discord.Embed(
                    title="❌ You Already Have a License!",
                    description=f"Your key: `{key_data['key']}`\nExpires: {expires.strftime('%d.%m.%Y %H:%M')}",
                    color=discord.Color.orange()
                )
                await interaction.followup.send(embed=embed)
                return
        
        # ===== YENI KEY OLUŞTUR (1 GÜN GEÇERLİ) =====
        new_key = generate_key()
        expires = now + timedelta(days=1)  # 🔥 1 GÜN
        
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
        
        # ===== EPHEMERAL MESAJ =====
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
            value="Enter this key when the script asks for a license.",
            inline=False
        )
        embed.add_field(
            name="⏳ Next Key",
            value=f"{now.strftime('%d.%m.%Y %H:%M')} + 24 hours",
            inline=False
        )
        embed.set_footer(text="yigit script v5.0 | 1 key per 24h | 24h validity")
        embed.color = discord.Color.green()
        
        await interaction.followup.send(embed=embed)

# ======================================================================
# BOT
# ======================================================================
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
tree = bot.tree

@bot.event
async def on_ready():
    print(f'✅ Bot hazir! {bot.user}')
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="/keylist | Claim your 24h key!"
        )
    )
    try:
        await tree.sync()
        print("✅ Slash komutlar senkronize edildi!")
    except Exception as e:
        print(f"❌ Slash komut senkronizasyon hatasi: {e}")

# ======================================================================
# FORUM KANALI KOMUTU (Key Claim Mesajını Gönder)
# ======================================================================
@tree.command(name="keylist", description="Knife Duels key claim page (Admin)")
@app_commands.default_permissions(administrator=True)
async def slash_keylist(interaction: discord.Interaction):
    """Key claim sayfasını gönderir"""
    
    if not interaction.user.guild_permissions.administrator:
        embed = discord.Embed(
            title="❌ Permission Denied!",
            description="You need Admin permissions to use this command.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    embed = discord.Embed(
        title="🔑 KNIFE DUELS LICENSE KEY",
        description="Click the button below to claim your **Knife Duels** license key.\n\n"
                    "⚡ **1 key per 24 hours**\n"
                    "⏰ **24 hours validity**\n"
                    "🔒 **Your key is sent as a private message**\n\n"
                    "**✨ Features:**\n"
                    "• Auto Aim\n"
                    "• ESP & Glow\n"
                    "• Rage Mode\n"
                    "• Visual Effects\n"
                    "• And much more!",
        color=discord.Color.blue()
    )
    embed.set_footer(text="yigit script v5.0 | Knife Duels | 24h key")
    
    view = KeyClaimButton()
    
    await interaction.response.send_message(embed=embed, view=view)

# ======================================================================
# /KEY KOMUTU (Alternatif)
# ======================================================================
@tree.command(name="key", description="Get your 24h Knife Duels license key")
async def slash_key(interaction: discord.Interaction):
    """Yeni lisans anahtarı al - 24s 1 key, 1 gün geçerli"""
    
    await interaction.response.defer(ephemeral=True)
    
    db = load_db()
    user_id = str(interaction.user.id)
    now = datetime.now()
    
    # 24 saat kontrolü (key alma aralığı)
    if user_id in db["last_key_time"]:
        last_time = datetime.fromisoformat(db["last_key_time"][user_id])
        time_diff = now - last_time
        
        if time_diff < timedelta(hours=24):
            remaining = timedelta(hours=24) - time_diff
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            
            embed = discord.Embed(
                title="⏳ Wait!",
                description=f"You can get a new key in **{hours}h {minutes}m**!",
                color=discord.Color.orange()
            )
            await interaction.followup.send(embed=embed)
            return
    
    # Aktif lisans kontrolü (1 gün geçerli)
    if user_id in db["users"]:
        key_data = db["users"][user_id]
        expires = datetime.fromisoformat(key_data["expires"])
        if expires > now:
            embed = discord.Embed(
                title="❌ You Already Have a License!",
                description=f"Your key: `{key_data['key']}`\nExpires: {expires.strftime('%d.%m.%Y %H:%M')}",
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
        value="Enter this key when the script asks for a license.",
        inline=False
    )
    embed.add_field(
        name="⏳ Next Key",
        value=f"{now.strftime('%d.%m.%Y %H:%M')} + 24 hours",
        inline=False
    )
    embed.set_footer(text="yigit script v5.0 | 1 key per 24h | 24h validity")
    
    await interaction.followup.send(embed=embed)

# ======================================================================
# /KEYINFO KOMUTU
# ======================================================================
@tree.command(name="keyinfo", description="Check your 24h license key info")
async def slash_keyinfo(interaction: discord.Interaction):
    """Kendi lisans bilgilerini göster"""
    
    await interaction.response.defer(ephemeral=True)
    
    db = load_db()
    user_id = str(interaction.user.id)
    
    if user_id not in db["users"]:
        embed = discord.Embed(
            title="❌ No License Found!",
            description="You don't have a license key yet.\nUse `/key` or click the button to get one!",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    key_data = db["users"][user_id]
    expires = datetime.fromisoformat(key_data["expires"])
    is_expired = expires < datetime.now()
    
    # Kalan süreyi hesapla
    if not is_expired:
        remaining = expires - datetime.now()
        hours = int(remaining.total_seconds() // 3600)
        minutes = int((remaining.total_seconds() % 3600) // 60)
        time_left = f"{hours}h {minutes}m"
    else:
        time_left = "EXPIRED"
    
    embed = discord.Embed(
        title="🔑 Your License Info",
        color=discord.Color.red() if is_expired else discord.Color.green()
    )
    embed.add_field(name="Key", value=f"`{key_data['key']}`", inline=False)
    embed.add_field(name="Status", value="❌ Expired" if is_expired else "✅ Active", inline=True)
    embed.add_field(name="Time Left", value=time_left, inline=True)
    embed.add_field(name="Expires", value=expires.strftime('%d.%m.%Y %H:%M'), inline=True)
    
    await interaction.followup.send(embed=embed)

# ======================================================================
# ADMIN KOMUTLARI
# ======================================================================
@tree.command(name="admin_keylist", description="List all keys (Admin only)")
@app_commands.default_permissions(administrator=True)
async def admin_keylist(interaction: discord.Interaction):
    """Tüm lisansları listele"""
    
    await interaction.response.defer(ephemeral=True)
    
    if not interaction.user.guild_permissions.administrator:
        await interaction.followup.send("❌ Permission denied!", ephemeral=True)
        return
    
    db = load_db()
    if not db["keys"]:
        await interaction.followup.send("📭 No keys found!")
        return
    
    embed = discord.Embed(
        title="📊 License List (24h Keys)",
        color=discord.Color.blue()
    )
    
    active = 0
    expired = 0
    for key, data in list(db["keys"].items())[:15]:
        expires = datetime.fromisoformat(data["expires"])
        is_expired = expires < datetime.now()
        status = "✅" if not is_expired else "❌"
        if not is_expired:
            active += 1
        else:
            expired += 1
        
        try:
            user = await bot.fetch_user(int(data["user"]))
            username = user.name
        except:
            username = "Unknown"
        
        # Kalan süre
        if not is_expired:
            remaining = expires - datetime.now()
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            time_left = f"{hours}h {minutes}m"
        else:
            time_left = "EXPIRED"
        
        embed.add_field(
            name=f"{status} {key}",
            value=f"👤 {username}\n⏳ {time_left}\n📅 {expires.strftime('%d.%m %H:%M')}",
            inline=False
        )
    
    embed.set_footer(text=f"Total: {len(db['keys'])} | Active: {active} | Expired: {expired}")
    await interaction.followup.send(embed=embed)

@tree.command(name="admin_keycancel", description="Cancel a license (Admin only)")
@app_commands.default_permissions(administrator=True)
async def admin_keycancel(interaction: discord.Interaction, key: str):
    """Lisansı iptal et"""
    
    await interaction.response.defer(ephemeral=True)
    
    if not interaction.user.guild_permissions.administrator:
        await interaction.followup.send("❌ Permission denied!", ephemeral=True)
        return
    
    db = load_db()
    if key not in db["keys"]:
        await interaction.followup.send("❌ Invalid key!", ephemeral=True)
        return
    
    user_id = db["keys"][key]["user"]
    db["keys"][key]["used"] = True
    db["keys"][key]["expires"] = datetime.now().isoformat()
    if user_id in db["users"]:
        del db["users"][user_id]
    save_db(db)
    
    await interaction.followup.send(f"✅ `{key}` has been cancelled!", ephemeral=True)
    
    try:
        user = await bot.fetch_user(int(user_id))
        await user.send("❌ Your license key has been cancelled! Contact an admin.")
    except:
        pass

# ======================================================================
# BOT ÇALIŞTIR
# ======================================================================
if __name__ == "__main__":
    bot.run(TOKEN)
