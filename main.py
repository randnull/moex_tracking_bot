import asyncio

import numpy
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

import emoji

from tradingview_ta import TA_Handler, Interval, Exchange

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

dict_rus_names = dict()

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
    Deepth = Column(Integer, name='Deepth')
    PrevPrices = Column(String, name='PrevPrices')

    def __repr__(self):
        return f"{self.Name}"

def get_all_companies():
    global dict_rus_names

    companies_list = []
    response = requests.get(url_moex)
    data = json.loads(response.text)
    for i in data['securities']['data']:
        companies_list.append((i[0], 0))
        dict_rus_names[i[0]] = i[2]
    return companies_list

def put_companies_to_table():
    companies_list = get_all_companies()
    items_dicts = []
    for item in companies_list:
        d = {'name': item[0], 'price': 0, 'index': item[1], 'volume': 0, 'deepth': 0, 'prevPrices': ''}
        items_dicts.append(d)
    db = sqlite3.connect('database.db')
    sql = db.cursor()
    for item in items_dicts:
        name = item['name']
        price = item['price']
        index = item['index']
        volume = item['volume']
        deepth = item['deepth']
        prevPrices = item['prevPrices']
        sql.execute('INSERT OR REPLACE INTO companies ("Name", "Price", "Index", "Volume", "Deepth", "PrevPrices") VALUES (?, ?, ?, ?, ?, ?)', (name, price,
                                                                                                                            index, volume, deepth, prevPrices))
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
    global not_stop, dict_rus_names
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
        try:
            all_actions += str(r) + str("  ") + str(dict_rus_names[str(r)])
        except:
            all_actions += str(r)
        all_actions += '\n'
    await message.answer(all_actions)
    await message.answer("Вы можете:\n"
                         "Ввести акцию из списка ваших акций, если хотите удалить ее из вашего списка отслеживания.\n"
                         "Ввести акцию/акции через пробел из списка доступных акций, если хотите добавить ее в ваш список отслеживания.\n"
                         "Вводу подлежит только тикер акции, например: YNDX.")


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
    mes_list = mes.split()
    for mes in mes_list:
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

def get_opinion(action):
    ans = TA_Handler(
        symbol=action,
        screener="russia",
        exchange="MOEX",
        interval=Interval.INTERVAL_15_MINUTES
    )
    return ans.get_analysis().summary['RECOMMENDATION']

def get_analisys(action):
    ans = TA_Handler(
        symbol=action,
        screener="russia",
        exchange="MOEX",
        interval=Interval.INTERVAL_15_MINUTES
    )
    return ans.get_analysis().indicators['RSI'], ans.get_analysis().indicators['CCI20']

def get_price(response, name):
    answer = json.loads(response.text)
    last_price = answer['marketdata']['data'][0][2]
    return last_price

def check_alg(score):
    recommendetion = ""
    if score > 0:
        if score < 10:
            recommendetion = "BUY"
        elif score < 23:
            recommendetion = "STRONG BUY"
        else:
            recommendetion = "SUPER STRONG BUY"
    else:
        if score > -10:
            recommendetion = "SELL"
        elif score > -23:
            recommendetion = "STRONG SELL"
        else:
            recommendetion = "SUPER STRONG SELL"
    return recommendetion

def alg_sell_buy(action, difference_price, deptht_sell, deptht_buy, rsi):
    score = 0
    if difference_price > 0:
        score += min(int(difference_price * 10), 10)
    else:
        score -= min(int(abs(difference_price) * 10), 10)
    if rsi < 50:
        score += int((100 - rsi) / 10)
    else:
        score -= int(rsi / 10)
    if deptht_buy > deptht_sell:
        score += int(deptht_buy / 10)
    else:
        score -= int(deptht_sell / 10)
    return check_alg(int(score))

def own_recommendetion(action, difference_price, difference_volume, deptht_sell, deptht_buy, rsi, cci):
    recommendation = ""
    if difference_price > 0.5 and deptht_buy > 70 and rsi < 50:
        if difference_volume > 0.5 and cci < -100:
            recommendation = "SUPER STRONG BUY"
        elif difference_volume > 0.3:
            recommendation = "STRONG BUY"
        elif difference_volume > 0.1:
            recommendation = "BUY"
    if difference_price > 0.3 and difference_price < 0.5 and deptht_buy > 60 and rsi < 40:
        recommendation = "BUY"
    if difference_price < -0.3 and difference_price > -0.5 and deptht_sell > 60 and rsi > 50:
        recommendation = "SELL"
    if difference_price < -0.5 and deptht_sell > 70 and rsi > 60:
        if difference_volume > 0.5 and cci > 100:
            recommendation = "SUPER STRONG SELL"
        elif difference_volume > 0.3:
            recommendation = "STRONG SELL"
        elif difference_volume > 0.1:
            recommendation = "SELL"
    return recommendation

def get_volume(response):
    answer = json.loads(response.text)
    last_volume = answer['marketdata']['data'][0][28]
    return last_volume

def get_glass(response):
    answer = json.loads(response.text)
    st_b = answer['marketdata']['data'][0][7]
    st_s = answer['marketdata']['data'][0][8]
    all_st = answer['marketdata']['data'][0][5]
    return st_b, st_s, all_st

def day_change(response):
    answer = json.loads(response.text)
    last_close_price = answer['marketdata']['data'][0][21]
    return last_close_price

