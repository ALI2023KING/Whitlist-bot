import discord
from discord import app_commands
import os
import requests
import base64
import json
import random
import string
from datetime import datetime, timedelta
import asyncio

TOKEN = os.environ.get("TOKEN")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
OWNER_ID = 1449777458218926243

GITHUB_REPO = "ALI2023KING/Whitlist-sys"
GITHUB_FILE = "whitelist.txt"
BAN_FILE = "banlist.txt"
KEY_FILE = "keys.txt"
SCRIPT_FILE = "script.txt"
HWID_RESET_FILE = "hwid_resets.txt"
SETTINGS_FILE = "settings.json"
RESELLERS_FILE = "resellers.txt"
FAILED_ATTEMPTS_FILE = "failed_attempts.txt"

cooldowns = {}
COOLDOWN_SECONDS = 3
START_TIME = datetime.utcnow()

BRAND_COLOR = 0xFFD700
BRAND_NAME = "ꜱᴇᴍɪ-ɪɴꜱᴛᴀɴᴛ"
BRAND_THUMBNAIL = "https://i.imgur.com/placeholder.png"

if not TOKEN:
    print("ERROR: No token found!")
    exit(1)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

COLORS = {
    "success": 0x57F287,
    "error": 0xED4245,
    "warning": 0xFEE75C,
    "info": 0x5865F2,
    "ban": 0xFF4500,
    "purple": 0x9B59B6,
    "blue": 0x00BFFF,
    "gold": BRAND_COLOR,
    "dark": 0x2B2D31
}

# =============================================
#   SETTINGS
# =============================================
def load_settings():
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{SETTINGS_FILE}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 404:
        return {}
    data = r.json()
    content = base64.b64decode(data["content"]).decode("utf-8")
    try:
        return json.loads(content)
    except:
        return {}

def save_settings(settings):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{SETTINGS_FILE}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    sha = r.json().get("sha") if r.status_code == 200 else None
    encoded = base64.b64encode(json.dumps(settings).encode("utf-8")).decode("utf-8")
    payload = {"message": "Updated settings", "content": encoded}
    if sha:
        payload["sha"] = sha
    requests.put(url, headers=headers, data=json.dumps(payload))

SETTINGS = load_settings()

def get_setting(key):
    return SETTINGS.get(key)

def set_setting(key, value):
    SETTINGS[key] = value
    save_settings(SETTINGS)

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

def get_roblox_avatar(user_id):
    try:
        url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=420x420&format=Png&isCircular=false"
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

def parse_entry(line):
    parts = line.split("|")
    user_id = parts[0].strip() if len(parts) > 0 else ""
    date = parts[1].strip() if len(parts) > 1 else "Unknown"
    roblox_name = parts[2].strip() if len(parts) > 2 else None
    discord_user = parts[3].strip() if len(parts) > 3 else None
    note = parts[4].strip() if len(parts) > 4 else None
    expiry = parts[5].strip() if len(parts) > 5 else None
    uses = parts[6].strip() if len(parts) > 6 else "0"
    hwid = parts[7].strip() if len(parts) > 7 else None
    script_key = parts[8].strip() if len(parts) > 8 else None
    return user_id, date, roblox_name, discord_user, note, expiry, uses, hwid, script_key

def parse_key(line):
    parts = line.split("|")
    key = parts[0].strip() if len(parts) > 0 else ""
    date = parts[1].strip() if len(parts) > 1 else ""
    used = parts[2].strip() if len(parts) > 2 else "false"
    max_uses = parts[3].strip() if len(parts) > 3 else "1"
    expiry = parts[4].strip() if len(parts) > 4 else "never"
    days = parts[5].strip() if len(parts) > 5 else "never"
    key_type = parts[6].strip() if len(parts) > 6 else "normal"
    return key, date, used, max_uses, expiry, days, key_type

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

def get_expiry_display(expiry_str):
    if not expiry_str or expiry_str == "never":
        return "Permanent"
    try:
        expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d %H:%M")
        now = datetime.utcnow()
        if now > expiry_date:
            return "⚠️ Expired"
        diff = expiry_date - now
        days = diff.days
        hours = diff.seconds // 3600
        if days > 0:
            return f"{days}d {hours}h left"
        else:
            return f"{hours}h left"
    except:
        return expiry_str

def generate_key(prefix="SEMI"):
    parts = [prefix] + ["".join(random.choices(string.ascii_uppercase + string.digits, k=4)) for _ in range(3)]
    return "-".join(parts)

def get_hwid_reset_time(discord_id):
    lines, _, _ = get_github_file(HWID_RESET_FILE)
    for line in lines:
        parts = line.split("|")
        if len(parts) >= 2 and parts[0].strip() == str(discord_id):
            try:
                last_reset = datetime.strptime(parts[1].strip(), "%Y-%m-%d %H:%M")
                next_reset = last_reset + timedelta(hours=1)
                if datetime.utcnow() < next_reset:
                    return next_reset
            except:
                pass
    return None

def set_hwid_reset_time(discord_id):
    lines, sha, content = get_github_file(HWID_RESET_FILE)
    new_lines = [l for l in lines if not l.startswith(str(discord_id))]
    date = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    new_lines.append(f"{discord_id} | {date}")
    update_github_file(HWID_RESET_FILE, "\n".join(new_lines), sha)

def is_reseller(user_id):
    lines, _, _ = get_github_file(RESELLERS_FILE)
    return str(user_id) in [l.split("|")[0].strip() for l in lines]

def get_reseller_keys_left(user_id):
    lines, _, _ = get_github_file(RESELLERS_FILE)
    for line in lines:
        parts = line.split("|")
        if parts[0].strip() == str(user_id):
            return int(parts[1].strip()) if len(parts) > 1 else 0
    return 0

def set_reseller_keys(user_id, count):
    lines, sha, _ = get_github_file(RESELLERS_FILE)
    new_lines = [l for l in lines if l.split("|")[0].strip() != str(user_id)]
    new_lines.append(f"{user_id} | {count}")
    update_github_file(RESELLERS_FILE, "\n".join(new_lines), sha)

def track_failed_attempt(discord_id):
    lines, sha, _ = get_github_file(FAILED_ATTEMPTS_FILE)
    found = False
    new_lines = []
    for line in lines:
        parts = line.split("|")
        if parts[0].strip() == str(discord_id):
            count = int(parts[1].strip()) + 1
            last_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
            new_lines.append(f"{discord_id} | {count} | {last_time}")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"{discord_id} | 1 | {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}")
    update_github_file(FAILED_ATTEMPTS_FILE, "\n".join(new_lines), sha)
    for line in new_lines:
        parts = line.split("|")
        if parts[0].strip() == str(discord_id):
            return int(parts[1].strip())
    return 1

def reset_failed_attempts(discord_id):
    lines, sha, _ = get_github_file(FAILED_ATTEMPTS_FILE)
    new_lines = [l for l in lines if l.split("|")[0].strip() != str(discord_id)]
    update_github_file(FAILED_ATTEMPTS_FILE, "\n".join(new_lines), sha)

async def send_log(embed):
    log_id = get_setting("log_channel")
    if log_id:
        channel = client.get_channel(int(log_id))
        if channel:
            await channel.send(embed=embed)

