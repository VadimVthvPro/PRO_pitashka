import psycopg2
from aiogram.filters import CommandStart
from aiogram.client.bot import DefaultBotProperties
from aiogram.enums import ParseMode
import aiosqlite
import base64
import json
import matplotlib.pyplot as plt  # type: ignore
import PIL  # type: ignore
import numpy as np  # type: ignore
from tensorflow import keras  # type: ignore
from tensorflow.keras import layers  # type: ignore
from tensorflow.keras.models import Sequential  # type: ignore
import pathlib
from dotenv import load_dotenv
import os
import keyboards as kb
import asyncio
import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message, FSInputFile, file
import tensorflow as tf  # type: ignore
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from gigachat import GigaChat
from aiogram.filters import Command
import main_mo as l
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from translate import Translator
import requests
from openai import OpenAI
import re



GIF_LIBRARY = {
    "Жим штанги лёжа": "https://i.giphy.com/media/v1.Y2lkPTc5MGI3NjExcnIycmluczlwMG92cXV0N3BpbG14ajdibzNxa2owc3M5N3U2cTNleCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/3tCMXFyNBabv8f6DoW/giphy.gif",
}




client = OpenAI(api_key='sk-7e56f002522c4a589d447cbef93c3d95', base_url="https://api.deepseek.com")


API_KEY = os.getenv('gpt')

# URL для отправки запросов к модели
URL = 'gpt://ajeva7v073iank62rr8g/yandexgpt-lite'




languages = {'Русский 🇷🇺':'ru', 'English 🇬🇧':'en', 'Deutsch 🇩🇪':'de','Française 🇫🇷':'fr', 'Spanish 🇪🇸':'es'}
llaallallaa = {'ru':'Русский 🇷🇺', 'en':'English 🇬🇧', 'de':'Deutsch 🇩🇪','fr':'Française 🇫🇷', 'es':'Spanish 🇪🇸'}


tren_list = [["Жим штанги лёжа","Bench press", "Banc de musculation", "Bankdrücken", "Press de banca" ], ["Подъём на бицепс", "Curl de bíceps", "Bizepscurl", "Flexion des biceps", "Biceps curl"], ["Подтягивания", "Pull-ups", "Tractions", "Klimmzüge", "Pull-ups"]]



dataset_dir = pathlib.Path("food-101")
batch_size = 32
img_width = 180
img_height = 180
train_ds = tf.keras.utils.image_dataset_from_directory(
    dataset_dir,
    validation_split=0.2,
    subset="training",
    seed=123,
   image_size=(img_height, img_width),
   batch_size=batch_size)

val_ds = tf.keras.utils.image_dataset_from_directory(
    dataset_dir,
    validation_split=0.2,
    subset="validation",
    seed=123,
    image_size=(img_height, img_width),
    batch_size=batch_size)

class_names = train_ds.class_names
print(f"Class names: {class_names}")

num_classes = len(class_names)
model = Sequential([
    tf.keras.layers.Rescaling(1. / 255, input_shape=(img_height, img_width, 3)),

    tf.keras.layers.RandomFlip("horizontal", input_shape=(img_height, img_width, 3)),
    tf.keras.layers.RandomRotation(0.1),
    tf.keras.layers.RandomZoom(0.1),
    tf.keras.layers.RandomContrast(0.2),

    layers.Conv2D(16, 3, padding='same', activation='relu'),
    layers.MaxPooling2D(),

    layers.Conv2D(32, 3, padding='same', activation='relu'),
    layers.MaxPooling2D(),

    layers.Conv2D(64, 3, padding='same', activation='relu'),
    layers.MaxPooling2D(),

    layers.Dropout(0.2),

    layers.Flatten(),
    layers.Dense(128, activation='relu'),
    layers.Dense(num_classes)
])

model.compile(
    optimizer='adam',
    loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),
    metrics=['accuracy'])

model.load_weights("Foood.weights.h5")

loss, acc = model.evaluate(train_ds, verbose=2)
print("Restored model, accuracy: {:5.2f}%".format(100 * acc))


load_dotenv()
TOKEN = os.getenv('TOKEN')

def decode_credentials(encoded_str):
    decoded_bytes = base64.b64decode(encoded_str)
    decoded_str = decoded_bytes.decode('utf-8')
    client_id, client_secret = decoded_str.split(':')
    return client_id, client_secret


encoded_credentials = os.getenv('GIGA')
client_id, client_secret = decode_credentials(encoded_credentials)
GIGA = {
    'client_id': client_id,
    'client_secret': client_secret
}



credentials_str = f"{GIGA['client_id']}:{GIGA['client_secret']}"
credentials_base64 = base64.b64encode(credentials_str.encode("utf-8")).decode("utf-8")

