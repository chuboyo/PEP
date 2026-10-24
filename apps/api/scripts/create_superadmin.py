"""One-shot Superadmin seed for environments that disable startup seeding.

Examples:
  docker compose run --rm api python -m scripts.create_superadmin
  docker compose run --rm -e SUPERADMIN_PASSWORD='your-strong-password' api \\
    python -m scripts.create_superadmin --email admin@example.com
"""

from __future__ import annotations

import argparse
import getpass
import sys

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.seed import SeedError, create_superadmin

_PUBLISHED_DEFAULT_PASSWORD = "changeme-superadmin"


def _resolve_password(cli_password: str | None, settings_password: str) -> str:
    if cli_password is not None:
        return cli_password
    if settings_password and settings_password != _PUBLISHED_DEFAULT_PASSWORD:
        return settings_password

    password = getpass.getpass("Superadmin password: ")
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        raise SeedError("Passwords do not match.")
    return password


def main(argv: list[str] | None = None) -> int:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Create the platform Superadmin once.")
    parser.add_argument(
        "--email",
        default=settings.superadmin_email,
        help="Superadmin email (default: SUPERADMIN_EMAIL / settings)",
    )
    parser.add_argument(
        "--password",
        default=None,
        help="Password (prefer omit and type interactively, or set SUPERADMIN_PASSWORD)",
    )
    args = parser.parse_args(argv)

    try:
        password = _resolve_password(args.password, settings.superadmin_password)
        db = SessionLocal()
        try:
            create_superadmin(db, email=args.email, password=password)
        finally:
            db.close()
    except SeedError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Created Superadmin {args.email}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
