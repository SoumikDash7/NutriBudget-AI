import asyncio
import asyncpg

DATABASE_URL = "postgresql://postgres.qrttlnofuiszohjlcufq:ReiSou300713@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres"


async def main():
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        print("✅ Connected successfully!")
        await conn.close()
    except Exception as e:
        print("❌", type(e).__name__)
        print(e)


asyncio.run(main())