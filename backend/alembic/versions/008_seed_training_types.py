"""Seed the standard catalog of training types (idempotent).

Revision ID: 008_seed_training_types
Revises: 007_audit_log
Create Date: 2026-04-19

Coefficients are MET values (kcal per kg of body weight per hour) drawn from
the Compendium of Physical Activities and used by `calculate_training_calories`.
"""
from typing import Sequence, Union
from alembic import op
from sqlalchemy import text

revision: str = "008_seed_training_types"
down_revision: Union[str, None] = "007_audit_log"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (name_ru, name_en, name_de, name_fr, name_es, MET, emoji,
#  desc_ru, desc_en, desc_de, desc_fr, desc_es)
TYPES = [
    ("Бег",            "Running",       "Laufen",         "Course à pied",     "Correr",
     9.8, "🏃",
     "Бег средней интенсивности (~9–10 км/ч).",
     "Steady running at a moderate ~9–10 km/h pace.",
     "Gleichmäßiges Laufen bei ca. 9–10 km/h.",
     "Course régulière à environ 9–10 km/h.",
     "Carrera constante a ~9–10 km/h."),
    ("Ходьба",         "Walking",       "Gehen",          "Marche",            "Caminar",
     3.5, "🚶",
     "Прогулка в умеренном темпе (~5 км/ч).",
     "Brisk walking at ~5 km/h.",
     "Zügiges Gehen bei ca. 5 km/h.",
     "Marche rapide à ~5 km/h.",
     "Caminata a paso ligero (~5 km/h)."),
    ("Велосипед",      "Cycling",       "Radfahren",      "Vélo",              "Ciclismo",
     7.5, "🚴",
     "Велосипед с умеренным усилием (~16–19 км/ч).",
     "Cycling at moderate effort (~16–19 km/h).",
     "Radfahren mit mäßiger Anstrengung (~16–19 km/h).",
     "Vélo à effort modéré (~16–19 km/h).",
     "Ciclismo a esfuerzo moderado (~16–19 km/h)."),
    ("Плавание",       "Swimming",      "Schwimmen",      "Natation",          "Natación",
     8.0, "🏊",
     "Плавание кролем со средним темпом.",
     "Freestyle swimming at moderate pace.",
     "Kraulschwimmen in mittlerem Tempo.",
     "Natation crawl à allure modérée.",
     "Natación crol a ritmo moderado."),
    ("Силовая тренировка", "Strength training", "Krafttraining", "Musculation", "Entrenamiento de fuerza",
     6.0, "🏋",
     "Тренировка с весами в зале или дома.",
     "Weight training, gym or home setup.",
     "Krafttraining mit Gewichten, im Studio oder daheim.",
     "Musculation avec charges, en salle ou à la maison.",
     "Entrenamiento con pesas, en gimnasio o en casa."),
    ("Йога",           "Yoga",          "Yoga",           "Yoga",              "Yoga",
     3.0, "🧘",
     "Спокойная практика хатха-йоги.",
     "Gentle hatha yoga practice.",
     "Sanftes Hatha-Yoga.",
     "Pratique douce de hatha yoga.",
     "Práctica suave de hatha yoga."),
    ("Пилатес",        "Pilates",       "Pilates",        "Pilates",           "Pilates",
     3.5, "🤸",
     "Контролируемые упражнения на пресс и стабилизацию.",
     "Core and stabilisation work.",
     "Übungen für Core und Stabilität.",
     "Exercices pour le tronc et la stabilité.",
     "Trabajo de core y estabilización."),
    ("HIIT",           "HIIT",          "HIIT",           "HIIT",              "HIIT",
     8.5, "🔥",
     "Интервальные высокоинтенсивные подходы.",
     "High-intensity interval bursts.",
     "Hochintensive Intervalle.",
     "Intervalles à haute intensité.",
     "Intervalos de alta intensidad."),
    ("Кроссфит",       "CrossFit",      "CrossFit",       "CrossFit",          "CrossFit",
     9.0, "🤾",
     "Функциональный тренинг с весами и кардио.",
     "Functional training mixing weights and cardio.",
     "Funktionelles Training aus Kraft und Cardio.",
     "Entraînement fonctionnel mêlant charge et cardio.",
     "Entrenamiento funcional con cargas y cardio."),
    ("Бокс",           "Boxing",        "Boxen",          "Boxe",              "Boxeo",
     9.0, "🥊",
     "Работа на снарядах, бой с тенью.",
     "Bag work and shadow boxing.",
     "Sackarbeit und Schattenboxen.",
     "Travail au sac et shadow boxing.",
     "Trabajo de saco y sombra."),
    ("Танцы",          "Dancing",       "Tanzen",         "Danse",             "Baile",
     5.0, "💃",
     "Активные танцы средней интенсивности.",
     "Energetic dancing at moderate intensity.",
     "Aktives Tanzen mit mittlerer Intensität.",
     "Danse énergique à intensité modérée.",
     "Baile enérgico a intensidad moderada."),
    ("Лыжи",           "Skiing",        "Skifahren",      "Ski",               "Esquí",
     7.0, "🎿",
     "Беговые или горные лыжи.",
     "Cross-country or alpine skiing.",
     "Langlauf oder Ski Alpin.",
     "Ski de fond ou alpin.",
     "Esquí de fondo o alpino."),
    ("Сноуборд",       "Snowboarding",  "Snowboarden",    "Snowboard",         "Snowboard",
     5.5, "🏂",
     "Катание на сноуборде.",
     "Snowboarding session.",
     "Snowboard fahren.",
     "Session de snowboard.",
     "Sesión de snowboard."),
    ("Скакалка",       "Jump rope",     "Seilspringen",   "Corde à sauter",    "Saltar la cuerda",
     12.3, "🪢",
     "Прыжки на скакалке в среднем темпе.",
     "Jumping rope at moderate pace.",
     "Seilspringen in mittlerem Tempo.",
     "Corde à sauter à allure modérée.",
     "Saltar la cuerda a ritmo moderado."),
    ("Гребля",         "Rowing",        "Rudern",         "Aviron",            "Remo",
     7.0, "🚣",
     "Гребной тренажёр или вёсельная лодка.",
     "Rowing machine or boat.",
     "Rudergerät oder Boot.",
     "Rameur ou aviron.",
     "Máquina de remo o barco."),
    ("Эллипсоид",      "Elliptical",    "Crosstrainer",   "Elliptique",        "Elíptica",
     5.0, "⚙️",
     "Кардио на эллиптическом тренажёре.",
     "Cardio on the elliptical trainer.",
     "Cardio auf dem Crosstrainer.",
     "Cardio sur elliptique.",
     "Cardio en elíptica."),
    ("Футбол",         "Football",      "Fußball",        "Football",          "Fútbol",
     7.0, "⚽",
     "Игра в футбол с друзьями.",
     "Casual football match.",
     "Fußballspiel.",
     "Match de football.",
     "Partido de fútbol."),
    ("Баскетбол",      "Basketball",    "Basketball",     "Basketball",        "Baloncesto",
     6.5, "🏀",
     "Игра в баскетбол.",
     "Basketball game.",
     "Basketballspiel.",
     "Match de basketball.",
     "Partido de baloncesto."),
    ("Теннис",         "Tennis",        "Tennis",         "Tennis",            "Tenis",
     7.0, "🎾",
     "Одиночные игры в теннис.",
     "Singles tennis match.",
     "Einzelspiel im Tennis.",
     "Match de tennis en simple.",
     "Partido de tenis individual."),
    ("Растяжка",       "Stretching",    "Stretching",     "Étirements",        "Estiramientos",
     2.3, "🤲",
     "Заминка и работа над гибкостью.",
     "Cool-down and mobility work.",
     "Cool-down und Mobility.",
     "Récup et mobilité.",
     "Vuelta a la calma y movilidad."),
]


def upgrade() -> None:
    bind = op.get_bind()
    stmt = text(
        """
        INSERT INTO training_types
          (name_ru, name_en, name_de, name_fr, name_es,
           base_coefficient, emoji,
           description_ru, description_en, description_de,
           description_fr, description_es, is_active)
        VALUES
          (:name_ru, :name_en, :name_de, :name_fr, :name_es,
           :base_coefficient, :emoji,
           :description_ru, :description_en, :description_de,
           :description_fr, :description_es, TRUE)
        ON CONFLICT (name_ru) DO UPDATE SET
          name_en          = EXCLUDED.name_en,
          name_de          = EXCLUDED.name_de,
          name_fr          = EXCLUDED.name_fr,
          name_es          = EXCLUDED.name_es,
          base_coefficient = EXCLUDED.base_coefficient,
          emoji            = EXCLUDED.emoji,
          description_ru   = EXCLUDED.description_ru,
          description_en   = EXCLUDED.description_en,
          description_de   = EXCLUDED.description_de,
          description_fr   = EXCLUDED.description_fr,
          description_es   = EXCLUDED.description_es,
          is_active        = TRUE,
          updated_at       = NOW();
        """
    )
    for row in TYPES:
        bind.execute(
            stmt,
            {
                "name_ru": row[0],
                "name_en": row[1],
                "name_de": row[2],
                "name_fr": row[3],
                "name_es": row[4],
                "base_coefficient": row[5],
                "emoji": row[6],
                "description_ru": row[7],
                "description_en": row[8],
                "description_de": row[9],
                "description_fr": row[10],
                "description_es": row[11],
            },
        )


def downgrade() -> None:
    names = tuple(r[0] for r in TYPES)
    bind = op.get_bind()
    bind.execute(
        text("DELETE FROM training_types WHERE name_ru = ANY(:names)"),
        {"names": list(names)},
    )
