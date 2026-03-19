
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
WHITELIST_ROLE_ID = None

cooldowns = {}
COOLDOWN_SECONDS = 3
START_TIME = datetime.utcnow()

if not TOKEN:
    print("ERROR: No token found!")
    exit(1)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

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
    user_id = parts[0].strip() if len(parts) > 0 else ""
    date = parts[1].strip() if len(parts) > 1 else "Unknown"
    roblox_name = parts[2].strip() if len(parts) > 2 else None
    discord_user = parts[3].strip() if len(parts) > 3 else None
    note = parts[4].strip() if len(parts) > 4 else None
    expiry = parts[5].strip() if len(parts) > 5 else None
    return user_id, date, roblox_name, discord_user, note, expiry

def get_ids_only(lines):
    return [parse_entry(line)[0] for line in lines if not line.startswith("--")]

def is_expired(expiry_str):
    if not expiry_str or expiry_str == "never":
        return False
    try:
        expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d %H:%M")
        return datetime.utcnow() > expiry_date
    except:
        return False

async def send_log(embed):
    if LOG_CHANNEL_ID:
        channel = client.get_channel(LOG_CHANNEL_ID)
        if channel:
            await channel.send(embed=embed)

async def give_whitelist_role(guild, discord_user_id):
    if WHITELIST_ROLE_ID and guild:
        try:
            member = guild.get_member(int(discord_user_id))
            if member:
                role = guild.get_role(WHITELIST_ROLE_ID)
                if role:
                    await member.add_roles(role)
        except:
            pass

async def remove_whitelist_role(guild, discord_user_id):
    if WHITELIST_ROLE_ID and guild:
        try:
            member = guild.get_member(int(discord_user_id))
            if member:
                role = guild.get_role(WHITELIST_ROLE_ID)
                if role:
                    await member.remove_roles(role)
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
#   AUTOCOMPLETE
# =============================================
async def username_autocomplete(interaction: discord.Interaction, current: str):
    lines, _, _ = get_github_file(GITHUB_FILE)
    choices = []
    for line in lines:
        uid, date, roblox_name, discord_user, note, expiry = parse_entry(line)
        if roblox_name and current.lower() in roblox_name.lower():
            choices.append(app_commands.Choice(name=roblox_name, value=roblox_name))
        if len(choices) >= 25:
            break
    return choices

# =============================================
#   CONFIRM VIEW
# =============================================
class ConfirmView(discord.ui.View):
    def __init__(self, action, embed_data):
        super().__init__(timeout=30)
        self.action = action
        self.embed_data = embed_data
        self.confirmed = False

    @discord.ui.button(label="✅ Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmed = True
        await self.action(interaction)
        self.stop()

    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="❌ Cancelled", description="Action cancelled.", color=COLORS["error"])
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()

