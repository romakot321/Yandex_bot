from typing import Union

from app import bot, locator, handler, mainWorker
from app.user import userWorker, User
from app.path import Path, Request, Response
from app.bill import Bill

import datetime
import geopy
import pytz
from telebot import types

path_create_steps = [
    ("from_point", 'Введите начальную точку, в которой вы будете находится. Указывайте адрес как можно точнее, '
                   'чтобы бот вас понял. Например, "Иркутск, Партизанская 1"'
                   'Введите "отмена" для отмены'),
    ("to_point", 'Введите адрес, в который вам необходимо попасть.'),
    ('add_text', 'Введите примечание к тексту("." чтобы оставить пустым)'),
    ('start_time', "Введите время, когда вы будете находится на начальной точке в формате ЧЧ:ММ по московскому времени"),
]


class notValidity(Exception):
    pass


def moder_testPath(call, *args):
    Path.addPath(None, call.from_user.username, None, 50,
                 'ТЕСТ', 'ТЕСТ', 10, 'ТЕСТТЕСТТЕСТ', datetime.datetime.now())
    mainWorker.mainMenu(call)


def comp_path_menu(call, *args):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text='Список созданных водителями маршрутов',
                                            callback_data='find_path'))
    keyboard.add(types.InlineKeyboardButton(text='Создать заявку', callback_data='new_request'))
    keyboard.add(types.InlineKeyboardButton(text='Назад', callback_data='mainMenu'))
    bot.edit_message_media(types.InputMediaPhoto(open('images/findPath.jpg', 'rb')),
                           call.message.chat.id, call.message.id,
                           reply_markup=keyboard)


def driver_path_menu(call, *args):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text='Список созданных попутчиками заявок',
                                            callback_data='find_request'))
    keyboard.add(types.InlineKeyboardButton(text='Создать маршрут', callback_data='new_path'))
    keyboard.add(types.InlineKeyboardButton(text='Назад', callback_data='mainMenu'))
    bot.edit_message_media(types.InputMediaPhoto(open('images/findPath.jpg', 'rb')),
                           call.message.chat.id, call.message.id,
                           reply_markup=keyboard)


def check_validity(msg: str, step: str) -> str:
    if step == 'from_point' or step == 'to_point':
        try:
            if locator.geocode(msg) is None:
                raise notValidity('Неверно введен адрес. Попробуйте снова.')
        except geopy.exc.GeocoderUnavailable:
            raise notValidity('Неверно введен адрес. Попробуйте снова.')
    if step == 'add_text':
        if msg == '.':
            return ''
    if step == 'start_time':
        if len(msg) >= 4 and ':' in msg:
            h, m = msg.split(':')
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
                raise notValidity('Неверный формат времени, попробуйте снова')
        else:
            raise notValidity('Неверный формат времени, попробуйте снова')
        return start_time
    return msg


def new_request(msg, user_id, data=None):
    if data is None and 'message' in msg.__dict__:
        if msg.from_user.username is None:
            bot.send_message(msg.message.chat.id, 'Пожалуйста, задайте имя пользователя в настройках вашего аккаунта, '
                                                  'чтобы другие попутчики могли с вами связаться.')
        data = []
        msg = msg.message
        bot.delete_message(msg.chat.id, msg.id)
    else:
        step = path_create_steps[len(data)][0]
        if step == 'from_point' and msg.text.lower() == 'отмена':
            bot.delete_message(msg.chat.id, msg.id - 1)
            mainWorker.sendMainMenu(msg)
            return
        try:
            data.append((step, check_validity(msg.text, step)))
        except notValidity as e:
            bot.send_message(msg.chat.id, e.args[0])
            bot.register_next_step_handler(msg, new_request, user_id, data)
            return
    if len(data) == len(path_create_steps):
        return create_request(msg, dict(data))
    step, text = path_create_steps[len(data)]
    bot.send_message(msg.chat.id, text)
    bot.register_next_step_handler(msg, new_request, user_id, data)


