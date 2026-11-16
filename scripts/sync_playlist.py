import json
import re
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

M3U_FILE = Path("toffee_playlist.m3u")
JSON_FILE = Path("toffee_data.json")

def parse_m3u():
    content = M3U_FILE.read_text(encoding="utf-8-sig")
    lines = content.splitlines()

    if not content.lstrip().startswith("#EXTM3U"):
        raise ValueError("Invalid M3U file")

    channels = []
    info = None

    for line in lines:
        line = line.strip()

        if line.startswith("#EXTINF:"):
            info = line

        elif line and not line.startswith("#") and info:
            name = info.split(",", 1)[-1].strip()

            category = re.search(
                r'group-title="([^"]*)"', info
            )
            logo = re.search(
                r'tvg-logo="([^"]*)"', info
            )

            channels.append({
                "category_name": category.group(1) if category else "",
                "name": name,
                "link": line,
                "logo": logo.group(1) if logo else ""
            })
            info = None

    if not channels:
        raise ValueError("No channels found")

    if len({c["name"] for c in channels}) != len(channels):
        raise ValueError("Duplicate channel names found")

    return channels


def main():
    old = json.loads(JSON_FILE.read_text(encoding="utf-8"))

    if not isinstance(old.get("response"), list):
        raise ValueError("Invalid existing JSON schema")

    old_channels = {
        c["name"]: c for c in old["response"]
    }

    new_channels = []

    for channel in parse_m3u():
        previous = old_channels.get(channel["name"], {})

        new_channels.append({
            "category_name": channel["category_name"],
            "name": channel["name"],
            "link": channel["link"],
            "headers": previous.get("headers", {}),
            "logo": channel["logo"]
        })

    old["channels_amount"] = len(new_channels)
    old["Last_update"] = datetime.now(
        ZoneInfo("Asia/Dhaka")
    ).strftime("%Y-%m-%d")
    old["response"] = new_channels

    JSON_FILE.write_text(
        json.dumps(old, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )

    print(f"Successfully synced {len(new_channels)} channels")


if __name__ == "__main__":
    main()
