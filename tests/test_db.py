"""Quick test: raw asyncpg connection to Neon.tech."""
import asyncio
import ssl
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import asyncpg

from app.config import settings


async def test():
    parsed = urlparse(settings.DATABASE_URL)
    clean_dsn = settings.DATABASE_URL.split("?", 1)[0]
    if clean_dsn.startswith("postgresql+asyncpg://"):
        clean_dsn = clean_dsn.replace("postgresql+asyncpg://", "postgresql://", 1)

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    print("Connecting to Neon.tech...")
    print(f"Host: {parsed.hostname}")
    print("Testing connection with extended timeout...")

    try:
        conn = await asyncpg.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            user=parsed.username,
            password=parsed.password,
            database=parsed.path.lstrip("/"),
            ssl=ctx,
            timeout=120,
            command_timeout=120,
        )
        result = await conn.fetchval("SELECT 1")
        print(f"[OK] Connected! Result: {result}")
        await conn.close()
    except asyncio.TimeoutError:
        print("[FAIL] Connection timeout - possible network/firewall issue")
        print("Trying alternative connection method...")

        try:
            conn = await asyncpg.connect(clean_dsn, timeout=120)
            result = await conn.fetchval("SELECT 1")
            print(f"[OK] Connected with alternative method! Result: {result}")
            await conn.close()
        except Exception as e2:
            print(f"[FAIL] Alternative method also failed: {type(e2).__name__}: {e2}")
    except Exception as e:
        print(f"[FAIL] Connection failed: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


asyncio.run(test())

