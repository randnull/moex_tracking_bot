import asyncio

import toml
from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram import executor
from aiogram.dispatcher.filters.state import State, StatesGroup

import sqlalchemy as db
import sqlite3
from sqlalchemy import *
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

import requests
import json

import datetime
import math
import numpy

with open("bot_config.toml",  "r",) as config_file:
    config_toml = toml.load(config_file)
    try:
        token: str = config_toml["bot"]["token"]
    except Exception:
        raise AttributeError('Config file does not have token properly defined.')

bot = Bot(token=token)
url_moex = 'https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities.json?first=350'
dp = Dispatcher(bot, storage=MemoryStorage())

engine = db.create_engine('sqlite+pysqlite:///database.db', echo=True)
Base = declarative_base()

Session = sessionmaker(bind=engine, future=True, expire_on_commit=False)
session = Session()

not_stop = True


class Persons(Base):
    __tablename__ = 'persons'

    UserID = Column(Integer, name='UserID', primary_key=True)
    Companies = Column(String, name='Companies')


class Companies(Base):
    __tablename__ = 'companies'

    Name = Column(String, name='Name', primary_key=True)
    Price = Column(Integer, name='Price')
    Index = Column(Integer, name='Index')
    Volume = Column(Integer, name='Volume')

    def __repr__(self):
        return f"{self.Name}"


def put_companies_to_table():
    companies_list = [("YNDX", 0),
                      ("ABRA", 0),
                      ("CHKZ", 0),
                      ("HIMCP", 0),
                      ("MTLR", 0),
                      ("ALRS", 0),
                      ("GAZP", 0),
                      ("LKOH", 0),
                      ("MGNT", 0),
                      ("NLMK", 0),
                      ("NVTK", 0),
                      ("ROSN", 0),
                      ("SBER", 0),
                      ]
    items_dicts = []
    for item in companies_list:
        d = {'name': item[0], 'price': 0, 'index': item[1], 'volume': 0}
        items_dicts.append(d)
    db = sqlite3.connect('database.db')
    sql = db.cursor()
    for item in items_dicts:
        name = item['name']
        price = item['price']
        index = item['index']
        volume = item['volume']
        sql.execute('INSERT OR REPLACE INTO companies ("Name", "Price", "Index", "Volume") VALUES (?, ?, ?, ?)', (name, price, index, volume))
    db.commit()


Base.metadata.create_all(engine)
put_companies_to_table()


class Actions(StatesGroup):
    ChooseCompany = State()


@dp.message_handler(commands=['start'], state="*")
async def start(message):
    user_id = message.from_user.id
    results = session.query(Persons).filter_by(UserID=user_id).all()
    await message.answer("Добро пожаловать! Для просмотра команд введите /help")
    if len(results) > 0:
        return
    new_track = Persons(UserID=message.from_user.id)
    session.add(new_track)
    session.commit()


@dp.message_handler(commands=['help'], state="*")
async def help(message):
    add_actions = KeyboardButton("Изменить акции для отслеживания")
    go = KeyboardButton("Перейти к отслеживанию")
    buttons = ReplyKeyboardMarkup(resize_keyboard=True)
    buttons.add(add_actions)
    buttons.add(go)
    await message.answer("Что вы хотите сделать?", reply_markup=buttons)


@dp.message_handler(lambda message: message.text == "Изменить акции для отслеживания", state="*")
async def choose_action(message):
    global not_stop
    not_stop = False
    await message.answer("Вы остановили отслеживание. Для получения списка команд нажмите /help")
    await Actions.ChooseCompany.set()
    user_id = message.from_user.id
    companies = session.query(Companies).all()
    person_actions = session.query(Persons).filter_by(UserID=user_id).first().Companies
    await message.answer("Акции, которые вы отслеживаете:")
    if person_actions is None or person_actions == '':
        person_actions = 'Вы пока не отслеживаете ни одной акции'
        await message.answer(person_actions)
    else:
        await message.answer('\n'.join(person_actions.split()))
    await message.answer('Доступные для отслеживания акции:')
    all_actions = ''
    for r in companies:
        all_actions += str(r)
        all_actions += '\n'
    await message.answer(all_actions)
    await message.answer("Вы можете:\n"
                         "Ввести акцию из списка ваших акций, если хотите удалить ее из вашего списка отслеживания.\n"
                         "Ввести акцию из списка доступных акций, если хотите добавить ее в ваш список отслеживания.")


