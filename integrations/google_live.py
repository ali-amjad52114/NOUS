#!/usr/bin/env python3
"""Stream marked Gmail and Google Calendar items into NOUS + LaserData.

For a safe hackathon demo, only Gmail messages matching ``NOUS`` and calendar
events whose title contains ``NOUS`` are read. The first run opens Google's
OAuth consent page. OAuth tokens and message IDs stay under the ignored state/
directory and are never written to Git.
"""
from __future__ import annotations

import argparse
import getpass
from email.utils import parseaddr
import json
import os
from pathlib import Path
import sys
import time
from urllib.error import URLError
from urllib.request import Request, urlopen

from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from kit.feed import classify  # noqa: E402
from integrations.publish_laserdata_evidence import (  # noqa: E402
    CERTIFICATE,
    STATE,
    _publish,
)

PROJECT = Path(__file__).resolve().parent.parent
CLIENT_SECRET = Path(
    os.environ.get("GOOGLE_OAUTH_CLIENT", PROJECT / "client_secret.json")
).expanduser()
TOKEN = Path(os.environ.get("GOOGLE_TOKEN", STATE / "google_token.json")).expanduser()
SEEN = STATE / "google_seen.json"
OUTBOX = STATE / "google_live_events.json"
GMAIL_QUERY = os.environ.get("GOOGLE_GMAIL_QUERY", "newer_than:1d NOUS")
CALENDAR_MARKER = os.environ.get("GOOGLE_CALENDAR_MARKER", "NOUS").lower()
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
]


def _credentials() -> Credentials:
    creds = None
    if TOKEN.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(GoogleRequest())
    if not creds or not creds.valid:
        if not CLIENT_SECRET.is_file():
            raise FileNotFoundError(
                f"Google OAuth file not found: {CLIENT_SECRET}\n"
                "Download a Desktop OAuth client and save it as client_secret.json."
            )
        flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
        creds = flow.run_local_server(port=0, open_browser=True)
    STATE.mkdir(exist_ok=True)
    TOKEN.write_text(creds.to_json())
    TOKEN.chmod(0o600)
    return creds


def _header(headers: list[dict], name: str) -> str:
    name = name.lower()
    return next((h.get("value", "") for h in headers if h.get("name", "").lower() == name), "")


def _gmail_events(service) -> list[dict]:
    response = service.users().messages().list(
        userId="me", q=GMAIL_QUERY, maxResults=20
    ).execute()
    events = []
    for item in response.get("messages", []):
        message = service.users().messages().get(
            userId="me", id=item["id"], format="metadata",
            metadataHeaders=["From", "To", "Subject", "Date"],
        ).execute()
        headers = message.get("payload", {}).get("headers", [])
        outgoing = "SENT" in message.get("labelIds", [])
        from_name, from_email = parseaddr(_header(headers, "From"))
        to_name, to_email = parseaddr(_header(headers, "To"))
        person = (to_name or to_email) if outgoing else (from_name or from_email)
        event = {
            "id": f"gmail-{message['id']}",
            "external_id": message["id"],
            "type": "message_out" if outgoing else "message_in",
            "channel": "gmail",
            "source": "gmail-live",
            "from": from_email or _header(headers, "From"),
            "to": to_email or _header(headers, "To"),
            "person": person or "Unknown",
            "subject": _header(headers, "Subject"),
            "body": message.get("snippet", ""),
            "received_at": _header(headers, "Date"),
            "ts": int(message.get("internalDate", "0")) / 1000,
        }
        event["trigger_class"] = classify(event)
        events.append(event)
    return events


def _calendar_events(service) -> list[dict]:
    now = time.time()
    response = service.events().list(
        calendarId="primary",
        timeMin=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now - 86400)),
        timeMax=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now + 30 * 86400)),
        maxResults=50,
        singleEvents=True,
        orderBy="startTime",
    ).execute()
    events = []
    for item in response.get("items", []):
        summary = item.get("summary", "")
        if CALENDAR_MARKER not in summary.lower():
            continue
        event = {
            "id": f"gcal-{item['id']}",
            "external_id": item["id"],
            "type": "calendar_event",
            "channel": "google_calendar",
            "source": "google-calendar-live",
            "person": item.get("organizer", {}).get("displayName", "Calendar"),
            "subject": summary,
            "body": item.get("description", ""),
            "start": item.get("start", {}).get("dateTime", item.get("start", {}).get("date")),
            "end": item.get("end", {}).get("dateTime", item.get("end", {}).get("date")),
            "status": item.get("status"),
            "html_link": item.get("htmlLink"),
            "ts": time.time(),
            "trigger_class": "calendar_change",
        }
        events.append(event)
    return events


def _load_seen() -> set[str]:
    if not SEEN.exists():
        return set()
    try:
        return set(json.loads(SEEN.read_text()))
    except (ValueError, OSError):
        return set()


def _save_seen(seen: set[str]) -> None:
    SEEN.write_text(json.dumps(sorted(seen)))


def _send_to_nous(event: dict, api: str) -> None:
    request = Request(
        f"{api.rstrip('/')}/events",
        data=json.dumps(event).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=2) as response:
            result = json.loads(response.read())
        print(f"   brain: {result.get('status', 'accepted')}")
    except (URLError, TimeoutError, ValueError) as exc:
        print(f"   brain API unavailable ({type(exc).__name__}); LaserData still received it")


def _sync(gmail, calendar, password: str, seen: set[str], api: str) -> int:
    candidates = _gmail_events(gmail) + _calendar_events(calendar)
    fresh = [event for event in candidates if event["id"] not in seen]
    if not fresh:
        print("No new NOUS-marked Gmail or Calendar events.")
        return 0
    OUTBOX.write_text(json.dumps(fresh))
    if _publish(password, "life-events", OUTBOX, len(fresh)) != 0:
        print("LaserData publish failed; nothing marked as seen.")
        return 1
    for event in fresh:
        print(f"✅ {event['channel']}: {event['subject']} → LaserData nous/life-events")
        _send_to_nous(event, api)
        seen.add(event["id"])
    _save_seen(seen)
    print(f"Live Google sync complete: {len(fresh)} new event(s)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--watch", type=int, metavar="SECONDS", help="keep polling")
    parser.add_argument("--nous-api", default="http://127.0.0.1:7200")
    args = parser.parse_args()
    if not CERTIFICATE.is_file():
        print(f"LaserData certificate not found: {CERTIFICATE}")
        return 1
    try:
        creds = _credentials()
    except Exception as exc:
        print(f"Google setup failed: {exc}")
        return 1
    gmail = build("gmail", "v1", credentials=creds, cache_discovery=False)
    calendar = build("calendar", "v3", credentials=creds, cache_discovery=False)
    password = getpass.getpass("LaserData password (hidden): ")
    if not password:
        return 1
    seen = _load_seen()
    while True:
        if _sync(gmail, calendar, password, seen, args.nous_api) != 0:
            return 1
        if not args.watch:
            return 0
        print(f"Watching Google every {args.watch}s — Ctrl-C to stop")
        try:
            time.sleep(args.watch)
        except KeyboardInterrupt:
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
