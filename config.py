"""
config.py — Loads environment variables and initialises the Supabase client.
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise EnvironmentError(
        "\n[ERROR] SUPABASE_URL and SUPABASE_KEY are not set.\n"
        "  1. Copy .env.example to .env\n"
        "  2. Fill in your Supabase project URL and API key.\n"
    )

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
