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
            name="/key | 24s 1 key"
        )
    )
    try:
        await tree.sync()
        print("✅ Slash komutlar senkronize edildi!")
    except Exception as e:
        print(f"❌ Slash komut senkronizasyon hatasi: {e}")

# ======================================================================
# SLASH KOMUTLAR
# ======================================================================

@tree.command(name="key", description="Yeni lisans anahtari al (24s 1 key)")
async def slash_key(interaction: discord.Interaction):
    """Yeni lisans anahtarı al - 24 saatte 1 key"""
    
    await interaction.response.defer(ephemeral=True)
    
    db = load_db()
    user_id = str(interaction.user.id)
    now = datetime.now()
    
    # ===== 24 SAAT KONTROLÜ =====
    if user_id in db["last_key_time"]:
        last_time = datetime.fromisoformat(db["last_key_time"][user_id])
        time_diff = now - last_time
        
        if time_diff < timedelta(hours=24):
            remaining = timedelta(hours=24) - time_diff
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            
            embed = discord.Embed(
                title="⏳ Bekle!",
                description=f"**{hours} saat {minutes} dakika** sonra tekrar key alabilirsin!",
                color=discord.Color.orange()
            )
            embed.add_field(
                name="📅 Son Key Alma",
                value=last_time.strftime('%d.%m.%Y %H:%M'),
                inline=False
            )
            await interaction.followup.send(embed=embed)
            return
    
    # ===== KULLANICININ AKTİF KEY'İ VAR MI? =====
    if user_id in db["users"]:
        key_data = db["users"][user_id]
        expires = datetime.fromisoformat(key_data["expires"])
        if expires > now:
            embed = discord.Embed(
                title="❌ Zaten Lisansiniz Var!",
                description=f"Lisans anahtariniz: `{key_data['key']}`\nSüresi: {expires.strftime('%d.%m.%Y %H:%M')}",
                color=discord.Color.orange()
            )
            embed.add_field(
                name="⏳ Key Alma",
                value="Aktif lisansın varken yeni key alamazsın!",
                inline=False
            )
            await interaction.followup.send(embed=embed)
            return
    
    # ===== YENİ KEY OLUŞTUR =====
    new_key = generate_key()
    expires = now + timedelta(days=30)
    
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
    
    # ===== GİZLİ MESAJ GÖNDER =====
    embed = discord.Embed(
        title="🔑 YIGIT SCRIPT LISANS ANAHTARI",
        description=f"```\n{new_key}\n```",
        color=discord.Color.green()
    )
    embed.add_field(
        name="📅 Geçerlilik Süresi",
        value=f"30 gün (Son: {expires.strftime('%d.%m.%Y')})",
        inline=False
    )
    embed.add_field(
        name="📝 Nasil Kullanilir?",
        value="Script'i çalistirdiginda açilan lisansa bu anahtari gir.",
        inline=False
    )
    embed.add_field(
        name="⏳ Sonraki Key",
        value=f"{now.strftime('%d.%m.%Y %H:%M')} + 24 saat",
        inline=False
    )
    embed.set_footer(text="yigit script v5.0 premium | 24s 1 key")
    
    await interaction.followup.send(embed=embed)


