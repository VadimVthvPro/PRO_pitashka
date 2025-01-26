from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import main_mo as l
from enum import Enum
import psycopg2
from aiogram import types
import gettext


lenguages = {'Русский 🇷🇺':'ru', 'English 🇬🇧':'en', 'Deutsch 🇩🇪':'de','Française 🇫🇷':'fr', 'Spanish 🇪🇸':'es'}



def starter(k):
    lenguage = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text='Русский 🇷🇺'),
                KeyboardButton(text='English 🇬🇧'),
                KeyboardButton(text='Deutsch 🇩🇪'),
            ],
            [
                KeyboardButton(text='Française 🇫🇷'),
                KeyboardButton(text='Spanish 🇪🇸'),

            ]

        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    kb = {'lenguage': lenguage}
    return kb[k]

def keyboard(user_id, k):
    conn = psycopg2.connect(dbname='propitashka', user='postgres', password='000', host='localhost', port="5432")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT lang FROM user_lang WHERE user_id = {}".format(int(user_id))
    )
    leng1 = cursor.fetchone()[0]
    conn.commit()
    cursor.close()

    leng = gettext.translation('messages', localedir='locales', languages=[leng1], fallback=False)
    leng.install()

    startMenu = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=l.printer_with_given(leng, "kbENTRANCE")),
                KeyboardButton(text=l.printer_with_given(leng, 'kbREG')),

            ]

        ],
        resize_keyboard=True,
        one_time_keyboard=True,

    )

    entranse = ReplyKeyboardMarkup(
        keyboard = [
            [
                KeyboardButton(text = l.printer_with_given( leng, "kbENTRANCE2PROG")),

            ]

        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    reRig = ReplyKeyboardMarkup(
        keyboard = [
            [
                KeyboardButton(text= l.printer_with_given(leng,"kbreREG")),

            ]

        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    sex = ReplyKeyboardMarkup(
        keyboard = [
            [
                KeyboardButton(text=l.printer_with_given( leng, "kbMAN")),
                KeyboardButton(text=l.printer_with_given(leng, "kbWOMAN")),

            ]

        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    food = ReplyKeyboardMarkup(
        keyboard = [
            [
                KeyboardButton(text=l.printer_with_given(leng, "kbfood1")),
                KeyboardButton(text=l.printer_with_given(leng, "kbfood2")),
            ]

        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    want = ReplyKeyboardMarkup(
        keyboard = [
            [
                KeyboardButton(text=l.printer_with_given(leng, "kbwant1")),
                KeyboardButton(text=l.printer_with_given(leng,"kbwant2")),
                KeyboardButton(text=l.printer_with_given(leng, "kbwant3")),

            ]

        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    main_menu = ReplyKeyboardMarkup(
        keyboard = [
            [
                KeyboardButton(text=l.printer_with_given(leng, "kbmain1")),
                KeyboardButton(text=l.printer_with_given( leng,"kbmain2")),
                KeyboardButton(text=l.printer_with_given( leng,"kbmain3")),
            ],
            [
                KeyboardButton(text=l.printer_with_given( leng,"kbmain4")),
                KeyboardButton(text=l.printer_with_given( leng, "kbmain5")),
            ],
            [
                KeyboardButton(text=l.printer_with_given(leng, "kbmain6")),
            ],
            [
                KeyboardButton(text=l.printer_with_given(leng, "kbmain7")),
            ],
            [
                KeyboardButton(text = l.printer_with_given(leng, "kbmain8")),
            ],
            [
                KeyboardButton(text=l.printer_with_given( leng,"kbmain9")),
            ]


        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    tren = ReplyKeyboardMarkup(
        keyboard = [
            [
                KeyboardButton(text=l.printer_with_given(leng, "kbtren1")),
                KeyboardButton(text=l.printer_with_given(leng, "kbtren2")),
                KeyboardButton(text=l.printer_with_given(leng, "kbtren3")),

            ]

        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    meals = ReplyKeyboardMarkup(
        keyboard = [
            [
                KeyboardButton(text=l.printer_with_given(leng, "kbmeal1")),
                KeyboardButton(text=l.printer_with_given(leng, "kbmeal2")),
                KeyboardButton(text=l.printer_with_given( leng,"kbmeal3")),

            ]

        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    svo = ReplyKeyboardMarkup(
        keyboard = [
            [
                KeyboardButton(text=l.printer_with_given(leng, "kbsvo1")),
                KeyboardButton(text=l.printer_with_given(leng, "kbsvo2")),
                KeyboardButton(text=l.printer_with_given(leng, "kbsvo3")),

            ]

        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    tren_type = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=l.printer_with_given(leng, "kbtype1")),
                KeyboardButton(text=l.printer_with_given(leng, "kbtype2")),
                KeyboardButton(text=l.printer_with_given(leng, "kbtype3")),

            ]

        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    tren_choise = ReplyKeyboardMarkup(
        keyboard = [
            [
                KeyboardButton(text=l.printer_with_given(leng, "kbchoise1")),
                KeyboardButton(text=l.printer_with_given(leng, "kbchoise2")),

            ]

        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    lenguage = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text='Русский 🇷🇺'),
                KeyboardButton(text='English 🇬🇧'),
                KeyboardButton(text='Deutsch 🇩🇪'),
            ],
            [
                KeyboardButton(text='Française 🇫🇷'),
                KeyboardButton(text='Spanish 🇪🇸'),

            ]

        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    kb = {'startMenu': startMenu, 'lenguage': lenguage, 'entranse': entranse,  'reRig': reRig, 'sex': sex, 'food': food,
          'want': want, 'main_menu': main_menu, 'tren': tren, 'meals': meals, 'svo': svo, 'tren_type': tren_type,
          'tren_choise': tren_choise}
    return kb[k]







