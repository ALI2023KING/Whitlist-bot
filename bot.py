
import discord
from discord import app_commands
import os
import requests
import base64
import json
from datetime import datetime, timedelta

TOKEN = os.environ.get("TOKEN")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
OWNER_ID = 1449777458218926243

GITHUB_REPO = "ALI2023KING/Whitlist-sys"
GITHUB_FILE = "whitelist.txt"
BAN_FILE = "banlist.txt"
LOG_CHANNEL_ID = None
VOICE_CHANNEL_ID = None

cooldowns = {}
COOLDOWN_SECONDS = 3
START_TIME = datetime.utcnow()

if not TOKEN:
    print("ERROR: No token found!")
    exit(1)

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

BANNER_URL = "https://i.imgur.com/4QbKf2Q.png"

COLORS = {
    "success": 0x00FF7F,
    "error": 0xFF0000,
    "warning": 0xFFCC00,
    "info": 0x5865F2,
    "ban": 0xFF4500,
    "purple": 0x9B59B6,
    "blue": 0x00BFFF
}

def is_on_cooldown(user_id):
    if user_id in cooldowns:
        if datetime.utcnow() < cooldowns[user_id]:
            return True
    cooldowns[user_id] = datetime.utcnow() + timedelta(seconds=COOLDOWN_SECONDS)
    return False

def get_github_file(filename):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{filename}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 404:
        return [], None, ""
    data = r.json()
    content = base64.b64decode(data["content"]).decode("utf-8")
    sha = data["sha"]
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    return lines, sha, content

def update_github_file(filename, new_content, sha):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{filename}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    encoded = base64.b64encode(new_content.encode("utf-8")).decode("utf-8")
    if sha:
        payload = {"message": f"Updated {filename}", "content": encoded, "sha": sha}
    else:
        payload = {"message": f"Created {filename}", "content": encoded}
    requests.put(url, headers=headers, data=json.dumps(payload))

def get_roblox_avatar(user_id):
    try:
        url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=150x150&format=Png&isCircular=false"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=5)
        data = r.json()
        if "data" in data and len(data["data"]) > 0:
            image_url = data["data"][0].get("imageUrl", "")
            if image_url and image_url.startswith("http"):
                return image_url
    except:
        pass
    return None

def get_roblox_user_by_username(username):
    try:
        url = "https://users.roblox.com/v1/usernames/users"
        headers = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}
        payload = {"usernames": [username], "excludeBannedUsers": False}
        r = requests.post(url, headers=headers, json=payload, timeout=5)
        data = r.json()
        if "data" in data and len(data["data"]) > 0:
            return str(data["data"][0]["id"]), data["data"][0]["name"]
    except:
        pass
    return None, None

def get_roblox_username(user_id):
    try:
        url = f"https://users.roblox.com/v1/users/{user_id}"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=5)
        data = r.json()
        return data.get("name", None)
    except:
        pass
    return None

def parse_entry(line):
    parts = line.split("|")
    user_id = parts[0].strip()
    date = parts[1].strip() if len(parts) > 1 else "Unknown"
    username = parts[2].strip() if len(parts) > 2 else None
    return user_id, date, username

def get_ids_only(lines):
    return [parse_entry(line)[0] for line in lines if not line.startswith("--")]

async def send_log(embed):
    if LOG_CHANNEL_ID:
        channel = client.get_channel(LOG_CHANNEL_ID)
        if channel:
            await channel.send(embed=embed)

async def play_voice_announcement(guild, message_text):
    if VOICE_CHANNEL_ID:
        channel = guild.get_channel(VOICE_CHANNEL_ID)
        if channel:
            try:
                vc = await channel.connect()
                await discord.utils.sleep_until(datetime.utcnow() + timedelta(seconds=1))
                await vc.disconnect()
            except:
                pass

def owner_only(interaction):
    return interaction.user.id == OWNER_ID

@client.event
async def on_ready():
    await tree.sync()
    await client.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="👑 Whitelist System"
        )
    )
    print(f"Bot is online as {client.user}")

# =============================================
#   SLASH COMMANDS
# =============================================

