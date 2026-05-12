# Fridge Recipe Maker — Hugging Face Space

## 1. Зарегистрируйся на https://huggingface.co/join

## 2. Создай Space
- Нажми + → New Space
- Name: `fridge-recipe`
- License: MIT
- Space SDK: **Docker**
- Hardware: **CPU free** (всегда бесплатно)
- Visibility: **Public**
- Create Space

## 3. Загрузи файлы в Space
Через **Add file → Upload files** загрузи эти файлы:

### `Dockerfile`
```dockerfile
FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m spacy download ru_core_news_md

COPY . .

CMD uvicorn main:app --host 0.0.0.0 --port 7860
```

### `requirements.txt`
```
fastapi
uvicorn
pillow
torch
transformers
sentence-transformers
chromadb
spacy
passlib
python-multipart
aiosqlite
sqlalchemy
bcrypt
```

### Остальные файлы
Скопируй из проекта:
- `main.py`
- папку `app/` (целиком)
- папку `food_parser/` (целиком)
- `fridge.db`

## 4. После деплоя
Space даст URL: `https://fridge-recipe.hf.space`

Введи его в Android APK.
