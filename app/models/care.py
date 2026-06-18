from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class CarePlan(Base):
    __tablename__ = "care_plans"
    __table_args__ = (
        CheckConstraint("status in ('DRAFT', 'ACTIVE')", name="ck_care_plans_status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(160), nullable=False)
    diagnosis = Column(String(255), nullable=True)
    status = Column(String(20), nullable=False, default="DRAFT", index=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    provider = relationship("User", foreign_keys=[provider_id])
    patient = relationship("User", foreign_keys=[patient_id])
    advisories = relationship("Advisory", back_populates="care_plan", cascade="all, delete-orphan")


class Advisory(Base):
    __tablename__ = "advisories"
    __table_args__ = (
        CheckConstraint(
            "advisory_type in ('medication', 'measurement', 'recommendation', 'investigation')",
            name="ck_advisories_type",
        ),
        CheckConstraint("status in ('DRAFT', 'PUBLISHED')", name="ck_advisories_status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    care_plan_id = Column(Integer, ForeignKey("care_plans.id"), nullable=False, index=True)
    provider_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    advisory_type = Column(String(32), nullable=False, index=True)
    concept_id = Column(String(64), nullable=False, index=True)
    term = Column(String(255), nullable=False)
    tag = Column(String(32), nullable=False)
    configuration_json = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="DRAFT", index=True)
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    care_plan = relationship("CarePlan", back_populates="advisories")
    provider = relationship("User", foreign_keys=[provider_id])
    patient = relationship("User", foreign_keys=[patient_id])
