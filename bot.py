import discord
import os

TOKEN = os.environ.get("TOKEN")
OWNER_ID = 1449777458218926243

if not TOKEN:
    print("ERROR: No token found!")
    exit(1)

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

    if message.author.id != OWNER_ID:
        if message.content.startswith("!add") or message.content.startswith("!remove") or message.content.startswith("!list"):
            embed = discord.Embed(
                title="❌ No Permission",
                description="Only the owner can use these commands.",
                color=discord.Color.red()
            )
            await message.channel.send(embed=embed)
            return

    if message.content.startswith("!add "):
        user_id = message.content.split(" ")[1].strip()
        ids = read_whitelist()
        if user_id in ids:
            embed = discord.Embed(
                title="⚠️ Already Whitelisted",
                description=f"`{user_id}` is already in the whitelist.",
                color=discord.Color.yellow()
            )
        else:
            ids.append(user_id)
            write_whitelist(ids)
            embed = discord.Embed(
                title="✅ Added",
                description=f"`{user_id}` has been added to the whitelist.",
                color=discord.Color.green()
            )
        await message.channel.send(embed=embed)

    elif message.content.startswith("!remove "):
        user_id = message.content.split(" ")[1].strip()
        ids = read_whitelist()
        if user_id not in ids:
            embed = discord.Embed(
                title="❌ Not Found",
                description=f"`{user_id}` is not in the whitelist.",
                color=discord.Color.red()
            )
        else:
            ids.remove(user_id)
            write_whitelist(ids)
            embed = discord.Embed(
                title="🗑️ Removed",
                description=f"`{user_id}` has been removed from the whitelist.",
                color=discord.Color.red()
            )
        await message.channel.send(embed=embed)

    elif message.content == "!list":
        ids = read_whitelist()
        if not ids:
            embed = discord.Embed(
                title="📋 Whitelist",
                description="The whitelist is empty.",
                color=discord.Color.blue()
            )
        else:
            embed = discord.Embed(
                title="📋 Whitelist",
                description="\n".join([f"`{id}`" for id in ids]),
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"Total: {len(ids)} users")
        await message.channel.send(embed=embed)

    elif message.content == "!help":
        embed = discord.Embed(
            title="📖 Commands",
            color=discord.Color.purple()
        )
        embed.add_field(name="!add [ID]", value="Add a user to whitelist", inline=False)
        embed.add_field(name="!remove [ID]", value="Remove a user from whitelist", inline=False)
        embed.add_field(name="!list", value="Show all whitelisted users", inline=False)
        await message.channel.send(embed=embed)

print("Starting bot...")
client.run(TOKEN)