# =============================================
#   /add
# =============================================
@tree.command(name="add", description="Add a Roblox user to the whitelist")
@app_commands.describe(
    username="Roblox username",
    discord_user="Their Discord user (optional)",
    note="Note about this user (optional)",
    days="Number of days access lasts (leave empty for permanent)"
)
async def add_user(interaction: discord.Interaction, username: str, discord_user: discord.Member = None, note: str = None, days: int = None):
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
        embed = discord.Embed(title="🔨 User is Banned", description=f"**{roblox_name}** is banned.", color=COLORS["error"])
        await interaction.followup.send(embed=embed)
        return
    if user_id in ids:
        embed = discord.Embed(title="⚠️ Already Whitelisted", description=f"**{roblox_name}** is already whitelisted.", color=COLORS["warning"])
        await interaction.followup.send(embed=embed)
        return
    date = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    expiry = "never"
    if days:
        expiry_date = datetime.utcnow() + timedelta(days=days)
        expiry = expiry_date.strftime("%Y-%m-%d %H:%M")
    discord_str = str(discord_user.id) if discord_user else "none"
    note_str = note if note else "none"
    new_entry = f"{user_id} | {date} | {roblox_name} | {discord_str} | {note_str} | {expiry}"
    new_content = content.strip() + f"\n{new_entry}"
    update_github_file(GITHUB_FILE, new_content, sha)
    avatar = get_roblox_avatar(user_id)
    embed = discord.Embed(
        title="✅ User Whitelisted",
        color=COLORS["success"]
    )
    embed.add_field(name="Roblox", value=roblox_name, inline=True)
    embed.add_field(name="Discord", value=discord_user.mention if discord_user else "Not set", inline=True)
    embed.add_field(name="Note", value=note or "None", inline=True)
    embed.add_field(name="Expires", value=expiry if expiry != "never" else "Never", inline=True)
    embed.add_field(name="Total Users", value=str(len(ids) + 1), inline=True)
    if avatar:
        embed.set_thumbnail(url=avatar)
    embed.set_footer(text="Whitelist Bot • GitHub updated")
    embed.timestamp = datetime.utcnow()
    await interaction.followup.send(embed=embed)
    await send_log(embed)
    if discord_user:
        await give_whitelist_role(interaction.guild, discord_user.id)
        try:
            dm_embed = discord.Embed(
                title="✅ You have been Whitelisted!",
                description=f"You now have access to the script.\n**Roblox:** {roblox_name}\n**Expires:** {expiry if expiry != 'never' else 'Never'}",
                color=COLORS["success"]
            )
            await discord_user.send(embed=dm_embed)
        except:
            pass

# =============================================
#   /remove
# =============================================
@tree.command(name="remove", description="Remove a Roblox user from the whitelist")
@app_commands.describe(username="Roblox username to remove")
@app_commands.autocomplete(username=username_autocomplete)
async def remove_user(interaction: discord.Interaction, username: str):
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
    lines, sha, content = get_github_file(GITHUB_FILE)
    ids = get_ids_only(lines)
    if user_id not in ids:
        embed = discord.Embed(title="❌ Not Found", description=f"**{roblox_name}** is not in the whitelist.", color=COLORS["error"])
        await interaction.followup.send(embed=embed)
        return
    found_line = None
    for line in lines:
        if line.startswith(user_id):
            found_line = line
            break
    uid, date, rname, discord_str, note, expiry = parse_entry(found_line) if found_line else (user_id, "", roblox_name, None, None, None)
    avatar = get_roblox_avatar(user_id)
    confirm_embed = discord.Embed(
        title="⚠️ Confirm Remove",
        description=f"Are you sure you want to remove **{roblox_name}**?",
        color=COLORS["warning"]
    )
    if avatar:
        confirm_embed.set_thumbnail(url=avatar)

    async def do_remove(i: discord.Interaction):
        new_lines = [line for line in lines if not line.startswith(user_id)]
        update_github_file(GITHUB_FILE, "\n".join(new_lines), sha)
        result_embed = discord.Embed(
            title="🗑️ User Removed",
            description=f"**{roblox_name}** has been removed from the whitelist.",
            color=COLORS["ban"]
        )
        result_embed.add_field(name="Total Users", value=str(len(ids) - 1), inline=True)
        if avatar:
            result_embed.set_thumbnail(url=avatar)
        result_embed.timestamp = datetime.utcnow()
        await i.response.edit_message(embed=result_embed, view=None)
        await send_log(result_embed)
        if discord_str and discord_str != "none":
            await remove_whitelist_role(i.guild, discord_str)
            try:
                member = i.guild.get_member(int(discord_str))
                if member:
                    dm_embed = discord.Embed(
                        title="❌ Whitelist Removed",
                        description="Your access to the script has been removed.",
                        color=COLORS["error"]
                    )
                    await member.send(embed=dm_embed)
            except:
                pass

    view = ConfirmView(do_remove, {})
    await interaction.followup.send(embed=confirm_embed, view=view)