@tree.command(name="add", description="Add a Roblox user to the whitelist by username")
@app_commands.describe(username="Roblox username to whitelist")
async def add_user(interaction: discord.Interaction, username: str):
    if not owner_only(interaction):
        embed = discord.Embed(title="🚫 Access Denied", description="Only the owner can use this.", color=COLORS["error"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    if is_on_cooldown(interaction.user.id):
        embed = discord.Embed(title="⏳ Cooldown", description=f"Wait {COOLDOWN_SECONDS} seconds.", color=COLORS["warning"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    await interaction.response.defer()
    user_id, roblox_name = get_roblox_user_by_username(username)
    if not user_id:
        embed = discord.Embed(title="❌ User Not Found", description=f"Could not find **{username}** on Roblox.", color=COLORS["error"])
        await interaction.followup.send(embed=embed)
        return
    lines, sha, content = get_github_file(GITHUB_FILE)
    ids = get_ids_only(lines)
    ban_lines, _, _ = get_github_file(BAN_FILE)
    ban_ids = get_ids_only(ban_lines)
    if user_id in ban_ids:
        embed = discord.Embed(title="🔨 User is Banned", description=f"**{roblox_name}** is banned and cannot be whitelisted.", color=COLORS["error"])
        await interaction.followup.send(embed=embed)
        return
    if user_id in ids:
        embed = discord.Embed(title="⚠️ Already Whitelisted", description=f"**{roblox_name}** is already whitelisted.", color=COLORS["warning"])
        await interaction.followup.send(embed=embed)
        return
    date = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    new_entry = f"{user_id} | {date} | {roblox_name}"
    new_content = content.strip() + f"\n{new_entry}"
    update_github_file(GITHUB_FILE, new_content, sha)
    avatar = get_roblox_avatar(user_id)
    embed = discord.Embed(
        title="✅ User Whitelisted",
        description=f"**Username:** {roblox_name}\n**User ID:** `{user_id}`\n**Added on:** {date} UTC",
        color=COLORS["success"]
    )
    embed.add_field(name="Total Users", value=str(len(ids) + 1), inline=True)
    embed.add_field(name="GitHub", value="✅ Updated", inline=True)
    if avatar:
        embed.set_thumbnail(url=avatar)
    embed.set_footer(text="Whitelist Bot • GitHub updated")
    embed.timestamp = datetime.utcnow()
    await interaction.followup.send(embed=embed)
    await send_log(embed)
    if interaction.guild:
        await play_voice_announcement(interaction.guild, f"{roblox_name} has been whitelisted")

@tree.command(name="remove", description="Remove a Roblox user from the whitelist by username")
@app_commands.describe(username="Roblox username to remove")
async def remove_user(interaction: discord.Interaction, username: str):
    if not owner_only(interaction):
        embed = discord.Embed(title="🚫 Access Denied", description="Only the owner can use this.", color=COLORS["error"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    if is_on_cooldown(interaction.user.id):
        embed = discord.Embed(title="⏳ Cooldown", description=f"Wait {COOLDOWN_SECONDS} seconds.", color=COLORS["warning"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    await interaction.response.defer()
    user_id, roblox_name = get_roblox_user_by_username(username)
    if not user_id:
        embed = discord.Embed(title="❌ User Not Found", description=f"Could not find **{username}** on Roblox.", color=COLORS["error"])
        await interaction.followup.send(embed=embed)
        return
    lines, sha, content = get_github_file(GITHUB_FILE)
    ids = get_ids_only(lines)
    if user_id not in ids:
        embed = discord.Embed(title="❌ Not Found", description=f"**{roblox_name}** is not in the whitelist.", color=COLORS["error"])
        await interaction.followup.send(embed=embed)
        return
    new_lines = [line for line in lines if not line.startswith(user_id)]
    update_github_file(GITHUB_FILE, "\n".join(new_lines), sha)
    avatar = get_roblox_avatar(user_id)
    embed = discord.Embed(
        title="🗑️ User Removed",
        description=f"**Username:** {roblox_name}\n**User ID:** `{user_id}`\nRemoved from whitelist.",
        color=COLORS["ban"]
    )
    embed.add_field(name="Total Users", value=str(len(ids) - 1), inline=True)
    embed.add_field(name="GitHub", value="✅ Updated", inline=True)
    if avatar:
        embed.set_thumbnail(url=avatar)
    embed.set_footer(text="Whitelist Bot • GitHub updated")
    embed.timestamp = datetime.utcnow()
    await interaction.followup.send(embed=embed)
    await send_log(embed)

@tree.command(name="check", description="Check if a Roblox user is whitelisted")
@app_commands.describe(username="Roblox username to check")
async def check_user(interaction: discord.Interaction, username: str):
    if not owner_only(interaction):
        embed = discord.Embed(title="🚫 Access Denied", description="Only the owner can use this.", color=COLORS["error"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    await interaction.response.defer()
    user_id, roblox_name = get_roblox_user_by_username(username)
    if not user_id:
        embed = discord.Embed(title="❌ User Not Found", description=f"Could not find **{username}** on Roblox.", color=COLORS["error"])
        await interaction.followup.send(embed=embed)
        return
    lines, _, _ = get_github_file(GITHUB_FILE)
    ban_lines, _, _ = get_github_file(BAN_FILE)
    ban_ids = get_ids_only(ban_lines)
    found = None
    for line in lines:
        if line.startswith(user_id):
            found = line
            break
    avatar = get_roblox_avatar(user_id)
    if user_id in ban_ids:
        embed = discord.Embed(title="🔨 User is Banned", description=f"**Username:** {roblox_name}\n**User ID:** `{user_id}`\nThis user is banned.", color=COLORS["error"])
    elif found:
        uid, date, uname = parse_entry(found)
        embed = discord.Embed(title="✅ User is Whitelisted", description=f"**Username:** {roblox_name}\n**User ID:** `{user_id}`\n**Added on:** {date} UTC", color=COLORS["success"])
    else:
        embed = discord.Embed(title="❌ Not Whitelisted", description=f"**Username:** {roblox_name}\n**User ID:** `{user_id}`\nThis user does not have access.", color=COLORS["ban"])
    if avatar:
        embed.set_thumbnail(url=avatar)
    embed.set_footer(text="Whitelist Bot")
    embed.timestamp = datetime.utcnow()
    await interaction.followup.send(embed=embed)

@tree.command(name="ban", description="Ban a Roblox user by username")
@app_commands.describe(username="Roblox username to ban")
async def ban_user(interaction: discord.Interaction, username: str):
    if not owner_only(interaction):
        embed = discord.Embed(title="🚫 Access Denied", description="Only the owner can use this.", color=COLORS["error"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    await interaction.response.defer()
    user_id, roblox_name = get_roblox_user_by_username(username)
    if not user_id:
        embed = discord.Embed(title="❌ User Not Found", description=f"Could not find **{username}** on Roblox.", color=COLORS["error"])
        await interaction.followup.send(embed=embed)
        return
    ban_lines, ban_sha, ban_content = get_github_file(BAN_FILE)
    ban_ids = get_ids_only(ban_lines)
    if user_id in ban_ids:
        embed = discord.Embed(title="⚠️ Already Banned", description=f"**{roblox_name}** is already banned.", color=COLORS["warning"])
        await interaction.followup.send(embed=embed)
        return
    lines, sha, content = get_github_file(GITHUB_FILE)
    ids = get_ids_only(lines)
    if user_id in ids:
        new_lines = [line for line in lines if not line.startswith(user_id)]
        update_github_file(GITHUB_FILE, "\n".join(new_lines), sha)
    date = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    new_ban = ban_content.strip() + f"\n{user_id} | {date} | {roblox_name}"
    update_github_file(BAN_FILE, new_ban, ban_sha)
    avatar = get_roblox_avatar(user_id)
    embed = discord.Embed(
        title="🔨 User Banned",
        description=f"**Username:** {roblox_name}\n**User ID:** `{user_id}`\nBanned and removed from whitelist.",
        color=COLORS["error"]
    )
    if avatar:
        embed.set_thumbnail(url=avatar)
    embed.set_footer(text="Whitelist Bot • GitHub updated")
    embed.timestamp = datetime.utcnow()
    await interaction.followup.send(embed=embed)
    await send_log(embed)

@tree.command(name="unban", description="Unban a Roblox user by username")
@app_commands.describe(username="Roblox username to unban")
async def unban_user(interaction: discord.Interaction, username: str):
    if not owner_only(interaction):
        embed = discord.Embed(title="🚫 Access Denied", description="Only the owner can use this.", color=COLORS["error"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    await interaction.response.defer()
    user_id, roblox_name = get_roblox_user_by_username(username)
    if not user_id:
        embed = discord.Embed(title="❌ User Not Found", description=f"Could not find **{username}** on Roblox.", color=COLORS["error"])
        await interaction.followup.send(embed=embed)
        return
    ban_lines, ban_sha, ban_content = get_github_file(BAN_FILE)
    ban_ids = get_ids_only(ban_lines)
    if user_id not in ban_ids:
        embed = discord.Embed(title="❌ Not Banned", description=f"**{roblox_name}** is not in the ban list.", color=COLORS["error"])
        await interaction.followup.send(embed=embed)
        return
    new_lines = [line for line in ban_lines if not line.startswith(user_id)]
    update_github_file(BAN_FILE, "\n".join(new_lines), ban_sha)
    embed = discord.Embed(title="✅ User Unbanned", description=f"**{roblox_name}** has been removed from the ban list.", color=COLORS["success"])
    embed.timestamp = datetime.utcnow()
    await interaction.followup.send(embed=embed)

@tree.command(name="list", description="Show all whitelisted users with their profile pictures")
async def list_users(interaction: discord.Interaction):
    if not owner_only(interaction):
        embed = discord.Embed(title="🚫 Access Denied", description="Only the owner can use this.", color=COLORS["error"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    await interaction.response.defer()
    lines, _, _ = get_github_file(GITHUB_FILE)
    ban_lines, _, _ = get_github_file(BAN_FILE)
    entries = [line for line in lines if not line.startswith("--")]
    ban_entries = [line for line in ban_lines if not line.startswith("--")]
    if not entries:
        embed = discord.Embed(title="📋 Whitelist", description="The whitelist is currently empty.", color=COLORS["info"])
        embed.set_footer(text="Whitelist Bot • Powered by GitHub")
        embed.timestamp = datetime.utcnow()
        await interaction.followup.send(embed=embed)
        return
    embed = discord.Embed(title="📋 Whitelist", color=COLORS["info"])
    embed.set_footer(text="Whitelist Bot • Powered by GitHub")
    embed.timestamp = datetime.utcnow()
    embed.add_field(name="✅ Whitelisted", value=str(len(entries)), inline=True)
    embed.add_field(name="🔨 Banned", value=str(len(ban_entries)), inline=True)
    desc = ""
    for line in entries:
        uid, date, uname = parse_entry(line)
        name = uname if uname else uid
        desc += f"• **{name}** — added {date}\n"
    embed.description = desc
    if entries:
        first_uid, _, _ = parse_entry(entries[0])
        avatar = get_roblox_avatar(first_uid)
        if avatar:
            embed.set_thumbnail(url=avatar)
    await interaction.followup.send(embed=embed)

@tree.command(name="banlist", description="Show all banned users")
async def ban_list(interaction: discord.Interaction):
    if not owner_only(interaction):
        embed = discord.Embed(title="🚫 Access Denied", description="Only the owner can use this.", color=COLORS["error"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    await interaction.response.defer()
    ban_lines, _, _ = get_github_file(BAN_FILE)
    entries = [line for line in ban_lines if not line.startswith("--")]
    if not entries:
        embed = discord.Embed(title="🔨 Ban List", description="No banned users.", color=COLORS["error"])
    else:
        desc = ""
        for line in entries:
            uid, date, uname = parse_entry(line)
            name = uname if uname else uid
            desc += f"• **{name}** — banned {date}\n"
        embed = discord.Embed(title="🔨 Ban List", description=desc, color=COLORS["error"])
        embed.add_field(name="Total Banned", value=str(len(entries)), inline=True)
    embed.set_footer(text="Whitelist Bot")
    embed.timestamp = datetime.utcnow()
    await interaction.followup.send(embed=embed)

@tree.command(name="rename", description="Update a user's Roblox username in the whitelist")
@app_commands.describe(old_username="Current username", new_username="New username")
async def rename_user(interaction: discord.Interaction, old_username: str, new_username: str):
    if not owner_only(interaction):
        embed = discord.Embed(title="🚫 Access Denied", description="Only the owner can use this.", color=COLORS["error"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    await interaction.response.defer()
    old_id, old_name = get_roblox_user_by_username(old_username)
    new_id, new_name = get_roblox_user_by_username(new_username)
    if not old_id:
        embed = discord.Embed(title="❌ Not Found", description=f"Could not find **{old_username}** on Roblox.", color=COLORS["error"])
        await interaction.followup.send(embed=embed)
        return
    lines, sha, content = get_github_file(GITHUB_FILE)
    ids = get_ids_only(lines)
    if old_id not in ids:
        embed = discord.Embed(title="❌ Not Whitelisted", description=f"**{old_name}** is not in the whitelist.", color=COLORS["error"])
        await interaction.followup.send(embed=embed)
        return
    date = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    new_lines = []
    for line in lines:
        if line.startswith(old_id):
            new_lines.append(f"{new_id or old_id} | {date} | {new_name or old_name}")
        else:
            new_lines.append(line)
    update_github_file(GITHUB_FILE, "\n".join(new_lines), sha)
    embed = discord.Embed(
        title="🔄 User Updated",
        description=f"**Old:** {old_name}\n**New:** {new_name or old_name}\nSuccessfully updated.",
        color=COLORS["blue"]
    )
    embed.set_footer(text="Whitelist Bot • GitHub updated")
    embed.timestamp = datetime.utcnow()
    await interaction.followup.send(embed=embed)
    await send_log(embed)

@tree.command(name="setlog", description="Set this channel as the log channel")
async def set_log(interaction: discord.Interaction):
    if not owner_only(interaction):
        embed = discord.Embed(title="🚫 Access Denied", description="Only the owner can use this.", color=COLORS["error"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    global LOG_CHANNEL_ID
    LOG_CHANNEL_ID = interaction.channel_id
    embed = discord.Embed(title="📋 Log Channel Set", description="This channel will now receive all whitelist logs.", color=COLORS["success"])
    embed.timestamp = datetime.utcnow()
    await interaction.response.send_message(embed=embed)

@tree.command(name="setvoice", description="Set the voice channel for announcements")
@app_commands.describe(channel="Voice channel to use for announcements")
async def set_voice(interaction: discord.Interaction, channel: discord.VoiceChannel):
    if not owner_only(interaction):
        embed = discord.Embed(title="🚫 Access Denied", description="Only the owner can use this.", color=COLORS["error"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    global VOICE_CHANNEL_ID
    VOICE_CHANNEL_ID = channel.id
    embed = discord.Embed(title="🔊 Voice Channel Set", description=f"Voice announcements will use **{channel.name}**.", color=COLORS["success"])
    embed.timestamp = datetime.utcnow()
    await interaction.response.send_message(embed=embed)

@tree.command(name="info", description="Show bot stats and info")
async def bot_info(interaction: discord.Interaction):
    if not owner_only(interaction):
        embed = discord.Embed(title="🚫 Access Denied", description="Only the owner can use this.", color=COLORS["error"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    await interaction.response.defer()
    lines, _, _ = get_github_file(GITHUB_FILE)
    ban_lines, _, _ = get_github_file(BAN_FILE)
    ids = get_ids_only(lines)
    ban_ids = get_ids_only(ban_lines)
    uptime = datetime.utcnow() - START_TIME
    hours, remainder = divmod(int(uptime.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    embed = discord.Embed(
        title="ℹ️ Whitelist Bot Info",
        description="Powered by GitHub • Made for Roblox script protection",
        color=COLORS["purple"]
    )
    embed.add_field(name="✅ Whitelisted Users", value=str(len(ids)), inline=True)
    embed.add_field(name="🔨 Banned Users", value=str(len(ban_ids)), inline=True)
    embed.add_field(name="⏱️ Uptime", value=f"{hours}h {minutes}m {seconds}s", inline=True)
    embed.add_field(name="📁 GitHub Repo", value=GITHUB_REPO, inline=False)
    embed.add_field(name="⏳ Cooldown", value=f"{COOLDOWN_SECONDS} seconds", inline=True)
    embed.add_field(name="📋 Log Channel", value=f"<#{LOG_CHANNEL_ID}>" if LOG_CHANNEL_ID else "Not set", inline=True)
    embed.add_field(name="🔊 Voice Channel", value=f"<#{VOICE_CHANNEL_ID}>" if VOICE_CHANNEL_ID else "Not set", inline=True)
    embed.set_footer(text="Whitelist Bot")
    embed.timestamp = datetime.utcnow()
    await interaction.followup.send(embed=embed)

@tree.command(name="help", description="Show all available commands")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📖 Whitelist Bot Commands",
        description="All commands use **/** slash commands",
        color=COLORS["purple"]
    )
    embed.add_field(name="/add [username]", value="➕ Add user to whitelist", inline=False)
    embed.add_field(name="/remove [username]", value="➖ Remove user from whitelist", inline=False)
    embed.add_field(name="/check [username]", value="🔍 Check if user is whitelisted", inline=False)
    embed.add_field(name="/rename [old] [new]", value="🔄 Update a username", inline=False)
    embed.add_field(name="/list", value="📋 Show all whitelisted users", inline=False)
    embed.add_field(name="/ban [username]", value="🔨 Ban a user permanently", inline=False)
    embed.add_field(name="/unban [username]", value="✅ Unban a user", inline=False)
    embed.add_field(name="/banlist", value="🔨 Show all banned users", inline=False)
    embed.add_field(name="/setlog", value="📋 Set log channel", inline=False)
    embed.add_field(name="/setvoice", value="🔊 Set voice announcement channel", inline=False)
    embed.add_field(name="/info", value="ℹ️ Show bot stats", inline=False)
    embed.add_field(name="/help", value="📖 Show this message", inline=False)
    embed.set_footer(text="Whitelist Bot • Only owner can use commands")
    embed.timestamp = datetime.utcnow()
    await interaction.response.send_message(embed=embed)

print("Starting bot...")
client.run(TOKON)
