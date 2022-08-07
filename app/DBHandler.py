import sqlite3
import time
import os


class Handler:
    def __init__(self):
        if 'data.db' not in os.listdir():
            self.conn = sqlite3.connect('data.db', check_same_thread=False, isolation_level=None)
            self.cur = self.conn.cursor()
            self.init()
        else:
            self.conn = sqlite3.connect('data.db', check_same_thread=False, isolation_level=None)
            self.cur = self.conn.cursor()

    def doAction(self, func, args):
        try:
            return func(*args)
        except sqlite3.ProgrammingError:
            time.sleep(1)
            self.doAction(func, args)

    def init(self):
        """Создание файла базы данных"""
        self.cur.executescript(
            '''
            CREATE TABLE users (
                id      INT     PRIMARY KEY
                                     NOT NULL
                                     UNIQUE,
                nickname     VARCHAR NOT NULL,
                is_driver    BOOLEAN NOT NULL
                                     DEFAULT (0),
                reviews_data TEXT,
                form         TEXT,
                last_paid    VARCHAR,
                requests_id  STRING
            );
            '''
        )
        self.cur.executescript(
            '''
                CREATE TABLE paths (
                id              INT      UNIQUE
                                         PRIMARY KEY
                                         NOT NULL,
                driver_username VARCHAR  NOT NULL,
                companions      TEXT,
                max_companions  INT      NOT NULL
                                         DEFAULT (1),
                from_point      VARCHAR  NOT NULL,
                to_point        VARCHAR  NOT NULL,
                price           INT      NOT NULL,
                add_text        TEXT,
                start_time      DATETIME,
                finish_time     DATETIME,
                type            VARCHAR
            );
            '''
        )
        self.cur.executescript(
            '''
                CREATE TABLE requests (
                id                    PRIMARY KEY
                                      UNIQUE
                                      NOT NULL,
                companion_id INT      NOT NULL,
                from_point   VARCHAR  NOT NULL,
                to_point     VARCHAR  NOT NULL,
                start_time   DATETIME NOT NULL,
                add_text     TEXT,
                status         INT      NOT NULL,
                responses_data TEXT
            );
            '''
        )
        self.cur.executescript(
            '''
            CREATE TABLE bills (
                id          INT     PRIMARY KEY
                                    UNIQUE
                                    NOT NULL,
                to_username VARCHAR NOT NULL,
                price       INT     NOT NULL
            );
            '''
        )

    def get_user(self, user_id) -> 'User':
        from app.user.u import User
        self.conn.commit()
        if isinstance(user_id, int) or isinstance(user_id, str) and user_id.isdigit():
            try:
                u = self.cur.execute(f"SELECT * FROM users WHERE id='{int(user_id)}'").fetchall()
            except sqlite3.ProgrammingError:
                return self.doAction(self.get_user.__func__, (self, user_id,))
        elif isinstance(user_id, str) or user_id is None:
            raise ValueError('Get user by username not allowed OR id is None')
        if u:
            return User(*u[0])
        return None

    def getUserId(self, username: str) -> int:
        try:
            u = self.cur.execute(f"SELECT id FROM users WHERE nickname='{username}'").fetchall()
        except sqlite3.ProgrammingError:
            return self.doAction(self.get_user.__func__, (self, username,))
        try:
            return u[0][0]
        except IndexError:
            raise ValueError('User not found')

    def get_all_users_ids(self, *args) -> list:
        try:
            return list(map(lambda i: i[0], self.cur.execute('SELECT id FROM users').fetchall()))
        except sqlite3.ProgrammingError:
            return self.doAction(self.get_all_users_ids.__func__, (self, None))

    def add_user(self, user_id, nickname):
        from app.user.u import User
        uu = User(user_id, nickname)
        s = "', '".join([str(v) for _, v in uu.__getstate__().items()])
        try:
            self.cur.execute(f"INSERT INTO users VALUES ('{s}')")
            # self.conn.commit()
        except sqlite3.ProgrammingError:
            return self.doAction(self.add_user.__func__, (self, user_id, nickname))
        return uu

    def update_user(self, user_id, key, value):
        try:
            self.cur.execute(f"UPDATE users SET {key}='{value}' WHERE id='{user_id}'")
            # self.conn.commit()
        except sqlite3.ProgrammingError:
            return self.doAction(self.update_user.__func__, (self, user_id, key, value))

    def get_path(self, path_id):
        from app.path.p import Path, Request
        try:
            p = self.cur.execute(f'SELECT * FROM paths WHERE id={path_id}').fetchall()
        except sqlite3.ProgrammingError:
            return self.doAction(self.get_path.__func__, (self, path_id,))
        if p:
            data = p[0]
            if data[10] == 'path':
                return Path(*data)
            elif data[10] == 'companion_path':
                return Request(data=data)

    def add_path(self, path):
        s = "', '".join([str(v) for _, v in path.__getstate__().items()])
        try:
            self.cur.execute(f"INSERT INTO paths VALUES ('{s}')")
        except sqlite3.ProgrammingError:
            return self.doAction(self.add_path.__func__, (self, path,))

    def update_path(self, path_id, key, value):
        try:
            self.cur.execute(f"UPDATE paths SET {key}='{value}' WHERE id='{path_id}'")
        except sqlite3.ProgrammingError:
            return self.doAction(self.update_path.__func__, (self, path_id, key, value))

    def get_all_paths_ids(self, *args) -> list:
        try:
            return list(map(lambda i: i[0], self.cur.execute('SELECT id FROM paths').fetchall()))
        except sqlite3.ProgrammingError:
            return self.doAction(self.get_all_paths_ids.__func__, (self, None))

    def add_bill(self, **bill_params):
        s = "', '".join([str(v) for _, v in bill_params.items()])
        try:
            self.cur.execute(f"INSERT INTO bills VALUES ('{s}')")
        except sqlite3.ProgrammingError:
            return self.doAction(self.add_user.__func__, (self, bill_params))

    def get_bill(self, id):
        from app.bill.b import Bill
        try:
            p = self.cur.execute(f"SELECT * FROM bills WHERE id='{id}'").fetchall()
        except sqlite3.ProgrammingError:
            return self.doAction(self.get_path.__func__, (self, id))
        if p:
            return Bill(*p[0])

    def delete_bill(self, id):
        try:
            p = self.cur.execute(f"DELETE FROM bills WHERE id='{id}'").fetchall()
        except sqlite3.ProgrammingError:
            return self.doAction(self.delete_bill.__func__, (self, id))

    def get_all_bills_ids(self, *args) -> list:
        try:
            return list(map(lambda i: i[0], self.cur.execute('SELECT id FROM bills').fetchall()))
        except sqlite3.ProgrammingError:
            return self.doAction(self.get_all_bills_ids.__func__, (self, None))

    def get_request(self, id):
        from app.path import Request
        try:
            r = self.cur.execute(f"SELECT * FROM requests WHERE id='{id}'").fetchall()
        except sqlite3.ProgrammingError:
            return self.doAction(self.get_request.__func__, (self, id))
        if r:
            return Request(*r[0])

    def delete_request(self, id):
        try:
            p = self.cur.execute(f"DELETE FROM requests WHERE id='{id}'").fetchall()
        except sqlite3.ProgrammingError:
            return self.doAction(self.delete_request.__func__, (self, id))

    def update_request(self, req_id, key, value):
        try:
            self.cur.execute(f"UPDATE requests SET {key}='{value}' WHERE id='{req_id}'")
        except sqlite3.ProgrammingError:
            return self.doAction(self.update_request.__func__, (self, req_id, key, value))

    def get_all_requests_ids(self, *args) -> list:
        try:
            return list(map(lambda i: i[0], self.cur.execute('SELECT id FROM requests').fetchall()))
        except sqlite3.ProgrammingError:
            return self.doAction(self.get_all_requests_ids.__func__, (self, None))

    def add_request(self, request):
        s = "', '".join([str(v) for _, v in request.__getstate__().items()])
        try:
            self.cur.execute(f"INSERT INTO requests VALUES ('{s}')")
        except sqlite3.ProgrammingError:
            return self.doAction(self.add_request.__func__, (self, request))