# =============================================
#   /ban
# =============================================
@tree.command(name="ban", description="Ban a Roblox user")
@app_commands.describe(username="Roblox username to ban")
@app_commands.autocomplete(username=username_autocomplete)
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
    avatar = get_roblox_avatar(user_id)
    confirm_embed = discord.Embed(
        title="⚠️ Confirm Ban",
        description=f"Are you sure you want to ban **{roblox_name}**?",
        color=COLORS["warning"]
    )
    if avatar:
        confirm_embed.set_thumbnail(url=avatar)

    async def do_ban(i: discord.Interaction):
        lines, sha, content = get_github_file(GITHUB_FILE)
        ids = get_ids_only(lines)
        found_line = None
        for line in lines:
            if line.startswith(user_id):
                found_line = line
                break
        discord_str = None
        if found_line:
            _, _, _, discord_str, _, _ = parse_entry(found_line)
            new_lines = [line for line in lines if not line.startswith(user_id)]
            update_github_file(GITHUB_FILE, "\n".join(new_lines), sha)
        date = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        new_ban = ban_content.strip() + f"\n{user_id} | {date} | {roblox_name}"
        update_github_file(BAN_FILE, new_ban, ban_sha)
        result_embed = discord.Embed(
            title="🔨 User Banned",
            description=f"**{roblox_name}** has been banned and removed from the whitelist.",
            color=COLORS["error"]
        )
        if avatar:
            result_embed.set_thumbnail(url=avatar)
        result_embed.timestamp = datetime.utcnow()
        await i.response.edit_message(embed=result_embed, view=None)
        await send_log(result_embed)
        if discord_str and discord_str != "none":
            await remove_whitelist_role(i.guild, discord_str)
            try:
                member = i.guild.get_member(int(discord_str))
                if member:
                    dm_embed = discord.Embed(
                        title="🔨 You have been Banned",
                        description="You have been banned from the whitelist.",
                        color=COLORS["error"]
                    )
                    await member.send(embed=dm_embed)
            except:
                pass

    view = ConfirmView(do_ban, {})
    await interaction.followup.send(embed=confirm_embed, view=view)

# =============================================
#   /unban
# =============================================
@tree.command(name="unban", description="Unban a Roblox user")
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
        embed = discord.Embed(title="❌ Not Banned", description=f"**{roblox_name}** is not banned.", color=COLORS["error"])
        await interaction.followup.send(embed=embed)
        return
    new_lines = [line for line in ban_lines if not line.startswith(user_id)]
    update_github_file(BAN_FILE, "\n".join(new_lines), ban_sha)
    embed = discord.Embed(title="✅ User Unbanned", description=f"**{roblox_name}** has been unbanned.", color=COLORS["success"])
    embed.timestamp = datetime.utcnow()
    await interaction.followup.send(embed=embed)

# =============================================
#   /check
# =============================================
@tree.command(name="check", description="Check if a Roblox user is whitelisted")
@app_commands.describe(username="Roblox username to check")
@app_commands.autocomplete(username=username_autocomplete)
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
        embed = discord.Embed(title="🔨 User is Banned", description=f"**{roblox_name}** is banned.", color=COLORS["error"])
    elif found:
        uid, date, rname, discord_str, note, expiry = parse_entry(found)
        expired = is_expired(expiry)
        embed = discord.Embed(
            title="⚠️ Expired" if expired else "✅ Whitelisted",
            color=COLORS["warning"] if expired else COLORS["success"]
        )
        embed.add_field(name="Roblox", value=roblox_name, inline=True)
        embed.add_field(name="Discord", value=f"<@{discord_str}>" if discord_str and discord_str != "none" else "Not set", inline=True)
        embed.add_field(name="Added", value=date, inline=True)
        embed.add_field(name="Note", value=note or "None", inline=True)
        embed.add_field(name="Expires", value=expiry if expiry != "never" else "Never", inline=True)
        embed.add_field(name="Status", value="⚠️ EXPIRED" if expired else "✅ Active", inline=True)
    else:
        embed = discord.Embed(title="❌ Not Whitelisted", description=f"**{roblox_name}** does not have access.", color=COLORS["ban"])
    if avatar:
        embed.set_thumbnail(url=avatar)
    embed.set_footer(text="Whitelist Bot")
    embed.timestamp = datetime.utcnow()
    await interaction.followup.send(embed=embed)

