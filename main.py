from app import bot, mainWorker
from app.path import pathWorker
from app.user import userWorker
from app.bill import billWorker

from telebot import types
import inspect
import logging


@bot.message_handler(commands=['start'])
def start_message(message):
    print(message.from_user.id, message.from_user.username, 'KEYBOARD')
    bot.send_photo(message.chat.id, open('images/main.jpg', 'rb'),
                   reply_markup=mainWorker.main_keyboard(message.from_user.id,
                                                         message.from_user.username))


@bot.callback_query_handler(func=lambda call: True)
def main(call: types.CallbackQuery):
    """Обработка нажатий кнопки и вызов нужной функции"""
    print(call.from_user.username, call.data)
    logging.info(f'{call.from_user.username} {call.data}')
    args = [call.data]
    if ' ' in args[0]:  # Создание аргументов для функции
        args = args[0].split()
        if args[1].isdigit():
            args = [args[0], int(args[1]), *map(lambda i: int(i) if i.isdigit() else i, args[2:])]  # Получение аргументов из call.data
    args.insert(1, call.from_user.id)
    for worker in (mainWorker, pathWorker, userWorker, billWorker):
        for name, f in inspect.getmembers(worker, predicate=inspect.isfunction):  # Перебор функций
            if name == args[0]:
                try:
                    f(call, *args[1:])
                except Exception as err:
                    logging.error(err, exc_info=True)


if __name__ == '__main__':
    bot.polling(none_stop=True, interval=0)
