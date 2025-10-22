import aiogram
import keyboards as kb
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command



class REG(StatesGroup):
    food = State()

async def f1(message:Message,  state: FSMContext):
    await message.answer(text='Выбери, как ты хотел бы добавить сьеденную пищу?', reply_markup=kb.food)
    await state.set_state(REG.food)

@dp.message(REG.food)
async def foodchoise(message: Message, state: FSMContext):
        await state.update_data(food=message.text)
        data = await state.get_data()
        if data['food'] == 'С помощью текста':
