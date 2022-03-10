import peewee
from bot_classes import Session, History
from loguru import logger
from typing import List, Dict, Any


@logger.catch
def create_tables(one_model: str) -> None:
    """
    Если отсутствует таблица, создает ее в базе данных
    :param one_model: название класса, для использования внутри функции
    """
    logger.info(f'Попытка создания таблицы {one_model}')
    if not eval(one_model).table_exists():
        eval(one_model).create_table()
        logger.info('Таблица создана')
    else:
        logger.info('Таблица существует')


@logger.catch
def update_record(one_field: str, one_value: str, this_chat_id: int):
    """
    Обновляет значение поля в записи таблицы
    :param one_field: название поля, которое надо модифиуцировать
    :param one_value: значение модифицируемого поля
    :param this_chat_id: id чата, в котором происходит взаимодействие с ботом
    :return:
    """
    query = eval(f"""Session.update({one_field}='{one_value}').where(
        (Session.chat_id == this_chat_id) &
        (Session.t_stamp == Session.select(peewee.fn.MAX(Session.t_stamp)).where(
        Session.chat_id == this_chat_id).scalar()))""")
    logger.info('Сохраняю изменения в базу')
    query.execute()


@logger.catch
def select_some(chat_id: int, one_model: str, *args: Any) -> List[Any]:
    """
    Производит выборку из таблицы базы данных
    :param chat_id: id чата, в котором происходит взаимодействие с ботом
    :param one_model: название класса, для использования внутри функции
    :param args: название полей, по которым нужно выполнить выборку из базы данных
    :return: результат запроса в виде списка
    """
    this_record = eval(one_model).select().dicts().where((
            (eval(one_model).chat_id == chat_id) &
            (eval(one_model).t_stamp == eval(one_model).select(peewee.fn.MAX(eval(one_model).t_stamp)).where(
                eval(one_model).chat_id == chat_id).scalar()))).get()
    result = [this_record.get(field) for field in args]
    return result


def select_history(chat_id: int, tm_stamp: float, *args: Any) -> List[Any]:
    """
    Возвращает результат последнего запроса пользователя
    :param chat_id: id чата, в котором происходит взаимодействие с ботом
    :param tm_stamp: таймстамп начала работы цепочки взаимодействия с пользователем
    :param args: название полей, по которым нужно выполнить выборку из базы данных
    :return: Результат запроса в виде списка
    """
    logger.info(type(tm_stamp))
    logger.info(tm_stamp)
    this_record = Session.select().dicts().where(Session.t_stamp == tm_stamp).get()
    logger.info(this_record)
    result = [this_record.get(field) for field in args]
    return result


@logger.catch
def create_record(chat_id: int, state: str, tm_stamp: float) -> None:
    """
    Добавляет в таблицу Sessions новую запись
    :param chat_id: id чата
    :param state: тип цепочки (low, high, best)
    :param tm_stamp: таймстамп, содержит время ввода пользователем команды, после которой начинается цепочка
    """
    this_session = Session(chat_id=chat_id, state=state, lang='', city='', location='', hot_num='',
                           persons='', check_in='', check_out='', currency='', start_price='',
                           stop_price='', t_stamp=tm_stamp, distance='')
    try:
        this_session.save()
        logger.info(f'Начало сессии с chat_id = {chat_id}, получена команда {state}')
    except Exception as err:
        logger.error(f'Произошла ошибка при добавлении записи сессии с chat_id = {chat_id}.')
        logger.error(err)


@logger.catch
def create_history(chat_id: int, hotels: str, tm_stamp: float) -> None:
    """
    Добавляет запись в таблицу истории запросов пользователя
    :param chat_id: id чата
    :param hotels: строка, десериализованная из списка отелей
    :param tm_stamp: время начала цепочки
    """
    this_session = History(chat_id=chat_id, hotels=hotels, t_stamp=tm_stamp)
    try:
        this_session.save()
        logger.info(f'Сохранение результатов запроса chat_id = {chat_id}')
    except Exception:
        logger.error(f'Произошла ошибка при сохранении результатов запроса с chat_id = {chat_id}.')
