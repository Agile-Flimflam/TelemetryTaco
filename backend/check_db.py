#!/usr/bin/env python3
"""
Quick script to check database connectivity.
Run this to diagnose database connection issues.
"""

import os
import sys

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(__file__))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "telemetry_taco.settings")

try:
    import django

    django.setup()

    from django.db import connection

    print("Attempting to connect to database...")
    print(f"Database config: {connection.settings_dict['NAME']}")
    print(f"User: {connection.settings_dict['USER']}")
    print(f"Host: {connection.settings_dict['HOST']}")
    print(f"Port: {connection.settings_dict['PORT']}")

    with connection.cursor() as cursor:
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print("\n✅ Successfully connected to PostgreSQL!")
        print(f"PostgreSQL version: {version[0]}")

except Exception as e:
    print("\n❌ Failed to connect to database:")
    print(f"Error: {e}")
    print("\nTroubleshooting steps:")
    print("1. Make sure Docker PostgreSQL is running: docker-compose up -d db")
    print("2. Wait 5-10 seconds for PostgreSQL to initialize")
    print("3. Check if local PostgreSQL is running: ps aux | grep postgres")
    print(
        "4. If local PostgreSQL is running, either stop it or update .env with correct credentials"
    )
    sys.exit(1)
