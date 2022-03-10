import telebot
import bots_funcs
import os
import atexit
from dotenv import load_dotenv
from loguru import logger
from bot_database import create_tables
load_dotenv()
my_token = os.getenv('BOT_TOKEN')
my_rapi = os.getenv('RAPI_TOKEN')

@atexit.register
def goodbye() -> None:
    """
    Выводит сообщение при выходе
    """
    logger.info('Завершение')


bot = telebot.TeleBot(my_token)


@bot.message_handler(commands=['start', 'help', 'lowprice', 'highprice', 'bestdeal'])
def get_commands(message: telebot.types.Message) -> None:
    """
    Обработчик зарегистрированных команд
    :param message: Полученное в чате сообщение
    """
    bots_funcs.command_router(bot, message)


@bot.message_handler(content_types=['text'])
def get_text_messages(message: telebot.types.Message) -> None:
    """
    Обработчик текстовых сообщений
    :param message: Полученное в чате сообщение
    """
    bots_funcs.command_router(bot, message)


@bot.callback_query_handler(func=lambda call: True)
def callback_worker(call: telebot.types.CallbackQuery) -> None:
    """
    Обработчик событий inline-клавиатуры
    :param call: сообщение от inline-клавиатуры
    """
    logger.info(f'call {call.from_user.id}')
    logger.info(call.data)
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
    if call.data.startswith('calendar'):
        name, action, year, month, day = call.data.split(':')
        if action == 'DAY':
            bots_funcs.set_date(call)
        else:
            if action == 'NEXT-MONTH':
                month = str(int(month) + 1)
            elif action == 'PREVIOUS-MONTH':
                month = str(int(month) - 1)
            bots_funcs.show_calendar(bot, call.message, int(month), name=name)
    else:
        capt_list = call.data.split(sep='.')
        if capt_list[1] == 'loc':
            bots_funcs.get_lang(capt_list[0], call, bot)
        elif capt_list[1] == 'city':
            bots_funcs.get_start(capt_list[0], call.message, bot)
        elif capt_list[1] == 'hot':
            bots_funcs.chosen_hotel(capt_list[0], call, bot)
        elif capt_list[1].endswith('pic'):
            bots_funcs.get_picts(capt_list[0], call.message, bot, capt_list[1])
        elif capt_list[1] == 'his':
            bots_funcs.show_history(call.message)


if __name__ == '__main__':

    logger.add('hotel_logging.log', rotation="100 MB", encoding='utf-8')
    logger.info('Bot is starting')
    create_tables('Session')
    create_tables('History')
    bot.polling(none_stop=True, interval=0)
