import discord
import os
import requests
import base64
import json

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
    ids = [line.strip() for line in content.splitlines() if line.strip() and not line.startswith("--")]
    return ids, sha, content

def update_github_whitelist(new_content, sha):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    encoded = base64.b64encode(new_content.encode("utf-8")).decode("utf-8")
    payload = {"message": "Updated whitelist", "content": encoded, "sha": sha}
    requests.put(url, headers=headers, data=json.dumps(payload))

@client.event
async def on_ready():
    print(f"Bot is online as {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith("!add") or message.content.startswith("!remove") or message.content == "!list" or message.content == "!help":
        if message.author.id != OWNER_ID:
            embed = discord.Embed(
                title="🚫 Access Denied",
                description="You are not authorized to use this bot.",
                color=0xFF0000
            )
            embed.set_footer(text="Whitelist Bot • Only owner can use commands")
            await message.channel.send(embed=embed)
            return

    if message.content.startswith("!add "):
        user_id = message.content.split(" ")[1].strip()
        ids, sha, content = get_github_whitelist()
        if user_id in ids:
            embed = discord.Embed(
                title="⚠️ Already Whitelisted",
                description=f"**{user_id}** is already in the whitelist.",
                color=0xFFCC00
            )
            embed.set_footer(text="Whitelist Bot")
        else:
            new_content = content.strip() + f"\n{user_id}"
            update_github_whitelist(new_content, sha)
            embed = discord.Embed(
                title="✅ User Added",
                description=f"**{user_id}** has been added to the whitelist.",
                color=0x00FF7F
            )
            embed.add_field(name="Total Users", value=str(len(ids) + 1), inline=True)
            embed.set_footer(text="Whitelist Bot • GitHub updated")
        await message.channel.send(embed=embed)

    elif message.content.startswith("!remove "):
        user_id = message.content.split(" ")[1].strip()
        ids, sha, content = get_github_whitelist()
        if user_id not in ids:
            embed = discord.Embed(
                title="❌ Not Found",
                description=f"**{user_id}** is not in the whitelist.",
                color=0xFF0000
            )
            embed.set_footer(text="Whitelist Bot")
        else:
            new_lines = [line for line in content.splitlines() if line.strip() != user_id]
            new_content = "\n".join(new_lines)
            update_github_whitelist(new_content, sha)
            embed = discord.Embed(
                title="🗑️ User Removed",
                description=f"**{user_id}** has been removed from the whitelist.",
                color=0xFF4500
            )
            embed.add_field(name="Total Users", value=str(len(ids) - 1), inline=True)
            embed.set_footer(text="Whitelist Bot • GitHub updated")
        await message.channel.send(embed=embed)

    elif message.content == "!list":
        ids, sha, content = get_github_whitelist()
        if not ids:
            embed = discord.Embed(
                title="📋 Whitelist",
                description="The whitelist is currently empty.",
                color=0x5865F2
            )
        else:
            embed = discord.Embed(
                title="📋 Whitelist",
                description="\n".join([f"• `{id}`" for id in ids]),
                color=0x5865F2
            )
            embed.add_field(name="Total Users", value=str(len(ids)), inline=True)
        embed.set_footer(text="Whitelist Bot • Powered by GitHub")
        await message.channel.send(embed=embed)

    elif message.content == "!help":
        embed = discord.Embed(
            title="📖 Whitelist Bot Commands",
            description="Here are all available commands:",
            color=0x9B59B6
        )
        embed.add_field(name="!add [ID]", value="➕ Add a user to the whitelist", inline=False)
        embed.add_field(name="!remove [ID]", value="➖ Remove a user from the whitelist", inline=False)
        embed.add_field(name="!list", value="📋 Show all whitelisted users", inline=False)
        embed.add_field(name="!help", value="📖 Show this help message", inline=False)
        embed.set_footer(text="Whitelist Bot • Only owner can use commands")
        await message.channel.send(embed=embed)

print("Starting bot...")
client.run(TOKEN)
