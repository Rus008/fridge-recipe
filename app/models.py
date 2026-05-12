# app/models.py
from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)

    # Связи
    products = relationship("Product", back_populates="user", lazy="selectin")
    recipes = relationship("Recipe", back_populates="user", lazy="selectin")


class Product(Base):
    __tablename__ = "fridge_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False, default="uncategorized", server_default="uncategorized")  # uncategorized, dairy, meat, vegetables, etc.
    count = Column(Integer, default=1)
    confidence = Column(Float, default=0.0)
    detection_date = Column(DateTime(timezone=True), server_default=func.now())
    expiry_date = Column(DateTime(timezone=True))

    # Связи
    user = relationship("User", back_populates="products", lazy="selectin")


class Recipe(Base): # todo: надо ли хранить рецепты в БД?
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    ingredients = Column(Text, nullable=False)  # JSON string
    instructions = Column(Text, nullable=False)
    cooking_time = Column(Integer)  # в минутах
    difficulty = Column(String(20))  # easy, medium, hard
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Связи
    user = relationship("User", back_populates="recipes")


class DetectionHistory(Base): # todo: надо ли хранить историю детекций в БД?
    __tablename__ = "detection_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    image_path = Column(String(255), nullable=False)
    detected_items = Column(Text, nullable=False)  # JSON string
    confidence_avg = Column(Float, default=0.0)
    processing_time = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


