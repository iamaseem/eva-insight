from psycopg2 import connect

from config import DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USERNAME

class DatabaseConnection:

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self,
        dbname: str = DB_NAME,
        user: str = DB_USERNAME,
        password: str = DB_PASSWORD,
        host: str = DB_HOST,
        port:str = DB_PORT,
    ):
        self.dbname = dbname
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self.connection = None

    def connect(self):
        if self.connection is None:
            self.connection = connect(
                database = self.dbname,
                user = self.user,
                host = self.host,
                port = self.port,
                password = self.password
            )
        return self.connection

    def close(self):
        if self.connection is not None:
            self.connection.close()
            self.connection = None
