from abc import ABC
from datetime import datetime
from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt, QAbstractItemModel, QAbstractTableModel, QModelIndex
from PyQt6.QtSql import QSqlDatabase, QSqlQuery
from tinkoff.invest import Account, AccessLevel, AccountType, AccountStatus, SecurityTradingStatus, Quotation
from LimitClasses import MyUnaryLimit, MyStreamLimit, UnaryLimitsManager
from MyDateTime import getUtcDateTime
from MyMoneyValue import MyMoneyValue


class MyTreeView(QtWidgets.QTreeView):
    def resizeColumnsToContents(self: QtWidgets.QTreeView):
        """Авторазмер всех столбцов TreeView под содержимое."""
        for i in range(self.model().columnCount()):
            self.resizeColumnToContents(i)  # Авторазмер i-го столбца под содержимое.


class update_class:
    def __init__(self, model: QAbstractTableModel | QAbstractItemModel, top_left_index: QModelIndex, bottom_right_index: QModelIndex):
        self._model: QAbstractTableModel | QAbstractItemModel = model
        self._top_left_index: QModelIndex = top_left_index
        self._bottom_right_index: QModelIndex = bottom_right_index

    def __call__(self):
        if not hasattr(self, '_model'):
            pass
            return
        return self._model.dataChanged.emit(self._top_left_index, self._bottom_right_index)


class Column:
    """Класс столбца."""
    def __init__(self, header: str | None = None, header_tooltip: str | None = None, data_function=None, display_function=None, tooltip_function=None,
                 background_function=None, foreground_function=None,
                 lessThan=None, sort_role: Qt.ItemDataRole = Qt.ItemDataRole.UserRole):
        self.header: str | None = header  # Название столбца.
        self.header_tooltip: str | None = header_tooltip  # Подсказка в заголовке.
        self.getData = data_function  # Функция для получения данных.
        self.getDisplay = data_function if display_function is None else display_function  # Функция для отображения данных.
        self.getToolTip = tooltip_function  # Функция для получения подсказки к отображаемым данным.
        self.getBackground = background_function
        self.getForeground = foreground_function

        self.getSortRole: Qt.ItemDataRole = sort_role  # Роль элементов, используемая для сортировки столбца.
        self.lessThan = lessThan

    def __call__(self, role: int = Qt.ItemDataRole.UserRole, *data):
        match role:
            case Qt.ItemDataRole.UserRole:
                if self.getData is None: return None
                return self.getData(*data)
            case Qt.ItemDataRole.DisplayRole:
                if self.getDisplay is None: return None
                return self.getDisplay(*data)
            case Qt.ItemDataRole.ToolTipRole:
                if self.getToolTip is None: return None
                return self.getToolTip(*data)
            case Qt.ItemDataRole.BackgroundRole:
                if self.getBackground is None: return None
                return self.getBackground(*data)
            case Qt.ItemDataRole.ForegroundRole:
                if self.getForeground is None: return None
                return self.getForeground(*data)


class TokenClass:
    """Мой класс для хранения всей информации, связанной с токеном."""
    def __init__(self, token: str, accounts: list[Account],
                 unary_limits: list[MyUnaryLimit], stream_limits: list[MyStreamLimit],
                 name: str = '', response_datetime: datetime = getUtcDateTime()):
        self.token: str = token  # Токен.
        self.name: str = name  # Название токена.
        self.accounts: list[Account] = accounts  # Список аккаунтов.
        self.unary_limits: list[MyUnaryLimit] = unary_limits  # Unary-лимиты.

        self.unary_limits_manager: UnaryLimitsManager = UnaryLimitsManager(self.unary_limits)  # Менеджер unary-лимитов.

        self.stream_limits: list[MyStreamLimit] = stream_limits  # Stream-лимиты.
        self.response_datetime: datetime = response_datetime


def reportAccountAccessLevel(access_level: AccessLevel) -> str:
    """Расшифровывает уровень доступа к текущему счёту."""
    match access_level:
        case AccessLevel.ACCOUNT_ACCESS_LEVEL_UNSPECIFIED: return 'Уровень доступа не определён.'
        case AccessLevel.ACCOUNT_ACCESS_LEVEL_FULL_ACCESS: return 'Полный доступ к счёту.'
        case AccessLevel.ACCOUNT_ACCESS_LEVEL_READ_ONLY: return 'Доступ с уровнем прав "только чтение".'
        case AccessLevel.ACCOUNT_ACCESS_LEVEL_NO_ACCESS: return 'Доступ отсутствует.'
        case _: raise ValueError('Неизвестное значение переменной класса AccessLevel ({0})!'.format(access_level))


