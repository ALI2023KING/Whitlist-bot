
import discord
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

cooldowns = {}
COOLDOWN_SECONDS = 3

if not TOKEN:
    print("ERROR: No token found!")
    exit(1)

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

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
    return user_id, date

def get_ids_only(lines):
    return [parse_entry(line)[0] for line in lines if not line.startswith("--")]

async def send_log(embed):
    if LOG_CHANNEL_ID:
        channel = client.get_channel(LOG_CHANNEL_ID)
        if channel:
            await channel.send(embed=embed)

@client.event
async def on_ready():
    print(f"Bot is online as {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    commands = ["!add", "!addname", "!remove", "!rename", "!check",
                "!list", "!help", "!info", "!ban", "!unban", "!banlist", "!setlog"]

    if any(message.content.startswith(cmd) for cmd in commands):
        if message.author.id != OWNER_ID:
            embed = discord.Embed(
                title="🚫 Access Denied",
                description="You are not authorized to use this bot.",
                color=0xFF0000
            )
            embed.set_footer(text="Whitelist Bot • Only owner can use commands")
            embed.timestamp = datetime.utcnow()
            await message.channel.send(embed=embed)
            return

        if is_on_cooldown(message.author.id):
            embed = discord.Embed(
                title="⏳ Cooldown",
                description=f"Please wait {COOLDOWN_SECONDS} seconds between commands.",
                color=0xFFCC00
            )
            embed.timestamp = datetime.utcnow()
            await message.channel.send(embed=embed)
            return

    # !setlog
    if message.content.startswith("!setlog"):
        global LOG_CHANNEL_ID
        LOG_CHANNEL_ID = message.channel.id
        embed = discord.Embed(
            title="📋 Log Channel Set",
            description=f"This channel will now receive all whitelist logs.",
            color=0x00FF7F
        )
        embed.timestamp = datetime.utcnow()
        await message.channel.send(embed=embed)

    # !add
    elif message.content.startswith("!add "):
        user_id = message.content.split(" ")[1].strip()
        lines, sha, content = get_github_file(GITHUB_FILE)
        ids = get_ids_only(lines)
        ban_lines, _, _ = get_github_file(BAN_FILE)
        ban_ids = get_ids_only(ban_lines)
        if user_id in ban_ids:
            embed = discord.Embed(
                title="🔨 User is Banned",
                description=f"**User ID:** `{user_id}`\nThis user is banned and cannot be whitelisted.",
                color=0xFF0000
            )
            embed.timestamp = datetime.utcnow()
            await message.channel.send(embed=embed)
            return
        if user_id in ids:
            embed = discord.Embed(
                title="⚠️ Already Whitelisted",
                description=f"**User ID:** `{user_id}`\nThis user is already in the whitelist.",
                color=0xFFCC00
            )
            embed.timestamp = datetime.utcnow()
            await message.channel.send(embed=embed)
        else:
            date = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
            new_entry = f"{user_id} | {date}"
            new_content = content.strip() + f"\n{new_entry}"
            update_github_file(GITHUB_FILE, new_content, sha)
            username = get_roblox_username(user_id)
            avatar = get_roblox_avatar(user_id)
            embed = discord.Embed(
                title="✅ User Whitelisted",
                description=f"**User ID:** `{user_id}`\n**Username:** {username or 'Unknown'}\n**Added on:** {date} UTC",
                color=0x00FF7F
            )
            embed.add_field(name="Total Users", value=str(len(ids) + 1), inline=True)
            embed.add_field(name="GitHub", value="✅ Updated", inline=True)
            if avatar:
                embed.set_thumbnail(url=avatar)
            embed.set_footer(text="Whitelist Bot • GitHub updated")
            embed.timestamp = datetime.utcnow()
            await message.channel.send(embed=embed)
            await send_log(embed)

    # !addname
    elif message.content.startswith("!addname "):
        username_input = message.content.split(" ")[1].strip()
        user_id, username = get_roblox_user_by_username(username_input)
        if not user_id:
            embed = discord.Embed(
                title="❌ User Not Found",
                description=f"Could not find Roblox user **{username_input}**.",
                color=0xFF0000
            )
            embed.timestamp = datetime.utcnow()
            await message.channel.send(embed=embed)
            return
        lines, sha, content = get_github_file(GITHUB_FILE)
        ids = get_ids_only(lines)
        ban_lines, _, _ = get_github_file(BAN_FILE)
        ban_ids = get_ids_only(ban_lines)
        if user_id in ban_ids:
            embed = discord.Embed(
                title="🔨 User is Banned",
                description=f"**{username}** is banned and cannot be whitelisted.",
                color=0xFF0000
            )
            embed.timestamp = datetime.utcnow()
            await message.channel.send(embed=embed)
            return
        if user_id in ids:
            embed = discord.Embed(
                title="⚠️ Already Whitelisted",
                description=f"**{username}** (`{user_id}`) is already whitelisted.",
                color=0xFFCC00
            )
            embed.timestamp = datetime.utcnow()
            await message.channel.send(embed=embed)
        else:
            date = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
            new_entry = f"{user_id} | {date}"
            new_content = content.strip() + f"\n{new_entry}"
            update_github_file(GITHUB_FILE, new_content, sha)
            avatar = get_roblox_avatar(user_id)
            embed = discord.Embed(
                title="✅ User Whitelisted",
                description=f"**Username:** {username}\n**User ID:** `{user_id}`\n**Added on:** {date} UTC",
                color=0x00FF7F
            )
            embed.add_field(name="Total Users", value=str(len(ids) + 1), inline=True)
            embed.add_field(name="GitHub", value="✅ Updated", inline=True)
            if avatar:
                embed.set_thumbnail(url=avatar)
            embed.set_footer(text="Whitelist Bot • GitHub updated")
            embed.timestamp = datetime.utcnow()
            await message.channel.send(embed=embed)
            await send_log(embed)

    # !remove
    elif message.content.startswith("!remove "):
        user_id = message.content.split(" ")[1].strip()
        lines, sha, content = get_github_file(GITHUB_FILE)
        ids = get_ids_only(lines)
        if user_id not in ids:
            embed = discord.Embed(
                title="❌ Not Found",
                description=f"**User ID:** `{user_id}` is not in the whitelist.",
                color=0xFF0000
            )
            embed.timestamp = datetime.utcnow()
            await message.channel.send(embed=embed)
        else:
            new_lines = [line for line in lines if not line.startswith(user_id)]
            new_content = "\n".join(new_lines)
            update_github_file(GITHUB_FILE, new_content, sha)
            username = get_roblox_username(user_id)
            avatar = get_roblox_avatar(user_id)
            embed = discord.Embed(
                title="🗑️ User Removed",
                description=f"**User ID:** `{user_id}`\n**Username:** {username or 'Unknown'}\nRemoved from whitelist.",
                color=0xFF4500
            )
            embed.add_field(name="Total Users", value=str(len(ids) - 1), inline=True)
            embed.add_field(name="GitHub", value="✅ Updated", inline=True)
            if avatar:
                embed.set_thumbnail(url=avatar)
            embed.set_footer(text="Whitelist Bot • GitHub updated")
            embed.timestamp = datetime.utcnow()
            await message.channel.send(embed=embed)
            await send_log(embed)

    # !rename
    elif message.content.startswith("!rename "):
        parts = message.content.split(" ")
        if len(parts) < 3:
            await message.channel.send("Usage: `!rename OLDID NEWID`")
            return
        old_id = parts[1].strip()
        new_id = parts[2].strip()
        lines, sha, content = get_github_file(GITHUB_FILE)
        ids = get_ids_only(lines)
        if old_id not in ids:
            embed = discord.Embed(
                title="❌ Not Found",
                description=f"`{old_id}` is not in the whitelist.",
                color=0xFF0000
            )
            embed.timestamp = datetime.utcnow()
            await message.channel.send(embed=embed)
        else:
            date = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
            new_lines = []
            for line in lines:
                if line.startswith(old_id):
                    new_lines.append(f"{new_id} | {date}")
                else:
                    new_lines.append(line)
            new_content = "\n".join(new_lines)
            update_github_file(GITHUB_FILE, new_content, sha)
            embed = discord.Embed(
                title="🔄 User ID Updated",
                description=f"**Old ID:** `{old_id}`\n**New ID:** `{new_id}`\nSuccessfully updated.",
                color=0x00BFFF
            )
            embed.set_footer(text="Whitelist Bot • GitHub updated")
            embed.timestamp = datetime.utcnow()
            await message.channel.send(embed=embed)
            await send_log(embed)

    # !ban
    elif message.content.startswith("!ban "):
        user_id = message.content.split(" ")[1].strip()
        ban_lines, ban_sha, ban_content = get_github_file(BAN_FILE)
        ban_ids = get_ids_only(ban_lines)
        if user_id in ban_ids:
            embed = discord.Embed(
                title="⚠️ Already Banned",
                description=f"`{user_id}` is already banned.",
                color=0xFFCC00
            )
            embed.timestamp = datetime.utcnow()
            await message.channel.send(embed=embed)
        else:
            lines, sha, content = get_github_file(GITHUB_FILE)
            ids = get_ids_only(lines)
            if user_id in ids:
                new_lines = [line for line in lines if not line.startswith(user_id)]
                update_github_file(GITHUB_FILE, "\n".join(new_lines), sha)
            date = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
            new_ban = ban_content.strip() + f"\n{user_id} | {date}"
            update_github_file(BAN_FILE, new_ban, ban_sha)
            username = get_roblox_username(user_id)
            avatar = get_roblox_avatar(user_id)
            embed = discord.Embed(
                title="🔨 User Banned",
                description=f"**User ID:** `{user_id}`\n**Username:** {username or 'Unknown'}\nBanned and removed from whitelist.",
                color=0xFF0000
            )
            if avatar:
                embed.set_thumbnail(url=avatar)
            embed.set_footer(text="Whitelist Bot • GitHub updated")
            embed.timestamp = datetime.utcnow()
            await message.channel.send(embed=embed)
            await send_log(embed)

    # !unban
    elif message.content.startswith("!unban "):
        user_id = message.content.split(" ")[1].strip()
        ban_lines, ban_sha, ban_content = get_github_file(BAN_FILE)
        ban_ids = get_ids_only(ban_lines)
        if user_id not in ban_ids:
            embed = discord.Embed(
                title="❌ Not Banned",
                description=f"`{user_id}` is not in the ban list.",
                color=0xFF0000
            )
            embed.timestamp = datetime.utcnow()
            await message.channel.send(embed=embed)
        else:
            new_lines = [line for line in ban_lines if not line.startswith(user_id)]
            update_github_file(BAN_FILE, "\n".join(new_lines), ban_sha)
            embed = discord.Embed(
                title="✅ User Unbanned",
                description=f"`{user_id}` has been removed from the ban list.",
                color=0x00FF7F
            )
            embed.timestamp = datetime.utcnow()
            await message.channel.send(embed=embed)

    # !banlist
    elif message.content == "!banlist":
        ban_lines, _, _ = get_github_file(BAN_FILE)
        entries = [line for line in ban_lines if not line.startswith("--")]
        if not entries:
            embed = discord.Embed(
                title="🔨 Ban List",
                description="No banned users.",
                color=0xFF0000
            )
        else:
            desc = ""
            for line in entries:
                uid, date = parse_entry(line)
                desc += f"• `{uid}` — banned {date}\n"
            embed = discord.Embed(
                title="🔨 Ban List",
                description=desc,
                color=0xFF0000
            )
            embed.add_field(name="Total Banned", value=str(len(entries)), inline=True)
        embed.set_footer(text="Whitelist Bot")
        embed.timestamp = datetime.utcnow()
        await message.channel.send(embed=embed)

    # !check
    elif message.content.startswith("!check "):
        user_id = message.content.split(" ")[1].strip()
        lines, sha, content = get_github_file(GITHUB_FILE)
        ban_lines, _, _ = get_github_file(BAN_FILE)
        ban_ids = get_ids_only(ban_lines)
        found = None
        for line in lines:
            if line.startswith(user_id):
                found = line
                break
        username = get_roblox_username(user_id)
        avatar = get_roblox_avatar(user_id)
        if user_id in ban_ids:
            embed = discord.Embed(
                title="🔨 User is Banned",
                description=f"**User ID:** `{user_id}`\n**Username:** {username or 'Unknown'}\nThis user is banned.",
                color=0xFF0000
            )
        elif found:
            uid, date = parse_entry(found)
            embed = discord.Embed(
                title="✅ User is Whitelisted",
                description=f"**User ID:** `{user_id}`\n**Username:** {username or 'Unknown'}\n**Added on:** {date} UTC",
                color=0x00FF7F
            )
        else:
            embed = discord.Embed(
                title="❌ Not Whitelisted",
                description=f"**User ID:** `{user_id}`\n**Username:** {username or 'Unknown'}\nThis user does not have access.",
                color=0xFF4500
            )
        if avatar:
            embed.set_thumbnail(url=avatar)
        embed.set_footer(text="Whitelist Bot")
        embed.timestamp = datetime.utcnow()
        await message.channel.send(embed=embed)

    # !list
    elif message.content == "!list":
        lines, sha, content = get_github_file(GITHUB_FILE)
        entries = [line for line in lines if not line.startswith("--")]
        if not entries:
            embed = discord.Embed(
                title="📋 Whitelist",
                description="The whitelist is currently empty.",
                color=0x5865F2
            )
        else:
            desc = ""
            for line in entries:
                uid, date = parse_entry(line)
                desc += f"• `{uid}` — added {date}\n"
            embed = discord.Embed(
                title="📋 Whitelist",
                description=desc,
                color=0x5865F2
            )
            embed.add_field(name="Total Users", value=str(len(entries)), inline=True)
        embed.set_footer(text="Whitelist Bot • Powered by GitHub")
        embed.timestamp = datetime.utcnow()
        await message.channel.send(embed=embed)

    # !info
    elif message.content == "!info":
        lines, _, _ = get_github_file(GITHUB_FILE)
        ban_lines, _, _ = get_github_file(BAN_FILE)
        ids = get_ids_only(lines)
        ban_ids = get_ids_only(ban_lines)
        embed = discord.Embed(
            title="ℹ️ Bot Info",
            description="Whitelist Bot — Powered by GitHub",
            color=0x9B59B6
        )
        embed.add_field(name="✅ Whitelisted Users", value=str(len(ids)), inline=True)
        embed.add_field(name="🔨 Banned Users", value=str(len(ban_ids)), inline=True)
        embed.add_field(name="📁 GitHub Repo", value=GITHUB_REPO, inline=False)
        embed.add_field(name="⏳ Cooldown", value=f"{COOLDOWN_SECONDS} seconds", inline=True)
        embed.add_field(name="📋 Log Channel", value=f"<#{LOG_CHANNEL_ID}>" if LOG_CHANNEL_ID else "Not set", inline=True)
        embed.set_footer(text="Whitelist Bot")
        embed.timestamp = datetime.utcnow()
        await message.channel.send(embed=embed)

    # !help
    elif message.content == "!help":
        embed = discord.Embed(
            title="📖 Whitelist Bot Commands",
            description="Here are all available commands:",
            color=0x9B59B6
        )
        embed.add_field(name="!add [ID]", value="➕ Add user by Roblox ID", inline=False)
        embed.add_field(name="!addname [USERNAME]", value="➕ Add user by Roblox username", inline=False)
        embed.add_field(name="!remove [ID]", value="➖ Remove user from whitelist", inline=False)
        embed.add_field(name="!rename [OLDID] [NEWID]", value="🔄 Update a user's ID", inline=False)
        embed.add_field(name="!check [ID]", value="🔍 Check if user is whitelisted", inline=False)
        embed.add_field(name="!list", value="📋 Show all whitelisted users", inline=False)
        embed.add_field(name="!ban [ID]", value="🔨 Ban a user permanently", inline=False)
        embed.add_field(name="!unban [ID]", value="✅ Unban a user", inline=False)
        embed.add_field(name="!banlist", value="🔨 Show all banned users", inline=False)
        embed.add_field(name="!setlog", value="📋 Set this channel as log channel", inline=False)
        embed.add_field(name="!info", value="ℹ️ Show bot info and stats", inline=False)
        embed.add_field(name="!help", value="📖 Show this help message", inline=False)
        embed.set_footer(text="Whitelist Bot • Only owner can use commands")
        embed.timestamp = datetime.utcnow()
        await message.channel.send(embed=embed)

print("Starting bot...")
client.run(TOKEN)
