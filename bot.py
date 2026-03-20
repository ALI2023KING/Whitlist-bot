import discord
from discord import app_commands
import os
import requests
import base64
import json
import random
import string
import hashlib
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
TRIAL_FILE = "trial.txt"

BRAND_COLOR = 0xFFD700
BRAND_NAME = "ꜱᴇᴍɪ-ɪɴꜱᴛᴀɴᴛ"

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
    "gold": BRAND_COLOR,
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
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        data = r.json()
        if "data" in data and data["data"]:
            img = data["data"][0].get("imageUrl", "")
            if img.startswith("http"):
                return img
    except:
        pass
    return None

def get_roblox_user_by_username(username):
    try:
        url = "https://users.roblox.com/v1/usernames/users"
        r = requests.post(url, headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"},
                         json={"usernames": [username], "excludeBannedUsers": False}, timeout=5)
        data = r.json()
        if "data" in data and data["data"]:
            return str(data["data"][0]["id"]), data["data"][0]["name"]
    except:
        pass
    return None, None

def parse_entry(line):
    parts = [p.strip() for p in line.split("|")]
    while len(parts) < 9:
        parts.append(None)
    return parts[0], parts[1], parts[2], parts[3], parts[4], parts[5], parts[6] or "0", parts[7], parts[8]

def parse_key(line):
    parts = [p.strip() for p in line.split("|")]
    while len(parts) < 7:
        parts.append(None)
    return parts[0], parts[1], parts[2] or "false", parts[3] or "1", parts[4] or "never", parts[5] or "never", parts[6] or "normal"

def get_ids_only(lines):
    return [parse_entry(l)[0] for l in lines if not l.startswith("--")]

def is_expired(expiry_str):
    if not expiry_str or expiry_str == "never":
        return False
    try:
        return datetime.utcnow() > datetime.strptime(expiry_str, "%Y-%m-%d %H:%M")
    except:
        return False

def get_expiry_display(expiry_str):
    if not expiry_str or expiry_str == "never":
        return "♾️ Permanent"
    try:
        expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d %H:%M")
        now = datetime.utcnow()
        if now > expiry_date:
            return "⚠️ Expired"
        diff = expiry_date - now
        days = diff.days
        hours = diff.seconds // 3600
        if days > 0:
            return f"⏰ {days}d {hours}h left"
        return f"⏰ {hours}h left"
    except:
        return expiry_str

def generate_key(prefix="SEMI"):
    return "-".join([prefix] + ["".join(random.choices(string.ascii_uppercase + string.digits, k=4)) for _ in range(3)])

def generate_script_key(uid, dstr):
    raw = f"{uid}{dstr}SEMIINSTANT2026"
    return "SK-" + hashlib.md5(raw.encode()).hexdigest()[:24].upper()

def get_hwid_reset_time(discord_id):
    lines, _, _ = get_github_file(HWID_RESET_FILE)
    for line in lines:
        parts = line.split("|")
        if len(parts) >= 2 and parts[0].strip() == str(discord_id):
            try:
                last = datetime.strptime(parts[1].strip(), "%Y-%m-%d %H:%M")
                nxt = last + timedelta(days=2)
                if datetime.utcnow() < nxt:
                    return nxt
            except:
                pass
    return None

def set_hwid_reset_time(discord_id):
    lines, sha, _ = get_github_file(HWID_RESET_FILE)
    new_lines = [l for l in lines if not l.startswith(str(discord_id))]
    new_lines.append(f"{discord_id} | {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}")
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
    count = 1
    for line in lines:
        parts = line.split("|")
        if parts[0].strip() == str(discord_id):
            count = int(parts[1].strip()) + 1
            new_lines.append(f"{discord_id} | {count} | {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"{discord_id} | 1 | {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}")
    update_github_file(FAILED_ATTEMPTS_FILE, "\n".join(new_lines), sha)
    return count

def reset_failed_attempts(discord_id):
    lines, sha, _ = get_github_file(FAILED_ATTEMPTS_FILE)
    update_github_file(FAILED_ATTEMPTS_FILE, "\n".join([l for l in lines if l.split("|")[0].strip() != str(discord_id)]), sha)

async def send_log(embed):
    log_id = get_setting("log_channel")
    if log_id:
        ch = client.get_channel(int(log_id))
        if ch:
            await ch.send(embed=embed)

async def post_purchase(guild, roblox_name, discord_user, expiry, avatar=None):
    cid = get_setting("purchase_channel")
    if cid:
        ch = guild.get_channel(int(cid))
        if ch:
            e = discord.Embed(title="🎉 New Purchase!", description=f"{discord_user.mention} just got access to **{BRAND_NAME}**!", color=COLORS["success"])
            e.add_field(name="Roblox", value=roblox_name, inline=True)
            e.add_field(name="Expires", value=get_expiry_display(expiry), inline=True)
            if avatar:
                e.set_thumbnail(url=avatar)
            e.set_footer(text=f"{BRAND_NAME}")
            e.timestamp = datetime.utcnow()
            await ch.send(embed=e)

async def give_whitelist_role(guild, discord_user_id):
    role_id = get_setting("whitelist_role")
    if not role_id or not guild:
        return False
    try:
        member = guild.get_member(int(discord_user_id))
        if not member:
            member = await guild.fetch_member(int(discord_user_id))
        if member:
            role = guild.get_role(int(role_id))
            if role:
                await member.add_roles(role)
                return True
    except Exception as e:
        print(f"give_role error: {e}")
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
    e = discord.Embed(title=title, color=COLORS.get(color_key, BRAND_COLOR))
    if description:
        e.description = description
    e.set_footer(text=f"{BRAND_NAME} Whitelist System")
    e.timestamp = datetime.utcnow()
    return e

# =============================================
#   BACKGROUND TASKS
# =============================================
async def check_expiries():
    await client.wait_until_ready()
    while not client.is_closed():
        try:
            lines, _, _ = get_github_file(GITHUB_FILE)
            now = datetime.utcnow()
            for line in lines:
                if line.startswith("--"):
                    continue
                uid, date, roblox_name, discord_str, note, expiry, uses, hwid, script_key = parse_entry(line)
                if expiry and expiry != "never":
                    try:
                        expiry_dt = datetime.strptime(expiry, "%Y-%m-%d %H:%M")
                        diff = expiry_dt - now
                        if 0 < diff.total_seconds() < 3600:
                            if discord_str and discord_str != "none":
                                for guild in client.guilds:
                                    member = guild.get_member(int(discord_str))
                                    if member:
                                        try:
                                            minutes = int(diff.total_seconds() // 60)
                                            dm = make_embed("⏰ Access Expiring Soon!", f"Hey **{roblox_name}**!\n\nYour **{BRAND_NAME}** access expires in **{minutes} minutes**!\n\nContact the owner to renew!", "warning")
                                            await member.send(embed=dm)
                                        except:
                                            pass
                    except:
                        pass
        except:
            pass
        await asyncio.sleep(1800)

async def rotate_status():
    await client.wait_until_ready()
    i = 0
    while not client.is_closed():
        try:
            lines, _, _ = get_github_file(GITHUB_FILE)
            count = len([l for l in lines if not l.startswith("--")])
            statuses = [f"👑 {count} users whitelisted", f"🔑 {BRAND_NAME}", "🛡️ Protecting Scripts"]
            await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=statuses[i % len(statuses)]))
            i += 1
        except:
            pass
        await asyncio.sleep(30)

