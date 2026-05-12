from collections import Counter
import torch
from PIL import Image
from .configs import get_config

config = get_config()

PRODUCT_PROMPTS = {
    "cheddar cheese": "a piece of cheddar cheese, orange cheese",
    "parmesan cheese": "a wedge of parmesan cheese, hard cheese",
    "milk": "a bottle or carton of milk",
    "egg": "a whole chicken egg, egg on table",
    "tomato": "a fresh red tomato, whole tomato",
    "cucumber": "a fresh green cucumber",
    "carrot": "a fresh orange carrot, whole carrot",
    "onion": "a whole onion, onion bulb",
    "garlic": "a head of garlic, garlic cloves",
    "potato": "a raw potato, whole potato",
    "apple": "a fresh apple, whole apple",
    "banana": "a fresh banana, yellow banana",
    "orange": "a fresh orange, whole orange",
    "lemon": "a fresh lemon, whole lemon",
    "butter": "a stick of butter, butter block",
    "bread": "a loaf of bread, sliced bread",
    "chicken": "a piece of raw chicken meat",
    "beef": "a piece of raw beef meat",
    "pork": "a piece of raw pork meat",
    "fish": "a raw fish fillet, whole fish",
    "rice": "a bowl of white rice grains",
    "pasta": "uncooked dry pasta, spaghetti",
    "yogurt": "a cup of yogurt, yogurt container",
    "cheese": "a piece of yellow cheese, cheese block",
    "cream": "a carton of liquid cream",
    "mushroom": "fresh whole mushrooms",
    "bell pepper": "a bell pepper, capsicum",
    "cabbage": "a whole head of cabbage",
    "lettuce": "a head of lettuce, green lettuce",
    "sour cream": "a container of sour cream",
}
PRODUCT_LABELS_ENG = list(config.PRODUCT_LABELS_ENG2RUS.keys())
PRODUCT_PROMPTS_LIST = [PRODUCT_PROMPTS.get(l, f"a photo of {l}") for l in PRODUCT_LABELS_ENG]

_model = None
_processor = None
_loaded = False


def load():
    global _model, _processor, _loaded
    if _loaded:
        return
    torch.set_num_threads(4)
    from transformers import CLIPProcessor, CLIPModel
    _processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    _model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
    _model.eval()
    _loaded = True


def detect_products(image: Image.Image, threshold: float = 0.12) -> dict:
    w, h = image.size
    crops = [image.crop((w * 0.05, h * 0.05, w * 0.95, h * 0.95))]
    if w > 600:
        crops.append(image.crop((0, 0, w * 0.6, h)))
        crops.append(image.crop((w * 0.4, 0, w, h)))

    all_probs = []
    for crop in crops:
        inputs = _processor(text=PRODUCT_PROMPTS_LIST, images=crop, return_tensors="pt", padding=True)
        with torch.no_grad():
            outputs = _model(**inputs)
        probs = outputs.logits_per_image.softmax(dim=-1)[0]
        all_probs.append(probs)

    avg_probs = torch.stack(all_probs).mean(dim=0)

    t = max(threshold, avg_probs.mean().item() + avg_probs.std().item() * 0.4)

    counts = Counter()
    for i, eng in enumerate(PRODUCT_LABELS_ENG):
        if avg_probs[i].item() >= t:
            rus = config.PRODUCT_LABELS_ENG2RUS.get(eng)
            if rus:
                counts[rus] += 1

    if not counts and avg_probs.max().item() > threshold:
        best = avg_probs.argmax().item()
        rus = config.PRODUCT_LABELS_ENG2RUS.get(PRODUCT_LABELS_ENG[best])
        if rus:
            counts[rus] = 1

    return dict(counts)


def warmup():
    load()
    dummy = Image.new("RGB", (224, 224), color=(128, 128, 128))
    detect_products(dummy)
