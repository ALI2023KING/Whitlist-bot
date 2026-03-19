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

LOG_CHANNEL_ID = None
WHITELIST_ROLE_ID = None
PANEL_CHANNEL_ID = None

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
    "gold": 0xFFD700,
    "white": 0xFFFFFF,
    "dark": 0x2B2D31
}

PROJECT_NAME = "ꜱᴇᴍɪ ɪɴꜱᴛᴀɴᴛ"

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
    return user_id, date, roblox_name, discord_user, note, expiry, uses, hwid

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
    parts = ["SEMI"] + ["".join(random.choices(string.ascii_uppercase + string.digits, k=4)) for _ in range(3)]
    return "-".join(parts)

def get_hwid_reset_time(discord_id):
    lines, _, _ = get_github_file(HWID_RESET_FILE)
    for line in lines:
        parts = line.split("|")
        if len(parts) >= 2 and parts[0].strip() == str(discord_id):
            try:
                last_reset = datetime.strptime(parts[1].strip(), "%Y-%m-%d %H:%M")
                next_reset = last_reset + timedelta(days=2)
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

async def username_autocomplete(interaction: discord.Interaction, current: str):
    lines, _, _ = get_github_file(GITHUB_FILE)
    choices = []
    for line in lines:
        uid, date, roblox_name, discord_user, note, expiry, uses, hwid = parse_entry(line)
        if roblox_name and current.lower() in roblox_name.lower():
            choices.append(app_commands.Choice(name=roblox_name, value=roblox_name))
        if len(choices) >= 25:
            break
    return choices

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

class GenerateKeyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(label="⏰ 4 Hours", style=discord.ButtonStyle.blurple)
    async def key_4h(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._generate(interaction, hours=4, label="4 Hours")

    @discord.ui.button(label="🌙 1 Day", style=discord.ButtonStyle.blurple)
    async def key_1d(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._generate(interaction, hours=24, label="1 Day")

    @discord.ui.button(label="📅 2 Days", style=discord.ButtonStyle.blurple)
    async def key_2d(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._generate(interaction, hours=48, label="2 Days")

    @discord.ui.button(label="📅 7 Days", style=discord.ButtonStyle.blurple)
    async def key_7d(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._generate(interaction, hours=168, label="7 Days")

    @discord.ui.button(label="♾️ Permanent", style=discord.ButtonStyle.green)
    async def key_perm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._generate(interaction, hours=None, label="Permanent")

    async def _generate(self, interaction: discord.Interaction, hours, label):
        key = generate_key()
        date = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        expiry = "never"
        if hours:
            expiry_dt = datetime.utcnow() + timedelta(hours=hours)
            expiry = expiry_dt.strftime("%Y-%m-%d %H:%M")
        key_lines, key_sha, key_content = get_github_file(KEY_FILE)
        new_entry = f"{key} | {date} | false | 1 | {expiry} | never"
        new_content = key_content.strip() + f"\n{new_entry}"
        update_github_file(KEY_FILE, new_content, key_sha)
        try:
            dm_embed = discord.Embed(title=f"🔑 {PROJECT_NAME} — Key Generated", color=COLORS["white"])
            dm_embed.add_field(name="🔑 Key", value=f"`{key}`", inline=False)
            dm_embed.add_field(name="Duration", value=label, inline=True)
            dm_embed.add_field(name="Key Expires", value=expiry if expiry != "never" else "Never", inline=True)
            dm_embed.set_footer(text="⚠️ Single use only — expires after 1 redemption!")
            dm_embed.timestamp = datetime.utcnow()
            await interaction.user.send(embed=dm_embed)
            confirm_embed = discord.Embed(
                title="✅ Key Sent to DMs",
                description=f"A **{label}** key has been sent to your DMs!\n⚠️ Single use only.",
                color=COLORS["success"]
            )
            await interaction.response.edit_message(embed=confirm_embed, view=None)
        except:
            embed = discord.Embed(title="❌ DM Failed", color=COLORS["error"])
            await interaction.response.edit_message(embed=embed, view=None)
        self.stop()

class CustomTimeModal(discord.ui.Modal, title="Custom Key Duration"):
    hours_input = discord.ui.TextInput(
        label="Hours (e.g. 12 for 12 hours)",
        placeholder="Enter number of hours",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            hours = int(self.hours_input.value.strip())
            if hours <= 0:
                raise ValueError
        except:
            embed = discord.Embed(title="❌ Invalid Input", description="Please enter a valid number of hours.", color=COLORS["error"])
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        key = generate_key()
        date = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        expiry_dt = datetime.utcnow() + timedelta(hours=hours)
        expiry = expiry_dt.strftime("%Y-%m-%d %H:%M")
        key_lines, key_sha, key_content = get_github_file(KEY_FILE)
        new_entry = f"{key} | {date} | false | 1 | {expiry} | never"
        new_content = key_content.strip() + f"\n{new_entry}"
        update_github_file(KEY_FILE, new_content, key_sha)
        try:
            dm_embed = discord.Embed(title=f"🔑 {PROJECT_NAME} — Key Generated", color=COLORS["white"])
            dm_embed.add_field(name="🔑 Key", value=f"`{key}`", inline=False)
            dm_embed.add_field(name="Duration", value=f"{hours} hours", inline=True)
            dm_embed.add_field(name="Key Expires", value=expiry, inline=True)
            dm_embed.set_footer(text="⚠️ Single use only!")
            dm_embed.timestamp = datetime.utcnow()
            await interaction.user.send(embed=dm_embed)
            embed = discord.Embed(
                title="✅ Key Sent to DMs",
                description=f"A **{hours} hour** key has been sent to your DMs!",
                color=COLORS["success"]
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except:
            embed = discord.Embed(title="❌ DM Failed", color=COLORS["error"])
            await interaction.response.send_message(embed=embed, ephemeral=True)

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
            uid, date, roblox_name, discord_str, note, expiry, uses, hwid = parse_entry(line)
            if discord_str and discord_str == str(interaction.user.id):
                user_entry = (uid, date, roblox_name, discord_str, note, expiry, uses, hwid)
                break
        if not user_entry:
            embed = discord.Embed(
                title="Not whitelisted!",
                description=(
                    f"You need to be whitelisted to get this script.\n"
                    f"If you have a script key, click on the **Redeem** button below to redeem it"
                ),
                color=COLORS["white"]
            )
            embed.timestamp = datetime.utcnow()
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        uid, date, roblox_name, discord_str, note, expiry, uses, hwid = user_entry
        if is_expired(expiry):
            embed = discord.Embed(
                title="⚠️ Access Expired",
                description="Your whitelist has expired. Contact the owner.",
                color=COLORS["white"]
            )
            embed.timestamp = datetime.utcnow()
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        _, _, script_content = get_github_file(SCRIPT_FILE)
        if not script_content:
            embed = discord.Embed(
                title="❌ No Script Set",
                description="Contact the owner.",
                color=COLORS["error"]
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        key = generate_key()
        key_lines, key_sha, key_content = get_github_file(KEY_FILE)
        script_key_entry = f"SCRIPTKEY-{uid} | {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} | false | 1 | never | never"
        script_with_key = f"-- 🔑 Script Key: SCRIPTKEY-{uid[:8]}\n-- ⚠️ Do not share this script!\n\n{script_content}"
        embed = discord.Embed(
            title=f"📜 {PROJECT_NAME} — Your Script",
            description=f"```lua\n{script_with_key[:1800]}\n```",
            color=COLORS["white"]
        )
        embed.set_footer(text="⚠️ Do not share this script with anyone!")
        embed.timestamp = datetime.utcnow()
        await interaction.response.send_message(embed=embed, ephemeral=True)
        if LOG_CHANNEL_ID:
            log_embed = discord.Embed(
                title="📜 Script Retrieved",
                description=f"{interaction.user.mention} got the script.",
                color=COLORS["info"]
            )
            log_embed.timestamp = datetime.utcnow()
            await send_log(log_embed)

    @discord.ui.button(label="👤 Get Role", style=discord.ButtonStyle.blurple, custom_id="panel_role", row=0)
    async def get_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not WHITELIST_ROLE_ID:
            embed = discord.Embed(
                title="❌ No Role Set",
                description="The owner has not set a whitelist role yet.",
                color=COLORS["error"]
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        lines, _, _ = get_github_file(GITHUB_FILE)
        user_entry = None
        for line in lines:
            uid, date, roblox_name, discord_str, note, expiry, uses, hwid = parse_entry(line)
            if discord_str and discord_str == str(interaction.user.id):
                user_entry = (uid, date, roblox_name, discord_str, note, expiry, uses, hwid)
                break
        if not user_entry:
            embed = discord.Embed(
                title="Not whitelisted!",
                description="You need to be whitelisted to get a role.\nIf you have a key, click **Redeem Key** first.",
                color=COLORS["white"]
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        uid, date, roblox_name, discord_str, note, expiry, uses, hwid = user_entry
        if is_expired(expiry):
            embed = discord.Embed(title="⚠️ Access Expired", color=COLORS["white"])
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        role = interaction.guild.get_role(WHITELIST_ROLE_ID)
        if not role:
            embed = discord.Embed(title="❌ Role Not Found", color=COLORS["error"])
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        if role in interaction.user.roles:
            embed = discord.Embed(
                title="✅ Already Have Role",
                description=f"You already have **{role.name}**!",
                color=COLORS["white"]
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        await interaction.user.add_roles(role)
        embed = discord.Embed(
            title="✅ Role Given",
            description=f"You have been given **{role.name}**!",
            color=COLORS["success"]
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="🔄 Reset HWID", style=discord.ButtonStyle.grey, custom_id="panel_hwid", row=0)
    async def reset_hwid(self, interaction: discord.Interaction, button: discord.ui.Button):
        next_reset = get_hwid_reset_time(interaction.user.id)
        if next_reset:
            time_left = next_reset - datetime.utcnow()
            hours_left = int(time_left.total_seconds() // 3600)
            minutes_left = int((time_left.total_seconds() % 3600) // 60)
            embed = discord.Embed(
                title="⏳ HWID Reset Cooldown",
                description=f"You can reset your HWID again in **{hours_left}h {minutes_left}m**.\nContact the owner for an emergency reset.",
                color=COLORS["white"]
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        lines, sha, content = get_github_file(GITHUB_FILE)
        new_lines = []
        found = False
        for line in lines:
            uid, date, roblox_name, discord_str, note, expiry, uses, hwid = parse_entry(line)
            if discord_str and discord_str == str(interaction.user.id):
                found = True
                new_lines.append(f"{uid} | {date} | {roblox_name} | {discord_str} | {note or 'none'} | {expiry or 'never'} | {uses} | none")
            else:
                new_lines.append(line)
        if not found:
            embed = discord.Embed(
                title="Not whitelisted!",
                description="You are not whitelisted.",
                color=COLORS["white"]
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        update_github_file(GITHUB_FILE, "\n".join(new_lines), sha)
        set_hwid_reset_time(interaction.user.id)
        embed = discord.Embed(
            title="🔄 HWID Reset",
            description="Your HWID has been reset!\nYou can now use the script on a new executor.\n\n⚠️ Next reset available in **48 hours**.",
            color=COLORS["success"]
        )
        embed.timestamp = datetime.utcnow()
        await interaction.response.send_message(embed=embed, ephemeral=True)
        if LOG_CHANNEL_ID:
            log_embed = discord.Embed(
                title="🔄 HWID Reset",
                description=f"{interaction.user.mention} reset their HWID.",
                color=COLORS["warning"]
            )
            log_embed.timestamp = datetime.utcnow()
            await send_log(log_embed)

    @discord.ui.button(label="📊 Get Stats", style=discord.ButtonStyle.grey, custom_id="panel_stats", row=0)
    async def get_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        lines, _, _ = get_github_file(GITHUB_FILE)
        for line in lines:
            uid, date, roblox_name, discord_str, note, expiry, uses, hwid = parse_entry(line)
            if discord_str and discord_str == str(interaction.user.id):
                expired = is_expired(expiry)
                next_hwid = get_hwid_reset_time(interaction.user.id)
                embed = discord.Embed(
                    title=f"📊 Stats — {roblox_name or uid}",
                    color=COLORS["white"]
                )
                embed.add_field(name="Roblox", value=roblox_name or uid, inline=True)
                embed.add_field(name="Status", value="⚠️ Expired" if expired else "✅ Active", inline=True)
                embed.add_field(name="Added", value=date, inline=True)
                embed.add_field(name="Expires", value=expiry if expiry and expiry != "never" else "Never", inline=True)
                embed.add_field(name="HWID", value="🔒 Locked" if hwid and hwid != "none" else "🔓 Unlocked", inline=True)
                if next_hwid:
                    time_left = next_hwid - datetime.utcnow()
                    hours_left = int(time_left.total_seconds() // 3600)
                    embed.add_field(name="Next HWID Reset", value=f"In {hours_left}h", inline=True)
                else:
                    embed.add_field(name="Next HWID Reset", value="Available now", inline=True)
                avatar = get_roblox_avatar(uid)
                if avatar:
                    embed.set_image(url=avatar)
                embed.timestamp = datetime.utcnow()
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
        embed = discord.Embed(
            title="Not whitelisted!",
            description="You are not whitelisted.",
            color=COLORS["white"]
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

class RedeemKeyModal(discord.ui.Modal, title="🔑 Redeem Key"):
    key_input = discord.ui.TextInput(
        label="Enter your key",
        placeholder="SEMI-XXXX-XXXX-XXXX",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        key = self.key_input.value.strip().upper()
        key_lines, key_sha, key_content = get_github_file(KEY_FILE)
        found_key = None
        for line in key_lines:
            k, date, used, max_uses, expiry, days = parse_key(line)
            if k == key:
                found_key = line
                break
        if not found_key:
            embed = discord.Embed(
                title="❌ Invalid Key",
                description="This key does not exist.",
                color=COLORS["white"]
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        k, date, used, max_uses, expiry, days = parse_key(found_key)
        if used == "true":
            embed = discord.Embed(
                title="❌ Key Already Used",
                description="This key has already been redeemed.",
                color=COLORS["white"]
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        if is_expired(expiry):
            embed = discord.Embed(
                title="❌ Key Expired",
                description="This key has expired.",
                color=COLORS["white"]
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        wl_lines, wl_sha, wl_content = get_github_file(GITHUB_FILE)
        for line in wl_lines:
            uid, date2, roblox_name2, discord_str2, note2, expiry2, uses2, hwid2 = parse_entry(line)
            if discord_str2 and discord_str2 == str(interaction.user.id):
                embed = discord.Embed(
                    title="⚠️ Already Whitelisted",
                    description="Your Discord account is already whitelisted.",
                    color=COLORS["white"]
                )
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
        discord_id = str(interaction.user.id)
        new_entry = f"DISCORD-{discord_id} | {add_date} | {interaction.user.name} | {discord_id} | Redeemed key | {expiry_date} | 0 | none"
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
        if WHITELIST_ROLE_ID and interaction.guild:
            role = interaction.guild.get_role(WHITELIST_ROLE_ID)
            if role:
                try:
                    await interaction.user.add_roles(role)
                except:
                    pass
        embed = discord.Embed(
            title="✅ Key Redeemed Successfully!",
            description=(
                f"Welcome **{interaction.user.name}**!\n\n"
                f"You now have access to **{PROJECT_NAME}**.\n"
                f"Click **Get Script** to receive your script.\n"
                f"Click **Get Role** to get your role."
            ),
            color=COLORS["success"]
        )
        embed.add_field(name="Discord", value=interaction.user.mention, inline=True)
        embed.add_field(name="Expires", value=expiry_date if expiry_date != "never" else "Never", inline=True)
        embed.set_footer(text=f"{PROJECT_NAME} Whitelist System")
        embed.timestamp = datetime.utcnow()
        await interaction.response.send_message(embed=embed, ephemeral=True)
        if LOG_CHANNEL_ID:
            log_embed = discord.Embed(
                title="🔑 Key Redeemed",
                description=f"{interaction.user.mention} redeemed key `{key}`",
                color=COLORS["success"]
            )
            log_embed.timestamp = datetime.utcnow()
            await send_log(log_embed)

@client.event
async def on_ready():
    await tree.sync()
    client.add_view(PanelView())
    await client.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=f"👑 {PROJECT_NAME}"
        )
    )
    print(f"Bot is online as {client.user}")

@tree.command(name="panel", description="Send the whitelist control panel")
async def panel(interaction: discord.Interaction):
    if not owner_only(interaction):
        embed = discord.Embed(title="🚫 Access Denied", color=COLORS["error"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    global PANEL_CHANNEL_ID
    PANEL_CHANNEL_ID = interaction.channel_id
    embed = discord.Embed(
        title=PROJECT_NAME,
        description=(
            f"This control panel is for the project: **{PROJECT_NAME}**\n"
            f"If you're a buyer, click on the buttons below to redeem your key, "
            f"get the script or get your role."
        ),
        color=COLORS["white"]
    )
    embed.set_footer(text=f"Sent by {interaction.user.name} • {datetime.utcnow().strftime('%m/%d/%Y %I:%M %p')}")
    await interaction.response.send_message(embed=embed, view=PanelView())

@tree.command(name="add", description="Add a Discord user to the whitelist")
@app_commands.describe(discord_user="Their Discord user", note="Note", days="Days of access")
async def add_user(interaction: discord.Interaction, discord_user: discord.Member, note: str = None, days: int = None):
    if not owner_only(interaction):
        embed = discord.Embed(title="🚫 Access Denied", color=COLORS["error"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    if is_on_cooldown(interaction.user.id):
        embed = discord.Embed(title="⏳ Cooldown", color=COLORS["warning"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    await interaction.response.defer()
    discord_id = str(discord_user.id)
    lines, sha, content = get_github_file(GITHUB_FILE)
    ban_lines, _, _ = get_github_file(BAN_FILE)
    for line in lines:
        uid, date, roblox_name, discord_str, note2, expiry, uses, hwid = parse_entry(line)
        if discord_str == discord_id:
            embed = discord.Embed(title="⚠️ Already Whitelisted", color=COLORS["warning"])
            await interaction.followup.send(embed=embed)
            return
    date = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    expiry = "never"
    if days:
        expiry_date = datetime.utcnow() + timedelta(days=days)
        expiry = expiry_date.strftime("%Y-%m-%d %H:%M")
    note_str = note if note else "none"
    new_entry = f"DISCORD-{discord_id} | {date} | {discord_user.name} | {discord_id} | {note_str} | {expiry} | 0 | none"
    new_content = content.strip() + f"\n{new_entry}"
    update_github_file(GITHUB_FILE, new_content, sha)
    embed = discord.Embed(title="✅ User Whitelisted", color=COLORS["success"])
    embed.add_field(name="Discord", value=discord_user.mention, inline=True)
    embed.add_field(name="Expires", value=expiry if expiry != "never" else "Never", inline=True)
    embed.set_footer(text=f"{PROJECT_NAME} • GitHub updated")
    embed.timestamp = datetime.utcnow()
    await interaction.followup.send(embed=embed)
    await send_log(embed)
    await give_whitelist_role(interaction.guild, discord_user.id)
    try:
        dm_embed = discord.Embed(
            title=f"✅ You have been Whitelisted — {PROJECT_NAME}!",
            description=f"**Expires:** {expiry if expiry != 'never' else 'Never'}\n\nGo to the server panel to get your script and role!",
            color=COLORS["success"]
        )
        await discord_user.send(embed=dm_embed)
    except:
        pass

@tree.command(name="remove", description="Remove a user from the whitelist")
@app_commands.describe(discord_user="Discord user to remove")
async def remove_user(interaction: discord.Interaction, discord_user: discord.Member):
    if not owner_only(interaction):
        embed = discord.Embed(title="🚫 Access Denied", color=COLORS["error"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    await interaction.response.defer()
    discord_id = str(discord_user.id)
    lines, sha, content = get_github_file(GITHUB_FILE)
    found_line = None
    for line in lines:
        uid, date, roblox_name, discord_str, note, expiry, uses, hwid = parse_entry(line)
        if discord_str == discord_id:
            found_line = line
            break
    if not found_line:
        embed = discord.Embed(title="❌ Not Found", color=COLORS["error"])
        await interaction.followup.send(embed=embed)
        return
    confirm_embed = discord.Embed(
        title="⚠️ Confirm Remove",
        description=f"Remove **{discord_user.name}**?",
        color=COLORS["warning"]
    )

    async def do_remove(i: discord.Interaction):
        new_lines = [l for l in lines if not (parse_entry(l)[3] == discord_id)]
        update_github_file(GITHUB_FILE, "\n".join(new_lines), sha)
        result_embed = discord.Embed(title="🗑️ User Removed", description=f"**{discord_user.name}** removed.", color=COLORS["ban"])
        result_embed.timestamp = datetime.utcnow()
        await i.response.edit_message(embed=result_embed, view=None)
        await send_log(result_embed)
        await remove_whitelist_role(i.guild, discord_id)
        try:
            dm_embed = discord.Embed(title="❌ Whitelist Removed", description="Your access has been removed.", color=COLORS["error"])
            await discord_user.send(embed=dm_embed)
        except:
            pass

    view = ConfirmView(do_remove)
    await interaction.followup.send(embed=confirm_embed, view=view)

@tree.command(name="ban", description="Ban a Discord user")
@app_commands.describe(discord_user="Discord user to ban")
async def ban_user(interaction: discord.Interaction, discord_user: discord.Member):
    if not owner_only(interaction):
        embed = discord.Embed(title="🚫 Access Denied", color=COLORS["error"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    await interaction.response.defer()
    discord_id = str(discord_user.id)
    ban_lines, ban_sha, ban_content = get_github_file(BAN_FILE)
    for line in ban_lines:
        if parse_entry(line)[3] == discord_id:
            embed = discord.Embed(title="⚠️ Already Banned", color=COLORS["warning"])
            await interaction.followup.send(embed=embed)
            return
    confirm_embed = discord.Embed(
        title="⚠️ Confirm Ban",
        description=f"Ban **{discord_user.name}**?",
        color=COLORS["warning"]
    )

    async def do_ban(i: discord.Interaction):
        lines, sha, content = get_github_file(GITHUB_FILE)
        new_lines = [l for l in lines if not (parse_entry(l)[3] == discord_id)]
        update_github_file(GITHUB_FILE, "\n".join(new_lines), sha)
        date = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        new_ban = ban_content.strip() + f"\nDISCORD-{discord_id} | {date} | {discord_user.name} | {discord_id}"
        update_github_file(BAN_FILE, new_ban, ban_sha)
        result_embed = discord.Embed(title="🔨 User Banned", description=f"**{discord_user.name}** has been banned.", color=COLORS["error"])
        result_embed.timestamp = datetime.utcnow()
        await i.response.edit_message(embed=result_embed, view=None)
        await send_log(result_embed)
        await remove_whitelist_role(i.guild, discord_id)
        try:
            dm_embed = discord.Embed(title="🔨 You have been Banned", color=COLORS["error"])
            await discord_user.send(embed=dm_embed)
        except:
            pass

    view = ConfirmView(do_ban)
    await interaction.followup.send(embed=confirm_embed, view=view)

@tree.command(name="unban", description="Unban a Discord user")
@app_commands.describe(discord_user="Discord user to unban")
async def unban_user(interaction: discord.Interaction, discord_user: discord.Member):
    if not owner_only(interaction):
        embed = discord.Embed(title="🚫 Access Denied", color=COLORS["error"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    await interaction.response.defer()
    discord_id = str(discord_user.id)
    ban_lines, ban_sha, _ = get_github_file(BAN_FILE)
    found = any(parse_entry(l)[3] == discord_id for l in ban_lines)
    if not found:
        embed = discord.Embed(title="❌ Not Banned", color=COLORS["error"])
        await interaction.followup.send(embed=embed)
        return
    new_lines = [l for l in ban_lines if not (parse_entry(l)[3] == discord_id)]
    update_github_file(BAN_FILE, "\n".join(new_lines), ban_sha)
    embed = discord.Embed(title="✅ User Unbanned", description=f"**{discord_user.name}** unbanned.", color=COLORS["success"])
    embed.timestamp = datetime.utcnow()
    await interaction.followup.send(embed=embed)

@tree.command(name="hwid_reset", description="Force reset HWID for a user as owner")
@app_commands.describe(discord_user="Discord user to reset")
async def hwid_reset(interaction: discord.Interaction, discord_user: discord.Member):
    if not owner_only(interaction):
        embed = discord.Embed(title="🚫 Access Denied", color=COLORS["error"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    await interaction.response.defer()
    discord_id = str(discord_user.id)
    lines, sha, content = get_github_file(GITHUB_FILE)
    new_lines = []
    found = False
    for line in lines:
        uid, date, rname, discord_str, note, expiry, uses, hwid = parse_entry(line)
        if discord_str == discord_id:
            found = True
            new_lines.append(f"{uid} | {date} | {rname} | {discord_str} | {note or 'none'} | {expiry or 'never'} | {uses} | none")
        else:
            new_lines.append(line)
    if not found:
        embed = discord.Embed(title="❌ Not Whitelisted", color=COLORS["error"])
        await interaction.followup.send(embed=embed)
        return
    update_github_file(GITHUB_FILE, "\n".join(new_lines), sha)
    reset_lines, reset_sha, _ = get_github_file(HWID_RESET_FILE)
    new_reset_lines = [l for l in reset_lines if not l.startswith(discord_id)]
    update_github_file(HWID_RESET_FILE, "\n".join(new_reset_lines), reset_sha)
    embed = discord.Embed(
        title="🔄 HWID Force Reset",
        description=f"**{discord_user.name}**'s HWID has been reset. Cooldown also cleared.",
        color=COLORS["success"]
    )
    embed.timestamp = datetime.utcnow()
    await interaction.followup.send(embed=embed)

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
    embed = discord.Embed(title=f"📋 {PROJECT_NAME} — Whitelist", color=COLORS["white"])
    if not entries:
        embed.description = "The whitelist is currently empty."
    else:
        desc = ""
        for line in entries:
            uid, date, roblox_name, discord_str, note, expiry, uses, hwid = parse_entry(line)
            name = roblox_name if roblox_name else uid
            discord_mention = f"<@{discord_str}>" if discord_str and discord_str != "none" else "No Discord"
            expired = is_expired(expiry)
            status = "⚠️" if expired else "✅"
            hwid_status = "🔒" if hwid and hwid != "none" else "🔓"
            expiry_text = expiry if expiry and expiry != "never" else "Never"
            desc += f"{status} **{name}** — {discord_mention} — {hwid_status} — Expires: {expiry_text}\n"
        embed.description = desc
    embed.add_field(name="✅ Whitelisted", value=str(len(entries)), inline=True)
    embed.add_field(name="🔨 Banned", value=str(len(ban_entries)), inline=True)
    embed.set_footer(text=f"{PROJECT_NAME} • Powered by GitHub")
    embed.timestamp = datetime.utcnow()
    await interaction.followup.send(embed=embed)

@tree.command(name="clear", description="Clear the entire whitelist")
async def clear_whitelist(interaction: discord.Interaction):
    if not owner_only(interaction):
        embed = discord.Embed(title="🚫 Access Denied", color=COLORS["error"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    confirm_embed = discord.Embed(title="⚠️ Confirm Clear", description="Clear the ENTIRE whitelist?", color=COLORS["warning"])

    async def do_clear(i: discord.Interaction):
        lines, sha, content = get_github_file(GITHUB_FILE)
        update_github_file(GITHUB_FILE, "", sha)
        result_embed = discord.Embed(title="🧹 Whitelist Cleared", color=COLORS["ban"])
        result_embed.timestamp = datetime.utcnow()
        await i.response.edit_message(embed=result_embed, view=None)
        await send_log(result_embed)

    view = ConfirmView(do_clear)
    await interaction.response.send_message(embed=confirm_embed, view=view)

@tree.command(name="genkey", description="Generate a whitelist key")
async def gen_key(interaction: discord.Interaction):
    if not owner_only(interaction):
        embed = discord.Embed(title="🚫 Access Denied", color=COLORS["error"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    embed = discord.Embed(
        title="🔑 Generate Key",
        description="Select how long this key should be valid:\n\n⚠️ Each key can only be used **once**.",
        color=COLORS["gold"]
    )
    embed.set_footer(text="Key sent to your DMs only")
    await interaction.response.send_message(embed=embed, view=GenerateKeyView(), ephemeral=True)

@tree.command(name="genkey_custom", description="Generate a key with custom hours")
@app_commands.describe(hours="Number of hours the key lasts")
async def gen_key_custom(interaction: discord.Interaction, hours: int):
    if not owner_only(interaction):
        embed = discord.Embed(title="🚫 Access Denied", color=COLORS["error"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    key = generate_key()
    date = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    expiry_dt = datetime.utcnow() + timedelta(hours=hours)
    expiry = expiry_dt.strftime("%Y-%m-%d %H:%M")
    key_lines, key_sha, key_content = get_github_file(KEY_FILE)
    new_entry = f"{key} | {date} | false | 1 | {expiry} | never"
    new_content = key_content.strip() + f"\n{new_entry}"
    update_github_file(KEY_FILE, new_content, key_sha)
    try:
        dm_embed = discord.Embed(title=f"🔑 {PROJECT_NAME} — Key Generated", color=COLORS["white"])
        dm_embed.add_field(name="🔑 Key", value=f"`{key}`", inline=False)
        dm_embed.add_field(name="Duration", value=f"{hours} hours", inline=True)
        dm_embed.add_field(name="Key Expires", value=expiry, inline=True)
        dm_embed.set_footer(text="⚠️ Single use only!")
        dm_embed.timestamp = datetime.utcnow()
        await interaction.user.send(embed=dm_embed)
        embed = discord.Embed(
            title="✅ Key Sent to DMs",
            description=f"A **{hours} hour** key has been sent to your DMs!",
            color=COLORS["success"]
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
    except:
        embed = discord.Embed(title="❌ DM Failed", color=COLORS["error"])
        await interaction.followup.send(embed=embed, ephemeral=True)

@tree.command(name="keylist", description="Show all generated keys")
async def key_list(interaction: discord.Interaction):
    if not owner_only(interaction):
        embed = discord.Embed(title="🚫 Access Denied", color=COLORS["error"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    key_lines, _, _ = get_github_file(KEY_FILE)
    if not key_lines:
        embed = discord.Embed(title="🔑 Keys", description="No keys.", color=COLORS["info"])
        await interaction.followup.send(embed=embed, ephemeral=True)
        return
    desc = ""
    for line in key_lines:
        k, date, used, max_uses, expiry, days = parse_key(line)
        status = "✅" if used == "false" else "❌"
        if is_expired(expiry):
            status = "⚠️"
        desc += f"{status} `{k}` — Expires: {expiry if expiry != 'never' else 'Never'}\n"
    embed = discord.Embed(title="🔑 All Keys", description=desc, color=COLORS["gold"])
    embed.add_field(name="Total", value=str(len(key_lines)), inline=True)
    embed.timestamp = datetime.utcnow()
    await interaction.followup.send(embed=embed, ephemeral=True)

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
    embed = discord.Embed(title="🗑️ Key Revoked", description=f"`{key_upper}` deleted.", color=COLORS["ban"])
    embed.timestamp = datetime.utcnow()
    await interaction.followup.send(embed=embed)

@tree.command(name="setscript", description="Set the script sent to whitelisted users")
@app_commands.describe(script="The script or loadstring URL")
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

@tree.command(name="setrole", description="Set the role for whitelisted users")
@app_commands.describe(role="The whitelist role")
async def set_role(interaction: discord.Interaction, role: discord.Role):
    if not owner_only(interaction):
        embed = discord.Embed(title="🚫 Access Denied", color=COLORS["error"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    global WHITELIST_ROLE_ID
    WHITELIST_ROLE_ID = role.id
    embed = discord.Embed(
        title="✅ Role Set",
        description=f"Whitelisted users will receive **{role.name}**.",
        color=COLORS["success"]
    )
    embed.timestamp = datetime.utcnow()
    await interaction.response.send_message(embed=embed)

@tree.command(name="setlog", description="Set this channel as the log channel")
async def set_log(interaction: discord.Interaction):
    if not owner_only(interaction):
        embed = discord.Embed(title="🚫 Access Denied", color=COLORS["error"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    global LOG_CHANNEL_ID
    LOG_CHANNEL_ID = interaction.channel_id
    embed = discord.Embed(title="📋 Log Channel Set", color=COLORS["success"])
    embed.timestamp = datetime.utcnow()
    await interaction.response.send_message(embed=embed)

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
    embed = discord.Embed(title="💾 Backup Created", description=f"Saved to `{backup_filename}`.", color=COLORS["success"])
    embed.add_field(name="Total Users", value=str(len(get_ids_only(lines))), inline=True)
    embed.timestamp = datetime.utcnow()
    await interaction.followup.send(embed=embed)

@tree.command(name="help", description="Show all commands")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title=f"📖 {PROJECT_NAME} — Commands", color=COLORS["white"])
    embed.add_field(name="👑 OWNER", value="\u200b", inline=False)
    embed.add_field(name="/add", value="➕ Add user", inline=True)
    embed.add_field(name="/remove", value="➖ Remove user", inline=True)
    embed.add_field(name="/ban", value="🔨 Ban user", inline=True)
    embed.add_field(name="/unban", value="✅ Unban user", inline=True)
    embed.add_field(name="/list", value="📋 List users", inline=True)
    embed.add_field(name="/clear", value="🧹 Clear all", inline=True)
    embed.add_field(name="/hwid_reset", value="🔄 Force reset HWID", inline=True)
    embed.add_field(name="/genkey", value="🔑 Generate key", inline=True)
    embed.add_field(name="/genkey_custom", value="🔑 Custom hours key", inline=True)
    embed.add_field(name="/keylist", value="🔑 List keys", inline=True)
    embed.add_field(name="/revokekey", value="🗑️ Delete key", inline=True)
    embed.add_field(name="/setscript", value="📜 Set script", inline=True)
    embed.add_field(name="/setrole", value="👑 Set role", inline=True)
    embed.add_field(name="/setlog", value="📋 Set log", inline=True)
    embed.add_field(name="/backup", value="💾 Backup", inline=True)
    embed.add_field(name="/panel", value="🎛️ Send panel", inline=True)
    embed.set_footer(text=f"{PROJECT_NAME} Whitelist")
    embed.timestamp = datetime.utcnow()
    await interaction.response.send_message(embed=embed)

print("Starting bot...")
client.run(TOKEN)