# =============================================
#   MODALS
# =============================================
class AddUserModal(discord.ui.Modal, title="➕ Add User"):
    username = discord.ui.TextInput(label="Roblox Username", required=True)
    discord_user = discord.ui.TextInput(label="Discord Username (e.g. yez.v)", required=False)
    days_input = discord.ui.TextInput(label="Days access (empty = permanent)", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        uid, rname = get_roblox_user_by_username(self.username.value.strip())
        if not uid:
            await interaction.followup.send(embed=make_embed("❌ Roblox User Not Found", color_key="error"), ephemeral=True)
            return
        lines, sha, content = get_github_file(GITHUB_FILE)
        if uid in get_ids_only(lines):
            await interaction.followup.send(embed=make_embed("⚠️ Already Whitelisted", color_key="warning"), ephemeral=True)
            return
        expiry = "never"
        if self.days_input.value.strip():
            try:
                expiry = (datetime.utcnow() + timedelta(days=int(self.days_input.value.strip()))).strftime("%Y-%m-%d %H:%M")
            except:
                pass
        discord_id = "none"
        discord_display = "none"
        if self.discord_user.value.strip():
            uname = self.discord_user.value.strip().lower().replace("@", "")
            for m in interaction.guild.members:
                if m.name.lower() == uname or m.display_name.lower() == uname:
                    discord_id = str(m.id)
                    discord_display = m.name
                    break
        script_key = generate_script_key(uid, discord_id)
        new_entry = f"{uid} | {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} | {rname} | {discord_id} | none | {expiry} | 0 | none | {script_key}"
        update_github_file(GITHUB_FILE, content.strip() + f"\n{new_entry}", sha)
        if discord_id != "none":
            await give_whitelist_role(interaction.guild, discord_id)
        e = make_embed("✅ User Added", color_key="success")
        e.add_field(name="Roblox", value=rname, inline=True)
        e.add_field(name="Discord", value=discord_display, inline=True)
        e.add_field(name="Expires", value=get_expiry_display(expiry), inline=True)
        e.add_field(name="Script Key", value=f"`{script_key}`", inline=False)
        await interaction.followup.send(embed=e, ephemeral=True)
        await send_log(e)

class RemoveUserModal(discord.ui.Modal, title="➖ Remove User"):
    username = discord.ui.TextInput(label="Roblox Username", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        uid, rname = get_roblox_user_by_username(self.username.value.strip())
        if not uid:
            await interaction.followup.send(embed=make_embed("❌ User Not Found", color_key="error"), ephemeral=True)
            return
        lines, sha, _ = get_github_file(GITHUB_FILE)
        found = next((l for l in lines if l.startswith(uid)), None)
        if not found:
            await interaction.followup.send(embed=make_embed("❌ Not Whitelisted", color_key="error"), ephemeral=True)
            return
        _, _, _, discord_str, _, _, _, _, _ = parse_entry(found)
        update_github_file(GITHUB_FILE, "\n".join([l for l in lines if not l.startswith(uid)]), sha)
        if discord_str and discord_str != "none":
            await remove_whitelist_role(interaction.guild, discord_str)
            try:
                m = interaction.guild.get_member(int(discord_str))
                if m:
                    await m.send(embed=make_embed("❌ Whitelist Removed", "Your access has been removed.", "error"))
            except:
                pass
        e = make_embed("🗑️ User Removed", f"**{rname}** removed.", "ban")
        await interaction.followup.send(embed=e, ephemeral=True)
        await send_log(e)

class BanUserModal(discord.ui.Modal, title="🔨 Ban User"):
    username = discord.ui.TextInput(label="Roblox Username", required=True)
    reason = discord.ui.TextInput(label="Reason", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        uid, rname = get_roblox_user_by_username(self.username.value.strip())
        if not uid:
            await interaction.followup.send(embed=make_embed("❌ User Not Found", color_key="error"), ephemeral=True)
            return
        ban_lines, ban_sha, ban_content = get_github_file(BAN_FILE)
        if uid in get_ids_only(ban_lines):
            await interaction.followup.send(embed=make_embed("⚠️ Already Banned", color_key="warning"), ephemeral=True)
            return
        lines, sha, _ = get_github_file(GITHUB_FILE)
        found = next((l for l in lines if l.startswith(uid)), None)
        discord_str = None
        if found:
            _, _, _, discord_str, _, _, _, _, _ = parse_entry(found)
            update_github_file(GITHUB_FILE, "\n".join([l for l in lines if not l.startswith(uid)]), sha)
        reason = self.reason.value.strip() or "No reason"
        update_github_file(BAN_FILE, ban_content.strip() + f"\n{uid} | {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} | {rname} | {reason}", ban_sha)
        if discord_str and discord_str != "none":
            await remove_whitelist_role(interaction.guild, discord_str)
            try:
                m = interaction.guild.get_member(int(discord_str))
                if m:
                    await m.send(embed=make_embed("🔨 You have been Banned", f"**Reason:** {reason}", "error"))
            except:
                pass
        e = make_embed("🔨 User Banned", f"**{rname}** banned.\n**Reason:** {reason}", "error")
        await interaction.followup.send(embed=e, ephemeral=True)
        await send_log(e)

class UnbanUserModal(discord.ui.Modal, title="✅ Unban User"):
    username = discord.ui.TextInput(label="Roblox Username", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        uid, rname = get_roblox_user_by_username(self.username.value.strip())
        if not uid:
            await interaction.followup.send(embed=make_embed("❌ User Not Found", color_key="error"), ephemeral=True)
            return
        ban_lines, ban_sha, _ = get_github_file(BAN_FILE)
        if uid not in get_ids_only(ban_lines):
            await interaction.followup.send(embed=make_embed("❌ Not Banned", color_key="error"), ephemeral=True)
            return
        update_github_file(BAN_FILE, "\n".join([l for l in ban_lines if not l.startswith(uid)]), ban_sha)
        e = make_embed("✅ User Unbanned", f"**{rname}** has been unbanned.", "success")
        await interaction.followup.send(embed=e, ephemeral=True)
        await send_log(e)

class ExtendExpiryModal(discord.ui.Modal, title="📅 Extend Expiry"):
    username = discord.ui.TextInput(label="Roblox Username", required=True)
    days_input = discord.ui.TextInput(label="Days to add", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        uid, rname = get_roblox_user_by_username(self.username.value.strip())
        if not uid:
            await interaction.followup.send(embed=make_embed("❌ User Not Found", color_key="error"), ephemeral=True)
            return
        lines, sha, _ = get_github_file(GITHUB_FILE)
        found = next((l for l in lines if l.startswith(uid)), None)
        if not found:
            await interaction.followup.send(embed=make_embed("❌ Not Whitelisted", color_key="error"), ephemeral=True)
            return
        try:
            days = int(self.days_input.value.strip())
        except:
            await interaction.followup.send(embed=make_embed("❌ Invalid days", color_key="error"), ephemeral=True)
            return
        e_uid, e_date, e_rname, e_dstr, e_note, e_expiry, e_uses, e_hwid, e_skey = parse_entry(found)
        if e_expiry and e_expiry != "never":
            try:
                base = datetime.strptime(e_expiry, "%Y-%m-%d %H:%M")
                if base < datetime.utcnow():
                    base = datetime.utcnow()
            except:
                base = datetime.utcnow()
        else:
            base = datetime.utcnow()
        new_expiry = (base + timedelta(days=days)).strftime("%Y-%m-%d %H:%M")
        new_lines = [f"{e_uid} | {e_date} | {e_rname} | {e_dstr or 'none'} | {e_note or 'none'} | {new_expiry} | {e_uses} | {e_hwid or 'none'} | {e_skey or 'none'}" if l.startswith(uid) else l for l in lines]
        update_github_file(GITHUB_FILE, "\n".join(new_lines), sha)
        e = make_embed("📅 Expiry Extended", f"**{e_rname}** +{days} days\n**New expiry:** {new_expiry}", "success")
        await interaction.followup.send(embed=e, ephemeral=True)
        await send_log(e)

class AnnounceModal(discord.ui.Modal, title="📢 Announce to All Users"):
    title_input = discord.ui.TextInput(label="Title", required=True)
    message_input = discord.ui.TextInput(label="Message", style=discord.TextStyle.paragraph, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        lines, _, _ = get_github_file(GITHUB_FILE)
        sent = 0
        failed = 0
        for line in lines:
            _, _, roblox_name, discord_str, _, _, _, _, _ = parse_entry(line)
            if discord_str and discord_str != "none":
                try:
                    m = interaction.guild.get_member(int(discord_str))
                    if m:
                        dm = discord.Embed(title=f"📢 {self.title_input.value}", description=self.message_input.value, color=BRAND_COLOR)
                        dm.set_footer(text=f"{BRAND_NAME} Announcement")
                        dm.timestamp = datetime.utcnow()
                        await m.send(embed=dm)
                        sent += 1
                except:
                    failed += 1
        await interaction.followup.send(embed=make_embed("📢 Done", f"✅ Sent: **{sent}**\n❌ Failed: **{failed}**", "success"), ephemeral=True)

class ResellerModal(discord.ui.Modal, title="👥 Add Reseller"):
    username = discord.ui.TextInput(label="Discord Username", placeholder="e.g. yez.v (no @)", required=True)
    keys_count = discord.ui.TextInput(label="Number of keys to give", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            count = int(self.keys_count.value.strip())
        except:
            await interaction.followup.send(embed=make_embed("❌ Invalid number", color_key="error"), ephemeral=True)
            return
        uname = self.username.value.strip().lower().replace("@", "")
        member = None
        for m in interaction.guild.members:
            if m.name.lower() == uname or m.display_name.lower() == uname:
                member = m
                break
        if not member:
            await interaction.followup.send(embed=make_embed("❌ User Not Found", color_key="error"), ephemeral=True)
            return
        current = get_reseller_keys_left(member.id)
        set_reseller_keys(member.id, current + count)
        await interaction.followup.send(embed=make_embed("✅ Reseller Updated", f"{member.mention} now has **{current + count}** keys.", "success"), ephemeral=True)
        try:
            await member.send(embed=make_embed("🔑 You are a Reseller!", f"You have **{count}** keys. Use `/adminpanel` to generate.", "gold"))
        except:
            pass

class ExtendExpiryModal2(discord.ui.Modal, title="📅 Extend Expiry"):
    username = discord.ui.TextInput(label="Roblox Username", required=True)
    days_input = discord.ui.TextInput(label="Days to add", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        uid, rname = get_roblox_user_by_username(self.username.value.strip())
        if not uid:
            await interaction.followup.send(embed=make_embed("❌ User Not Found", color_key="error"), ephemeral=True)
            return
        lines, sha, _ = get_github_file(GITHUB_FILE)
        found = next((l for l in lines if l.startswith(uid)), None)
        if not found:
            await interaction.followup.send(embed=make_embed("❌ Not Whitelisted", color_key="error"), ephemeral=True)
            return
        try:
            days = int(self.days_input.value.strip())
        except:
            await interaction.followup.send(embed=make_embed("❌ Invalid days", color_key="error"), ephemeral=True)
            return
        e_uid, e_date, e_rname, e_dstr, e_note, e_expiry, e_uses, e_hwid, e_skey = parse_entry(found)
        base = datetime.utcnow()
        if e_expiry and e_expiry != "never":
            try:
                b = datetime.strptime(e_expiry, "%Y-%m-%d %H:%M")
                if b > base:
                    base = b
            except:
                pass
        new_expiry = (base + timedelta(days=days)).strftime("%Y-%m-%d %H:%M")
        new_lines = [f"{e_uid} | {e_date} | {e_rname} | {e_dstr or 'none'} | {e_note or 'none'} | {new_expiry} | {e_uses} | {e_hwid or 'none'} | {e_skey or 'none'}" if l.startswith(uid) else l for l in lines]
        update_github_file(GITHUB_FILE, "\n".join(new_lines), sha)
        e = make_embed("📅 Expiry Extended", f"**{e_rname}** +{days} days → **{new_expiry}**", "success")
        await interaction.followup.send(embed=e, ephemeral=True)
        await send_log(e)

class AddAltAdminModal(discord.ui.Modal, title="➕ Add Alt Account"):
    discord_username = discord.ui.TextInput(label="Discord Username", placeholder="e.g. yez.v (no @)", required=True)
    roblox_username = discord.ui.TextInput(label="Alt Roblox Username", placeholder="The alt Roblox account", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        uname = self.discord_username.value.strip().lower().replace("@", "")
        member = None
        for m in interaction.guild.members:
            if m.name.lower() == uname or m.display_name.lower() == uname:
                member = m
                break
        if not member:
            await interaction.followup.send(embed=make_embed("❌ Discord User Not Found", color_key="error"), ephemeral=True)
            return
        lines, sha, content = get_github_file(GITHUB_FILE)
        main_entry = None
        for line in lines:
            uid, date, rname, dstr, note, expiry, uses, hwid, sk = parse_entry(line)
            if dstr and dstr == str(member.id):
                main_entry = (uid, date, rname, dstr, note, expiry, uses, hwid, sk)
                break
        if not main_entry:
            await interaction.followup.send(embed=make_embed("❌ User Not Whitelisted", color_key="error"), ephemeral=True)
            return
        main_uid, main_date, main_rname, main_dstr, main_note, main_expiry, main_uses, main_hwid, main_sk = main_entry
        alt_id, alt_name = get_roblox_user_by_username(self.roblox_username.value.strip())
        if not alt_id:
            await interaction.followup.send(embed=make_embed("❌ Roblox User Not Found", color_key="error"), ephemeral=True)
            return
        if alt_id in get_ids_only(lines):
            await interaction.followup.send(embed=make_embed("⚠️ Alt Already Whitelisted", color_key="warning"), ephemeral=True)
            return
        alt_script_key = generate_script_key(alt_id, str(member.id))
        date = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        new_entry = f"{alt_id} | {date} | {alt_name} | {member.id} | ALT of {main_rname} | {main_expiry} | 0 | none | {alt_script_key}"
        update_github_file(GITHUB_FILE, content.strip() + f"\n{new_entry}", sha)
        e = make_embed("✅ Alt Added!", f"**{alt_name}** added for **{main_rname}**\nExpires: {get_expiry_display(main_expiry)}", "success")
        await interaction.followup.send(embed=e, ephemeral=True)
        await send_log(e)
        try:
            await member.send(embed=make_embed("➕ Alt Added", f"**{alt_name}** added to your whitelist!\nExpires: {get_expiry_display(main_expiry)}", "success"))
        except:
            pass

class SearchUserModal(discord.ui.Modal, title="🔍 Search User"):
    query = discord.ui.TextInput(label="Roblox or Discord username", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        q = self.query.value.strip().lower()
        lines, _, _ = get_github_file(GITHUB_FILE)
        results = []
        for line in lines:
            if line.startswith("--"):
                continue
            uid, date, rname, dstr, note, expiry, uses, hwid, sk = parse_entry(line)
            if (rname and q in rname.lower()) or (dstr and q in dstr.lower()):
                results.append((uid, date, rname, dstr, note, expiry, uses, hwid, sk))
        if not results:
            await interaction.followup.send(embed=make_embed("🔍 No Results", f"No user found matching **{q}**", "warning"), ephemeral=True)
            return
        embeds = []
        for uid, date, rname, dstr, note, expiry, uses, hwid, sk in results:
            expired = is_expired(expiry)
            e = discord.Embed(color=COLORS["error"] if expired else COLORS["success"])
            e.title = f"{rname or uid}"
            dmention = f"<@{dstr}>" if dstr and dstr != "none" else "No Discord"
            e.description = (
                f"**Discord:** {dmention}\n"
                f"**Status:** {'⚠️ Expired' if expired else '✅ Active'}\n"
                f"**Expires:** {get_expiry_display(expiry)}\n"
                f"**HWID:** {'🔒 Locked' if hwid and hwid != 'none' else '🔓 Unlocked'}\n"
                f"**Script Key:** `{sk or 'none'}`\n"
                f"**Added:** {date}"
            )
            avatar = get_roblox_avatar(uid)
            if avatar:
                e.set_thumbnail(url=avatar)
            e.set_footer(text=f"{BRAND_NAME}")
            embeds.append(e)
        await interaction.followup.send(embeds=embeds[:10], ephemeral=True)

class SetChannelModal(discord.ui.Modal, title="📌 Set Channel"):
    channel_id = discord.ui.TextInput(label="Channel ID", placeholder="Right click channel → Copy ID", required=True)
    channel_type = discord.ui.TextInput(label="Type: purchase / vouch / log", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            cid = int(self.channel_id.value.strip())
            ctype = self.channel_type.value.strip().lower()
            valid = ["purchase", "vouch", "log"]
            if ctype not in valid:
                await interaction.response.send_message(embed=make_embed(f"❌ Use: {', '.join(valid)}", color_key="error"), ephemeral=True)
                return
            key = "log_channel" if ctype == "log" else f"{ctype}_channel"
            set_setting(key, cid)
            await interaction.response.send_message(embed=make_embed(f"✅ {ctype.capitalize()} Channel Set!", color_key="success"), ephemeral=True)
        except:
            await interaction.response.send_message(embed=make_embed("❌ Invalid Channel ID", color_key="error"), ephemeral=True)

class DMKeyModal(discord.ui.Modal, title="📤 DM Key to User"):
    discord_username = discord.ui.TextInput(label="Discord Username", placeholder="e.g. yez.v (no @)", required=True)
    days_input = discord.ui.TextInput(label="Days access (empty = permanent)", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        if not owner_or_reseller(interaction):
            await interaction.response.send_message("🚫", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        uname = self.discord_username.value.strip().lower().replace("@", "")
        member = None
        for m in interaction.guild.members:
            if m.name.lower() == uname or m.display_name.lower() == uname:
                member = m
                break
        if not member:
            await interaction.followup.send(embed=make_embed("❌ User Not Found", f"Could not find **{uname}**", "error"), ephemeral=True)
            return
        total_hours = None
        if self.days_input.value.strip():
            try:
                total_hours = int(self.days_input.value.strip()) * 24
            except:
                pass
        key = generate_key("SEMI")
        expiry = "never"
        if total_hours:
            expiry = (datetime.utcnow() + timedelta(hours=total_hours)).strftime("%Y-%m-%d %H:%M")
        kl, ks, kc = get_github_file(KEY_FILE)
        update_github_file(KEY_FILE, kc.strip() + f"\n{key} | {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} | false | 1 | {expiry} | never | normal", ks)
        dm_sent = False
        try:
            dm_channel = await member.create_dm()
            dm = discord.Embed(title=f"🔑 Your {BRAND_NAME} Key", color=BRAND_COLOR)
            dm.description = (
                f"Hey **{member.display_name}**!\n\n"
                f"Here is your key:\n"
                f"```\n{key}\n```\n"
                f"**How to use:**\n"
                f"1️⃣ Go to the panel\n"
                f"2️⃣ Click **Redeem Key**\n"
                f"3️⃣ Enter this key + your Roblox username\n\n"
                f"**Expires:** {expiry if expiry != 'never' else 'Never (Permanent)'}\n"
                f"⚠️ Single use only!"
            )
            dm.set_footer(text=f"{BRAND_NAME}")
            dm.timestamp = datetime.utcnow()
            await dm_channel.send(embed=dm)
            dm_sent = True
        except Exception as e:
            print(f"DM error: {e}")
        if dm_sent:
            await interaction.followup.send(embed=make_embed("✅ Key Sent!", f"Key sent to **{member.display_name}** via DM.\nKey: `{key}`", "success"), ephemeral=True)
        else:
            await interaction.followup.send(embed=make_embed("⚠️ DM Failed", f"DMs disabled.\nKey: ```{key}```", "warning"), ephemeral=True)

class QuickSellModal(discord.ui.Modal, title="💨 Quick Sell"):
    roblox_username = discord.ui.TextInput(label="Roblox Username", required=True)
    discord_username = discord.ui.TextInput(label="Discord Username (e.g. yez.v)", required=True)
    days_input = discord.ui.TextInput(label="Days (empty = permanent)", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        if not owner_or_reseller(interaction):
            await interaction.response.send_message("🚫", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        user_id, roblox_name = get_roblox_user_by_username(self.roblox_username.value.strip())
        if not user_id:
            await interaction.followup.send(embed=make_embed("❌ Roblox User Not Found", color_key="error"), ephemeral=True)
            return
        uname = self.discord_username.value.strip().lower().replace("@", "")
        member = None
        for m in interaction.guild.members:
            if m.name.lower() == uname or m.display_name.lower() == uname:
                member = m
                break
        if not member:
            await interaction.followup.send(embed=make_embed("❌ Discord User Not Found", color_key="error"), ephemeral=True)
            return
        lines, sha, content = get_github_file(GITHUB_FILE)
        if user_id in get_ids_only(lines):
            await interaction.followup.send(embed=make_embed("⚠️ Already Whitelisted", color_key="warning"), ephemeral=True)
            return
        expiry = "never"
        if self.days_input.value.strip():
            try:
                expiry = (datetime.utcnow() + timedelta(days=int(self.days_input.value.strip()))).strftime("%Y-%m-%d %H:%M")
            except:
                pass
        script_key = generate_script_key(user_id, str(member.id))
        date = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        new_entry = f"{user_id} | {date} | {roblox_name} | {member.id} | QuickSell | {expiry} | 0 | none | {script_key}"
        update_github_file(GITHUB_FILE, content.strip() + f"\n{new_entry}", sha)
        await give_whitelist_role(interaction.guild, str(member.id))
        avatar = get_roblox_avatar(user_id)
        try:
            dm = make_embed(f"✅ Welcome to {BRAND_NAME}!", f"Hey **{roblox_name}**! You have been whitelisted!\n\n1️⃣ Go to the panel\n2️⃣ Click **Get Script**\n3️⃣ Run in your executor", "success")
            dm.add_field(name="Expires", value=get_expiry_display(expiry), inline=True)
            await member.send(embed=dm)
        except:
            pass
        e = make_embed("💨 Quick Sell Done!", color_key="success")
        e.add_field(name="Roblox", value=roblox_name, inline=True)
        e.add_field(name="Discord", value=member.mention, inline=True)
        e.add_field(name="Expires", value=get_expiry_display(expiry), inline=True)
        if avatar:
            e.set_thumbnail(url=avatar)
        await interaction.followup.send(embed=e, ephemeral=True)
        await send_log(e)

class CustomKeyModal(discord.ui.Modal, title="⏱️ Custom Key Duration"):
    days_input = discord.ui.TextInput(label="Days", placeholder="e.g. 30", required=False)
    hours_input = discord.ui.TextInput(label="Hours", placeholder="e.g. 12", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        if not owner_or_reseller(interaction):
            await interaction.response.send_message("🚫", ephemeral=True)
            return
        total_hours = 0
        try:
            if self.days_input.value.strip():
                total_hours += int(self.days_input.value.strip()) * 24
            if self.hours_input.value.strip():
                total_hours += int(self.hours_input.value.strip())
        except:
            await interaction.response.send_message(embed=make_embed("❌ Invalid input", color_key="error"), ephemeral=True)
            return
        if total_hours <= 0:
            await interaction.response.send_message(embed=make_embed("❌ Enter days or hours", color_key="error"), ephemeral=True)
            return
        key = generate_key("SEMI")
        expiry = (datetime.utcnow() + timedelta(hours=total_hours)).strftime("%Y-%m-%d %H:%M")
        kl, ks, kc = get_github_file(KEY_FILE)
        update_github_file(KEY_FILE, kc.strip() + f"\n{key} | {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} | false | 1 | {expiry} | never | normal", ks)
        try:
            dm = make_embed("🔑 Custom Key Generated", color_key="gold")
            dm.add_field(name="Key", value=f"`{key}`", inline=False)
            dm.add_field(name="Duration", value=f"{total_hours}h", inline=True)
            dm.add_field(name="Expires", value=expiry, inline=True)
            await interaction.user.send(embed=dm)
            await interaction.response.send_message(embed=make_embed("✅ Key Sent to DMs!", color_key="success"), ephemeral=True)
        except:
            await interaction.response.send_message(embed=make_embed("❌ DM Failed", color_key="error"), ephemeral=True)

# =============================================
#   VIEWS
# =============================================
class HWIDResetView(discord.ui.View):
    def __init__(self, entries):
        super().__init__(timeout=60)
        for i, (uid, rname, dstr) in enumerate(entries[:10]):
            btn = discord.ui.Button(label=f"{rname[:20]}", style=discord.ButtonStyle.grey, row=i // 3)
            btn.callback = self.make_callback(uid, rname, dstr)
            self.add_item(btn)

    def make_callback(self, uid, rname, dstr):
        async def callback(interaction: discord.Interaction):
            if not owner_only(interaction):
                await interaction.response.send_message("🚫", ephemeral=True)
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
            if dstr and dstr != "none":
                rl, rs, _ = get_github_file(HWID_RESET_FILE)
                update_github_file(HWID_RESET_FILE, "\n".join([l for l in rl if not l.startswith(str(dstr))]), rs)
            await interaction.response.edit_message(embed=make_embed("🔄 HWID Reset", f"**{rname}**'s HWID has been reset.", "success"), view=None)
        return callback

class ConfirmClearView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=30)

    @discord.ui.button(label="✅ Yes, Clear All", style=discord.ButtonStyle.red)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not owner_only(interaction):
            await interaction.response.send_message("🚫", ephemeral=True)
            return
        _, sha, _ = get_github_file(GITHUB_FILE)
        update_github_file(GITHUB_FILE, "", sha)
        await interaction.response.edit_message(embed=make_embed("🗑️ Whitelist Cleared", "All users have been removed.", "error"), view=None)
        log = make_embed("🗑️ Whitelist Cleared", f"{interaction.user.mention} cleared the entire whitelist.", "error")
        await send_log(log)

    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.grey)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=make_embed("❌ Cancelled", "Whitelist was not cleared.", "info"), view=None)

class GenerateKeyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="♾️ Permanent", style=discord.ButtonStyle.grey, row=0)
    async def key_perm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._generate(interaction, hours=None, label="Permanent")

    @discord.ui.button(label="⏱️ Custom", style=discord.ButtonStyle.grey, row=0)
    async def key_custom(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CustomKeyModal())
        self.stop()

    @discord.ui.button(label="📤 DM to User", style=discord.ButtonStyle.grey, row=1)
    async def dm_key_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(DMKeyModal())
        self.stop()

    @discord.ui.button(label="💨 Quick Sell", style=discord.ButtonStyle.grey, row=1)
    async def quick_sell_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(QuickSellModal())
        self.stop()

    @discord.ui.button(label="📋 Unused Keys", style=discord.ButtonStyle.grey, row=2)
    async def saved_keys_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not owner_or_reseller(interaction):
            await interaction.response.send_message("🚫", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        kl, _, _ = get_github_file(KEY_FILE)
        unused = [(parse_key(l)[0], parse_key(l)[4]) for l in kl if parse_key(l)[2] == "false" and not is_expired(parse_key(l)[4])]
        if not unused:
            await interaction.followup.send(embed=make_embed("📋 No Unused Keys", "All keys have been redeemed.", "info"), ephemeral=True)
            return
        desc = f"**{len(unused)} unused keys:**\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        for k, exp in unused:
            desc += f"`{k}` — {get_expiry_display(exp)}\n"
        desc += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        await interaction.followup.send(embed=make_embed(f"📋 Unused Keys ({len(unused)})", desc, "gold"), ephemeral=True)

    async def _generate(self, interaction: discord.Interaction, hours, label):
        if not owner_or_reseller(interaction):
            await interaction.response.send_message("🚫", ephemeral=True)
            return
        if is_reseller(interaction.user.id) and not owner_only(interaction):
            kl = get_reseller_keys_left(interaction.user.id)
            if kl <= 0:
                await interaction.response.edit_message(embed=make_embed("❌ No Keys Left", color_key="error"), view=None)
                return
            set_reseller_keys(interaction.user.id, kl - 1)
        key = generate_key("SEMI")
        expiry = "never"
        if hours:
            expiry = (datetime.utcnow() + timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M")
        kl, ks, kc = get_github_file(KEY_FILE)
        update_github_file(KEY_FILE, kc.strip() + f"\n{key} | {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} | false | 1 | {expiry} | never | normal", ks)
        try:
            dm = make_embed("🔑 New Key Generated", color_key="gold")
            dm.add_field(name="Key", value=f"`{key}`", inline=False)
            dm.add_field(name="Duration", value=label, inline=True)
            dm.add_field(name="Expires", value=expiry if expiry != "never" else "Never", inline=True)
            dm.set_footer(text="⚠️ Single use only!")
            await interaction.user.send(embed=dm)
            await interaction.response.edit_message(embed=make_embed("✅ Key Sent to DMs!", f"**{label}** key sent!", "success"), view=None)
        except:
            await interaction.response.edit_message(embed=make_embed("❌ DM Failed", color_key="error"), view=None)
        self.stop()

class AdminPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    # ROW 0 — User management
    @discord.ui.button(label="Add", style=discord.ButtonStyle.grey, row=0)
    async def add_btn(self, i, b):
        if not owner_only(i): await i.response.send_message("🚫", ephemeral=True); return
        await i.response.send_modal(AddUserModal())

    @discord.ui.button(label="Remove", style=discord.ButtonStyle.grey, row=0)
    async def remove_btn(self, i, b):
        if not owner_only(i): await i.response.send_message("🚫", ephemeral=True); return
        await i.response.send_modal(RemoveUserModal())

    @discord.ui.button(label="Ban", style=discord.ButtonStyle.grey, row=0)
    async def ban_btn(self, i, b):
        if not owner_only(i): await i.response.send_message("🚫", ephemeral=True); return
        await i.response.send_modal(BanUserModal())

    # ROW 1 — More user actions
    @discord.ui.button(label="Unban", style=discord.ButtonStyle.grey, row=1)
    async def unban_btn(self, i, b):
        if not owner_only(i): await i.response.send_message("🚫", ephemeral=True); return
        await i.response.send_modal(UnbanUserModal())

    @discord.ui.button(label="+Days", style=discord.ButtonStyle.grey, row=1)
    async def extend_btn(self, i, b):
        if not owner_only(i): await i.response.send_message("🚫", ephemeral=True); return
        await i.response.send_modal(ExtendExpiryModal())

    @discord.ui.button(label="Add Alt", style=discord.ButtonStyle.grey, row=1)
    async def addalt_btn(self, i, b):
        if not owner_only(i): await i.response.send_message("🚫", ephemeral=True); return
        await i.response.send_modal(AddAltAdminModal())

    # ROW 2 — View data
    @discord.ui.button(label="List", style=discord.ButtonStyle.grey, row=2)
    async def list_btn(self, i, b):
        if not owner_only(i): await i.response.send_message("🚫", ephemeral=True); return
        await i.response.defer(ephemeral=True)
        lines, _, _ = get_github_file(GITHUB_FILE)
        ban_lines, _, _ = get_github_file(BAN_FILE)
        entries = [l for l in lines if not l.startswith("--")]
        ban_entries = [l for l in ban_lines if not l.startswith("--")]
        if not entries:
            await i.followup.send(embed=make_embed("📋 Whitelist Empty", color_key="info"), ephemeral=True)
            return
        embeds = []
        for line in entries:
            uid, date, rname, dstr, note, expiry, uses, hwid, sk = parse_entry(line)
            name = rname if rname else uid
            expired = is_expired(expiry)
            e = discord.Embed(color=COLORS["error"] if expired else COLORS["success"])
            e.title = name
            dmention = f"<@{dstr}>" if dstr and dstr != "none" else "No Discord"
            e.description = (
                f"**Discord:** {dmention}\n"
                f"**Status:** {'⚠️ Expired' if expired else '✅ Active'}\n"
                f"**Expires:** {get_expiry_display(expiry)}\n"
                f"**HWID:** {'🔒 Locked' if hwid and hwid != 'none' else '🔓 Unlocked'}\n"
                f"**Script Key:** `{sk or 'none'}`"
            )
            avatar = get_roblox_avatar(uid)
            if avatar:
                e.set_thumbnail(url=avatar)
            e.set_footer(text=f"{BRAND_NAME} • {len(entries)} total • {len(ban_entries)} banned")
            embeds.append(e)
        for chunk in [embeds[x:x+10] for x in range(0, len(embeds), 10)]:
            await i.followup.send(embeds=chunk, ephemeral=True)

    @discord.ui.button(label="Search", style=discord.ButtonStyle.grey, row=2)
    async def search_btn(self, i, b):
        if not owner_only(i): await i.response.send_message("🚫", ephemeral=True); return
        await i.response.send_modal(SearchUserModal())

    @discord.ui.button(label="Banned", style=discord.ButtonStyle.grey, row=2)
    async def banlist_btn(self, i, b):
        if not owner_only(i): await i.response.send_message("🚫", ephemeral=True); return
        await i.response.defer(ephemeral=True)
        ban_lines, _, _ = get_github_file(BAN_FILE)
        entries = [l for l in ban_lines if not l.startswith("--")]
        embed = make_embed("Banned Users", color_key="ban")
        if not entries:
            embed.description = "No banned users."
        else:
            desc = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            for line in entries:
                parts = [p.strip() for p in line.split("|")]
                rname = parts[2] if len(parts) > 2 else parts[0]
                reason = parts[3] if len(parts) > 3 else "No reason"
                desc += f"**{rname}** — {reason}\n"
            desc += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            embed.description = desc
        embed.add_field(name="Total", value=str(len(entries)), inline=True)
        await i.followup.send(embed=embed, ephemeral=True)

    # ROW 3 — Keys and HWID
    @discord.ui.button(label="Gen Key", style=discord.ButtonStyle.grey, row=3)
    async def genkey_btn(self, i, b):
        if not owner_or_reseller(i): await i.response.send_message("🚫", ephemeral=True); return
        await i.response.send_message(embed=make_embed("Generate Key", "Select an option:", "gold"), view=GenerateKeyView(), ephemeral=True)

    @discord.ui.button(label="Stock", style=discord.ButtonStyle.grey, row=3)
    async def stock_btn(self, i, b):
        if not owner_only(i): await i.response.send_message("🚫", ephemeral=True); return
        await i.response.defer(ephemeral=True)
        kl, _, _ = get_github_file(KEY_FILE)
        unused = [l for l in kl if parse_key(l)[2] == "false" and not is_expired(parse_key(l)[4])]
        used = [l for l in kl if parse_key(l)[2] == "true"]
        embed = make_embed(f"Stock — {len(unused)} available", color_key="gold")
        desc = f"✅ **Available:** {len(unused)}\n❌ **Used:** {len(used)}\n📊 **Total:** {len(kl)}\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        for line in unused:
            k, date, _, _, expiry, _, _ = parse_key(line)
            desc += f"`{k}` — {get_expiry_display(expiry)}\n"
        embed.description = desc
        await i.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(label="HWID", style=discord.ButtonStyle.grey, row=3)
    async def hwid_btn(self, i, b):
        if not owner_only(i): await i.response.send_message("🚫", ephemeral=True); return
        await i.response.defer(ephemeral=True)
        lines, _, _ = get_github_file(GITHUB_FILE)
        entries = []
        for l in lines:
            if not l.startswith("--"):
                e = parse_entry(l)
                if e[7] and e[7] != "none":
                    entries.append((e[0], e[2] or e[0], e[3] or "none"))
        if not entries:
            await i.followup.send(embed=make_embed("No HWID locked users", color_key="info"), ephemeral=True)
            return
        await i.followup.send(embed=make_embed("HWID Reset Panel", "Tap a user to force reset their HWID.", "gold"), view=HWIDResetView(entries), ephemeral=True)

    # ROW 4 — Admin tools
    @discord.ui.button(label="DM All", style=discord.ButtonStyle.grey, row=4)
    async def announce_btn(self, i, b):
        if not owner_only(i): await i.response.send_message("🚫", ephemeral=True); return
        await i.response.send_modal(AnnounceModal())

    @discord.ui.button(label="Resellers", style=discord.ButtonStyle.grey, row=4)
    async def resellers_btn(self, i, b):
        if not owner_only(i): await i.response.send_message("🚫", ephemeral=True); return
        await i.response.send_modal(ResellerModal())

    @discord.ui.button(label="Channels", style=discord.ButtonStyle.grey, row=4)
    async def channels_btn(self, i, b):
        if not owner_only(i): await i.response.send_message("🚫", ephemeral=True); return
        await i.response.send_modal(SetChannelModal())

    @discord.ui.button(label="Clear All", style=discord.ButtonStyle.grey, row=4)
    async def clear_btn(self, i, b):
        if not owner_only(i): await i.response.send_message("🚫", ephemeral=True); return
        await i.response.send_message(embed=make_embed("⚠️ Are you sure?", "This will **delete every user** from the whitelist. This cannot be undone!", "warning"), view=ConfirmClearView(), ephemeral=True)

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
            uid, date, rname, dstr, note, expiry, uses, hwid, sk = parse_entry(line)
            if dstr and dstr == str(interaction.user.id):
                user_entry = (uid, date, rname, dstr, note, expiry, uses, hwid, sk)
                break
        if not user_entry:
            await interaction.response.send_message(embed=make_embed("❌ Not Whitelisted", "Redeem a key first.", "error"), ephemeral=True)
            return
        uid, date, rname, dstr, note, expiry, uses, hwid, sk = user_entry
        if is_expired(expiry):
            await interaction.response.send_message(embed=make_embed("⚠️ Access Expired", "Contact the owner to renew.", "warning"), ephemeral=True)
            return
        _, _, script_content = get_github_file(SCRIPT_FILE)
        if not script_content:
            await interaction.response.send_message(embed=make_embed("❌ No Script Set", "Contact the owner.", "error"), ephemeral=True)
            return
        script_key = sk if sk and sk != "none" else generate_script_key(uid, dstr)
        embed = discord.Embed(color=COLORS["success"])
        embed.title = f"📜 {BRAND_NAME} — Your Script"
        embed.description = (
            f"**Your Script Key:**\n"
            f"```\n{script_key}\n```\n"
            f"**Loadstring:**\n"
            f"```lua\n{script_content[:1400]}\n```"
        )
        embed.set_footer(text=f"Only you can see this • {rname}")
        embed.timestamp = datetime.utcnow()
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="👤 Get Role", style=discord.ButtonStyle.blurple, custom_id="panel_role", row=0)
    async def get_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        role_id = get_setting("whitelist_role")
        if not role_id:
            await interaction.response.send_message(embed=make_embed("❌ No Role Set", "Owner needs to run /setrole first.", "error"), ephemeral=True)
            return
        lines, _, _ = get_github_file(GITHUB_FILE)
        user_entry = None
        for line in lines:
            uid, date, rname, dstr, note, expiry, uses, hwid, sk = parse_entry(line)
            if dstr and dstr == str(interaction.user.id):
                user_entry = (uid, date, rname, dstr, note, expiry, uses, hwid, sk)
                break
        if not user_entry:
            await interaction.response.send_message(embed=make_embed("❌ Not Whitelisted", color_key="error"), ephemeral=True)
            return
        _, _, rname, _, _, expiry, _, _, _ = user_entry
        if is_expired(expiry):
            await interaction.response.send_message(embed=make_embed("⚠️ Access Expired", color_key="warning"), ephemeral=True)
            return
        try:
            role = interaction.guild.get_role(int(role_id))
            if not role:
                await interaction.response.send_message(embed=make_embed("❌ Role Not Found", "Contact the owner.", "error"), ephemeral=True)
                return
            if role in interaction.user.roles:
                await interaction.response.send_message(embed=make_embed("✅ Already Have Role", f"You already have **{role.name}**!", "warning"), ephemeral=True)
                return
            await interaction.user.add_roles(role)
            await interaction.response.send_message(embed=make_embed("✅ Role Given", f"You now have **{role.name}**!", "success"), ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message(embed=make_embed("❌ Permission Error", "Bot role must be **above** the whitelist role in Server Settings!", "error"), ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(embed=make_embed("❌ Error", str(e), "error"), ephemeral=True)

    @discord.ui.button(label="🔄 Reset HWID", style=discord.ButtonStyle.grey, custom_id="panel_hwid", row=1)
    async def reset_hwid(self, interaction: discord.Interaction, button: discord.ui.Button):
        nxt = get_hwid_reset_time(interaction.user.id)
        if nxt:
            tl = nxt - datetime.utcnow()
            days_left = tl.days
            hours_left = tl.seconds // 3600
            await interaction.response.send_message(embed=make_embed("⏳ HWID Cooldown", f"Reset available in **{days_left}d {hours_left}h**.", "warning"), ephemeral=True)
            return
        lines, sha, content = get_github_file(GITHUB_FILE)
        new_lines = []
        found = False
        for line in lines:
            uid, date, rname, dstr, note, expiry, uses, hwid, sk = parse_entry(line)
            if dstr and dstr == str(interaction.user.id):
                found = True
                new_lines.append(f"{uid} | {date} | {rname} | {dstr} | {note or 'none'} | {expiry or 'never'} | {uses} | none | {sk or 'none'}")
            else:
                new_lines.append(line)
        if not found:
            await interaction.response.send_message(embed=make_embed("❌ Not Whitelisted", color_key="error"), ephemeral=True)
            return
        update_github_file(GITHUB_FILE, "\n".join(new_lines), sha)
        set_hwid_reset_time(interaction.user.id)
        await interaction.response.send_message(embed=make_embed("🔄 HWID Reset", "Done! Next reset available in **2 days**.", "success"), ephemeral=True)
        await send_log(make_embed("🔄 HWID Reset", f"{interaction.user.mention} reset their HWID.", "warning"))

    @discord.ui.button(label="📊 Stats", style=discord.ButtonStyle.grey, custom_id="panel_stats", row=1)
    async def get_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        lines, _, _ = get_github_file(GITHUB_FILE)
        for line in lines:
            uid, date, rname, dstr, note, expiry, uses, hwid, sk = parse_entry(line)
            if dstr and dstr == str(interaction.user.id):
                expired = is_expired(expiry)
                nxt = get_hwid_reset_time(interaction.user.id)
                if nxt:
                    tl = nxt - datetime.utcnow()
                    hwid_reset_text = f"In {tl.days}d {tl.seconds // 3600}h"
                else:
                    hwid_reset_text = "Available ✅"
                embed = discord.Embed(color=COLORS["warning"] if expired else COLORS["success"])
                embed.description = (
                    f"**{rname or uid}**\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"**Status:** {'⚠️ Expired' if expired else '✅ Active'}\n"
                    f"**Expires:** {get_expiry_display(expiry)}\n"
                    f"**HWID:** {'🔒 Locked' if hwid and hwid != 'none' else '🔓 Unlocked'}\n"
                    f"**HWID Reset:** {hwid_reset_text}\n"
                    f"**Added:** {date}"
                )
                embed.set_footer(text=f"{BRAND_NAME} Whitelist System")
                embed.timestamp = datetime.utcnow()
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
            k, date, used, mu, expiry, days, kt = parse_key(line)
            if k == key:
                found_key = line
                break
        if not found_key:
            attempts = track_failed_attempt(interaction.user.id)
            if attempts >= 5:
                try:
                    owner = await client.fetch_user(OWNER_ID)
                    alert = make_embed("🚨 Suspicious Activity!", f"**{interaction.user.mention}** failed key redemption **{attempts}** times!", "error")
                    alert.add_field(name="Discord ID", value=str(interaction.user.id), inline=True)
                    await owner.send(embed=alert)
                except:
                    pass
            await interaction.response.send_message(embed=make_embed("❌ Invalid Key", color_key="error"), ephemeral=True)
            return
        k, date, used, mu, expiry, days, kt = parse_key(found_key)
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
                expiry_date = (datetime.utcnow() + timedelta(days=int(days))).strftime("%Y-%m-%d %H:%M")
            except:
                pass
        script_key = generate_script_key(user_id, str(interaction.user.id))
        update_github_file(GITHUB_FILE, wl_content.strip() + f"\n{user_id} | {add_date} | {roblox_name} | {interaction.user.id} | Redeemed key | {expiry_date} | 0 | none | {script_key}", wl_sha)
        new_key_lines = [f"{k2} | {d2} | true | {m2} | {e2} | {dy2} | {kt2}" if parse_key(line)[0] == key else line for line in key_lines for k2, d2, _, m2, e2, dy2, kt2 in [parse_key(line)]]
        update_github_file(KEY_FILE, "\n".join(new_key_lines), key_sha)
        reset_failed_attempts(interaction.user.id)
        role_given = await give_whitelist_role(interaction.guild, str(interaction.user.id))
        avatar = get_roblox_avatar(user_id)
        embed = discord.Embed(
            title="✅ Key Redeemed!",
            description=(
                f"Welcome **{roblox_name}**!\n\n"
                f"Click **Get Script** to receive your script.\n"
                f"{'✅ Role given!' if role_given else '👤 Click Get Role for your role.'}"
            ),
            color=COLORS["success"]
        )
        embed.add_field(name="Roblox", value=roblox_name, inline=True)
        embed.add_field(name="Expires", value=get_expiry_display(expiry_date), inline=True)
        if avatar:
            embed.set_image(url=avatar)
        embed.set_footer(text=f"{BRAND_NAME} Whitelist System")
        embed.timestamp = datetime.utcnow()
        await interaction.response.send_message(embed=embed, ephemeral=True)
        try:
            vouch_cid = get_setting("vouch_channel")
            vouch_text = f"\n\n📣 Please leave a vouch in <#{vouch_cid}>!" if vouch_cid else ""
            welcome_dm = discord.Embed(title=f"👑 Welcome to {BRAND_NAME}!", color=BRAND_COLOR)
            welcome_dm.description = (
                f"Hey **{roblox_name}**! Key redeemed.\n\n"
                f"**How to use:**\n"
                f"1️⃣ Go to panel → Click **Get Script**\n"
                f"2️⃣ Copy the loadstring\n"
                f"3️⃣ Run it in your executor\n\n"
                f"**HWID:** Locks to your executor on first run.\n"
                f"Reset every **2 days** from the panel.{vouch_text}"
            )
            welcome_dm.add_field(name="Expires", value=get_expiry_display(expiry_date), inline=True)
            welcome_dm.set_footer(text=f"{BRAND_NAME}")
            welcome_dm.timestamp = datetime.utcnow()
            await interaction.user.send(embed=welcome_dm)
        except:
            pass
        await post_purchase(interaction.guild, roblox_name, interaction.user, expiry_date, avatar)
        log_embed = make_embed("🔑 Key Redeemed", f"**{roblox_name}** redeemed a key", "success")
        log_embed.add_field(name="Discord", value=interaction.user.mention, inline=True)
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
    print(f"Bot online: {client.user}")

@tree.command(name="panel", description="Send the whitelist panel")
async def panel_cmd(interaction: discord.Interaction):
    if not owner_only(interaction):
        await interaction.response.send_message(embed=make_embed("🚫 Access Denied", color_key="error"), ephemeral=True)
        return
    embed = discord.Embed(title=BRAND_NAME, color=BRAND_COLOR)
    embed.description = (
        f"This control panel is for the project: **{BRAND_NAME}**\n"
        f"If you're a buyer, click on the buttons below to redeem your key, "
        f"get the script or get your role."
    )
    embed.set_footer(text=f"Sent by {interaction.user.name} • {datetime.utcnow().strftime('%m/%d/%Y %I:%M %p')}")
    await interaction.response.send_message(embed=embed, view=PanelView())

@tree.command(name="adminpanel", description="Open the admin panel")
async def adminpanel_cmd(interaction: discord.Interaction):
    if not owner_only(interaction) and not is_reseller(interaction.user.id):
        await interaction.response.send_message(embed=make_embed("🚫 Access Denied", color_key="error"), ephemeral=True)
        return
    is_res = is_reseller(interaction.user.id) and not owner_only(interaction)
    kl_left = get_reseller_keys_left(interaction.user.id) if is_res else None
    lines, _, _ = get_github_file(GITHUB_FILE)
    ban_lines, _, _ = get_github_file(BAN_FILE)
    total = len([l for l in lines if not l.startswith("--")])
    banned = len([l for l in ban_lines if not l.startswith("--")])
    embed = discord.Embed(color=0x2B2D31)
    embed.title = f"⚙️ {BRAND_NAME} — Admin Panel"
    embed.description = (
        f"{'> 🔑 Reseller — **' + str(kl_left) + '** keys left\n' if is_res else ''}"
        f"```\nWhitelisted : {total}\nBanned      : {banned}\n```\n"
        f"**ROW 1** · Add · Remove · Ban\n"
        f"**ROW 2** · Unban · +Days · Add Alt\n"
        f"**ROW 3** · List · Search · Banned\n"
        f"**ROW 4** · Gen Key · Stock · HWID\n"
        f"**ROW 5** · DM All · Resellers · Channels · Clear All"
    )
    embed.set_footer(text="Only you can see this")
    embed.timestamp = datetime.utcnow()
    await interaction.response.send_message(embed=embed, view=AdminPanelView(), ephemeral=True)

@tree.command(name="setrole", description="Set the whitelist role")
@app_commands.describe(role="The whitelist role")
async def setrole_cmd(interaction: discord.Interaction, role: discord.Role):
    if not owner_only(interaction):
        await interaction.response.send_message(embed=make_embed("🚫 Access Denied", color_key="error"), ephemeral=True)
        return
    set_setting("whitelist_role", role.id)
    await interaction.response.send_message(embed=make_embed("✅ Role Set", f"Whitelisted users will receive **{role.name}**.\n\n⚠️ Make sure the bot role is **above** `{role.name}` in Server Settings → Roles!", "success"))

@tree.command(name="setscript", description="Set the script for whitelisted users")
@app_commands.describe(script="The loadstring or script")
async def setscript_cmd(interaction: discord.Interaction, script: str):
    if not owner_only(interaction):
        await interaction.response.send_message(embed=make_embed("🚫 Access Denied", color_key="error"), ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    _, sha, _ = get_github_file(SCRIPT_FILE)
    update_github_file(SCRIPT_FILE, script, sha)
    await interaction.followup.send(embed=make_embed("✅ Script Set", color_key="success"), ephemeral=True)

@tree.command(name="givetrial", description="Give a user free trial access (owner only)")
@app_commands.describe(user="The Discord user", hours="Hours", days="Days")
async def givetrial_cmd(interaction: discord.Interaction, user: discord.Member, hours: int = 0, days: int = 0):
    if not owner_only(interaction):
        await interaction.response.send_message(embed=make_embed("🚫 Access Denied", color_key="error"), ephemeral=True)
        return
    if hours == 0 and days == 0:
        await interaction.response.send_message(embed=make_embed("❌ Set a time", "Enter hours or days.", "error"), ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    total_hours = (days * 24) + hours
    lines, sha, content = get_github_file(GITHUB_FILE)
    for line in lines:
        uid, date, rname, dstr, note, expiry, uses, hwid, sk = parse_entry(line)
        if dstr and dstr == str(user.id):
            await interaction.followup.send(embed=make_embed("⚠️ Already Whitelisted", color_key="warning"), ephemeral=True)
            return
    expiry = (datetime.utcnow() + timedelta(hours=total_hours)).strftime("%Y-%m-%d %H:%M")
    script_key = generate_script_key("TRIAL", str(user.id))
    new_entry = f"TRIAL | {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} | {user.display_name} | {user.id} | Free Trial | {expiry} | 0 | none | {script_key}"
    update_github_file(GITHUB_FILE, content.strip() + f"\n{new_entry}", sha)
    await give_whitelist_role(interaction.guild, str(user.id))
    label = f"{days}d {hours}h".strip() if days else f"{hours}h"
    try:
        dm = discord.Embed(title=f"🧪 Free Trial — {label}", color=BRAND_COLOR)
        dm.description = f"Hey **{user.display_name}**!\n\nYou have **{label}** free trial access!\n\nGo to the panel → Click **Get Script**\n\n**Expires:** {expiry} UTC"
        dm.set_footer(text=f"{BRAND_NAME}")
        await user.send(embed=dm)
    except:
        pass
    embed = make_embed("✅ Trial Given", f"{user.mention} has **{label}** trial access.\nExpires: {expiry}", "success")
    await interaction.followup.send(embed=embed, ephemeral=True)
    await send_log(embed)

@tree.command(name="help", description="Show all commands")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(color=BRAND_COLOR)
    embed.title = f"📖 {BRAND_NAME} — Guide"

    embed.add_field(name="━━━ SLASH COMMANDS ━━━", value=(
        "`/panel`\n└ Post the user panel in channel\n\n"
        "`/adminpanel`\n└ Open your private control panel\n\n"
        "`/givetrial @user hours:2`\n└ Give someone free timed trial\n\n"
        "`/setrole`\n└ Set which role buyers receive\n\n"
        "`/setscript`\n└ Set the script buyers get\n\n"
        "`/help`\n└ Show this guide"
    ), inline=False)

    embed.add_field(name="━━━ ADMIN PANEL ━━━", value=(
        "**Add**\n└ Add a user (Roblox + Discord + days)\n\n"
        "**Remove**\n└ Remove a user from whitelist\n\n"
        "**Ban**\n└ Ban a user permanently\n\n"
        "**Unban**\n└ Remove a ban\n\n"
        "**+Days**\n└ Add more days to someone's access\n\n"
        "**Add Alt**\n└ Add a 2nd Roblox account for a user"
    ), inline=False)

    embed.add_field(name="━━━ ADMIN PANEL (cont.) ━━━", value=(
        "**List**\n└ See all users with avatar and info\n\n"
        "**Search**\n└ Find a user by Roblox or Discord username\n\n"
        "**Banned**\n└ See full ban list with reasons\n\n"
        "**Gen Key**\n└ Generate permanent / custom / DM to user / quick sell\n\n"
        "**Stock**\n└ See all unused available keys\n\n"
        "**HWID**\n└ Force reset someone's executor lock\n\n"
        "**DM All**\n└ Send announcement to every whitelisted user\n\n"
        "**Resellers**\n└ Give someone keys to sell\n\n"
        "**Channels**\n└ Set purchase / vouch / log channels\n\n"
        "**Clear All**\n└ Wipe entire whitelist (asks for confirm)"
    ), inline=False)

    embed.add_field(name="━━━ USER PANEL ━━━", value=(
        "**Redeem Key**\n└ Enter key + Roblox username to get access\n\n"
        "**Get Script**\n└ Shows your personal script key + loadstring\n\n"
        "**Get Role**\n└ Claims your Discord whitelist role\n\n"
        "**Reset HWID**\n└ Unlocks executor (2 day cooldown)\n\n"
        "**Stats**\n└ Shows expiry date, HWID status, access info"
    ), inline=False)

    embed.add_field(name="━━━ FREE TRIAL ━━━", value=(
        "**Option 1 — Everyone:**\n"
        "└ Go to `trial.txt` on GitHub\n"
        "└ Change to `ACTIVE` → everyone can use\n"
        "└ Change back to `ended` when done\n\n"
        "**Option 2 — One person:**\n"
        "└ `/givetrial @user hours:2`"
    ), inline=False)

    embed.set_footer(text=f"{BRAND_NAME} Whitelist System")
    embed.timestamp = datetime.utcnow()
    await interaction.response.send_message(embed=embed, ephemeral=True)

print("Starting bot...")
client.run(TOKEN)
