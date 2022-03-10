import time
import datetime
import bot_database
import json
from telebot import types
from typing import Dict, List, Tuple
from main import bot, my_rapi, logger
from bot_classes import BotKeyboard, ApiQuest
from telebot_calendar import Calendar, RUSSIAN_LANGUAGE, CallbackData
hotel_messages: Dict = {'low': ['Ищем отели с демократическими ценами.', 'PRICE'],
                  'high': ['Ищем отели с максимальной стоимостью.', 'PRICE_HIGHEST_FIRST'],
                  'best': ['Ищем отели по соотношению цены и расстояния до центра города', 'DISTANCE_FROM_LANDMARK'],
                  'error': ['Ошибка ввода. Лучше начните сначала. Будут выведены отели с низкими ценами.', 'PRICE']}
calendar = Calendar(language=RUSSIAN_LANGUAGE)
calendar_1_callback = CallbackData("calendar_1", "action", "year", "month", "day")


def service_message(bot, message: types.Message, sm_num: int) -> None:
    """
    Функция выводит пользователю сервисные сообщения про командам /help и /start
    :param bot: чатбот
    :param message: Полученное в чате сообщение
    :param sm_num: ключ в словаре service_message
    """
    service_messages: Dict = {0: 'Давайте подберем вам подходящий отель. Для этого используйте следующие команды:\n'
                                 '\'/lowprice\' - самые дешевые отели в городе\n'
                                 '\'/highprice\' - самые дорогие отели в городе\n'
                                 '\'/bestdeal\' - лучшее предложение по цене и расстоянию до центра\n'
                                 '\'/history\' - Просмотр результатов последнего запроса',
                              1: 'Этот бот предназначен для поиска отелей в различных городах.\n'
                                 'Для помощи по командам наберите /help'}

    bot.send_message(message.from_user.id, service_messages[sm_num])


def brake_chain(message: types.Message) -> bool:
    """
    Функция прерывания цепочки опроса пользователя по вводу пользователем зарегистрированной команды
    :param message: Полученное в чате сообщение
    :return: True возвращается, если текст сообщения начинается с /, иначе False
    """
    if message.text.startswith('/'):
        return True


def command_router(bot, message: types.Message) -> None:
    """
    Запуск цепочки опроса пользователя, создание записи сессии в базе данных
    :param bot: чат-бот
    :param message: Полученное в чате сообщение
    """
    tm_stamp = time.time()
    chat_id = message.chat.id
    logger.info(f'Начало цепочки: {message.text}, chat.id: {message.chat.id}')
    if message.text == '/help':
        service_message(bot, message, 0)
        state = 'help'
    elif message.text == '/start':
        service_message(bot, message, 1)
        state = 'start'
    elif message.text == '/lowprice':
        state = 'low'
        get_locale(message, bot)
    elif message.text == '/highprice':
        state = 'high'
        get_locale(message, bot)
    elif message.text == '/bestdeal':
        state = 'best'
        get_locale(message, bot)
    elif message.text == '/history':
        state = 'hist'
        show_history(message)
    else:
        bot.send_message(message.chat.id, 'К сожалению, эта команда мне непонятна.\nПопробуйте еще раз.\n'
                                          'Для помощи, введите /help')
        state = 'error'
    if message.text in ('/lowprice', '/highprice', '/bestdeal'):
        bot_database.create_record(chat_id, state, tm_stamp)


def show_calendar(bot,
                  message: types.Message,
                  month: int = 0,
                  quest: str = 'Выберите дату заезда в отель',
                  name: str = calendar_1_callback.prefix) -> None:
    """
    Создание inline-клавиатуры календаря
    :param bot: чат-бот
    :param message: Полученное в чате сообщение
    :param month: номер месяца
    :param quest: передаваемый пользователю вопрос
    :param name: имя передаваемого пользователю календаря
    """
    now = datetime.datetime.now()
    if month == 0:
        month = now.month
    if name == 'calendar_2':
        quest = 'Выберите дату выезда'
    bot.send_message(
        message.chat.id,
        quest,
        reply_markup=calendar.create_calendar(
            name=name,
            year=now.year,
            month=month,
        ),
    )