# =============================================
#   /list
# =============================================
@tree.command(name="list", description="Show all whitelisted users")
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
    embeds = []
    for i, line in enumerate(entries):
        uid, date, roblox_name, discord_str, note, expiry = parse_entry(line)
        name = roblox_name if roblox_name else uid
        expired = is_expired(expiry)
        status = "⚠️ Expired" if expired else "✅ Active"
        avatar = get_roblox_avatar(uid)
        entry_embed = discord.Embed(
            title=f"{'⚠️' if expired else '✅'} {name}",
            color=COLORS["warning"] if expired else COLORS["success"]
        )
        entry_embed.add_field(name="Discord", value=f"<@{discord_str}>" if discord_str and discord_str != "none" else "Not set", inline=True)
        entry_embed.add_field(name="Note", value=note or "None", inline=True)
        entry_embed.add_field(name="Status", value=status, inline=True)
        if avatar:
            entry_embed.set_thumbnail(url=avatar)
        embeds.append(entry_embed)
    summary = discord.Embed(
        title="📋 Whitelist Summary",
        color=COLORS["info"]
    )
    summary.add_field(name="✅ Whitelisted", value=str(len(entries)), inline=True)
    summary.add_field(name="🔨 Banned", value=str(len(ban_entries)), inline=True)
    summary.set_footer(text="Whitelist Bot • Powered by GitHub")
    summary.timestamp = datetime.utcnow()
    await interaction.followup.send(embed=summary)
    for e in embeds[:10]:
        await interaction.followup.send(embed=e)

