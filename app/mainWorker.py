from app.user import User
from app.bill import Bill
from app import bot, handler

from telebot import types


def main_keyboard(user_id, nickname):
    keyboard = types.InlineKeyboardMarkup()
    u = User.getUser(user_id)
    if u is None:
        u = User.newUser(user_id, nickname)

    keyboard.add(types.InlineKeyboardButton(text='Найти машину(по Иркутску)', callback_data='comp_path_menu'))
    if u.is_driver:
        keyboard.add(types.InlineKeyboardButton(text='Найти пассажира(по Иркутску)', callback_data='driver_path_menu'))
        keyboard.add(types.InlineKeyboardButton(text='Мой профиль', callback_data='profile'))
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
                     'Наша компания была основана (число) Поленок Антоном и Коваль Романом. Поле’Ок '
                     'ЯПопутчик предоставляет услуги перевозки груза и пассажиров в пределах вашего '
                     'населённого пункта (района, города). Благодаря нашему сервису люди могут сэкономить '
                     'значительную часть средств. А благодаря системе регистрации с помощью водительского '
                     'удостоверения и данных об автомобиле вы точно не будете беспокоиться о сохранности '
                     'своей жизни и вещей во время поездки. Наш девиз — «Наш клиент — компании элемент!»',
                     reply_markup=keyboard)


def question(call, *args):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text='Назад', callback_data='delete_message'))
    bot.send_message(call.message.chat.id, 'По всем вопросам обращайтесь к @Polenok_Anton',
                     reply_markup=keyboard)


def moder_menu(call, user_id):
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
    if int(user_id) in User.getModersId():
        keyboard = types.InlineKeyboardMarkup()
        bills = [Bill.get_bill(i) for i in handler.get_all_bills_ids() if not Bill.get_bill(i).status]
        for b in bills:
            keyboard.add(types.InlineKeyboardButton(text=f'{b.to_username} {b.price}руб.',
                                                    callback_data=f'moder_seeBill {b.bill_object.bill_id}'))
        keyboard.add(types.InlineKeyboardButton(text='Назад', callback_data='mainMenu'))
        bot.edit_message_reply_markup(call.message.chat.id, call.message.id, reply_markup=keyboard)


def moder_seeBill(call, user_id, bill_id):
    if int(user_id) in User.getModersId():
        bill = Bill.get_bill(bill_id)
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text='Аннулировать', callback_data=f'delete_bill {bill_id}'))
        keyboard.add(types.InlineKeyboardButton(text='Перевыпустить', callback_data=f'renew_bill {bill_id}'))
        keyboard.add(types.InlineKeyboardButton(text='Назад', callback_data='delete_message'))
        bot.send_message(call.message.chat.id, bill.text(), reply_markup=keyboard)


def moder_regRequests(call, *args):
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
    """
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
Водительское удостоверение: {u.form['driver_license']}
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
                                    'менеджеру @Polenok_Anton')
    moder_regRequests(call, user_id)


def delete_message(call, *args):
    bot.delete_message(call.message.chat.id, call.message.id)


def mainMenu(call: types.CallbackQuery, *args):
    bot.edit_message_media(types.InputMediaPhoto(open('images/main.jpg', 'rb')),
                           call.message.chat.id, call.message.id,
                           reply_markup=main_keyboard(call.from_user.id,
                                                      call.from_user.username))


def sendMainMenu(call, *args):
    """Не редактирование, а отправка"""
    if 'message' in call.__dict__:
        call = call.message
    bot.send_photo(call.chat.id, open('images/main.jpg', 'rb'),
                   reply_markup=main_keyboard(call.from_user.id,
                                              call.from_user.username))
    bot.delete_message(call.chat.id, call.id)