bot = Bot(TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


conn = psycopg2.connect(dbname='propitashka', user='postgres', password='000', host='localhost', port="5432")
cursor = conn.cursor()


class REG(StatesGroup):
    height = State()
    age = State()
    sex = State()
    want = State()
    weight = State()
    types = State()
    length = State()
    food = State()
    food_list = State()
    food_photo = State()
    grams = State()
    food_meals = State()
    train = State()
    tren_choiser = State()
    svo = State()
    leng = State()
    leng2 = State()
    grams1 = State()
    new_weight = State()
    tren_ai = State()
    new_height = State()
    ai_ans = State()




@dp.message(CommandStart())
async def leng(message: Message, state: FSMContext):
    await state.set_state(REG.leng)
    await message.answer(text = 'Please, choose a language:', reply_markup=kb.starter('lenguage'))


@dp.message(REG.leng)
async def start(message: Message, state: FSMContext):
    await state.update_data(leng=message.text)
    data = await state.get_data()
    cursor.execute(
                 f"""
                    
                    DO $$
                    BEGIN
                        IF EXISTS (SELECT * FROM user_lang WHERE user_id = {message.from_user.id}) THEN
                            UPDATE 
                            user_lang 
                            SET lang='{languages[data['leng']]}'
                             WHERE user_id = {message.from_user.id};
                        ELSE
                            INSERT INTO 
                            user_lang(user_id, lang)
                            VALUES
                            ({str(message.from_user.id)}, '{languages[data['leng']]}');
                        END IF;
                    END;
                    $$
                        
                """)
    conn.commit()
    await message.answer_photo(
        FSInputFile(path='new_logo.jpg'),
        caption= l.printer(message.from_user.id, "start").format(message.from_user.first_name),

        reply_markup=kb.keyboard(message.from_user.id, 'startMenu')
    )
    await state.clear()





@dp.message(F.text.in_({'Вход','Entry','Entrée','Entrada','Eintrag'}))
async def entrance(message: Message, state: FSMContext):
    try:
        cursor.execute(f"""SELECT 
        *
        FROM user_health 
        WHERE user_id = {message.from_user.id} """)
        user_data = cursor.fetchall()[0]

#AND date = '{datetime.datetime.now().strftime('%Y-%m-%d')}'


        imt, imt_str, cal, weight, height =  float(user_data[1]), user_data[2], float(user_data[3]), user_data[6], user_data[7]
        conn.commit()
        if weight and imt and imt_str and cal and height:
            await bot.send_message(
                message.chat.id,
                text=l.printer(message.from_user.id, 'info').format(message.from_user.first_name,weight,height,imt,imt_str)
            )
            await message.answer(
                l.printer(message.from_user.id, 'SuccesfulEntrance'),
                reply_markup=kb.keyboard(message.from_user.id, 'main_menu'))


        else:
            await bot.send_message(message.chat.id, text=l.printer(message.from_user.id, 'MissedReg'),
                                   reply_markup=kb.keyboard(message.from_user.id,  'reRig'))
    except:
        await bot.send_message(message.chat.id, text=l.printer(message.from_user.id, 'MissedReg'),
                               reply_markup=kb.keyboard(message.from_user.id, 'reRig'))


@dp.message(F.text.in_( {'Регистрация', "Anmeldung" ,'Registration','Enregistrement','Inscripción'}))
async def registration(message: Message, state: FSMContext):

    await state.set_state(REG.height)
    await bot.send_message(message.chat.id, text=l.printer(message.from_user.id, 'height'))


@dp.message(REG.height)
async def height(message: Message, state: FSMContext):
    try:
        await state.update_data(height=float(message.text))
        await state.set_state(REG.age)
        await message.answer(l.printer(message.from_user.id, 'age'))
    except:
        await state.set_state(REG.height)
        await bot.send_message(message.chat.id, text=l.printer(message.from_user.id, 'height'))


@dp.message(REG.age)
async def age(message: Message, state: FSMContext):
    try:
        await state.update_data(age=int(message.text))
        await state.set_state(REG.sex)
        await message.answer(l.printer(message.from_user.id, 'sex'), reply_markup=kb.keyboard(message.from_user.id, 'sex'))
    except:
        await state.set_state(REG.age)
        await message.answer(l.printer(message.from_user.id, 'age'))


@dp.message(REG.sex)
async def sex(message: Message, state: FSMContext):
    await state.update_data(sex=message.text)
    await state.set_state(REG.want)
    await message.answer(l.printer(message.from_user.id, 'aim'), reply_markup=kb.keyboard(message.from_user.id, 'want'))

@dp.message(REG.want)
async def want(message: Message, state: FSMContext):
    await state.update_data(want=message.text)
    await state.set_state(REG.weight)
    await message.answer(l.printer(message.from_user.id, 'weight'), reply_markup=types.ReplyKeyboardRemove())

@dp.message(REG.weight)
async def wei(message: Message, state: FSMContext):
    try:
        await state.update_data(weight=message.text)
        data = await state.get_data()
        height, sex, age, weight, aim = data['height'], data['sex'], data['age'], data['weight'], data['want']


        if "," in weight:
            we1 = message.text.split(",")
            weight = int(we1[0]) + int(we1[1]) / 10 ** len(we1[1])
        else:
            weight = float(message.text)
        height, sex, age = float(height), str(sex), int(age)
        imt = round(weight / ((height / 100) ** 2), 3)
        imt_using_words = calculate_imt_description(imt, message)
        cal = float(calculate_calories(sex, weight, height, age, message))

        cursor.execute(f"""
            INSERT INTO user_health (user_id,imt,imt_str,cal,date, weight, height) VALUES ({message.from_user.id},{imt},'{imt_using_words}',{cal},'{datetime.datetime.now().strftime('%Y-%m-%d')}', {weight}, {height} )
            ;
            DO $$
            BEGIN

                IF EXISTS (SELECT * FROM user_main WHERE user_id = {message.from_user.id}) THEN 
                    UPDATE user_main SET user_sex = '{sex}'  WHERE user_id = {message.from_user.id};
                ELSE
                    INSERT INTO user_main 
                    (user_id, user_name,user_sex,date_of_birth) VALUES ({message.from_user.id},'{message.from_user.first_name}','{sex}',{age})
                    ;
                END IF;

                IF EXISTS (SELECT * FROM user_aims WHERE user_id = {message.from_user.id}) THEN 
                    UPDATE user_aims SET (user_aim, daily_cal)=('{aim}',{cal})  WHERE user_id = {message.from_user.id};
                ELSE
                    INSERT INTO user_aims 
                    (user_aim, daily_cal, user_id) VALUES ('{aim}',{cal}, {message.from_user.id})
                    ;
                END IF;
                
            END;
            $$
                
            """)

        conn.commit()
        await bot.send_message(
            message.chat.id,
            text=l.printer(message.from_user.id, 'info').format(message.from_user.first_name,weight,height,imt,imt_using_words)
            )
        await message.answer(text=l.printer(message.from_user.id, 'SuccesfulReg'), reply_markup=kb.keyboard(message.from_user.id, 'main_menu'))
        await state.clear()
    except Exception as e:
        print(e)
        await state.set_state(REG.weight)
        await message.answer(l.printer(message.from_user.id, 'weight'), reply_markup=types.ReplyKeyboardRemove())






def calculate_imt_description(imt, message:Message):
    if round(imt) < 15:
        return l.printer(message.from_user.id, 'imt1')
    elif round(imt) in range(14, 18):
        return l.printer(message.from_user.id, 'imt2')
    elif round(imt) in range(18, 25):
        return l.printer(message.from_user.id, 'imt3')
    elif round(imt) in range(25, 30):
        return l.printer(message.from_user.id, 'imt4')
    else:
        return l.printer(message.from_user.id, 'imt5')

def calculate_calories(sex, weight, height, age, message):
    if sex == l.printer(message.from_user.id, 'kbMAN'):
        return (10 * weight) + (6.25 * height) - (5 * age) + 5
    elif sex == l.printer(message.from_user.id, 'kbWOMAN'):
        return (10 * weight) + (6.25 * height) - (5 * age) - 161



def split_message(text, user_id):
    a = list(text.split("\n"))
    cursor.execute("SELECT lang FROM user_lang WHERE user_id = {}".format(user_id))
    ll = cursor.fetchone()[0]
    b = ''
    translator = Translator(from_lang='ru', to_lang=ll)
    for i in range(len(a)):
        b = b + translator.translate(a[i]) + '\n'


    max_length = 4096
    return [text[i:i + max_length] for i in range(0, len(text), max_length)]
def is_not_none(variable):
    return 0 if variable is None else variable


async def send_photo_to_deepseek(api_url, api_key, image_path, query):
    try:
        with open(image_path, 'rb') as image_file:
            # Создаем словарь с данными для отправки
            files = {
                'file': (image_path, image_file, 'image/jpeg'),  # Указываем тип содержимого
                'query': (None, query)  # Текстовый запрос
            }

            # Заголовки запроса (включая API-ключ)
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'multipart/form-data'
            }

            # Отправляем POST-запрос на сервер
            response = requests.post(api_url, headers=headers, files=files)
            return response.text


    except Exception as e:
        print(f"Ошибка при генерации плана: {str(e)}")
        return f"Ошибка при генерации плана: {e}"