def create_request(msg, data: dict):
    data['id'] = None
    data['companion_id'] = msg.from_user.id
    Request.addRequest(req=Request(**data))
    bot.send_message(msg.chat.id, 'Заявка создана, ожидайте отклика одного из водителей.')
    mainWorker.sendMainMenu(msg)


def new_path(msg, user_id):
    u = User.getUser(user_id)
    if 'message' in msg.__dict__:
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
            bot.send_message(msg.chat.id, 'Введите стоимость проезда')
            bot.register_next_step_handler(msg, new_path4, from_point, to_point)
    except geopy.exc.GeocoderUnavailable:
        bot.send_message(msg.chat.id, 'Неверно введена конечная точка маршрута.')
        new_path2(msg, from_point)


def new_path4(msg, from_point, to_point, price=None):
    if price is None:
        price = msg.text
    if isinstance(price, str) and not price.isdigit():
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


def find_request(call, user_id, page=0):
    keyboard = types.InlineKeyboardMarkup()
    paths = Request.getAllRequestsId(paginition=True)
    for req_id in paths[page]:  # TODO система поиска
        req = Request.getRequest(req_id)
        if req.status == req.STATUS_LISTED:
            keyboard.add(types.InlineKeyboardButton(text=str(req),
                                                    callback_data=f'about_request {req_id}'))
    keyboard.add(types.InlineKeyboardButton(text='В меню', callback_data=f'mainMenu'))
    if page > 0:
        if page + 1 < len(paths):
            keyboard.row(
                types.InlineKeyboardButton(text='Следующие', callback_data=f'find_request {page + 1}'),
                types.InlineKeyboardButton(text='Назад', callback_data=f'find_request {page - 1}')
            )
        else:
            keyboard.add(types.InlineKeyboardButton(text='Назад', callback_data=f'find_request {page - 1}'))
        bot.edit_message_reply_markup(call.message.chat.id, call.message.id, reply_markup=keyboard)
    else:
        if page + 1 < len(paths):
            keyboard.add(
                types.InlineKeyboardButton(text='Следующие', callback_data=f'find_request {page + 1}'))
        bot.edit_message_media(types.InputMediaPhoto(open('images/findRequest.jpeg', 'rb')),
                               call.message.chat.id, call.message.id,
                               reply_markup=keyboard)


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


def about_request(call, user_id, req_id):
    keyboard = types.InlineKeyboardMarkup()
    req = Request.getRequest(req_id)
    if call.from_user.id == req.companion_id and req.status == Request.STATUS_LISTED:
        keyboard.add(types.InlineKeyboardButton(text='Посмотреть отклики', callback_data=f'responses {req_id}'))
        keyboard.add(types.InlineKeyboardButton(text='Отозвать заявку', callback_data=f'delete_request {req_id}'))
        keyboard.add(types.InlineKeyboardButton(text='Откликнуться', callback_data=f'respond {req_id}'))
    elif req.status == Request.STATUS_LISTED:
        keyboard.add(types.InlineKeyboardButton(text='Откликнуться', callback_data=f'respond {req_id}'))
    elif req.status == Request.STATUS_ACCEPTED \
            and req.start_time.timestamp() <= datetime.datetime.now(pytz.timezone('Europe/Moscow')).timestamp():
        user = User.getUser(user_id)
        if any([r == req.id for r in user.requests_id]):
            keyboard.add(types.InlineKeyboardButton(text='Завершить заявку', callback_data=f'finish_request {req_id}'))
    keyboard.add(types.InlineKeyboardButton(text='Назад', callback_data=f'delete_message'))
    bot.send_message(call.message.chat.id, req.about(), reply_markup=keyboard)


def finish_request(call, user_id, req_id):
    req = Request.getRequest(req_id)
    if not req.status == Request.STATUS_ACCEPTED:
        return
    userWorker.add_review1(call, req.companion_id, user_id)
    Request.deleteRequest(req_id)
    User.getUser(user_id).deleteRequest(req_id)
    mainWorker.delete_message(call)


