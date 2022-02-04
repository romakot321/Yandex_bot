import datetime
from typing import List

from DBHandler import Handler


class Path:
    handler = Handler()

    def __init__(self, id, driver_username, companions, max_companions,
                 from_point, to_point, price: int, add_text=None,
                 start_time=None, finish_time=None):
        """Создание маршрута

        :param id: айди маршрута, None для автоматического определения
        :param driver_username: Ник водителя
        :param from_point: Откуда
        :param to_point: Куда
        :param price: Цена
        :param add_text: Замечание от водителя
        """
        if id is None:
            id = len(Path.handler.get_all_paths_ids()) + 1
        if companions:
            if companions == 'None':
                companions = []
            else:
                companions = list(map(int, str(companions).split(',')))
        else:
            companions = []
        self.id = int(id)
        self.driver_username = driver_username
        self.companions: List[int] = companions
        self.max_companions = int(max_companions)
        self.from_point = from_point
        self.to_point = to_point
        self.price = price
        self.add_text = '' if not add_text else add_text  # TODO: ввод замечания от водителя
        if isinstance(start_time, datetime.datetime):
            self.start_time = start_time
        else:
            self.start_time = datetime.datetime.fromisoformat(start_time) if start_time and start_time != 'None' else None
        self.finish_time = datetime.datetime.fromisoformat(finish_time) if finish_time and finish_time != 'None' else None

    @staticmethod
    def getPath(path_id) -> 'Path':
        return Path.handler.get_path(path_id)

    @staticmethod
    def addPath(*path_params, path: 'Path' = None):
        if path:
            Path.handler.add_path(path)
        else:
            Path.handler.add_path(Path(*path_params))

    def addCompanion(self, user_id):
        if len(self.companions) < self.max_companions:
            self.companions.append(user_id)
            Path.handler.update_path(self.id, 'companions', self.__getstate__()['companions_data'])

    def removeCompanion(self, user_id):
        if len(self.companions) > 0:
            try:
                self.companions.remove(user_id)
                Path.handler.update_path(self.id, 'companions', self.__getstate__()['companions_data'])
            except ValueError:
                pass

    def about(self):
        from u import User
        s = f'''
{User.getUser(self.driver_username).about()}
Цена - {self.price}
Примечание: {self.add_text}
Попутчики: {", ".join([f"@{User.getUser(i).nickname}" for i in self.companions])}({len(self.companions)}/{self.max_companions})'''
        if self.start_time is not None:
            s += '\n' + f'Время начала: {self.start_time.isoformat(sep=" ", timespec="minutes")}'
        if self.finish_time is not None:
            s += '\n' + f'Время окончания: {self.finish_time.isoformat(sep=" ", timespec="minutes")}'
        return s

    def __getstate__(self):
        d = self.__dict__.copy()
        d = list(d.items())
        d.insert(2, ('companions_data', ','.join([str(i) for i in self.companions])))
        d = dict(d)
        if not d['companions_data']:
            d['companions_data'] = None
        d.pop('companions')
        return d

    def __setattr__(self, key, value):
        self.__dict__[key] = value
        if key in ('start_time', 'finish_time') and value is not None:
            Path.handler.update_path(self.id, key, value.isoformat())

    def __str__(self):
        """Сокращенный текст маршрута"""
        return f'{self.from_point} - {self.to_point} [{self.price} руб.]'