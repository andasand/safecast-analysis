import os
from pathlib import Path
import requests

API_KEY = os.environ.get("SAFECAST_API_KEY")
BASE_URL = "https://api.safecast.org/en-US"
USER_ID = "11754"

if not API_KEY:
    raise SystemExit("SAFECAST_API_KEY not set")

DRIVES_DIR = Path("data/drives")
JOURNALS_DIR = Path("data/journals")


def api_get(path, params=None):
    params = params or {}
    params["api_key"] = API_KEY

    r = requests.get(
        f"{BASE_URL}{path}",
        params=params,
        timeout=60,
    )
    print("GET", r.url.replace(API_KEY, "***"))
    print("Status:", r.status_code)
    r.raise_for_status()
    return r.json()


def get_submitted_filenames():
    imports = api_get(
        "/bgeigie_imports.json",
        {
            "by_user_id": USER_ID,
            "format": "json",
        },
    )

    submitted = set()

    for item in imports:
        filename = item.get("filename") or item.get("name")

        if not filename and item.get("source"):
            url = item["source"].get("url", "")
            filename = url.split("/")[-1]

        if filename:
            submitted.add(filename)

    return submitted


def find_local_logs():
    logs = []

    for folder, kind in [(DRIVES_DIR, "drive"), (JOURNALS_DIR, "journal")]:
        if not folder.exists():
            continue

        for path in sorted(folder.glob("*.log")):
            logs.append(
                {
                    "path": path,
                    "filename": path.name,
                    "kind": kind,
                }
            )

    return logs


def upload_drive_log(path):
    data = {
        "api_key": API_KEY,
        "bgeigie_import[name]": path.name,
        "bgeigie_import[description]": "bGeigieZen walking survey from Andhra Pradesh.",
        "bgeigie_import[credits]": "Anand Sandhinti",
        "bgeigie_import[cities]": "Pulivendula, Andhra Pradesh, India",
        "bgeigie_import[orientation]": "Facing Up",
        "bgeigie_import[height]": "1.0",
    }

    with open(path, "rb") as f:
        files = {
            "bgeigie_import[source]": f,
        }

        r = requests.post(
            f"{BASE_URL}/bgeigie_imports.json",
            data=data,
            files=files,
            timeout=120,
        )

    print("POST", path)
    print("Status:", r.status_code)
    print(r.text[:1000])
    r.raise_for_status()


def main():
    submitted = get_submitted_filenames()
    print("\nAlready submitted:")
    for name in sorted(submitted):
        print("-", name)

    local_logs = find_local_logs()

    print("\nLocal logs:")
    for item in local_logs:
        status = "submitted" if item["filename"] in submitted else "not submitted"
        print(f"- {item['kind']}: {item['filename']} [{status}]")

    print("\nUploading unsubmitted drive logs only...")

    for item in local_logs:
        if item["kind"] != "drive":
            print(f"Skipping journal file: {item['filename']}")
            continue

        if item["filename"] in submitted:
            print(f"Skipping already submitted: {item['filename']}")
            continue

        upload_drive_log(item["path"])


if __name__ == "__main__":
    main()
