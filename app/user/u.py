import datetime
import json
from typing import Union
from typing import Any

from app.DBHandler import Handler
from app.bill.b import Bill


class Review:
    def __init__(self, score, text=''):
        self.score = int(score)
        self.text = text if text else '(Пустой комментарий)'

    def textForm(self) -> str:
        """Возвращение __dict__ в текстовой(для БД) форме"""
        return '::'.join([str(v) for i, v in self.__dict__.items()])

    @staticmethod
    def fromTextToObject(data: str) -> 'Review':
        return Review(*data.split('::'))


class User:
    handler = Handler()

    def __init__(self, user_id, nickname, is_driver=None, reviews_data: str = None,
                 form: str = None, last_paid: str = None, requests_id=None):
        """

        :param user_id:
        :param nickname:
        :param is_driver:
        :param reviews_data:
        :param form:
        :param last_paid: Когда был оплачен доступ
        """
        if not is_driver:
            is_driver = False
        self.user_id = int(user_id)
        self.nickname = nickname
        self.is_driver = is_driver == 'True' if isinstance(is_driver, str) else is_driver
        self.reviews = []
        self.form = json.loads(form) if form and form != 'None' else None
        self.last_paid: datetime.datetime = datetime.datetime.fromisoformat(last_paid) \
            if last_paid and last_paid != 'None' else None
        self.requests_id = []
        if reviews_data and reviews_data != 'None':
            for r in reviews_data.split('$$$'):
                self.reviews.append(Review.fromTextToObject(r))
        if isinstance(requests_id, str) and requests_id != 'None':
            for r in requests_id.split(','):
                print((requests_id, r))
                self.requests_id.append(int(r))

    @staticmethod
    def getUserId(username):
        if isinstance(username, str) and username.isdigit():
            return int(username)
        elif isinstance(username, int):
            return username
        return User.handler.getUserId(username) if str(username) != 'None' else None

    @staticmethod
    def getUser(user_id):
        return User.handler.get_user(user_id)

    @staticmethod
    def newUser(user_id, nickname) -> 'User':
        """Вносит данные в БД"""
        return User.handler.add_user(user_id, nickname)

    @staticmethod
    def getModersId() -> list:
        return list(map(int, open('moderators_id.txt', 'r').readlines()))

    def addReview(self, review: 'Review'):
        self.reviews.append(review)
        User.handler.update_user(self.user_id, 'reviews_data', self.__getstate__()['reviews_data'])

    def addRequest(self, request_id):
        self.requests_id.append(request_id)
        User.handler.update_user(self.user_id, 'requests_id', self.__getstate__()['requests_id'])

    def checkBills(self) -> Union[bool, Any]:
        '''Проверяет наличие неоплаченных счетов. True - есть'''
        for i in User.handler.get_all_bills_ids():
            i = Bill.get_bill(i)
            if i.to_username == self.nickname:
                if i.status is False:
                    return i
        if (datetime.datetime.now() - self.last_paid).days >= 30:
            Bill.add_bill(self.nickname, Bill.BILL_PRICE)
            return True
        return False

    def getScore(self):
        try:
            return round(sum([r.score for r in self.reviews]) / len(self.reviews), 2)
        except ZeroDivisionError:
            return 0

    def about(self):
        if self.is_driver:
            s = f'''
Водитель @{self.nickname}
Полное имя: {self.form['full_name']}
Автомобиль: {self.form['car_info']}
Номер авто: {self.form['car_number']}
Рейтинг: {self.getScore()}/5
            '''
        else:
            s = f'Пользователь @{self.nickname}' if self.nickname else 'Пользователь'
        return s

    def setDriver(self, val):
        self.is_driver = val
        if val:
            self.last_paid = datetime.datetime.now()

    def __getstate__(self) -> dict:
        d = self.__dict__.copy()
        d['reviews_data'] = ','.join([r.textForm() for r in self.reviews])
        if not d['reviews_data']:
            d['reviews_data'] = None
        d['requests_id'] = ','.join(map(str, self.requests_id))
        print('REQ', d['requests_id'])
        if not d['requests_id']:
            d['requests_id'] = None
        d.pop('reviews')
        d['last_paid'] = self.last_paid.isoformat() if self.last_paid is not None else None
        return d

    def __setattr__(self, key, value):
        self.__dict__[key] = value
        if key == 'user_id' or key == 'reviews' or key == 'requests_id':
            return
        if key == 'form' and value is not None:
            value = json.dumps(value)
        User.handler.update_user(self.user_id, key, value)

    def __str__(self):
        return f'{self.nickname}'