def get_locale(message: types.Message, bot) -> None:
    """
    Создает inline-клавиатуру для запроса языка у пользователя
    :param message: Полученное в чате сообщение
    :param bot: чат-бот
    """
    this_keyboard = BotKeyboard([('Русский', 'ru_RU.loc'), ('English', 'en_US.loc')], 2)
    keyboard = this_keyboard.create_keys()
    question = 'На каком языке будем искать?'
    bot.send_message(message.from_user.id, text=question, reply_markup=keyboard)


def get_lang(one_locale: str, in_message: types.CallbackQuery, bot) -> None:
    """
    Принимает выбранное значение из inline-клавиатуры, созданной в get_locale
    Производит запись полученного значения в базу данных
    :param one_locale: выбранный пользователем язык
    :param in_message: вызов из inline-клавиатуры
    :param bot: чат-бот
    """
    bot_database.update_record('lang', one_locale, in_message.message.chat.id)
    msg = bot.send_message(in_message.from_user.id, 'В каком городе ищем отели? ')
    bot.register_next_step_handler(msg, get_city, bot)


def get_city(message: types.Message, bot) -> None:
    """
    Вызывает find_city для получения списка городов. Если получен список более чем из одного элемена,
    выводит inline-клавиатуру для вывода вариантов пользователю. Если возвращен список из одного элеменат,
    вызывает get_start, передает в нее id выбранного города.
    Если возвращен пустой список, выводит сообщение об ошибке, возвращает пользователя к выбору города.
    :param message: Полученное в чате сообщение
    :param bot: чат-бот
    """
    if brake_chain(message):
        command_router(bot, message)
    else:
        city: str = message.text
        bot_database.update_record('city', city, message.chat.id)
        cities: List = find_city(city, message)
        if len(cities) == 0:
            msg = bot.send_message(message.chat.id, 'Ничего не найдено\nПопробуйте ввести название более точно:')
            bot.register_next_step_handler(msg, get_city, bot)
        elif len(cities) > 1:
            places: List[Tuple] = [(city + ',' + ''.join(one_city[0].split(sep=',')[1:]), one_city[1] + '.city')
                      for one_city in cities]
            this_keyboard = BotKeyboard(places, 1)
            keyboard: types.InlineKeyboardMarkup = this_keyboard.create_keys()
            question: str = 'Найдено несколько городов. Выберите подходящий:'
            bot.send_message(message.from_user.id, text=question, reply_markup=keyboard)
        else:
            get_start(cities[0][1], message, bot)


def find_city(city: str, message: types.Message) -> List[Tuple]:
    """
    Создает объект класса ApiQuest, вызывает его метод get_city для получения списка id городов по названию,
    введенному пользователем. Возвращает этот список в get_city
    :param city: Название города, введенное пользователем.
    :param message: Полученное в чате сообщение
    :return: Список кортежей, содержащих название с географической привязкой и id городов,
    название которых совпадает с введенным пользователем
    """
    lang: str = bot_database.select_some(message.chat.id, 'Session',  'lang')[0]
    searched_cities = ApiQuest(my_rapi, city, lang)
    cities: List = searched_cities.get_city()
    return cities


def get_start(location: str, message, bot) -> None:
    """
    Производит запись полученного из get_city значения в базу данных
    Отсылает пользователю сообщение с вопросом о количестве отелей для поиска.
    Назначает обработчиком следующего шага hotel_numbers
    :param location: id выбранного города
    :param message: Полученное в чате сообщение
    :param bot: чат-бот
    """
    bot_database.update_record('location', location, message.chat.id)
    state = bot_database.select_some(message.chat.id, 'Session',  'state')[0]
    bot.send_message(message.chat.id, hotel_messages[state][0])
    bot.send_message(message.chat.id, 'Введите количество отелей для поиска.\n'
                                      'Замечу, что я могу найти не более 25 отелей.')
    bot.register_next_step_handler(message, hotel_numbers, bot, location)


