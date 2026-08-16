"""One-off migration: create schema, create the owner account, and move
existing flat-file client data into the database under that account.

Usage: MIGRATE_EMAIL=... MIGRATE_PASSWORD=... venv/bin/python migrate.py
"""
import json
import os
import sys

from app import app
from models import Client, User, db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENTS_PATH = os.path.join(BASE_DIR, "data", "clients.json")
DEFAULT_OPTIONS_PATH = os.path.join(BASE_DIR, "default_options.json")


def main():
    email = os.environ.get("MIGRATE_EMAIL", "").strip().lower()
    password = os.environ.get("MIGRATE_PASSWORD", "")
    if not email or not password:
        print("Set MIGRATE_EMAIL and MIGRATE_PASSWORD environment variables.")
        sys.exit(1)

    with app.app_context():
        db.create_all()

        existing = User.query.filter_by(email=email).first()
        if existing:
            print(f"User {email} already exists (id={existing.id}); reusing it.")
            user = existing
        else:
            with open(DEFAULT_OPTIONS_PATH) as f:
                options_text = f.read()
            user = User(email=email, practice_name="", options_json=options_text)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            print(f"Created user {email} (id={user.id}).")

        if not os.path.exists(CLIENTS_PATH):
            print("No data/clients.json found; nothing to migrate.")
            return

        with open(CLIENTS_PATH) as f:
            old_clients = json.load(f)

        migrated = 0
        for c in old_clients:
            if Client.query.filter_by(id=c["id"]).first():
                print(f"  Client {c['id']} ({c.get('name')}) already migrated, skipping.")
                continue
            client = Client(
                id=c["id"],
                user_id=user.id,
                name=c.get("name", ""),
                dob=c.get("dob", ""),
                diagnosis=c.get("diagnosis", ""),
                guardian_name=c.get("guardian_name", ""),
                guardian_relationship=c.get("guardian_relationship", ""),
                rbt_name=c.get("rbt_name", ""),
                replacement_programs=c.get("replacement_programs") or [],
                maladaptive_behaviors=c.get("maladaptive_behaviors") or [],
            )
            db.session.add(client)
            migrated += 1

        db.session.commit()
        print(f"Migrated {migrated} client(s) into user {email} (id={user.id}).")


if __name__ == "__main__":
    main()
