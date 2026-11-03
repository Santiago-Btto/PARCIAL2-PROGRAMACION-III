import asyncio
import os

os.environ.setdefault("POSTGRES_USER", "postgres")
os.environ.setdefault("POSTGRES_PASSWORD", "testpass")
os.environ.setdefault("POSTGRES_DB", "libreria")
os.environ.setdefault("JWT_SECRET_KEY", "test_secret_key_de_al_menos_32_bytes_123456789")
os.environ.setdefault("BCRYPT_ROUNDS", "4")


async def _fake_to_thread(func, /, *args, **kwargs):
    return func(*args, **kwargs)


asyncio.to_thread = _fake_to_thread
