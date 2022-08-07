from app.user import User
from app.bill import Bill
from app import bot, handler

from telebot import types


def main_keyboard(user_id: int, nickname: str) -> types.InlineKeyboardMarkup:
    """Клавиатура для главного меню"""
    keyboard = types.InlineKeyboardMarkup()
    u = User.getUser(user_id)
    if u is None:
        u = User.newUser(user_id, nickname)
    elif u.nickname != nickname:
        u.nickname = nickname

    keyboard.add(types.InlineKeyboardButton(text='Найти машину(по Иркутску)', callback_data='comp_path_menu'))
    if u.is_driver:
        keyboard.add(types.InlineKeyboardButton(text='Найти пассажира(по Иркутску)', callback_data='driver_path_menu'))
        keyboard.add(types.InlineKeyboardButton(text='Мой профиль', callback_data='profile'))
        keyboard.add(types.InlineKeyboardButton(text='Принятые заявки', callback_data='driver_requests'))
    elif not u.is_driver and u.form is None:
        keyboard.add(types.InlineKeyboardButton(text='Регистрация (водитель)', callback_data='register1'))

    keyboard.add(types.InlineKeyboardButton(text='О нашей компании', callback_data='about'))
    keyboard.add(types.InlineKeyboardButton(text='Задать вопрос', callback_data='question'))
    if int(user_id) in User.getModersId():
        keyboard.add(types.InlineKeyboardButton(text='Управление', callback_data='moder_menu'))
    return keyboard


def about(call, *args):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text='Назад', callback_data='delete_message'))
    bot.send_message(call.message.chat.id,
                     '''Данное коммерческое предприятие было основано 7 марта 2022 года в городе Иркутск (Россия).
Благодаря услугам сервиса «ЯПопутчик» люди, проживающие в Иркутске и его окрестностях имеют возможность сэкономить часть средств на поездках с попутчиками (водители могут заработать деньги на бензин, а пассажиры получат дешёвую, по сравнению с тарифами такси, поездку).
                     
Все права на коммерческое предприятие «ЯПопутчик» принадлежат Поленок Антону Дмитриевичу (ИНН: 383406776110)''',
                     reply_markup=keyboard)


def question(call, *args):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text='Назад', callback_data='delete_message'))
    bot.send_message(call.message.chat.id, 'По всем вопросам обращайтесь к @Anton_Polenok',
                     reply_markup=keyboard)


def moder_menu(call, user_id):
    """Отправление сообщения с меню модерации"""
    if int(user_id) in User.getModersId():
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text='Заявки', callback_data='moder_regRequests'))
        keyboard.add(types.InlineKeyboardButton(text='Создать тестовый маршрут', callback_data='moder_testPath'))
        keyboard.add(types.InlineKeyboardButton(text='Список открытых счетов', callback_data='moder_openBills'))
        keyboard.add(types.InlineKeyboardButton(text='Назад', callback_data='mainMenu'))
        bot.edit_message_media(types.InputMediaPhoto(open('images/moderMenu.jpg', 'rb')),
                               call.message.chat.id, call.message.id,
                               reply_markup=keyboard)


def moder_openBills(call, user_id):
    """Просмотр открытых счетов модерацией"""
    if int(user_id) in User.getModersId():
        keyboard = types.InlineKeyboardMarkup()
        bills = [Bill.get_bill(i) for i in handler.get_all_bills_ids() if not Bill.get_bill(i).status]
        for b in bills:
            keyboard.add(types.InlineKeyboardButton(text=f'{b.to_username} {b.price}руб.',
                                                    callback_data=f'moder_seeBill {b.bill_object.bill_id}'))
        keyboard.add(types.InlineKeyboardButton(text='Назад', callback_data='mainMenu'))
        bot.edit_message_reply_markup(call.message.chat.id, call.message.id, reply_markup=keyboard)


