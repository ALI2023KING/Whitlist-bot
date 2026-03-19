import discord
from discord import app_commands
import os
import requests
import base64
import json
import random
import string
from datetime import datetime, timedelta

TOKEN = os.environ.get("TOKEN")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
OWNER_ID = 1449777458218926243

GITHUB_REPO = "ALI2023KING/Whitlist-sys"
GITHUB_FILE = "whitelist.txt"
BAN_FILE = "banlist.txt"
KEY_FILE = "keys.txt"
SCRIPT_FILE = "script.txt"

LOG_CHANNEL_ID = None
PANEL_CHANNEL_ID = None
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
    "blue": 0x00BFFF,
    "gold": 0xFFD700
}

# =============================================
#   GITHUB HELPERS
# =============================================
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

# =============================================
#   ROBLOX HELPERS
# =============================================
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

# =============================================
#   PARSE HELPERS
# =============================================
def parse_entry(line):
    parts = line.split("|")
    user_id = parts[0].strip() if len(parts) > 0 else ""
    date = parts[1].strip() if len(parts) > 1 else "Unknown"
    roblox_name = parts[2].strip() if len(parts) > 2 else None
    discord_user = parts[3].strip() if len(parts) > 3 else None
    note = parts[4].strip() if len(parts) > 4 else None
    expiry = parts[5].strip() if len(parts) > 5 else None
    uses = parts[6].strip() if len(parts) > 6 else "0"
    return user_id, date, roblox_name, discord_user, note, expiry, uses

def parse_key(line):
    parts = line.split("|")
    key = parts[0].strip() if len(parts) > 0 else ""
    date = parts[1].strip() if len(parts) > 1 else ""
    used = parts[2].strip() if len(parts) > 2 else "false"
    max_uses = parts[3].strip() if len(parts) > 3 else "1"
    expiry = parts[4].strip() if len(parts) > 4 else "never"
    days = parts[5].strip() if len(parts) > 5 else "never"
    return key, date, used, max_uses, expiry, days

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

def generate_key():
    parts = ["VOID"] + ["".join(random.choices(string.ascii_uppercase + string.digits, k=4)) for _ in range(3)]
    return "-".join(parts)

def is_on_cooldown(user_id):
    if user_id in cooldowns:
        if datetime.utcnow() < cooldowns[user_id]:
            return True
    cooldowns[user_id] = datetime.utcnow() + timedelta(seconds=COOLDOWN_SECONDS)
    return False

# =============================================
#   LOG AND ROLE HELPERS
# =============================================
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

# =============================================
#   AUTOCOMPLETE
# =============================================
async def username_autocomplete(interaction: discord.Interaction, current: str):
    lines, _, _ = get_github_file(GITHUB_FILE)
    choices = []
    for line in lines:
        uid, date, roblox_name, discord_user, note, expiry, uses = parse_entry(line)
        if roblox_name and current.lower() in roblox_name.lower():
            choices.append(app_commands.Choice(name=roblox_name, value=roblox_name))
        if len(choices) >= 25:
            break
    return choices

# =============================================
#   CONFIRM VIEW
# =============================================
class ConfirmView(discord.ui.View):
    def __init__(self, action):
        super().__init__(timeout=30)
        self.action = action

    @discord.ui.button(label="✅ Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.action(interaction)
        self.stop()

    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="❌ Cancelled", description="Action cancelled.", color=COLORS["error"])
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()

