import socket
import struct
import select
import asyncio
import threading
import logging
import scapy
import os
import csv
import sys
import tempfile
import json
import hashlib
import re
import operator
from collections import OrderedDict


file_handler = logging.FileHandler(filename='tmp.log')
stdout_handler = logging.StreamHandler(stream=sys.stdout)
handlers = [stdout_handler]
# handlers = [file_handler, stdout_handler]

logging.basicConfig(
    level=logging.DEBUG, 
    format='[%(asctime)s] %(name)s - %(message)s',
    handlers=handlers
)

class Server:
    """
    Запуск сервера, приём клиентов, делегирование
    их обработки. Делегирует соединение в ClientHandler.
    """
    def __init__(self, database_path='./data', host='localhost', port='7777'):
        self.host = host
        self.port = port
        self.db_path = database_path
        self.server_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)


    def start(self):
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(1)
        client, addr = self.server_socket.accept()


    def accept_connections(self):
        pass

    
    def shutdown(self):
        pass


class ClientHandler:
    def __init__(self, conn, addr, database_manager, auth_manager, logger):
        pass

        
    def handle(self):
        pass


class SQLParser:
    """
    Парсит SQL-подобные запросы вида:
    SELECT col1, col2 FROM table WHERE col3 >= 10
    """

    SUPPORTED_OPERATORS = ['>=', '<=', '!=', '=', '<', '>']

    def parse(self, raw_query: str) -> dict:
        query = raw_query.strip().lower()
        pattern = r'^select\s+(?P<columns>[\*\w,\s]+)\s+from\s+(?P<table>\w+)(?:\s+where\s+(?P<condition>.+))?$'
        match = re.match(pattern, query)

        if not match: raise ValueError('Неверный формат запроса.')

        columns = [col.strip() for col in match.group('columns').split(',')]
        table = match.group('table')
        raw_condition = match.group('condition')

        condition = None
        if raw_condition:
            condition = self._parse_condition(raw_condition)
        
        return {
            'table': table,
            'columns': columns,
            'condition': condition
        }
    

    def _parse_condition(self, condition_str: str) -> dict:
        for op in self.SUPPORTED_OPERATORS:
            if op in condition_str:
                parts = condition_str.split(op)
                if len(parts) != 2:
                    raise ValueError('Неверное условие WHERE.')
                
                column = parts[0].strip()
                value = parts[1].strip().strip("'\'")

                if value.isdigit():
                    value = int(value)
                else:
                    try: value = float(value)
                    except ValueError: pass

                return {
                    'column': column,
                    'operator': op,
                    'value': value
                }
        raise ValueError('Неизвестный оператор в WHERE-условии.')
    

