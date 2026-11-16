import json
import re
import os
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

M3U = Path("toffee_playlist.m3u")
JSON_FILE = Path("toffee_data.json")

def parse_playlist():
    text = M3U.read_text(encoding="utf-8-sig")
    if not text.lstrip().startswith("#EXTM3U"):
        raise ValueError("Invalid M3U header")

    channels = []
    info = None

    for raw in text.splitlines():
        line = raw.strip()

        if line.startswith("#EXTINF:"):
            info = line
        elif line and not line.startswith("#") and info:
            name = info.split(",", 1)[-1].strip()

            def attr(key):
                match = re.search(
                    rf'{re.escape(key)}="([^"]*)"', info
                )
                return match.group(1) if match else ""

            channels.append({
                "category_name": attr("group-title"),
                "name": name,
                "link": line,
                "logo": attr("tvg-logo")
            })
            info = None

    if not channels:
        raise ValueError("No channels found")

    names = [c["name"] for c in channels]
    if len(names) != len(set(names)):
        raise ValueError("Duplicate channel names")

    return channels


def check_expiry(channels):
    now = datetime.now(timezone.utc).timestamp()
    expired, soon, unknown = [], [], []

    for channel in channels:
        match = re.search(r'Expires=(\d+)', channel["link"])

        if not match:
            unknown.append(channel["name"])
            continue

        expiry = int(match.group(1))

        if expiry <= now:
            expired.append(channel["name"])
        elif expiry - now <= 7200:
            soon.append(channel["name"])

    return expired, soon, unknown


def main():
    old = json.loads(JSON_FILE.read_text(encoding="utf-8"))

    if not isinstance(old.get("response"), list):
        raise ValueError("Invalid JSON schema")

    channels = parse_playlist()

    previous = {
        c["name"]: c for c in old["response"]
    }

    updated = []

    for channel in channels:
        old_channel = previous.get(channel["name"], {})

        updated.append({
            "category_name": (
                channel["category_name"]
                or old_channel.get("category_name", "")
            ),
            "name": channel["name"],
            "link": channel["link"],
            "headers": old_channel.get("headers", {}),
            "logo": (
                channel["logo"]
                or old_channel.get("logo", "")
            )
        })

    changed = updated != old["response"]

    if changed:
        old["response"] = updated
        old["channels_amount"] = len(updated)
        old["Last_update"] = datetime.now(
            ZoneInfo("Asia/Dhaka")
        ).strftime("%Y-%m-%d")

        JSON_FILE.write_text(
            json.dumps(old, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8"
        )

    expired, soon, unknown = check_expiry(channels)

    print(f"Channels: {len(channels)}")
    print(f"JSON changed: {changed}")
    print(f"Expired URLs: {len(expired)}")
    print(f"Expiring within 2 hours: {len(soon)}")
    print(f"Unknown expiry: {len(unknown)}")

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write("# Toffee Playlist Health Report\n\n")
            f.write(f"- Channels: {len(channels)}\n")
            f.write(f"- JSON changed: {changed}\n")
            f.write(f"- Expired URLs: {len(expired)}\n")
            f.write(f"- Expiring within 2 hours: {len(soon)}\n")
            f.write(f"- Unknown expiry: {len(unknown)}\n")

            if expired:
                f.write("\n## Expired channels\n")
                f.write("\n".join(f"- {n}" for n in expired))

            if soon:
                f.write("\n\n## Expiring soon\n")
                f.write("\n".join(f"- {n}" for n in soon))

    if expired:
        print("WARNING: Some signed URLs have expired.")

    print("Toffee sync completed.")


if __name__ == "__main__":
    main()
