from flask import Flask, request, jsonify
import requests
import base64
import json
import os
from datetime import datetime

app = Flask(__name__)

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = "ALI2023KING/Whitlist-sys"
WHITELIST_FILE = "whitelist.txt"
API_SECRET = os.environ.get("API_SECRET")

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

def parse_entry(line):
    parts = line.split("|")
    return [p.strip() for p in parts]

@app.route("/verify", methods=["POST"])
def verify():
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "No data"}), 400
    secret = data.get("secret")
    if secret != API_SECRET:
        return jsonify({"status": "error", "message": "Invalid secret"}), 403
    roblox_id = str(data.get("roblox_id"))
    hwid = data.get("hwid")
    lines, sha, content = get_github_file(WHITELIST_FILE)
    new_lines = []
    found = False
    result = {}
    for line in lines:
        if line.startswith("--"):
            new_lines.append(line)
            continue
        parts = parse_entry(line)
        if len(parts) < 1:
            new_lines.append(line)
            continue
        if parts[0] == roblox_id:
            found = True
            expiry = parts[5] if len(parts) > 5 else "never"
            if expiry and expiry != "never" and expiry != "":
                try:
                    expiry_dt = datetime.strptime(expiry, "%Y-%m-%d %H:%M")
                    if datetime.utcnow() > expiry_dt:
                        result = {"status": "expired"}
                        new_lines.append(line)
                        continue
                except:
                    pass
            stored_hwid = parts[7] if len(parts) > 7 else "none"
            script_key = parts[8] if len(parts) > 8 else "none"
            uses = parts[6] if len(parts) > 6 else "0"
            date = parts[1] if len(parts) > 1 else ""
            roblox_name = parts[2] if len(parts) > 2 else ""
            discord_str = parts[3] if len(parts) > 3 else "none"
            note = parts[4] if len(parts) > 4 else "none"
            if stored_hwid != "none" and stored_hwid != "" and stored_hwid != hwid:
                result = {"status": "hwid_mismatch"}
                new_lines.append(line)
                continue
            if stored_hwid == "none" or stored_hwid == "":
                stored_hwid = hwid
            try:
                uses = str(int(uses) + 1)
            except:
                uses = "1"
            last_seen = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
            new_line = f"{roblox_id} | {date} | {roblox_name} | {discord_str} | {note} | {expiry} | {uses} | {stored_hwid} | {script_key} | {last_seen}"
            new_lines.append(new_line)
            result = {
                "status": "ok",
                "script_key": script_key,
                "uses": uses,
                "expiry": expiry
            }
        else:
            new_lines.append(line)
    if not found:
        return jsonify({"status": "not_whitelisted"}), 403
    update_github_file(WHITELIST_FILE, "\n".join(new_lines), sha)
    return jsonify(result)

@app.route("/ping", methods=["GET"])
def ping():
    return jsonify({"status": "online"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