def get_SPREAD(response):
    answer = json.loads(response.text)
    spread = answer['marketdata']['data'][0][6]
    return spread

def check(response, name):
    new_price = get_price(response, name)
    new_volume = get_volume(response)
    company = session.query(Companies).filter_by(Name=name).first()
    price = company.Price
    index = company.Index
    volume = company.Volume
    deepth = company.Deepth
    prevPrices = company.PrevPrices
    difference = 0
    if new_price is None:
        ret_val = 0
        difference = 0
    else:
        if price == 0:
            difference = 0
        else:
            difference = abs((1 - (new_price / (price))))
        ret_val = (price - new_price)
    if abs(ret_val) > 0:
        prevPricesList = prevPrices.split()
        prevPrices = " ".join(prevPricesList)
        db = sqlite3.connect('database.db')
        sql = db.cursor()
        sql.execute('INSERT OR REPLACE INTO companies ("Name", "Price", "Index", "Volume", "Deepth", "PrevPrices") VALUES (?, ?, ?, ?, ?, ?)', (name,
                                                                                                             new_price, index, volume, deepth, prevPrices))
        db.commit()
        session.commit()
    difference_volume = 0
    if new_volume is None:
        ret_vol = 0
        difference_volume = 0
    else:
        ret_vol = volume - new_volume
        if volume == 0:
            difference_volume = 0
        else:
            difference_volume = abs((1 - (new_volume / (volume))))
    if abs(ret_vol) > 0:
        db = sqlite3.connect('database.db')
        sql = db.cursor()
        sql.execute('INSERT OR REPLACE INTO companies ("Name", "Price", "Index", "Volume", "Deepth", "PrevPrices") VALUES (?, ?, ?, ?, ?, ?)',
                    (name, new_price, index, new_volume, deepth, prevPrices))
        db.commit()
        session.commit()
    return price, new_price, volume, new_volume

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
        try:
            for action in person_actions:
                response = requests.get(
                    f"https://iss.moex.com/iss/engines/stock/markets/shares/boards/tqbr/securities/{action}.json")
                price, new_price, volume, new_volume = check(response, action)
                day_change_ = day_change(response)
                st_b, st_s, all_st = get_glass(response)
                if price == 0:
                    difference = 0
                else:
                    difference = abs((1 - (new_price/(price)))) * numpy.sign(-price + new_price)
                mes = ""
                if difference > 0:
                    if abs(difference * 100) > 0.3:
                        mes = f"{emoji.emojize(':green_circle:')}{emoji.emojize(':green_circle:')}#{action}\nЗамечено изменение цены!\n"
                    elif abs(difference * 100) > 0.1:
                        mes = f"{emoji.emojize(':green_circle:')}#{action}\nЗамечено изменение цены!\n"
                    else:
                        mes = ""
                elif difference < 0:
                    if abs(difference * 100) > 0.3:
                        mes = f"{emoji.emojize(':red_circle:')}{emoji.emojize(':red_circle:')}#{action}\nЗамечено изменение цены!\n"
                    elif abs(difference * 100) > 0.1:
                        mes = f"{emoji.emojize(':red_circle:')}#{action}\nЗамечено изменение цены!\n"
                    else:
                        mes = ""
                if volume == 0:
                    difference_volume = 0
                else:
                    difference_volume = abs((1 - (new_volume/(volume)))) * numpy.sign(-volume + new_volume)
                try:
                    st_b_pr = st_b / (st_b + st_s) * 100
                    st_s_pr = st_s / (st_b + st_s) * 100
                except:
                    st_s_pr = 0
                    st_b_pr = 0
                if (st_b_pr > 85):
                    mes += f"{emoji.emojize(':green_circle:')}#{action}\nСтакан несбалансирован!\nОжидается резкое изменение цены\n"
                if (st_s_pr > 85):
                    mes += f"{emoji.emojize(':red_circle:')}#{action}\nСтакан несбалансирован!\nОжидается резкое изменение цены\n"
                if abs(difference_volume * 100) > 0.5:
                    mes += "Замечено изменение объема!\n"
                    mes += f"#{action} Изменения объема: {volume} -> {new_volume} ({(difference_volume * 100):.2f}%)\n"
                if len(mes) > 0:
                    r, s = get_analisys(action)
                    mes += f"\n\nТех. индикаторы: RSI: {r}, CCI: {s}\n\n"
                if len(mes) > 0:
                    now = datetime.datetime.now()
                    formatted_date = now.strftime("%H:%M %d.%m.%Y")
                    answer = f"{mes}{action}: {price} -> {new_price} ({(difference * 100):.2f}%)\nАктуальный стакан:\nПокупка: {st_b_pr:.2f}% Продажа: {st_s_pr:.2f}%\nОбъем: {new_volume} руб.\n{formatted_date}"
                    answer += f"\nПоказатели индикаторов: {get_opinion(action)}\n"
                    r, s = get_analisys(action)
                    f_answer = own_recommendetion(action, difference, difference_volume, st_s_pr, st_b_pr, r, s)
                    s_answer = alg_sell_buy(action, difference, st_s_pr, st_b_pr, r)
                    if f_answer != "":
                        answer += f"По анализу(1): {f_answer}\n"
                    if s_answer != "":
                        answer += f"По анализу(2): {s_answer}"
                    await message.reply(answer)
        except Exception as ex:
            print(ex)
            print("error")
        await asyncio.sleep(10)


if __name__ == "__main__":
    executor.start_polling(dp)
