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
HWID_RESET_FILE = "hwid_resets.txt"
SETTINGS_FILE = "settings.json"
RESELLERS_FILE = "resellers.txt"

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
    "success": 0x57F287,
    "error": 0xED4245,
    "warning": 0xFEE75C,
    "info": 0x5865F2,
    "ban": 0xFF4500,
    "purple": 0x9B59B6,
    "blue": 0x00BFFF,
    "gold": 0xFFD700,
    "dark": 0x2B2D31
}

# =============================================
#   SETTINGS (persisted to GitHub)
# =============================================
def load_settings():
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{SETTINGS_FILE}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 404:
        return {"log_channel": None, "whitelist_role": None, "panel_channel": None}
    data = r.json()
    content = base64.b64decode(data["content"]).decode("utf-8")
    try:
        return json.loads(content)
    except:
        return {"log_channel": None, "whitelist_role": None, "panel_channel": None}

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
                next_reset = last_reset + timedelta(days=3)
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

async def send_log(embed):
    log_id = get_setting("log_channel")
    if log_id:
        channel = client.get_channel(int(log_id))
        if channel:
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
        except:
            pass
    return False

async def remove_whitelist_role(guild, discord_user_id):
    role_id = get_setting("whitelist_role")
    if role_id and guild:
        try:
            member = guild.get_member(int(discord_user_id))
            if member:
                role = guild.get_role(int(role_id))
                if role:
                    await member.remove_roles(role)
        except:
            pass

def owner_only(interaction):
    return interaction.user.id == OWNER_ID

def owner_or_reseller(interaction):
    return interaction.user.id == OWNER_ID or is_reseller(interaction.user.id)

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
#   VIEWS
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
        embed = discord.Embed(title="❌ Cancelled", color=COLORS["error"])
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()

class ScriptView(discord.ui.View):
    def __init__(self, script_text):
        super().__init__(timeout=60)
        self.script_text = script_text

    @discord.ui.button(label="📋 Copy Script", style=discord.ButtonStyle.grey)
    async def copy_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            f"```lua\n{self.script_text}\n```",
            ephemeral=True
        )

class AdminPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)

    @discord.ui.button(label="➕ Add User", style=discord.ButtonStyle.green, row=0)
    async def add_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not owner_only(interaction):
            await interaction.response.send_message("🚫 Access Denied", ephemeral=True)
            return
        await interaction.response.send_modal(AddUserModal())

    @discord.ui.button(label="➖ Remove User", style=discord.ButtonStyle.red, row=0)
    async def remove_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not owner_only(interaction):
            await interaction.response.send_message("🚫 Access Denied", ephemeral=True)
            return
        await interaction.response.send_modal(RemoveUserModal())

    @discord.ui.button(label="🔨 Ban User", style=discord.ButtonStyle.red, row=0)
    async def ban_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not owner_only(interaction):
            await interaction.response.send_message("🚫 Access Denied", ephemeral=True)
            return
        await interaction.response.send_modal(BanUserModal())

    @discord.ui.button(label="🔑 Gen Key", style=discord.ButtonStyle.blurple, row=1)
    async def genkey_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not owner_or_reseller(interaction):
            await interaction.response.send_message("🚫 Access Denied", ephemeral=True)
            return
        embed = discord.Embed(title="🔑 Generate Key", description="Select key duration:", color=COLORS["gold"])
        await interaction.response.send_message(embed=embed, view=GenerateKeyView(), ephemeral=True)

    @discord.ui.button(label="📋 List Users", style=discord.ButtonStyle.grey, row=1)
    async def list_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not owner_only(interaction):
            await interaction.response.send_message("🚫 Access Denied", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        lines, _, _ = get_github_file(GITHUB_FILE)
        ban_lines, _, _ = get_github_file(BAN_FILE)
        entries = [l for l in lines if not l.startswith("--")]
        ban_entries = [l for l in ban_lines if not l.startswith("--")]
        github_url = f"https://github.com/{GITHUB_REPO}/blob/main/{GITHUB_FILE}"
        embed = discord.Embed(title="📋 ꜱᴇᴍɪ-ɪɴꜱᴛᴀɴᴛ WHITELIST", color=COLORS["info"])
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
                expiry_text = expiry if expiry and expiry != "never" else "Never"
                embed.description += f"{status} **{name}** — {discord_mention} • Expires: {expiry_text}\n"
        embed.description += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        embed.add_field(name="✅ Whitelisted", value=str(len(entries)), inline=True)
        embed.add_field(name="🔨 Banned", value=str(len(ban_entries)), inline=True)
        embed.set_footer(text="ꜱᴇᴍɪ-ɪɴꜱᴛᴀɴᴛ Whitelist")
        embed.timestamp = datetime.utcnow()
        await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(label="📢 Announce", style=discord.ButtonStyle.grey, row=1)
    async def announce_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not owner_only(interaction):
            await interaction.response.send_message("🚫 Access Denied", ephemeral=True)
            return
        await interaction.response.send_modal(AnnounceModal())

    @discord.ui.button(label="🔒 HWID Panel", style=discord.ButtonStyle.grey, row=2)
    async def hwid_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not owner_only(interaction):
            await interaction.response.send_message("🚫 Access Denied", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        lines, _, _ = get_github_file(GITHUB_FILE)
        entries = []
        for line in lines:
            if not line.startswith("--"):
                uid, date, roblox_name, discord_str, note, expiry, uses, hwid, script_key = parse_entry(line)
                if hwid and hwid != "none":
                    entries.append((uid, roblox_name or uid, discord_str or "none"))
        if not entries:
            embed = discord.Embed(title="🔒 HWID Panel", description="No HWID locked users.", color=COLORS["info"])
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        embed = discord.Embed(title="🔒 HWID Reset Panel", description="Tap a user to reset their HWID.", color=COLORS["gold"])
        view = HWIDResetView(entries)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="🔑 Key List", style=discord.ButtonStyle.grey, row=2)
    async def keylist_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not owner_only(interaction):
            await interaction.response.send_message("🚫 Access Denied", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        key_lines, _, _ = get_github_file(KEY_FILE)
        if not key_lines:
            embed = discord.Embed(title="🔑 No Keys", color=COLORS["info"])
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        desc = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        for line in key_lines:
            k, date, used, max_uses, expiry, days, key_type = parse_key(line)
            status = "✅" if used == "false" else "❌"
            if is_expired(expiry):
                status = "⚠️"
            trial = " 🧪" if key_type == "trial" else ""
            desc += f"{status} `{k}`{trial} — {expiry if expiry != 'never' else 'Never'}\n"
        desc += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        embed = discord.Embed(title="🔑 All Keys", description=desc, color=COLORS["gold"])
        embed.add_field(name="Total", value=str(len(key_lines)), inline=True)
        embed.timestamp = datetime.utcnow()
        await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(label="👥 Resellers", style=discord.ButtonStyle.grey, row=2)
    async def resellers_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not owner_only(interaction):
            await interaction.response.send_message("🚫 Access Denied", ephemeral=True)
            return
        await interaction.response.send_modal(ResellerModal())

class AddUserModal(discord.ui.Modal, title="➕ Add User"):
    username = discord.ui.TextInput(label="Roblox Username", placeholder="Enter Roblox username", required=True)
    days_input = discord.ui.TextInput(label="Days (leave empty for permanent)", placeholder="e.g. 30", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user_id, roblox_name = get_roblox_user_by_username(self.username.value.strip())
        if not user_id:
            embed = discord.Embed(title="❌ User Not Found", color=COLORS["error"])
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        lines, sha, content = get_github_file(GITHUB_FILE)
        if user_id in get_ids_only(lines):
            embed = discord.Embed(title="⚠️ Already Whitelisted", color=COLORS["warning"])
            await interaction.followup.send(embed=embed, ephemeral=True)
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
        embed = discord.Embed(title="✅ User Added", color=COLORS["success"])
        embed.add_field(name="Roblox", value=roblox_name, inline=True)
        embed.add_field(name="Expires", value=expiry if expiry != "never" else "Never", inline=True)
        embed.timestamp = datetime.utcnow()
        await interaction.followup.send(embed=embed, ephemeral=True)
        await send_log(embed)

class RemoveUserModal(discord.ui.Modal, title="➖ Remove User"):
    username = discord.ui.TextInput(label="Roblox Username", placeholder="Enter Roblox username", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user_id, roblox_name = get_roblox_user_by_username(self.username.value.strip())
        if not user_id:
            embed = discord.Embed(title="❌ User Not Found", color=COLORS["error"])
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        lines, sha, _ = get_github_file(GITHUB_FILE)
        found_line = next((l for l in lines if l.startswith(user_id)), None)
        if not found_line:
            embed = discord.Embed(title="❌ Not Whitelisted", color=COLORS["error"])
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        _, _, _, discord_str, _, _, _, _, _ = parse_entry(found_line)
        new_lines = [l for l in lines if not l.startswith(user_id)]
        update_github_file(GITHUB_FILE, "\n".join(new_lines), sha)
        if discord_str and discord_str != "none":
            await remove_whitelist_role(interaction.guild, discord_str)
            try:
                member = interaction.guild.get_member(int(discord_str))
                if member:
                    dm = discord.Embed(title="❌ Whitelist Removed", description="Your access has been removed.", color=COLORS["error"])
                    await member.send(embed=dm)
            except:
                pass
        embed = discord.Embed(title="🗑️ User Removed", description=f"**{roblox_name}** removed.", color=COLORS["ban"])
        embed.timestamp = datetime.utcnow()
        await interaction.followup.send(embed=embed, ephemeral=True)
        await send_log(embed)

class BanUserModal(discord.ui.Modal, title="🔨 Ban User"):
    username = discord.ui.TextInput(label="Roblox Username", placeholder="Enter Roblox username", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user_id, roblox_name = get_roblox_user_by_username(self.username.value.strip())
        if not user_id:
            embed = discord.Embed(title="❌ User Not Found", color=COLORS["error"])
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        ban_lines, ban_sha, ban_content = get_github_file(BAN_FILE)
        if user_id in get_ids_only(ban_lines):
            embed = discord.Embed(title="⚠️ Already Banned", color=COLORS["warning"])
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        lines, sha, _ = get_github_file(GITHUB_FILE)
        found_line = next((l for l in lines if l.startswith(user_id)), None)
        discord_str = None
        if found_line:
            _, _, _, discord_str, _, _, _, _, _ = parse_entry(found_line)
            new_lines = [l for l in lines if not l.startswith(user_id)]
            update_github_file(GITHUB_FILE, "\n".join(new_lines), sha)
        date = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        update_github_file(BAN_FILE, ban_content.strip() + f"\n{user_id} | {date} | {roblox_name}", ban_sha)
        if discord_str and discord_str != "none":
            await remove_whitelist_role(interaction.guild, discord_str)
            try:
                member = interaction.guild.get_member(int(discord_str))
                if member:
                    dm = discord.Embed(title="🔨 You have been Banned", color=COLORS["error"])
                    await member.send(embed=dm)
            except:
                pass
        embed = discord.Embed(title="🔨 User Banned", description=f"**{roblox_name}** banned.", color=COLORS["error"])
        embed.timestamp = datetime.utcnow()
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
                        dm_embed = discord.Embed(
                            title=f"📢 {self.title_input.value}",
                            description=self.message_input.value,
                            color=COLORS["gold"]
                        )
                        dm_embed.set_footer(text="ꜱᴇᴍɪ-ɪɴꜱᴛᴀɴᴛ Whitelist")
                        dm_embed.timestamp = datetime.utcnow()
                        await member.send(embed=dm_embed)
                        sent += 1
                except:
                    failed += 1
        embed = discord.Embed(
            title="📢 Announcement Sent",
            description=f"✅ Sent to **{sent}** users\n❌ Failed: **{failed}**",
            color=COLORS["success"]
        )
        embed.timestamp = datetime.utcnow()
        await interaction.followup.send(embed=embed, ephemeral=True)

class ResellerModal(discord.ui.Modal, title="👥 Manage Reseller"):
    discord_id = discord.ui.TextInput(label="Discord ID", placeholder="Their Discord user ID", required=True)
    keys_count = discord.ui.TextInput(label="Number of keys to give", placeholder="e.g. 5", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            uid = int(self.discord_id.value.strip())
            count = int(self.keys_count.value.strip())
        except:
            embed = discord.Embed(title="❌ Invalid Input", color=COLORS["error"])
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        current = get_reseller_keys_left(uid)
        set_reseller_keys(uid, current + count)
        embed = discord.Embed(
            title="✅ Reseller Updated",
            description=f"<@{uid}> now has **{current + count}** keys to generate.",
            color=COLORS["success"]
        )
        embed.timestamp = datetime.utcnow()
        await interaction.followup.send(embed=embed, ephemeral=True)
        try:
            member = interaction.guild.get_member(uid)
            if member:
                dm = discord.Embed(
                    title="🔑 You are now a Reseller!",
                    description=f"You have been given **{count}** keys to generate and sell.\n\nUse `/adminpanel` to generate keys.",
                    color=COLORS["gold"]
                )
                dm.set_footer(text="ꜱᴇᴍɪ-ɪɴꜱᴛᴀɴᴛ Whitelist")
                await member.send(embed=dm)
        except:
            pass

class HWIDResetView(discord.ui.View):
    def __init__(self, entries):
        super().__init__(timeout=60)
        for i, (uid, roblox_name, discord_str) in enumerate(entries[:10]):
            button = discord.ui.Button(
                label=f"🔄 {roblox_name[:20]}",
                style=discord.ButtonStyle.red,
                row=i // 3
            )
            button.callback = self.make_callback(uid, roblox_name, discord_str)
            self.add_item(button)

    def make_callback(self, uid, roblox_name, discord_str):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != OWNER_ID:
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
            embed = discord.Embed(title="🔄 HWID Reset", description=f"**{roblox_name}**'s HWID reset.", color=COLORS["success"])
            embed.timestamp = datetime.utcnow()
            await interaction.response.edit_message(embed=embed, view=None)
        return callback

class GenerateKeyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(label="⏰ 4 Hours", style=discord.ButtonStyle.blurple)
    async def key_4h(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._generate(interaction, hours=4, label="4 Hours")

    @discord.ui.button(label="🌙 1 Day", style=discord.ButtonStyle.blurple)
    async def key_1d(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._generate(interaction, hours=24, label="1 Day")

    @discord.ui.button(label="📅 7 Days", style=discord.ButtonStyle.blurple)
    async def key_7d(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._generate(interaction, hours=168, label="7 Days")

    @discord.ui.button(label="♾️ Permanent", style=discord.ButtonStyle.green)
    async def key_perm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._generate(interaction, hours=None, label="Permanent")

    @discord.ui.button(label="🧪 Trial (1hr)", style=discord.ButtonStyle.grey)
    async def key_trial(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._generate(interaction, hours=1, label="Trial 1 Hour", key_type="trial")

    async def _generate(self, interaction: discord.Interaction, hours, label, key_type="normal"):
        is_owner = interaction.user.id == OWNER_ID
        is_res = is_reseller(interaction.user.id)
        if not is_owner and not is_res:
            await interaction.response.send_message("🚫 Access Denied", ephemeral=True)
            return
        if is_res and not is_owner:
            keys_left = get_reseller_keys_left(interaction.user.id)
            if keys_left <= 0:
                embed = discord.Embed(title="❌ No Keys Left", description="You have no keys left to generate. Contact the owner.", color=COLORS["error"])
                await interaction.response.edit_message(embed=embed, view=None)
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
            dm_embed = discord.Embed(title="🔑 New Key Generated", color=COLORS["gold"])
            dm_embed.add_field(name="🔑 Key", value=f"`{key}`", inline=False)
            dm_embed.add_field(name="Type", value="🧪 Trial" if key_type == "trial" else "✅ Full", inline=True)
            dm_embed.add_field(name="Duration", value=label, inline=True)
            dm_embed.add_field(name="Expires", value=expiry if expiry != "never" else "Never", inline=True)
            dm_embed.set_footer(text="⚠️ Single use only!")
            dm_embed.timestamp = datetime.utcnow()
            await interaction.user.send(embed=dm_embed)
            confirm_embed = discord.Embed(
                title="✅ Key Sent to DMs",
                description=f"A **{label}** key sent!\n⚠️ Single use only.",
                color=COLORS["success"]
            )
            await interaction.response.edit_message(embed=confirm_embed, view=None)
        except:
            embed = discord.Embed(title="❌ DM Failed", color=COLORS["error"])
            await interaction.response.edit_message(embed=embed, view=None)
        self.stop()

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
            embed = discord.Embed(title="❌ Not Whitelisted", description="Redeem a key first.", color=COLORS["error"])
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        uid, date, roblox_name, discord_str, note, expiry, uses, hwid, script_key = user_entry
        if is_expired(expiry):
            embed = discord.Embed(title="⚠️ Access Expired", color=COLORS["warning"])
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        _, _, script_content = get_github_file(SCRIPT_FILE)
        if not script_content:
            embed = discord.Embed(title="❌ No Script Set", color=COLORS["error"])
            await interaction.response.send_message(embed=embed, ephemeral=True)
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
            embed = discord.Embed(title="❌ No Role Set", color=COLORS["error"])
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        lines, _, _ = get_github_file(GITHUB_FILE)
        user_entry = None
        for line in lines:
            uid, date, roblox_name, discord_str, note, expiry, uses, hwid, script_key = parse_entry(line)
            if discord_str and discord_str == str(interaction.user.id):
                user_entry = (uid, date, roblox_name, discord_str, note, expiry, uses, hwid, script_key)
                break
        if not user_entry:
            embed = discord.Embed(title="❌ Not Whitelisted", color=COLORS["error"])
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        uid, date, roblox_name, discord_str, note, expiry, uses, hwid, script_key = user_entry
        if is_expired(expiry):
            embed = discord.Embed(title="⚠️ Access Expired", color=COLORS["warning"])
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        role = interaction.guild.get_role(int(role_id))
        if not role:
            embed = discord.Embed(title="❌ Role Not Found", color=COLORS["error"])
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        if role in interaction.user.roles:
            embed = discord.Embed(title="✅ Already Have Role", color=COLORS["warning"])
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        await interaction.user.add_roles(role)
        embed = discord.Embed(title="✅ Role Given", description=f"You now have **{role.name}**!", color=COLORS["success"])
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="🔄 Reset HWID", style=discord.ButtonStyle.grey, custom_id="panel_hwid", row=1)
    async def reset_hwid(self, interaction: discord.Interaction, button: discord.ui.Button):
        next_reset = get_hwid_reset_time(interaction.user.id)
        if next_reset:
            time_left = next_reset - datetime.utcnow()
            hours_left = int(time_left.total_seconds() // 3600)
            minutes_left = int((time_left.total_seconds() % 3600) // 60)
            embed = discord.Embed(
                title="⏳ HWID Reset Cooldown",
                description=f"Reset available in **{hours_left}h {minutes_left}m**.",
                color=COLORS["warning"]
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
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
            embed = discord.Embed(title="❌ Not Whitelisted", color=COLORS["error"])
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        update_github_file(GITHUB_FILE, "\n".join(new_lines), sha)
        set_hwid_reset_time(interaction.user.id)
        embed = discord.Embed(title="🔄 HWID Reset", description="Done! Next reset in **72 hours**.", color=COLORS["success"])
        embed.timestamp = datetime.utcnow()
        await interaction.response.send_message(embed=embed, ephemeral=True)
        if get_setting("log_channel"):
            log_embed = discord.Embed(title="🔄 HWID Reset", description=f"{interaction.user.mention} reset HWID.", color=COLORS["warning"])
            log_embed.timestamp = datetime.utcnow()
            await send_log(log_embed)

    @discord.ui.button(label="📊 Get Stats", style=discord.ButtonStyle.grey, custom_id="panel_stats", row=1)
    async def get_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        lines, _, _ = get_github_file(GITHUB_FILE)
        for line in lines:
            uid, date, roblox_name, discord_str, note, expiry, uses, hwid, script_key = parse_entry(line)
            if discord_str and discord_str == str(interaction.user.id):
                expired = is_expired(expiry)
                next_hwid = get_hwid_reset_time(interaction.user.id)
                embed = discord.Embed(title="📊 Your Stats", color=COLORS["warning"] if expired else COLORS["success"])
                embed.add_field(name="Roblox", value=roblox_name or uid, inline=True)
                embed.add_field(name="Status", value="⚠️ Expired" if expired else "✅ Active", inline=True)
                embed.add_field(name="Added", value=date, inline=True)
                embed.add_field(name="Expires", value=expiry if expiry and expiry != "never" else "Never", inline=True)
                embed.add_field(name="HWID", value="🔒 Locked" if hwid and hwid != "none" else "🔓 Unlocked", inline=True)
                if next_hwid:
                    time_left = next_hwid - datetime.utcnow()
                    embed.add_field(name="Next HWID Reset", value=f"In {int(time_left.total_seconds() // 3600)}h", inline=True)
                else:
                    embed.add_field(name="Next HWID Reset", value="Available ✅", inline=True)
                avatar = get_roblox_avatar(uid)
                if avatar:
                    embed.set_image(url=avatar)
                embed.set_footer(text="ꜱᴇᴍɪ-ɪɴꜱᴛᴀɴᴛ Whitelist System")
                embed.timestamp = datetime.utcnow()
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
        embed = discord.Embed(title="❌ Not Whitelisted", color=COLORS["error"])
        await interaction.response.send_message(embed=embed, ephemeral=True)

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
            embed = discord.Embed(title="❌ Invalid Key", color=COLORS["error"])
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        k, date, used, max_uses, expiry, days, key_type = parse_key(found_key)
        if used == "true":
            embed = discord.Embed(title="❌ Key Already Used", color=COLORS["error"])
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        if is_expired(expiry):
            embed = discord.Embed(title="❌ Key Expired", color=COLORS["error"])
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        user_id, roblox_name = get_roblox_user_by_username(roblox_username)
        if not user_id:
            embed = discord.Embed(title="❌ Roblox User Not Found", color=COLORS["error"])
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        wl_lines, wl_sha, wl_content = get_github_file(GITHUB_FILE)
        for line in wl_lines:
            uid, d, rn, ds, no, ex, us, hw, sk = parse_entry(line)
            if ds and ds == str(interaction.user.id):
                embed = discord.Embed(title="⚠️ Already Whitelisted", color=COLORS["warning"])
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            if uid == user_id:
                embed = discord.Embed(title="⚠️ Roblox Account Already Whitelisted", color=COLORS["warning"])
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
        role_given = False
        role_id = get_setting("whitelist_role")
        if role_id and interaction.guild:
            role = interaction.guild.get_role(int(role_id))
            if role:
                try:
                    await interaction.user.add_roles(role)
                    role_given = True
                except:
                    pass
        avatar = get_roblox_avatar(user_id)
        is_trial = key_type == "trial"
        embed = discord.Embed(
            title="✅ Key Redeemed!" if not is_trial else "🧪 Trial Key Redeemed!",
            description=(
                f"Welcome **{roblox_name}**!\n\n"
                f"{'🧪 This is a **trial key** — access is limited.' if is_trial else ''}\n"
                f"Click **Get Script** to receive your script.\n"
                f"{'✅ Role given!' if role_given else '👤 Click Get Role for your role.'}"
            ),
            color=COLORS["warning"] if is_trial else COLORS["success"]
        )
        embed.add_field(name="Roblox", value=roblox_name, inline=True)
        embed.add_field(name="Expires", value=expiry_date if expiry_date != "never" else "Never", inline=True)
        if avatar:
            embed.set_image(url=avatar)
        embed.set_footer(text="ꜱᴇᴍɪ-ɪɴꜱᴛᴀɴᴛ Whitelist System")
        embed.timestamp = datetime.utcnow()
        await interaction.response.send_message(embed=embed, ephemeral=True)
        try:
            welcome_dm = discord.Embed(
                title="👑 Welcome to ꜱᴇᴍɪ-ɪɴꜱᴛᴀɴᴛ!",
                description=(
                    f"Hey **{roblox_name}**! Your key has been redeemed successfully.\n\n"
                    f"**How to use:**\n"
                    f"1️⃣ Go to the panel channel\n"
                    f"2️⃣ Click **Get Script** to get your script\n"
                    f"3️⃣ Copy and run it in your executor\n\n"
                    f"**HWID Lock:** Your script will lock to your executor on first run.\n"
                    f"You can reset HWID every **3 days** from the panel.\n\n"
                    f"{'⚠️ This is a **trial key**. Upgrade for full access!' if is_trial else '✅ You have full access!'}"
                ),
                color=COLORS["gold"]
            )
            welcome_dm.add_field(name="Expires", value=expiry_date if expiry_date != "never" else "Never", inline=True)
            welcome_dm.set_footer(text="ꜱᴇᴍɪ-ɪɴꜱᴛᴀɴᴛ Whitelist System")
            welcome_dm.timestamp = datetime.utcnow()
            await interaction.user.send(embed=welcome_dm)
        except:
            pass
        log_id = get_setting("log_channel")
        if log_id:
            log_embed = discord.Embed(title="🔑 Key Redeemed", description=f"**{roblox_name}** redeemed `{key}`", color=COLORS["success"])
            log_embed.add_field(name="Discord", value=interaction.user.mention, inline=True)
            log_embed.add_field(name="Type", value="🧪 Trial" if is_trial else "✅ Full", inline=True)
            if avatar:
                log_embed.set_thumbnail(url=avatar)
            log_embed.timestamp = datetime.utcnow()
            await send_log(log_embed)

@client.event
async def on_ready():
    await tree.sync()
    client.add_view(PanelView())
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="ꜱᴇᴍɪ-ɪɴꜱᴛᴀɴᴛ"))
    print(f"Bot is online as {client.user}")

@tree.command(name="panel", description="Send the ꜱᴇᴍɪ-ɪɴꜱᴛᴀɴᴛ whitelist control panel")
async def panel(interaction: discord.Interaction):
    if not owner_only(interaction):
        embed = discord.Embed(title="🚫 Access Denied", color=COLORS["error"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    embed = discord.Embed(
        title="ꜱᴇᴍɪ-ɪɴꜱᴛᴀɴᴛ",
        description=(
            "This control panel is for the project: **ꜱᴇᴍɪ-ɪɴꜱᴛᴀɴᴛ**\n"
            "If you're a buyer, click on the buttons below to redeem your key, "
            "get the script or get your role."
        ),
        color=COLORS["gold"]
    )
    embed.set_footer(text=f"Sent by {interaction.user.name} • {datetime.utcnow().strftime('%m/%d/%Y %I:%M %p')}")
    await interaction.response.send_message(embed=embed, view=PanelView())

@tree.command(name="adminpanel", description="Open the admin control panel")
async def admin_panel(interaction: discord.Interaction):
    if not owner_only(interaction) and not is_reseller(interaction.user.id):
        embed = discord.Embed(title="🚫 Access Denied", color=COLORS["error"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    is_res = is_reseller(interaction.user.id) and not owner_only(interaction)
    keys_left = get_reseller_keys_left(interaction.user.id) if is_res else None
    embed = discord.Embed(
        title="👑 Admin Panel — ꜱᴇᴍɪ-ɪɴꜱᴛᴀɴᴛ",
        description=(
            f"{'🔑 You are a **Reseller** — Keys left: **' + str(keys_left) + '**' if is_res else 'Welcome back! Use the buttons to manage the whitelist.'}"
        ),
        color=COLORS["gold"]
    )
    embed.set_footer(text="ꜱᴇᴍɪ-ɪɴꜱᴛᴀɴᴛ Admin Panel • Only you can see this")
    embed.timestamp = datetime.utcnow()
    await interaction.response.send_message(embed=embed, view=AdminPanelView(), ephemeral=True)

@tree.command(name="setrole", description="Set the whitelist role")
@app_commands.describe(role="The whitelist role")
async def set_role(interaction: discord.Interaction, role: discord.Role):
    if not owner_only(interaction):
        embed = discord.Embed(title="🚫 Access Denied", color=COLORS["error"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    set_setting("whitelist_role", role.id)
    embed = discord.Embed(title="✅ Role Set", description=f"Whitelisted users will receive **{role.name}**.", color=COLORS["success"])
    embed.timestamp = datetime.utcnow()
    await interaction.response.send_message(embed=embed)

@tree.command(name="setlog", description="Set this channel as the log channel")
async def set_log(interaction: discord.Interaction):
    if not owner_only(interaction):
        embed = discord.Embed(title="🚫 Access Denied", color=COLORS["error"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    set_setting("log_channel", interaction.channel_id)
    embed = discord.Embed(title="📋 Log Channel Set", color=COLORS["success"])
    embed.timestamp = datetime.utcnow()
    await interaction.response.send_message(embed=embed)

@tree.command(name="setscript", description="Set the script for whitelisted users")
@app_commands.describe(script="The loadstring or script")
async def set_script(interaction: discord.Interaction, script: str):
    if not owner_only(interaction):
        embed = discord.Embed(title="🚫 Access Denied", color=COLORS["error"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    _, sha, _ = get_github_file(SCRIPT_FILE)
    update_github_file(SCRIPT_FILE, script, sha)
    embed = discord.Embed(title="✅ Script Set", color=COLORS["success"])
    embed.timestamp = datetime.utcnow()
    await interaction.followup.send(embed=embed, ephemeral=True)

@tree.command(name="help", description="Show all commands")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(
        title="ꜱᴇᴍɪ-ɪɴꜱᴛᴀɴᴛ — Help",
        description="━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        color=COLORS["gold"]
    )
    embed.add_field(name="🎛️ Main Commands", value="`/panel` — Send user panel\n`/adminpanel` — Open admin panel\n`/setscript` — Set the script\n`/setrole` — Set whitelist role\n`/setlog` — Set log channel", inline=False)
    embed.add_field(name="👑 Admin Panel Buttons", value="➕ Add • ➖ Remove • 🔨 Ban\n🔑 Gen Key • 📋 List • 📢 Announce\n🔒 HWID Panel • 🔑 Key List • 👥 Resellers", inline=False)
    embed.add_field(name="👤 User Panel Buttons", value="🔑 Redeem • 📜 Get Script • 👤 Get Role\n🔄 Reset HWID • 📊 Get Stats", inline=False)
    embed.set_footer(text="ꜱᴇᴍɪ-ɪɴꜱᴛᴀɴᴛ Whitelist System")
    embed.timestamp = datetime.utcnow()
    await interaction.response.send_message(embed=embed, ephemeral=True)

print("Starting bot...")
client.run(TOKEN)
