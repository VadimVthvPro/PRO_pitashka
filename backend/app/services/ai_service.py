import json
import logging
import google.generativeai as genai
from app.config import get_settings
from app.utils.retry import async_retry

logger = logging.getLogger(__name__)

_model = None
_vision_model = None


def _get_model():
    global _model
    if _model is None:
        genai.configure(api_key=get_settings().GEMINI_API_KEY)
        _model = genai.GenerativeModel("gemini-2.5-flash")
    return _model


def _get_vision_model():
    global _vision_model
    if _vision_model is None:
        genai.configure(api_key=get_settings().GEMINI_API_KEY)
        _vision_model = genai.GenerativeModel("gemini-2.5-flash")
    return _vision_model


@async_retry(attempts=3, delay=1.0)
async def recognize_food_photo(image_bytes: bytes) -> list[dict]:
    model = _get_vision_model()
    prompt = (
        "Analyze this food photo. Return a JSON array of items: "
        '[{"name": "food name", "grams": estimated_grams, "cal": calories, "b": protein_g, "g": fat_g, "u": carbs_g}]. '
        "Only JSON, no other text."
    )
    import PIL.Image
    import io
    image = PIL.Image.open(io.BytesIO(image_bytes))
    response = await model.generate_content_async([prompt, image])
    text = response.text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    return json.loads(text)


@async_retry(attempts=3, delay=1.0)
async def analyze_food_text(foods: list[str], grams: list[float], lang: str = "ru") -> list[dict]:
    model = _get_model()
    items = ", ".join(f"{f} {g}g" for f, g in zip(foods, grams))
    prompt = (
        f"Calculate KBJU for these foods: {items}. "
        f'Return JSON array: [{{"name": "...", "grams": N, "cal": N, "b": N, "g": N, "u": N}}]. '
        f"Language: {lang}. Only JSON."
    )
    response = await model.generate_content_async(prompt)
    text = response.text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    return json.loads(text)


@async_retry(attempts=3, delay=1.0)
async def generate_meal_plan(user_info: dict, lang: str = "ru") -> str:
    model = _get_model()
    prompt = (
        f"Create a detailed weekly meal plan (7 days, 3 meals + snacks) for a person with these parameters:\n"
        f"Sex: {user_info.get('sex', 'unknown')}, Weight: {user_info.get('weight')}kg, "
        f"Height: {user_info.get('height')}cm, BMI: {user_info.get('imt')}, "
        f"Goal: {user_info.get('aim')}, Daily calories: {user_info.get('daily_cal')}kcal.\n"
        f"Include KBJU for each meal. Language: {lang}."
    )
    response = await model.generate_content_async(prompt)
    return response.text


@async_retry(attempts=3, delay=1.0)
async def generate_workout_plan(user_info: dict, lang: str = "ru") -> str:
    model = _get_model()
    prompt = (
        f"Create a weekly workout plan (7 days) for:\n"
        f"Sex: {user_info.get('sex', 'unknown')}, Weight: {user_info.get('weight')}kg, "
        f"BMI: {user_info.get('imt')}, Goal: {user_info.get('aim')}.\n"
        f"Include exercise names, sets, reps, rest times. Language: {lang}."
    )
    response = await model.generate_content_async(prompt)
    return response.text


@async_retry(attempts=3, delay=1.0)
async def generate_recipe(meal_type: str, user_info: dict, lang: str = "ru") -> str:
    model = _get_model()
    prompt = (
        f"Generate a healthy {meal_type} recipe for a person with daily calorie target "
        f"{user_info.get('daily_cal')}kcal, goal: {user_info.get('aim')}.\n"
        f"Include ingredients, steps, and KBJU. Language: {lang}."
    )
    response = await model.generate_content_async(prompt)
    return response.text


@async_retry(attempts=3, delay=1.0)
async def chat(message: str, context: list[dict], user_info: dict, lang: str = "ru") -> str:
    model = _get_model()
    system = (
        "You are PROpitashka AI assistant — a friendly nutrition and fitness expert. "
        f"User parameters: {json.dumps(user_info)}. "
        f"Respond in language: {lang}. Be helpful, specific, and encouraging."
    )
    history_text = "\n".join(
        f"{'User' if m['message_type'] == 'user' else 'Assistant'}: {m['message_text']}"
        for m in context[-10:]
    )
    full_prompt = f"{system}\n\nChat history:\n{history_text}\n\nUser: {message}\nAssistant:"
    response = await model.generate_content_async(full_prompt)
    return response.text
