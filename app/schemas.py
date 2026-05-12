from pydantic import BaseModel, EmailStr, ConfigDict, Field
from typing import List, Optional

# Схемы нужны для того, чтобы FastAPI мог преобразовывать данные в JSON для отправки юзеру и обратно, имея объект из БД
# То есть валидация входящих и исходящих данных

class ProductCountBase(BaseModel):
    name: str
    count: int

class ProductCount(ProductCountBase):
    id: int
    user_id: int
    model_config = ConfigDict(
        from_attributes=True,  # чтобы использовать атрибуты модели SQLAlchemy, а не через ключ как в словарях
        populate_by_name=True
    )

class UserBase(BaseModel):
    email: EmailStr

class UserLogin(UserBase):
    password: str

class UserCreate(UserLogin):
    name: str

class User(UserBase):
    id: int
    products: list[ProductCount] = []
    model_config = ConfigDict(from_attributes=True)

class RecipeResponse(BaseModel):
    recipes: List[str]

class TaskBase(BaseModel):
    task_id: str

class TaskResponse(TaskBase):
    status: str
    counts: Optional[dict] = None