# =============================================
#   PANEL VIEW
# =============================================
class PanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔑 Redeem Key", style=discord.ButtonStyle.green, custom_id="redeem_key")
    async def redeem_key(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RedeemKeyModal())

    @discord.ui.button(label="📜 Get Script", style=discord.ButtonStyle.blurple, custom_id="get_script")
    async def get_script(self, interaction: discord.Interaction, button: discord.ui.Button):
        lines, _, _ = get_github_file(GITHUB_FILE)
        ids = get_ids_only(lines)
        roblox_id = None
        for line in lines:
            uid, date, roblox_name, discord_str, note, expiry, uses = parse_entry(line)
            if discord_str and discord_str == str(interaction.user.id):
                roblox_id = uid
                if is_expired(expiry):
                    embed = discord.Embed(title="⚠️ Access Expired", description="Your whitelist has expired. Please contact the owner.", color=COLORS["warning"])
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return
                break
        if not roblox_id:
            embed = discord.Embed(title="❌ Not Whitelisted", description="You are not whitelisted. Redeem a key to get access.", color=COLORS["error"])
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        script_lines, _, script_content = get_github_file(SCRIPT_FILE)
        if not script_content:
            embed = discord.Embed(title="❌ No Script", description="No script has been set yet. Contact the owner.", color=COLORS["error"])
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        try:
            dm_embed = discord.Embed(title="📜 Your Script", description=f"```lua\n{script_content[:1900]}\n```", color=COLORS["success"])
            dm_embed.set_footer(text="Do not share this script!")
            await interaction.user.send(embed=dm_embed)
            embed = discord.Embed(title="✅ Script Sent", description="Check your DMs for your script!", color=COLORS["success"])
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except:
            embed = discord.Embed(title="❌ DM Failed", description="Could not send DM. Please enable DMs from server members.", color=COLORS["error"])
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="👤 Get Role", style=discord.ButtonStyle.blurple, custom_id="get_role")
    async def get_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        lines, _, _ = get_github_file(GITHUB_FILE)
        for line in lines:
            uid, date, roblox_name, discord_str, note, expiry, uses = parse_entry(line)
            if discord_str and discord_str == str(interaction.user.id):
                if is_expired(expiry):
                    embed = discord.Embed(title="⚠️ Access Expired", description="Your whitelist has expired.", color=COLORS["warning"])
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return
                await give_whitelist_role(interaction.guild, interaction.user.id)
                embed = discord.Embed(title="✅ Role Given", description="Your whitelist role has been assigned!", color=COLORS["success"])
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
        embed = discord.Embed(title="❌ Not Whitelisted", description="You are not whitelisted.", color=COLORS["error"])
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="📊 Get Stats", style=discord.ButtonStyle.grey, custom_id="get_stats")
    async def get_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        lines, _, _ = get_github_file(GITHUB_FILE)
        for line in lines:
            uid, date, roblox_name, discord_str, note, expiry, uses = parse_entry(line)
            if discord_str and discord_str == str(interaction.user.id):
                expired = is_expired(expiry)
                embed = discord.Embed(title="📊 Your Stats", color=COLORS["info"])
                embed.add_field(name="Roblox", value=roblox_name or uid, inline=True)
                embed.add_field(name="Status", value="⚠️ Expired" if expired else "✅ Active", inline=True)
                embed.add_field(name="Added", value=date, inline=True)
                embed.add_field(name="Expires", value=expiry if expiry and expiry != "never" else "Never", inline=True)
                embed.add_field(name="Note", value=note or "None", inline=True)
                avatar = get_roblox_avatar(uid)
                if avatar:
                    embed.set_thumbnail(url=avatar)
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
        embed = discord.Embed(title="❌ Not Whitelisted", description="You are not whitelisted.", color=COLORS["error"])
        await interaction.response.send_message(embed=embed, ephemeral=True)