class QueryExecutor:
    """ВЫполняет SELECT-запросы по csv таблицам."""

    OPERATORS = {
        '=': operator.eq,
        '!=': operator.ne,
        '<': operator.lt,
        '>': operator.gt,
        '<=': operator.le,
        '>=': operator.ge
    }

    def __init__(self, database_path: str):
        self.db_path = database_path


    def execute(self, query_dict: dict) -> list[dict]:
        table_name = query_dict['table']
        columns = query_dict['columns']
        condition = query_dict['condition']

        table_dir = os.path.join(self.db_path, table_name)
        csv_file = os.path.join(table_dir, 'table.csv')

        if not os.path.isfile(csv_file):
            raise FileNotFoundError(f'Файл таблицы не найден: {csv_file}')

        result = []

        with open(csv_file, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # применяем условие where
                if condition:
                    col = condition['column']
                    op_str = condition['operator']
                    value = condition['value']

                    if col not in row:
                        continue

                    # преобразуем значения к флоату, если можно
                    row_val = row[col]

                    try: 
                        row_val = float(row_val)
                        value = float(value)

                    except ValueError: pass

                    op_func = self.OPERATORS.get(op_str)
                    if not op_func or not op_func(row_val, value): continue

                # выбираем только нужные колонки
                if columns == ['*']: filtered = row
                else: filtered = {col: row[col] for col in columns if col in row}

                result.append(filtered)

        return result

class CacheManager:
    """
    Кэширует результаты запросов по их хэшам.
    При переполнении удаляет самый старый элемент (FIFO).
    """

    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self.cache = OrderedDict()


    def get(self, query_hash: str):
        """
        Возвращает результат по хэшу запроса или None.
        """
        return self.cache.get(query_hash)


    def set(self, query_hash, result):
        """
        Сохраянет результат запроса в кэш.
        Удаляет старейший элемент при переполнении.
        """
        if query_hash in self.cache:
            # обновляем порядок
            self.cache.move_to_end(query_hash)
        self.cache[query_hash] = result

        if len(self.cache) > self.max_size:
            # удаляем первый (самый старый)
            self.cache.popitem(last=False) 


class DatabaseStructureBuilder:
    """
    Строит описание структуры базы данных:
    таблицы и их колонки.
    """
    
    def __init__(self, database_path: str):
        self.db_path = database_path


    def build(self) -> dict:
        structure = {}

        if not os.path.isdir(self.db_path):
            raise FileNotFoundError(f"Путь к базе данных не найден: {self.db_path}")

        for table_name in os.listdir(self.db_path):
            table_path = os.path.join(self.database_path, table_name)
            csv_file = os.path.join(table_path, 'table.csv')

            if not os.path.isfile(csv_file): continue # пропускаем, если файла нет

            try:
                with open(csv_file, mode='r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    headers = next(reader, None)
                    if headers:
                        structure[table_name] = headers
            except Exception as e:
                # пропускаем некорректные таблицы, но логируем
                print(f"Ошибка при чтении {csv_file}: {e}")

        return structure

class AuthenticationManager:
    """
    Отвечает за базовую аутентификацию клиентов.
    Проверяет логин и пароль по локальному хранилищу (файл), хэширует пароли.
    Хранит пользователей в JSON-файле в виде {username: password_hash}.
    """

    def __init__(self, users_file: str, logger):
        
        self.users_file = users_file
        self.logger = logger
        self.users = {}

        if os.path.exists(self.users_file):

            try:
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    self.users = json.load(f)
                self.logger.info(f"[Auth] Загружены {len(self.users)} пользователей.")

            except Exception as e:
                self.logger.error(f"[Auth] Ошибка при чтении файла пользователей: {e}")
            
        else:
            self.logger.warning(f"[Auth] Файл пользователей не найден: {self.users_file}")


    def authenticate(self, username: str, password: str) -> bool:
        """
        Проверка логина и пароля (MD-5 хеш).
        """
        password_hash = hashlib.md5(password.encode()).hexdigest()
        stored_hash = self.users.get(username)

        if stored_hash is None:
            self.logger.warning(f'[Auth] попытка входа с неизвестным пользователем: {username}')
            return False
        
        if stored_hash == password_hash:
            self.logger.info(f'[Auth] успешная аутентификация пользователя: {username}')
            return True
        
        else:
            self.logger.warning(f'[Auth] Неверный пароль для пользователя: {username}')
            return False
        
    
    def add_user(self, username: str, password: str):
        """
        Добавить нового пользователя. Хэширует пароль и сохраняет в файл.
        """

        if username in self.users:
            self.logger.warning(f'[Auth] Пользователь уже существует.')
            return False

        password_hash = hashlib.md5(password.encode()).hexdigest()
        self.users[username] = password_hash

        try:
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(self.users, f, indent=4)
            self.logger.info(f'[Auth] Пользователь добавлен: {username}')
            return True
        
        except Exception as e:
            self.logger.error(f'[Auth] Ошибка при сохранении пользователя: {e}')
            return False
              

class Logger:
    """
    Обёртка над стандартным logging.
    Используется для централизованного логгирования на клиенте и сервере.
    """

    def __init__(
            self,
            name: str = 'AppLogger',
            log_to_file: bool = False,
            file_name: str = 'app.log'
    ):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False      # для избежания дублежа сообщений

        formatter = logging.Formatter('[%(asctime)s] %(name)s - %(levelname)s - %(message)s')

        # поток в stdout
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        self.logger.addHandler(stream_handler)

        if log_to_file:
            file_handler = logging.FileHandler(filename=file_name)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def log(self, level: str, message: str):
        """
        Записывает сообщение с заданным уровнем.
        :param level: 'debug', 'info', 'warning', 'error', 'critical'
        :param message: текст сообщения
        """

        level = level.lower()
    
        if level == 'debug':
            self.logger.debug(message)
        elif level == 'info':
            self.logger.info(message)
        elif level == 'warning':
            self.logger.warning(message)
        elif level == 'error':
            self.logger.error(message)
        elif level == 'critical':
            self.logger.critical(message)
        else:
            self.logger.info(message)  # по дефолту

    def debug(self, message: str):
        self.logger.debug(message)

    def info(self, message: str):
        self.logger.info(message)

    def warning(self, message: str):
        self.logger.warning(message)

    def error(self, message: str):
        self.logger.error(message)

    def critical(self, message: str):
        self.logger.critical(message)
