import datetime
import inspect

import pytz as pytz
import telebot
from telebot import types

from b import Bill
from p import Path
from u import User, Review
from DBHandler import Handler
import geopy

bot = telebot.TeleBot(open('config_file').read())
locator = geopy.Nominatim(user_agent="A")
handler = Handler()


def main_keyboard(user_id, nickname):
    keyboard = types.InlineKeyboardMarkup()
    u = User.getUser(user_id)
    if u is None:
        u = User.newUser(user_id, nickname)

    keyboard.add(types.InlineKeyboardButton(text='Найти машину(по Иркутску)', callback_data='find_path'))
    if u.is_driver:
        keyboard.add(types.InlineKeyboardButton(text='Найти пассажира(по Иркутску)', callback_data='new_path'))
        keyboard.add(types.InlineKeyboardButton(text='Профиль', callback_data='profile'))
    elif not u.is_driver and u.form is None:
        keyboard.add(types.InlineKeyboardButton(text='Регистрация (водитель)', callback_data='register1'))

    keyboard.add(types.InlineKeyboardButton(text='О нашей компании', callback_data='about'))
    keyboard.add(types.InlineKeyboardButton(text='Задать вопрос', callback_data='question'))
    if int(user_id) in User.getModersId():
        keyboard.add(types.InlineKeyboardButton(text='Управление', callback_data='moder_menu'))
    return keyboard


