from fastapi import FastAPI, Depends, UploadFile, File, HTTPException, Query
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app import models, schemas, detection_qwen as detection, recipes
from app.database import get_async_db, async_engine, Base
from starlette.concurrency import run_in_threadpool
from contextlib import asynccontextmanager
import io
import uuid
from PIL import Image

_completed_tasks: dict = {}


class DetectionMode(str, Enum):
    UPDATE = "update"
    ADD = "add"


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(lifespan=lifespan, title="Fridge Assistant API")


@app.get("/users/auto", response_model=schemas.User)
async def auto_login(db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(models.User).filter(models.User.email == "guest@fridge.app"))
    user = result.scalar_one_or_none()
    if not user:
        from passlib.context import CryptContext
        pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
        user = models.User(name="Guest", email="guest@fridge.app", password_hash=pwd.hash("guest"))
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user


@app.post("/users/{user_id}/detect", response_model=schemas.TaskBase)
async def detect_products(
    user_id: int,
    mode: DetectionMode = Query(DetectionMode.UPDATE),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_async_db),
):
    user = await db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    img_bytes = await file.read()
    image = Image.open(io.BytesIO(img_bytes)).convert("RGB")

    try:
        counts = await run_in_threadpool(detection.detect_products, image)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Detection error: {e}")

    if mode == DetectionMode.UPDATE:
        await db.execute(delete(models.Product).where(models.Product.user_id == user_id))

    for name, cnt in counts.items():
        db.add(models.Product(user_id=user_id, name=name, count=cnt))

    await db.commit()

    task_id = str(uuid.uuid4())
    _completed_tasks[task_id] = counts
    return schemas.TaskBase(task_id=task_id)


@app.get("/tasks/{task_id}", response_model=schemas.TaskResponse)
async def get_task_status(task_id: str):
    if task_id in _completed_tasks:
        return schemas.TaskResponse(task_id=task_id, status="SUCCESS", counts=_completed_tasks[task_id])
    return schemas.TaskResponse(task_id=task_id, status="PENDING", counts=None)


@app.get("/users/{user_id}/recipes", response_model=schemas.RecipeResponse)
async def get_recipes(user_id: int, db: AsyncSession = Depends(get_async_db)):
    user = await db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    product_counts = {p.name: p.count for p in user.products}
    r = await recipes.get_recipes(product_counts)
    return schemas.RecipeResponse(recipes=r)


class ChangeMode(str, Enum):
    ADD = "add"
    REMOVE = "remove"
    DELETE = "delete"


@app.post("/users/{user_id}/change_products", response_model=schemas.User)
async def change_products(
    user_id: int,
    product: schemas.ProductCountBase,
    mode: ChangeMode = Query(ChangeMode.ADD),
    db: AsyncSession = Depends(get_async_db),
):
    user = await db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(select(models.Product).filter_by(user_id=user_id, name=product.name))
    record = result.scalar_one_or_none()

    if mode == ChangeMode.ADD:
        if record:
            record.count += product.count
        else:
            db.add(models.Product(user_id=user_id, name=product.name, count=product.count))
    elif mode == ChangeMode.REMOVE:
        if not record:
            raise HTTPException(status_code=404, detail="Product not found")
        record.count -= product.count
        if record.count <= 0:
            await db.delete(record)
    elif mode == ChangeMode.DELETE:
        if not record:
            raise HTTPException(status_code=404, detail="Product not found")
        await db.delete(record)

    await db.commit()
    await db.refresh(user)
    return user
