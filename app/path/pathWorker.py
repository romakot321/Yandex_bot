from app import bot, locator, handler, mainWorker
from app.user import userWorker, User
from app.path import Path
from app.bill import Bill

import datetime
import geopy
import pytz
from telebot import types


def moder_testPath(call, *args):
    Path.addPath(None, call.from_user.username, None, 50,
                 'ТЕСТ', 'ТЕСТ', 10, 'ТЕСТТЕСТТЕСТ', datetime.datetime.now())
    mainWorker.mainMenu(call)


def new_path(msg, user_id):
    u = User.getUser(user_id)
    if 'message' in msg.__dict__:
        call = msg
        msg = msg.message
    b = u.checkBills()
    if not b:
        text = 'Введите начальную точку маршрута. Указывайте адрес как можно точнее, чтобы бот вас понял. ' \
               'Например, "Иркутск, Партизанская 1"' \
               'Введите "отмена" для отмены'
        bot.delete_message(msg.chat.id, msg.id)
        bot.send_message(msg.chat.id, text)
        bot.register_next_step_handler(msg, new_path2)
    else:
        bot.send_message(msg.chat.id, 'Оплатите все счета для продолжения. При возникновении проблем обращайтесь '
                                      f'в модерацию \n\n{b.text()}')


def new_path2(msg, from_point=None):
    if msg.text.lower() == 'отмена':
        bot.send_photo(msg.chat.id, open('images/main.jpg', 'rb'),
                       reply_markup=mainWorker.main_keyboard(msg.from_user.id,
                                                             msg.from_user.username))
        bot.delete_message(msg.chat.id, msg.id)
        bot.delete_message(msg.chat.id, msg.id - 1)
        return
    if from_point is None:
        from_point = msg.text
    try:
        if locator.geocode(from_point) is None:
            bot.send_message(msg.chat.id, 'Неверно введена начальная точка маршрута.')
            new_path(msg, msg.from_user.id)
        else:
            bot.send_message(msg.chat.id, 'Введите конечную точку маршрута.')
            bot.register_next_step_handler(msg, new_path3, from_point)
    except geopy.exc.GeocoderUnavailable:
        bot.send_message(msg.chat.id, 'Неверно введена начальная точка маршрута.')
        new_path(msg, msg.from_user.id)


def new_path3(msg, from_point, to_point=None):
    if to_point is None:
        to_point = msg.text
    try:
        if locator.geocode(to_point) is None:
            bot.send_message(msg.chat.id, 'Неверно введена конечная точка маршрута.')
            new_path2(msg, from_point)
        else:
            bot.send_message(msg.chat.id, 'Введите стоимость проезда. Минимум 10 рублей.')
            bot.register_next_step_handler(msg, new_path4, from_point, to_point)
    except geopy.exc.GeocoderUnavailable:
        bot.send_message(msg.chat.id, 'Неверно введена конечная точка маршрута.')
        new_path2(msg, from_point)


def new_path4(msg, from_point, to_point, price=None):
    if price is None:
        price = msg.text
    if isinstance(price, str) and not price.isdigit() or price.isdigit() and int(price) < 10:
        bot.send_message(msg.chat.id, 'Неверно введена стоимость проезда, попробуйте снова')
        new_path3(msg, from_point, to_point)
        return
    bot.send_message(msg.chat.id, 'Введите максимальное кол-во попутчиков(пассажиров).')
    bot.register_next_step_handler(msg, new_path5, from_point, to_point, price)


def new_path5(msg, from_point, to_point, price, max_companions=None):
    if max_companions is None:
        max_companions = msg.text
    if isinstance(max_companions, str) and not max_companions.isdigit() \
            or int(max_companions) < 1:
        bot.send_message(msg.chat.id, 'Неверно введено кол-во попутчиков, попробуйте снова')
        new_path4(msg, from_point, to_point, price)
        return
    bot.send_message(msg.chat.id, 'Введите примечание к заказу("." чтобы оставить пустым). Например, допустимый '
                                  'багаж, или присутствие детского кресла.')
    bot.register_next_step_handler(msg, new_path6, from_point, to_point, price, max_companions)


def new_path6(msg, from_point, to_point, price, max_companions, add_text=None):
    if add_text is None:
        add_text = msg.text
    bot.send_message(msg.chat.id, 'Введите время начала поездки в формате ЧЧ:ММ по московскому времени')
    bot.register_next_step_handler(msg, new_path7, from_point, to_point,
                                   price, max_companions, add_text)


