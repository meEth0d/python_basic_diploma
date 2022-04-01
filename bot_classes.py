from typing import List, Dict, Tuple
from telebot import types
import requests
import peewee
from loguru import logger


db = peewee.SqliteDatabase('bot_sessions.db')


class BotKeyboard:

    """
    Класс, реализующий inline keyboard
    """

    def __init__(self, keys: List[Tuple], rows: int):
        """
        первичная инициализация класса
        :param keys: список, содержащий названия и возвращаемые значения кнопок
        :param rows: количество столбцов в клавиатуре. пока не работает
        """
        self.keys: List = keys
        self.rows: int = rows
        self.key_list: List = []

    @property
    def keys(self) -> List:
        """
        Возвращает список кнопок
        :return: список кнопок
        """
        return self._keys

    @keys.setter
    def keys(self, keys: List) -> None:
        """
        Инициализирует переменную, содержащую список кнопок
        :param keys: список кнопок
        """
        self._keys = keys[:]

    @property
    def rows(self) -> int:
        """
        Возвращает количество стобцов клавиатуры
        :return: количество столбцов клавиатуры
        """
        return self._rows

    @rows.setter
    def rows(self, rows: int) -> None:
        """
        Инициализирует переменную, содержащую количество столбцов
        :param rows: количество столбцов клавиатуры
        """
        self._rows = rows

    def create_keys(self) -> types.InlineKeyboardMarkup:
        """
        Создает и возвращает inline-клавиатуру
        :return:собственно, клавиатура
        """
        bot_keyboard = types.InlineKeyboardMarkup(row_width=self.rows)
        for one_key in self.keys:
            self.key_list.append(types.InlineKeyboardButton(one_key[0], callback_data=one_key[1]))
        for all_keys in self.key_list:
            bot_keyboard.add(all_keys)
        return bot_keyboard


class ThisHotel:

    """
    Класс, предоставляющий информацию по выбранному отелю
    """

    def __init__(self, all_data: Dict):
        self.data_dict: Dict = all_data

    @property
    def data_dict(self) -> Dict:
        return self._data_dict

    @data_dict.setter
    def data_dict(self, all_data: Dict) -> None:
        """
        Инициализирует переменную, содержащую список всех данных отеля
        :param all_data: все данные об отеле в виде словаря
        """
        self._data_dict: Dict = all_data

    def show_name(self) -> str:
        """
        Возвращает имя отеля
        :return: имя отеля
        """
        return self.data_dict.get('data').get('body').get('propertyDescription').get('name')

    def show_coordinates(self) -> List:
        """
        Возвращает координаты отеля
        :return: список, содержащий координаты отеля
        """
        latitude = self.data_dict.get('data').get('body').get('pdpHeader')\
            .get('hotelLocation').get('coordinates').get('latitude')
        longitude = self.data_dict.get('data').get('body').get('pdpHeader')\
            .get('hotelLocation').get('coordinates').get('longitude')
        return [latitude, longitude]

    def show_overview(self) -> Dict:
        """
        Возвращает обзор отеля
        :return: словарь, содержащий обзор отеля
        """
        this_overview = self.data_dict.get('data').get('body').get('overview').get('overviewSections')[0].get('content')
        return this_overview

    def show_around(self) -> Dict:
        """
        Возвращает окружение отеля
        :return: словарь, содержащий описание того, что рядом с отелем
        """
        this_around = self.data_dict.get('data').get('body').get('overview').get('overviewSections')[1].get('content')
        return this_around

    def show_address(self) -> str:
        """
        Возвращает адрес отеля
        :return: адрес отеля
        """
        this_address = self.data_dict.get('data').get('body').get('propertyDescription').get('address').get('fullAddress')
        return this_address

    def show_price(self) -> str:
        """
        Возвращает стоимость суток проживания в отеле
        :return: стоимость
        """
        this_price = str(self.data_dict.get('data').get('body').get('propertyDescription').get('featuredPrice')\
            .get('currentPrice').get('plain'))
        return this_price

    def get_all_info(self) -> str:
        """
        Собирает и возвращает строку, содержащую все данные об отеле
        :return: суммарно все данные об отеле в одной строке, разделенной символами перевода строки.
        """
        info_string: str = ''
        coords = self.show_coordinates()
        info_string += self.show_name()
        info_string += '\n'
        info_string += f'Координаты отеля: {coords[0]}, {coords[1]}\n\n'
        info_string += 'Описание:\n'
        info_string += '\n'.join(self.show_overview())
        info_string += '\n'
        info_string += '\n'
        info_string += 'Что находится рядом с отелем:\n'
        info_string += '\n'.join(self.show_around())
        info_string += '\n'
        info_string += 'Цена за одну ночь:\n'
        info_string += self.show_price()
        info_string += '\n'
        info_string += 'Адрес отеля:\n'
        info_string += self.show_address()
        return info_string