def hotel_numbers(message, bot, location: str) -> None:
    """
    Производит запись полученного от пользователя значения в базу данных
    В зависимости от выбранного сценария либо опрашиваетпользователя о количестве проживающих,
    либо запрашиваетмаксимальное расстояние до центра города. назначает следующий обработчки сообщения
    :param message: Полученное в чате сообщение
    :param bot: чат-бот
    :param location: id выбранного города
    """
    if brake_chain(message):
        command_router(bot, message)
    else:
        hot_num = message.text
        if not hot_num.isdigit():
            bot.send_message(message.from_user.id, 'Неправильный ввод, попробуйте еще раз')
            bot.register_next_step_handler(message, hotel_numbers, bot, location)
        elif 0 >= int(hot_num) or int(hot_num) > 25:
            bot.send_message(message.from_user.id, 'Похоже, вы ввели неправильное количество отелей. Попробуйте снова.')
            bot.register_next_step_handler(message, hotel_numbers, bot, location)
        else:
            bot_database.update_record('hot_num', hot_num, message.chat.id)
            state = bot_database.select_some(message.chat.id, 'Session', 'state')[0]
            logger.info(f'После выбора отелей проверка критерия поиска: {state}')
            if state == 'best':
                logger.info('Переход на запрос расстояния')
                msg = bot.send_message(message.from_user.id, 'Какое должно быть максимальное расстояние '
                                                             'от отеля до центра города?')
                bot.register_next_step_handler(msg, get_landmarks, bot)
            else:
                msg = bot.send_message(message.from_user.id, 'Сколько человек планирует проживать в отеле?')
                bot.register_next_step_handler(msg, get_person, bot)


@logger.catch()
def get_landmarks(message: types.Message, bot):
    """
    Участвует только в цепочке /bestdeal
    Сохраняет значение расстояния до центра города в базу. Задает вопрос пользователю о максимальной стоимости
    проживания. назначает следующий обработчик
    :param message: Полученное в чате сообщение
    :param bot: чат-бот
    """
    if brake_chain(message):
        command_router(bot, message)
    else:
        distance = message.text
        if not distance.isdigit():
            msg = bot.send_message(message.from_user.id, 'Неправильный ввод. '
                                                         'Какое должно быть максимальное расстояние '
                                                         'от отеля до центра города?')
            bot.register_next_step_handler(msg, get_landmarks, bot)
        else:
            bot_database.update_record('distance', distance, message.chat.id)
            msg = bot.send_message(message.from_user.id, 'Какова должна быть максимальная стоимость суток проживания?')
            bot.register_next_step_handler(msg, get_max_price, bot)


def get_max_price(message: types.Message, bot) -> None:
    """
    Участвует только в цепочке /bestdeal
    Сохраняет значение цены проживания в базу. Задает вопрос пользователю о количестве проживающих.
    Назначает следующий обработчик
    :param message: Полученное в чате сообщение
    :param bot:чат-бот
    """
    if brake_chain(message):
        command_router(bot, message)
    else:
        max_price = message.text
        if not max_price.isdigit():
            msg = bot.send_message(message.from_user.id, 'Неправильный ввод. '
                                                         'Какова должна быть максимальная стоимость суток проживания?')
            bot.register_next_step_handler(msg, get_max_price, bot)
        else:
            bot_database.update_record('stop_price', max_price, message.chat.id)
            msg = bot.send_message(message.from_user.id, 'Сколько человек планирует проживать в отеле?')
            bot.register_next_step_handler(msg, get_person, bot)


