#!/usr/bin/env python3
"""Find LaserData deployment + Iggy credentials using .env API key.

Reads LASERDATA_API_KEY and LASERDATA_TENANT_ID from .env (gitignored).
Does not print the API key. Prints host/username and writes LASERDATA_URL
back into .env when credentials are found.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"
API = "https://api.laserdata.cloud"


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def save_env(path: Path, values: dict[str, str]) -> None:
    existing = load_env(path)
    existing.update(values)
    lines = [f"{k}={v}" for k, v in existing.items()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def get_json(url: str, api_key: str) -> dict | list:
    # Cloudflare Error 1010 bans Python-urllib's default User-Agent.
    req = urllib.request.Request(
        url,
        headers={
            "ld-api-key": api_key,
            "Accept": "application/json",
            "User-Agent": "curl/8.4.0",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            return json.loads(response.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} for {url}\n{body[:800]}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Network error for {url}: {exc}") from exc


def items_of(payload: dict | list) -> list:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        value = payload.get("items")
        if isinstance(value, list):
            return value
    return []


def main() -> int:
    env = load_env(ENV_PATH)
    api_key = env.get("LASERDATA_API_KEY") or os.environ.get("LASERDATA_API_KEY")
    tenant = (
        env.get("LASERDATA_TENANT_ID")
        or os.environ.get("LASERDATA_TENANT_ID")
        or "631246688891175252"
    )
    if not api_key:
        print("Missing LASERDATA_API_KEY in .env")
        return 1

    print(f"tenant={tenant}")
    print(f"api_key_len={len(api_key)} (value hidden)")

    context = get_json(f"{API}/tenants/{tenant}/api_keys/context", api_key)
    print("context_ok=true")
    print(json.dumps(context, indent=2)[:1200])

    divisions = items_of(get_json(f"{API}/tenants/{tenant}/divisions?results=100", api_key))
    print(f"divisions={len(divisions)}")
    found = None

    for division in divisions:
        did = division.get("id")
        print(f"\ndivision id={did} name={division.get('name')}")
        environments = items_of(
            get_json(f"{API}/tenants/{tenant}/divisions/{did}/environments?results=100", api_key)
        )
        for environment in environments:
            eid = environment.get("id")
            print(f"  environment id={eid} name={environment.get('name')}")
            deployments = items_of(
                get_json(
                    f"{API}/tenants/{tenant}/divisions/{did}/environments/{eid}/deployments?results=100",
                    api_key,
                )
            )
            for deployment in deployments:
                dep_id = deployment.get("id")
                host = (
                    deployment.get("subdomain")
                    or deployment.get("hostname")
                    or deployment.get("endpoint")
                    or deployment.get("host")
                )
                supervisor = deployment.get("supervisor_url") or deployment.get("supervisor")
                status = deployment.get("status") or deployment.get("state")
                print(
                    f"    deployment id={dep_id} status={status} host={host} "
                    f"supervisor={supervisor}"
                )
                print(f"    raw_keys={sorted(deployment.keys())}")
                if dep_id and supervisor:
                    found = {
                        "division_id": did,
                        "environment_id": eid,
                        "deployment_id": dep_id,
                        "host": host,
                        "supervisor_url": str(supervisor).rstrip("/"),
                        "deployment": deployment,
                    }

    if not found:
        print("\nNo deployment with supervisor_url found.")
        print("Create/open a starter deployment in the LaserData console, then re-run.")
        return 2

    cred_url = f"{found['supervisor_url']}/deployments/{found['deployment_id']}/credentials"
    print(f"\nFetching credentials from supervisor for deployment {found['deployment_id']}")
    creds = get_json(cred_url, api_key)
    username = creds.get("username") or creds.get("user")
    password = creds.get("password")
    print(f"username_present={bool(username)} password_present={bool(password)}")

    host = found["host"] or env.get("LASERDATA_HOST")
    if not host or not username or not password:
        print("Incomplete credentials/host.")
        print("cred_keys=" + ",".join(sorted(str(k) for k in creds.keys() if k != "password")))
        return 3

    # Common LaserData/Iggy ports: 8090 TCP. Prefer host as returned by API.
    host = str(host).removeprefix("https://").removeprefix("http://").split("/")[0]
    port = env.get("LASERDATA_PORT", "8090")
    user_q = urllib.parse.quote(str(username), safe="")
    pass_q = urllib.parse.quote(str(password), safe="")
    laserdata_url = f"iggy://{user_q}:{pass_q}@{host}:{port}"

    save_env(
        ENV_PATH,
        {
            "LASERDATA_API_KEY": api_key,
            "LASERDATA_TENANT_ID": tenant,
            "LASERDATA_HOST": host,
            "LASERDATA_PORT": port,
            "LASERDATA_STREAM": env.get("LASERDATA_STREAM", "nous"),
            "LASERDATA_URL": laserdata_url,
            "LASERDATA_DIVISION_ID": str(found["division_id"]),
            "LASERDATA_ENVIRONMENT_ID": str(found["environment_id"]),
            "LASERDATA_DEPLOYMENT_ID": str(found["deployment_id"]),
        },
    )
    print("\nWrote LASERDATA_URL to .env (value not printed; gitignored).")
    print(f"host={host} port={port} stream=nous")
    print("Next: python integrations/laserdata_smoke.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
