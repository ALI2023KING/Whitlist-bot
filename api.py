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

# HWID cooldown = 3 DAYS
def get_hwid_reset_time(discord_id):
    lines, _, _ = get_github_file(HWID_RESET_FILE)
    for line in lines:
        parts = line.split("|")
        if len(parts) >= 2 and parts[0].strip() == str(discord_id):
            try:
                last = datetime.strptime(parts[1].strip(), "%Y-%m-%d %H:%M")
                nxt = last + timedelta(days=3)
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
            e.set_footer(text=f"{BRAND_NAME} • Thank you!")
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
                                            dm = make_embed("⏰ Access Expiring in 1 Hour!", f"Hey **{roblox_name}**!\n\nYour **{BRAND_NAME}** access expires in **{minutes} minutes**!\n\nContact the owner to renew!", "warning")
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

class AddUserModal(discord.ui.Modal, title="➕ Add User"):
    username = discord.ui.TextInput(label="Roblox Username", required=True)
    days_input = discord.ui.TextInput(label="Days access (empty = permanent)", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        uid, rname = get_roblox_user_by_username(self.username.value.strip())
        if not uid:
            await interaction.followup.send(embed=make_embed("❌ User Not Found", color_key="error"), ephemeral=True)
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
        update_github_file(GITHUB_FILE, content.strip() + f"\n{uid} | {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} | {rname} | none | none | {expiry} | 0 | none | none", sha)
        e = make_embed("✅ User Added", color_key="success")
        e.add_field(name="Roblox", value=rname, inline=True)
        e.add_field(name="Expires", value=get_expiry_display(expiry), inline=True)
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
    username = discord.ui.TextInput(label="Discord Username", placeholder="e.g. yez.v (without @)", required=True)
    keys_count = discord.ui.TextInput(label="Number of keys to give", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            count = int(self.keys_count.value.strip())
        except:
            await interaction.followup.send(embed=make_embed("❌ Invalid number", color_key="error"), ephemeral=True)
            return
        username = self.username.value.strip().lower().replace("@", "")
        member = None
        for m in interaction.guild.members:
            if m.name.lower() == username or (m.display_name.lower() == username):
                member = m
                break
        if not member:
            await interaction.followup.send(embed=make_embed("❌ User Not Found", f"Could not find **{username}** in this server.", "error"), ephemeral=True)
            return
        current = get_reseller_keys_left(member.id)
        set_reseller_keys(member.id, current + count)
        await interaction.followup.send(embed=make_embed("✅ Reseller Updated", f"{member.mention} now has **{current + count}** keys.", "success"), ephemeral=True)
        try:
            await member.send(embed=make_embed("🔑 You are a Reseller!", f"You have **{count}** keys. Use `/adminpanel` to generate.", "gold"))
        except:
            pass

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
        new_lines = []
        for line in lines:
            if line.startswith(uid):
                new_lines.append(f"{e_uid} | {e_date} | {e_rname} | {e_dstr or 'none'} | {e_note or 'none'} | {new_expiry} | {e_uses} | {e_hwid or 'none'} | {e_skey or 'none'}")
            else:
                new_lines.append(line)
        update_github_file(GITHUB_FILE, "\n".join(new_lines), sha)
        e = make_embed("📅 Expiry Extended", f"**{e_rname}** +{days} days\n**New expiry:** {new_expiry}", "success")
        await interaction.followup.send(embed=e, ephemeral=True)
        await send_log(e)

class TransferModal(discord.ui.Modal, title="🔄 Transfer Whitelist"):
    old_username = discord.ui.TextInput(label="Current Roblox Username", required=True)
    new_username = discord.ui.TextInput(label="New Roblox Username", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        old_id, old_name = get_roblox_user_by_username(self.old_username.value.strip())
        new_id, new_name = get_roblox_user_by_username(self.new_username.value.strip())
        if not old_id or not new_id:
            await interaction.followup.send(embed=make_embed("❌ User Not Found", color_key="error"), ephemeral=True)
            return
        lines, sha, _ = get_github_file(GITHUB_FILE)
        found = next((l for l in lines if l.startswith(old_id)), None)
        if not found:
            await interaction.followup.send(embed=make_embed("❌ Not Whitelisted", color_key="error"), ephemeral=True)
            return
        e_uid, e_date, e_rname, e_dstr, e_note, e_expiry, e_uses, e_hwid, e_skey = parse_entry(found)
        new_lines = [f"{new_id} | {e_date} | {new_name} | {e_dstr or 'none'} | {e_note or 'none'} | {e_expiry or 'never'} | {e_uses} | none | none" if l.startswith(old_id) else l for l in lines]
        update_github_file(GITHUB_FILE, "\n".join(new_lines), sha)
        e = make_embed("🔄 Transfer Complete", f"**{old_name}** → **{new_name}**", "success")
        await interaction.followup.send(embed=e, ephemeral=True)
        await send_log(e)

class PriceListModal(discord.ui.Modal, title="💰 Set Price List"):
    prices = discord.ui.TextInput(label="Prices (one per line)", placeholder="7 Days — 50 Robux\n30 Days — 150 Robux\nLifetime — 300 Robux", style=discord.TextStyle.paragraph, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        set_setting("price_list", self.prices.value)
        await interaction.response.send_message(embed=make_embed("✅ Price List Updated", color_key="success"), ephemeral=True)

class SetChannelModal(discord.ui.Modal, title="📌 Set Channel ID"):
    channel_id = discord.ui.TextInput(label="Channel ID", placeholder="Right click channel → Copy ID", required=True)
    channel_type = discord.ui.TextInput(label="Type: purchase / vouch / stock / log", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            cid = int(self.channel_id.value.strip())
            ctype = self.channel_type.value.strip().lower()
            valid = ["purchase", "vouch", "stock", "log"]
            if ctype not in valid:
                await interaction.response.send_message(embed=make_embed(f"❌ Use: {', '.join(valid)}", color_key="error"), ephemeral=True)
                return
            key = "log_channel" if ctype == "log" else f"{ctype}_channel"
            set_setting(key, cid)
            await interaction.response.send_message(embed=make_embed(f"✅ {ctype.capitalize()} Channel Set!", color_key="success"), ephemeral=True)
        except:
            await interaction.response.send_message(embed=make_embed("❌ Invalid Channel ID", color_key="error"), ephemeral=True)

class CustomKeyModal(discord.ui.Modal, title="⏱️ Custom Key Duration"):
    days_input = discord.ui.TextInput(label="Days", placeholder="e.g. 30", required=False)
    hours_input = discord.ui.TextInput(label="Hours", placeholder="e.g. 12", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        if not owner_or_reseller(interaction):
            await interaction.response.send_message("🚫 Access Denied", ephemeral=True)
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
        key_lines, key_sha, key_content = get_github_file(KEY_FILE)
        update_github_file(KEY_FILE, key_content.strip() + f"\n{key} | {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} | false | 1 | {expiry} | never | normal", key_sha)
        try:
            dm = make_embed("🔑 Custom Key Generated", color_key="gold")
            dm.add_field(name="🔑 Key", value=f"`{key}`", inline=False)
            dm.add_field(name="Duration", value=f"{total_hours}h", inline=True)
            dm.add_field(name="Expires", value=expiry, inline=True)
            await interaction.user.send(embed=dm)
            await interaction.response.send_message(embed=make_embed("✅ Key Sent to DMs!", color_key="success"), ephemeral=True)
        except:
            await interaction.response.send_message(embed=make_embed("❌ DM Failed", color_key="error"), ephemeral=True)

class HWIDResetView(discord.ui.View):
    def __init__(self, entries):
        super().__init__(timeout=60)
        for i, (uid, rname, dstr) in enumerate(entries[:10]):
            btn = discord.ui.Button(label=f"🔄 {rname[:20]}", style=discord.ButtonStyle.red, row=i // 3)
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
            await interaction.response.edit_message(embed=make_embed("🔄 HWID Reset", f"**{rname}**'s HWID reset.", "success"), view=None)
        return callback

class GenerateKeyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)

    @discord.ui.button(label="♾️ Permanent", style=discord.ButtonStyle.green, row=0)
    async def key_perm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._generate(interaction, hours=None, label="Permanent")

    @discord.ui.button(label="⏱️ Custom Duration", style=discord.ButtonStyle.blurple, row=0)
    async def key_custom(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CustomKeyModal())
        self.stop()

    @discord.ui.button(label="🧪 Trial (1hr)", style=discord.ButtonStyle.grey, row=0)
    async def key_trial(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._generate(interaction, hours=1, label="Trial 1 Hour", key_type="trial")

    async def _generate(self, interaction: discord.Interaction, hours, label, key_type="normal"):
        if not owner_or_reseller(interaction):
            await interaction.response.send_message("🚫", ephemeral=True)
            return
        if is_reseller(interaction.user.id) and not owner_only(interaction):
            kl = get_reseller_keys_left(interaction.user.id)
            if kl <= 0:
                await interaction.response.edit_message(embed=make_embed("❌ No Keys Left", color_key="error"), view=None)
                return
            set_reseller_keys(interaction.user.id, kl - 1)
        prefix = "TRIAL" if key_type == "trial" else "SEMI"
        key = generate_key(prefix)
        expiry = "never"
        if hours:
            expiry = (datetime.utcnow() + timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M")
        kl2, ks, kc = get_github_file(KEY_FILE)
        update_github_file(KEY_FILE, kc.strip() + f"\n{key} | {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} | false | 1 | {expiry} | never | {key_type}", ks)
        try:
            dm = make_embed("🔑 New Key Generated", color_key="gold")
            dm.add_field(name="🔑 Key", value=f"`{key}`", inline=False)
            dm.add_field(name="Type", value="🧪 Trial" if key_type == "trial" else "✅ Full", inline=True)
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
        super().__init__(timeout=180)

    @discord.ui.button(label="➕ Add", style=discord.ButtonStyle.green, row=0)
    async def add_btn(self, i: discord.Interaction, b: discord.ui.Button):
        if not owner_only(i): await i.response.send_message("🚫", ephemeral=True); return
        await i.response.send_modal(AddUserModal())

    @discord.ui.button(label="➖ Remove", style=discord.ButtonStyle.red, row=0)
    async def remove_btn(self, i: discord.Interaction, b: discord.ui.Button):
        if not owner_only(i): await i.response.send_message("🚫", ephemeral=True); return
        await i.response.send_modal(RemoveUserModal())

    @discord.ui.button(label="🔨 Ban", style=discord.ButtonStyle.red, row=0)
    async def ban_btn(self, i: discord.Interaction, b: discord.ui.Button):
        if not owner_only(i): await i.response.send_message("🚫", ephemeral=True); return
        await i.response.send_modal(BanUserModal())

    @discord.ui.button(label="✅ Unban", style=discord.ButtonStyle.green, row=0)
    async def unban_btn(self, i: discord.Interaction, b: discord.ui.Button):
        if not owner_only(i): await i.response.send_message("🚫", ephemeral=True); return
        await i.response.send_modal(UnbanUserModal())

    @discord.ui.button(label="📅 +Days", style=discord.ButtonStyle.blurple, row=0)
    async def extend_btn(self, i: discord.Interaction, b: discord.ui.Button):
        if not owner_only(i): await i.response.send_message("🚫", ephemeral=True); return
        await i.response.send_modal(ExtendExpiryModal())

    @discord.ui.button(label="🔑 Key", style=discord.ButtonStyle.blurple, row=1)
    async def genkey_btn(self, i: discord.Interaction, b: discord.ui.Button):
        if not owner_or_reseller(i): await i.response.send_message("🚫", ephemeral=True); return
        await i.response.send_message(embed=make_embed("🔑 Generate Key", "Select key type:", "gold"), view=GenerateKeyView(), ephemeral=True)

    @discord.ui.button(label="📋 List", style=discord.ButtonStyle.grey, row=1)
    async def list_btn(self, i: discord.Interaction, b: discord.ui.Button):
        if not owner_only(i): await i.response.send_message("🚫", ephemeral=True); return
        await i.response.defer(ephemeral=True)
        lines, _, _ = get_github_file(GITHUB_FILE)
        ban_lines, _, _ = get_github_file(BAN_FILE)
        entries = [l for l in lines if not l.startswith("--")]
        ban_entries = [l for l in ban_lines if not l.startswith("--")]
        embed = make_embed(f"📋 {BRAND_NAME} WHITELIST", color_key="info")
        embed.description = f"[📄 View on GitHub](https://github.com/{GITHUB_REPO}/blob/main/{GITHUB_FILE})\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        if not entries:
            embed.description += "Empty.\n"
        else:
            for line in entries:
                uid, date, rname, dstr, note, expiry, uses, hwid, sk = parse_entry(line)
                name = rname if rname else uid
                dmention = f"<@{dstr}>" if dstr and dstr != "none" else "No Discord"
                status = "⚠️" if is_expired(expiry) else "✅"
                embed.description += f"{status} **{name}** — {dmention}\n"
        embed.description += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        embed.add_field(name="✅", value=str(len(entries)), inline=True)
        embed.add_field(name="🔨", value=str(len(ban_entries)), inline=True)
        await i.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(label="📢 DM All", style=discord.ButtonStyle.grey, row=1)
    async def announce_btn(self, i: discord.Interaction, b: discord.ui.Button):
        if not owner_only(i): await i.response.send_message("🚫", ephemeral=True); return
        await i.response.send_modal(AnnounceModal())

    @discord.ui.button(label="🔄 Transfer", style=discord.ButtonStyle.grey, row=1)
    async def transfer_btn(self, i: discord.Interaction, b: discord.ui.Button):
        if not owner_only(i): await i.response.send_message("🚫", ephemeral=True); return
        await i.response.send_modal(TransferModal())

    @discord.ui.button(label="🔑 Keys", style=discord.ButtonStyle.grey, row=1)
    async def keylist_btn(self, i: discord.Interaction, b: discord.ui.Button):
        if not owner_only(i): await i.response.send_message("🚫", ephemeral=True); return
        await i.response.defer(ephemeral=True)
        kl, _, _ = get_github_file(KEY_FILE)
        if not kl:
            await i.followup.send(embed=make_embed("🔑 No Keys", color_key="info"), ephemeral=True)
            return
        desc = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        for line in kl:
            k, date, used, mu, expiry, days, kt = parse_key(line)
            st = "✅" if used == "false" else "❌"
            if is_expired(expiry): st = "⚠️"
            desc += f"{st} `{k}`{'🧪' if kt == 'trial' else ''} — {get_expiry_display(expiry)}\n"
        desc += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        embed = make_embed("🔑 All Keys", desc, "gold")
        embed.add_field(name="Total", value=str(len(kl)), inline=True)
        await i.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(label="🔒 HWID", style=discord.ButtonStyle.grey, row=2)
    async def hwid_btn(self, i: discord.Interaction, b: discord.ui.Button):
        if not owner_only(i): await i.response.send_message("🚫", ephemeral=True); return
        await i.response.defer(ephemeral=True)
        lines, _, _ = get_github_file(GITHUB_FILE)
        entries = [(parse_entry(l)[0], parse_entry(l)[2] or parse_entry(l)[0], parse_entry(l)[3] or "none") for l in lines if not l.startswith("--") and parse_entry(l)[7] and parse_entry(l)[7] != "none"]
        if not entries:
            await i.followup.send(embed=make_embed("🔒 No HWID locked users", color_key="info"), ephemeral=True)
            return
        await i.followup.send(embed=make_embed("🔒 HWID Reset Panel", "Tap a user to reset.", "gold"), view=HWIDResetView(entries), ephemeral=True)

    @discord.ui.button(label="👥 Resell", style=discord.ButtonStyle.grey, row=2)
    async def resellers_btn(self, i: discord.Interaction, b: discord.ui.Button):
        if not owner_only(i): await i.response.send_message("🚫", ephemeral=True); return
        await i.response.send_modal(ResellerModal())

    @discord.ui.button(label="💰 Prices", style=discord.ButtonStyle.grey, row=2)
    async def prices_btn(self, i: discord.Interaction, b: discord.ui.Button):
        if not owner_only(i): await i.response.send_message("🚫", ephemeral=True); return
        await i.response.send_modal(PriceListModal())

    @discord.ui.button(label="📌 Channels", style=discord.ButtonStyle.grey, row=2)
    async def channels_btn(self, i: discord.Interaction, b: discord.ui.Button):
        if not owner_only(i): await i.response.send_message("🚫", ephemeral=True); return
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
            uid, date, rname, dstr, note, expiry, uses, hwid, sk = parse_entry(line)
            if dstr and dstr == str(interaction.user.id):
                user_entry = (uid, date, rname, dstr, note, expiry, uses, hwid, sk)
                break
        if not user_entry:
            await interaction.response.send_message(embed=make_embed("❌ Not Whitelisted", "Redeem a key first.", "error"), ephemeral=True)
            return
        uid, date, rname, dstr, note, expiry, uses, hwid, sk = user_entry
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
            await interaction.response.send_message(embed=make_embed("❌ Permission Error", "Bot role must be **above** the whitelist role in server settings!", "error"), ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(embed=make_embed("❌ Error", str(e), "error"), ephemeral=True)

    @discord.ui.button(label="🔄 Reset HWID", style=discord.ButtonStyle.grey, custom_id="panel_hwid", row=1)
    async def reset_hwid(self, interaction: discord.Interaction, button: discord.ui.Button):
        nxt = get_hwid_reset_time(interaction.user.id)
        if nxt:
            tl = nxt - datetime.utcnow()
            h = int(tl.total_seconds() // 3600)
            m = int((tl.total_seconds() % 3600) // 60)
            await interaction.response.send_message(embed=make_embed("⏳ HWID Cooldown", f"Reset available in **{h}h {m}m**.", "warning"), ephemeral=True)
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
        await interaction.response.send_message(embed=make_embed("🔄 HWID Reset", "Done! Next reset in **3 days**.", "success"), ephemeral=True)
        await send_log(make_embed("🔄 HWID Reset", f"{interaction.user.mention} reset HWID.", "warning"))

    @discord.ui.button(label="📊 Get Stats", style=discord.ButtonStyle.grey, custom_id="panel_stats", row=1)
    async def get_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        lines, _, _ = get_github_file(GITHUB_FILE)
        for line in lines:
            uid, date, rname, dstr, note, expiry, uses, hwid, sk = parse_entry(line)
            if dstr and dstr == str(interaction.user.id):
                expired = is_expired(expiry)
                nxt = get_hwid_reset_time(interaction.user.id)
                embed = make_embed("📊 Your Stats", color_key="warning" if expired else "success")
                embed.add_field(name="Roblox", value=rname or uid, inline=True)
                embed.add_field(name="Status", value="⚠️ Expired" if expired else "✅ Active", inline=True)
                embed.add_field(name="Added", value=date, inline=True)
                embed.add_field(name="Expires", value=get_expiry_display(expiry), inline=True)
                embed.add_field(name="HWID", value="🔒 Locked" if hwid and hwid != "none" else "🔓 Unlocked", inline=True)
                if nxt:
                    tl = nxt - datetime.utcnow()
                    embed.add_field(name="HWID Reset", value=f"In {int(tl.total_seconds()//3600)}h", inline=True)
                else:
                    embed.add_field(name="HWID Reset", value="Available ✅", inline=True)
                av = get_roblox_avatar(uid)
                if av:
                    embed.set_image(url=av)
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
        update_github_file(GITHUB_FILE, wl_content.strip() + f"\n{user_id} | {add_date} | {roblox_name} | {interaction.user.id} | Redeemed key | {expiry_date} | 0 | none | none", wl_sha)
        new_key_lines = []
        for line in key_lines:
            k2, d2, u2, m2, e2, dy2, kt2 = parse_key(line)
            new_key_lines.append(f"{k2} | {d2} | true | {m2} | {e2} | {dy2} | {kt2}" if k2 == key else line)
        update_github_file(KEY_FILE, "\n".join(new_key_lines), key_sha)
        reset_failed_attempts(interaction.user.id)
        role_given = await give_whitelist_role(interaction.guild, str(interaction.user.id))
        avatar = get_roblox_avatar(user_id)
        is_trial = kt == "trial"
        embed = discord.Embed(
            title="✅ Key Redeemed!" if not is_trial else "🧪 Trial Key Redeemed!",
            description=(f"Welcome **{roblox_name}**!\n\n{'🧪 **Trial** — limited access.\n' if is_trial else ''}Click **Get Script** to receive your script.\n{'✅ Role given!' if role_given else '👤 Click Get Role for your role.'}"),
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
            vouch_cid = get_setting("vouch_channel")
            vouch_text = f"\n\n📣 Please leave a vouch in <#{vouch_cid}>!" if vouch_cid else ""
            welcome_dm = discord.Embed(
                title=f"👑 Welcome to {BRAND_NAME}!",
                description=(f"Hey **{roblox_name}**! Key redeemed.\n\n**How to use:**\n1️⃣ Go to panel\n2️⃣ Click **Get Script**\n3️⃣ Run it in your executor\n\n**HWID:** Locks on first run.\nReset every **3 days** from panel.\n\n{'⚠️ **Trial** — upgrade for full!' if is_trial else '✅ Full access!'}{vouch_text}"),
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
    embed = discord.Embed(title=BRAND_NAME, description=(f"This control panel is for the project: **{BRAND_NAME}**\nIf you're a buyer, click on the buttons below to redeem your key, get the script or get your role."), color=BRAND_COLOR)
    embed.set_footer(text=f"Sent by {interaction.user.name} • {datetime.utcnow().strftime('%m/%d/%Y %I:%M %p')}")
    await interaction.response.send_message(embed=embed, view=PanelView())

@tree.command(name="adminpanel", description="Open the admin control panel")
async def admin_panel(interaction: discord.Interaction):
    if not owner_only(interaction) and not is_reseller(interaction.user.id):
        await interaction.response.send_message(embed=make_embed("🚫 Access Denied", color_key="error"), ephemeral=True)
        return
    is_res = is_reseller(interaction.user.id) and not owner_only(interaction)
    kl = get_reseller_keys_left(interaction.user.id) if is_res else None
    lines, _, _ = get_github_file(GITHUB_FILE)
    ban_lines, _, _ = get_github_file(BAN_FILE)
    total = len([l for l in lines if not l.startswith("--")])
    banned = len([l for l in ban_lines if not l.startswith("--")])
    embed = discord.Embed(
        title=f"👑 {BRAND_NAME} — Admin Panel",
        description=(f"{'🔑 **Reseller** — Keys left: **' + str(kl) + '**\n' if is_res else ''}━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n✅ **Whitelisted:** {total}   🔨 **Banned:** {banned}\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━"),
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
    await interaction.response.send_message(embed=make_embed("✅ Role Set", f"Whitelisted users will receive **{role.name}**.\n\n⚠️ Make sure the bot role is **above** `{role.name}` in Server Settings → Roles!", "success"))

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
        await interaction.response.send_message(embed=make_embed("❌ No Price List Set", "Owner needs to set prices via /adminpanel → 💰 Prices.", "error"), ephemeral=True)
        return
    embed = discord.Embed(title=f"💰 {BRAND_NAME} — Price List", description=prices, color=BRAND_COLOR)
    embed.set_footer(text=f"{BRAND_NAME} • DM to purchase")
    embed.timestamp = datetime.utcnow()
    await interaction.response.send_message(embed=embed)

@tree.command(name="stock", description="Show available keys stock")
async def stock(interaction: discord.Interaction):
    kl, _, _ = get_github_file(KEY_FILE)
    available = sum(1 for l in kl if parse_key(l)[2] == "false" and not is_expired(parse_key(l)[4]))
    embed = discord.Embed(
        title=f"📦 {BRAND_NAME} — Stock",
        description=(f"🔑 **Available Keys:** {available}\n\n{'✅ Keys available! DM to purchase.' if available > 0 else '❌ No keys available right now.'}"),
        color=COLORS["success"] if available > 0 else COLORS["error"]
    )
    embed.set_footer(text=f"{BRAND_NAME} • Updated live")
    embed.timestamp = datetime.utcnow()
    await interaction.response.send_message(embed=embed)

@tree.command(name="help", description="Show all commands")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title=f"{BRAND_NAME} — Help", description="━━━━━━━━━━━━━━━━━━━━━━━━━━━━", color=BRAND_COLOR)
    embed.add_field(name="🎛️ Main", value="`/panel` `/adminpanel` `/setscript` `/setrole` `/setlog`", inline=False)
    embed.add_field(name="📦 Public", value="`/pricelist` `/stock`", inline=False)
    embed.add_field(name="👑 Admin Panel Buttons", value="➕ Add • ➖ Remove • 🔨 Ban • ✅ Unban • 📅 Extend\n🔑 Gen Key • 📋 List • 📢 Announce • 🔄 Transfer\n🔒 HWID • 🔑 Keys • 👥 Resellers • 💰 Prices • 📌 Channels", inline=False)
    embed.add_field(name="👤 User Panel", value="🔑 Redeem • 📜 Get Script • 👤 Get Role\n🔄 Reset HWID • 📊 Get Stats", inline=False)
    embed.set_footer(text=f"{BRAND_NAME} Whitelist System")
    embed.timestamp = datetime.utcnow()
    await interaction.response.send_message(embed=embed, ephemeral=True)

print("Starting bot...")
client.run(TOKEN)