async def post_purchase(guild, roblox_name, discord_user, expiry, avatar=None):
    purchase_channel_id = get_setting("purchase_channel")
    if purchase_channel_id:
        channel = guild.get_channel(int(purchase_channel_id))
        if channel:
            embed = discord.Embed(
                title="🎉 New Purchase!",
                description=f"**{discord_user.mention}** just got access to **{BRAND_NAME}**!",
                color=COLORS["success"]
            )
            embed.add_field(name="Roblox", value=roblox_name, inline=True)
            embed.add_field(name="Expires", value=get_expiry_display(expiry), inline=True)
            if avatar:
                embed.set_thumbnail(url=avatar)
            embed.set_footer(text=f"{BRAND_NAME} • Thank you for your purchase!")
            embed.timestamp = datetime.utcnow()
            await channel.send(embed=embed)

async def give_whitelist_role(guild, discord_user_id):
    role_id = get_setting("whitelist_role")
    if role_id and guild:
        try:
            member = guild.get_member(int(discord_user_id))
            if member:
                role = guild.get_role(int(role_id))
                if role:
                    await member.add_roles(role)
                    return True
        except Exception as e:
            print(f"Role error: {e}")
    return False

async def remove_whitelist_role(guild, discord_user_id):
    role_id = get_setting("whitelist_role")
    if role_id and guild:
        try:
            member = guild.get_member(int(discord_user_id))
            if member:
                role = guild.get_role(int(role_id))
                if role and role in member.roles:
                    await member.remove_roles(role)
        except:
            pass

def owner_only(interaction):
    return interaction.user.id == OWNER_ID

def owner_or_reseller(interaction):
    return interaction.user.id == OWNER_ID or is_reseller(interaction.user.id)

def make_embed(title, description=None, color_key="gold"):
    embed = discord.Embed(title=title, color=COLORS.get(color_key, BRAND_COLOR))
    if description:
        embed.description = description
    embed.set_footer(text=f"{BRAND_NAME} Whitelist System")
    embed.timestamp = datetime.utcnow()
    return embed

async def username_autocomplete(interaction: discord.Interaction, current: str):
    lines, _, _ = get_github_file(GITHUB_FILE)
    choices = []
    for line in lines:
        uid, date, roblox_name, discord_user, note, expiry, uses, hwid, script_key = parse_entry(line)
        if roblox_name and current.lower() in roblox_name.lower():
            choices.append(app_commands.Choice(name=roblox_name, value=roblox_name))
        if len(choices) >= 25:
            break
    return choices

# =============================================
#   BACKGROUND TASKS
# =============================================
async def check_expiries():
    await client.wait_until_ready()
    while not client.is_closed():
        try:
            lines, sha, content = get_github_file(GITHUB_FILE)
            now = datetime.utcnow()
            for line in lines:
                if line.startswith("--"):
                    continue
                uid, date, roblox_name, discord_str, note, expiry, uses, hwid, script_key = parse_entry(line)
                if expiry and expiry != "never":
                    try:
                        expiry_dt = datetime.strptime(expiry, "%Y-%m-%d %H:%M")
                        diff = expiry_dt - now
                        if 0 < diff.total_seconds() < 259200:
                            if discord_str and discord_str != "none":
                                for guild in client.guilds:
                                    member = guild.get_member(int(discord_str))
                                    if member:
                                        try:
                                            days_left = diff.days
                                            hours_left = diff.seconds // 3600
                                            dm = make_embed(
                                                "⏰ Access Expiring Soon!",
                                                f"Hey **{roblox_name}**!\n\nYour access to **{BRAND_NAME}** expires in **{days_left}d {hours_left}h**.\n\nContact the owner to renew your access!",
                                                "warning"
                                            )
                                            await member.send(embed=dm)
                                        except:
                                            pass
                    except:
                        pass
        except:
            pass
        await asyncio.sleep(3600)

async def rotate_status():
    await client.wait_until_ready()
    statuses = [
        f"👑 {BRAND_NAME}",
        "🔑 Keys Available",
        "🛡️ Protecting Scripts",
    ]
    i = 0
    while not client.is_closed():
        try:
            lines, _, _ = get_github_file(GITHUB_FILE)
            count = len([l for l in lines if not l.startswith("--")])
            statuses[0] = f"👑 {count} users whitelisted"
        except:
            pass
        await client.change_presence(activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=statuses[i % len(statuses)]
        ))
        i += 1
        await asyncio.sleep(30)