# =============================================
#   REDEEM KEY MODAL
# =============================================
class RedeemKeyModal(discord.ui.Modal, title="Redeem Key"):
    key_input = discord.ui.TextInput(
        label="Enter your key",
        placeholder="VOID-XXXX-XXXX-XXXX",
        required=True
    )
    roblox_input = discord.ui.TextInput(
        label="Your Roblox username",
        placeholder="Your Roblox username",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        key = self.key_input.value.strip().upper()
        roblox_username = self.roblox_input.value.strip()
        key_lines, key_sha, key_content = get_github_file(KEY_FILE)
        found_key = None
        for line in key_lines:
            k, date, used, max_uses, expiry, days = parse_key(line)
            if k == key:
                found_key = line
                break
        if not found_key:
            embed = discord.Embed(title="❌ Invalid Key", description="This key does not exist.", color=COLORS["error"])
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        k, date, used, max_uses, expiry, days = parse_key(found_key)
        if used == "true" and max_uses == "1":
            embed = discord.Embed(title="❌ Key Already Used", description="This key has already been redeemed.", color=COLORS["error"])
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        if is_expired(expiry):
            embed = discord.Embed(title="❌ Key Expired", description="This key has expired.", color=COLORS["error"])
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        user_id, roblox_name = get_roblox_user_by_username(roblox_username)
        if not user_id:
            embed = discord.Embed(title="❌ Roblox User Not Found", description=f"Could not find **{roblox_username}** on Roblox.", color=COLORS["error"])
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        wl_lines, wl_sha, wl_content = get_github_file(GITHUB_FILE)
        ids = get_ids_only(wl_lines)
        if user_id in ids:
            embed = discord.Embed(title="⚠️ Already Whitelisted", description=f"**{roblox_name}** is already whitelisted.", color=COLORS["warning"])
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        add_date = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        expiry_date = "never"
        if days and days != "never":
            try:
                expiry_dt = datetime.utcnow() + timedelta(days=int(days))
                expiry_date = expiry_dt.strftime("%Y-%m-%d %H:%M")
            except:
                pass
        new_entry = f"{user_id} | {add_date} | {roblox_name} | {interaction.user.id} | Redeemed key | {expiry_date} | 0"
        new_wl_content = wl_content.strip() + f"\n{new_entry}"
        update_github_file(GITHUB_FILE, new_wl_content, wl_sha)
        new_key_lines = []
        for line in key_lines:
            k2, d2, u2, m2, e2, dy2 = parse_key(line)
            if k2 == key:
                new_key_lines.append(f"{k2} | {d2} | true | {m2} | {e2} | {dy2}")
            else:
                new_key_lines.append(line)
        update_github_file(KEY_FILE, "\n".join(new_key_lines), key_sha)
        await give_whitelist_role(interaction.guild, interaction.user.id)
        avatar = get_roblox_avatar(user_id)
        embed = discord.Embed(
            title="✅ Key Redeemed!",
            description=f"Welcome **{roblox_name}**! You now have access.",
            color=COLORS["success"]
        )
        embed.add_field(name="Roblox", value=roblox_name, inline=True)
        embed.add_field(name="Expires", value=expiry_date if expiry_date != "never" else "Never", inline=True)
        if avatar:
            embed.set_thumbnail(url=avatar)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        if LOG_CHANNEL_ID:
            log_embed = discord.Embed(
                title="🔑 Key Redeemed",
                description=f"**{roblox_name}** redeemed key `{key}`",
                color=COLORS["success"]
            )
            log_embed.add_field(name="Discord", value=interaction.user.mention, inline=True)
            log_embed.timestamp = datetime.utcnow()
            await send_log(log_embed)

# =============================================
#   ON READY
# =============================================
@client.event
async def on_ready():
    await tree.sync()
    client.add_view(PanelView())
    await client.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="👑 Whitelist System"
        )
    )
    print(f"Bot is online as {client.user}")

