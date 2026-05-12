import torch
from PIL import Image
from .configs import get_config

config = get_config()

_model = None
_processor = None
_loaded = False

PROMPT = "Какие из этих продуктов есть на фото? " + ", ".join(config.PRODUCT_LABELS_ENG2RUS.values()) + ". Ответь только список найденного через запятую."
VALID = set(config.PRODUCT_LABELS_ENG2RUS.values())


def load():
    global _model, _processor, _loaded
    if _loaded:
        return
    from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
    _model = Qwen2VLForConditionalGeneration.from_pretrained(
        "Qwen/Qwen2-VL-2B-Instruct", torch_dtype=torch.bfloat16, device_map="auto"
    )
    _model.eval()
    _processor = AutoProcessor.from_pretrained("Qwen/Qwen2-VL-2B-Instruct")
    _loaded = True


def detect_products(image: Image.Image) -> dict:
    load()

    msgs = [{"role": "user", "content": [{"type": "image", "image": image}, {"type": "text", "text": PROMPT}]}]
    text = _processor.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    inputs = _processor(text=[text], images=[image], return_tensors="pt").to(_model.device)

    with torch.no_grad():
        out = _model.generate(**inputs, max_new_tokens=64)

    resp = _processor.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)

    counts = {}
    for token in resp.lower().split(","):
        token = token.strip().strip(".")
        for rus in VALID:
            if rus.lower() in token:
                counts[rus] = counts.get(rus, 0) + 1
                break

    return counts
