from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram import executor
from aiogram.dispatcher.filters.state import State, StatesGroup

import sqlalchemy as db
import sqlite3
from sqlalchemy.ext.declarative import *
from sqlalchemy import *
from sqlalchemy.orm import sessionmaker

import time

import requests
import json

bot = Bot(token='')
dp = Dispatcher(bot, storage=MemoryStorage())

engine = db.create_engine('sqlite+pysqlite:///database.db', echo=True)
Base = declarative_base()

Session = sessionmaker(bind=engine, future=True, expire_on_commit=False)
session = Session()

class Persons(Base):
    __tablename__ = 'persons'

    UserID = Column(Integer, name='UserId', primary_key=True)


Base.metadata.create_all(engine)

@dp.message_handler(commands=['start'], state="*")
async def start(message):
    results = session.query(Persons).all()

    create = KeyboardButton("Получать стоимость акций")
    buttons = ReplyKeyboardMarkup(resize_keyboard=True)
    buttons.add(create)

    await message.answer("Добро пожаловать! Что вы хотите сделать?",
                         reply_markup=buttons)
    if len(results) > 0:
        return
    new_track = Persons(UserID=message.from_user.id)
    session.add(new_track)
    session.commit()

@dp.message_handler(lambda message: message.text == "Получать стоимость акций", state="*")
async def choose_company(message):
    create = KeyboardButton("Yandex")
    buttons = ReplyKeyboardMarkup(resize_keyboard=True)
    buttons.add(create)

    await message.answer("Выберете компанию", reply_markup=buttons)

@dp.message_handler(lambda message: message.text == "Yandex", state="*")
async def yandex(message):
    while True:
        url = 'https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities.json?first=350'
        response = requests.get(url)
        price = "1000"
        #answer = json.loads(response.text)
        #price = str(answer["securities"]["data"][243][0]) + " " + str(answer["securities"]["data"][243][22])
        await message.answer(price)
        time.sleep(10)

if __name__ == "__main__":
    executor.start_polling(dp)