# =============================================
#   /panel
# =============================================
@tree.command(name="panel", description="Send the whitelist control panel")
async def panel(interaction: discord.Interaction):
    if not owner_only(interaction):
        embed = discord.Embed(title="🚫 Access Denied", color=COLORS["error"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    embed = discord.Embed(
        title="👑 VOIDHUB WHITELIST SYSTEM",
        description="Welcome! If you have a key, click **Redeem Key** to get access.\nAlready whitelisted? Use the buttons below.",
        color=COLORS["gold"]
    )
    embed.add_field(name="🔑 Redeem Key", value="Enter your key to get whitelisted", inline=False)
    embed.add_field(name="📜 Get Script", value="Get your script sent via DM", inline=False)
    embed.add_field(name="👤 Get Role", value="Claim your whitelist role", inline=False)
    embed.add_field(name="📊 Get Stats", value="View your whitelist stats", inline=False)
    embed.set_footer(text="VoidHub Whitelist • Powered by GitHub")
    embed.timestamp = datetime.utcnow()
    await interaction.response.send_message(embed=embed, view=PanelView())

# =============================================
#   /add
# =============================================
@tree.command(name="add", description="Add a Roblox user to the whitelist")
@app_commands.describe(
    username="Roblox username",
    discord_user="Their Discord user",
    note="Note about this user",
    days="Days of access (empty for permanent)"
)
async def add_user(interaction: discord.Interaction, username: str, discord_user: discord.Member = None, note: str = None, days: int = None):
    if not owner_only(interaction):
        embed = discord.Embed(title="🚫 Access Denied", color=COLORS["error"])
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
    new_entry = f"{user_id} | {date} | {roblox_name} | {discord_str} | {note_str} | {expiry} | 0"
    new_content = content.strip() + f"\n{new_entry}"
    update_github_file(GITHUB_FILE, new_content, sha)
    avatar = get_roblox_avatar(user_id)
    embed = discord.Embed(title="✅ User Whitelisted", color=COLORS["success"])
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
                description=f"You now have access.\n**Roblox:** {roblox_name}\n**Expires:** {expiry if expiry != 'never' else 'Never'}",
                color=COLORS["success"]
            )
            await discord_user.send(embed=dm_embed)
        except:
            pass

# =============================================
#   /remove
# =============================================
@tree.command(name="remove", description="Remove a user from the whitelist")
@app_commands.describe(username="Roblox username to remove")
@app_commands.autocomplete(username=username_autocomplete)
async def remove_user(interaction: discord.Interaction, username: str):
    if not owner_only(interaction):
        embed = discord.Embed(title="🚫 Access Denied", color=COLORS["error"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    await interaction.response.defer()
    user_id, roblox_name = get_roblox_user_by_username(username)
    if not user_id:
        embed = discord.Embed(title="❌ User Not Found", color=COLORS["error"])
        await interaction.followup.send(embed=embed)
        return
    lines, sha, content = get_github_file(GITHUB_FILE)
    ids = get_ids_only(lines)
    if user_id not in ids:
        embed = discord.Embed(title="❌ Not Found", description=f"**{roblox_name}** is not whitelisted.", color=COLORS["error"])
        await interaction.followup.send(embed=embed)
        return
    found_line = next((l for l in lines if l.startswith(user_id)), None)
    uid, date, rname, discord_str, note, expiry, uses = parse_entry(found_line) if found_line else (user_id, "", roblox_name, None, None, None, "0")
    avatar = get_roblox_avatar(user_id)
    confirm_embed = discord.Embed(title="⚠️ Confirm Remove", description=f"Remove **{roblox_name}**?", color=COLORS["warning"])
    if avatar:
        confirm_embed.set_thumbnail(url=avatar)

    async def do_remove(i: discord.Interaction):
        new_lines = [l for l in lines if not l.startswith(user_id)]
        update_github_file(GITHUB_FILE, "\n".join(new_lines), sha)
        result_embed = discord.Embed(title="🗑️ User Removed", description=f"**{roblox_name}** removed.", color=COLORS["ban"])
        result_embed.timestamp = datetime.utcnow()
        await i.response.edit_message(embed=result_embed, view=None)
        await send_log(result_embed)
        if discord_str and discord_str != "none":
            await remove_whitelist_role(i.guild, discord_str)
            try:
                member = i.guild.get_member(int(discord_str))
                if member:
                    dm_embed = discord.Embed(title="❌ Whitelist Removed", description="Your access has been removed.", color=COLORS["error"])
                    await member.send(embed=dm_embed)
            except:
                pass

    view = ConfirmView(do_remove)
    await interaction.followup.send(embed=confirm_embed, view=view)

# =============================================
#   /ban
# =============================================
@tree.command(name="ban", description="Ban a Roblox user")
@app_commands.describe(username="Roblox username to ban")
@app_commands.autocomplete(username=username_autocomplete)
async def ban_user(interaction: discord.Interaction, username: str):
    if not owner_only(interaction):
        embed = discord.Embed(title="🚫 Access Denied", color=COLORS["error"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    await interaction.response.defer()
    user_id, roblox_name = get_roblox_user_by_username(username)
    if not user_id:
        embed = discord.Embed(title="❌ User Not Found", color=COLORS["error"])
        await interaction.followup.send(embed=embed)
        return
    ban_lines, ban_sha, ban_content = get_github_file(BAN_FILE)
    ban_ids = get_ids_only(ban_lines)
    if user_id in ban_ids:
        embed = discord.Embed(title="⚠️ Already Banned", color=COLORS["warning"])
        await interaction.followup.send(embed=embed)
        return
    avatar = get_roblox_avatar(user_id)
    confirm_embed = discord.Embed(title="⚠️ Confirm Ban", description=f"Ban **{roblox_name}**?", color=COLORS["warning"])
    if avatar:
        confirm_embed.set_thumbnail(url=avatar)

    async def do_ban(i: discord.Interaction):
        lines, sha, content = get_github_file(GITHUB_FILE)
        found_line = next((l for l in lines if l.startswith(user_id)), None)
        discord_str = None
        if found_line:
            _, _, _, discord_str, _, _, _ = parse_entry(found_line)
            new_lines = [l for l in lines if not l.startswith(user_id)]
            update_github_file(GITHUB_FILE, "\n".join(new_lines), sha)
        date = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        new_ban = ban_content.strip() + f"\n{user_id} | {date} | {roblox_name}"
        update_github_file(BAN_FILE, new_ban, ban_sha)
        result_embed = discord.Embed(title="🔨 User Banned", description=f"**{roblox_name}** has been banned.", color=COLORS["error"])
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
                    dm_embed = discord.Embed(title="🔨 You have been Banned", description="You have been banned from the whitelist.", color=COLORS["error"])
                    await member.send(embed=dm_embed)
            except:
                pass

    view = ConfirmView(do_ban)
    await interaction.followup.send(embed=confirm_embed, view=view)

# =============================================
#   /unban
# =============================================
@tree.command(name="unban", description="Unban a Roblox user")
@app_commands.describe(username="Roblox username to unban")
async def unban_user(interaction: discord.Interaction, username: str):
    if not owner_only(interaction):
        embed = discord.Embed(title="🚫 Access Denied", color=COLORS["error"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    await interaction.response.defer()
    user_id, roblox_name = get_roblox_user_by_username(username)
    if not user_id:
        embed = discord.Embed(title="❌ User Not Found", color=COLORS["error"])
        await interaction.followup.send(embed=embed)
        return
    ban_lines, ban_sha, _ = get_github_file(BAN_FILE)
    ban_ids = get_ids_only(ban_lines)
    if user_id not in ban_ids:
        embed = discord.Embed(title="❌ Not Banned", color=COLORS["error"])
        await interaction.followup.send(embed=embed)
        return
    new_lines = [l for l in ban_lines if not l.startswith(user_id)]
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
        embed = discord.Embed(title="🚫 Access Denied", color=COLORS["error"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    await interaction.response.defer()
    user_id, roblox_name = get_roblox_user_by_username(username)
    if not user_id:
        embed = discord.Embed(title="❌ User Not Found", color=COLORS["error"])
        await interaction.followup.send(embed=embed)
        return
    lines, _, _ = get_github_file(GITHUB_FILE)
    ban_lines, _, _ = get_github_file(BAN_FILE)
    ban_ids = get_ids_only(ban_lines)
    found = next((l for l in lines if l.startswith(user_id)), None)
    avatar = get_roblox_avatar(user_id)
    if user_id in ban_ids:
        embed = discord.Embed(title="🔨 User is Banned", description=f"**{roblox_name}** is banned.", color=COLORS["error"])
    elif found:
        uid, date, rname, discord_str, note, expiry, uses = parse_entry(found)
        expired = is_expired(expiry)
        embed = discord.Embed(title="⚠️ Expired" if expired else "✅ Whitelisted", color=COLORS["warning"] if expired else COLORS["success"])
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
        embed = discord.Embed(title="🚫 Access Denied", color=COLORS["error"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    await interaction.response.defer()
    lines, _, _ = get_github_file(GITHUB_FILE)
    ban_lines, _, _ = get_github_file(BAN_FILE)
    entries = [l for l in lines if not l.startswith("--")]
    ban_entries = [l for l in ban_lines if not l.startswith("--")]
    if not entries:
        embed = discord.Embed(title="📋 Whitelist", description="Empty.", color=COLORS["info"])
        await interaction.followup.send(embed=embed)
        return
    summary = discord.Embed(title="📋 Whitelist Summary", color=COLORS["info"])
    summary.add_field(name="✅ Whitelisted", value=str(len(entries)), inline=True)
    summary.add_field(name="🔨 Banned", value=str(len(ban_entries)), inline=True)
    summary.set_footer(text="Whitelist Bot • Powered by GitHub")
    summary.timestamp = datetime.utcnow()
    await interaction.followup.send(embed=summary)
    for line in entries[:10]:
        uid, date, roblox_name, discord_str, note, expiry, uses = parse_entry(line)
        name = roblox_name if roblox_name else uid
        expired = is_expired(expiry)
        entry_embed = discord.Embed(
            title=f"{'⚠️' if expired else '✅'} {name}",
            color=COLORS["warning"] if expired else COLORS["success"]
        )
        entry_embed.add_field(name="Discord", value=f"<@{discord_str}>" if discord_str and discord_str != "none" else "Not set", inline=True)
        entry_embed.add_field(name="Note", value=note or "None", inline=True)
        entry_embed.add_field(name="Status", value="⚠️ Expired" if expired else "✅ Active", inline=True)
        avatar = get_roblox_avatar(uid)
        if avatar:
            entry_embed.set_thumbnail(url=avatar)
        await interaction.followup.send(embed=entry_embed)

# =============================================
#   /genkey
# =============================================
@tree.command(name="genkey", description="Generate a whitelist key")
@app_commands.describe(
    max_uses="How many times the key can be used",
    days_access="Days of access the key gives",
    expiry_days="Days until the key expires"
)
async def gen_key(interaction: discord.Interaction, max_uses: int = 1, days_access: int = None, expiry_days: int = None):
    if not owner_only(interaction):
        embed = discord.Embed(title="🚫 Access Denied", color=COLORS["error"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    await interaction.response.defer()
    key = generate_key()
    date = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    expiry = "never"
    if expiry_days:
        expiry_dt = datetime.utcnow() + timedelta(days=expiry_days)
        expiry = expiry_dt.strftime("%Y-%m-%d %H:%M")
    days_str = str(days_access) if days_access else "never"
    key_lines, key_sha, key_content = get_github_file(KEY_FILE)
    new_entry = f"{key} | {date} | false | {max_uses} | {expiry} | {days_str}"
    new_content = key_content.strip() + f"\n{new_entry}"
    update_github_file(KEY_FILE, new_content, key_sha)
    embed = discord.Embed(title="🔑 Key Generated", color=COLORS["gold"])
    embed.add_field(name="Key", value=f"`{key}`", inline=False)
    embed.add_field(name="Max Uses", value=str(max_uses), inline=True)
    embed.add_field(name="Access Duration", value=f"{days_access} days" if days_access else "Permanent", inline=True)
    embed.add_field(name="Key Expires", value=expiry if expiry != "never" else "Never", inline=True)
    embed.set_footer(text="Share this key carefully!")
    embed.timestamp = datetime.utcnow()
    await interaction.followup.send(embed=embed, ephemeral=True)

# =============================================
#   /keylist
# =============================================
@tree.command(name="keylist", description="Show all generated keys")
async def key_list(interaction: discord.Interaction):
    if not owner_only(interaction):
        embed = discord.Embed(title="🚫 Access Denied", color=COLORS["error"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    key_lines, _, _ = get_github_file(KEY_FILE)
    if not key_lines:
        embed = discord.Embed(title="🔑 Keys", description="No keys generated.", color=COLORS["info"])
        await interaction.followup.send(embed=embed, ephemeral=True)
        return
    desc = ""
    for line in key_lines:
        k, date, used, max_uses, expiry, days = parse_key(line)
        status = "✅ Available" if used == "false" else "❌ Used"
        if is_expired(expiry):
            status = "⚠️ Expired"
        desc += f"`{k}` — {status} — Max uses: {max_uses}\n"
    embed = discord.Embed(title="🔑 All Keys", description=desc, color=COLORS["gold"])
    embed.add_field(name="Total Keys", value=str(len(key_lines)), inline=True)
    embed.timestamp = datetime.utcnow()
    await interaction.followup.send(embed=embed, ephemeral=True)

# =============================================
#   /revokekey
# =============================================
@tree.command(name="revokekey", description="Delete a key")
@app_commands.describe(key="Key to revoke")
async def revoke_key(interaction: discord.Interaction, key: str):
    if not owner_only(interaction):
        embed = discord.Embed(title="🚫 Access Denied", color=COLORS["error"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    await interaction.response.defer()
    key_lines, key_sha, _ = get_github_file(KEY_FILE)
    key_upper = key.strip().upper()
    found = any(parse_key(l)[0] == key_upper for l in key_lines)
    if not found:
        embed = discord.Embed(title="❌ Key Not Found", color=COLORS["error"])
        await interaction.followup.send(embed=embed)
        return
    new_lines = [l for l in key_lines if parse_key(l)[0] != key_upper]
    update_github_file(KEY_FILE, "\n".join(new_lines), key_sha)
    embed = discord.Embed(title="🗑️ Key Revoked", description=f"`{key_upper}` has been deleted.", color=COLORS["ban"])
    embed.timestamp = datetime.utcnow()
    await interaction.followup.send(embed=embed)

# =============================================
#   /setscript
# =============================================
@tree.command(name="setscript", description="Set the script that gets sent to whitelisted users")
@app_commands.describe(script="The script content or loadstring URL")
async def set_script(interaction: discord.Interaction, script: str):
    if not owner_only(interaction):
        embed = discord.Embed(title="🚫 Access Denied", color=COLORS["error"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    _, sha, _ = get_github_file(SCRIPT_FILE)
    update_github_file(SCRIPT_FILE, script, sha)
    embed = discord.Embed(title="✅ Script Set", description="Script has been saved. Users can now get it via the panel.", color=COLORS["success"])
    embed.timestamp = datetime.utcnow()
    await interaction.followup.send(embed=embed, ephemeral=True)

# =============================================
#   /note
# =============================================
@tree.command(name="note", description="Add a note to a whitelisted user")
@app_commands.describe(username="Roblox username", note="Note to add")
@app_commands.autocomplete(username=username_autocomplete)
async def add_note(interaction: discord.Interaction, username: str, note: str):
    if not owner_only(interaction):
        embed = discord.Embed(title="🚫 Access Denied", color=COLORS["error"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    await interaction.response.defer()
    user_id, roblox_name = get_roblox_user_by_username(username)
    if not user_id:
        embed = discord.Embed(title="❌ User Not Found", color=COLORS["error"])
        await interaction.followup.send(embed=embed)
        return
    lines, sha, content = get_github_file(GITHUB_FILE)
    ids = get_ids_only(lines)
    if user_id not in ids:
        embed = discord.Embed(title="❌ Not Whitelisted", color=COLORS["error"])
        await interaction.followup.send(embed=embed)
        return
    new_lines = []
    for line in lines:
        if line.startswith(user_id):
            uid, date, rname, discord_str, old_note, expiry, uses = parse_entry(line)
            new_lines.append(f"{uid} | {date} | {rname} | {discord_str or 'none'} | {note} | {expiry or 'never'} | {uses or '0'}")
        else:
            new_lines.append(line)
    update_github_file(GITHUB_FILE, "\n".join(new_lines), sha)
    embed = discord.Embed(title="📝 Note Updated", description=f"Note for **{roblox_name}**: {note}", color=COLORS["success"])
    embed.timestamp = datetime.utcnow()
    await interaction.followup.send(embed=embed)

# =============================================
#   /setrole
# =============================================
@tree.command(name="setrole", description="Set the role for whitelisted users")
@app_commands.describe(role="The whitelist role")
async def set_role(interaction: discord.Interaction, role: discord.Role):
    if not owner_only(interaction):
        embed = discord.Embed(title="🚫 Access Denied", color=COLORS["error"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    global WHITELIST_ROLE_ID
    WHITELIST_ROLE_ID = role.id
    embed = discord.Embed(title="✅ Role Set", description=f"Whitelisted users will receive **{role.name}**.", color=COLORS["success"])
    embed.timestamp = datetime.utcnow()
    await interaction.response.send_message(embed=embed)

# =============================================
#   /setlog
# =============================================
@tree.command(name="setlog", description="Set this channel as the log channel")
async def set_log(interaction: discord.Interaction):
    if not owner_only(interaction):
        embed = discord.Embed(title="🚫 Access Denied", color=COLORS["error"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    global LOG_CHANNEL_ID
    LOG_CHANNEL_ID = interaction.channel_id
    embed = discord.Embed(title="📋 Log Channel Set", description="This channel will receive all logs.", color=COLORS["success"])
    embed.timestamp = datetime.utcnow()
    await interaction.response.send_message(embed=embed)

# =============================================
#   /backup
# =============================================
@tree.command(name="backup", description="Backup the whitelist")
async def backup(interaction: discord.Interaction):
    if not owner_only(interaction):
        embed = discord.Embed(title="🚫 Access Denied", color=COLORS["error"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    await interaction.response.defer()
    lines, sha, content = get_github_file(GITHUB_FILE)
    date = datetime.utcnow().strftime("%Y-%m-%d_%H-%M")
    backup_filename = f"backup_{date}.txt"
    update_github_file(backup_filename, content, None)
    embed = discord.Embed(title="💾 Backup Created", description=f"Saved to `{backup_filename}` on GitHub.", color=COLORS["success"])
    embed.add_field(name="Total Users", value=str(len(get_ids_only(lines))), inline=True)
    embed.timestamp = datetime.utcnow()
    await interaction.followup.send(embed=embed)

# =============================================
#   /rename
# =============================================
@tree.command(name="rename", description="Update a username in the whitelist")
@app_commands.describe(old_username="Current username", new_username="New username")
@app_commands.autocomplete(old_username=username_autocomplete)
async def rename_user(interaction: discord.Interaction, old_username: str, new_username: str):
    if not owner_only(interaction):
        embed = discord.Embed(title="🚫 Access Denied", color=COLORS["error"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    await interaction.response.defer()
    old_id, old_name = get_roblox_user_by_username(old_username)
    new_id, new_name = get_roblox_user_by_username(new_username)
    if not old_id:
        embed = discord.Embed(title="❌ Not Found", color=COLORS["error"])
        await interaction.followup.send(embed=embed)
        return
    lines, sha, content = get_github_file(GITHUB_FILE)
    ids = get_ids_only(lines)
    if old_id not in ids:
        embed = discord.Embed(title="❌ Not Whitelisted", color=COLORS["error"])
        await interaction.followup.send(embed=embed)
        return
    new_lines = []
    for line in lines:
        if line.startswith(old_id):
            uid, date, rname, discord_str, note, expiry, uses = parse_entry(line)
            new_lines.append(f"{new_id or old_id} | {date} | {new_name or old_name} | {discord_str or 'none'} | {note or 'none'} | {expiry or 'never'} | {uses or '0'}")
        else:
            new_lines.append(line)
    update_github_file(GITHUB_FILE, "\n".join(new_lines), sha)
    embed = discord.Embed(title="🔄 Updated", description=f"**{old_name}** → **{new_name or old_name}**", color=COLORS["blue"])
    embed.timestamp = datetime.utcnow()
    await interaction.followup.send(embed=embed)
    await send_log(embed)

# =============================================
#   /help
# =============================================
@tree.command(name="help", description="Show all commands")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title="📖 Whitelist Bot Commands", color=COLORS["purple"])
    embed.add_field(name="👑 OWNER COMMANDS", value="\u200b", inline=False)
    embed.add_field(name="/add", value="➕ Add user to whitelist", inline=True)
    embed.add_field(name="/remove", value="➖ Remove user", inline=True)
    embed.add_field(name="/ban", value="🔨 Ban user", inline=True)
    embed.add_field(name="/unban", value="✅ Unban user", inline=True)
    embed.add_field(name="/check", value="🔍 Check user status", inline=True)
    embed.add_field(name="/list", value="📋 List all users", inline=True)
    embed.add_field(name="/note", value="📝 Add note to user", inline=True)
    embed.add_field(name="/rename", value="🔄 Update username", inline=True)
    embed.add_field(name="/genkey", value="🔑 Generate key", inline=True)
    embed.add_field(name="/keylist", value="🔑 List all keys", inline=True)
    embed.add_field(name="/revokekey", value="🗑️ Delete a key", inline=True)
    embed.add_field(name="/setscript", value="📜 Set the script", inline=True)
    embed.add_field(name="/setrole", value="👑 Set whitelist role", inline=True)
    embed.add_field(name="/setlog", value="📋 Set log channel", inline=True)
    embed.add_field(name="/backup", value="💾 Backup whitelist", inline=True)
    embed.add_field(name="/panel", value="🎛️ Send control panel", inline=True)
    embed.add_field(name="\u200b", value="\u200b", inline=False)
    embed.add_field(name="👤 USER COMMANDS", value="\u200b", inline=False)
    embed.add_field(name="🔑 Redeem Key", value="Enter key in panel", inline=True)
    embed.add_field(name="📜 Get Script", value="Get script via DM", inline=True)
    embed.add_field(name="👤 Get Role", value="Get your role", inline=True)
    embed.add_field(name="📊 Get Stats", value="View your stats", inline=True)
    embed.set_footer(text="Whitelist Bot • VoidHub")
    embed.timestamp = datetime.utcnow()
    await interaction.response.send_message(embed=embed)

print("Starting bot...")
client.run(TOKEN)