class Worker:
    register_steps = [
        ('full_name', 'Введите ФИО. Кстати, наш сервис будет брать с вас комиссию 10% с каждого выполненного заказа.'),
        ('birthday', 'Введите дату рождения'),
        ('driver_license', "Введите данные водительского удостоверения"),
        ('car_info', "Введите полное название и цвет авто (пример: белый Kia Rio 2019 год)"),
        ('car_number', "Введите номерной знак автомобиля (пример: М123ЯУ138)"),
        ('car_photo', 'Отправьте фотографию автомобиля.')
    ]

    @staticmethod
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

    @staticmethod
    def question(call, *args):
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text='Назад', callback_data='delete_message'))
        bot.send_message(call.message.chat.id, 'По всем вопросам обращайтесь к @Polenok_Anton',
                         reply_markup=keyboard)

    @staticmethod
    def register1(message, user_id, data=None):
        if 'message' in message.__dict__.keys():
            message = message.message
        if User.getUser(user_id).is_driver is False:
            if data is None:
                bot.send_photo(message.chat.id, open('registration.jpg', 'rb'))
                data = []
            else:
                if Worker.register_steps[len(data)][0] == 'car_photo':
                    data.append((Worker.register_steps[len(data)][0], message.photo[-1].file_id))
                else:
                    data.append((Worker.register_steps[len(data)][0], message.text))

            if len(data) == len(Worker.register_steps):
                Worker.register2(message, user_id, dict(data))
            else:
                bot.send_message(message.chat.id, Worker.register_steps[len(data)][1])
                bot.register_next_step_handler(message, Worker.register1, user_id, data)
        else:
            bot.send_message(message.chat.id, 'Вы уже зарегестрированы.')

    @staticmethod
    def register2(msg, user_id, data):
        bot.send_message(msg.chat.id, 'Заявка на регистрацию подана на рассмотрение, ожидайте.')
        User.getUser(user_id).form = data

    @staticmethod
    def moder_menu(call, user_id):
        if int(user_id) in User.getModersId():
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton(text='Заявки', callback_data='moder_regRequests'))
            keyboard.add(types.InlineKeyboardButton(text='Создать тестовый маршрут', callback_data='moder_testPath'))
            keyboard.add(types.InlineKeyboardButton(text='Назад', callback_data='mainMenu'))
            bot.edit_message_media(types.InputMediaPhoto(open('moderMenu.jpg', 'rb')),
                                   call.message.chat.id, call.message.id,
                                   reply_markup=keyboard)

    @staticmethod
    def moder_testPath(call, *args):
        Path.addPath(None, call.from_user.username, None, 50,
                     'ТЕСТ', 'ТЕСТ', 10, 'ТЕСТТЕСТТЕСТ', datetime.datetime.now())
        Worker.mainMenu(call)

    @staticmethod
    def moder_regRequests(call, *args):
        keyboard = types.InlineKeyboardMarkup()
        for user_id in handler.get_all_users_ids():
            u = User.getUser(user_id)
            if not u.is_driver and u.form:
                keyboard.add(types.InlineKeyboardButton(text=str(u), callback_data=f'moder_seeUserForm {u.user_id}'))
        keyboard.add(types.InlineKeyboardButton(text='Назад', callback_data=f'mainMenu'))
        bot.edit_message_media(types.InputMediaPhoto(open('moderMenu.jpg', 'rb')),
                               call.message.chat.id, call.message.id,
                               reply_markup=keyboard)

    @staticmethod
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

    @staticmethod
    def delete_message(call, *args):
        bot.delete_message(call.message.chat.id, call.message.id)

    @staticmethod
    def confirm_reg(call, user_id, other_user_id: int):
        """
        :param user_id: Тот, кто нажал на кнопку
        :param other_user_id: Тот, с кем выполняются действия
        """
        User.getUser(other_user_id).is_driver = True
        bot.send_message(other_user_id, f'Поздравляем, {User.getUser(other_user_id).nickname}, вы полностью прошли '
                                        f'регистрацию! Размещайте свои '
                                        'заявки на подвоз во вкладке «Найти пассажиров», которая находится в главном '
                                        'меню. Удачных поездок!')
        bot.delete_message(call.message.chat.id, call.message.id)
        bot.delete_message(call.message.chat.id, call.message.id - 1)
        # Worker.moder_regRequests(call, user_id)

    @staticmethod
    def cancel_reg(call, user_id, other_user_id: int):
        """
        :param user_id: Тот, кто нажал на кнопку
        :param other_user_id: Тот, с кем выполняются действия
        """
        User.getUser(other_user_id).form = ''
        bot.send_message(other_user_id, 'К сожалению вы не прошли регистрацию. Проверьте достоверность введённых вами '
                                        'данных. Если есть дополнительные вопросы, то обращайтесь к главному '
                                        'менеджеру @Polenok_Anton')
        Worker.moder_regRequests(call, user_id)

    @staticmethod
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
            bot.register_next_step_handler(msg, Worker.new_path2)
        else:
            bot.send_message(msg.chat.id, 'Оплатите все счета для продолжения. При возникновении проблем обращайтесь '
                                          f'в модерацию \n\n{b.text()}')

    @staticmethod
    def new_path2(msg, from_point=None):
        if msg.text.lower() == 'отмена':
            bot.send_photo(msg.chat.id, open('main.jpg', 'rb'),
                           reply_markup=main_keyboard(msg.from_user.id,
                                                      msg.from_user.username))
            bot.delete_message(msg.chat.id, msg.id)
            bot.delete_message(msg.chat.id, msg.id - 1)
            return
        if from_point is None:
            from_point = msg.text
        try:
            if locator.geocode(from_point) is None:
                bot.send_message(msg.chat.id, 'Неверно введена начальная точка маршрута.')
                Worker.new_path(msg, msg.from_user.id)
            else:
                bot.send_message(msg.chat.id, 'Введите конечную точку маршрута.')
                bot.register_next_step_handler(msg, Worker.new_path3, from_point)
        except geopy.exc.GeocoderUnavailable:
            bot.send_message(msg.chat.id, 'Неверно введена начальная точка маршрута.')
            Worker.new_path(msg, msg.from_user.id)

    @staticmethod
    def new_path3(msg, from_point, to_point=None):
        if to_point is None:
            to_point = msg.text
        try:
            if locator.geocode(to_point) is None:
                bot.send_message(msg.chat.id, 'Неверно введена конечная точка маршрута.')
                Worker.new_path2(msg, from_point)
            else:
                bot.send_message(msg.chat.id, 'Введите стоимость проезда. Минимум 10 рублей.')
                bot.register_next_step_handler(msg, Worker.new_path4, from_point, to_point)
        except geopy.exc.GeocoderUnavailable:
            bot.send_message(msg.chat.id, 'Неверно введена конечная точка маршрута.')
            Worker.new_path2(msg, from_point)

    @staticmethod
    def new_path4(msg, from_point, to_point, price=None):
        if price is None:
            price = msg.text
        if isinstance(price, str) and not price.isdigit() or price.isdigit() and int(price) < 10:
            bot.send_message(msg.chat.id, 'Неверно введена стоимость проезда, попробуйте снова')
            Worker.new_path3(msg, from_point, to_point)
            return
        bot.send_message(msg.chat.id, 'Введите максимальное кол-во попутчиков(пассажиров).')
        bot.register_next_step_handler(msg, Worker.new_path5, from_point, to_point, price)

    @staticmethod
    def new_path5(msg, from_point, to_point, price, max_companions=None):
        if max_companions is None:
            max_companions = msg.text
        if isinstance(max_companions, str) and not max_companions.isdigit():
            bot.send_message(msg.chat.id, 'Неверно введено кол-во попутчиков, попробуйте снова')
            Worker.new_path4(msg, from_point, to_point, price)
            return
        bot.send_message(msg.chat.id, 'Введите примечание к заказу("." чтобы оставить пустым). Например, допустимый '
                                      'багаж, или присутствие детского кресла.')
        bot.register_next_step_handler(msg, Worker.new_path6, from_point, to_point, price, max_companions)

    @staticmethod
    def new_path6(msg, from_point, to_point, price, max_companions, add_text=None):
        if add_text is None:
            add_text = msg.text
        bot.send_message(msg.chat.id, 'Введите время начала поездки в формате ЧЧ:ММ по московскому времени')
        bot.register_next_step_handler(msg, Worker.new_path7, from_point, to_point,
                                       price, max_companions, add_text)

    @staticmethod
    def new_path7(msg, from_point, to_point, price, max_companions, add_text):
        if len(msg.text) > 4 and ':' in msg.text:
            h, m = msg.text.split(':')
            if h.isdigit() and m.isdigit():
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
                Worker.new_path6(msg, from_point, to_point, price, max_companions, add_text)
                return
        else:
            bot.send_message(msg.chat.id, 'Неверный формат времени, попробуйте снова')
            Worker.new_path6(msg, from_point, to_point, price, max_companions, add_text)
            return
        if add_text == '.':
            add_text = ''

        bot.send_message(msg.chat.id, 'Маршрут зарегистрирован.')
        Path.addPath(None, msg.from_user.username, None, int(max_companions),
                     from_point, to_point, int(price), add_text, start_time)
        for i in range(12):
            bot.delete_message(msg.chat.id, msg.id - i)
        bot.send_photo(msg.chat.id, open('main.jpg', 'rb'),
                       reply_markup=main_keyboard(msg.from_user.id,
                                                  msg.from_user.username))

    @staticmethod
    def mainMenu(call: types.CallbackQuery, *args):
        bot.edit_message_media(types.InputMediaPhoto(open('main.jpg', 'rb')),
                               call.message.chat.id, call.message.id,
                               reply_markup=main_keyboard(call.from_user.id,
                                                          call.from_user.username))

    @staticmethod
    def sendMainMenu(call, *args):
        """Не редактирование, а отправка"""
        bot.send_photo(call.message.chat.id, open('main.jpg', 'rb'),
                       reply_markup=main_keyboard(call.from_user.id,
                                                  call.from_user.username))
        bot.delete_message(call.message.chat.id, call.message.id)

    @staticmethod
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
            bot.edit_message_media(types.InputMediaPhoto(open('findPath.jpg', 'rb')),
                                   call.message.chat.id, call.message.id,
                                   reply_markup=keyboard)

    @staticmethod
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

    @staticmethod
    def start_path(call, user_id, path_id):
        p = Path.getPath(path_id)
        if not any([Path.getPath(i).start_time is not None and Path.getPath(i).finish_time is None for i in
                    handler.get_all_paths_ids()
                    if Path.getPath(i).driver_username == p.driver_username]):
            p.start_time = datetime.datetime.now()
            # bot.send_message(call.message.chat.id, f'Начало поездки - {p.start_time}')
            for c in p.companions:
                bot.send_message(c, f'Поездка {str(p)} началась')
            Worker.about_path(call, user_id, path_id, edit_msg=True)

    @staticmethod
    def finish_path(call, user_id, path_id):
        p = Path.getPath(path_id)
        p.finish_time = datetime.datetime.now()
        Worker.about_path(call, user_id, path_id, edit_msg=True)
        for c in p.companions:
            Worker.add_review1(call, c, p.driver_username)
        b = Bill.add_bill(p.driver_username, p.price // 10)
        bot.send_message(call.message.chat.id, b.text())

    @staticmethod
    def add_review1(call, user_id, to_user):
        if isinstance(to_user, int):
            to_user = User.getUser(to_user).nickname
        m = bot.send_message(user_id, f'Введите комментарий("." чтобы оставить пустым) отзыва для '
                                      f'пользователя @{to_user}.')
        bot.register_next_step_handler(m, Worker.add_review2, user_id, to_user)

    @staticmethod
    def add_review2(msg, user_id, to_user):
        if '$' in msg.text:
            bot.send_message(msg.chat.id, 'Нельзя использовать символ "$" в отзыве. Отзыв оставлен пустым')
            msg.text = '.'
        bot.send_message(msg.chat.id, f'Введите оценку от 1 до 5(целое число) для пользователя @{to_user}.')
        bot.register_next_step_handler(msg, Worker.add_review3, user_id, to_user, msg.text)

    @staticmethod
    def add_review3(msg, user_id, to_user_id, text):
        if isinstance(msg.text, str) and msg.text.isdigit() and int(msg.text) in range(1, 6):
            if text.strip() == '.':
                text = ''
            User.getUser(to_user_id).addReview(Review(int(msg.text), text))
            bot.send_message(msg.chat.id, 'Отзыв оставлен.')
        else:
            bot.send_message(msg.chat.id, 'Неверно введена оценка')

    @staticmethod
    def join_to_path(call, user_id, path_id):
        p = Path.getPath(path_id)
        p.addCompanion(user_id)
        Worker.about_path(call, user_id, path_id, edit_msg=True)

    @staticmethod
    def leave_path(call, user_id, path_id):
        p = Path.getPath(path_id)
        p.removeCompanion(user_id)
        Worker.about_path(call, user_id, path_id, edit_msg=True)

    @staticmethod
    def reviews_user(call, user_id, reviews_user_id, ref_path_id):
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text='Назад', callback_data=f'about_path {ref_path_id} 1'))
        u = User.getUser(reviews_user_id)
        t = 'Отзывы:\n'
        for r in u.reviews:
            t += '\t' + r.text + f'\n\tОценка: {r.score}/5\n\n'
        bot.edit_message_caption(t, call.message.chat.id, call.message.id, reply_markup=keyboard)

    @staticmethod
    def profile(call, user_id):
        u = User.getUser(user_id)
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text='Назад', callback_data=f'mainMenu'))
        keyboard.add(types.InlineKeyboardButton(text='Редактировать профиль', callback_data=f'edit_profile'))
        t = f'''
Водитель @{u.nickname}
Полное имя: {u.form['full_name']}
Дата рождения: {u.form['birthday']}
Водительское удостоверение: {u.form['driver_license']}
Автомобиль: {u.form['car_info']}
Номер авто: {u.form['car_number']}
Рейтинг: {u.getScore()}/5
        '''
        bot.edit_message_media(types.InputMediaPhoto(u.form['car_photo'], caption=t),
                               call.message.chat.id, call.message.id,
                               reply_markup=keyboard)

    @staticmethod
    def edit_profile(call, user_id):
        bot.delete_message(call.message.chat.id, call.message.id)
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text='Назад', callback_data=f'delete_message'))
        keyboard.add(types.InlineKeyboardButton(text='Согласен(-на)', callback_data=f'edit_profile2'))
        bot.send_message(call.message.chat.id, 'После редактирования профиля, доступ к созданию маршрутов будет '
                                               'временно заблокирован, пока модераторы не подтвердят новую '
                                               'информацию. Вы согласны на продолжение?', reply_markup=keyboard)

    @staticmethod
    def edit_profile2(message, user_id, data=None):
        if 'message' in message.__dict__.keys():
            message = message.message
        if data is None:
            User.getUser(user_id).is_driver = False
            data = []
        else:
            if message.text == '.':
                data.append((Worker.register_steps[len(data)][0],
                             User.getUser(user_id).form[Worker.register_steps[len(data)][0]]))
            elif Worker.register_steps[len(data)][0] == 'car_photo':
                data.append((Worker.register_steps[len(data)][0], message.photo[-1].file_id))
            else:
                data.append((Worker.register_steps[len(data)][0], message.text))

        if len(data) == len(Worker.register_steps):
            Worker.register2(message, user_id, dict(data))
        else:
            bot.send_message(message.chat.id, Worker.register_steps[len(data)][1]
                             + '\nВведите "." чтобы не редактировать.')
            bot.register_next_step_handler(message, Worker.edit_profile2, user_id, data)


@bot.message_handler(commands=['start'])
def start_message(message):
    print(message.from_user.id, message.from_user.username, 'KEYBOARD')
    bot.send_photo(message.chat.id, open('main.jpg', 'rb'),
                   reply_markup=main_keyboard(message.from_user.id,
                                              message.from_user.username))


@bot.callback_query_handler(func=lambda call: True)
def main(call: types.CallbackQuery):
    print(call.from_user.username, call.data)
    args = [call.data]
    if ' ' in args[0]:
        args = args[0].split()
        if args[1].isdigit():
            args = [args[0], int(args[1]), *map(lambda i: int(i) if i.isdigit() else i, args[2:])]
    args.insert(1, call.from_user.id)
    for name, f in inspect.getmembers(Worker, predicate=inspect.isfunction):
        if name == args[0]:
            f(call, *args[1:])


if __name__ == '__main__':
    bot.polling(none_stop=True, interval=0)