async def generate(zap):
        try:

            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=  [
                    {"role": "system", "content": "You are a personal trainer"},
                    {"role": "user", "content": zap},
                ]
,
                stream=False
            )

            return response.choices[0].message.content
        except Exception as e:
            print(f"Ошибка при генерации плана: {str(e)}")
            return f"Ошибка при генерации плана: {e}"


@dp.message(F.text.in_({'Добавить тренировки',"Añadir formación" ,'Add training','Ajouter une formation' , 'Ausbildung hinzufügen'}))
async def tren(message: Message, state: FSMContext):
    await bot.send_message(message.chat.id, text=l.printer(message.from_user.id, 'TrenType'), reply_markup=kb.keyboard(message.from_user.id, 'tren'))
    await state.set_state(REG.types)
@dp.message(REG.types)
async def tren_type(message: Message, state: FSMContext):
    await state.update_data(types=message.text)
    await state.set_state(REG.length)
    await message.answer(text = l.printer(message.from_user.id, 'trenMIN'))
@dp.message(REG.length)
async def tren_len(message: Message, state: FSMContext):
        await state.update_data(length=message.text)
        data = await state.get_data()
        cursor.execute(f"SELECT weight FROM user_health WHERE user_id = {message.from_user.id} AND date = '{datetime.datetime.now().strftime('%Y-%m-%d')}'")
        weight = float(cursor.fetchone()[0])
        time = int(data['length'])
        intensivity = intensiv(data['types'], message.from_user.id)

        tren_cal = round((weight * intensivity * time / 24), 3)
        cursor.execute(
        f"""INSERT INTO user_training (user_id, date, training_cal, tren_time) 
        VALUES ({message.from_user.id}, '{datetime.datetime.now().strftime('%Y-%m-%d')}', {tren_cal}, {time})""")
        conn.commit()

        cursor.execute(f"SELECT SUM(training_cal) FROM user_training WHERE date = '{datetime.datetime.now().strftime('%Y-%m-%d')}' AND user_id = {message.from_user.id}")
        result = cursor.fetchone()[0]
        await bot.send_message(message.chat.id, text=l.printer(message.from_user.id, 'TrenCal').format(tren_cal),
                         )



        await bot.send_message(message.chat.id,
                         text=l.printer(message.from_user.id, 'TrenCalDay').format(message.from_user.first_name,result), reply_markup=kb.keyboard(message.from_user.id, 'main_menu'))
        await state.clear()


def intensiv(intensiv, id):
    if intensiv == l.printer(id, 'tren1'):
        return 2.5
    if intensiv == l.printer(id, 'tren2'):
        return 3
    if intensiv == l.printer(id, 'tren3'):
        return 3.5

def replace_none_with_zero_in_list(lst, index):
    if 0 <= index < len(lst):
        if lst[index] is None:  # Проверяем, является ли элемент None
            lst[index] = 0  # Заменяем на 0
    return lst


@dp.message(F.text.in_({'Ввести еду за день', "Das Essen des Tages einführen" ,"Enter a day's worth of food","Introducir la comida del día" , 'Présenter les aliments du jour'}))
async def food1(message: Message, state: FSMContext):
    await message.answer(text=l.printer(message.from_user.id, 'ChooseTheWay'), reply_markup=kb.keyboard(message.from_user.id, 'food'))
    await state.set_state(REG.food)


