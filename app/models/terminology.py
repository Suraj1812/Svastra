from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Term(Base):
    __tablename__ = "terms"

    concept_id = Column(String(64), primary_key=True)
    term = Column(String(255), nullable=False, unique=True, index=True)
    language = Column(String(16), nullable=False, default="en", index=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    tags = relationship("TermTag", back_populates="term_record", cascade="all, delete-orphan")


class TermTag(Base):
    __tablename__ = "term_tags"

    concept_id = Column(String(64), ForeignKey("terms.concept_id"), primary_key=True)
    tag = Column(String(32), primary_key=True, index=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    term_record = relationship("Term", back_populates="tags")
