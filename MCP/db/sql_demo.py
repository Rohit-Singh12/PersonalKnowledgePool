from db.database import engine, Base
import asyncio
from db.models.article import ArticleMetadata, ArticleType
from db.session import get_db

print(Base.metadata.tables.keys())

async def create_table():
    async with engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.create_all    
        )

async def add_article_type():
    async with get_db() as session:
        article_type = ArticleType(kind="AI & ML")
        
        session.add(article_type)
        
        await session.flush()
        await session.refresh(article_type)
        
        return article_type

async def add_links():
    async with get_db() as session:
        metadata = ArticleMetadata(article_type=1, link="link1")
        session.add(metadata)
        
        await session.flush()
        await session.refresh(metadata)
        return metadata

if __name__=="__main__":
    asyncio.run(add_links())

