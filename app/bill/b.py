import datetime

from pyqiwip2p import QiwiP2P
from app.DBHandler import Handler


class Bill:
    p2p = QiwiP2P(
        auth_key='eyJ2ZXJzaW9uIjoiUDJQIiwiZGF0YSI6eyJwYXlpbl9tZXJjaGFudF9zaXRlX3VpZCI6Im0wZ21ydy0wMCIsInVzZXJfaWQiOiI3OTAxNjMwNjkxMSIsInNlY3JldCI6IjhiOTRkNjM4ZDNiYjEwMWYxNWY3ZTVmYzdkNmFiYmZhMGFjYjY0ZTM2YmEzMmZiMTdjNzIyZTAzOGZhMTI0NmMifX0=', )
    handler = Handler()
    BILL_PRICE = 20

    def __init__(self, id, to_username, price):
        '''

        :param id: Айди счета, полученный из pyqiwip2p. None для создания
        :param to_username:
        :param price:
        '''
        if id is None:
            self.bill_object = Bill.p2p.bill(amount=int(price),
                                             expiration=datetime.datetime.now() + datetime.timedelta(days=1))
        else:
            self.bill_object = Bill.p2p.bill(bill_id=id)
        self.to_username = to_username
        self.price = int(price)

    @property
    def status(self):
        return None
    @status.getter
    def status(self) -> bool:
        '''True - оплачено, False - ожидание или просрочено'''
        return Bill.p2p.check(bill_id=self.bill_object.bill_id).status == 'PAID'

    @staticmethod
    def add_bill(to_username, price) -> 'Bill':
        b = Bill(None, to_username, price)
        Bill.handler.add_bill(**b.__getstate__())
        return b

    @staticmethod
    def get_bill(id):
        return Bill.handler.get_bill(id)

    def text(self):
        s = f'''
Счет для @{self.to_username}, Статус - {Bill.p2p.check(bill_id=self.bill_object.bill_id).status}
Стоимость: {self.price} руб.
Ссылка на оплату: {self.bill_object.pay_url}
        '''
        return s

    def delete(self):
        Bill.handler.delete_bill(self.bill_object.bill_id)

    def renew(self):
        self.bill_object = Bill.p2p.bill(amount=int(self.price),
                                         expiration=datetime.datetime.now() + datetime.timedelta(days=1))

    def __getstate__(self) -> dict:
        d = {'id': self.bill_object.bill_id}
        d.update(self.__dict__.copy())
        d.pop('bill_object')
        return d