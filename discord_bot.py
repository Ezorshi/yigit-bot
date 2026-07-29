import discord
from discord.ext import commands
import json
import random
import string
import os
from datetime import datetime, timedelta

# ======================================================================
# TOKEN - RENDER ENV'DEN ALINACAK
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
        return {"keys": {}, "users": {}}

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

@bot.event
async def on_ready():
    print(f'✅ Bot hazir! {bot.user}')
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="!key al | yigit script"
        )
    )

# ======================================================================
# KOMUTLAR
# ======================================================================

@bot.command(name='key')
async def get_key(ctx):
    db = load_db()
    user_id = str(ctx.author.id)
    
    if user_id in db["users"]:
        key_data = db["users"][user_id]
        expires = datetime.fromisoformat(key_data["expires"])
        if expires > datetime.now():
            embed = discord.Embed(
                title="❌ Zaten Lisansiniz Var!",
                description=f"Lisans anahtariniz: `{key_data['key']}`\nSuresi: {expires.strftime('%d.%m.%Y %H:%M')}",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            return
    
    new_key = generate_key()
    expires = datetime.now() + timedelta(days=30)
    
    db["keys"][new_key] = {
        "user": user_id,
        "created": datetime.now().isoformat(),
        "expires": expires.isoformat(),
        "used": False
    }
    db["users"][user_id] = {
        "key": new_key,
        "expires": expires.isoformat()
    }
    save_db(db)
    
    try:
        embed = discord.Embed(
            title="🔑 YIGIT SCRIPT LISANS ANAHTARI",
            description=f"```\n{new_key}\n```",
            color=discord.Color.green()
        )
        embed.add_field(
            name="📅 Gecerlilik Suresi",
            value=f"30 gun (Son: {expires.strftime('%d.%m.%Y')})",
            inline=False
        )
        embed.add_field(
            name="📝 Nasil Kullanilir?",
            value="Script'i calistirdiginda acilan lisansa bu anahtari gir.",
            inline=False
        )
        embed.set_footer(text="yigit script v5.0 premium")
        
        await ctx.author.send(embed=embed)
        await ctx.send("✅ Lisans anahtari DM olarak gonderildi!")
    except:
        await ctx.send("❌ DM gonderilemedi! DM'lerinizi acin.")

@bot.command(name='keyinfo')
async def key_info(ctx, key: str = None):
    if not key:
        await ctx.send("❌ Kullanim: !keyinfo YIGIT-XXXX-XXXX-XXXX")
        return
    
    db = load_db()
    if key not in db["keys"]:
        await ctx.send("❌ Gecersiz lisans anahtari!")
        return
    
    key_data = db["keys"][key]
    expires = datetime.fromisoformat(key_data["expires"])
    is_expired = expires < datetime.now()
    
    embed = discord.Embed(
        title="🔑 Lisans Bilgisi",
        color=discord.Color.red() if is_expired else discord.Color.green()
    )
    embed.add_field(name="Anahtar", value=f"`{key}`", inline=False)
    embed.add_field(name="Durum", value="❌ Suresi Doldu" if is_expired else "✅ Aktif", inline=True)
    embed.add_field(name="Sure", value=expires.strftime('%d.%m.%Y %H:%M'), inline=True)
    
    await ctx.send(embed=embed)

# ======================================================================
# BOT CALISTIR
# ======================================================================
if __name__ == "__main__":
    bot.run(TOKEN)
