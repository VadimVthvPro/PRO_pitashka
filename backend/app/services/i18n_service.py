import json
import os
import logging

logger = logging.getLogger(__name__)

_translations: dict[str, dict] = {}

SUPPORTED_LANGUAGES = ("ru", "en", "de", "fr", "es")
DEFAULT_LANGUAGE = "ru"

LOCALES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "locales")


def load_translations() -> None:
    global _translations
    for lang in SUPPORTED_LANGUAGES:
        path = os.path.join(LOCALES_DIR, f"{lang}.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                _translations[lang] = json.load(f)
            logger.info("Loaded %d translations for %s", len(_translations[lang]), lang)
        else:
            _translations[lang] = {}
            logger.warning("No translations file for %s", lang)


def t(key: str, lang: str = DEFAULT_LANGUAGE) -> str:
    if lang not in _translations:
        lang = DEFAULT_LANGUAGE
    return _translations.get(lang, {}).get(key, key)


BMI_LABELS = {
    "severely_underweight": {"ru": "Сильно ниже нормы", "en": "Severely underweight", "de": "Stark untergewichtig", "fr": "Très insuffisant", "es": "Muy bajo peso"},
    "underweight": {"ru": "Недостаточная масса", "en": "Underweight", "de": "Untergewichtig", "fr": "Insuffisant", "es": "Bajo peso"},
    "normal": {"ru": "Норма", "en": "Normal", "de": "Normalgewicht", "fr": "Normal", "es": "Normal"},
    "overweight": {"ru": "Предожирение", "en": "Overweight", "de": "Übergewichtig", "fr": "Surpoids", "es": "Sobrepeso"},
    "obese": {"ru": "Ожирение", "en": "Obese", "de": "Fettleibig", "fr": "Obèse", "es": "Obesidad"},
}

AIM_LABELS = {
    "weight_loss": {"ru": "Сброс веса", "en": "Weight loss", "de": "Gewichtsverlust", "fr": "Perte de poids", "es": "Pérdida de peso"},
    "maintain": {"ru": "Удержание веса", "en": "Maintain weight", "de": "Gewicht halten", "fr": "Maintien du poids", "es": "Mantenimiento"},
    "weight_gain": {"ru": "Набор массы", "en": "Weight gain", "de": "Gewichtszunahme", "fr": "Prise de poids", "es": "Ganar peso"},
}

SEX_LABELS = {
    "M": {"ru": "Мужчина", "en": "Male", "de": "Mann", "fr": "Homme", "es": "Hombre"},
    "F": {"ru": "Женщина", "en": "Female", "de": "Frau", "fr": "Femme", "es": "Mujer"},
}
