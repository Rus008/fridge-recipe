from .configs import get_config
from .logger import setup_colored_logger
import httpx, asyncio, backoff, json
from sentence_transformers import SentenceTransformer
from chromadb.config import Settings
import chromadb
import spacy

logger = setup_colored_logger(__name__)
config = get_config()

nlp = spacy.load("ru_core_news_md")
_model = SentenceTransformer(config.MODEL_NAME)
_chroma_client = chromadb.PersistentClient(
    path=config.CHROMA_PATH,
    settings=Settings(anonymized_telemetry=False)
)
_chroma_collection = _chroma_client.get_or_create_collection(config.COLL_NAME)
logger.debug(f"Размер бд Chroma: {_chroma_collection.count()}")

def make_user_query(product_counts: dict) -> str:
    items = [f"{k} ({v})" for k, v in product_counts.items()]
    return f"У меня есть: {', '.join(items)}"

def preprocess_query(text: str):
    doc = nlp(text.lower())
    tokens = [
        token.lemma_
        for token in doc
        if not token.is_stop and not token.is_punct and len(token.text) > 2
    ]
    return ' '.join(tokens), tokens

def preprocess_for_embed(product_counts: dict) -> str:
    return "; ".join(preprocess_query(name)[0] for name in product_counts.keys())

def coverage(recipe_ingrs: str, inv: list) -> float:
    try:
        items = json.loads(recipe_ingrs)
    except:
        return 0
    got, total = 0, len(items)
    for ingr in items:
        name_cleaned = preprocess_query(ingr['name'])[0]
        if name_cleaned in inv:
            got += 1
    return got / total if total else 0

def semantic_search(product_counts: dict, k: int = 200) -> list[dict]:
    text = preprocess_for_embed(product_counts)
    emb = _model.encode([text], normalize_embeddings=True)[0]
    cand = _chroma_collection.query(
        query_embeddings=[emb.tolist()],
        n_results=k,
        include=['documents', 'metadatas', 'distances']
    )
    logger.debug(f"Найдено {len(cand['metadatas'][0])} кандидатов")
    combined = zip(cand['distances'][0], cand['metadatas'][0])
    scored = sorted(combined, key=lambda x: x[0])
    return [meta for _, meta in scored]


def format_recipes(context: list[dict]) -> list[str]:
    recipes = []
    for meta in context:
        parts = []
        parts.append(f"{meta['title']}")
        parts.append(f"Время: {meta['time']} мин | {meta.get('count', '?')} порции")
        try:
            ingrs = json.loads(meta.get('ingredients_per_one', meta.get('ingredients', '[]')))
            ingr_names = ', '.join(i.get('name', '') for i in ingrs)
            parts.append(f"Ингредиенты: {ingr_names}")
        except:
            parts.append(f"Ингредиенты: {meta.get('ingredients', 'Нет данных')}")
        parts.append("")
        parts.append(f"Приготовление:\n{meta['recipe']}")
        recipes.append("\n".join(parts))
    return recipes


async def get_recipes(product_counts: dict) -> list[str]:
    if not product_counts:
        return ["Продукты не найдены. Добавьте продукты в холодильник."]

    user_q = make_user_query(product_counts)
    logger.info(f"Пользовательский запрос: {user_q}")

    context = semantic_search(product_counts, k=200)
    logger.info(f"Найдено {len(context)} кандидатов")

    inv_cleaned = [preprocess_query(name)[0] for name in product_counts.keys()]

    scored = []
    for meta in context:
        cov = coverage(meta['ingredients'], inv_cleaned)
        if cov > 0:
            scored.append((cov, meta))

    scored.sort(key=lambda x: -x[0])

    thresholds = [1.0, 0.7, 0.5]
    filtered = []
    for t in thresholds:
        filtered = [meta for cov, meta in scored if cov >= t]
        if len(filtered) >= 15:
            logger.info(f"Порог покрытия {t}: {len(filtered)} рецептов")
            break

    if not filtered:
        return ["Нет рецептов из ваших продуктов. Добавьте больше продуктов."]

    easy, medium, hard = [], [], []
    for meta in filtered:
        try:
            tm = int(meta['time'])
        except:
            tm = 30
        if tm <= 30:
            easy.append(meta)
        elif tm <= 60:
            medium.append(meta)
        else:
            hard.append(meta)

    selected = easy[:5] + medium[:5] + hard[:5]

    if not selected:
        return ["Нет подходящих рецептов."]

    logger.info(f"Отобрано: {len(easy[:5])} лёгких, {len(medium[:5])} средних, {len(hard[:5])} сложных")
    return format_recipes(selected)
