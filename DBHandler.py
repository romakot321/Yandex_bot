import sqlite3
import time


class Handler:
    conn = sqlite3.connect('../taxi_bot/data', check_same_thread=False)
    cur = conn.cursor()

    def __init__(self):
        self.conn = sqlite3.connect('../taxi_bot/data', check_same_thread=False, isolation_level=None)
        self.cur = self.conn.cursor()

    def doAction(self, func, args):
        print(func, args)
        try:
            return func(*args)
        except sqlite3.ProgrammingError:
            time.sleep(1)
            self.doAction(func, args)

    @staticmethod
    def init():
        Handler.cur.executescript(
            '''
            CREATE TABLE users (
                id      INT     PRIMARY KEY
                                     NOT NULL
                                     UNIQUE,
                nickname     VARCHAR NOT NULL
                                     UNIQUE,
                is_driver    BOOLEAN NOT NULL
                                     DEFAULT (0),
                reviews_data TEXT,
                form         TEXT
            );
            '''
        )
        Handler.cur.executescript(
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
                finish_time     DATETIME
            );
            '''
        )
        Handler.cur.executescript(
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

    def get_user(self, user_id):
        from u import User
        self.conn.commit()
        if isinstance(user_id, int) or isinstance(user_id, str) and user_id.isdigit():
            try:
                u = Handler.cur.execute(f"SELECT * FROM users WHERE id='{int(user_id)}'").fetchall()
            except sqlite3.ProgrammingError:
                return self.doAction(self.get_user.__func__, (self, user_id,))
        elif isinstance(user_id, str):
            try:
                u = Handler.cur.execute(f"SELECT * FROM users WHERE nickname='{user_id}'").fetchall()
            except sqlite3.ProgrammingError:
                return self.doAction(self.get_user.__func__, (self, user_id,))
        if u:
            return User(*u[0])
        return None

    def get_all_users_ids(self, *args) -> list:
        try:
            return list(map(lambda i: i[0], self.cur.execute('SELECT id FROM users').fetchall()))
        except sqlite3.ProgrammingError:
            return self.doAction(self.get_all_users_ids.__func__, (self, None))

    def add_user(self, user_id, nickname):
        from u import User
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
        from p import Path
        try:
            p = self.cur.execute(f'SELECT * FROM paths WHERE id={path_id}').fetchall()
        except sqlite3.ProgrammingError:
            return self.doAction(self.get_path.__func__, (self, path_id,))
        if p:
            return Path(*p[0])

    def add_path(self, path):
        s = "', '".join([str(v) for _, v in path.__getstate__().items()])
        try:
            self.cur.execute(f"INSERT INTO paths VALUES ('{s}')")
            # self.conn.commit()
        except sqlite3.ProgrammingError:
            return self.doAction(self.add_path.__func__, (self, path,))

    def update_path(self, path_id, key, value):
        try:
            self.cur.execute(f"UPDATE paths SET {key}='{value}' WHERE id='{path_id}'")
            # self.conn.commit()
        except sqlite3.ProgrammingError:
            return self.doAction(self.update_path.__func__, (self, path_id, key, value))

    def get_all_paths_ids(self, *args) -> list:
        try:
            return list(map(lambda i: i[0], self.cur.execute('SELECT id FROM paths').fetchall()))
        except sqlite3.ProgrammingError:
            return self.doAction(self.get_all_paths_ids.__func__, (self, None))

    def add_bill(self, **bill_params):
        s = "', '".join([str(v) for _, v in bill_params.items()])
        print(s)
        try:
            self.cur.execute(f"INSERT INTO bills VALUES ('{s}')")
        except sqlite3.ProgrammingError:
            return self.doAction(self.add_user.__func__, (self, bill_params))

    def get_bill(self, id):
        from b import Bill
        try:
            p = self.cur.execute(f"SELECT * FROM bills WHERE id='{id}'").fetchall()
        except sqlite3.ProgrammingError:
            return self.doAction(self.get_path.__func__, (self, id))
        if p:
            return Bill(*p[0])

    def get_all_bills_ids(self, *args) -> list:
        try:
            return list(map(lambda i: i[0], self.cur.execute('SELECT id FROM bills').fetchall()))
        except sqlite3.ProgrammingError:
            return self.doAction(self.get_all_paths_ids.__func__, (self, None))