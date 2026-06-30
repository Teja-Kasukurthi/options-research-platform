#!/usr/bin/env python3
"""Create or update the admin user.

Usage:
    python scripts/seed_admin.py
    python scripts/seed_admin.py --email admin@example.com --password MySecurePass123

The script prints the bcrypt hash and upserts the user into the DB.
Also updates ADMIN_PASSWORD_HASH in .env if the file exists.
"""

import argparse
import asyncio
import getpass
import re
import sys
from pathlib import Path


def hash_password(password: str) -> str:
    import bcrypt
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def update_env_file(key: str, value: str) -> None:
    env_path = Path(".env")
    if not env_path.exists():
        return
    content = env_path.read_text()
    pattern = rf"^{re.escape(key)}=.*$"
    replacement = f"{key}={value}"
    if re.search(pattern, content, flags=re.MULTILINE):
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    else:
        content += f"\n{replacement}\n"
    env_path.write_text(content)
    print(f"Updated .env: {key}=<hash>")


async def upsert_user(email: str, password_hash: str) -> None:
    from app.core.db import AsyncSessionLocal
    from sqlalchemy import text

    async with AsyncSessionLocal() as db:
        await db.execute(
            text("""
                INSERT INTO admin_users (email, password_hash)
                VALUES (:email, :hash)
                ON CONFLICT (email) DO UPDATE SET password_hash = EXCLUDED.password_hash
            """),
            {"email": email, "hash": password_hash},
        )
        await db.commit()
    print(f"Admin user upserted: {email}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed admin user")
    parser.add_argument("--email", default=None)
    parser.add_argument("--password", default=None)
    parser.add_argument("--hash-only", action="store_true", help="Print hash only, skip DB insert")
    args = parser.parse_args()

    email = args.email or input("Admin email [admin@example.com]: ").strip() or "admin@example.com"
    password = args.password or getpass.getpass("Admin password: ")

    if len(password) < 8:
        print("ERROR: Password must be at least 8 characters", file=sys.stderr)
        sys.exit(1)

    password_hash = hash_password(password)
    print(f"\nBcrypt hash:\n{password_hash}\n")
    print("Paste this into .env as:")
    print(f"ADMIN_PASSWORD_HASH={password_hash}\n")

    update_env_file("ADMIN_PASSWORD_HASH", password_hash)
    update_env_file("ADMIN_EMAIL", email)

    if args.hash_only:
        return

    try:
        asyncio.run(upsert_user(email, password_hash))
    except Exception as e:
        print(f"DB insert skipped (run after `alembic upgrade head`): {e}")
        print("You can still paste the hash into .env manually.")


if __name__ == "__main__":
    main()
