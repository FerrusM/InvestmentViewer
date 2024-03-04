from abc import ABC
from datetime import datetime
from PyQt6 import QtWidgets, QtGui, QtSql, QtCore
from tinkoff.invest import Account, AccessLevel, AccountType, AccountStatus, SecurityTradingStatus, Quotation, MoneyValue, Bond, RealExchange
from tinkoff.invest.schemas import RiskLevel, Share, ShareType, Coupon, CouponType, LastPrice, Dividend, HistoricCandle, ConsensusItem, Recommendation
from LimitClasses import MyUnaryLimit, MyStreamLimit, UnaryLimitsManager
from MyMoneyValue import MyMoneyValue


TITLE_FONT = QtGui.QFont()
TITLE_FONT.setPointSize(9)
TITLE_FONT.setBold(True)


def partition(array: list, length: int) -> list[list]:
    """Разбивает список на части длиной до length элементов и возвращает полученный список списков."""
    def __splitIntoParts():
        for i in range(0, len(array), length):
            yield array[i:(i + length)]
    return list(__splitIntoParts())


@QtCore.pyqtSlot(str)
def print_slot(text: str):
    """По моим наблюдениям, функция print с добавленным декоратором pyqtSlot работает быстрее.
    Но это следует проверить."""
    print(text)


class MyTreeView(QtWidgets.QTreeView):
    def resizeColumnsToContents(self: QtWidgets.QTreeView):
        """Авторазмер всех столбцов TreeView под содержимое."""
        for i in range(self.model().columnCount()):
            self.resizeColumnToContents(i)  # Авторазмер i-го столбца под содержимое.


class Column:
    """Класс столбца."""
    def __init__(self, header: str | None = None, header_tooltip: str | None = None, data_function=None, display_function=None, tooltip_function=None,
                 background_function=None, foreground_function=None,
                 lessThan=None, sort_role: QtCore.Qt.ItemDataRole = QtCore.Qt.ItemDataRole.UserRole):
        self.header: str | None = header  # Название столбца.
        self.header_tooltip: str | None = header_tooltip  # Подсказка в заголовке.
        self.getData = data_function  # Функция для получения данных.
        self.getDisplay = data_function if display_function is None else display_function  # Функция для отображения данных.
        self.getToolTip = tooltip_function  # Функция для получения подсказки к отображаемым данным.
        self.getBackground = background_function
        self.getForeground = foreground_function

        self.getSortRole: QtCore.Qt.ItemDataRole = sort_role  # Роль элементов, используемая для сортировки столбца.
        self.lessThan = lessThan

    def __call__(self, role: int = QtCore.Qt.ItemDataRole.UserRole, *data):
        match role:
            case QtCore.Qt.ItemDataRole.UserRole:
                if self.getData is None: return None
                return self.getData(*data)
            case QtCore.Qt.ItemDataRole.DisplayRole:
                if self.getDisplay is None: return None
                return self.getDisplay(*data)
            case QtCore.Qt.ItemDataRole.ToolTipRole:
                if self.getToolTip is None: return None
                return self.getToolTip(*data)
            case QtCore.Qt.ItemDataRole.BackgroundRole:
                if self.getBackground is None: return None
                return self.getBackground(*data)
            case QtCore.Qt.ItemDataRole.ForegroundRole:
                if self.getForeground is None: return None
                return self.getForeground(*data)


