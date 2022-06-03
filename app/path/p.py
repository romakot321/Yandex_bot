import datetime
from typing import List, Union

from app.DBHandler import Handler


class Path:
    handler = Handler()
    PATHS_PER_PAGE = 10

    def __init__(self, id: int, driver_username: str, companions: Union[list, str], max_companions: int,
                 from_point: str, to_point: str, price: int, add_text: str = None,
                 start_time=None, finish_time=None, type=None):
        """Создание маршрута

        :param id: айди маршрута, None для автоматического определения
        :param driver_username: Ник водителя
        :param from_point: Откуда
        :param to_point: Куда
        :param price: Цена
        :param add_text: Замечание от водителя
        """
        from app.user.u import User
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
        self.driver_id = User.getUserId(driver_username)
        self.companions: List[int] = companions
        self.max_companions = int(max_companions)
        self.from_point = from_point
        self.to_point = to_point
        self.price = price
        self.add_text = '' if not add_text else add_text
        if isinstance(start_time, datetime.datetime):
            self.start_time = start_time
        else:
            self.start_time = datetime.datetime.fromisoformat(start_time) \
                if start_time and start_time != 'None' else None
        self.finish_time = datetime.datetime.fromisoformat(finish_time) \
            if finish_time and finish_time != 'None' else None
        self.type = 'path' if type is None else type

    @staticmethod
    def getPath(path_id) -> 'Path':
        return Path.handler.get_path(path_id)

    @staticmethod
    def addPath(*path_params, path: 'Path' = None):
        if path:
            Path.handler.add_path(path)
        else:
            Path.handler.add_path(Path(*path_params))

    @staticmethod
    def getAllPathsId(paginition=False) -> List[List[int]]:
        if not paginition:
            return Path.handler.get_all_paths_ids()
        paths = Path.handler.get_all_paths_ids()
        return [paths[i:i + Path.PATHS_PER_PAGE]
                for i in range(0, len(paths), Path.PATHS_PER_PAGE)] if len(paths) > 0 else [[]]

    def addCompanion(self, user_id):
        if len(self.companions) < self.max_companions and user_id not in self.companions:
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
        from app.user.u import User
        s = f'''
{User.getUser(self.driver_id).about()}
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
        d.pop('driver_id')
        return d

    def __setattr__(self, key, value):
        self.__dict__[key] = value
        if key in ('start_time', 'finish_time') and value is not None:
            Path.handler.update_path(self.id, key, value.isoformat())

    def __str__(self):
        """Сокращенный текст маршрута"""
        return f'{self.from_point} - {self.to_point} [{self.price} руб.]'


class CompanionPath(Path):
    def __init__(self, id=None, from_point=None, to_point=None, add_text=None, start_time=None, companion_id=None,
                 data=None, **kwargs):
        if data is not None:  # Значения индексов берутся из sql таблицы data.db, table paths
            id = data[0]
            companion_id = int(data[1])
            from_point = data[4]
            to_point = data[5]
            add_text = data[7]
            start_time = data[8]
        if id is None:
            id = len(Path.handler.get_all_paths_ids()) + 1
        self.id = int(id)
        self.companion_id = companion_id
        self.from_point = from_point
        self.to_point = to_point
        self.add_text = add_text
        self.type = 'companion_path'
        if isinstance(start_time, datetime.datetime):
            self.start_time = start_time
        else:
            self.start_time = datetime.datetime.fromisoformat(start_time) \
                if start_time and start_time != 'None' else None

    def about(self):
        from app.user.u import User
        s = f'''
{User.getUser(self.companion_id).about()}
Примечание: {self.add_text}
Время начала: {self.start_time.isoformat(sep=" ", timespec="minutes")}'''
        return s

    def __str__(self):
        """Сокращенный текст маршрута"""
        return f'{self.from_point} - {self.to_point}'

    def __getstate__(self):
        d = self.__dict__.copy()
        d['driver_username'] = self.companion_id
        d.pop('companion_id')
        d.update({'companions': None, 'max_companions': 0, 'price': 0, 'finish_time': None})
        d = Path(**d).__getstate__()  # Возвращение данных в порядке как у Path
        d['type'] = 'companion_path'
        return d