import discord
from discord.ext import commands
import json
import random
import string
import os
from datetime import datetime, timedelta
import asyncio
from flask import Flask, request, jsonify
import threading
import psutil
import time

# ======================================================================
# WEB SUNUCUSU (Render için + API)
# ======================================================================
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Yigit Keys Bot çalışıyor!"

@app.route('/health')
def health():
    return "OK", 200

# ======================================================================
# API - KEY DOĞRULAMA (Script'ler için)
# ======================================================================
@app.route('/verify', methods=['POST'])
def verify_key():
    """Script'lerin key doğrulama API'si"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"valid": False, "error": "No data provided"}), 400
        
        key = data.get('key')
        hwid = data.get('hwid', 'unknown')
        
        if not key:
            return jsonify({"valid": False, "error": "No key provided"}), 400
        
        # Veritabanını yükle
        db = load_db()
        
        # Key var mı?
        if key not in db["keys"]:
            return jsonify({"valid": False, "error": "Invalid key"}), 200
        
        key_data = db["keys"][key]
        
        # Süresi dolmuş mu?
        expires = datetime.fromisoformat(key_data["expires"])
        if expires < datetime.now():
            return jsonify({"valid": False, "error": "Key expired"}), 200
        
        # HWID kontrolü (ilk kullanımda kaydeder)
        if "hwid" in key_data and key_data["hwid"] != hwid:
            return jsonify({"valid": False, "error": "Already used on another device"}), 200
        
        # İlk kullanımda HWID kaydet
        if "hwid" not in key_data:
            key_data["hwid"] = hwid
            save_db(db)
        
        return jsonify({
            "valid": True,
            "expires": key_data["expires"],
            "message": "License valid!"
        }), 200
        
    except Exception as e:
        return jsonify({"valid": False, "error": str(e)}), 500

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
STATUS_CHANNEL_ID = 1531992520547106930   # 🔥 Durum kanalı ID
CLICKED_ROLE_ID = 1531968801308938250     # 🔥 Clicked rolü ID
BOT_COMMAND_CHANNEL = 1531966775154180286 # 🔥 Bot komut kanalı ID

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
        embed.set_footer(text="yigit keys | Knife Duels")
        
        await interaction.followup.send(embed=embed, ephemeral=True)

# ======================================================================
# BOT
# ======================================================================
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix='y!', intents=intents, help_command=None)

# ======================================================================
# KANAL KONTROLÜ
# ======================================================================
def command_channel_only():
    async def predicate(ctx):
        if ctx.author.id == AUTHORIZED_USER_ID:
            return True
        if ctx.channel.id == BOT_COMMAND_CHANNEL:
            return True
        await ctx.send("❌ This channel is not a bot command channel! Please use <#1531966775154180286>", delete_after=5)
        return False
    return commands.check(predicate)

# ======================================================================
# DURUM MESAJI (5 DAKİKADA BİR)
# ======================================================================
async def status_message_loop():
    await bot.wait_until_ready()
    
    while not bot.is_closed():
        try:
            channel = bot.get_channel(STATUS_CHANNEL_ID)
            if not channel:
                print(f"❌ Durum kanalı bulunamadi! ID: {STATUS_CHANNEL_ID}")
                await asyncio.sleep(60)
                continue
            
            db = load_db()
            total_keys = len(db["keys"])
            active_keys = 0
            now = datetime.now()
            for key, data in db["keys"].items():
                if datetime.fromisoformat(data["expires"]) > now:
                    active_keys += 1
            
            expired_keys = total_keys - active_keys
            total_members = 0
            for guild in bot.guilds:
                total_members += guild.member_count or 0
            
            ping = round(bot.latency * 1000)
            uptime = time.time() - bot.uptime if hasattr(bot, 'uptime') else 0
            uptime_str = str(timedelta(seconds=int(uptime)))
            
            embed = discord.Embed(
                title="⚡ YIGIT KEYS",
                description="**Status:** 🟢 Online & Ready",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="📊 SERVER INFO",
                value=f"┌ 👥 Members: **{total_members}**\n"
                      f"├ 🔑 Keys Generated: **{total_keys}**\n"
                      f"├ ✅ Active Keys: **{active_keys}**\n"
                      f"└ ⏰ Expired Keys: **{expired_keys}**",
                inline=False
            )
            
            try:
                cpu = psutil.cpu_percent()
                ram = psutil.virtual_memory()
                ram_used = ram.used // (1024**3)
                ram_total = ram.total // (1024**3)
                
                embed.add_field(
                    name="💻 SYSTEM",
                    value=f"┌ 📡 Ping: **{ping}ms**\n"
                          f"├ ⏱️ Uptime: **{uptime_str}**\n"
                          f"├ 💻 CPU: **%{cpu}**\n"
                          f"└ 🧠 RAM: **{ram_used}GB / {ram_total}GB**",
                    inline=False
                )
            except:
                embed.add_field(
                    name="💻 SYSTEM",
                    value=f"┌ 📡 Ping: **{ping}ms**\n"
                          f"├ ⏱️ Uptime: **{uptime_str}**\n"
                          f"└ 💻 System info not available",
                    inline=False
                )
            
            embed.add_field(
                name="🎮 SCRIPTS",
                value="┌ **Knife Duel** — 🟢 Working\n"
                      "│  └ Key system active, claim your key!\n"
                      "├ **Coming Soon** — 🔜\n"
                      "└ **More scripts in development...**",
                inline=False
            )
            
            embed.add_field(
                name="🔗 HOW TO GET A KEY",
                value="Click **CLAIM KEY** button or use `y!key-info`",
                inline=False
            )
            
            embed.set_footer(text="yigit keys | knife duels | 24h keys")
            
            await channel.send(embed=embed)
            print(f"✅ Durum mesajı gönderildi: {datetime.now().strftime('%H:%M:%S')}")
            
        except Exception as e:
            print(f"❌ Durum mesajı hatasi: {e}")
        
        await asyncio.sleep(300)

# ======================================================================
# BOT STATUS DÖNGÜSÜ
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
                f"yigit keys | {total_keys} keys",
                f"Knife Duels | {active_keys} active",
                f"yigit keys | {total_members} users",
                "yigit keys | new scripts"
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
@bot.command(name='yardim')
@command_channel_only()
async def help_command(ctx):
    embed = discord.Embed(
        title="📋 YIGIT KEYS - COMMANDS",
        description="**Prefix:** `y!`\nAll commands must be used in <#1531966775154180286>",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="🎯 KEY & LICENSE",
        value=(
            "**y!knife-duel**\n"
            "└ Send Knife Duels key claim message with CLAIM KEY button\n\n"
            "**y!key-info**\n"
            "└ Check your Knife Duels license key information"
        ),
        inline=False
    )
    embed.add_field(
        name="👥 ACCESS & ROLES",
        value=(
            "**y!click-mesaj**\n"
            "└ Send access message with ✅ reaction to get clicked role"
        ),
        inline=False
    )
    embed.add_field(
        name="⚙️ ADMIN",
        value=(
            "**y!clear [amount]**\n"
            "└ Delete messages (max 100) - Admin only"
        ),
        inline=False
    )
    embed.add_field(
        name="ℹ️ INFO",
        value=(
            "**y!yardim**\n"
            "└ Show this help menu"
        ),
        inline=False
    )
    embed.add_field(
        name="📌 QUICK GUIDE",
        value=(
            "1️⃣ `y!click-mesaj` → React ✅ to get **clicked** role\n"
            "2️⃣ Access **#knife-duels-key** channel\n"
            "3️⃣ `y!knife-duel` → Click **CLAIM KEY**\n"
            "4️⃣ `y!key-info` → Check your license\n\n"
            "⚡ **1 key per 24 hours**\n"
            "⏰ **24 hours validity**"
        ),
        inline=False
    )
    embed.set_footer(text="yigit keys | knife duels | v5.0")
    await ctx.send(embed=embed)

@bot.command(name='knife-duel')
@command_channel_only()
async def send_knife_duel_key(ctx):
    if ctx.author.id != AUTHORIZED_USER_ID:
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
    embed.set_footer(text="yigit keys | Knife Duels | 24h keys")
    view = KeyClaimButton()
    await ctx.send(embed=embed, view=view)
    await ctx.send(f"✅ Knife Duels key message sent to this channel!")

@bot.command(name='click-mesaj')
@command_channel_only()
async def send_click_message(ctx):
    if ctx.author.id != AUTHORIZED_USER_ID:
        return
    
    role = ctx.guild.get_role(CLICKED_ROLE_ID)
    if not role:
        await ctx.send(f"❌ Role not found! ID: {CLICKED_ROLE_ID}")
        return
    
    embed = discord.Embed(
        title="🔪 KNIFE DUELS ACCESS",
        description=f"React with ✅ below to get the **{role.name}** role and access **Knife Duels** keys!",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="🎯 HOW TO GET ACCESS",
        value=(
            "**1.** React with ✅ below this message\n"
            f"**2.** You will receive the **{role.name}** role\n"
            "**3.** Access to **#knife-duels-key** channel\n"
            "**4.** Claim your Knife Duels key!\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "⚡ **1 key per 24 hours**\n"
            "⏰ **24 hours validity**\n"
            "🔒 **Private key delivery**"
        ),
        inline=False
    )
    embed.add_field(
        name="📌 HOW TO USE",
        value=(
            "1️⃣ Click ✅ reaction\n"
            f"2️⃣ Get **{role.name}** role\n"
            "3️⃣ Access **#knife-duels-key**\n"
            "4️⃣ Use `y!key-info`\n"
            "5️⃣ Click **CLAIM KEY**"
        ),
        inline=True
    )
    embed.set_footer(text=f"yigit keys | {role.name} | knife duels")
    
    message = await ctx.send(embed=embed)
    await message.add_reaction("✅")
    await ctx.send(f"✅ Knife Duels access message sent! React with ✅ to get the **{role.name}** role.")

@bot.command(name='key-info')
@command_channel_only()
async def key_info(ctx):
    db = load_db()
    user_id = str(ctx.author.id)
    
    if user_id not in db["users"]:
        embed = discord.Embed(
            title="❌ No License Found!",
            description="Click the **CLAIM KEY** button in the key channel to get your Knife Duels license!",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
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
    embed.set_footer(text="yigit keys | Knife Duels")
    
    await ctx.send(embed=embed)

@bot.command(name='clear')
@command_channel_only()
async def clear_messages(ctx, amount: int = 100):
    if ctx.author.id != AUTHORIZED_USER_ID:
        await ctx.send("❌ You don't have permission to use this command!")
        return
    
    if amount > 100:
        amount = 100
        await ctx.send("⚠️ Maximum 100 messages can be deleted at once.", delete_after=3)
    
    if amount < 1:
        await ctx.send("❌ Please specify a number greater than 0.", delete_after=3)
        return
    
    try:
        deleted = await ctx.channel.purge(limit=amount)
        await ctx.send(f"✅ Deleted **{len(deleted)}** messages!", delete_after=3)
        print(f"🗑️ {ctx.author.name} deleted {len(deleted)} messages in #{ctx.channel.name}")
        
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to delete messages!", delete_after=3)
    except discord.HTTPException as e:
        await ctx.send(f"❌ Failed to delete messages: {e}", delete_after=3)

# ======================================================================
# REAKSIYON OLAYI - EPHEMERAL
# ======================================================================
@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return
    
    if str(reaction.emoji) != "✅":
        return
    
    if reaction.message.author.id != bot.user.id:
        return
    
    if not reaction.message.embeds:
        return
    
    embed = reaction.message.embeds[0]
    if not embed.title or "KNIFE DUELS" not in embed.title.upper():
        return
    
    guild = reaction.message.guild
    if not guild:
        return
    
    member = guild.get_member(user.id)
    if not member:
        return
    
    role = guild.get_role(CLICKED_ROLE_ID)
    
    if not role:
        try:
            role = await guild.create_role(
                name="clicked",
                color=discord.Color.green(),
                reason="Knife Duels access role"
            )
            print(f"✅ 'clicked' rolü oluşturuldu! ID: {role.id}")
        except Exception as e:
            print(f"❌ Rol oluşturma hatası: {e}")
            return
    
    if role in member.roles:
        embed_already = discord.Embed(
            title="ℹ️ ALREADY HAVE ACCESS",
            description=f"You already have the **{role.name}** role!\n\n"
                        f"🔑 Access **#knife-duels-key** channel for your key.",
            color=discord.Color.blue()
        )
        embed_already.set_footer(text="yigit keys | knife duels")
        await reaction.message.channel.send(embed=embed_already, ephemeral=True)
        return
    
    try:
        await member.add_roles(role)
        print(f"✅ {user.name} - {role.name} rolü verildi!")
        
        embed_success = discord.Embed(
            title="✅ ROLE GRANTED!",
            description=f"You have been given the **{role.name}** role!",
            color=discord.Color.green()
        )
        embed_success.add_field(
            name="📋 WHAT NOW?",
            value=(
                f"🔑 Go to **#knife-duels-key** channel\n"
                f"🎯 Click **CLAIM KEY** to get your 24h key\n"
                f"📌 Use `y!key-info` to check your license\n\n"
                f"⚡ **1 key per 24 hours**\n"
                f"⏰ **24 hours validity**"
            ),
            inline=False
        )
        embed_success.set_footer(text="yigit keys | knife duels")
        
        await reaction.message.channel.send(embed=embed_success, ephemeral=True)
        print(f"✅ {user.name} - Ephemeral rol bildirimi gönderildi!")
            
    except Exception as e:
        print(f"❌ Rol verme hatası: {e}")
        embed_error = discord.Embed(
            title="❌ ERROR",
            description=f"Could not give you the **{role.name}** role. Please contact an admin.",
            color=discord.Color.red()
        )
        await reaction.message.channel.send(embed=embed_error, ephemeral=True)

# ======================================================================
# BOT ÇALIŞTIR
# ======================================================================
@bot.event
async def on_ready():
    print(f'✅ Bot ready! {bot.user}')
    print(f'📊 {len(bot.guilds)} servers active')
    for guild in bot.guilds:
        print(f'📌 {guild.name} - {guild.member_count} members')
    
    bot.uptime = time.time()
    
    bot.loop.create_task(status_loop())
    bot.loop.create_task(status_message_loop())
    
    try:
        await bot.tree.sync()
        print("✅ Slash commands synced!")
    except Exception as e:
        print(f"❌ Sync error: {e}")

if __name__ == "__main__":
    print("🔪 Yigit Keys Bot starting...")
    bot.run(TOKEN)