# =============================================
#   MODALS
# =============================================
class AddUserModal(discord.ui.Modal, title="➕ Add User"):
    username = discord.ui.TextInput(label="Roblox Username", placeholder="Enter Roblox username", required=True)
    days_input = discord.ui.TextInput(label="Days (leave empty for permanent)", placeholder="e.g. 30", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user_id, roblox_name = get_roblox_user_by_username(self.username.value.strip())
        if not user_id:
            await interaction.followup.send(embed=make_embed("❌ User Not Found", color_key="error"), ephemeral=True)
            return
        lines, sha, content = get_github_file(GITHUB_FILE)
        if user_id in get_ids_only(lines):
            await interaction.followup.send(embed=make_embed("⚠️ Already Whitelisted", color_key="warning"), ephemeral=True)
            return
        date = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        expiry = "never"
        if self.days_input.value.strip():
            try:
                expiry = (datetime.utcnow() + timedelta(days=int(self.days_input.value.strip()))).strftime("%Y-%m-%d %H:%M")
            except:
                pass
        new_entry = f"{user_id} | {date} | {roblox_name} | none | none | {expiry} | 0 | none | none"
        update_github_file(GITHUB_FILE, content.strip() + f"\n{new_entry}", sha)
        embed = make_embed("✅ User Added", color_key="success")
        embed.add_field(name="Roblox", value=roblox_name, inline=True)
        embed.add_field(name="Expires", value=get_expiry_display(expiry), inline=True)
        await interaction.followup.send(embed=embed, ephemeral=True)
        await send_log(embed)

class RemoveUserModal(discord.ui.Modal, title="➖ Remove User"):
    username = discord.ui.TextInput(label="Roblox Username", placeholder="Enter Roblox username", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user_id, roblox_name = get_roblox_user_by_username(self.username.value.strip())
        if not user_id:
            await interaction.followup.send(embed=make_embed("❌ User Not Found", color_key="error"), ephemeral=True)
            return
        lines, sha, _ = get_github_file(GITHUB_FILE)
        found_line = next((l for l in lines if l.startswith(user_id)), None)
        if not found_line:
            await interaction.followup.send(embed=make_embed("❌ Not Whitelisted", color_key="error"), ephemeral=True)
            return
        _, _, _, discord_str, _, _, _, _, _ = parse_entry(found_line)
        new_lines = [l for l in lines if not l.startswith(user_id)]
        update_github_file(GITHUB_FILE, "\n".join(new_lines), sha)
        if discord_str and discord_str != "none":
            await remove_whitelist_role(interaction.guild, discord_str)
            try:
                member = interaction.guild.get_member(int(discord_str))
                if member:
                    await member.send(embed=make_embed("❌ Whitelist Removed", "Your access has been removed.", "error"))
            except:
                pass
        embed = make_embed("🗑️ User Removed", f"**{roblox_name}** removed.", "ban")
        await interaction.followup.send(embed=embed, ephemeral=True)
        await send_log(embed)

class BanUserModal(discord.ui.Modal, title="🔨 Ban User"):
    username = discord.ui.TextInput(label="Roblox Username", placeholder="Enter Roblox username", required=True)
    reason = discord.ui.TextInput(label="Reason", placeholder="Why are you banning?", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user_id, roblox_name = get_roblox_user_by_username(self.username.value.strip())
        if not user_id:
            await interaction.followup.send(embed=make_embed("❌ User Not Found", color_key="error"), ephemeral=True)
            return
        ban_lines, ban_sha, ban_content = get_github_file(BAN_FILE)
        if user_id in get_ids_only(ban_lines):
            await interaction.followup.send(embed=make_embed("⚠️ Already Banned", color_key="warning"), ephemeral=True)
            return
        lines, sha, _ = get_github_file(GITHUB_FILE)
        found_line = next((l for l in lines if l.startswith(user_id)), None)
        discord_str = None
        if found_line:
            _, _, _, discord_str, _, _, _, _, _ = parse_entry(found_line)
            new_lines = [l for l in lines if not l.startswith(user_id)]
            update_github_file(GITHUB_FILE, "\n".join(new_lines), sha)
        reason = self.reason.value.strip() if self.reason.value.strip() else "No reason given"
        date = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        update_github_file(BAN_FILE, ban_content.strip() + f"\n{user_id} | {date} | {roblox_name} | {reason}", ban_sha)
        if discord_str and discord_str != "none":
            await remove_whitelist_role(interaction.guild, discord_str)
            try:
                member = interaction.guild.get_member(int(discord_str))
                if member:
                    await member.send(embed=make_embed("🔨 You have been Banned", f"**Reason:** {reason}", "error"))
            except:
                pass
        embed = make_embed("🔨 User Banned", f"**{roblox_name}** banned.\n**Reason:** {reason}", "error")
        await interaction.followup.send(embed=embed, ephemeral=True)
        await send_log(embed)

class UnbanUserModal(discord.ui.Modal, title="✅ Unban User"):
    username = discord.ui.TextInput(label="Roblox Username", placeholder="Enter Roblox username", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user_id, roblox_name = get_roblox_user_by_username(self.username.value.strip())
        if not user_id:
            await interaction.followup.send(embed=make_embed("❌ User Not Found", color_key="error"), ephemeral=True)
            return
        ban_lines, ban_sha, _ = get_github_file(BAN_FILE)
        if user_id not in get_ids_only(ban_lines):
            await interaction.followup.send(embed=make_embed("❌ Not Banned", color_key="error"), ephemeral=True)
            return
        new_lines = [l for l in ban_lines if not l.startswith(user_id)]
        update_github_file(BAN_FILE, "\n".join(new_lines), ban_sha)
        embed = make_embed("✅ User Unbanned", f"**{roblox_name}** unbanned.", "success")
        await interaction.followup.send(embed=embed, ephemeral=True)
        await send_log(embed)

class AnnounceModal(discord.ui.Modal, title="📢 Announce to All Users"):
    title_input = discord.ui.TextInput(label="Title", placeholder="e.g. Script Updated!", required=True)
    message_input = discord.ui.TextInput(label="Message", placeholder="Your announcement...", style=discord.TextStyle.paragraph, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        lines, _, _ = get_github_file(GITHUB_FILE)
        sent = 0
        failed = 0
        for line in lines:
            uid, date, roblox_name, discord_str, note, expiry, uses, hwid, script_key = parse_entry(line)
            if discord_str and discord_str != "none":
                try:
                    member = interaction.guild.get_member(int(discord_str))
                    if member:
                        dm = discord.Embed(title=f"📢 {self.title_input.value}", description=self.message_input.value, color=BRAND_COLOR)
                        dm.set_footer(text=f"{BRAND_NAME} Announcement")
                        dm.timestamp = datetime.utcnow()
                        await member.send(embed=dm)
                        sent += 1
                except:
                    failed += 1
        embed = make_embed("📢 Announcement Sent", f"✅ Sent to **{sent}** users\n❌ Failed: **{failed}**", "success")
        await interaction.followup.send(embed=embed, ephemeral=True)

class ResellerModal(discord.ui.Modal, title="👥 Add Reseller"):
    discord_id = discord.ui.TextInput(label="Discord ID", placeholder="Their Discord user ID", required=True)
    keys_count = discord.ui.TextInput(label="Number of keys to give", placeholder="e.g. 5", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            uid = int(self.discord_id.value.strip())
            count = int(self.keys_count.value.strip())
        except:
            await interaction.followup.send(embed=make_embed("❌ Invalid Input", color_key="error"), ephemeral=True)
            return
        current = get_reseller_keys_left(uid)
        set_reseller_keys(uid, current + count)
        embed = make_embed("✅ Reseller Updated", f"<@{uid}> now has **{current + count}** keys.", "success")
        await interaction.followup.send(embed=embed, ephemeral=True)
        try:
            member = interaction.guild.get_member(uid)
            if member:
                dm = make_embed("🔑 You are now a Reseller!", f"You have **{count}** keys to generate.\nUse `/adminpanel` to generate keys.", "gold")
                await member.send(embed=dm)
        except:
            pass

class ExtendExpiryModal(discord.ui.Modal, title="📅 Extend Expiry"):
    username = discord.ui.TextInput(label="Roblox Username", placeholder="Enter Roblox username", required=True)
    days_input = discord.ui.TextInput(label="Days to add", placeholder="e.g. 30", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user_id, roblox_name = get_roblox_user_by_username(self.username.value.strip())
        if not user_id:
            await interaction.followup.send(embed=make_embed("❌ User Not Found", color_key="error"), ephemeral=True)
            return
        lines, sha, content = get_github_file(GITHUB_FILE)
        found_line = next((l for l in lines if l.startswith(user_id)), None)
        if not found_line:
            await interaction.followup.send(embed=make_embed("❌ Not Whitelisted", color_key="error"), ephemeral=True)
            return
        try:
            days = int(self.days_input.value.strip())
        except:
            await interaction.followup.send(embed=make_embed("❌ Invalid days", color_key="error"), ephemeral=True)
            return
        uid, date, rname, discord_str, note, expiry, uses, hwid, script_key = parse_entry(found_line)
        if expiry and expiry != "never":
            try:
                base = datetime.strptime(expiry, "%Y-%m-%d %H:%M")
                if base < datetime.utcnow():
                    base = datetime.utcnow()
            except:
                base = datetime.utcnow()
        else:
            base = datetime.utcnow()
        new_expiry = (base + timedelta(days=days)).strftime("%Y-%m-%d %H:%M")
        new_lines = []
        for line in lines:
            if line.startswith(user_id):
                new_lines.append(f"{uid} | {date} | {rname} | {discord_str or 'none'} | {note or 'none'} | {new_expiry} | {uses} | {hwid or 'none'} | {script_key or 'none'}")
            else:
                new_lines.append(line)
        update_github_file(GITHUB_FILE, "\n".join(new_lines), sha)
        embed = make_embed("📅 Expiry Extended", f"**{rname}** — +{days} days\n**New expiry:** {new_expiry}", "success")
        await interaction.followup.send(embed=embed, ephemeral=True)
        await send_log(embed)

class TransferModal(discord.ui.Modal, title="🔄 Transfer Whitelist"):
    old_username = discord.ui.TextInput(label="Current Roblox Username", placeholder="Old username", required=True)
    new_username = discord.ui.TextInput(label="New Roblox Username", placeholder="New username", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        old_id, old_name = get_roblox_user_by_username(self.old_username.value.strip())
        new_id, new_name = get_roblox_user_by_username(self.new_username.value.strip())
        if not old_id or not new_id:
            await interaction.followup.send(embed=make_embed("❌ User Not Found", color_key="error"), ephemeral=True)
            return
        lines, sha, content = get_github_file(GITHUB_FILE)
        found_line = next((l for l in lines if l.startswith(old_id)), None)
        if not found_line:
            await interaction.followup.send(embed=make_embed("❌ Not Whitelisted", color_key="error"), ephemeral=True)
            return
        uid, date, rname, discord_str, note, expiry, uses, hwid, script_key = parse_entry(found_line)
        new_lines = []
        for line in lines:
            if line.startswith(old_id):
                new_lines.append(f"{new_id} | {date} | {new_name} | {discord_str or 'none'} | {note or 'none'} | {expiry or 'never'} | {uses} | none | none")
            else:
                new_lines.append(line)
        update_github_file(GITHUB_FILE, "\n".join(new_lines), sha)
        embed = make_embed("🔄 Transfer Complete", f"**{old_name}** → **{new_name}**\nHWID reset for new account.", "success")
        await interaction.followup.send(embed=embed, ephemeral=True)
        await send_log(embed)

class PriceListModal(discord.ui.Modal, title="💰 Update Price List"):
    prices = discord.ui.TextInput(
        label="Prices (one per line)",
        placeholder="7 Days — 50 Robux\n30 Days — 150 Robux\nLifetime — 300 Robux",
        style=discord.TextStyle.paragraph,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        set_setting("price_list", self.prices.value)
        await interaction.response.send_message(embed=make_embed("✅ Price List Updated", color_key="success"), ephemeral=True)

class SetChannelModal(discord.ui.Modal, title="📌 Set Channel"):
    channel_id = discord.ui.TextInput(label="Channel ID", placeholder="Right click channel → Copy ID", required=True)
    channel_type = discord.ui.TextInput(label="Type (purchase/vouch/stock)", placeholder="purchase, vouch, or stock", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            cid = int(self.channel_id.value.strip())
            ctype = self.channel_type.value.strip().lower()
            if ctype not in ["purchase", "vouch", "stock"]:
                await interaction.response.send_message(embed=make_embed("❌ Invalid type. Use: purchase, vouch, or stock", color_key="error"), ephemeral=True)
                return
            set_setting(f"{ctype}_channel", cid)
            await interaction.response.send_message(embed=make_embed(f"✅ {ctype.capitalize()} Channel Set", color_key="success"), ephemeral=True)
        except:
            await interaction.response.send_message(embed=make_embed("❌ Invalid Channel ID", color_key="error"), ephemeral=True)

# =============================================
#   VIEWS
# =============================================
class UserDetailView(discord.ui.View):
    def __init__(self, uid, roblox_name, discord_str, expiry, hwid, date, uses):
        super().__init__(timeout=60)
        self.uid = uid
        self.roblox_name = roblox_name
        self.discord_str = discord_str
        self.expiry = expiry
        self.hwid = hwid
        self.date = date
        self.uses = uses

    @discord.ui.button(label="📊 Details", style=discord.ButtonStyle.blurple)
    async def show_details(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not owner_only(interaction):
            await interaction.response.send_message("🚫 Access Denied", ephemeral=True)
            return
        avatar = get_roblox_avatar(self.uid)
        embed = make_embed(f"📊 {self.roblox_name}", color_key="info")
        embed.add_field(name="Roblox ID", value=self.uid, inline=True)
        embed.add_field(name="Discord", value=f"<@{self.discord_str}>" if self.discord_str and self.discord_str != "none" else "None", inline=True)
        embed.add_field(name="Added", value=self.date, inline=True)
        embed.add_field(name="Expires", value=get_expiry_display(self.expiry), inline=True)
        embed.add_field(name="HWID", value="🔒 Locked" if self.hwid and self.hwid != "none" else "🔓 Unlocked", inline=True)
        embed.add_field(name="Script Runs", value=self.uses, inline=True)
        if avatar:
            embed.set_image(url=avatar)
        await interaction.response.send_message(embed=embed, ephemeral=True)

class ScriptView(discord.ui.View):
    def __init__(self, script_text):
        super().__init__(timeout=60)
        self.script_text = script_text

    @discord.ui.button(label="📋 Copy Script", style=discord.ButtonStyle.grey)
    async def copy_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"```lua\n{self.script_text}\n```", ephemeral=True)

class HWIDResetView(discord.ui.View):
    def __init__(self, entries):
        super().__init__(timeout=60)
        for i, (uid, roblox_name, discord_str) in enumerate(entries[:10]):
            button = discord.ui.Button(label=f"🔄 {roblox_name[:20]}", style=discord.ButtonStyle.red, row=i // 3)
            button.callback = self.make_callback(uid, roblox_name, discord_str)
            self.add_item(button)

    def make_callback(self, uid, roblox_name, discord_str):
        async def callback(interaction: discord.Interaction):
            if not owner_only(interaction):
                await interaction.response.send_message("🚫 Access Denied", ephemeral=True)
                return
            lines, sha, _ = get_github_file(GITHUB_FILE)
            new_lines = []
            for line in lines:
                if line.startswith(uid):
                    e = parse_entry(line)
                    new_lines.append(f"{e[0]} | {e[1]} | {e[2]} | {e[3]} | {e[4] or 'none'} | {e[5] or 'never'} | {e[6]} | none | {e[8] or 'none'}")
                else:
                    new_lines.append(line)
            update_github_file(GITHUB_FILE, "\n".join(new_lines), sha)
            if discord_str and discord_str != "none":
                reset_lines, reset_sha, _ = get_github_file(HWID_RESET_FILE)
                new_reset = [l for l in reset_lines if not l.startswith(str(discord_str))]
                update_github_file(HWID_RESET_FILE, "\n".join(new_reset), reset_sha)
            embed = make_embed("🔄 HWID Reset", f"**{roblox_name}**'s HWID reset.", "success")
            await interaction.response.edit_message(embed=embed, view=None)
        return callback

class GenerateKeyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)

    @discord.ui.button(label="⏰ 4 Hours", style=discord.ButtonStyle.blurple, row=0)
    async def key_4h(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._generate(interaction, hours=4, label="4 Hours")

    @discord.ui.button(label="🌙 1 Day", style=discord.ButtonStyle.blurple, row=0)
    async def key_1d(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._generate(interaction, hours=24, label="1 Day")

    @discord.ui.button(label="📅 7 Days", style=discord.ButtonStyle.blurple, row=0)
    async def key_7d(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._generate(interaction, hours=168, label="7 Days")

    @discord.ui.button(label="♾️ Permanent", style=discord.ButtonStyle.green, row=0)
    async def key_perm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._generate(interaction, hours=None, label="Permanent")

    @discord.ui.button(label="🧪 Trial (1hr)", style=discord.ButtonStyle.grey, row=1)
    async def key_trial(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._generate(interaction, hours=1, label="Trial 1 Hour", key_type="trial")

    @discord.ui.button(label="⏱️ Custom Time", style=discord.ButtonStyle.grey, row=1)
    async def key_custom(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CustomKeyModal())
        self.stop()

    async def _generate(self, interaction: discord.Interaction, hours, label, key_type="normal"):
        is_owner = owner_only(interaction)
        is_res = is_reseller(interaction.user.id)
        if not is_owner and not is_res:
            await interaction.response.send_message("🚫 Access Denied", ephemeral=True)
            return
        if is_res and not is_owner:
            keys_left = get_reseller_keys_left(interaction.user.id)
            if keys_left <= 0:
                await interaction.response.edit_message(embed=make_embed("❌ No Keys Left", "Contact the owner.", "error"), view=None)
                return
            set_reseller_keys(interaction.user.id, keys_left - 1)
        prefix = "TRIAL" if key_type == "trial" else "SEMI"
        key = generate_key(prefix)
        date = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        expiry = "never"
        if hours:
            expiry_dt = datetime.utcnow() + timedelta(hours=hours)
            expiry = expiry_dt.strftime("%Y-%m-%d %H:%M")
        key_lines, key_sha, key_content = get_github_file(KEY_FILE)
        new_entry = f"{key} | {date} | false | 1 | {expiry} | never | {key_type}"
        update_github_file(KEY_FILE, key_content.strip() + f"\n{new_entry}", key_sha)
        try:
            dm = make_embed("🔑 New Key Generated", color_key="gold")
            dm.add_field(name="🔑 Key", value=f"`{key}`", inline=False)
            dm.add_field(name="Type", value="🧪 Trial" if key_type == "trial" else "✅ Full", inline=True)
            dm.add_field(name="Duration", value=label, inline=True)
            dm.add_field(name="Expires", value=expiry if expiry != "never" else "Never", inline=True)
            dm.set_footer(text="⚠️ Single use only!")
            await interaction.user.send(embed=dm)
            await interaction.response.edit_message(embed=make_embed("✅ Key Sent to DMs", f"**{label}** key sent! Single use only.", "success"), view=None)
        except:
            await interaction.response.edit_message(embed=make_embed("❌ DM Failed", "Enable DMs and try again.", "error"), view=None)
        self.stop()

class CustomKeyModal(discord.ui.Modal, title="⏱️ Custom Key Duration"):
    hours_input = discord.ui.TextInput(label="Hours", placeholder="e.g. 48 for 2 days", required=False)
    days_input = discord.ui.TextInput(label="Days", placeholder="e.g. 30 for 30 days", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        if not owner_or_reseller(interaction):
            await interaction.response.send_message("🚫 Access Denied", ephemeral=True)
            return
        total_hours = 0
        try:
            if self.hours_input.value.strip():
                total_hours += int(self.hours_input.value.strip())
            if self.days_input.value.strip():
                total_hours += int(self.days_input.value.strip()) * 24
        except:
            await interaction.response.send_message(embed=make_embed("❌ Invalid input", color_key="error"), ephemeral=True)
            return
        if total_hours <= 0:
            await interaction.response.send_message(embed=make_embed("❌ Enter at least hours or days", color_key="error"), ephemeral=True)
            return
        key = generate_key("SEMI")
        date = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        expiry_dt = datetime.utcnow() + timedelta(hours=total_hours)
        expiry = expiry_dt.strftime("%Y-%m-%d %H:%M")
        key_lines, key_sha, key_content = get_github_file(KEY_FILE)
        new_entry = f"{key} | {date} | false | 1 | {expiry} | never | normal"
        update_github_file(KEY_FILE, key_content.strip() + f"\n{new_entry}", key_sha)
        label = f"{total_hours}h custom"
        try:
            dm = make_embed("🔑 Custom Key Generated", color_key="gold")
            dm.add_field(name="🔑 Key", value=f"`{key}`", inline=False)
            dm.add_field(name="Duration", value=label, inline=True)
            dm.add_field(name="Expires", value=expiry, inline=True)
            await interaction.user.send(embed=dm)
            await interaction.response.send_message(embed=make_embed("✅ Key Sent to DMs", color_key="success"), ephemeral=True)
        except:
            await interaction.response.send_message(embed=make_embed("❌ DM Failed", color_key="error"), ephemeral=True)

class AdminPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)

    @discord.ui.button(label="➕ Add", style=discord.ButtonStyle.green, row=0)
    async def add_btn(self, i: discord.Interaction, b: discord.ui.Button):
        if not owner_only(i): return
        await i.response.send_modal(AddUserModal())

    @discord.ui.button(label="➖ Remove", style=discord.ButtonStyle.red, row=0)
    async def remove_btn(self, i: discord.Interaction, b: discord.ui.Button):
        if not owner_only(i): return
        await i.response.send_modal(RemoveUserModal())

    @discord.ui.button(label="🔨 Ban", style=discord.ButtonStyle.red, row=0)
    async def ban_btn(self, i: discord.Interaction, b: discord.ui.Button):
        if not owner_only(i): return
        await i.response.send_modal(BanUserModal())

    @discord.ui.button(label="✅ Unban", style=discord.ButtonStyle.green, row=0)
    async def unban_btn(self, i: discord.Interaction, b: discord.ui.Button):
        if not owner_only(i): return
        await i.response.send_modal(UnbanUserModal())

    @discord.ui.button(label="📅 Extend", style=discord.ButtonStyle.blurple, row=0)
    async def extend_btn(self, i: discord.Interaction, b: discord.ui.Button):
        if not owner_only(i): return
        await i.response.send_modal(ExtendExpiryModal())

    @discord.ui.button(label="🔑 Gen Key", style=discord.ButtonStyle.blurple, row=1)
    async def genkey_btn(self, i: discord.Interaction, b: discord.ui.Button):
        if not owner_or_reseller(i): return
        embed = make_embed("🔑 Generate Key", "Select key duration:", "gold")
        await i.response.send_message(embed=embed, view=GenerateKeyView(), ephemeral=True)

    @discord.ui.button(label="📋 List", style=discord.ButtonStyle.grey, row=1)
    async def list_btn(self, i: discord.Interaction, b: discord.ui.Button):
        if not owner_only(i): return
        await i.response.defer(ephemeral=True)
        lines, _, _ = get_github_file(GITHUB_FILE)
        ban_lines, _, _ = get_github_file(BAN_FILE)
        entries = [l for l in lines if not l.startswith("--")]
        ban_entries = [l for l in ban_lines if not l.startswith("--")]
        github_url = f"https://github.com/{GITHUB_REPO}/blob/main/{GITHUB_FILE}"
        embed = make_embed(f"📋 {BRAND_NAME} WHITELIST", color_key="info")
        embed.description = f"[📄 View on GitHub]({github_url})\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        if not entries:
            embed.description += "Empty.\n"
        else:
            for line in entries:
                uid, date, roblox_name, discord_str, note, expiry, uses, hwid, script_key = parse_entry(line)
                name = roblox_name if roblox_name else uid
                discord_mention = f"<@{discord_str}>" if discord_str and discord_str != "none" else "No Discord"
                expired = is_expired(expiry)
                status = "⚠️" if expired else "✅"
                expiry_text = get_expiry_display(expiry)
                embed.description += f"{status} **{name}** — {discord_mention}\n┗ ⏰ {expiry_text}\n"
        embed.description += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        embed.add_field(name="✅ Total", value=str(len(entries)), inline=True)
        embed.add_field(name="🔨 Banned", value=str(len(ban_entries)), inline=True)
        await i.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(label="📢 Announce", style=discord.ButtonStyle.grey, row=1)
    async def announce_btn(self, i: discord.Interaction, b: discord.ui.Button):
        if not owner_only(i): return
        await i.response.send_modal(AnnounceModal())

    @discord.ui.button(label="🔄 Transfer", style=discord.ButtonStyle.grey, row=1)
    async def transfer_btn(self, i: discord.Interaction, b: discord.ui.Button):
        if not owner_only(i): return
        await i.response.send_modal(TransferModal())

    @discord.ui.button(label="🔒 HWID", style=discord.ButtonStyle.grey, row=2)
    async def hwid_btn(self, i: discord.Interaction, b: discord.ui.Button):
        if not owner_only(i): return
        await i.response.defer(ephemeral=True)
        lines, _, _ = get_github_file(GITHUB_FILE)
        entries = []
        for line in lines:
            if not line.startswith("--"):
                uid, date, roblox_name, discord_str, note, expiry, uses, hwid, script_key = parse_entry(line)
                if hwid and hwid != "none":
                    entries.append((uid, roblox_name or uid, discord_str or "none"))
        if not entries:
            await i.followup.send(embed=make_embed("🔒 No HWID locked users", color_key="info"), ephemeral=True)
            return
        embed = make_embed("🔒 HWID Reset Panel", "Tap a user to reset their HWID.", "gold")
        await i.followup.send(embed=embed, view=HWIDResetView(entries), ephemeral=True)

    @discord.ui.button(label="🔑 Keys", style=discord.ButtonStyle.grey, row=2)
    async def keylist_btn(self, i: discord.Interaction, b: discord.ui.Button):
        if not owner_only(i): return
        await i.response.defer(ephemeral=True)
        key_lines, _, _ = get_github_file(KEY_FILE)
        if not key_lines:
            await i.followup.send(embed=make_embed("🔑 No Keys", color_key="info"), ephemeral=True)
            return
        desc = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        for line in key_lines:
            k, date, used, max_uses, expiry, days, key_type = parse_key(line)
            status = "✅" if used == "false" else "❌"
            if is_expired(expiry): status = "⚠️"
            trial = " 🧪" if key_type == "trial" else ""
            desc += f"{status} `{k}`{trial} — {get_expiry_display(expiry)}\n"
        desc += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        embed = make_embed("🔑 All Keys", desc, "gold")
        embed.add_field(name="Total", value=str(len(key_lines)), inline=True)
        await i.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(label="👥 Resellers", style=discord.ButtonStyle.grey, row=2)
    async def resellers_btn(self, i: discord.Interaction, b: discord.ui.Button):
        if not owner_only(i): return
        await i.response.send_modal(ResellerModal())

    @discord.ui.button(label="💰 Prices", style=discord.ButtonStyle.grey, row=2)
    async def prices_btn(self, i: discord.Interaction, b: discord.ui.Button):
        if not owner_only(i): return
        await i.response.send_modal(PriceListModal())

    @discord.ui.button(label="📌 Channels", style=discord.ButtonStyle.grey, row=2)
    async def channels_btn(self, i: discord.Interaction, b: discord.ui.Button):
        if not owner_only(i): return
        await i.response.send_modal(SetChannelModal())

class PanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔑 Redeem Key", style=discord.ButtonStyle.green, custom_id="panel_redeem", row=0)
    async def redeem_key(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RedeemKeyModal())

    @discord.ui.button(label="📜 Get Script", style=discord.ButtonStyle.blurple, custom_id="panel_script", row=0)
    async def get_script(self, interaction: discord.Interaction, button: discord.ui.Button):
        lines, _, _ = get_github_file(GITHUB_FILE)
        user_entry = None
        for line in lines:
            uid, date, roblox_name, discord_str, note, expiry, uses, hwid, script_key = parse_entry(line)
            if discord_str and discord_str == str(interaction.user.id):
                user_entry = (uid, date, roblox_name, discord_str, note, expiry, uses, hwid, script_key)
                break
        if not user_entry:
            await interaction.response.send_message(embed=make_embed("❌ Not Whitelisted", "Redeem a key first.", "error"), ephemeral=True)
            return
        uid, date, roblox_name, discord_str, note, expiry, uses, hwid, script_key = user_entry
        if is_expired(expiry):
            await interaction.response.send_message(embed=make_embed("⚠️ Access Expired", color_key="warning"), ephemeral=True)
            return
        _, _, script_content = get_github_file(SCRIPT_FILE)
        if not script_content:
            await interaction.response.send_message(embed=make_embed("❌ No Script Set", color_key="error"), ephemeral=True)
            return
        embed = discord.Embed(title="Here is your script:", color=COLORS["success"])
        embed.description = f"```lua\n{script_content[:1900]}\n```"
        embed.set_footer(text="Only you can see this • Dismiss message")
        embed.timestamp = datetime.utcnow()
        await interaction.response.send_message(embed=embed, view=ScriptView(script_content[:1900]), ephemeral=True)

    @discord.ui.button(label="👤 Get Role", style=discord.ButtonStyle.blurple, custom_id="panel_role", row=0)
    async def get_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        role_id = get_setting("whitelist_role")
        if not role_id:
            await interaction.response.send_message(embed=make_embed("❌ No Role Set", "Owner needs to run /setrole first.", "error"), ephemeral=True)
            return
        lines, _, _ = get_github_file(GITHUB_FILE)
        user_entry = None
        for line in lines:
            uid, date, roblox_name, discord_str, note, expiry, uses, hwid, script_key = parse_entry(line)
            if discord_str and discord_str == str(interaction.user.id):
                user_entry = (uid, date, roblox_name, discord_str, note, expiry, uses, hwid, script_key)
                break
        if not user_entry:
            await interaction.response.send_message(embed=make_embed("❌ Not Whitelisted", color_key="error"), ephemeral=True)
            return
        uid, date, roblox_name, discord_str, note, expiry, uses, hwid, script_key = user_entry
        if is_expired(expiry):
            await interaction.response.send_message(embed=make_embed("⚠️ Access Expired", color_key="warning"), ephemeral=True)
            return
        try:
            role = interaction.guild.get_role(int(role_id))
            if not role:
                await interaction.response.send_message(embed=make_embed("❌ Role Not Found", color_key="error"), ephemeral=True)
                return
            if role in interaction.user.roles:
                await interaction.response.send_message(embed=make_embed("✅ Already Have Role", f"You already have **{role.name}**!", "warning"), ephemeral=True)
                return
            await interaction.user.add_roles(role)
            await interaction.response.send_message(embed=make_embed("✅ Role Given", f"You now have **{role.name}**!", "success"), ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(embed=make_embed("❌ Failed to give role", str(e), "error"), ephemeral=True)

    @discord.ui.button(label="🔄 Reset HWID", style=discord.ButtonStyle.grey, custom_id="panel_hwid", row=1)
    async def reset_hwid(self, interaction: discord.Interaction, button: discord.ui.Button):
        next_reset = get_hwid_reset_time(interaction.user.id)
        if next_reset:
            time_left = next_reset - datetime.utcnow()
            minutes_left = int(time_left.total_seconds() // 60)
            await interaction.response.send_message(embed=make_embed("⏳ HWID Cooldown", f"Reset available in **{minutes_left} minutes**.", "warning"), ephemeral=True)
            return
        lines, sha, content = get_github_file(GITHUB_FILE)
        new_lines = []
        found = False
        for line in lines:
            uid, date, roblox_name, discord_str, note, expiry, uses, hwid, script_key = parse_entry(line)
            if discord_str and discord_str == str(interaction.user.id):
                found = True
                new_lines.append(f"{uid} | {date} | {roblox_name} | {discord_str} | {note or 'none'} | {expiry or 'never'} | {uses} | none | {script_key or 'none'}")
            else:
                new_lines.append(line)
        if not found:
            await interaction.response.send_message(embed=make_embed("❌ Not Whitelisted", color_key="error"), ephemeral=True)
            return
        update_github_file(GITHUB_FILE, "\n".join(new_lines), sha)
        set_hwid_reset_time(interaction.user.id)
        await interaction.response.send_message(embed=make_embed("🔄 HWID Reset", "Done! Next reset available in **1 hour**.", "success"), ephemeral=True)
        log_embed = make_embed("🔄 HWID Reset", f"{interaction.user.mention} reset HWID.", "warning")
        await send_log(log_embed)

    @discord.ui.button(label="📊 Get Stats", style=discord.ButtonStyle.grey, custom_id="panel_stats", row=1)
    async def get_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        lines, _, _ = get_github_file(GITHUB_FILE)
        for line in lines:
            uid, date, roblox_name, discord_str, note, expiry, uses, hwid, script_key = parse_entry(line)
            if discord_str and discord_str == str(interaction.user.id):
                expired = is_expired(expiry)
                next_hwid = get_hwid_reset_time(interaction.user.id)
                embed = make_embed("📊 Your Stats", color_key="warning" if expired else "success")
                embed.add_field(name="Roblox", value=roblox_name or uid, inline=True)
                embed.add_field(name="Status", value="⚠️ Expired" if expired else "✅ Active", inline=True)
                embed.add_field(name="Added", value=date, inline=True)
                embed.add_field(name="Expires", value=get_expiry_display(expiry), inline=True)
                embed.add_field(name="HWID", value="🔒 Locked" if hwid and hwid != "none" else "🔓 Unlocked", inline=True)
                if next_hwid:
                    time_left = next_hwid - datetime.utcnow()
                    minutes_left = int(time_left.total_seconds() // 60)
                    embed.add_field(name="Next HWID Reset", value=f"In {minutes_left}min", inline=True)
                else:
                    embed.add_field(name="Next HWID Reset", value="Available ✅", inline=True)
                avatar = get_roblox_avatar(uid)
                if avatar:
                    embed.set_image(url=avatar)
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
        await interaction.response.send_message(embed=make_embed("❌ Not Whitelisted", color_key="error"), ephemeral=True)

class RedeemKeyModal(discord.ui.Modal, title="🔑 Redeem Key"):
    key_input = discord.ui.TextInput(label="Enter your key", placeholder="SEMI-XXXX-XXXX-XXXX", required=True)
    roblox_input = discord.ui.TextInput(label="Your Roblox username", placeholder="Your Roblox username", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        key = self.key_input.value.strip().upper()
        roblox_username = self.roblox_input.value.strip()
        key_lines, key_sha, key_content = get_github_file(KEY_FILE)
        found_key = None
        for line in key_lines:
            k, date, used, max_uses, expiry, days, key_type = parse_key(line)
            if k == key:
                found_key = line
                break
        if not found_key:
            attempts = track_failed_attempt(interaction.user.id)
            if attempts >= 5:
                owner = await client.fetch_user(OWNER_ID)
                if owner:
                    alert = make_embed("🚨 Suspicious Activity!", f"**{interaction.user.mention}** has failed key redemption **{attempts}** times!\nMay be attempting to brute force keys.", "error")
                    alert.add_field(name="Discord ID", value=str(interaction.user.id), inline=True)
                    try:
                        await owner.send(embed=alert)
                    except:
                        pass
            await interaction.response.send_message(embed=make_embed("❌ Invalid Key", color_key="error"), ephemeral=True)
            return
        k, date, used, max_uses, expiry, days, key_type = parse_key(found_key)
        if used == "true":
            await interaction.response.send_message(embed=make_embed("❌ Key Already Used", color_key="error"), ephemeral=True)
            return
        if is_expired(expiry):
            await interaction.response.send_message(embed=make_embed("❌ Key Expired", color_key="error"), ephemeral=True)
            return
        user_id, roblox_name = get_roblox_user_by_username(roblox_username)
        if not user_id:
            await interaction.response.send_message(embed=make_embed("❌ Roblox User Not Found", color_key="error"), ephemeral=True)
            return
        wl_lines, wl_sha, wl_content = get_github_file(GITHUB_FILE)
        for line in wl_lines:
            uid, d, rn, ds, no, ex, us, hw, sk = parse_entry(line)
            if ds and ds == str(interaction.user.id):
                await interaction.response.send_message(embed=make_embed("⚠️ Already Whitelisted", color_key="warning"), ephemeral=True)
                return
            if uid == user_id:
                await interaction.response.send_message(embed=make_embed("⚠️ Roblox Account Already Whitelisted", color_key="warning"), ephemeral=True)
                return
        add_date = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        expiry_date = "never"
        if days and days != "never":
            try:
                expiry_dt = datetime.utcnow() + timedelta(days=int(days))
                expiry_date = expiry_dt.strftime("%Y-%m-%d %H:%M")
            except:
                pass
        new_entry = f"{user_id} | {add_date} | {roblox_name} | {interaction.user.id} | Redeemed key | {expiry_date} | 0 | none | none"
        update_github_file(GITHUB_FILE, wl_content.strip() + f"\n{new_entry}", wl_sha)
        new_key_lines = []
        for line in key_lines:
            k2, d2, u2, m2, e2, dy2, kt2 = parse_key(line)
            if k2 == key:
                new_key_lines.append(f"{k2} | {d2} | true | {m2} | {e2} | {dy2} | {kt2}")
            else:
                new_key_lines.append(line)
        update_github_file(KEY_FILE, "\n".join(new_key_lines), key_sha)
        reset_failed_attempts(interaction.user.id)
        role_given = await give_whitelist_role(interaction.guild, str(interaction.user.id))
        avatar = get_roblox_avatar(user_id)
        is_trial = key_type == "trial"
        embed = discord.Embed(
            title="✅ Key Redeemed!" if not is_trial else "🧪 Trial Key Redeemed!",
            description=(
                f"Welcome **{roblox_name}**!\n\n"
                f"{'🧪 **Trial key** — limited access.' if is_trial else ''}\n"
                f"Click **Get Script** to receive your script.\n"
                f"{'✅ Role given!' if role_given else '👤 Click Get Role for your role.'}"
            ),
            color=COLORS["warning"] if is_trial else COLORS["success"]
        )
        embed.add_field(name="Roblox", value=roblox_name, inline=True)
        embed.add_field(name="Expires", value=get_expiry_display(expiry_date), inline=True)
        if avatar:
            embed.set_image(url=avatar)
        embed.set_footer(text=f"{BRAND_NAME} Whitelist System")
        embed.timestamp = datetime.utcnow()
        await interaction.response.send_message(embed=embed, ephemeral=True)
        try:
            vouch_channel_id = get_setting("vouch_channel")
            vouch_text = f"\n\nPlease leave a vouch in <#{vouch_channel_id}>! 🙏" if vouch_channel_id else ""
            welcome_dm = discord.Embed(
                title=f"👑 Welcome to {BRAND_NAME}!",
                description=(
                    f"Hey **{roblox_name}**! Your key has been redeemed.\n\n"
                    f"**How to use:**\n"
                    f"1️⃣ Go to the panel channel\n"
                    f"2️⃣ Click **Get Script**\n"
                    f"3️⃣ Copy and run it in your executor\n\n"
                    f"**HWID Lock:** Locks to your executor on first run.\n"
                    f"Reset HWID every **1 hour** from the panel.\n\n"
                    f"{'⚠️ **Trial key** — upgrade for full access!' if is_trial else '✅ Full access!'}"
                    f"{vouch_text}"
                ),
                color=BRAND_COLOR
            )
            welcome_dm.add_field(name="Expires", value=get_expiry_display(expiry_date), inline=True)
            welcome_dm.set_footer(text=f"{BRAND_NAME} Whitelist System")
            welcome_dm.timestamp = datetime.utcnow()
            await interaction.user.send(embed=welcome_dm)
        except:
            pass
        await post_purchase(interaction.guild, roblox_name, interaction.user, expiry_date, avatar)
        log_embed = make_embed("🔑 Key Redeemed", f"**{roblox_name}** redeemed `{key}`", "success")
        log_embed.add_field(name="Discord", value=interaction.user.mention, inline=True)
        log_embed.add_field(name="Type", value="🧪 Trial" if is_trial else "✅ Full", inline=True)
        if avatar:
            log_embed.set_thumbnail(url=avatar)
        await send_log(log_embed)

# =============================================
#   EVENTS & COMMANDS
# =============================================
@client.event
async def on_ready():
    await tree.sync()
    client.add_view(PanelView())
    client.loop.create_task(check_expiries())
    client.loop.create_task(rotate_status())
    print(f"Bot is online as {client.user}")

@tree.command(name="panel", description="Send the whitelist control panel")
async def panel(interaction: discord.Interaction):
    if not owner_only(interaction):
        await interaction.response.send_message(embed=make_embed("🚫 Access Denied", color_key="error"), ephemeral=True)
        return
    embed = discord.Embed(
        title=BRAND_NAME,
        description=(
            f"This control panel is for the project: **{BRAND_NAME}**\n"
            "If you're a buyer, click on the buttons below to redeem your key, "
            "get the script or get your role."
        ),
        color=BRAND_COLOR
    )
    embed.set_footer(text=f"Sent by {interaction.user.name} • {datetime.utcnow().strftime('%m/%d/%Y %I:%M %p')}")
    await interaction.response.send_message(embed=embed, view=PanelView())

@tree.command(name="adminpanel", description="Open the admin control panel")
async def admin_panel(interaction: discord.Interaction):
    if not owner_only(interaction) and not is_reseller(interaction.user.id):
        await interaction.response.send_message(embed=make_embed("🚫 Access Denied", color_key="error"), ephemeral=True)
        return
    is_res = is_reseller(interaction.user.id) and not owner_only(interaction)
    keys_left = get_reseller_keys_left(interaction.user.id) if is_res else None
    lines, _, _ = get_github_file(GITHUB_FILE)
    ban_lines, _, _ = get_github_file(BAN_FILE)
    total = len([l for l in lines if not l.startswith("--")])
    banned = len([l for l in ban_lines if not l.startswith("--")])
    embed = discord.Embed(
        title=f"👑 {BRAND_NAME} — Admin Panel",
        description=(
            f"{'🔑 **Reseller** — Keys left: **' + str(keys_left) + '**' if is_res else '━━━━━━━━━━━━━━━━━━━━━━━━━━━━'}\n\n"
            f"✅ **Whitelisted:** {total}\n"
            f"🔨 **Banned:** {banned}\n"
        ),
        color=BRAND_COLOR
    )
    embed.set_footer(text=f"{BRAND_NAME} Admin Panel • Only you can see this")
    embed.timestamp = datetime.utcnow()
    await interaction.response.send_message(embed=embed, view=AdminPanelView(), ephemeral=True)

@tree.command(name="setrole", description="Set the whitelist role")
@app_commands.describe(role="The whitelist role")
async def set_role(interaction: discord.Interaction, role: discord.Role):
    if not owner_only(interaction):
        await interaction.response.send_message(embed=make_embed("🚫 Access Denied", color_key="error"), ephemeral=True)
        return
    set_setting("whitelist_role", role.id)
    await interaction.response.send_message(embed=make_embed("✅ Role Set", f"Whitelisted users will receive **{role.name}**.", "success"))

@tree.command(name="setlog", description="Set this channel as the log channel")
async def set_log(interaction: discord.Interaction):
    if not owner_only(interaction):
        await interaction.response.send_message(embed=make_embed("🚫 Access Denied", color_key="error"), ephemeral=True)
        return
    set_setting("log_channel", interaction.channel_id)
    await interaction.response.send_message(embed=make_embed("📋 Log Channel Set", color_key="success"))

@tree.command(name="setscript", description="Set the script for whitelisted users")
@app_commands.describe(script="The loadstring or script")
async def set_script(interaction: discord.Interaction, script: str):
    if not owner_only(interaction):
        await interaction.response.send_message(embed=make_embed("🚫 Access Denied", color_key="error"), ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    _, sha, _ = get_github_file(SCRIPT_FILE)
    update_github_file(SCRIPT_FILE, script, sha)
    await interaction.followup.send(embed=make_embed("✅ Script Set", color_key="success"), ephemeral=True)

@tree.command(name="pricelist", description="Show the price list")
async def price_list(interaction: discord.Interaction):
    prices = get_setting("price_list")
    if not prices:
        await interaction.response.send_message(embed=make_embed("❌ No Price List Set", "Owner needs to set prices via /adminpanel → Prices.", "error"), ephemeral=True)
        return
    embed = discord.Embed(
        title=f"💰 {BRAND_NAME} — Price List",
        description=prices,
        color=BRAND_COLOR
    )
    embed.set_footer(text=f"{BRAND_NAME} • DM to purchase")
    embed.timestamp = datetime.utcnow()
    await interaction.response.send_message(embed=embed)

@tree.command(name="stock", description="Show available keys stock")
async def stock(interaction: discord.Interaction):
    key_lines, _, _ = get_github_file(KEY_FILE)
    available = sum(1 for l in key_lines if parse_key(l)[2] == "false" and not is_expired(parse_key(l)[4]))
    total = len(key_lines)
    embed = discord.Embed(
        title=f"📦 {BRAND_NAME} — Stock",
        description=(
            f"🔑 **Available Keys:** {available}\n"
            f"📊 **Total Generated:** {total}\n\n"
            f"{'✅ Keys are available! DM to purchase.' if available > 0 else '❌ No keys available right now.'}"
        ),
        color=COLORS["success"] if available > 0 else COLORS["error"]
    )
    embed.set_footer(text=f"{BRAND_NAME} • Updated live")
    embed.timestamp = datetime.utcnow()
    await interaction.response.send_message(embed=embed)

@tree.command(name="help", description="Show all commands")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(
        title=f"{BRAND_NAME} — Help",
        description="━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        color=BRAND_COLOR
    )
    embed.add_field(name="🎛️ Main", value="`/panel` `/adminpanel` `/setscript` `/setrole` `/setlog`", inline=False)
    embed.add_field(name="📦 Public", value="`/pricelist` `/stock`", inline=False)
    embed.add_field(name="👑 Admin Panel Buttons", value="➕ Add • ➖ Remove • 🔨 Ban • ✅ Unban • 📅 Extend\n🔑 Gen Key • 📋 List • 📢 Announce • 🔄 Transfer\n🔒 HWID • 🔑 Keys • 👥 Resellers • 💰 Prices • 📌 Channels", inline=False)
    embed.add_field(name="👤 User Panel", value="🔑 Redeem • 📜 Get Script • 👤 Get Role\n🔄 Reset HWID • 📊 Get Stats", inline=False)
    embed.set_footer(text=f"{BRAND_NAME} Whitelist System")
    embed.timestamp = datetime.utcnow()
    await interaction.response.send_message(embed=embed, ephemeral=True)

print("Starting bot...")
client.run(TOKEN)