class ApiQuest:
    """
    Класс работы с rapidapi.com
    """

    def __init__(self, my_api: str, *args, **kwargs):
        """
        Инициализация переменных класса. Используются сеттеры ниже.
        :param токен подключения к rapidapi:
        :param args: urls and headers участвующие в запросе
        :param kwargs:
        """
        self.this_api = my_api
        self.this_query = args
        self._headers = {'x-rapidapi-key': self.this_api, 'x-rapidapi-host': "hotels4.p.rapidapi.com"}
        self._city_url = "https://hotels4.p.rapidapi.com/locations/search"
        self._hotels_url = "https://hotels4.p.rapidapi.com/properties/list"
        self._one_hotel_url = "https://hotels4.p.rapidapi.com/properties/get-details"
        self._hotel_pics_url = "https://hotels4.p.rapidapi.com/properties/get-hotel-photos"

    @property
    def this_api(self) -> str:
        return self._this_api

    @this_api.setter
    def this_api(self, my_api: str):
        self._this_api: str = my_api

    @property
    def this_query(self) -> Tuple[str]:
        return self._this_query

    @this_query.setter
    def this_query(self, args: Tuple):
        self._this_query: Tuple = args

    def get_response(self, one_url: str, query: Dict) -> Dict:
        """
        Получает, сериализует и возвращает ответ от API
        В случае ошибки при получении ответа, возвращает пустой словарь
        :param one_url: url, по которому производится запрос
        :param query: словарь, содержащий переменные, участвующие в запросе
        :return: Dict
        """
        response = dict()
        try:
            logger.info(f'Посылаю запрос {query} на url {one_url}')
            response = requests.request("GET", one_url, headers=self._headers, params=query)
            logger.info(f'Получен ответ {response}')
        except Exception:
            logger.info('Произошла ошибка при обращении к API сайта')
        return response.json()

    def get_city(self) -> List[Tuple]:
        """
        Получает список id городов, имя которых совпадает с введенным пользователем
        В случае ошибки возвращает пустой список
        :return: список кортежей, содержащих имя города с географической привязкой и его id
        """
        try:
            querystring = {'query': self.this_query[0], 'locale': self.this_query[1]}
            found_city = self.get_response(self._city_url, querystring)
            cities = [(elem.get('caption'), elem.get('destinationId'))
                      for elem in found_city.get('suggestions', [])[0].get('entities')
                      if elem.get('type') == 'CITY' and self.this_query[0].lower() in elem.get('name').lower()]
        except IndexError:
            cities = []
            logger.warning('Получен неправильный ответ от сайта при запросе города.')
        return cities

    @logger.catch
    def get_hotels(self) -> List[Tuple]:
        """
        Получает список отелей, подходящих под критерии, введенные пользователем.
        В случае ошибки возвращает пустой список
        :return: список кортежей, содержащих информацию об отелях
        """
        hotels_list = []
        try:
            querystring = {"adults1": self.this_query[0], "pageNumber": self.this_query[1],
                           "destinationId": self.this_query[2], "pageSize": self.this_query[3],
                           "checkOut": self.this_query[4], "checkIn": self.this_query[5], "sortOrder": self.this_query[6],
                           "locale": self.this_query[7], "currency": self.this_query[8]}
            if self.this_query[6] != 'DISTANCE_FROM_LANDMARK':
                logger.info(f'Команда {self.this_query[6]} в классе поиска отелей')
                found_hotels = self.get_response(self._hotels_url, querystring)
                hotels_list = [(f"{one_hotel.get('name')}\n{'⭐️' * int(one_hotel.get('starRating', 0))}\n "
                                f"{one_hotel.get('address').get('streetAddress')}. \n"
                                f"{str(one_hotel.get('ratePlan').get('price').get('exactCurrent'))} руб.\n"
                                f"{one_hotel.get('landmarks')[0].get('distance').split(sep=' ')[0]} \n до центра",
                                str(one_hotel.get('id')) + '.hot')
                               for one_hotel in found_hotels['data']['body']['searchResults']['results']]
            else:
                logger.info(f'Команда {self.this_query[6]} в классе поиска отелей, раздел bestdeal')
                if self.this_query[7] == 'en_US':
                    distance = round(float(self.this_query[10]) * 0.62, 2)
                else:
                    distance = float(self.this_query[10])
                querystring["priceMax"] = self.this_query[9]
                querystring["priceMin"] = '100'
                while len(hotels_list) < int(self.this_query[3]):
                    found_hotels: Dict = self.get_response(self._hotels_url, querystring)
                    next_page: str = found_hotels.get('data').get('body').get('searchResults').get(
                        'pagination').get("nextPageNumber")
                    if not next_page or int(next_page) <= int(querystring['pageNumber']):
                        break
                    logger.info(f'Номер следующей страницы: {next_page}')
                    querystring['pageNumber'] = next_page
                    hotels_list.extend([(f"{one_hotel.get('name')}\n{'⭐️' * int(one_hotel.get('starRating', 0))}\n "
                                         f"{one_hotel.get('address').get('streetAddress')}. \n"
                                         f"{str(one_hotel.get('ratePlan').get('price').get('exactCurrent'))} руб. \n"
                                         f"{one_hotel.get('landmarks')[0].get('distance').split(sep=' ')[0]} \n до центра",
                                         str(one_hotel.get('id')) + '.hot')
                                        for one_hotel in found_hotels['data']['body']['searchResults']['results']
                                        if float(one_hotel.get('landmarks')[0].get(
                            'distance').split(sep=' ')[0].replace(',', '.')) <= distance])
        except IndexError as err:
            logger.warning('Получен неправильный ответ от сайта при запросе отелей.')
            logger.warning(err)
        return hotels_list

    def get_one_hotel(self) -> str:
        """
        Получает от API и возвращает информацию об одном отеле. Использует для этого
        экземпляр класса ThisHotel
        :return: строка, содержащая полную информацию об отеле, получается с помощью экземпляра класса ThisHotel
        """
        try:
            querystring = {"id": self._this_query[0], "checkIn": self._this_query[1],
                                         "checkOut": self._this_query[2], "adults1": self._this_query[3],
                                         "currency": self._this_query[4], "locale": self._this_query[5]}
            this_hotel = self.get_response(self._one_hotel_url, querystring)
            if this_hotel.get('result') != 'OK':
                hotel_info = 'Произошла ошибка при обращении к сайту.'
            else:
                our_hotel = ThisHotel(this_hotel)
                hotel_info = our_hotel.get_all_info()
        except IndexError:
            hotel_info = 'Запрос составлен неверно, обратитесь к администратору.'
            logger.warning('Получен неправильный ответ от сайта при запросе конкретного отеля.')
            logger.warning(f'ID отеля: {self._this_query[0]}')
        return hotel_info

    def get_hotel_pics(self) -> List[str]:
        """
        Возвращает список url изображений отеля
        :return: список url изображений
        """
        pics: List = []
        try:
            querystring = {"id": self._this_query[0]}
            pictures = self.get_response(self._hotel_pics_url, querystring)
            one_hotel = pictures.get('hotelImages')
            if one_hotel:
                for one_pic in one_hotel:
                    pics.append(one_pic.get("baseUrl"))
            return pics
        except IndexError:
            logger.warning(f'Произошла ошибка при получении изображений отеля с id {self._this_query[0]}')
            return pics


class MainModel(peewee.Model):
    """
    Основной класс Peewee
    определяет базу данных
    """

    class Meta:
        database = db


class Session(MainModel):
    """
    Класс, определяющий таблицу запросов пользователя newsessions и методы работы с ней
    """
    chat_id = peewee.CharField()
    state = peewee.CharField()
    lang = peewee.CharField()
    city = peewee.CharField()
    location = peewee.CharField()
    hot_num = peewee.CharField()
    persons = peewee.CharField()
    check_in = peewee.CharField()
    check_out = peewee.CharField()
    currency = peewee.CharField()
    start_price = peewee.CharField()
    stop_price = peewee.CharField()
    t_stamp = peewee.FloatField()
    distance = peewee.CharField()

    class Meta:
        db_table = 'newsessions'


class History(MainModel):
    """
    Класс, определяющий таблицу истории запросов пользователя и методы работы с ней.
    """
    chat_id = peewee.CharField()
    hotels = peewee.TextField()
    t_stamp = peewee.FloatField()

    class Meta:
        db_table = 'newhistory'