def get_person(message: types.Message, bot) -> None:
    """
    Сохраняет количество проживающих в базу. Вызывет создание inline-клавиатуры-календаря для получения дат
    заезда и выезда из отеля
    :param message: Полученное в чате сообщение
    :param bot: чат-бот
    """
    if brake_chain(message):
        command_router(bot, message)
    else:
        persons = message.text
        bot_database.update_record('persons', persons, message.chat.id)
        show_calendar(bot, message, quest='Выберите дату заезда')


def get_check_in(message: types.Message, bot, location: str, hot_num: str, persons: str) -> None:
    """
    Функция в данный момент не используется. Сохранена для будущей работы.
    :param message: Полученное в чате сообщение
    :param bot: чат-бот
    :param location: id выбранного города
    :param hot_num: количество отелей
    :param persons: количество проживающих
    :return:
    """
    if brake_chain(message):
        command_router(bot, message)
    else:
        check_in = message.text
        bot_database.update_record('check_in', check_in, message.chat.id)
        msg = bot.send_message(message.chat.id, 'Когда планируется выезд из в отеля?')
        bot.register_next_step_handler(msg, get_check_out, bot, location, hot_num, persons, check_in)


# def get_currency(message, bot, location, hot_num, persons, check_in):
#     check_out = message.text
#     msg = bot.send_message(message.chat.id, 'Какую валюту будем использовать?')
#     bot.register_next_step_handler(msg, find_hotels, bot, location, hot_num, persons, check_in, check_out)


def get_check_out(message: types.Message, bot, currency: str='RUB') -> None:
    """
    Получает список отелей по заданным критериям. Вызыввет show_hotels для вывода списка пользователю.
    :param message: types.Message
    :param bot: чяат-бот
    :param currency: используемая валюта. Пока использвется только RUB
    """
    if brake_chain(message):
        command_router(bot, message)
    else:
        bot.send_message(message.chat.id, 'Веду поиск, пожалуйста, подождите...⏱')
        persons, location, hot_num, check_out, check_in, sorting_m, lang, max_price, distance, tm_stamp = \
            bot_database.select_some(message.chat.id, 'Session', 'persons', 'location', 'hot_num',
                                     'check_out', 'check_in', 'state', 'lang', 'stop_price', 'distance', 't_stamp')
        sorting_method = hotel_messages[sorting_m][1]
        page_number = "1"
        if sorting_m != 'best':
            searched_hotels = ApiQuest(my_rapi, persons, page_number, location, hot_num, check_out, check_in,
                                       sorting_method, lang, currency)
        else:
            searched_hotels = ApiQuest(my_rapi, persons, page_number, location, hot_num, check_out, check_in,
                                       sorting_method, lang, currency, max_price, distance)
        hotels_list = searched_hotels.get_hotels()
        if hotels_list:
            hotels_history = json.dumps(hotels_list, ensure_ascii=False)
            logger.info('Получен список отелей:')
            logger.info(hotels_history)
            bot_database.create_history(message.chat.id, hotels_history, tm_stamp)
            show_hotels(message.chat.id, hotels_list)
        else:
            logger.warning('Список отелей не получен', message.chat.id)
            bot.send_message(message.chat.id, 'К сожалению, ни одного отеля не найдено')