@dp.message(REG.food)
async def foodchoise(message: Message, state: FSMContext):
    await state.update_data(food=message.text)
    await state.set_state(REG.food_photo)

    data = await state.get_data()
    if data['food'] == l.printer(message.from_user.id, 'kbfood2'):
        await message.answer(text=l.printer(message.from_user.id, 'SendMes'), reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(REG.food_list)

    if data['food'] == l.printer(message.from_user.id, 'kbfood1'):
        await message.answer(text=l.printer(message.from_user.id, 'SengFoto'), reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(REG.food_photo)

@dp.message(REG.food_list)
async def names(message:Message, state: FSMContext):
    await state.update_data(food_list = message.text.split(","))
    await bot.send_message(message.chat.id, text=l.printer(message.from_user.id, 'gram'))
    await state.set_state(REG.grams)


@dp.message(REG.food_photo)
async def handle_photo(message:Message, state: FSMContext):
    await state.update_data(food_photo=message.photo)
    data = await state.get_data()
    photo = data['food_photo'][-1]

    await state.clear()
    name_a = []
    file_info = await bot.get_file(photo.file_id)
    downloaded_file = await bot.download_file(file_info.file_path)
    save_path = 'photo.jpg'
    with open(save_path, 'wb') as new_file:
         new_file.write(downloaded_file.read())
    await bot.send_message(message.chat.id, l.printer(message.from_user.id, 'foto'))
    img =  tf.keras.utils.load_img("photo.jpg", target_size=(img_height, img_width))
    img_array =  tf.keras.utils.img_to_array(img)
    img_array =  tf.expand_dims(img_array, 0)
    predictions = model.predict(img_array)
    score =  tf.nn.softmax(predictions[0])
    lol =  str(class_names[np.argmax(score)])
    translator =  Translator(from_lang="en", to_lang="ru")
    name_a.append(translator.translate(lol).title())
    await state.set_state(REG.grams1)
    await bot.send_message(message.chat.id, text=l.printer(message.from_user.id, 'gram'))
    await state.update_data(food_list=name_a)


@dp.message(F.text.in_({'Присоедениться к чату',"Dem Chatraum beitreten" ,"Join the chat room" ,"Rejoindre le salon de discussion" , 'Unirse a la sala de chat'}))
async def chat(message:Message):
    await message.answer(text = 'https://t.me/+QVhMA2topDgzOWVi', reply_markup=kb.keyboard(message.from_user.id, 'main_menu'))


@dp.message(F.text.in_({'Добавить выпитый стаканчик воды', "Añade un vaso de agua", "Ajoutez un verre d'eau potable" ,"Add a drunken glass of water" , 'Ein getrunkenes Glas Wasser hinzufügen'}))
async def chating(message:Message):

    cursor.execute(f"""
    
            SELECT SUM(count) FROM water WHERE data = '{datetime.datetime.now().strftime('%Y-%m-%d')}' AND user_id = {message.from_user.id};
       """)
    lst = cursor.fetchone()
    drank = lst[0] if lst[0] else 0
    cursor.execute(f"""
    DO $$
    BEGIN
        IF EXISTS(SELECT * FROM water WHERE user_id = {message.from_user.id} AND data = '{datetime.datetime.now().strftime('%Y-%m-%d')}') THEN
            UPDATE water SET count = {drank + 1} WHERE user_id = {message.from_user.id} AND data = '{datetime.datetime.now().strftime('%Y-%m-%d')}';
        ELSE
            INSERT INTO water (data, count, user_id) VALUES ('{datetime.datetime.now().strftime('%Y-%m-%d')}', 1, {message.from_user.id});
        END IF;
    END;
    $$
""")



    conn.commit()
    await message.answer(text = l.printer(message.from_user.id, 'cup'), reply_markup=kb.keyboard(message.from_user.id, 'main_menu'))

@dp.message(REG.grams1)
async def grams1(message:Message, state: FSMContext):
    try:
        await state.update_data(grams1=message.text)
        data = await state.get_data()
        gram = data['grams1'].split(",")[0]
        name_a = data['food_list']
        cursor.execute(f"SELECT lang FROM user_lang WHERE user_id = {message.from_user.id}",
                       )
        ll = cursor.fetchone()[0]
        translator = Translator(from_lang="ru", to_lang=ll)
        print(name_a, data, gram)

        prod_kbgu = await generate(
            f'Представь кбжу {name_a} в виде чисел в формате файла json {'{"name":{cal:"",b:””, g:””, u:””}, }'}')
        pattern = r'\"(\w+)\":\s*{\s*\"cal\":\s*(\d+\.?\d*),\s*\"b\":\s*(\d+\.?\d*),\s*\"g\":\s*(\d+\.?\d*),\s*\"u\":\s*(\d+\.?\d*)\s*}'

        # Результирующий словарь
        result = {}

        # Поиск всех совпадений
        matches = re.findall(pattern, prod_kbgu)
        for match in matches:
            dish, cal, b, g, u = match
            result[dish] = {
                "cal": float(cal),
                "b": float(b),
                "g": float(g),
                "u": float(u)
            }

        # Преобразование в JSON
        result_json = json.dumps(result, ensure_ascii=False, indent=4)
        print("Извлеченные данные в формате JSON:")
        print(result_json)

        # Преобразование JSON-строки в словарь
        json_data = json.loads(result_json)

        # Расчет БЖУ и калорий для каждого блюда
        for m in range(len(name_a)):
            dish_name = name_a[m]  # Название блюда
            if dish_name in json_data:  # Проверка, есть ли блюдо в данных
                b = round(float(json_data[dish_name]["b"]) * float(gram[m]) / 100, 3)
                g = round(float(json_data[dish_name]["g"]) * float(gram[m]) / 100, 3)
                u = round(float(json_data[dish_name]["u"]) * float(gram[m]) / 100, 3)
                food_cal = round(float(json_data[dish_name]["cal"]) * float(gram[m]) / 100, 3)
                print(b, g, u, food_cal, translator.translate(name_a[m]))
                a = f"""INSERT INTO food
                                                (
                                                    user_id, 
                                                    date, 
                                                    name_of_food,
                                                    b, g, u,
                                                    cal
                                                )
                                                VALUES
                                                (
                                                    {message.from_user.id}, 
                                                    '{datetime.datetime.now().strftime('%Y-%m-%d')}',
                                                    '{translator.translate(name_a[m]).title()}',
                                                    {b}, {g}, {u},
                                                    {food_cal}
                                                )
                                            """
                cursor.execute(a)
                conn.commit()


        await message.answer(text=l.printer(message.from_user.id, "InfoInBase"),
                             reply_markup=kb.keyboard(message.from_user.id, 'main_menu'))
        await state.clear()
    except:
        await message.answer(text=l.printer(message.from_user.id, 'SendMes'), reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(REG.food_list)


@dp.message(REG.grams)
async def grams(message:Message, state: FSMContext):
    try:
        await state.update_data(grams=message.text)
        data = await state.get_data()
        gram = data['grams'].split(",")
        name_a =  data['food_list']
        name_a = [dish.strip() for dish in name_a]
        name_b = [i.replace(" ", "") for i in name_a]
        cursor.execute(f"SELECT lang FROM user_lang WHERE user_id = {message.from_user.id}",
                       )
        ll = cursor.fetchone()[0]
        translator = Translator(from_lang=ll, to_lang="ru")
        print(name_a, data, gram)
        prod_kbgu = await generate(f'Представь кбжу {name_b} в виде чисел в формате файла json {'{"name":{cal:"",b:””, g:””, u:””}, }'}')
        pattern = r'\"(\w+)\":\s*{\s*\"cal\":\s*(\d+\.?\d*),\s*\"b\":\s*(\d+\.?\d*),\s*\"g\":\s*(\d+\.?\d*),\s*\"u\":\s*(\d+\.?\d*)\s*}'

        # Результирующий словарь
        result = {}

        # Поиск всех совпадений
        matches = re.findall(pattern, prod_kbgu)
        for match in matches:
            dish, cal, b, g, u = match
            result[dish] = {
                "cal": float(cal),
                "b": float(b),
                "g": float(g),
                "u": float(u)
            }

        # Преобразование в JSON
        result_json = json.dumps(result, ensure_ascii=False, indent=4)
        print("Извлеченные данные в формате JSON:")
        print(result_json)

        # Преобразование JSON-строки в словарь
        json_data = json.loads(result_json)



        # Расчет БЖУ и калорий для каждого блюда
        for m in range(len(name_b)):
            dish_name = name_b[m]  # Название блюда
            if dish_name in json_data:  # Проверка, есть ли блюдо в данных
                b = round(float(json_data[dish_name]["b"]) * float(gram[m]) / 100, 3)
                g = round(float(json_data[dish_name]["g"]) * float(gram[m]) / 100, 3)
                u = round(float(json_data[dish_name]["u"]) * float(gram[m]) / 100, 3)
                food_cal = round(float(json_data[dish_name]["cal"]) * float(gram[m]) / 100, 3)
                print(b, g, u, food_cal, translator.translate(name_a[m]))
                a = f"""INSERT INTO food
                                        (
                                            user_id, 
                                            date, 
                                            name_of_food,
                                            b, g, u,
                                            cal
                                        )
                                        VALUES
                                        (
                                            {message.from_user.id}, 
                                            '{datetime.datetime.now().strftime('%Y-%m-%d')}',
                                            '{translator.translate(name_a[m]).title()}',
                                            {b}, {g}, {u},
                                            {food_cal}
                                        )
                                    """
                cursor.execute(a)
                conn.commit()

        await message.answer(text=l.printer(message.from_user.id, "InfoInBase"), reply_markup=kb.keyboard(message.from_user.id, 'main_menu'))
        await state.clear()
    except:
        await message.answer(text=l.printer(message.from_user.id, 'SendMes'), reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(REG.food_list)





@dp.message(F.text.in_({'Недельный план питания и тренировок' ,"Wöchentlicher Ernährungs- und Trainingsplan" ,"Plan semanal de nutrición y entrenamiento" ,"Weekly nutrition and exercise plan" , 'Plan semanal de dieta y entrenamiento'}))
async def ai(message: Message, state: FSMContext):
    await message.answer( text=l.printer(message.from_user.id, 'InProcess'))
    cursor.execute(
        "SELECT lang FROM user_lang WHERE user_id = {}".format(message.from_user.id)
    )
    ll = cursor.fetchone()[0]
    translator = Translator(from_lang=ll, to_lang='ru')
    cursor.execute(
        "SELECT user_aim, daily_cal FROM user_aims WHERE user_id = {}".format(message.from_user.id)
    )
    aim, cal = cursor.fetchone()
    cursor.execute(
        f"SELECT user_sex, date_of_birth FROM user_main WHERE user_id = {message.from_user.id} "
    )
    sex, age = cursor.fetchone()
    cursor.execute(
        f"SELECT imt, weight, height FROM user_health WHERE user_id = {message.from_user.id}"
    )
    imt, weight, height = cursor.fetchone()
    aim, cal, sex, age, imt, weight, height = translator.translate(aim), cal,translator.translate(sex), age, imt,weight, height
    zap_pit=  l.printer(message.from_user.id, 'pitforweek').format(sex, height, age, imt, aim)
    plan_pit= await generate(zap_pit)
    zap_tren= l.printer(message.from_user.id, 'trenforweek').format(sex, height, age, imt, aim, plan_pit)
    plan_train = await generate(zap_tren)

    try:
        if plan_pit and plan_train:
            # Разделяем длинные сообщения на части
            for part in split_message(plan_pit, message.from_user.id):
                await message.answer(part)

            for part in split_message(plan_train, message.from_user.id):
                await message.answer(part)

            await message.answer(
                text=l.printer(message.from_user.id, 'recommend'),
                reply_markup=kb.keyboard(message.from_user.id, 'main_menu'))

        else:
            await bot.send_message(message.chat.id, text="Not enough info about user", reply_markup=kb.keyboard(message.from_user.id, 'main_menu'))
    except Exception as e:
        print(f"Ошибка при генерации плана: {str(e)}")
        return f"Ошибка при генерации плана: {e}"


@dp.message(F.text.in_({'Помочь с рецептом', "Ayuda con una receta" ,"Hilfe bei einem Rezept" ,"Aide pour une recette", 'Help with the recipe'}))
async def ai_food(message: Message, state: FSMContext):
    await message.answer(text = l.printer(message.from_user.id, 'choosemeal'), reply_markup=kb.keyboard(message.from_user.id, 'meals'))
    await state.set_state(REG.food_meals)

@dp.message(REG.food_meals)
async def ai_food_meals(message: Message, state: FSMContext):
    await state.update_data(food_meals=message.text)
    data = await state.get_data()
    cursor.execute(f"SELECT lang FROM user_lang WHERE user_id = {message.from_user.id}",
                   )

    ll = cursor.fetchone()[0]
    translator = Translator(from_lang=ll, to_lang="ru")
    meal = translator.translate(data['food_meals'])
    zap = l.printer(message.from_user.id, 'mealai').format(meal)
    await message.answer( text=l.printer(message.from_user.id, 'InProcess'))
    plan_pit= await generate(zap)
    try:
        if plan_pit:
            # Разделяем длинные сообщения на части
            for part in split_message(plan_pit, message.from_user.id):
                await bot.send_message(message.chat.id, text=part, reply_markup=kb.keyboard(message.from_user.id, 'main_menu'))
        else:
            await bot.send_message(message.chat.id, text="Не удалось получить данные пользователя.",
                                   reply_markup=kb.keyboard(message.from_user.id, 'main_menu'))
    except Exception as e:
        print(f"Ошибка при генерации плана: {str(e)}")
        return f"Ошибка при генерации плана: {e}"
    await state.clear()


@dp.message(F.text.in_({ 'Помочь с тренировкой',"Help with training", "Aide à la formation" ,"Hilfe bei der Ausbildung" , "Ayuda a la formación"}))
async def ai_food(message: Message, state: FSMContext):
    await message.answer(text = l.printer(message.from_user.id, 'trenchoose'), reply_markup=kb.keyboard(message.from_user.id, 'tren_type'))
    await state.set_state(REG.train)

@dp.message(REG.train)
async def train(message: Message, state: FSMContext):
    await state.update_data(train=message.text)
    data = await state.get_data()
    cursor.execute(f"SELECT lang FROM user_lang WHERE user_id = {message.from_user.id}",
                   )

    ll = cursor.fetchone()[0]
    translator = Translator(from_lang=ll, to_lang="ru")
    type_tren = translator.translate(data['train'])
    await state.clear()
    await message.answer( text=l.printer(message.from_user.id, 'InProcess'))
    cursor.execute(f"SELECT imt FROM user_health WHERE date = '{datetime.datetime.now().strftime('%Y-%m-%d')}' AND user_id = {message.from_user.id}")
    imt = float(cursor.fetchone()[0])
    zap = l.printer(message.from_user.id, 'trenai').format(type_tren, imt)
    tren = await generate(zap)
    await state.update_data(tren_ai=tren)

    try:
        if tren:
            for part in split_message(tren, message.from_user.id):
                await bot.send_message(message.chat.id, text=part, reply_markup=kb.keyboard(message.from_user.id, 'tren_choise'))
                await state.set_state(REG.tren_choiser)


        else:
            await bot.send_message(message.chat.id, text="Не удалось получить данные пользователя.",
                                   reply_markup=kb.keyboard(message.from_user.id, 'main_menu'))
    except Exception as e:
        print(f"Ошибка при генерации плана: {str(e)}")
        return f"Ошибка при генерации плана: {e}"

@dp.message(REG.tren_choiser)
async def choising(message: Message, state: FSMContext):
    await state.update_data(tren_choiser=message.text)
    data = await state.get_data()
    mes = data['tren_choiser']
    if mes == l.printer(message.from_user.id, 'return'):
        await message.answer(text = l.printer(message.from_user.id, 'ret2main'),reply_markup=kb.keyboard(message.from_user.id, 'main_menu'))
    else:
        c = 0
        tren = data["tren_ai"]
        for i in range(len(tren_list)):
            for m in range(len(tren_list[i])):
                if tren_list[i][m] in tren:
                    gif_url = GIF_LIBRARY.get(tren_list[i][0], None)

                    if gif_url:
                        await bot.send_animation(
                            chat_id=message.chat.id,
                            animation=gif_url,
                            caption=l.printer(message.from_user.id, 'correct_tech').format(tren_list[i][m]),
                            reply_markup=kb.keyboard(message.from_user.id, 'main_menu')
                        )
                    else:
                        c = c + 1
        if c > 0:
            gif_url = "https://media.giphy.com/media/xT9IgIc0lryrxvqVGM/giphy.gif"
            await bot.send_animation(
                chat_id=message.chat.id,
                animation=gif_url,
                reply_markup=kb.keyboard(message.from_user.id, 'main_menu')
            )

        await message.answer(text = l.printer(message.from_user.id, "ret2main"),reply_markup=kb.keyboard(message.from_user.id, 'main_menu'))


    await state.clear()


@dp.message(F.text.in_({'Вход в програму' ,'Acceder al programa' , "Aufnahme in das Programm" ,"Entrée dans le programme" , "Entering the program"}))
async def ais(message: Message, state: FSMContext):
    await message.answer( text=l.printer(message.from_user.id, 'begining'),reply_markup=kb.keyboard(message.from_user.id, 'main_menu')
)
@dp.message(F.text.in_({'Смена языка', "Change language" , "Changement de langue" , "Änderung der Sprache" ,"Cambio lingüístico"}))
async def leng2(message: Message, state: FSMContext):
    await state.set_state(REG.leng2)
    await message.answer(text = 'Please, chose your lenguage:', reply_markup=kb.keyboard(message.from_user.id, 'lenguage'))





@dp.message(REG.leng2)
async def start2(message: Message, state: FSMContext):
    await state.update_data(leng2=message.text)
    data = await state.get_data()
    cursor.execute(f"""

    UPDATE user_lang SET lang='{languages[data['leng2']]}' WHERE user_id = {message.from_user.id};

            """
            )
    conn.commit()
    await message.answer(text =data['leng2'], reply_markup=kb.keyboard(message.from_user.id, 'main_menu'))
    await state.clear()
@dp.message(F.text.in_({'Сводка', "Resumen" ,"Zusammenfassung" , "Résumé" , "Summary"}))
async def svod(message: Message, state: FSMContext):
    await state.set_state(REG.new_weight)
    await message.answer(l.printer(message.from_user.id, 'weight'), reply_markup=types.ReplyKeyboardRemove())


@dp.message(REG.new_weight)
async def new_we(message: Message, state: FSMContext):
    await state.update_data(new_weight = message.text)
    await state.set_state(REG.new_height)
    await message.answer(l.printer(message.from_user.id, 'height'))


@dp.message(REG.new_height)
async def new_he(message: Message, state: FSMContext):
    await state.update_data(new_height = float(message.text))
    await message.answer(text=l.printer(message.from_user.id, 'svoPERIOD'),
                         reply_markup=kb.keyboard(message.from_user.id, 'svo'))
    await state.set_state(REG.svo)

@dp.message(REG.svo)
async def svodka(message: Message, state: FSMContext):
    await state.update_data(tren_choiser=message.text)
    data = await state.get_data()
    mes = data['tren_choiser']
    new_weight = data['new_weight']
    new_height = float(data['new_height'])
    if "," in new_weight:
        we1 = message.text.split(",")
        new_weight = int(we1[0]) + int(we1[1]) / 10 ** len(we1[1])
    else:
        new_weight = float(new_weight)
    cursor.execute(f"""
    SELECT * FROM user_main WHERE user_id = {message.from_user.id}
    """)
    data_sql = cursor.fetchall()[0]
    sex, age = data_sql[1], int(data_sql[2])
    await state.clear()
    imt = round(new_weight / ((new_height / 100) ** 2), 3)
    imt_using_words = calculate_imt_description(imt, message)
    cal = float(calculate_calories(sex, new_weight, new_height, age, message))

    cursor.execute(f"""
                    INSERT INTO user_health (user_id,imt,imt_str,cal,date, weight, height) VALUES ({message.from_user.id},{imt},'{imt_using_words}',{cal},'{datetime.datetime.now().strftime('%Y-%m-%d')}', {new_weight}, {new_height} )
                    ;
    """)
    conn.commit()
    try:
        if mes == 'День' or mes == "Day" or mes == "Jour" or mes == "Tag" or mes == "Día":
            cursor.execute("SELECT SUM(training_cal) FROM user_training WHERE date = '{}' AND user_id = {}".format(datetime.datetime.now().strftime('%Y-%m-%d'), message.from_user.id))
            result_tren = cursor.fetchone()
            col_call_tren = result_tren[0] if result_tren[0] else 0
            cursor.execute("SELECT SUM(cal) FROM food WHERE date = '{}' AND user_id = {}".format(datetime.datetime.now().strftime('%Y-%m-%d'), message.from_user.id))
            result_cal_food = cursor.fetchone()
            col_cal_food = result_cal_food[0] if result_cal_food[0] else 0
            cursor.execute("SELECT SUM(b) FROM food WHERE date = '{}' AND user_id = {}".format(datetime.datetime.now().strftime('%Y-%m-%d'), message.from_user.id))
            result_b = cursor.fetchone()
            col_b = round(result_b[0], 3) if result_b[0] else 0
            cursor.execute("SELECT SUM(g) FROM food WHERE date = '{}' AND user_id = {}".format(datetime.datetime.now().strftime('%Y-%m-%d'), message.from_user.id))
            result_g = cursor.fetchone()
            col_g = round(result_g[0], 3) if result_g[0] else 0
            cursor.execute("SELECT SUM(u) FROM food WHERE date = '{}' AND user_id = {}".format(datetime.datetime.now().strftime('%Y-%m-%d'), message.from_user.id))
            result_u = cursor.fetchone()
            col_u = round(result_u[0], 3) if result_u[0] else 0
            cursor.execute("SELECT SUM(count) FROM water WHERE data = '{}' AND user_id = {}".format(datetime.datetime.now().strftime('%Y-%m-%d'), message.from_user.id))
            result_wat = cursor.fetchone()
            col_wat = round(result_wat[0], 3) if result_wat[0] else 0
            cursor.execute("SELECT name_of_food FROM food WHERE date = '{}' AND user_id = {}".format(datetime.datetime.now().strftime('%Y-%m-%d'), message.from_user.id))
            ff = ''
            result_ff = cursor.fetchall()
            for i in result_ff:
                ff += str(i[0])
                ff += ', '

            await bot.send_message(message.chat.id, text=l.printer(message.from_user.id, 'svoDAY').format(message.from_user.first_name,datetime.datetime.now().strftime('%Y-%m-%d'), round(col_call_tren, 3) if col_call_tren else 0, ff,round(col_cal_food, 3) if col_cal_food else 0, col_b if col_b else 0, col_g if col_g else 0, col_u if col_u else 0, col_wat * 300 if col_wat else 0)
                             ,reply_markup=kb.keyboard(message.from_user.id, 'main_menu'))
        elif mes == 'Месяц' or mes == "Mes" or mes == "Monat" or mes == "Mois" or mes == "Month":
            weight_month = []
            sr_b = []
            sr_g = []
            sr_u = []
            sr_cal = []
            sr_w = []
            sr_tren = []
            for i in range(1, 32):
                datee = f'{str(datetime.datetime.now().year)}-{str(datetime.datetime.now().month).zfill(2)}-{str(i).zfill(2)}'
                cursor.execute("SELECT weight FROM user_health WHERE user_id = {} AND date = '{}' ".format(message.from_user.id, datetime.datetime.now().strftime('%Y-%m-%d')))
                weight_data = cursor.fetchall()
                if weight_data:
                    weight_month.append(weight_data)
                cursor.execute("SELECT sum(b) FROM food WHERE user_id = {} AND date = '{}'".format(message.from_user.id, datee))
                b_data = cursor.fetchone()
                if b_data:
                    sr_b.append(b_data[0])
                cursor.execute("SELECT sum(g) FROM food WHERE user_id = {} AND date = '{}'".format(message.from_user.id, datee))
                g_data = cursor.fetchone()
                if g_data:
                    sr_g.append(g_data[0])
                cursor.execute("SELECT sum(u) FROM food WHERE user_id = {} AND date = '{}'".format(message.from_user.id, datee))
                u_data = cursor.fetchone()
                if u_data:
                    sr_u.append(u_data[0])
                cursor.execute("SELECT sum(count) FROM water WHERE user_id = {} AND data = '{}'".format(message.from_user.id, datee))
                w_data = cursor.fetchone()
                if w_data:
                    sr_w.append(w_data[0])
                cursor.execute("SELECT sum(training_cal) FROM user_training WHERE user_id = {} AND date = '{}'".format(message.from_user.id, datee))
                cal_data = cursor.fetchone()
                if cal_data:
                    sr_cal.append(cal_data[0])
                cursor.execute("SELECT sum(tren_time) FROM user_training WHERE user_id = {} AND date = '{}'".format(message.from_user.id, datee))
                time_data = cursor.fetchone()
                if time_data:
                    sr_tren.append(time_data[0])
            if weight_month and sr_b and sr_g and sr_u and sr_cal and sr_tren and sr_w:
                weig_1 = weight_month[0][0]
                weig_2 = new_weight
                new_sr_b = list(filter(is_not_none, sr_b))
                new_sr_g = list(filter(is_not_none, sr_g))
                new_sr_u = list(filter(is_not_none, sr_u))
                new_sr_w = list(filter(is_not_none, sr_w))
                new_sr_cal = list(filter(is_not_none, sr_cal))
                new_sr_tren = list(filter(is_not_none, sr_tren))
                if sum(new_sr_b) > 0:
                    avg_b = round(sum(new_sr_b) / len(new_sr_b), 3)
                else:
                    avg_b = 0
                if sum(new_sr_g) > 0:
                    avg_g = round(sum(new_sr_g) / len(new_sr_g), 3)
                else:
                    avg_g = 0
                if sum(new_sr_u) > 0:
                    avg_u = round(sum(new_sr_u) / len(new_sr_u), 3)
                else:
                    avg_u = 0
                if sum(new_sr_w) > 0:
                    avg_w = sum(new_sr_w) / len(new_sr_w) * 300
                else:
                    avg_w = 0

                avg_training_time = round(sum(new_sr_tren) / len(new_sr_tren), 3) if round(
                    sum(new_sr_tren) / len(new_sr_tren), 3) else 0  # Расчет среднего времени тренировок
                avg_calories_burned = round(sum(new_sr_cal) / len(new_sr_cal), 3) if round(
                    sum(new_sr_cal) / len(new_sr_cal), 3) else 0  # Расчет среднего числа сожжённых калорий
                await bot.send_message(message.chat.id, text=l.printer(message.from_user.id, 'svoMONTH').format(message.from_user.first_name, weig_1[0],weig_2, avg_training_time, avg_calories_burned, avg_b, avg_g, avg_u, avg_w),
                                 reply_markup=kb.keyboard(message.from_user.id, 'main_menu'))
            else:
                await bot.send_message(message.chat.id, "Нет данных за этот месяц.")
        elif mes == 'Год' or mes == "Year" or mes == "Année" or mes == "Jahr" or mes == "Año":
            all_data = []
            total_food_cal = 0
            total_b = 0
            total_g = 0
            total_u = 0
            total_w = 0
            weight_data_all = []
            food_months_with_data = set()

            current_date = datetime.datetime.now()

            for i in range(12):
                current_month = current_date.month - i
                current_year = current_date.year

                if current_month <= 0:
                    current_year -= 1
                    current_month += 12

                first_day_of_month = datetime.date(current_year, current_month, 1)
                if current_month == 12:
                    last_day_of_month = datetime.date(current_year + 1, 1, 1) - datetime.timedelta(days=1)
                else:
                    last_day_of_month = datetime.date(current_year, current_month + 1, 1) - datetime.timedelta(days=1)

                cursor.execute("""
                        SELECT SUM(cal), SUM(b), SUM(g), SUM(u)
                        FROM food 
                        WHERE date >= '{}' AND date <= '{}' AND user_id = {}
                    """.format(
                    first_day_of_month.strftime('%Y-%m-%d'), last_day_of_month.strftime('%Y-%m-%d'), message.from_user.id))
                result_food = cursor.fetchone()
                cursor.execute("""
                              SELECT SUM(count)
                              FROM water
                              WHERE data >= '{}' AND data <= '{}' AND user_id = {}
                          """.format(
                    first_day_of_month.strftime('%Y-%m-%d'), last_day_of_month.strftime('%Y-%m-%d'), message.from_user.id))
                result_wat = cursor.fetchone()
                if result_food and result_food[0]:
                    all_data.append(result_food)
                    total_food_cal += result_food[0]
                    total_b += result_food[1]
                    total_g += result_food[2]
                    total_u += result_food[3]
                    food_months_with_data.add((current_year, current_month))
                if result_wat and result_wat[0]:
                    total_w += result_wat[0]

                    #
                cursor.execute("""
                        SELECT weight 
                        FROM user_health
                        WHERE date >= '{}' AND date <= '{}' AND user_id = {}
                        
                        ORDER BY date ASC
                    """.format(first_day_of_month.strftime('%Y-%m-%d'), last_day_of_month.strftime('%Y-%m-%d'),message.from_user.id))
                weight_data = cursor.fetchall()

                if weight_data:
                    weight_data_all.extend(weight_data)

            if weight_data_all:
                weight_data_all.sort(key=lambda x: x[0])
                start_weight = weight_data_all[0][0]
                end_weight = new_weight
            else:
                start_weight = 'no info'
                end_weight = 'no info'

            cursor.execute("""
                    SELECT AVG(training_cal) 
                    FROM user_training 
                    WHERE user_id = {}
                """.format(message.from_user.id,))
            result_train = cursor.fetchone()
            avg_train_cal = result_train[0] if result_train and result_train[0] else 0

            avg_food_cal = total_food_cal / len(food_months_with_data) if food_months_with_data else 0
            avg_b = round(total_b / len(food_months_with_data), 3) if food_months_with_data else 0
            avg_g = round(total_g / len(food_months_with_data), 3) if food_months_with_data else 0
            avg_u = round(total_u / len(food_months_with_data), 3) if food_months_with_data else 0
            all_data = list(filter(is_not_none, all_data))
            await bot.send_message(message.chat.id, text=l.printer(message.from_user.id, 'svoYEAR').format('\n', start_weight,end_weight, '\n', round(avg_train_cal , 3), '\n', round(avg_food_cal, 3), '\n' , round(float(all_data[-1][0]), 3) if round(float(all_data[-1][0]), 3) else 0,round(float(all_data[0][0]), 3) if round(float(all_data[0][0]), 3) else 0 , avg_b, avg_g, avg_u, round(all_data[-1][1], 3) if round(all_data[-1][1], 3) else 0, round(all_data[-1][2], 3) if round(all_data[-1][2], 3) else 0, round(all_data[-1][3], 3) if round(all_data[-1][3], 3) else 0, round(all_data[0][1], 3) if round(all_data[0][1], 3) else 0, round(all_data[0][2], 3) if round(all_data[0][2], 3) else 0, round(all_data[0][3], 3) if round(all_data[0][3], 3) else 0, total_w / len(food_months_with_data) * 300 if total_w / len(food_months_with_data) * 300 else 0),
                             reply_markup=kb.keyboard(message.from_user.id, 'main_menu'))
    except Exception as e:
        print(f"Ошибка при генерации плана: {str(e)}")
        return f"Ошибка при генерации плана: {e}"
#    except :
 #       await state.set_state(REG.new_weight)
 #       await message.answer(l.printer(message.from_user.id, 'weight'), reply_markup=types.ReplyKeyboardRemove())



async def main():

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())