def responses(call, user_id, req_id):
    keyboard = types.InlineKeyboardMarkup()
    req = Request.getRequest(req_id)
    for num, resp in enumerate(req.responses):
        keyboard.add(types.InlineKeyboardButton(text=str(resp), callback_data=f'about_response {req_id} {num}'))
    keyboard.add(types.InlineKeyboardButton(text='Назад', callback_data=f'delete_message'))
    bot.edit_message_reply_markup(call.message.chat.id, call.message.id, reply_markup=keyboard)


def about_response(call, user_id, req_id, resp_id):
    req = Request.getRequest(req_id)
    resp = req.responses[resp_id]
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text='Принять', callback_data=f'confirm_response {req_id} {resp_id}'))
    keyboard.add(types.InlineKeyboardButton(text='Отказать', callback_data=f'delete_response {req_id} {resp_id}'))
    keyboard.add(types.InlineKeyboardButton(text='Назад', callback_data=f'delete_message'))
    bot.send_message(call.message.chat.id, resp.about(), reply_markup=keyboard)


def confirm_response(call, user_id, req_id, resp_id):
    req = Request.getRequest(req_id)
    resp = req.responses[resp_id]
    driver = User.getUser(User.getUserId(resp.driver_username))
    bot.send_message(User.getUserId(resp.driver_username), f'Ваш отклик на заявку {req} приняли. Удачного пути!')
    req.status = Request.STATUS_ACCEPTED
    driver.addRequest(req.id)
    bot.delete_message(call.message.chat.id, call.message.id)


def delete_request(call, user_id, req_id):
    Request.deleteRequest(req_id)
    mainWorker.delete_message(call, user_id)


def respond(call, user_id, req_id):
    for resp in Request.getRequest(req_id).responses:
        if resp.driver_username == User.getUser(user_id).nickname:
            bot.send_message(call.message.chat.id, 'Вы уже оставили отклик на эту заявку')
            return
    bot.send_message(call.message.chat.id, 'Введите стоимость проезда')
    bot.register_next_step_handler(call.message, respond2, user_id, req_id)


def respond2(msg, user_id, req_id):
    if isinstance(msg.text, str) and not msg.text.isdigit():
        bot.send_message(msg.chat.id, 'Неверно введена стоимость проезда, попробуйте снова')
        bot.register_next_step_handler(msg, respond2, user_id, req_id)
        return
    bot.send_message(msg.chat.id, 'Введите примечание к заказу("." чтобы оставить пустым). Например, допустимый '
                                  'багаж, или присутствие детского кресла.')
    bot.register_next_step_handler(msg, respond3, user_id, req_id, int(msg.text))


def respond3(msg, user_id, req_id, price):
    add_text = msg.text if msg.text != '.' else ''
    Request.getRequest(req_id).addResponse(Response(req_id, msg.from_user.username, price, add_text))
    bot.send_message(msg.chat.id, 'Отклик оставлен, ожидайте')


def driver_requests(call, user_id):
    user = User.getUser(user_id)
    keyboard = types.InlineKeyboardMarkup()
    for req_id in user.requests_id:
        keyboard.add(types.InlineKeyboardButton(text=str(Request.getRequest(req_id)),
                                                callback_data=f'about_request {req_id}'))
    keyboard.add(types.InlineKeyboardButton(text='Назад', callback_data=f'mainMenu'))
    bot.edit_message_media(types.InputMediaPhoto(open('images/findRequest.jpeg', 'rb')),
                           call.message.chat.id, call.message.id,
                           reply_markup=keyboard)


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
    # b = Bill.add_bill(p.driver_username, p.price // 10)
    # bot.send_message(call.message.chat.id, b.text())


def join_to_path(call, user_id, path_id):
    p = Path.getPath(path_id)
    p.addCompanion(user_id)
    about_path(call, user_id, path_id, edit_msg=True)


def leave_path(call, user_id, path_id):
    p = Path.getPath(path_id)
    p.removeCompanion(user_id)
    about_path(call, user_id, path_id, edit_msg=True)