def chosen_hotel(hotel_id: str, call: types.CallbackQuery, bot, currency: str='RUB') -> None:
    """
    Выводит пользователю информацию по выбранному отелю. Предлагает на выбор вывод изображений отеля,
    либо просмотр рещультатов последнего запроса.
    :param hotel_id: id выбранного пользователем отеля
    :param call: вызов из inline -клавиатуры
    :param bot: чат-бот
    :param currency: используемая валюта
    """
    persons, check_out, check_in, lang = bot_database.select_some(
        call.message.chat.id, 'Session', 'persons', 'check_out', 'check_in', 'lang')
    logger.info(f'переменные для конкретного отеля: {call.message.chat.id}, {persons}, {check_out}, {check_in}, {lang}')
    one_hotel = ApiQuest(my_rapi, hotel_id, check_in, check_out, persons, currency, lang)
    hotel_info = one_hotel.get_one_hotel()
    hotels = bot_database.select_some(call.message.chat.id, 'History', 'hotels')[0]
    hotels_list = json.loads(hotels)
    for one_hotel in hotels_list:
        if one_hotel[1].split(sep='.')[0] == hotel_id:
            distance = one_hotel[0].split(sep='\n')[-2]
            if lang == 'en_US':
                distance = round(float(distance) * 1.609, 2)
            hotel_info += f'\nРасстояние до центра города: {distance} км.'
    bot.send_message(call.message.chat.id, hotel_info)
    bot.send_message(call.message.chat.id, f'https://ru.hotels.com/ho{hotel_id}')
    next_step: List = [('Изображения отеля', hotel_id + '.h_pic'),
                       ('Показать последний запрос', str(call.message.chat.id) + '.his')]
    this_keyboard = BotKeyboard(next_step, 1)
    keyboard = this_keyboard.create_keys()
    bot.send_message(call.message.chat.id, text='Выберите действие: ', reply_markup=keyboard)


def set_date(call: types.CallbackQuery) -> None:
    """
    Получает даты заезда и выезда, записывает их в базу данных
    :param call: вызов из inline-клавиатуры
    """
    name, action, year, month, day = call.data.split(':')
    if len(day) == 1:
        day = '0' + day
    if len(month) == 1:
        month = '0' + month
    now = datetime.datetime.now()
    proper = False
    stage = 'none'
    this_date = f'{now.year}-{now.month}-{now.day}'
    if name == 'calendar_1':
        stage = 'check_in'
        if datetime.date(int(year), int(month), int(day)) >= datetime.date.today():
            this_date = f'{year}-{month}-{day}'
            proper = True
            logger.info('определена дата заезда')
    else:
        chk_in = bot_database.select_some(call.message.chat.id, 'Session', 'check_in')[0]
        logger.info(chk_in)
        if chk_in:
            c_year, c_month, c_day = map(int, chk_in.split(sep='-'))
            if datetime.date(int(c_year), int(c_month), int(c_day)) < datetime.date(int(year), int(month), int(day)):
                this_date = f'{year}-{month}-{day}'
                stage = 'check_out'
                proper = True
                logger.info('определена дата выезда')
    if proper:
        bot_database.update_record(stage, this_date, call.message.chat.id)
        if stage == 'check_in':
            show_calendar(bot, call.message, quest='Выберите дату выезда', name='calendar_2')
            logger.info('Определяем дату выезда')
        else:
            get_check_out(call.message, bot)
    else:
        if name == 'calendar_1':
            action_now = 'въезда'
            bot.send_message(call.message.chat.id, 'Дата въезда указана ранее текущей даты.')
        else:
            action_now = 'выезда'
            bot.send_message(call.message.chat.id, 'Дата выезда указана ранее даты въезда.')
        bot.send_message(call.message.chat.id, 'Неправильный ввод, пожалуйста, повторите')
        show_calendar(bot, call.message, quest=f'Выберите дату {action_now}', name=name)


def show_hotels(chat_id: int, hotels: List, question: str = 'Отели найдены. Выберите подходящий:') -> None:
    """
    Выводит inline-клавиатуру со списком отелей, попавших в критерии, указанные пользователем.
    Выделена в отдельную функцию для удобства показа результата последнего запроса.
    :param chat_id: id чата, в котором происходит взаимодействие с пользователем
    :param hotels: Список, содержащий списки/кортежи, содержащие id и описание отелей, подходящих критериям пользователя
    :param question: вопрос, задаваемый пользователю
    """
    logger.info('Вход в функцию show_hotels')
    logger.info(hotels)
    this_keyboard = BotKeyboard(hotels, 1)
    keyboard = this_keyboard.create_keys()
    bot.send_message(chat_id, text=question, reply_markup=keyboard)


