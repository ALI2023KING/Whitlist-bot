import discord
import os
import requests
import base64
import json

TOKEN = os.environ.get("TOKEN")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

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

    if message.content.startswith("!add "):
        user_id = message.content.split(" ")[1].strip()
        ids, sha, content = get_github_whitelist()
        if user_id in ids:
            embed = discord.Embed(title="⚠️ Already Whitelisted", description=f"`{user_id}` is already in the whitelist.", color=discord.Color.yellow())
        else:
            new_content = content.strip() + f"\n{user_id}"
            update_github_whitelist(new_content, sha)
            embed = discord.Embed(title="✅ Added", description=f"`{user_id}` has been added.", color=discord.Color.green())
        await message.channel.send(embed=embed)

    elif message.content.startswith("!remove "):
        user_id = message.content.split(" ")[1].strip()
        ids, sha, content = get_github_whitelist()
        if user_id not in ids:
            embed = discord.Embed(title="❌ Not Found", description=f"`{user_id}` is not in the whitelist.", color=discord.Color.red())
        else:
            new_lines = [line for line in content.splitlines() if line.strip() != user_id]
            new_content = "\n".join(new_lines)
            update_github_whitelist(new_content, sha)
            embed = discord.Embed(title="🗑️ Removed", description=f"`{user_id}` has been removed.", color=discord.Color.red())
        await message.channel.send(embed=embed)

    elif message.content == "!list":
        ids, sha, content = get_github_whitelist()
        if not ids:
            embed = discord.Embed(title="📋 Whitelist", description="The whitelist is empty.", color=discord.Color.blue())
        else:
            embed = discord.Embed(title="📋 Whitelist", description="\n".join([f"`{id}`" for id in ids]), color=discord.Color.blue())
            embed.set_footer(text=f"Total: {len(ids)} users")
        await message.channel.send(embed=embed)

print("Starting bot...")
client.run(TOKEN)