def reportAccountType(account_type: AccountType) -> str:
    """Расшифровывает тип счёта."""
    match account_type:
        case AccountType.ACCOUNT_TYPE_UNSPECIFIED: return 'Тип аккаунта не определён.'
        case AccountType.ACCOUNT_TYPE_TINKOFF: return 'Брокерский счёт Тинькофф.'
        case AccountType.ACCOUNT_TYPE_TINKOFF_IIS: return 'ИИС счёт.'
        case AccountType.ACCOUNT_TYPE_INVEST_BOX: return 'Инвесткопилка.'
        case _: raise ValueError('Неизвестное значение переменной класса AccountType ({0})!'.format(account_type))


def reportAccountStatus(account_status: AccountStatus) -> str:
    """Расшифровывает статус счёта."""
    match account_status:
        case AccountStatus.ACCOUNT_STATUS_UNSPECIFIED: return 'Статус счёта не определён.'
        case AccountStatus.ACCOUNT_STATUS_NEW: return 'Новый, в процессе открытия.'
        case AccountStatus.ACCOUNT_STATUS_OPEN: return 'Открытый и активный счёт.'
        case AccountStatus.ACCOUNT_STATUS_CLOSED: return 'Закрытый счёт.'
        case _: raise ValueError('Неизвестное значение переменной класса AccountStatus ({0})!'.format(account_status))


def reportTradingStatus(trading_status: int) -> str:
    """Расшифровывает режим торгов инструмента."""
    match trading_status:
        case SecurityTradingStatus.SECURITY_TRADING_STATUS_UNSPECIFIED:
            return "Торговый статус не определён"
        case SecurityTradingStatus.SECURITY_TRADING_STATUS_NOT_AVAILABLE_FOR_TRADING:
            return "Недоступен для торгов"
        case SecurityTradingStatus.SECURITY_TRADING_STATUS_OPENING_PERIOD:
            return "Период открытия торгов"
        case SecurityTradingStatus.SECURITY_TRADING_STATUS_CLOSING_PERIOD:
            return "Период закрытия торгов"
        case SecurityTradingStatus.SECURITY_TRADING_STATUS_BREAK_IN_TRADING:
            return "Перерыв в торговле"
        case SecurityTradingStatus.SECURITY_TRADING_STATUS_NORMAL_TRADING:
            return "Нормальная торговля"
        case SecurityTradingStatus.SECURITY_TRADING_STATUS_CLOSING_AUCTION:
            return "Аукцион закрытия"
        case SecurityTradingStatus.SECURITY_TRADING_STATUS_DARK_POOL_AUCTION:
            return "Аукцион крупных пакетов"
        case SecurityTradingStatus.SECURITY_TRADING_STATUS_DISCRETE_AUCTION:
            return "Дискретный аукцион"
        case SecurityTradingStatus.SECURITY_TRADING_STATUS_OPENING_AUCTION_PERIOD:
            return "Аукцион открытия"
        case SecurityTradingStatus.SECURITY_TRADING_STATUS_TRADING_AT_CLOSING_AUCTION_PRICE:
            return "Период торгов по цене аукциона закрытия"
        case SecurityTradingStatus.SECURITY_TRADING_STATUS_SESSION_ASSIGNED:
            return "Сессия назначена"
        case SecurityTradingStatus.SECURITY_TRADING_STATUS_SESSION_CLOSE:
            return "Сессия закрыта"
        case SecurityTradingStatus.SECURITY_TRADING_STATUS_SESSION_OPEN:
            return "Сессия открыта"
        case SecurityTradingStatus.SECURITY_TRADING_STATUS_DEALER_NORMAL_TRADING:
            return "Доступна торговля в режиме внутренней ликвидности брокера"
        case SecurityTradingStatus.SECURITY_TRADING_STATUS_DEALER_BREAK_IN_TRADING:
            return "Перерыв торговли в режиме внутренней ликвидности брокера"
        case SecurityTradingStatus.SECURITY_TRADING_STATUS_DEALER_NOT_AVAILABLE_FOR_TRADING:
            return "Недоступна торговля в режиме внутренней ликвидности брокера"
        case _:
            raise ValueError("Некорректный режим торгов инструмента ({0})!".format(trading_status))


