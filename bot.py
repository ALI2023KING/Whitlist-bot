import discord
import os

TOKEN = os.environ.get("TOKEN")

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

WHITELIST_FILE = "whitelist.txt"

def read_whitelist():
    if not os.path.exists(WHITELIST_FILE):
        return []
    with open(WHITELIST_FILE, "r") as f:
        return [line.strip() for line in f.readlines() if line.strip()]

def write_whitelist(ids):
    with open(WHITELIST_FILE, "w") as f:
        f.write("\n".join(ids))

@client.event
async def on_ready():
    print(f"Bot is online as {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith("!add "):
        user_id = message.content.split(" ")[1].strip()
        ids = read_whitelist()
        if user_id in ids:
            await message.channel.send(f"❌ {user_id} is already whitelisted")
        else:
            ids.append(user_id)
            write_whitelist(ids)
            await message.channel.send(f"✅ Added {user_id}")

    elif message.content.startswith("!remove "):
        user_id = message.content.split(" ")[1].strip()
        ids = read_whitelist()
        if user_id not in ids:
            await message.channel.send(f"❌ {user_id} not found")
        else:
            ids.remove(user_id)
            write_whitelist(ids)
            await message.channel.send(f"✅ Removed {user_id}")

    elif message.content == "!list":
        ids = read_whitelist()
        if not ids:
            await message.channel.send("Whitelist is empty")
        else:
            await message.channel.send("**Whitelisted IDs:**\n" + "\n".join(ids))
