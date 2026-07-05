from db.database import Base

from sqlalchemy.orm import Mapped, mapped_column, relationship, deferred
from sqlalchemy import ForeignKey, String, Text


class ArticleType(Base):
    __tablename__ = "article_type"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=True)
    
    links: Mapped[list["ArticleMetadata"]] = relationship(back_populates="article")
    

class ArticleMetadata(Base):
    __tablename__ = "articlemetadata"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    article_type: Mapped[int] = mapped_column(ForeignKey("article_type.id"))
    link: Mapped[str] = mapped_column(String(255), nullable=False)
    snippet: Mapped[str] = mapped_column(String(1000), nullable=True)
    is_populated: Mapped[bool] = mapped_column(default=False, nullable=True)
    
    article: Mapped["ArticleType"] = relationship(back_populates="links")
    
class ArticleDetails(Base):
    __tablename__ = "article_details"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    metadata_id: Mapped[int] = mapped_column(ForeignKey("articlemetadata.id"))
    content: Mapped[str] = deferred(mapped_column(Text, nullable=False))
    