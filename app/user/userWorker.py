import os
from typing import Union

from app import mainWorker, bot
from app.user import User, Review
from telebot import types


import datetime

register_steps = [
    ('full_name', 'Введите ФИО.\nДля отмены введите "отмена"'),
    ('birthday', 'Введите дату рождения в формате ДД.ММ.ГГГГ(пример: 01.05.1968)'),
#    ('driver_license', "Введите данные водительского удостоверения"),
    ('car_info', "Введите полное название и цвет авто (пример: белый Kia Rio 2019 год)"),
    ('car_number', "Введите номерной знак автомобиля (пример: М123ЯУ138)"),
    ('car_photo', 'Отправьте фотографию автомобиля.')
]



class notValidity(Exception):
    pass


def check_validity(msg: Union[str, types.Message], step: str) -> Union[str, types.Message]:
    """Проверка на правильность заполнения формы регистрации
    :param msg: Полученое сообщение
    :param step: Шаг заполнения из register_steps"""
    if step == 'birthday':
        msg = msg.split('.')
        if len(msg) == 3:
            day, month, year = msg
            if day.isdigit() and month.isdigit() and year.isdigit():
                if int(day) in range(1, 32) and int(month) in range(1, 13) \
                        and datetime.datetime.now().year - 100 < int(year) < datetime.datetime.now().year:
                    return '.'.join(msg)
        raise notValidity('Неверно введена дата рождения. Попробуйте снова')
    elif step == 'car_number':
        letters = 'АВЕКМНОРСТУХ'
        nums = '1234567890'
        if 7 < len(msg) <= 9 and any([i in msg for i in nums]) and any([i.lower() in msg.lower() for i in letters]):
            return msg
        raise notValidity('Неверно введен номер автомобиля. Попробуйте снова')
    elif step == 'car_photo':
        if msg.photo is not None:
            return msg
        raise notValidity('Фото не найдено. Попробуйте снова')
    return msg


def register1(message, user_id, data=None):
    if 'message' in message.__dict__.keys():
        if message.from_user.username is None:
            bot.send_message(message.message.chat.id,
                             'Задайте имя пользователя в настройках своего аккаунта для продолжения.')
            return
        message = message.message
    if User.getUser(user_id).is_driver is False:
        if data is None:
            bot.send_photo(message.chat.id, open('images/registration.jpg', 'rb'))
            data = []
        else:
            with open('msgs.log', 'a') as f:
                f.write(f"{datetime.datetime.now().isoformat()}\t{message.from_user.username} {message.text}\n")
            if message.text and message.text.lower() == 'отмена':
                mainWorker.sendMainMenu(message, user_id)
                return
            step = register_steps[len(data)][0]
            try:
                if step == 'car_photo':
                    data.append((step, check_validity(message, step).photo[-1].file_id))
                else:
                    data.append((step, check_validity(message.text, step)))
            except notValidity as e:
                bot.send_message(message.chat.id, e.args[0])
                bot.register_next_step_handler(message, register1, user_id, data)
                return
        if len(data) == len(register_steps):
            return register2(message, user_id, dict(data))
        else:
            bot.send_message(message.chat.id, register_steps[len(data)][1])
            bot.register_next_step_handler(message, register1, user_id, data)
    else:
        bot.send_message(message.chat.id, 'Вы уже зарегистрированы.')


def register2(msg, user_id, data: dict):
    bot.send_message(msg.chat.id, 'Заявка на регистрацию подана на рассмотрение, ожидайте. Регистрируясь, '
                                  'вы принимаете политику обработки персональных данных')
    with open(os.path.join('images', 'data_info_comp.docx'), 'rb') as f:
        bot.send_document(msg.chat.id, f)
    User.getUser(user_id).is_driver = False
    User.getUser(user_id).form = data
    if user_id in User.getModersId():
        return
    for moder in User.getModersId():
        bot.send_message(moder, 'Создана новая заявка на регистрацию')


