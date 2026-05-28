import os
from pathlib import Path
import requests

API_KEY = os.environ.get("SAFECAST_API_KEY")
BASE_URL = "https://api.safecast.org/en-US"
USER_ID = "11754"

if not API_KEY:
    raise SystemExit("SAFECAST_API_KEY not set")

DRIVES_DIR = Path("data/drives")
DRIVES_CLEANED_DIR = Path("data/drives_cleaned")
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

    for folder, kind in [
        (DRIVES_DIR, "drive"),
        (JOURNALS_DIR, "journal"),
    ]:
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


def extract_device_id(path):
    """
    Extract bGeigie device ID from first $BNRDD line.
    Example:
    $BNRDD,5167,...
    """
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("$BNRDD"):
                parts = line.split(",")

                if len(parts) > 1:
                    return parts[1]

    return "unknown"


def is_invalid_bgeigie_line(line):
    """
    Strict QA removal for bGeigie measurement rows.

    Remove:
    - malformed $BNRDD rows
    - rows with 0000.0000 latitude or longitude
    - rows where measurement status is V

    In $BNRDD:
    parts[6] = measurement status
    parts[7] = latitude
    parts[9] = longitude
    """

    if not line.startswith("$BNRDD"):
        return False

    body = line.split("*", 1)[0]
    parts = body.split(",")

    if len(parts) < 14:
        return True

    measurement_status = parts[6]
    lat = parts[7]
    lon = parts[9]

    if measurement_status == "V":
        return True

    if lat == "0000.0000" or lon == "0000.0000":
        return True

    return False


def clean_drive_log(path):
    DRIVES_CLEANED_DIR.mkdir(parents=True, exist_ok=True)

    cleaned_path = DRIVES_CLEANED_DIR / path.name

    kept = 0
    removed = 0

    with open(path, "r", encoding="utf-8", errors="replace") as src, open(
        cleaned_path,
        "w",
        encoding="utf-8",
    ) as dst:

        for line in src:
            stripped = line.strip()

            if is_invalid_bgeigie_line(stripped):
                removed += 1
                continue

            dst.write(line)

            if stripped.startswith("$BNRDD"):
                kept += 1

    print(f"Cleaned {path.name}: kept {kept}, removed {removed}")

    return cleaned_path, kept, removed


def upload_drive_log(path):
    device_id = extract_device_id(path)

    data = {
        "api_key": API_KEY,
        "bgeigie_import[name]": path.name,
        "bgeigie_import[description]":
            f"bGeigie #{device_id} walking survey in Pulivendula, Andhra Pradesh.",
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
        status = (
            "submitted"
            if item["filename"] in submitted
            else "not submitted"
        )

        print(f"- {item['kind']}: {item['filename']} [{status}]")

    print("\nCleaning and uploading unsubmitted drive logs only...")

    for item in local_logs:
        if item["kind"] != "drive":
            print(f"Skipping journal file: {item['filename']}")
            continue

        if item["filename"] in submitted:
            print(f"Skipping already submitted: {item['filename']}")
            continue

        cleaned_path, kept, removed = clean_drive_log(item["path"])

        if kept == 0:
            print(
                f"Skipping upload: no valid GPS measurements "
                f"in {item['filename']}"
            )
            continue

        upload_drive_log(cleaned_path)


if __name__ == "__main__":
    main()
