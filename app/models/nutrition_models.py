from sqlalchemy import (
    Column,
    Integer,
    Float,
    String,
    DateTime,
    ForeignKey,
    Enum as SQLEnum,
    Text,
)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from sqlalchemy.sql import text
from app.database.database import Base
from app.models.meal_models import GICategory, Level
# Remove the direct import of User and WeixinUser to break the circular dependency
# from app.models.user_models import User, WeixinUser


class NutritionRecord(Base):
    __tablename__ = "nutrition_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    weixin_user_id = Column(Integer, ForeignKey("weixin_users.id"), nullable=True)
    meal_type = Column(String(50), nullable=True)
    meal_time = Column(DateTime(timezone=True), nullable=True)
    pre_glucose = Column(Float, nullable=True)
    post_glucose = Column(Float, nullable=True)
    notes = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)
    total_carbs = Column(Float)
    total_protein = Column(Float)
    total_fat = Column(Float)
    total_gl = Column(Float)
    meal_gl_category = Column(String(50))
    impact_level = Column(String(50))
    protein_level = Column(String(50))
    fat_level = Column(String(50))
    protein_explanation = Column(Text)
    fat_explanation = Column(Text)
    impact_explanation = Column(Text)
    best_time = Column(Text)
    image_url = Column(String(255))

    # Use string references for relationships to avoid circular imports
    user = relationship("User", back_populates="nutrition_records")
    weixin_user = relationship("WeixinUser", back_populates="nutrition_records")
    ingredients = relationship(
        "Ingredient", back_populates="nutrition_record", cascade="all, delete-orphan"
    )

    def __init__(self, **kwargs):
        now = datetime.now(timezone.utc)
        kwargs.setdefault("created_at", now)
        kwargs.setdefault("updated_at", now)
        super().__init__(**kwargs)


class Ingredient(Base):
    __tablename__ = "ingredients"

    id = Column(Integer, primary_key=True, index=True)
    nutrition_record_id = Column(
        Integer, ForeignKey("nutrition_records.id"), nullable=False
    )
    name = Column(String(100), nullable=False)
    carbs_per_100g = Column(Float, nullable=True)
    protein_per_100g = Column(Float, nullable=True)
    fat_per_100g = Column(Float, nullable=True)
    gi = Column(Float, nullable=True)
    gl = Column(Float, nullable=True)
    gi_category = Column(String(50), nullable=True)
    portion = Column(Float, nullable=True)
    nutrition_record = relationship("NutritionRecord", back_populates="ingredients")