def add_review1(call, user_id, to_user):
    """Создание отзыва о водителе"""
    if isinstance(to_user, int):
        to_user = User.getUser(to_user).nickname
    m = bot.send_message(user_id, f'Введите комментарий("." чтобы оставить пустым) отзыва для '
                                  f'пользователя @{to_user}.')
    bot.register_next_step_handler(m, add_review2, user_id, to_user)


def add_review2(msg, user_id, to_user):
    if '$' in msg.text:
        bot.send_message(msg.chat.id, 'Нельзя использовать символ "$" в отзыве.')
        add_review1(None, user_id, to_user)
    bot.send_message(msg.chat.id, f'Введите оценку от 1 до 5(целое число) для пользователя @{to_user}.')
    bot.register_next_step_handler(msg, add_review3, user_id, to_user, msg.text)


def add_review3(msg, user_id, to_user, text):
    if isinstance(msg.text, str) and msg.text.isdigit() and int(msg.text) in range(1, 6):
        if text.strip() == '.':
            text = ''
        User.getUser(User.getUserId(to_user)).addReview(Review(int(msg.text), text))
        bot.send_message(msg.chat.id, 'Отзыв оставлен.')
    else:
        bot.send_message(msg.chat.id, 'Неверно введена оценка')


def profile(call, user_id):
    """Кнопка Профиль в главном меню"""
    u = User.getUser(user_id)
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text='Назад', callback_data=f'mainMenu'))
    keyboard.add(types.InlineKeyboardButton(text='Редактировать профиль', callback_data=f'edit_profile'))
    text = f'''
Водитель @{u.nickname}
Полное имя: {u.form['full_name']}
Дата рождения: {u.form['birthday']}
Автомобиль: {u.form['car_info']}
Номер авто: {u.form['car_number']}
Рейтинг: {u.getScore()}/5
    '''
    bot.edit_message_media(types.InputMediaPhoto(u.form['car_photo'], caption=text),
                           call.message.chat.id, call.message.id,
                           reply_markup=keyboard)


def edit_profile(call, user_id):
    bot.delete_message(call.message.chat.id, call.message.id)
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text='Назад', callback_data=f'delete_message'))
    keyboard.add(types.InlineKeyboardButton(text='Согласен(-на)', callback_data=f'edit_profile2'))
    bot.send_message(call.message.chat.id, 'После редактирования профиля, доступ к созданию маршрутов будет '
                                           'временно заблокирован, пока модераторы не подтвердят новую '
                                           'информацию. Вы согласны на продолжение?', reply_markup=keyboard)


def edit_profile2(message, user_id, data=None):
    if 'message' in message.__dict__.keys():
        message = message.message
    if data is None:
        data = []
    else:
        step = register_steps[len(data)][0]
        try:
            if message.text and message.text == '.':
                data.append((step, User.getUser(user_id).form[step]))
            elif register_steps[len(data)][0] == 'car_photo':
                data.append((step, check_validity(message, step).photo[-1].file_id))
            else:
                if message.text.lower() == 'отмена':
                    mainWorker.sendMainMenu(message, user_id)
                    return
                data.append((register_steps[len(data)][0], check_validity(message.text, step)))
        except notValidity as e:
            bot.send_message(message.chat.id, e.args[0])
            bot.register_next_step_handler(message, edit_profile2, user_id, data)
            return
    if len(data) == len(register_steps):
        register2(message, user_id, dict(data))
    else:
        bot.send_message(message.chat.id, register_steps[len(data)][1]
                         + '\nВведите "." чтобы не редактировать.')
        bot.register_next_step_handler(message, edit_profile2, user_id, data)


def reviews_user(call, user_id, reviews_user_id: int, ref_path_id: int):
    """
    :param user_id: От кого получено сообщение
    :param reviews_user_id: У кого смотреть отзывы"""
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text='Назад', callback_data=f'about_path {ref_path_id} 1'))
    u = User.getUser(reviews_user_id)
    t = 'Отзывы:\n'
    for r in u.reviews:
        t += '\t' + r.text + f'\n\tОценка: {r.score}/5\n\n'
    bot.edit_message_caption(t, call.message.chat.id, call.message.id, reply_markup=keyboard)