@dp.message_handler(state=Actions.ChooseCompany)
async def choose_company(message, state):
    user_id = message.from_user.id
    mes = str(message.text)
    if mes == "Выйти":
        await message.answer("Вы вышли. Для просмотра команд нажмите /help")
        await state.finish()
        return
    create = KeyboardButton("Выйти")
    buttons = ReplyKeyboardMarkup(resize_keyboard=True)
    buttons.add(create)
    check_name = session.query(Companies).filter_by(Name=mes).all()
    if len(check_name) == 0:
        await message.answer("Акций с таким названием не существует. Введите другое название или нажмите Выйти.", reply_markup=buttons)
    else:
        companies = session.query(Persons).filter_by(UserID=user_id).first().Companies
        if companies is None:
            companies = []
        else:
            companies = companies.split()
        if mes in set(companies):
            i = companies.index(mes)
            new_companies = companies[:i] + companies[i + 1:]
            companies_str = ' '.join(new_companies)
            db = sqlite3.connect('database.db')
            sql = db.cursor()
            sql.execute('INSERT OR REPLACE INTO persons ("UserID", "Companies") VALUES (?, ?)', (user_id, companies_str))
            db.commit()
            session.commit()
            await message.answer("Акция успешно удалена. Введите название другой акции, которую хотите добавить/удалить, или нажмите Выйти.",
                                 reply_markup=buttons)
        else:
            companies.append(mes)
            companies_str = ' '.join(companies)
            db = sqlite3.connect('database.db')
            sql = db.cursor()
            sql.execute('INSERT OR REPLACE INTO persons ("UserID", "Companies") VALUES (?, ?)', (user_id, companies_str))
            db.commit()
            session.commit()
            await message.answer("Акция успешно добавлена. Введите название другой акции, которую хотите добавить/удалить, или нажмите Выйти.",
                                 reply_markup=buttons)
        person_actions = session.query(Persons).filter_by(UserID=user_id).first().Companies.split()
        await message.answer("Акции, которые вы отслеживаете:")
        await message.answer('\n'.join(person_actions))


def get_price(response, name):
    answer = json.loads(response.text)
    last_price = answer['marketdata']['data'][0][2]
    return last_price


def get_volume(response):
    answer = json.loads(response.text)
    last_volume = answer['marketdata']['data'][0][28]
    return last_volume


def check(response, name):
    new_price = get_price(response, name)
    company = session.query(Companies).filter_by(Name=name).first()
    price = company.Price
    index = company.Index
    volume = company.Volume
    if new_price is None:
        ret_val = 0
    else:
        ret_val = (price - new_price)
    if abs(ret_val) > 0:
        db = sqlite3.connect('database.db')
        sql = db.cursor()
        sql.execute('INSERT OR REPLACE INTO companies ("Name", "Price", "Index", "Volume") VALUES (?, ?, ?, ?)', (name, new_price, index, volume))
        db.commit()
        session.commit()
    return price, new_price


@dp.message_handler(lambda message: message.text == "Остановить отслеживание", state="*")
async def stop(message, state):
    global not_stop
    not_stop = False
    await message.answer("Вы остановили отслеживание. Для получения списка команд нажмите /help")


@dp.message_handler(lambda message: message.text == "Перейти к отслеживанию", state="*")
async def process(message):
    global not_stop
    user_id = message.from_user.id
    person_actions = session.query(Persons).filter_by(UserID=user_id).first().Companies
    if person_actions is None or person_actions == '':
        text = 'Вы пока не отслеживаете ни одной акции. Для перехода к списку команд введите /help'
        await message.answer(text)
        return
    await message.answer("Мы отслеживаем следующие акции:")
    person_actions = person_actions.split()
    not_stop = True
    create = KeyboardButton("Остановить отслеживание")
    buttons = ReplyKeyboardMarkup(resize_keyboard=True)
    buttons.add(create)
    await message.answer('\n'.join(person_actions), reply_markup=buttons)
    while not_stop:
        #try:
        for action in person_actions:
            response = requests.get(
                f"https://iss.moex.com/iss/engines/stock/markets/shares/boards/tqbr/securities/{action}.json")
            price, new_price = check(response, action)
            volume = get_volume(response)
            if price == 0:
                difference = 0
            else:
                difference = abs((1 - (new_price/(price)))) * numpy.sign(-price + new_price)
            mes = ""
            if difference > 0:
                mes = f"🟢#{action}\n"
            elif difference < 0:
                mes = f"🔴#{action}\n"
            if len(mes) > 0:
                now = datetime.datetime.now()
                formatted_date = now.strftime("%H:%M %d.%m.%Y")
                answer = f"{mes}{action}: {price} -> {new_price} ({(difference * 100):.2f}%)\nОбъем: {volume} руб.\n{formatted_date}"
                await message.reply(answer)
        # except:
        #     print("error")
        await asyncio.sleep(5)


if __name__ == "__main__":
    executor.start_polling(dp)
