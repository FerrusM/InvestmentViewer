from datetime import datetime
from PyQt6.QtSql import QSqlDatabase, QSqlQuery
from Classes import TokenClass


class MyDatabase(QSqlDatabase):
    def __init__(self):
        super().__init__('QSQLITE')
        self.setDatabaseName('tinkoff_invest.db')
        open_flag: bool = self.open()
        assert open_flag and self.isOpen()

        '''------------Создание таблицы токенов------------'''
        query = QSqlQuery(self)
        query.prepare('''
        CREATE TABLE IF NOT EXISTS Tokens (
        token TEXT PRIMARY KEY,
        name TEXT
        )
        ''')
        exec_flag: bool = query.exec()
        assert exec_flag
        assert exec_flag, query.lastError().text()
        '''------------------------------------------------'''

        '''------------Создание таблиц лимитов------------'''
        unary_limits_query = QSqlQuery(self)
        unary_limits_query.prepare('''
        CREATE TABLE IF NOT EXISTS UnaryLimits (
        token TEXT,
        limit_per_minute INTEGER,
        methods TEXT,
        FOREIGN KEY (token) REFERENCES Tokens(token)
        )
        ''')
        exec_flag: bool = unary_limits_query.exec()
        assert exec_flag, unary_limits_query.lastError().text()

        query = QSqlQuery(self)
        query.prepare('''
        CREATE TABLE IF NOT EXISTS StreamLimits (
        token TEXT,
        limit_count INTEGER,
        streams TEXT,
        open INTEGER,
        FOREIGN KEY (token) REFERENCES Tokens(token)
        )
        ''')
        exec_flag: bool = query.exec()
        assert exec_flag, query.lastError().text()
        '''-----------------------------------------------'''

        '''------------------Создание таблицы счетов------------------'''
        query = QSqlQuery(self)
        query.prepare('''
        CREATE TABLE IF NOT EXISTS Accounts (
        token TEXT,
        id TEXT,
        type INTEGER,
        name TEXT,
        status INTEGER,
        opened_date TEXT,
        closed_date TEXT,
        access_level INTEGER,
        PRIMARY KEY (token, id),
        FOREIGN KEY (token) REFERENCES Tokens(token)
        )
        ''')
        exec_flag: bool = query.exec()
        assert exec_flag, query.lastError().text()
        '''-----------------------------------------------------------'''

        '''------------Триггер перед удалением токена------------'''
        tokens_on_delete_trigger_query = QSqlQuery(self)
        tokens_on_delete_trigger_query.prepare('''
        CREATE TRIGGER IF NOT EXISTS Tokens_on_delete_trigger BEFORE DELETE
        ON Tokens
        BEGIN
            DELETE FROM UnaryLimits WHERE token = OLD.token;
            DELETE FROM StreamLimits WHERE token = OLD.token;
            DELETE FROM Accounts WHERE token = OLD.token;
        END;
        ''')
        tokens_on_delete_trigger_exec_flag: bool = tokens_on_delete_trigger_query.exec()
        assert tokens_on_delete_trigger_exec_flag, tokens_on_delete_trigger_query.lastError().text()
        '''------------------------------------------------------'''

        '''------------------Создание таблицы облигаций------------------'''
        query = QSqlQuery(self)
        query.prepare('''
        CREATE TABLE IF NOT EXISTS Bonds (
        figi TEXT,
        ticker TEXT,
        class_code TEXT,
        isin TEXT,
        lot INTEGER,
        currency TEXT,
        klong,
        kshort,
        dlong,
        dshort,
        dlong_min,
        dshort_min,
        short_enabled_flag BOOL,
        name TEXT,
        exchange TEXT,
        coupon_quantity_per_year INTEGER,
        maturity_date TEXT,
        nominal,
        initial_nominal,
        state_reg_date TEXT,
        placement_date TEXT,
        placement_price,
        aci_value,
        country_of_risk TEXT,
        country_of_risk_name TEXT,
        sector TEXT,
        issue_kind TEXT,
        issue_size INTEGER,
        issue_size_plan INTEGER,
        trading_status INTEGER,
        otc_flag BOOL,
        buy_available_flag BOOL,
        sell_available_flag BOOL,
        floating_coupon_flag BOOL,
        perpetual_flag BOOL,
        amortization_flag BOOL,
        min_price_increment,
        api_trade_available_flag BOOL,
        uid TEXT,
        real_exchange INTEGER,
        position_uid TEXT,
        for_iis_flag BOOL,
        for_qual_investor_flag BOOL,
        weekend_flag BOOL,
        blocked_tca_flag BOOL,
        subordinated_flag BOOL,
        liquidity_flag BOOL,
        first_1min_candle_date TEXT,
        first_1day_candle_date TEXT,
        risk_level INTEGER
        )
        ''')
        exec_flag: bool = query.exec()
        assert exec_flag, query.lastError().text()
        '''--------------------------------------------------------------'''

        '''--------------------Создание таблицы акций--------------------'''
        query = QSqlQuery(self)
        query.prepare('''
        CREATE TABLE IF NOT EXISTS Shares (
        figi TEXT,
        ticker TEXT,
        class_code TEXT,
        isin TEXT,
        lot INTEGER,
        currency TEXT,
        klong,
        kshort,
        dlong,
        dshort,
        dlong_min,
        dshort_min,
        short_enabled_flag BOOL,
        name TEXT,
        exchange TEXT, 
        ipo_date TEXT,
        issue_size INTEGER,
        country_of_risk TEXT,
        country_of_risk_name TEXT,
        sector TEXT,
        issue_size_plan INTEGER,
        nominal,
        trading_status INTEGER,
        otc_flag BOOL,
        buy_available_flag BOOL,
        sell_available_flag BOOL,
        div_yield_flag BOOL,
        share_type INTEGER,
        min_price_increment,
        api_trade_available_flag BOOL,
        uid TEXT,
        real_exchange INTEGER,
        position_uid TEXT,
        for_iis_flag BOOL,
        for_qual_investor_flag BOOL,
        weekend_flag BOOL,
        blocked_tca_flag BOOL,
        liquidity_flag BOOL,
        first_1min_candle_date TEXT,
        first_1day_candle_date TEXT
        )
        ''')
        exec_flag: bool = query.exec()
        assert exec_flag, query.lastError().text()
        '''--------------------------------------------------------------'''

    @staticmethod  # Преобразует метод класса в статический метод этого класса.
    def convertDateTimeToText(dt: datetime) -> str:
        """Конвертирует datetime в TEXT для хранения в БД."""
        print('\nconvertDateTimeToText __str__: {0}'.format(dt.__str__()))
        print('convertDateTimeToText __repr__: {0}'.format(dt.__repr__()))
        return str(dt)

    @staticmethod  # Преобразует метод класса в статический метод этого класса.
    def convertTextToDateTime(text: str) -> datetime:
        """Конвертирует TEXT в datetime при извлечении из БД."""
        dt: datetime = datetime.strptime(text, '%Y-%m-%d %H:%M:%S%z')
        print('\nconvertTextToDateTime __str__: {0}'.format(dt.__str__()))
        print('convertTextToDateTime __repr__: {0}'.format(dt.__repr__()))
        return datetime.strptime(text, '%Y-%m-%d %H:%M:%S%z')

    def addNewToken(self, token: TokenClass):
        """Добавляет новый токен в таблицу токенов."""
        query = QSqlQuery(self)
        query.prepare('INSERT INTO Tokens (token, name) VALUES (:token, :name)')
        query.bindValue(':token', token.token)
        query.bindValue(':name', token.name)
        exec_flag: bool = query.exec()
        assert exec_flag, query.lastError().text()

        for unary_limit in token.unary_limits:
            query = QSqlQuery(self)
            query.prepare('''
            INSERT INTO UnaryLimits (token, limit_per_minute, methods) 
            VALUES (:token, :limit_per_minute, :methods)
            ''')
            query.bindValue(':token', token.token)
            query.bindValue(':limit_per_minute', unary_limit.limit_per_minute)
            query.bindValue(':methods', ', '.join([method.full_method for method in unary_limit.methods]))
            exec_flag: bool = query.exec()
            assert exec_flag, query.lastError().text()

        for stream_limit in token.stream_limits:
            query = QSqlQuery(self)
            query.prepare('''
            INSERT INTO StreamLimits (token, limit_count, streams, open) 
            VALUES (:token, :limit_count, :streams, :open)
            ''')
            query.bindValue(':token', token.token)
            query.bindValue(':limit_count', stream_limit.limit)
            query.bindValue(':streams', ', '.join([method.full_method for method in stream_limit.methods]))
            query.bindValue(':open', stream_limit.open)
            exec_flag: bool = query.exec()
            assert exec_flag, query.lastError().text()

        for account in token.accounts:
            query = QSqlQuery(self)
            query.prepare('''
            INSERT INTO Accounts (token, id, type, name, status, opened_date, closed_date, access_level)
            VALUES (:token, :id, :type, :name, :status, :opened_date, :closed_date, :access_level)
            ''')
            query.bindValue(':token', token.token)
            query.bindValue(':id', account.id)
            query.bindValue(':type', int(account.type))
            query.bindValue(':name', account.name)
            query.bindValue(':status', int(account.status))
            query.bindValue(':opened_date', MyDatabase.convertDateTimeToText(account.opened_date))
            query.bindValue(':closed_date', MyDatabase.convertDateTimeToText(account.closed_date))
            query.bindValue(':access_level', int(account.access_level))
            exec_flag: bool = query.exec()
            assert exec_flag, query.lastError().text()

    def deleteToken(self, token: str):
        """Удаляет токен и все связанные с ним данные."""
        query = QSqlQuery(self)
        query.prepare('DELETE FROM Tokens WHERE token = :token')
        query.bindValue(':token', token)
        exec_flag: bool = query.exec()
        assert exec_flag, query.lastError().text()