class TokenClass:
    """Мой класс для хранения всей информации, связанной с токеном."""
    def __init__(self, token: str, accounts: list[Account] | None = None,
                 unary_limits: list[MyUnaryLimit] | None = None, stream_limits: list[MyStreamLimit] | None = None,
                 name: str = ''):
        self.token: str = token  # Токен.
        self.name: str = name  # Название токена.
        self.__accounts: list[Account] = [] if accounts is None else accounts  # Список аккаунтов.

        self.__unary_limits_manager: UnaryLimitsManager = UnaryLimitsManager(unary_limits)  # Менеджер unary-лимитов.

        self.__stream_limits: list[MyStreamLimit] = [] if stream_limits is None else stream_limits  # Stream-лимиты.

    @property
    def accounts(self) -> list[Account]:
        return self.__accounts

    @accounts.setter
    def accounts(self, accounts: list[Account]):
        self.__accounts = accounts

    @property
    def unary_limits(self) -> list[MyUnaryLimit]:
        return self.__unary_limits_manager.unary_limits

    @unary_limits.setter
    def unary_limits(self, unary_limits: list[MyUnaryLimit]):
        self.__unary_limits_manager.setData(unary_limits)

    @property
    def unary_limits_manager(self) -> UnaryLimitsManager:
        return self.__unary_limits_manager

    @property
    def stream_limits(self):
        return self.__stream_limits

    @stream_limits.setter
    def stream_limits(self, stream_limits: list[MyStreamLimit]):
        self.__stream_limits = stream_limits


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

    '''---------------Названия таблиц БД---------------'''
    TOKENS_TABLE: str = 'Tokens'
    ACCOUNTS_TABLE: str = 'Accounts'
    BONDS_TABLE: str = 'Bonds'
    BRANDS_TABLE: str = 'Brands'
    LAST_PRICES_TABLE: str = 'LastPrices'
    COUPONS_TABLE: str = 'Coupons'
    CANDLES_TABLE: str = 'HistoricCandles'
    SHARES_TABLE: str = 'Shares'
    DIVIDENDS_TABLE: str = 'Dividends'
    STREAM_LIMITS_TABLE: str = 'StreamLimits'
    UNARY_LIMITS_TABLE: str = 'UnaryLimits'
    INSTRUMENT_UIDS_TABLE: str = 'InstrumentUniqueIdentifiers'
    INSTRUMENT_STATUS_TABLE: str = 'InstrumentsStatus'
    TARGET_ITEMS_TABLE: str = 'TargetItems'
    CONSENSUS_ITEMS_TABLE: str = 'ConsensusItems'
    ASSETS_TABLE: str = 'Assets'
    INSTRUMENT_LINKS_TABLE: str = 'InstrumentLinks'
    ASSET_INSTRUMENTS_TABLE: str = 'AssetInstruments'
    ASSET_SECURITIES_TABLE: str = 'AssetSecurities'
    ASSET_CURRENCIES_TABLE: str = 'AssetCurrencies'
    BRANDS_DATA_TABLE: str = 'BrandsData'

    LAST_PRICES_VIEW: str = 'LastPricesView'

    ASSETS_BEFORE_UPDATE_TRIGGER: str = 'Assets_on_update_trigger'
    SHARES_TRIGGER_BEFORE_INSERT: str = 'Shares_before_insert_trigger'
    BONDS_TRIGGER_BEFORE_INSERT: str = 'Bonds_before_insert_trigger'
    CANDLES_TRIGGER_BEFORE_INSERT: str = 'Candles_before_insert_trigger'
    INSTRUMENT_UIDS_BEFORE_UPDATE_TRIGGER: str = 'InstrumentUniqueIdentifiers_before_update_trigger'
    '''------------------------------------------------'''

    SQLITE_DRIVER: str = 'QSQLITE'
    assert QtSql.QSqlDatabase.isDriverAvailable(SQLITE_DRIVER), 'Драйвер {0} недоступен!'.format(SQLITE_DRIVER)

    DATABASE_NAME: str = 'tinkoff_invest.db'
    CONNECTION_NAME: str  # "Абстрактная" переменная класса, должна быть определена в наследуемом классе.

    @staticmethod
    def _getSQLiteLimitVariableNumber(database_name: str):
        """Получает и возвращает лимит на количество переменных в одном запросе."""
        from sqlite3 import connect, Connection, SQLITE_LIMIT_VARIABLE_NUMBER
        connection: Connection = connect(database_name)  # Создаем подключение к базе данных (файл DATABASE_NAME будет создан).

        # sqlite3_update_hook()
        # connection.set

        limit: int = connection.getlimit(SQLITE_LIMIT_VARIABLE_NUMBER)
        connection.close()
        return limit

    VARIABLE_LIMIT: int = _getSQLiteLimitVariableNumber(DATABASE_NAME)  # Лимит на количество переменных в одном запросе.

    @classmethod
    def open(cls):
        """Открывает соединение с базой данных."""
        db: QtSql.QSqlDatabase = QtSql.QSqlDatabase.addDatabase(cls.SQLITE_DRIVER, cls.CONNECTION_NAME)
        db.setDatabaseName(cls.DATABASE_NAME)
        open_flag: bool = db.open()
        assert open_flag and db.isOpen()

        if db.transaction():
            '''----Включаем использование внешних ключей для соединения----'''
            """
            Использование внешних ключей по умолчанию отключено.
            Эта функция включает использование внешних ключей для конкретного соединения.
            """
            fk_query = QtSql.QSqlQuery(db)
            fk_prepare_flag: bool = fk_query.prepare('PRAGMA foreign_keys = ON;')
            assert fk_prepare_flag, fk_query.lastError().text()
            fk_exec_flag: bool = fk_query.exec()
            assert fk_exec_flag, fk_query.lastError().text()
            '''------------------------------------------------------------'''

            '''------------------Задаём тайм-аут занятости------------------'''
            bt_query = QtSql.QSqlQuery(db)
            bt_prepare_flag: bool = bt_query.prepare('PRAGMA busy_timeout = 60000;')
            assert bt_prepare_flag, bt_query.lastError().text()
            bt_exec_flag: bool = bt_query.exec()
            assert bt_exec_flag, bt_query.lastError().text()
            '''-------------------------------------------------------------'''

            commit_flag: bool = db.commit()  # Фиксирует транзакцию в базу данных.
            assert commit_flag, db.lastError().text()
        else:
            raise SystemError('Не получилось начать транзакцию! db.lastError().text(): \'{0}\'.'.format(db.lastError().text()))

    @classmethod
    def removeConnection(cls):
        """Удаляет соединение с базой данных."""
        db: QtSql.QSqlDatabase = cls.getDatabase()
        db.close()  # Для удаления соединения с базой данных, надо сначала закрыть базу данных.
        db.removeDatabase(cls.CONNECTION_NAME)

    @classmethod
    def getDatabase(cls) -> QtSql.QSqlDatabase:
        return QtSql.QSqlDatabase.database(cls.CONNECTION_NAME)

    @staticmethod
    def convertDateTimeToText(dt: datetime, sep: str = 'T', timespec: str = 'auto') -> str:
        """Конвертирует datetime в TEXT для хранения в БД."""
        return dt.isoformat(sep=sep, timespec=timespec)

    @staticmethod
    def convertTextToDateTime(text: str) -> datetime:
        """Конвертирует TEXT в datetime при извлечении из БД."""
        return datetime.fromisoformat(text)

    @staticmethod
    def extractUnitsAndNanoFromText(text: str) -> tuple[int, int]:
        """Извлекает units и nano из строки Quotation."""
        try:
            units_str, nano_str = text.split('.', 1)
        except AttributeError:
            raise AttributeError('AttributeError: text = \'{0}\'.'.format(text))
        units: int = int(units_str)
        nano: int = int(nano_str)
        return units, nano

    @staticmethod
    def convertTextToQuotation(text: str) -> Quotation:
        """Конвертирует TEXT в Quotation при извлечении из БД."""
        units, nano = MyConnection.extractUnitsAndNanoFromText(text)
        return Quotation(units, nano)

    @staticmethod
    def convertTextToMoneyValue(text: str) -> MoneyValue:
        """Конвертирует TEXT в MoneyValue при извлечении из БД."""
        quotation_str, currency = text.split(' ', 1)
        units, nano = MyConnection.extractUnitsAndNanoFromText(quotation_str)
        return MoneyValue(currency=currency, units=units, nano=nano)

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

    @staticmethod
    def convertCouponsFlagToBool(coupons_flag_str: str) -> bool:
        """Конвертирует значение поля coupons таблицы облигаций в булевый тип."""
        if coupons_flag_str:
            if coupons_flag_str == 'Yes':
                return True
            elif coupons_flag_str == 'No':
                return False
            else:
                raise ValueError('Некорректное значение флага наличия купонов ({0})!'.format(coupons_flag_str))
        else:
            return False

    @staticmethod
    def convertDividendsFlagToBool(dividends_flag_str: str) -> bool:
        """Конвертирует значение поля dividends таблицы акций в булевый тип."""
        if dividends_flag_str:
            if dividends_flag_str == 'Yes':
                return True
            elif dividends_flag_str == 'No':
                return False
            else:
                raise ValueError('Некорректное значение флага наличия дивидендов ({0})!'.format(dividends_flag_str))
        else:
            return False

    @classmethod
    def getCurrentShare(cls, query: QtSql.QSqlQuery) -> Share:
        """Создаёт и возвращает экземпляр класса Bond."""
        figi: str = query.value('figi')
        ticker: str = query.value('ticker')
        class_code: str = query.value('class_code')
        isin: str = query.value('isin')
        lot: int = query.value('lot')
        currency: str = query.value('currency')
        klong: Quotation = cls.convertTextToQuotation(query.value('klong'))
        kshort: Quotation = cls.convertTextToQuotation(query.value('kshort'))
        dlong: Quotation = cls.convertTextToQuotation(query.value('dlong'))
        dshort: Quotation = cls.convertTextToQuotation(query.value('dshort'))
        dlong_min: Quotation = cls.convertTextToQuotation(query.value('dlong_min'))
        dshort_min: Quotation = cls.convertTextToQuotation(query.value('dshort_min'))
        short_enabled_flag: bool = bool(query.value('short_enabled_flag'))
        name: str = query.value('name')
        exchange: str = query.value('exchange')
        ipo_date: datetime = cls.convertTextToDateTime(query.value('ipo_date'))
        issue_size: int = query.value('issue_size')
        country_of_risk: str = query.value('country_of_risk')
        country_of_risk_name: str = query.value('country_of_risk_name')
        sector: str = query.value('sector')
        issue_size_plan: int = query.value('issue_size_plan')
        nominal: MoneyValue = cls.convertTextToMoneyValue(query.value('nominal'))
        trading_status: SecurityTradingStatus = SecurityTradingStatus.from_string(query.value('trading_status'))
        otc_flag: bool = bool(query.value('otc_flag'))
        buy_available_flag: bool = bool(query.value('buy_available_flag'))
        sell_available_flag: bool = bool(query.value('sell_available_flag'))
        div_yield_flag: bool = bool(query.value('div_yield_flag'))
        share_type: ShareType = ShareType.from_string(query.value('share_type'))
        min_price_increment: Quotation = cls.convertTextToQuotation(query.value('min_price_increment'))
        api_trade_available_flag: bool = bool(query.value('api_trade_available_flag'))
        uid: str = query.value('uid')
        real_exchange: RealExchange = RealExchange.from_string(query.value('real_exchange'))
        position_uid: str = query.value('position_uid')
        asset_uid: str = query.value('asset_uid')
        for_iis_flag: bool = bool(query.value('for_iis_flag'))
        for_qual_investor_flag: bool = bool(query.value('for_qual_investor_flag'))
        weekend_flag: bool = bool(query.value('weekend_flag'))
        blocked_tca_flag: bool = bool(query.value('blocked_tca_flag'))
        liquidity_flag: bool = bool(query.value('liquidity_flag'))
        first_1min_candle_date: datetime = cls.convertTextToDateTime(query.value('first_1min_candle_date'))
        first_1day_candle_date: datetime = cls.convertTextToDateTime(query.value('first_1day_candle_date'))
        return Share(figi=figi, ticker=ticker, class_code=class_code, isin=isin, lot=lot, currency=currency,
                     klong=klong, kshort=kshort, dlong=dlong, dshort=dshort, dlong_min=dlong_min, dshort_min=dshort_min,
                     short_enabled_flag=short_enabled_flag, name=name, exchange=exchange, ipo_date=ipo_date,
                     issue_size=issue_size, country_of_risk=country_of_risk, country_of_risk_name=country_of_risk_name,
                     sector=sector, issue_size_plan=issue_size_plan, nominal=nominal, trading_status=trading_status,
                     otc_flag=otc_flag, buy_available_flag=buy_available_flag, sell_available_flag=sell_available_flag,
                     div_yield_flag=div_yield_flag, share_type=share_type, min_price_increment=min_price_increment,
                     api_trade_available_flag=api_trade_available_flag, uid=uid, real_exchange=real_exchange,
                     position_uid=position_uid, asset_uid=asset_uid, for_iis_flag=for_iis_flag,
                     for_qual_investor_flag=for_qual_investor_flag, weekend_flag=weekend_flag,
                     blocked_tca_flag=blocked_tca_flag, liquidity_flag=liquidity_flag,
                     first_1min_candle_date=first_1min_candle_date, first_1day_candle_date=first_1day_candle_date)

    @classmethod
    def getCurrentBond(cls, query: QtSql.QSqlQuery) -> Bond:
        """Создаёт и возвращает экземпляр класса Bond."""
        figi: str = query.value('figi')
        ticker: str = query.value('ticker')
        class_code: str = query.value('class_code')
        isin: str = query.value('isin')
        lot: int = query.value('lot')
        currency: str = query.value('currency')
        klong: Quotation = cls.convertTextToQuotation(query.value('klong'))
        kshort: Quotation = cls.convertTextToQuotation(query.value('kshort'))
        dlong: Quotation = cls.convertTextToQuotation(query.value('dlong'))
        dshort: Quotation = cls.convertTextToQuotation(query.value('dshort'))
        dlong_min: Quotation = cls.convertTextToQuotation(query.value('dlong_min'))
        dshort_min: Quotation = cls.convertTextToQuotation(query.value('dshort_min'))
        short_enabled_flag: bool = bool(query.value('short_enabled_flag'))
        name: str = query.value('name')
        exchange: str = query.value('exchange')
        coupon_quantity_per_year: int = query.value('coupon_quantity_per_year')
        maturity_date: datetime = cls.convertTextToDateTime(query.value('maturity_date'))
        nominal: MoneyValue = cls.convertTextToMoneyValue(query.value('nominal'))
        initial_nominal: MoneyValue = cls.convertTextToMoneyValue(query.value('initial_nominal'))
        state_reg_date: datetime = cls.convertTextToDateTime(query.value('state_reg_date'))
        placement_date: datetime = cls.convertTextToDateTime(query.value('placement_date'))
        placement_price: MoneyValue = cls.convertTextToMoneyValue(query.value('placement_price'))
        aci_value: MoneyValue = cls.convertTextToMoneyValue(query.value('aci_value'))
        country_of_risk: str = query.value('country_of_risk')
        country_of_risk_name: str = query.value('country_of_risk_name')
        sector: str = query.value('sector')
        issue_kind: str = query.value('issue_kind')
        issue_size: int = query.value('issue_size')
        issue_size_plan: int = query.value('issue_size_plan')
        trading_status: SecurityTradingStatus = SecurityTradingStatus.from_string(query.value('trading_status'))
        otc_flag: bool = bool(query.value('otc_flag'))
        buy_available_flag: bool = bool(query.value('buy_available_flag'))
        sell_available_flag: bool = bool(query.value('sell_available_flag'))
        floating_coupon_flag: bool = bool(query.value('floating_coupon_flag'))
        perpetual_flag: bool = bool(query.value('perpetual_flag'))
        amortization_flag: bool = bool(query.value('amortization_flag'))
        min_price_increment: Quotation = cls.convertTextToQuotation(query.value('min_price_increment'))
        api_trade_available_flag: bool = bool(query.value('api_trade_available_flag'))
        uid: str = query.value('uid')
        real_exchange: RealExchange = RealExchange.from_string(query.value('real_exchange'))
        position_uid: str = query.value('position_uid')
        asset_uid: str = query.value('asset_uid')
        for_iis_flag: bool = bool(query.value('for_iis_flag'))
        for_qual_investor_flag: bool = bool(query.value('for_qual_investor_flag'))
        weekend_flag: bool = bool(query.value('weekend_flag'))
        blocked_tca_flag: bool = bool(query.value('blocked_tca_flag'))
        subordinated_flag: bool = bool(query.value('subordinated_flag'))
        liquidity_flag: bool = bool(query.value('liquidity_flag'))
        first_1min_candle_date: datetime = cls.convertTextToDateTime(query.value('first_1min_candle_date'))
        first_1day_candle_date: datetime = cls.convertTextToDateTime(query.value('first_1day_candle_date'))
        risk_level: RiskLevel = RiskLevel.from_string(query.value('risk_level'))
        return Bond(figi=figi, ticker=ticker, class_code=class_code, isin=isin, lot=lot, currency=currency, klong=klong,
                    kshort=kshort, dlong=dlong, dshort=dshort, dlong_min=dlong_min, dshort_min=dshort_min,
                    short_enabled_flag=short_enabled_flag, name=name, exchange=exchange,
                    coupon_quantity_per_year=coupon_quantity_per_year, maturity_date=maturity_date,
                    nominal=nominal, initial_nominal=initial_nominal, state_reg_date=state_reg_date,
                    placement_date=placement_date, placement_price=placement_price, aci_value=aci_value,
                    country_of_risk=country_of_risk, country_of_risk_name=country_of_risk_name, sector=sector,
                    issue_kind=issue_kind, issue_size=issue_size, issue_size_plan=issue_size_plan,
                    trading_status=trading_status, otc_flag=otc_flag, buy_available_flag=buy_available_flag,
                    sell_available_flag=sell_available_flag, floating_coupon_flag=floating_coupon_flag,
                    perpetual_flag=perpetual_flag, amortization_flag=amortization_flag,
                    min_price_increment=min_price_increment, api_trade_available_flag=api_trade_available_flag, uid=uid,
                    real_exchange=real_exchange, position_uid=position_uid, asset_uid=asset_uid,
                    for_iis_flag=for_iis_flag, for_qual_investor_flag=for_qual_investor_flag, weekend_flag=weekend_flag,
                    blocked_tca_flag=blocked_tca_flag, subordinated_flag=subordinated_flag,
                    liquidity_flag=liquidity_flag, first_1min_candle_date=first_1min_candle_date,
                    first_1day_candle_date=first_1day_candle_date, risk_level=risk_level)

    @classmethod
    def getCurrentCoupon(cls, coupons_query: QtSql.QSqlQuery) -> Coupon:
        figi: str = coupons_query.value('figi')
        coupon_date: datetime = cls.convertTextToDateTime(coupons_query.value('coupon_date'))
        coupon_number: int = coupons_query.value('coupon_number')
        fix_date: datetime = cls.convertTextToDateTime(coupons_query.value('fix_date'))
        pay_one_bond: MoneyValue = cls.convertTextToMoneyValue(coupons_query.value('pay_one_bond'))
        coupon_type: CouponType = CouponType.from_string(coupons_query.value('coupon_type'))
        coupon_start_date: datetime = cls.convertTextToDateTime(coupons_query.value('coupon_start_date'))
        coupon_end_date: datetime = cls.convertTextToDateTime(coupons_query.value('coupon_end_date'))
        coupon_period: int = coupons_query.value('coupon_period')
        return Coupon(figi=figi, coupon_date=coupon_date, coupon_number=coupon_number, fix_date=fix_date,
                      pay_one_bond=pay_one_bond, coupon_type=coupon_type, coupon_start_date=coupon_start_date,
                      coupon_end_date=coupon_end_date, coupon_period=coupon_period)

    @classmethod
    def getCurrentDividend(cls, dividends_query: QtSql.QSqlQuery) -> Dividend:
        dividend_net: MoneyValue = cls.convertTextToMoneyValue(dividends_query.value('dividend_net'))
        payment_date: datetime = cls.convertTextToDateTime(dividends_query.value('payment_date'))
        declared_date: datetime = cls.convertTextToDateTime(dividends_query.value('declared_date'))
        last_buy_date: datetime = cls.convertTextToDateTime(dividends_query.value('last_buy_date'))
        dividend_type: str = dividends_query.value('dividend_type')
        record_date: datetime = cls.convertTextToDateTime(dividends_query.value('record_date'))
        regularity: str = dividends_query.value('regularity')
        close_price: MoneyValue = cls.convertTextToMoneyValue(dividends_query.value('close_price'))
        yield_value: Quotation = cls.convertTextToQuotation(dividends_query.value('yield_value'))
        created_at: datetime = cls.convertTextToDateTime(dividends_query.value('created_at'))
        return Dividend(dividend_net=dividend_net, payment_date=payment_date, declared_date=declared_date,
                        last_buy_date=last_buy_date, dividend_type=dividend_type, record_date=record_date,
                        regularity=regularity, close_price=close_price, yield_value=yield_value, created_at=created_at)

    @classmethod
    def getLastPrice(cls, db: QtSql.QSqlDatabase, instrument_uid: str) -> LastPrice | None:
        last_price_sql_command: str = 'SELECT \"figi\", \"price\", \"time\" FROM \"{0}\" WHERE \"instrument_uid\" = :instrument_uid;'.format(cls.LAST_PRICES_VIEW)

        last_price_query = QtSql.QSqlQuery(db)
        last_price_query.setForwardOnly(True)  # Возможно, это ускоряет извлечение данных.
        last_price_prepare_flag: bool = last_price_query.prepare(last_price_sql_command)
        assert last_price_prepare_flag, last_price_query.lastError().text()
        last_price_query.bindValue(':instrument_uid', instrument_uid)
        last_price_exec_flag: bool = last_price_query.exec()
        assert last_price_exec_flag, last_price_query.lastError().text()

        last_price_rows_count: int = 0
        last_price: LastPrice | None = None
        while last_price_query.next():
            last_price_rows_count += 1
            assert last_price_rows_count < 2, 'Не должно быть нескольких строк с одним и тем же instrument_uid (\'{0}\')!'.format(instrument_uid)
            figi: str = last_price_query.value('figi')
            price_str: str = last_price_query.value('price')
            time_str: str = last_price_query.value('time')
            price: Quotation = cls.convertTextToQuotation(price_str)
            time: datetime = cls.convertTextToDateTime(time_str)
            last_price = LastPrice(figi=figi, price=price, time=time, instrument_uid=instrument_uid)
        return last_price

    @classmethod
    def getCurrentAccount(cls, query: QtSql.QSqlQuery) -> Account:
        return Account(
            id=query.value('id'),
            type=AccountType.from_string(query.value('type')),
            name=query.value('name'),
            status=AccountStatus.from_string(query.value('status')),
            opened_date=cls.convertTextToDateTime(query.value('opened_date')),
            closed_date=cls.convertTextToDateTime(query.value('closed_date')),
            access_level=AccessLevel.from_string(query.value('access_level'))
        )

    @classmethod
    def getHistoricCandle(cls, query: QtSql.QSqlQuery) -> HistoricCandle:
        """Создаёт и возвращает экземпляр класса HistoricCandle."""
        open_: Quotation = cls.convertTextToQuotation(query.value('open'))
        high: Quotation = cls.convertTextToQuotation(query.value('high'))
        low: Quotation = cls.convertTextToQuotation(query.value('low'))
        close: Quotation = cls.convertTextToQuotation(query.value('close'))
        volume: int = query.value('volume')
        time: datetime = cls.convertTextToDateTime(query.value('time'))
        is_complete: bool = cls.convertBlobToBool(query.value('is_complete'))
        return HistoricCandle(open=open_, high=high, low=low, close=close, volume=volume, time=time, is_complete=is_complete)

    @classmethod
    def getConsensusItem(cls, query: QtSql.QSqlQuery) -> ConsensusItem:
        """Создаёт и возвращает экземпляр класса ConsensusItem."""
        uid: str = query.value('uid')
        ticker: str = query.value('ticker')
        recommendation: Recommendation = Recommendation.from_string(query.value('recommendation'))
        currency: str = query.value('currency')
        current_price: Quotation = cls.convertTextToQuotation(query.value('current_price'))
        consensus: Quotation = cls.convertTextToQuotation(query.value('consensus'))
        min_target: Quotation = cls.convertTextToQuotation(query.value('min_target'))
        max_target: Quotation = cls.convertTextToQuotation(query.value('max_target'))
        price_change: Quotation = cls.convertTextToQuotation(query.value('price_change'))
        price_change_rel: Quotation = cls.convertTextToQuotation(query.value('price_change_rel'))
        return ConsensusItem(uid=uid, ticker=ticker, recommendation=recommendation, currency=currency,
                             current_price=current_price, consensus=consensus, min_target=min_target,
                             max_target=max_target, price_change=price_change, price_change_rel=price_change_rel)