def get_picts(hot_id: str, message: types.Message, bot, p_type: str) -> None:
    """
    Запрашивает у пользователя количество выводимых изображений отеля.
    :param hot_id: id выбранного отеля
    :param message: Полученное в чате сообщение
    :param bot: чат-бот
    :param p_type: тип изображении: экстеррьер/комнаты. Пока не используется в полной мере.
    """
    msg = bot.send_message(message.chat.id, 'Сколько изображений вывести?\n'
                                           'Замечу, что я могу вывести не более 10 изображений.')
    bot.register_next_step_handler(msg, show_picts, hot_id, bot, p_type)


def show_picts(message: types.Message, hot_id: str, bot, p_type: str) -> None:
    """
    Получает и выводит изображения отеля
    :param message: Полученное в чате сообщение
    :param hot_id: id отеля
    :param bot: чат-бот
    :param p_type: тип изображении: экстеррьер/комнаты. Пока не используется в полной мере.
    """
    picts_quont = message.text
    if not picts_quont.isdigit() or int(picts_quont) < 1 or int(picts_quont) > 10:
        msg = bot.send_message(message.chat.id, 'Неправильный ввод. \nСколько изображений вывести?\n'
                                           'Замечу, что я могу вывести не более 10 изображений.')
        bot.register_next_step_handler(msg, show_picts, hot_id, bot, p_type)
    else:
        logger.info('Получен id отеля для показа изображений')
        logger.info(hot_id)
        if p_type == 'h_pic':
            one_hotel = ApiQuest(my_rapi, hot_id)
            logger.info('Отправлен запрос на получение изображений отеля')
            hotel_pics = one_hotel.get_hotel_pics()
            logger.info('Получен список url изображений отеля')
            logger.info(hotel_pics)
            for index, one_pict in enumerate(hotel_pics):
                if index < int(message.text):
                    final_pic = one_pict.replace('{size}', 'z')
                    bot.send_photo(chat_id=message.chat.id, photo=final_pic)
                    time.sleep(0.1)
                else:
                    break
        next_step: List = [('Показать последний запрос', str(message.chat.id) + '.his')]
        this_keyboard = BotKeyboard(next_step, 1)
        keyboard = this_keyboard.create_keys()
        bot.send_message(message.chat.id, text='Выберите действие: ', reply_markup=keyboard)


def show_history(message: types.Message) -> None:
    """
    Показывает легенду и результат последнего запроса пользователя
    :param message: Полученное в чате сообщение
    """
    hotels, tm_stamp = bot_database.select_some(message.chat.id, 'History', 'hotels', 't_stamp')
    hotels_list = json.loads(hotels)
    when = datetime.datetime.fromtimestamp(tm_stamp).strftime('%Y-%m-%d %H:%M')
    persons, city, hot_num, check_out, check_in, sorting_m, lang = bot_database.select_history(
        message.chat.id, tm_stamp, 'persons', 'city', 'hot_num',
        'check_out', 'check_in', 'state', 'lang')
    if sorting_m == 'low':
        sorting_m = 'lowprice'
    elif sorting_m == 'high':
        sorting_m = 'highprice'
    else:
        sorting_m = 'bestdeal'
    history_info = f'Последний запрос: \n' \
                   f'Время запроса: {when} \n' \
                   f'Команда: {sorting_m} \n' \
                   f'Город поиска: {city} \n' \
                   f'Дата заезда: {check_in} \n' \
                   f'Дата выезда: {check_out} \n' \
                   f'Количество проживающих: {persons} \n' \
                   f'Язык поиска: {lang} \n' \
                   f'Количество отелей: {hot_num} \n'
    bot.send_message(message.chat.id, history_info)
    show_hotels(message.chat.id, hotels_list, question='Результаты последнего запроса:')
