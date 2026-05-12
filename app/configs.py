import os


class Config:
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./fridge.db")
    SYNC_DATABASE_URL = os.getenv("SYNC_DATABASE_URL", "sqlite:///./fridge.db")
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"

    # ChromaDB
    CHROMA_PATH = os.getenv(
        "CHROMA_PATH",
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "food_parser", "chroma_db")
    )
    COLL_NAME = "chroma_db"

    # Sentence embeddings for recipes
    MODEL_NAME = os.getenv("MODEL_NAME", "paraphrase-multilingual-mpnet-base-v2")

    # Product labels
    PRODUCT_LABELS_ENG2RUS = {
        "cheddar cheese": "сыр",
        "parmesan cheese": "пармезан",
        "milk": "молоко",
        "egg": "яйцо",
        "tomato": "помидор",
        "cucumber": "огурец",
        "carrot": "морковь",
        "onion": "лук",
        "garlic": "чеснок",
        "potato": "картофель",
        "apple": "яблоко",
        "banana": "банан",
        "orange": "апельсин",
        "lemon": "лимон",
        "butter": "масло",
        "bread": "хлеб",
        "chicken": "курица",
        "beef": "говядина",
        "pork": "свинина",
        "fish": "рыба",
        "rice": "рис",
        "pasta": "макароны",
        "yogurt": "йогурт",
        "cheese": "сыр",
        "cream": "сливки",
        "mushroom": "грибы",
        "bell pepper": "перец",
        "cabbage": "капуста",
        "lettuce": "салат",
        "sour cream": "сметана",
    }

    SYSTEM_MSG = (
        "Ты — AI-ассистент для подбора рецептов. "
        "У пользователя есть определённый набор продуктов. "
        "На основе базы знаний предложи 3-5 подходящих рецептов. "
        "Для каждого рецепта укажи: название, время приготовления, "
        "список ингредиентов, пошаговый рецепт, аллергены и пищевую ценность. "
        "Ответ дай на русском языке."
    )


config = Config()


def get_config():
    return config