def moder_seeBill(call, user_id, bill_id):
    """Подробная информация о счете."""
    if int(user_id) in User.getModersId():
        bill = Bill.get_bill(bill_id)
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text='Аннулировать', callback_data=f'delete_bill {bill_id}'))
        keyboard.add(types.InlineKeyboardButton(text='Перевыпустить', callback_data=f'renew_bill {bill_id}'))
        keyboard.add(types.InlineKeyboardButton(text='Назад', callback_data='delete_message'))
        bot.send_message(call.message.chat.id, bill.text(), reply_markup=keyboard)


def moder_regRequests(call, *args):
    """Заявки на регистрацию. Одобрение или отклонение"""
    keyboard = types.InlineKeyboardMarkup()
    for user_id in handler.get_all_users_ids():
        u = User.getUser(user_id)
        if not u.is_driver and u.form:
            keyboard.add(types.InlineKeyboardButton(text=str(u), callback_data=f'moder_seeUserForm {u.user_id}'))
    keyboard.add(types.InlineKeyboardButton(text='Назад', callback_data=f'mainMenu'))
    bot.edit_message_media(types.InputMediaPhoto(open('images/moderMenu.jpg', 'rb')),
                           call.message.chat.id, call.message.id,
                           reply_markup=keyboard)


def moder_seeUserForm(call, user_id, form_user_id: int):
    """Просмотр определенной заявки с полной информацией
    :param user_id: Тот, кто нажал на кнопку
    :param form_user_id: Тот, чья форма
    """
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton(text='Подтвердить', callback_data=f'confirm_reg {form_user_id}'),
        types.InlineKeyboardButton(text='Отказать', callback_data=f'cancel_reg {form_user_id}'))
    keyboard.add(types.InlineKeyboardButton(text='Назад', callback_data=f'delete_message'))
    u = User.getUser(form_user_id)
    t = f'''
Водитель @{u.nickname}
Полное имя: {u.form['full_name']}
Дата рождения: {u.form['birthday']}
Автомобиль: {u.form['car_info']}
Номер авто: {u.form['car_number']}
Рейтинг: {u.getScore()}/5
    '''
    bot.send_photo(call.message.chat.id, u.form['car_photo'], caption=t, reply_markup=keyboard)


def confirm_reg(call, user_id, other_user_id: int):
    """
    :param user_id: Тот, кто нажал на кнопку
    :param other_user_id: Тот, с кем выполняются действия
    """
    User.getUser(other_user_id).setDriver(True)
    bot.send_message(other_user_id, f'Поздравляем, {User.getUser(other_user_id).nickname}, вы полностью прошли '
                                    f'регистрацию! Размещайте свои '
                                    'заявки на подвоз во вкладке «Найти пассажиров», которая находится в главном '
                                    'меню. Удачных поездок!')
    bot.delete_message(call.message.chat.id, call.message.id)
    bot.delete_message(call.message.chat.id, call.message.id - 1)


def cancel_reg(call, user_id, other_user_id: int):
    """
    :param user_id: Тот, кто нажал на кнопку
    :param other_user_id: Тот, с кем выполняются действия
    """
    User.getUser(other_user_id).form = None
    bot.send_message(other_user_id, 'К сожалению вы не прошли регистрацию. Проверьте достоверность введённых вами '
                                    'данных. Если есть дополнительные вопросы, то обращайтесь к главному '
                                    'менеджеру @Anton_Polenok')
    moder_regRequests(call, user_id)


def delete_message(call, *args):
    bot.delete_message(call.message.chat.id, call.message.id)


def mainMenu(call: types.CallbackQuery, *args):
    bot.edit_message_media(types.InputMediaPhoto(open('images/main.jpg', 'rb')),
                           call.message.chat.id, call.message.id,
                           reply_markup=main_keyboard(call.from_user.id,
                                                      call.from_user.username))


def sendMainMenu(msg, *args):
    """Не редактирование, а отправка"""
    if 'message' in msg.__dict__:
        msg = msg.message
    bot.send_photo(msg.chat.id, open('images/main.jpg', 'rb'),
                   reply_markup=main_keyboard(msg.from_user.id,
                                              msg.from_user.username))
    bot.delete_message(msg.chat.id, msg.id)
