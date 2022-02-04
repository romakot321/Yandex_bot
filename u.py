import json
from typing import Union
from typing import Any

from DBHandler import Handler
from b import Bill


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
                 form: str = None):
        if not is_driver:
            is_driver = False
        self.user_id = int(user_id)
        self.nickname = nickname
        self.is_driver = is_driver == 'True' if isinstance(is_driver, str) else is_driver
        self.reviews = []
        self.form = json.loads(form) if form and form != 'None' else None
        if reviews_data and reviews_data != 'None':
            for r in reviews_data.split('$$$'):
                self.reviews.append(Review.fromTextToObject(r))

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

    def checkBills(self) -> Union[bool, Any]:
        '''Проверяет наличие неоплаченных счетов. True - есть'''
        for i in User.handler.get_all_bills_ids():
            i = Bill.get_bill(i)
            if i.to_username == self.nickname:
                if i.status is False:
                    return i
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
            s = f'Пользователь @{self.nickname} (Оценка: {self.getScore()}/5)'
        return s

    def __getstate__(self) -> dict:
        d = self.__dict__.copy()
        d['reviews_data'] = ','.join([r.textForm() for r in self.reviews])
        if not d['reviews_data']:
            d['reviews_data'] = None
        d.pop('reviews')
        return d

    def __setattr__(self, key, value):
        self.__dict__[key] = value
        if key == 'user_id' or key == 'reviews':
            return
        if key == 'form' and value is not None:
            value = json.dumps(value)
        User.handler.update_user(self.user_id, key, value)

    def __str__(self):
        return f'{self.nickname}'