@tree.command(name="keyinfo", description="Lisans bilgilerini göster")
async def slash_keyinfo(interaction: discord.Interaction, key: str):
    """Lisans bilgilerini göster"""
    
    await interaction.response.defer(ephemeral=True)
    
    db = load_db()
    if key not in db["keys"]:
        embed = discord.Embed(
            title="❌ Geçersiz Lisans",
            description="Bu lisans anahtarı geçerli değil!",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    key_data = db["keys"][key]
    expires = datetime.fromisoformat(key_data["expires"])
    is_expired = expires < datetime.now()
    created = datetime.fromisoformat(key_data["created"])
    
    embed = discord.Embed(
        title="🔑 Lisans Bilgisi",
        color=discord.Color.red() if is_expired else discord.Color.green()
    )
    embed.add_field(name="Anahtar", value=f"`{key}`", inline=False)
    embed.add_field(name="Durum", value="❌ Süresi Doldu" if is_expired else "✅ Aktif", inline=True)
    embed.add_field(name="Oluşturulma", value=created.strftime('%d.%m.%Y %H:%M'), inline=True)
    embed.add_field(name="Son Kullanım", value=expires.strftime('%d.%m.%Y %H:%M'), inline=True)
    
    await interaction.followup.send(embed=embed)


@tree.command(name="keylist", description="Tüm lisansları listele (Sadece Admin)")
@app_commands.default_permissions(administrator=True)
async def slash_keylist(interaction: discord.Interaction):
    """Tüm lisansları listele"""
    
    await interaction.response.defer(ephemeral=True)
    
    if not interaction.user.guild_permissions.administrator:
        embed = discord.Embed(
            title="❌ Yetki Yok!",
            description="Bu komutu kullanmak için Admin yetkin olmalı!",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    db = load_db()
    if not db["keys"]:
        embed = discord.Embed(
            title="📭 Lisans Listesi",
            description="Henüz oluşturulmuş lisans yok!",
            color=discord.Color.blue()
        )
        await interaction.followup.send(embed=embed)
        return
    
    embed = discord.Embed(
        title="📊 Lisans Listesi",
        color=discord.Color.blue()
    )
    
    active = 0
    expired = 0
    for key, data in list(db["keys"].items())[:10]:
        expires = datetime.fromisoformat(data["expires"])
        status = "✅" if expires > datetime.now() else "❌"
        if expires > datetime.now():
            active += 1
        else:
            expired += 1
        
        try:
            user = await bot.fetch_user(int(data["user"]))
            username = user.name
        except:
            username = "Bilinmeyen"
        
        created = datetime.fromisoformat(data["created"])
        embed.add_field(
            name=f"{status} {key}",
            value=f"👤 {username}\n📅 {created.strftime('%d.%m')} → {expires.strftime('%d.%m.%Y')}",
            inline=False
        )
    
    embed.set_footer(text=f"Toplam: {len(db['keys'])} | Aktif: {active} | Süresi Dolan: {expired}")
    await interaction.followup.send(embed=embed)


@tree.command(name="keycancel", description="Lisansı iptal et (Sadece Admin)")
@app_commands.default_permissions(administrator=True)
async def slash_keycancel(interaction: discord.Interaction, key: str):
    """Lisansı iptal et"""
    
    await interaction.response.defer(ephemeral=True)
    
    if not interaction.user.guild_permissions.administrator:
        embed = discord.Embed(
            title="❌ Yetki Yok!",
            description="Bu komutu kullanmak için Admin yetkin olmalı!",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    db = load_db()
    if key not in db["keys"]:
        embed = discord.Embed(
            title="❌ Geçersiz Lisans",
            description="Bu lisans anahtarı geçerli değil!",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    user_id = db["keys"][key]["user"]
    db["keys"][key]["used"] = True
    db["keys"][key]["expires"] = datetime.now().isoformat()
    if user_id in db["users"]:
        del db["users"][user_id]
    save_db(db)
    
    embed = discord.Embed(
        title="✅ Lisans İptal Edildi",
        description=f"`{key}` anahtarı başarıyla iptal edildi!",
        color=discord.Color.green()
    )
    await interaction.followup.send(embed=embed)
    
    try:
        user = await bot.fetch_user(int(user_id))
        await user.send("❌ Lisans anahtarınız iptal edildi! Yetkili ile iletişime geçin.")
    except:
        pass


@tree.command(name="keystats", description="Lisans istatistikleri (Sadece Admin)")
@app_commands.default_permissions(administrator=True)
async def slash_keystats(interaction: discord.Interaction):
    """Lisans istatistikleri"""
    
    await interaction.response.defer(ephemeral=True)
    
    if not interaction.user.guild_permissions.administrator:
        embed = discord.Embed(
            title="❌ Yetki Yok!",
            description="Bu komutu kullanmak için Admin yetkin olmalı!",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    db = load_db()
    total = len(db["keys"])
    active = 0
    used = 0
    
    for key, data in db["keys"].items():
        expires = datetime.fromisoformat(data["expires"])
        if expires > datetime.now():
            active += 1
        if data["used"]:
            used += 1
    
    embed = discord.Embed(
        title="📊 Lisans İstatistikleri",
        color=discord.Color.gold()
    )
    embed.add_field(name="Toplam Anahtar", value=str(total), inline=True)
    embed.add_field(name="Aktif Anahtar", value=str(active), inline=True)
    embed.add_field(name="Kullanılan", value=str(used), inline=True)
    embed.add_field(name="Kullanılmayan", value=str(total - used), inline=True)
    embed.add_field(name="Süresi Dolan", value=str(total - active), inline=True)
    
    await interaction.followup.send(embed=embed)

# ======================================================================
# ESKİ KOMUTLAR
# ======================================================================

@bot.command(name='key')
async def old_get_key(ctx):
    """Eski !key komutu - Günlük limit ile"""
    db = load_db()
    user_id = str(ctx.author.id)
    now = datetime.now()
    
    # 24 saat kontrolü
    if user_id in db["last_key_time"]:
        last_time = datetime.fromisoformat(db["last_key_time"][user_id])
        time_diff = now - last_time
        if time_diff < timedelta(hours=24):
            remaining = timedelta(hours=24) - time_diff
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            await ctx.send(f"⏳ **{hours} saat {minutes} dakika** sonra tekrar key alabilirsin!")
            return
    
    if user_id in db["users"]:
        key_data = db["users"][user_id]
        expires = datetime.fromisoformat(key_data["expires"])
        if expires > now:
            await ctx.send(f"❌ Zaten lisansın var! !keyinfo {key_data['key']} ile kontrol et.")
            return
    
    new_key = generate_key()
    expires = now + timedelta(days=30)
    
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
    
    try:
        embed = discord.Embed(
            title="🔑 YIGIT SCRIPT LISANS ANAHTARI",
            description=f"```\n{new_key}\n```",
            color=discord.Color.green()
        )
        embed.add_field(
            name="📅 Geçerlilik Süresi",
            value=f"30 gün (Son: {expires.strftime('%d.%m.%Y')})",
            inline=False
        )
        embed.add_field(
            name="⏳ Sonraki Key",
            value=f"{now.strftime('%d.%m.%Y %H:%M')} + 24 saat",
            inline=False
        )
        await ctx.author.send(embed=embed)
        await ctx.send("✅ Lisans anahtarı DM olarak gönderildi!")
    except:
        await ctx.send("❌ DM gönderilemedi! DM'lerini aç veya /key kullan.")

@bot.command(name='keyinfo')
async def old_key_info(ctx, key: str = None):
    if not key:
        await ctx.send("❌ Kullanım: !keyinfo YIGIT-XXXX-XXXX-XXXX")
        return
    
    db = load_db()
    if key not in db["keys"]:
        await ctx.send("❌ Geçersiz lisans anahtarı!")
        return
    
    key_data = db["keys"][key]
    expires = datetime.fromisoformat(key_data["expires"])
    is_expired = expires < datetime.now()
    
    embed = discord.Embed(
        title="🔑 Lisans Bilgisi",
        color=discord.Color.red() if is_expired else discord.Color.green()
    )
    embed.add_field(name="Anahtar", value=f"`{key}`", inline=False)
    embed.add_field(name="Durum", value="❌ Süresi Doldu" if is_expired else "✅ Aktif", inline=True)
    embed.add_field(name="Süre", value=expires.strftime('%d.%m.%Y %H:%M'), inline=True)
    
    await ctx.send(embed=embed)

# ======================================================================
# BOT ÇALIŞTIR
# ======================================================================
if __name__ == "__main__":
    bot.run(TOKEN)
