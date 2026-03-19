import discord
import os
import requests
import base64
import json
from datetime import datetime

TOKEN = os.environ.get("TOKEN")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
OWNER_ID = 1449777458218926243

GITHUB_REPO = "ALI2023KING/Whitlist-sys"
GITHUB_FILE = "whitelist.txt"

if not TOKEN:
    print("ERROR: No token found!")
    exit(1)

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

def get_github_whitelist():
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    data = r.json()
    content = base64.b64decode(data["content"]).decode("utf-8")
    sha = data["sha"]
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    return lines, sha, content

def update_github_whitelist(new_content, sha):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    encoded = base64.b64encode(new_content.encode("utf-8")).decode("utf-8")
    payload = {"message": "Updated whitelist", "content": encoded, "sha": sha}
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

@client.event
async def on_ready():
    print(f"Bot is online as {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith("!add") or message.content.startswith("!remove") or message.content == "!list" or message.content == "!help" or message.content.startswith("!check") or message.content == "!clear":
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

    if message.content.startswith("!add "):
        user_id = message.content.split(" ")[1].strip()
        lines, sha, content = get_github_whitelist()
        ids = get_ids_only(lines)
        if user_id in ids:
            embed = discord.Embed(
                title="⚠️ Already Whitelisted",
                description=f"**User ID:** `{user_id}`\nThis user is already in the whitelist.",
                color=0xFFCC00
            )
            embed.set_footer(text="Whitelist Bot")
            embed.timestamp = datetime.utcnow()
        else:
            date = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
            new_entry = f"{user_id} | {date}"
            new_content = content.strip() + f"\n{new_entry}"
            update_github_whitelist(new_content, sha)
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

    elif message.content.startswith("!remove "):
        user_id = message.content.split(" ")[1].strip()
        lines, sha, content = get_github_whitelist()
        ids = get_ids_only(lines)
        if user_id not in ids:
            embed = discord.Embed(
                title="❌ Not Found",
                description=f"**User ID:** `{user_id}`\nThis user is not in the whitelist.",
                color=0xFF0000
            )
            embed.set_footer(text="Whitelist Bot")
            embed.timestamp = datetime.utcnow()
        else:
            new_lines = [line for line in lines if not line.startswith(user_id)]
            new_content = "\n".join(new_lines)
            update_github_whitelist(new_content, sha)
            username = get_roblox_username(user_id)
            avatar = get_roblox_avatar(user_id)
            embed = discord.Embed(
                title="🗑️ User Removed",
                description=f"**User ID:** `{user_id}`\n**Username:** {username or 'Unknown'}\nThis user has been removed.",
                color=0xFF4500
            )
            embed.add_field(name="Total Users", value=str(len(ids) - 1), inline=True)
            embed.add_field(name="GitHub", value="✅ Updated", inline=True)
            if avatar:
                embed.set_thumbnail(url=avatar)
            embed.set_footer(text="Whitelist Bot • GitHub updated")
            embed.timestamp = datetime.utcnow()
        await message.channel.send(embed=embed)

    elif message.content.startswith("!check "):
        user_id = message.content.split(" ")[1].strip()
        lines, sha, content = get_github_whitelist()
        found = None
        for line in lines:
            if line.startswith(user_id):
                found = line
                break
        username = get_roblox_username(user_id)
        avatar = get_roblox_avatar(user_id)
        if found:
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
                color=0xFF0000
            )
        if avatar:
            embed.set_thumbnail(url=avatar)
        embed.set_footer(text="Whitelist Bot")
        embed.timestamp = datetime.utcnow()
        await message.channel.send(embed=embed)

    elif message.content == "!list":
        lines, sha, content = get_github_whitelist()
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

    elif message.content == "!clear":
        lines, sha, content = get_github_whitelist()
        update_github_whitelist("", sha)
        embed = discord.Embed(
            title="🧹 Whitelist Cleared",
            description="All users have been removed from the whitelist.",
            color=0xFF4500
        )
        embed.set_footer(text="Whitelist Bot • GitHub updated")
        embed.timestamp = datetime.utcnow()
        await message.channel.send(embed=embed)

    elif message.content == "!help":
        embed = discord.Embed(
            title="📖 Whitelist Bot Commands",
            description="Here are all available commands:",
            color=0x9B59B6
        )
        embed.add_field(name="!add [ID]", value="➕ Add a user to the whitelist", inline=False)
        embed.add_field(name="!remove [ID]", value="➖ Remove a user from the whitelist", inline=False)
        embed.add_field(name="!check [ID]", value="🔍 Check if a user is whitelisted", inline=False)
        embed.add_field(name="!list", value="📋 Show all whitelisted users", inline=False)
        embed.add_field(name="!clear", value="🧹 Clear the entire whitelist", inline=False)
        embed.add_field(name="!help", value="📖 Show this help message", inline=False)
        embed.set_footer(text="Whitelist Bot • Only owner can use commands")
        embed.timestamp = datetime.utcnow()
        await message.channel.send(embed=embed)

print("Starting bot...")
client.run(TOKEN)
