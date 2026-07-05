from contextlib import asynccontextmanager
from db.database import AsyncSessionLocal

@asynccontextmanager
async def get_db():
    session = AsyncSessionLocal()
    
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()