class MyConnection(ABC):
    """Абстрактный класс, хранящий общий функционал соединений с БД."""

    '''---------Названия таблиц БД---------'''
    BONDS_TABLE: str = 'Bonds'
    '''------------------------------------'''

    SQLITE_DRIVER: str = 'QSQLITE'
    assert QSqlDatabase.isDriverAvailable(SQLITE_DRIVER), 'Драйвер {0} недоступен!'.format(SQLITE_DRIVER)

    DATABASE_NAME: str = 'tinkoff_invest.db'
    CONNECTION_NAME: str  # "Абстрактная" переменная класса, должна быть определена в наследуемом классе.

    @staticmethod
    def _getSQLiteLimitVariableNumber(database_name: str):
        """Получает и возвращает лимит на количество переменных в одном запросе."""
        from sqlite3 import connect, Connection, SQLITE_LIMIT_VARIABLE_NUMBER
        connection = connect(database_name)  # Создаем подключение к базе данных (файл DATABASE_NAME будет создан).
        limit: int = connection.getlimit(SQLITE_LIMIT_VARIABLE_NUMBER)
        connection.close()
        return limit

    VARIABLE_LIMIT: int = _getSQLiteLimitVariableNumber(DATABASE_NAME)  # Лимит на количество переменных в одном запросе.

    @staticmethod
    def __setForeignKeysOn(db: QSqlDatabase):
        """
        Использование внешних ключей по умолчанию отключено.
        Эта функция включает использование внешних ключей для конкретного соединения.
        """
        query = QSqlQuery(db)
        prepare_flag: bool = query.prepare('PRAGMA foreign_keys = ON;')
        assert prepare_flag, query.lastError().text()
        exec_flag: bool = query.exec()
        assert exec_flag, query.lastError().text()

    @classmethod
    def open(cls):
        """Открывает соединение с базой данных."""
        db: QSqlDatabase = QSqlDatabase.addDatabase(cls.SQLITE_DRIVER, cls.CONNECTION_NAME)
        db.setDatabaseName(cls.DATABASE_NAME)
        open_flag: bool = db.open()
        assert open_flag and db.isOpen()
        cls.__setForeignKeysOn(db)  # Включаем использование внешних ключей.

    @classmethod
    def removeConnection(cls):
        """Удаляет соединение с базой данных."""
        db: QSqlDatabase = cls.getDatabase()
        db.close()  # Для удаления соединения с базой данных, надо сначала закрыть базу данных.
        db.removeDatabase(cls.CONNECTION_NAME)

    @classmethod
    def getDatabase(cls) -> QSqlDatabase:
        return QSqlDatabase.database(cls.CONNECTION_NAME)

    @staticmethod
    def convertDateTimeToText(dt: datetime, sep: str = ' ', timespec: str = 'auto') -> str:
        """Конвертирует datetime в TEXT для хранения в БД."""
        # return str(dt)
        return dt.isoformat(sep=sep, timespec=timespec)

    @staticmethod
    def convertTextToDateTime(text: str) -> datetime:
        """Конвертирует TEXT в datetime при извлечении из БД."""
        # return datetime.strptime(text, '%Y-%m-%d %H:%M:%S%z')
        return datetime.fromisoformat(text)

    @staticmethod
    def convertTextToQuotation(text: str) -> Quotation:
        """Конвертирует TEXT в Quotation при извлечении из БД."""
        units_str, nano_str = text.split('.', 1)
        units: int = int(units_str)
        nano: int = int(nano_str)
        return Quotation(units, nano)

    @staticmethod
    def convertTextToMyMoneyValue(text: str) -> MyMoneyValue:
        """Конвертирует TEXT в MyMoneyValue при извлечении из БД."""
        quotation_str, currency = text.split(' ', 1)
        quotation: Quotation = MyConnection.convertTextToQuotation(quotation_str)
        return MyMoneyValue(currency, quotation)

    @staticmethod
    def convertStrListToStr(str_list: list[str]) -> str:
        """Преобразует список строк в одну строку."""
        return ', '.join(str_list)

    @staticmethod
    def convertBoolToBlob(value: bool) -> int:
        """Преобразует значение типа bool в 1 или 0 (тип BLOB в SQLite)."""
        return 1 if value else 0

    @staticmethod
    def convertBlobToBool(value: int) -> bool:
        """Преобразует значение типа BLOB (1 или 0) в значение типа bool."""
        assert value == 0 or value == 1, 'Значение переменной типа BLOB (в SQLite) должно быть 0 или 1. Вместо этого передано {0}.'.format(value)
        return bool(value)
