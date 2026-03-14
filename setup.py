#!/usr/bin/env python3
"""Kiro Gateway interactive setup CLI."""
import secrets
import sys
from pathlib import Path

import questionary

ENV_FILE = Path(".env")

AWS_REGIONS = [
    "us-east-1       (US East - N. Virginia)",
    "us-east-2       (US East - Ohio)",
    "us-west-1       (US West - N. California)",
    "us-west-2       (US West - Oregon)",
    "ap-south-1      (Asia Pacific - Mumbai)",
    "ap-northeast-3  (Asia Pacific - Osaka)",
    "ap-northeast-2  (Asia Pacific - Seoul)",
    "ap-southeast-1  (Asia Pacific - Singapore)",
    "ap-southeast-2  (Asia Pacific - Sydney)",
    "ap-northeast-1  (Asia Pacific - Tokyo)",
    "ca-central-1    (Canada - Central)",
    "eu-central-1    (Europe - Frankfurt)",
    "eu-west-1       (Europe - Ireland)",
    "eu-west-2       (Europe - London)",
    "eu-west-3       (Europe - Paris)",
    "eu-north-1      (Europe - Stockholm)",
    "sa-east-1       (South America - São Paulo)",
    "us-gov-east-1   (AWS GovCloud - US-East)",
    "us-gov-west-1   (AWS GovCloud - US-West)",
]


def _region_id(choice: str) -> str:
    return choice.split()[0]


def _upsert_env(var: str, value: str) -> None:
    lines = ENV_FILE.read_text().splitlines(keepends=True) if ENV_FILE.exists() else []
    prefix = f"{var}="
    replaced = False
    for i, line in enumerate(lines):
        if line.startswith(prefix):
            lines[i] = f"{prefix}{value}\n"
            replaced = True
            break
    if not replaced:
        lines.append(f"{prefix}{value}\n")
    ENV_FILE.write_text("".join(lines))


def cmd_generate_key() -> None:
    key = f"sk-{secrets.token_hex(32)}"
    print(f"\nGenerated key:\n  {key}\n")

    save = questionary.confirm("Save to .env as PROXY_API_KEY?", default=False).ask()
    if save is None:
        sys.exit(0)
    if save:
        _upsert_env("PROXY_API_KEY", key)
        print("Saved. Restart the server for the new key to take effect.")


def cmd_nginx_config() -> None:
    domain = questionary.text("Domain name (e.g. api.example.com):").ask()
    if not domain:
        sys.exit(0)
    domain = domain.strip()

    config = f"""\
server {{
    listen 80;
    listen [::]:80;
    server_name {domain};
    return 301 https://$host$request_uri;
}}

server {{
    listen 443 ssl;
    listen [::]:443 ssl;
    server_name {domain};

    # Run: certbot --nginx -d {domain}
    ssl_certificate     /etc/letsencrypt/live/{domain}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{domain}/privkey.pem;
    include             /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam         /etc/letsencrypt/ssl-dhparams.pem;

    location / {{
        proxy_pass         http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_buffering    off;   # Required for LLM SSE streaming
        proxy_cache        off;
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_set_header   Connection        "";
    }}
}}"""

    out_file = questionary.text(
        "Save to file? (leave blank to print to stdout):"
    ).ask()
    if out_file is None:
        sys.exit(0)

    if out_file.strip():
        Path(out_file.strip()).write_text(config + "\n")
        print(f"Written to {out_file.strip()}")
    else:
        print(f"\n{config}\n")


def cmd_set_region() -> None:
    choice = questionary.select(
        "Select AWS region for Kiro API:",
        choices=AWS_REGIONS,
    ).ask()
    if choice is None:
        sys.exit(0)

    region = _region_id(choice)
    save = questionary.confirm(f"Save KIRO_REGION={region} to .env?", default=True).ask()
    if save is None:
        sys.exit(0)
    if save:
        _upsert_env("KIRO_REGION", region)
        print(f"Saved KIRO_REGION={region}")
    else:
        print(f"KIRO_REGION={region}")


COMMANDS = {
    "Generate API key": cmd_generate_key,
    "Set AWS region": cmd_set_region,
    "Generate nginx config (optional)": cmd_nginx_config,
}


def main() -> None:
    print("Kiro Gateway Setup\n")
    choice = questionary.select(
        "What would you like to do?",
        choices=list(COMMANDS.keys()),
    ).ask()
    if choice is None:
        sys.exit(0)
    COMMANDS[choice]()


if __name__ == "__main__":
    main()