# =============================================
#   /note
# =============================================
@tree.command(name="note", description="Add or update a note for a whitelisted user")
@app_commands.describe(username="Roblox username", note="Note to add")
@app_commands.autocomplete(username=username_autocomplete)
async def add_note(interaction: discord.Interaction, username: str, note: str):
    if not owner_only(interaction):
        embed = discord.Embed(title="🚫 Access Denied", description="Only the owner can use this.", color=COLORS["error"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    await interaction.response.defer()
    user_id, roblox_name = get_roblox_user_by_username(username)
    if not user_id:
        embed = discord.Embed(title="❌ User Not Found", description=f"Could not find **{username}**.", color=COLORS["error"])
        await interaction.followup.send(embed=embed)
        return
    lines, sha, content = get_github_file(GITHUB_FILE)
    ids = get_ids_only(lines)
    if user_id not in ids:
        embed = discord.Embed(title="❌ Not Whitelisted", description=f"**{roblox_name}** is not in the whitelist.", color=COLORS["error"])
        await interaction.followup.send(embed=embed)
        return
    new_lines = []
    for line in lines:
        if line.startswith(user_id):
            uid, date, rname, discord_str, old_note, expiry = parse_entry(line)
            new_lines.append(f"{uid} | {date} | {rname} | {discord_str or 'none'} | {note} | {expiry or 'never'}")
        else:
            new_lines.append(line)
    update_github_file(GITHUB_FILE, "\n".join(new_lines), sha)
    embed = discord.Embed(title="📝 Note Updated", description=f"Note for **{roblox_name}** updated to: {note}", color=COLORS["success"])
    embed.timestamp = datetime.utcnow()
    await interaction.followup.send(embed=embed)

# =============================================
#   /setrole
# =============================================
@tree.command(name="setrole", description="Set the role to give whitelisted users")
@app_commands.describe(role="The role to give when someone is whitelisted")
async def set_role(interaction: discord.Interaction, role: discord.Role):
    if not owner_only(interaction):
        embed = discord.Embed(title="🚫 Access Denied", description="Only the owner can use this.", color=COLORS["error"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    global WHITELIST_ROLE_ID
    WHITELIST_ROLE_ID = role.id
    embed = discord.Embed(title="✅ Role Set", description=f"Whitelisted users will now receive **{role.name}**.", color=COLORS["success"])
    embed.timestamp = datetime.utcnow()
    await interaction.response.send_message(embed=embed)

# =============================================
#   /setlog
# =============================================
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

# =============================================
#   /backup
# =============================================
@tree.command(name="backup", description="Save a backup of the whitelist")
async def backup(interaction: discord.Interaction):
    if not owner_only(interaction):
        embed = discord.Embed(title="🚫 Access Denied", description="Only the owner can use this.", color=COLORS["error"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    await interaction.response.defer()
    lines, sha, content = get_github_file(GITHUB_FILE)
    date = datetime.utcnow().strftime("%Y-%m-%d_%H-%M")
    backup_filename = f"backup_{date}.txt"
    update_github_file(backup_filename, content, None)
    embed = discord.Embed(
        title="💾 Backup Created",
        description=f"Whitelist backed up to `{backup_filename}` on GitHub.",
        color=COLORS["success"]
    )
    embed.add_field(name="Total Users", value=str(len(get_ids_only(lines))), inline=True)
    embed.timestamp = datetime.utcnow()
    await interaction.followup.send(embed=embed)

# =============================================
#   /rename
# =============================================
@tree.command(name="rename", description="Update a user's Roblox username")
@app_commands.describe(old_username="Current username", new_username="New username")
@app_commands.autocomplete(old_username=username_autocomplete)
async def rename_user(interaction: discord.Interaction, old_username: str, new_username: str):
    if not owner_only(interaction):
        embed = discord.Embed(title="🚫 Access Denied", description="Only the owner can use this.", color=COLORS["error"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    await interaction.response.defer()
    old_id, old_name = get_roblox_user_by_username(old_username)
    new_id, new_name = get_roblox_user_by_username(new_username)
    if not old_id:
        embed = discord.Embed(title="❌ Not Found", description=f"Could not find **{old_username}**.", color=COLORS["error"])
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
            uid, old_date, rname, discord_str, note, expiry = parse_entry(line)
            new_lines.append(f"{new_id or old_id} | {old_date} | {new_name or old_name} | {discord_str or 'none'} | {note or 'none'} | {expiry or 'never'}")
        else:
            new_lines.append(line)
    update_github_file(GITHUB_FILE, "\n".join(new_lines), sha)
    embed = discord.Embed(
        title="🔄 User Updated",
        description=f"**Old:** {old_name}\n**New:** {new_name or old_name}",
        color=COLORS["blue"]
    )
    embed.timestamp = datetime.utcnow()
    await interaction.followup.send(embed=embed)
    await send_log(embed)

# =============================================
#   /help
# =============================================
@tree.command(name="help", description="Show all available commands")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📖 Whitelist Bot Commands",
        description="All commands use **/** slash commands",
        color=COLORS["purple"]
    )
    embed.add_field(name="/add [username]", value="➕ Add user + Discord + note + expiry days", inline=False)
    embed.add_field(name="/remove [username]", value="➖ Remove user with confirm button", inline=False)
    embed.add_field(name="/check [username]", value="🔍 Check user status + expiry", inline=False)
    embed.add_field(name="/rename [old] [new]", value="🔄 Update a username", inline=False)
    embed.add_field(name="/note [username] [note]", value="📝 Add a note to a user", inline=False)
    embed.add_field(name="/list", value="📋 Show all users with avatars", inline=False)
    embed.add_field(name="/ban [username]", value="🔨 Ban with confirm button", inline=False)
    embed.add_field(name="/unban [username]", value="✅ Unban a user", inline=False)
    embed.add_field(name="/setrole [role]", value="👑 Set role for whitelisted users", inline=False)
    embed.add_field(name="/setlog", value="📋 Set log channel", inline=False)
    embed.add_field(name="/backup", value="💾 Backup whitelist to GitHub", inline=False)
    embed.add_field(name="/help", value="📖 Show this message", inline=False)
    embed.set_footer(text="Whitelist Bot • Only owner can use commands")
    embed.timestamp = datetime.utcnow()
    await interaction.response.send_message(embed=embed)

print("Starting bot...")
client.run(TOKEN)