def new_path7(msg, from_point, to_point, price, max_companions, add_text):
    if len(msg.text) >= 4 and ':' in msg.text:
        h, m = msg.text.split(':')
        if h.isdigit() and m.isdigit() and int(h) in range(0, 24) and int(m) in range(0, 60):
            start_time = datetime.datetime.now().replace(hour=int(h), minute=int(m),
                                                         second=0)
            if datetime.datetime.now(pytz.timezone('Europe/Moscow')).hour > start_time.hour:
                try:
                    start_time = start_time.replace(day=start_time.day + 1)
                except ValueError:
                    try:
                        start_time = start_time.replace(month=start_time.month + 1, day=1)
                    except ValueError:
                        start_time = start_time.replace(month=1, day=1)
        else:
            bot.send_message(msg.chat.id, 'Неверный формат времени, попробуйте снова')
            new_path6(msg, from_point, to_point, price, max_companions, add_text)
            return
    else:
        bot.send_message(msg.chat.id, 'Неверный формат времени, попробуйте снова')
        new_path6(msg, from_point, to_point, price, max_companions, add_text)
        return
    if add_text == '.':
        add_text = ''

    bot.send_message(msg.chat.id, 'Маршрут зарегистрирован.')
    Path.addPath(None, msg.from_user.username, None, int(max_companions),
                 from_point, to_point, int(price), add_text, start_time)
    for i in range(12):
        bot.delete_message(msg.chat.id, msg.id - i)
    bot.send_photo(msg.chat.id, open('images/main.jpg', 'rb'),
                   reply_markup=mainWorker.main_keyboard(msg.from_user.id,
                                                         msg.from_user.username))


def find_path(call, user_id, page=0):
    keyboard = types.InlineKeyboardMarkup()
    paths = Path.getAllPathsId(paginition=True)
    for path_id in paths[page]:  # TODO система поиска
        p = Path.getPath(path_id)
        if p.finish_time is None:
            keyboard.add(types.InlineKeyboardButton(text=str(p),
                                                    callback_data=f'about_path {path_id}'))
    keyboard.add(types.InlineKeyboardButton(text='В меню', callback_data=f'mainMenu'))
    if page > 0:
        if page + 1 < len(paths):
            keyboard.row(
                types.InlineKeyboardButton(text='Следующие', callback_data=f'find_path {page + 1}'),
                types.InlineKeyboardButton(text='Назад', callback_data=f'find_path {page - 1}')
            )
        else:
            keyboard.add(types.InlineKeyboardButton(text='Назад', callback_data=f'find_path {page - 1}'))
        bot.edit_message_reply_markup(call.message.chat.id, call.message.id, reply_markup=keyboard)
    else:
        if page + 1 < len(paths):
            keyboard.add(types.InlineKeyboardButton(text='Следующие', callback_data=f'find_path {page + 1}'))
        bot.edit_message_media(types.InputMediaPhoto(open('images/findPath.jpg', 'rb')),
                               call.message.chat.id, call.message.id,
                               reply_markup=keyboard)


def about_path(call, user_id, path_id, edit_msg=False):
    keyboard = types.InlineKeyboardMarkup()
    p = Path.getPath(path_id)
    keyboard.add(types.InlineKeyboardButton(text='Отзывы о водителе',
                                            callback_data=f'reviews_user {p.driver_id} {path_id}'))
    if call.from_user.id == p.driver_id:
        if p.start_time is None:
            keyboard.add(types.InlineKeyboardButton(text='Начать поездку',
                                                    callback_data=f'start_path {p.id}'))
        elif p.finish_time is None \
                and p.start_time.timestamp() <= datetime.datetime.now(pytz.timezone('Europe/Moscow')).timestamp():
            keyboard.add(types.InlineKeyboardButton(text='Окончить поездку',
                                                    callback_data=f'finish_path {p.id}'))
    elif p.finish_time is None:
        if int(call.from_user.id) not in p.companions and len(p.companions) < p.max_companions:
            keyboard.add(types.InlineKeyboardButton(text='Присоединиться',
                                                    callback_data=f'join_to_path {p.id}'))
        else:
            keyboard.add(types.InlineKeyboardButton(text='Выйти',
                                                    callback_data=f'leave_path {p.id}'))
    keyboard.add(types.InlineKeyboardButton(text='Назад', callback_data=f'delete_message'))
    if edit_msg:
        bot.edit_message_caption(p.about(), call.message.chat.id, call.message.id,
                                 reply_markup=keyboard)
    else:
        bot.send_photo(call.message.chat.id, User.getUser(p.driver_id).form['car_photo'],
                       caption=p.about(), reply_markup=keyboard)


def start_path(call, user_id, path_id):
    p = Path.getPath(path_id)
    if not any([Path.getPath(i).start_time is not None and Path.getPath(i).finish_time is None for i in
                handler.get_all_paths_ids()
                if Path.getPath(i).driver_username == p.driver_username]):
        p.start_time = datetime.datetime.now()
        # bot.send_message(call.message.chat.id, f'Начало поездки - {p.start_time}')
        for c in p.companions:
            bot.send_message(c, f'Поездка {str(p)} началась')
        about_path(call, user_id, path_id, edit_msg=True)


def finish_path(call, user_id, path_id):
    p = Path.getPath(path_id)
    p.finish_time = datetime.datetime.now()
    about_path(call, user_id, path_id, edit_msg=True)
    for c in p.companions:
        userWorker.add_review1(call, c, p.driver_username)
    b = Bill.add_bill(p.driver_username, p.price // 10)
    bot.send_message(call.message.chat.id, b.text())


def join_to_path(call, user_id, path_id):
    p = Path.getPath(path_id)
    p.addCompanion(user_id)
    about_path(call, user_id, path_id, edit_msg=True)


def leave_path(call, user_id, path_id):
    p = Path.getPath(path_id)
    p.removeCompanion(user_id)
    about_path(call, user_id, path_id, edit_msg=True)
