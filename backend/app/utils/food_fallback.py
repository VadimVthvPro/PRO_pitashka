FOOD_DATABASE = {
    "гречка": {"cal": 343, "b": 12.6, "g": 3.3, "u": 62.1},
    "рис": {"cal": 344, "b": 6.7, "g": 0.7, "u": 78.9},
    "овсянка": {"cal": 342, "b": 12.3, "g": 6.1, "u": 59.5},
    "курица": {"cal": 165, "b": 31, "g": 3.6, "u": 0},
    "говядина": {"cal": 250, "b": 26, "g": 15, "u": 0},
    "свинина": {"cal": 242, "b": 16, "g": 21.2, "u": 0},
    "лосось": {"cal": 208, "b": 20, "g": 13, "u": 0},
    "яйцо": {"cal": 155, "b": 12.6, "g": 10.6, "u": 1.1},
    "молоко": {"cal": 64, "b": 3.2, "g": 3.6, "u": 4.8},
    "творог": {"cal": 121, "b": 16, "g": 5, "u": 3},
    "хлеб": {"cal": 265, "b": 9, "g": 3.2, "u": 49},
    "макароны": {"cal": 371, "b": 13, "g": 1.5, "u": 70.5},
    "картофель": {"cal": 77, "b": 2, "g": 0.1, "u": 17},
    "банан": {"cal": 89, "b": 1.1, "g": 0.3, "u": 22.8},
    "яблоко": {"cal": 52, "b": 0.3, "g": 0.2, "u": 14},
    "помидор": {"cal": 18, "b": 0.9, "g": 0.2, "u": 3.9},
    "огурец": {"cal": 15, "b": 0.65, "g": 0.11, "u": 3.63},
    "сыр": {"cal": 350, "b": 25, "g": 26, "u": 1.3},
    "масло сливочное": {"cal": 717, "b": 0.85, "g": 81, "u": 0.06},
    "масло подсолнечное": {"cal": 884, "b": 0, "g": 100, "u": 0},
}

FOOD_SYNONYMS = {
    "buckwheat": "гречка", "rice": "рис", "oatmeal": "овсянка",
    "chicken": "курица", "beef": "говядина", "pork": "свинина",
    "salmon": "лосось", "egg": "яйцо", "milk": "молоко",
    "cottage cheese": "творог", "bread": "хлеб", "pasta": "макароны",
    "potato": "картофель", "banana": "банан", "apple": "яблоко",
    "tomato": "помидор", "cucumber": "огурец", "cheese": "сыр",
}


def find_food(name: str) -> dict | None:
    key = name.lower().strip()
    if key in FOOD_DATABASE:
        return FOOD_DATABASE[key]
    if key in FOOD_SYNONYMS:
        return FOOD_DATABASE.get(FOOD_SYNONYMS[key])
    return None


def calculate_nutrition(food_data: dict, grams: float) -> dict:
    factor = grams / 100.0
    return {
        "cal": round(food_data["cal"] * factor, 1),
        "b": round(food_data["b"] * factor, 1),
        "g": round(food_data["g"] * factor, 1),
        "u": round(food_data["u"] * factor, 1),
    }
