from sqlite3 import connect, Connection, SQLITE_LIMIT_VARIABLE_NUMBER
from datetime import datetime
from PyQt6.QtSql import QSqlDatabase, QSqlQuery, QSqlDriver
from tinkoff.invest import Bond, Coupon
from Classes import TokenClass
from MyMoneyValue import MyMoneyValue
from MyQuotation import MyQuotation


class MyDatabase:
    DATABASE_NAME: str = 'tinkoff_invest.db'
    SQLITE_DRIVER: str = 'QSQLITE'
    CONNECTION_NAME: str = 'InvestmentViewer'

    def __init__(self):
        """"""
        '''-------------------------------------------------'''
        # Создаем подключение к базе данных (файл my_database.db будет создан)
        connection = connect(self.DATABASE_NAME)
        self.limit = connection.getlimit(SQLITE_LIMIT_VARIABLE_NUMBER)
        connection.close()
        '''-------------------------------------------------'''

        assert QSqlDatabase.isDriverAvailable(self.SQLITE_DRIVER), 'Драйвер {0} недоступен!'.format(self.SQLITE_DRIVER)

        """---------Открываем соединение с базой данных---------"""
        db: QSqlDatabase = QSqlDatabase.addDatabase(self.SQLITE_DRIVER, self.CONNECTION_NAME)
        db.setDatabaseName(self.DATABASE_NAME)
        open_flag: bool = db.open()
        assert open_flag and db.isOpen()
        """-----------------------------------------------------"""

        self.createDataBase()  # Создаёт базу данных.

        def notificationSlot(name: str, source: QSqlDriver.NotificationSource, payload):
            match name:
                case 'Bonds':
                    print('notificationSlot: name = Bonds, source = {0}, payload = {1}'.format(source, payload))
                case _:
                    print('notificationSlot: name = {0}, source = {1}, payload = {2}'.format(name, source, payload))
                    assert False, 'Неверный параметр name ({0}).'.format(name)

        driver = db.driver()
        driver.subscribeToNotification('Bonds')
        driver.notification.connect(notificationSlot)

    @classmethod  # Привязывает метод к классу, а не к конкретному экземпляру этого класса.
    def getDatabase(cls) -> QSqlDatabase:
        return QSqlDatabase.database(cls.CONNECTION_NAME)

    @classmethod  # Привязывает метод к классу, а не к конкретному экземпляру этого класса.
    def createDataBase(cls):
        """Создаёт базу данных."""
        db: QSqlDatabase = cls.getDatabase()
        transaction_flag: bool = db.transaction()  # Начинает транзакцию в базе данных.
        assert transaction_flag

        if transaction_flag:
            '''------------Создание таблицы токенов------------'''
            query = QSqlQuery(db)
            query.prepare('''
            CREATE TABLE IF NOT EXISTS Tokens (
            token TEXT PRIMARY KEY,
            name TEXT
            )''')
            exec_flag: bool = query.exec()
            assert exec_flag
            assert exec_flag, query.lastError().text()
            '''------------------------------------------------'''

            '''------------Создание таблиц лимитов------------'''
            unary_limits_query = QSqlQuery(db)
            unary_limits_query.prepare('''
            CREATE TABLE IF NOT EXISTS UnaryLimits (
            token TEXT,
            limit_per_minute INTEGER,
            methods TEXT,
            FOREIGN KEY (token) REFERENCES Tokens(token)
            )''')
            exec_flag: bool = unary_limits_query.exec()
            assert exec_flag, unary_limits_query.lastError().text()

            query = QSqlQuery(db)
            query.prepare('''
            CREATE TABLE IF NOT EXISTS StreamLimits (
            token TEXT,
            limit_count INTEGER,
            streams TEXT,
            open INTEGER,
            FOREIGN KEY (token) REFERENCES Tokens(token)
            )''')
            exec_flag: bool = query.exec()
            assert exec_flag, query.lastError().text()
            '''-----------------------------------------------'''

            '''------------------Создание таблицы счетов------------------'''
            query = QSqlQuery(db)
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
            )''')
            exec_flag: bool = query.exec()
            assert exec_flag, query.lastError().text()
            '''-----------------------------------------------------------'''

            '''------------Триггер перед удалением токена------------'''
            tokens_on_delete_trigger_query = QSqlQuery(db)
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
            query = QSqlQuery(db)
            query.prepare('''
            CREATE TABLE IF NOT EXISTS Bonds (
            figi TEXT,
            ticker TEXT,
            class_code TEXT,
            isin TEXT,
            lot INTEGER,
            currency TEXT,
            klong TEXT,
            kshort TEXT,
            dlong TEXT,
            dshort TEXT,
            dlong_min TEXT,
            dshort_min TEXT,
            short_enabled_flag BOOL,
            name TEXT,
            exchange TEXT,
            coupon_quantity_per_year INTEGER,
            maturity_date TEXT,
            nominal TEXT,
            initial_nominal TEXT,
            state_reg_date TEXT,
            placement_date TEXT,
            placement_price TEXT,
            aci_value TEXT,
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
            min_price_increment TEXT,
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
            risk_level INTEGER,
            coupons TEXT
            )''')
            exec_flag: bool = query.exec()
            assert exec_flag, query.lastError().text()
            '''--------------------------------------------------------------'''

            '''-------------------Создание таблицы купонов-------------------'''
            query = QSqlQuery(db)
            query.prepare('''
            CREATE TABLE IF NOT EXISTS Coupons (
            figi TEXT,
            coupon_date TEXT,
            coupon_number INTEGER,
            fix_date TEXT,
            pay_one_bond TEXT,
            coupon_type INTEGER,
            coupon_start_date TEXT,
            coupon_end_date TEXT,
            coupon_period INTEGER,
            PRIMARY KEY (figi, coupon_number),
            FOREIGN KEY (figi) REFERENCES Bonds(figi)
            )''')
            exec_flag: bool = query.exec()
            assert exec_flag, query.lastError().text()
            '''--------------------------------------------------------------'''

            '''---------------Триггер перед удалением облигации---------------'''
            bonds_on_delete_trigger_query = QSqlQuery(db)
            bonds_on_delete_trigger_query.prepare('''
            CREATE TRIGGER IF NOT EXISTS Bonds_on_delete_trigger BEFORE DELETE
            ON Bonds
            BEGIN
                DELETE FROM Coupons WHERE figi = OLD.figi;
            END;
            ''')
            bonds_on_delete_trigger_exec_flag: bool = bonds_on_delete_trigger_query.exec()
            assert bonds_on_delete_trigger_exec_flag, bonds_on_delete_trigger_query.lastError().text()
            '''---------------------------------------------------------------'''

            '''----------------Триггер перед удалением купона----------------'''
            # coupons_on_delete_trigger_query = QSqlQuery(db)
            # coupons_on_delete_trigger_query.prepare('''
            # CREATE TRIGGER IF NOT EXISTS Coupons_on_delete_trigger AFTER DELETE
            # ON Coupons
            # BEGIN
            #     UPDATE Bonds SET coupons = :coupons WHERE figi = :coupon_figi;
            # END;
            # ''')
            # coupons_on_delete_trigger_exec_flag: bool = coupons_on_delete_trigger_query.exec()
            # assert coupons_on_delete_trigger_exec_flag, coupons_on_delete_trigger_query.lastError().text()
            '''--------------------------------------------------------------'''

            '''--------------------Создание таблицы акций--------------------'''
            query = QSqlQuery(db)
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
            )''')
            exec_flag: bool = query.exec()
            assert exec_flag, query.lastError().text()
            '''--------------------------------------------------------------'''

            commit_flag: bool = db.commit()  # Фиксирует транзакцию в базу данных.
            assert commit_flag

    @staticmethod  # Преобразует метод класса в статический метод этого класса.
    def convertDateTimeToText(dt: datetime) -> str:
        """Конвертирует datetime в TEXT для хранения в БД."""
        # print('\nconvertDateTimeToText __str__: {0}'.format(dt.__str__()))
        # print('convertDateTimeToText __repr__: {0}'.format(dt.__repr__()))
        return str(dt)

    @staticmethod  # Преобразует метод класса в статический метод этого класса.
    def convertTextToDateTime(text: str) -> datetime:
        """Конвертирует TEXT в datetime при извлечении из БД."""
        # dt: datetime = datetime.strptime(text, '%Y-%m-%d %H:%M:%S%z')
        # print('\nconvertTextToDateTime __str__: {0}'.format(dt.__str__()))
        # print('convertTextToDateTime __repr__: {0}'.format(dt.__repr__()))
        return datetime.strptime(text, '%Y-%m-%d %H:%M:%S%z')

    @classmethod  # Привязывает метод к классу, а не к конкретному экземпляру этого класса.
    def addNewToken(cls, token: TokenClass):
        """Добавляет новый токен в таблицу токенов."""
        db: QSqlDatabase = cls.getDatabase()

        transaction_flag: bool = db.transaction()  # Начинает транзакцию в базе данных.
        assert transaction_flag

        if transaction_flag:
            query = QSqlQuery(db)
            query.prepare('INSERT INTO Tokens (token, name) VALUES (:token, :name)')
            query.bindValue(':token', token.token)
            query.bindValue(':name', token.name)
            exec_flag: bool = query.exec()
            assert exec_flag, query.lastError().text()

            for unary_limit in token.unary_limits:
                query = QSqlQuery(db)
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
                query = QSqlQuery(db)
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
                query = QSqlQuery(db)
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

            commit_flag: bool = db.commit()  # Фиксирует транзакцию в базу данных.
            assert commit_flag

    @classmethod  # Привязывает метод к классу, а не к конкретному экземпляру этого класса.
    def deleteToken(cls, token: str):
        """Удаляет токен и все связанные с ним данные."""
        db: QSqlDatabase = cls.getDatabase()
        query = QSqlQuery(db)
        query.prepare('DELETE FROM Tokens WHERE token = :token')
        query.bindValue(':token', token)
        exec_flag: bool = query.exec()
        assert exec_flag, query.lastError().text()

    def addBonds(self, bonds: list[Bond]):
        """Добавляет облигации в таблицу облигаций."""
        if bonds:  # Если список облигаций не пуст.
            VARIABLES_COUNT: int = 50  # Количество variables в каждом insert.
            bonds_in_pack: int = int(self.limit / VARIABLES_COUNT)
            assert bonds_in_pack > 0

            def partition(array: list, length=bonds_in_pack):
                for j in range(0, len(array), length):
                    yield array[j:(j + length)]

            db: QSqlDatabase = self.getDatabase()
            print('addBonds: имя: {0}, open: {1}'.format(db.databaseName(), db.isOpen()))
            transaction_flag: bool = db.transaction()  # Начинает транзакцию в базе данных.
            assert transaction_flag

            if transaction_flag:
                bonds_packs: list[list[Bond]] = list(partition(bonds))
                for pack in bonds_packs:
                    query = QSqlQuery(db)
                    sql_command: str = 'INSERT INTO Bonds (' \
                                       'figi, ticker, class_code, isin, lot, currency, klong, kshort, dlong, dshort, ' \
                                       'dlong_min, dshort_min, short_enabled_flag, name, exchange, ' \
                                       'coupon_quantity_per_year, maturity_date, nominal, initial_nominal, ' \
                                       'state_reg_date, placement_date, placement_price, aci_value, country_of_risk, ' \
                                       'country_of_risk_name, sector, issue_kind, issue_size, issue_size_plan, ' \
                                       'trading_status, otc_flag, buy_available_flag, sell_available_flag, ' \
                                       'floating_coupon_flag, perpetual_flag, amortization_flag, min_price_increment, ' \
                                       'api_trade_available_flag, uid, real_exchange, position_uid, for_iis_flag, ' \
                                       'for_qual_investor_flag, weekend_flag, blocked_tca_flag, subordinated_flag, ' \
                                       'liquidity_flag, first_1min_candle_date, first_1day_candle_date, risk_level' \
                                       ') VALUES '
                    bonds_count: int = len(pack)  # Количество облигаций.
                    for i in range(bonds_count):
                        if i > 0: sql_command += ', '  # Если добавляемая облигация не первая.
                        sql_command += '(' \
                                       ':figi{0}, :ticker{0}, :class_code{0}, :isin{0}, :lot{0}, :currency{0}, ' \
                                       ':klong{0}, :kshort{0}, :dlong{0}, :dshort{0}, :dlong_min{0}, :dshort_min{0}, ' \
                                       ':short_enabled_flag{0}, :name{0}, :exchange{0}, :coupon_quantity_per_year{0}, ' \
                                       ':maturity_date{0}, :nominal{0}, :initial_nominal{0}, :state_reg_date{0}, ' \
                                       ':placement_date{0}, :placement_price{0}, :aci_value{0}, :country_of_risk{0}, ' \
                                       ':country_of_risk_name{0}, :sector{0}, :issue_kind{0}, :issue_size{0},' \
                                       ':issue_size_plan{0}, :trading_status{0}, :otc_flag{0}, :buy_available_flag{0}, ' \
                                       ':sell_available_flag{0}, :floating_coupon_flag{0}, :perpetual_flag{0}, ' \
                                       ':amortization_flag{0}, :min_price_increment{0}, :api_trade_available_flag{0}, ' \
                                       ':uid{0}, :real_exchange{0}, :position_uid{0}, :for_iis_flag{0}, ' \
                                       ':for_qual_investor_flag{0}, :weekend_flag{0}, :blocked_tca_flag{0}, ' \
                                       ':subordinated_flag{0}, :liquidity_flag{0}, :first_1min_candle_date{0}, ' \
                                       ':first_1day_candle_date{0}, :risk_level{0}' \
                                       ')'.format(i)

                    prepare_flag: bool = query.prepare(sql_command)
                    assert prepare_flag, query.lastError().text()

                    for i, bond in enumerate(pack):
                        query.bindValue(':figi{0}'.format(i), bond.figi)
                        query.bindValue(':ticker{0}'.format(i), bond.ticker)
                        query.bindValue(':class_code{0}'.format(i), bond.class_code)
                        query.bindValue(':isin{0}'.format(i), bond.isin)
                        query.bindValue(':lot{0}'.format(i), bond.lot)
                        query.bindValue(':currency{0}'.format(i), bond.currency)
                        query.bindValue(':klong{0}'.format(i), MyQuotation.__repr__(bond.klong))
                        query.bindValue(':kshort{0}'.format(i), MyQuotation.__repr__(bond.kshort))
                        query.bindValue(':dlong{0}'.format(i), MyQuotation.__repr__(bond.dlong))
                        query.bindValue(':dshort{0}'.format(i), MyQuotation.__repr__(bond.dshort))
                        query.bindValue(':dlong_min{0}'.format(i), MyQuotation.__repr__(bond.dlong_min))
                        query.bindValue(':dshort_min{0}'.format(i), MyQuotation.__repr__(bond.dshort_min))
                        query.bindValue(':short_enabled_flag{0}'.format(i), bond.short_enabled_flag)
                        query.bindValue(':name{0}'.format(i), bond.name)
                        query.bindValue(':exchange{0}'.format(i), bond.exchange)
                        query.bindValue(':coupon_quantity_per_year{0}'.format(i), bond.coupon_quantity_per_year)
                        query.bindValue(':maturity_date{0}'.format(i), MyDatabase.convertDateTimeToText(bond.maturity_date))
                        query.bindValue(':nominal{0}'.format(i), MyMoneyValue.__repr__(bond.nominal))
                        query.bindValue(':initial_nominal{0}'.format(i), MyMoneyValue.__repr__(bond.initial_nominal))
                        query.bindValue(':state_reg_date{0}'.format(i), MyDatabase.convertDateTimeToText(bond.state_reg_date))
                        query.bindValue(':placement_date{0}'.format(i), MyDatabase.convertDateTimeToText(bond.placement_date))
                        query.bindValue(':placement_price{0}'.format(i), MyMoneyValue.__repr__(bond.placement_price))
                        query.bindValue(':aci_value{0}'.format(i), MyMoneyValue.__repr__(bond.aci_value))
                        query.bindValue(':country_of_risk{0}'.format(i), bond.country_of_risk)
                        query.bindValue(':country_of_risk_name{0}'.format(i), bond.country_of_risk_name)
                        query.bindValue(':sector{0}'.format(i), bond.sector)
                        query.bindValue(':issue_kind{0}'.format(i), bond.issue_kind)
                        query.bindValue(':issue_size{0}'.format(i), bond.issue_size)
                        query.bindValue(':issue_size_plan{0}'.format(i), bond.issue_size_plan)
                        query.bindValue(':trading_status{0}'.format(i), int(bond.trading_status))
                        query.bindValue(':otc_flag{0}'.format(i), bond.otc_flag)
                        query.bindValue(':buy_available_flag{0}'.format(i), bond.buy_available_flag)
                        query.bindValue(':sell_available_flag{0}'.format(i), bond.sell_available_flag)
                        query.bindValue(':floating_coupon_flag{0}'.format(i), bond.floating_coupon_flag)
                        query.bindValue(':perpetual_flag{0}'.format(i), bond.perpetual_flag)
                        query.bindValue(':amortization_flag{0}'.format(i), bond.amortization_flag)
                        query.bindValue(':min_price_increment{0}'.format(i), MyQuotation.__repr__(bond.min_price_increment))
                        query.bindValue(':api_trade_available_flag{0}'.format(i), bond.api_trade_available_flag)
                        query.bindValue(':uid{0}'.format(i), bond.uid)
                        query.bindValue(':real_exchange{0}'.format(i), int(bond.real_exchange))
                        query.bindValue(':position_uid{0}'.format(i), bond.position_uid)
                        query.bindValue(':for_iis_flag{0}'.format(i), bond.for_iis_flag)
                        query.bindValue(':for_qual_investor_flag{0}'.format(i), bond.for_qual_investor_flag)
                        query.bindValue(':weekend_flag{0}'.format(i), bond.weekend_flag)
                        query.bindValue(':blocked_tca_flag{0}'.format(i), bond.blocked_tca_flag)
                        query.bindValue(':subordinated_flag{0}'.format(i), bond.subordinated_flag)
                        query.bindValue(':liquidity_flag{0}'.format(i), bond.liquidity_flag)
                        query.bindValue(':first_1min_candle_date{0}'.format(i), MyDatabase.convertDateTimeToText(bond.first_1min_candle_date))
                        query.bindValue(':first_1day_candle_date{0}'.format(i), MyDatabase.convertDateTimeToText(bond.first_1day_candle_date))
                        query.bindValue(':risk_level{0}'.format(i), int(bond.risk_level))

                    exec_flag: bool = query.exec()
                    assert exec_flag, query.lastError().text()

                commit_flag: bool = db.commit()  # Фиксирует транзакцию в базу данных.
                assert commit_flag
