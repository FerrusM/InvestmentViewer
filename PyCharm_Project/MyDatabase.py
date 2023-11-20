from PyQt6.QtSql import QSqlDatabase, QSqlQuery, QSqlDriver
from tinkoff.invest import Bond, LastPrice, Asset, InstrumentLink, AssetInstrument
from Classes import TokenClass, MyConnection
from MyMoneyValue import MyMoneyValue
from MyQuotation import MyQuotation


class MainConnection(MyConnection):
    CONNECTION_NAME: str = 'InvestmentViewer'

    def __init__(self):
        self.open()  # Открываем соединение с базой данных.
        self.createDataBase()  # Создаёт базу данных.

        def notificationSlot(name: str, source: QSqlDriver.NotificationSource, payload):
            match name:
                case 'Bonds':
                    print('notificationSlot: name = Bonds, source = {0}, payload = {1}'.format(source, payload))
                case _:
                    print('notificationSlot: name = {0}, source = {1}, payload = {2}'.format(name, source, payload))
                    assert False, 'Неверный параметр name ({0}).'.format(name)

        db: QSqlDatabase = self.getDatabase()
        driver = db.driver()
        driver.subscribeToNotification('Bonds')
        driver.notification.connect(notificationSlot)

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
            token TEXT NOT NULL PRIMARY KEY,
            name TEXT NULL
            )''')
            exec_flag: bool = query.exec()
            assert exec_flag, query.lastError().text()
            '''------------------------------------------------'''

            '''------------Создание таблиц лимитов------------'''
            unary_limits_query = QSqlQuery(db)
            unary_limits_query.prepare('''
            CREATE TABLE IF NOT EXISTS UnaryLimits (
            token TEXT NOT NULL,
            limit_per_minute INTEGER NOT NULL,
            methods TEXT NOT NULL,
            FOREIGN KEY (token) REFERENCES Tokens(token) ON DELETE CASCADE
            )''')
            exec_flag: bool = unary_limits_query.exec()
            assert exec_flag, unary_limits_query.lastError().text()

            query = QSqlQuery(db)
            query.prepare('''
            CREATE TABLE IF NOT EXISTS StreamLimits (
            token TEXT NOT NULL,
            limit_count INTEGER NOT NULL,
            streams TEXT NOT NULL,
            open INTEGER NOT NULL,
            FOREIGN KEY (token) REFERENCES Tokens(token) ON DELETE CASCADE
            )''')
            exec_flag: bool = query.exec()
            assert exec_flag, query.lastError().text()
            '''-----------------------------------------------'''

            '''------------------Создание таблицы счетов------------------'''
            query = QSqlQuery(db)
            query.prepare('''
            CREATE TABLE IF NOT EXISTS Accounts (
            token TEXT NOT NULL,
            id TEXT NOT NULL,
            type INTEGER NOT NULL,
            name TEXT NOT NULL,
            status INTEGER NOT NULL,
            opened_date TEXT NOT NULL,
            closed_date TEXT NOT NULL,
            access_level INTEGER NOT NULL,
            PRIMARY KEY (token, id),
            FOREIGN KEY (token) REFERENCES Tokens(token) ON DELETE CASCADE
            );''')
            exec_flag: bool = query.exec()
            assert exec_flag, query.lastError().text()
            '''-----------------------------------------------------------'''

            '''--------Создание таблицы figi-идентификаторов облигаций--------'''
            query = QSqlQuery(db)
            query.prepare('''
            CREATE TABLE IF NOT EXISTS "BondsFinancialInstrumentGlobalIdentifiers"(
            figi TEXT NOT NULL,
            coupons TEXT,
            PRIMARY KEY (figi)
            );''')
            exec_flag: bool = query.exec()
            assert exec_flag, query.lastError().text()
            '''---------------------------------------------------------------'''

            '''------------------Создание таблицы облигаций------------------'''
            query = QSqlQuery(db)
            query.prepare('''
            CREATE TABLE IF NOT EXISTS Bonds (
            figi TEXT NOT NULL,
            ticker TEXT NOT NULL,
            class_code TEXT NOT NULL,
            isin TEXT NOT NULL,
            lot INTEGER NOT NULL,
            currency TEXT NOT NULL,
            klong TEXT NOT NULL,
            kshort TEXT NOT NULL,
            dlong TEXT NOT NULL,
            dshort TEXT NOT NULL,
            dlong_min TEXT NOT NULL,
            dshort_min TEXT NOT NULL,
            short_enabled_flag BOOL NOT NULL,
            name TEXT NOT NULL,
            exchange TEXT NOT NULL,
            coupon_quantity_per_year INTEGER NOT NULL,
            maturity_date TEXT NOT NULL,
            nominal TEXT NOT NULL,
            initial_nominal TEXT NOT NULL,
            state_reg_date TEXT NOT NULL,
            placement_date TEXT NOT NULL,
            placement_price TEXT NOT NULL,
            aci_value TEXT NOT NULL,
            country_of_risk TEXT NOT NULL,
            country_of_risk_name TEXT NOT NULL,
            sector TEXT NOT NULL,
            issue_kind TEXT NOT NULL,
            issue_size INTEGER NOT NULL,
            issue_size_plan INTEGER NOT NULL,
            trading_status INTEGER NOT NULL,
            otc_flag BOOL NOT NULL,
            buy_available_flag BOOL NOT NULL,
            sell_available_flag BOOL NOT NULL,
            floating_coupon_flag BOOL NOT NULL,
            perpetual_flag BOOL NOT NULL,
            amortization_flag BOOL NOT NULL,
            min_price_increment TEXT NOT NULL,
            api_trade_available_flag BOOL NOT NULL,
            uid TEXT NOT NULL,
            real_exchange INTEGER NOT NULL,
            position_uid TEXT NOT NULL,
            for_iis_flag BOOL NOT NULL,
            for_qual_investor_flag BOOL NOT NULL,
            weekend_flag BOOL NOT NULL,
            blocked_tca_flag BOOL NOT NULL,
            subordinated_flag BOOL NOT NULL,
            liquidity_flag BOOL NOT NULL,
            first_1min_candle_date TEXT NOT NULL,
            first_1day_candle_date TEXT NOT NULL,
            risk_level INTEGER NOT NULL,
            coupons TEXT,
            PRIMARY KEY (uid),
            FOREIGN KEY (figi) REFERENCES "BondsFinancialInstrumentGlobalIdentifiers"("figi")
            );''')
            exec_flag: bool = query.exec()
            assert exec_flag, query.lastError().text()
            '''--------------------------------------------------------------'''

            '''--------------------Создание таблицы акций--------------------'''
            query = QSqlQuery(db)
            query.prepare('''
            CREATE TABLE IF NOT EXISTS Shares (
            figi TEXT NOT NULL,
            ticker TEXT NOT NULL,
            class_code TEXT NOT NULL,
            isin TEXT NOT NULL,
            lot INTEGER NOT NULL,
            currency TEXT NOT NULL,
            klong TEXT NOT NULL,
            kshort TEXT NOT NULL,
            dlong TEXT NOT NULL,
            dshort TEXT NOT NULL,
            dlong_min TEXT NOT NULL,
            dshort_min TEXT NOT NULL,
            short_enabled_flag BOOL NOT NULL,
            name TEXT NOT NULL,
            exchange TEXT NOT NULL, 
            ipo_date TEXT NOT NULL,
            issue_size INTEGER NOT NULL,
            country_of_risk TEXT NOT NULL,
            country_of_risk_name TEXT NOT NULL,
            sector TEXT NOT NULL,
            issue_size_plan INTEGER NOT NULL,
            nominal TEXT NOT NULL,
            trading_status INTEGER NOT NULL,
            otc_flag BOOL NOT NULL,
            buy_available_flag BOOL NOT NULL,
            sell_available_flag BOOL NOT NULL,
            div_yield_flag BOOL NOT NULL,
            share_type INTEGER NOT NULL,
            min_price_increment TEXT NOT NULL,
            api_trade_available_flag BOOL NOT NULL,
            uid TEXT NOT NULL PRIMARY KEY,
            real_exchange INTEGER NOT NULL,
            position_uid TEXT NOT NULL,
            for_iis_flag BOOL NOT NULL,
            for_qual_investor_flag BOOL NOT NULL,
            weekend_flag BOOL NOT NULL,
            blocked_tca_flag BOOL NOT NULL,
            liquidity_flag BOOL NOT NULL,
            first_1min_candle_date TEXT NOT NULL,
            first_1day_candle_date TEXT NOT NULL
            )''')
            exec_flag: bool = query.exec()
            assert exec_flag, query.lastError().text()
            '''--------------------------------------------------------------'''

            '''-----Создание представления figi-идентификаторов облигаций-----'''
            # query = QSqlQuery(db)
            # query.prepare('''
            # CREATE VIEW IF NOT EXISTS "BondsFinancialInstrumentGlobalIdentifiers"("figi", "coupons")
            # AS
            # SELECT DISTINCT "Bonds"."figi" AS "figi", NULL AS "coupons" FROM "Bonds";
            # ''')
            # exec_flag: bool = query.exec()
            # assert exec_flag, query.lastError().text()
            '''---------------------------------------------------------------'''

            '''----------Создание представления uid-идентификаторов----------'''
            query = QSqlQuery(db)
            query.prepare('''
            CREATE VIEW IF NOT EXISTS InstrumentUniqueIdentifiers(uid)
            AS
            SELECT Bonds.uid FROM Bonds UNION SELECT Shares.uid FROM Shares;
            ''')
            exec_flag: bool = query.exec()
            assert exec_flag, query.lastError().text()
            '''--------------------------------------------------------------'''

            '''-------------------Создание таблицы купонов-------------------'''
            query = QSqlQuery(db)
            query.prepare('''
            CREATE TABLE IF NOT EXISTS Coupons (
            figi TEXT NOT NULL,
            coupon_date TEXT NOT NULL,
            coupon_number INTEGER NOT NULL,
            fix_date TEXT NOT NULL,
            pay_one_bond TEXT NOT NULL,
            coupon_type INTEGER NOT NULL,
            coupon_start_date TEXT NOT NULL,
            coupon_end_date TEXT NOT NULL,
            coupon_period INTEGER NOT NULL,
            UNIQUE (figi, coupon_number),
            FOREIGN KEY (figi) REFERENCES "BondsFinancialInstrumentGlobalIdentifiers"("figi") ON DELETE CASCADE
            );''')
            exec_flag: bool = query.exec()
            assert exec_flag, query.lastError().text()
            '''--------------------------------------------------------------'''

            '''---------------Триггер перед добавлением облигации---------------'''
            bonds_before_insert_trigger_query = QSqlQuery(db)
            bonds_before_insert_trigger_query.prepare('''
            CREATE TRIGGER IF NOT EXISTS "Bonds_before_insert_trigger" BEFORE INSERT ON "Bonds"
            BEGIN             
                INSERT OR IGNORE INTO "BondsFinancialInstrumentGlobalIdentifiers"("figi") VALUES (NEW."figi");
            END;
            ''')
            bonds_before_insert_trigger_exec_flag: bool = bonds_before_insert_trigger_query.exec()
            assert bonds_before_insert_trigger_exec_flag, bonds_before_insert_trigger_query.lastError().text()
            '''-----------------------------------------------------------------'''

            '''---------------Триггер перед обновлением облигации---------------'''
            bonds_before_update_trigger_query = QSqlQuery(db)
            bonds_before_update_trigger_query.prepare('''
            CREATE TRIGGER IF NOT EXISTS Bonds_before_update_trigger BEFORE UPDATE ON Bonds
            BEGIN
                DELETE FROM Coupons WHERE figi = OLD.figi AND NEW.figi != OLD.figi;
                UPDATE "BondsFinancialInstrumentGlobalIdentifiers" SET "coupons" = NULL WHERE figi = OLD.figi;
            END;
            ''')
            bonds_before_update_trigger_exec_flag: bool = bonds_before_update_trigger_query.exec()
            assert bonds_before_update_trigger_exec_flag, bonds_before_update_trigger_query.lastError().text()
            '''-----------------------------------------------------------------'''

            '''----------------Создание таблицы последних цен----------------'''
            query = QSqlQuery(db)
            # query.prepare('''
            # CREATE TABLE IF NOT EXISTS LastPrices (
            # figi TEXT NOT NULL,
            # price TEXT NOT NULL,
            # time TEXT NOT NULL,
            # instrument_uid TEXT NOT NULL,
            # PRIMARY KEY (time, instrument_uid),
            # FOREIGN KEY (instrument_uid) REFERENCES InstrumentUniqueIdentifiers(uid) ON DELETE CASCADE
            # );''')
            query.prepare('''
            CREATE TABLE IF NOT EXISTS LastPrices (
            figi TEXT NOT NULL,
            price TEXT NOT NULL,
            time TEXT NOT NULL,
            instrument_uid TEXT NOT NULL,
            PRIMARY KEY (time, instrument_uid)
            );''')
            exec_flag: bool = query.exec()
            assert exec_flag, query.lastError().text()
            '''--------------------------------------------------------------'''

            '''-------------------Создание таблицы брэндов-------------------'''
            query = QSqlQuery(db)
            query.prepare('''
            CREATE TABLE IF NOT EXISTS Brands (
            uid TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            info TEXT NOT NULL,
            company TEXT NOT NULL,
            sector TEXT NOT NULL,
            country_of_risk TEXT NOT NULL,
            country_of_risk_name TEXT NOT NULL,         
            PRIMARY KEY (uid)
            );''')
            exec_flag: bool = query.exec()
            assert exec_flag, query.lastError().text()
            '''--------------------------------------------------------------'''

            '''-------------------Создание таблицы активов-------------------'''
            query = QSqlQuery(db)
            query.prepare('''
            CREATE TABLE IF NOT EXISTS Assets (
            uid TEXT NOT NULL PRIMARY KEY,
            type INTEGER NOT NULL,
            name TEXT NOT NULL,
            name_brief TEXT, 
            description TEXT,
            deleted_at TEXT,
            required_tests TEXT,
            currency,
            security,
            gos_reg_code TEXT,
            cfi TEXT,
            code_nsd TEXT,
            status TEXT,
            brand_uid TEXT,
            updated_at TEXT,
            br_code TEXT,
            br_code_name TEXT,
            FOREIGN KEY(brand_uid) REFERENCES Brands(uid)
            );''')
            exec_flag: bool = query.exec()
            assert exec_flag, query.lastError().text()
            '''--------------------------------------------------------------'''

            '''--------------Создание таблицы AssetInstruments--------------'''
            query = QSqlQuery(db)
            query.prepare('''
            CREATE TABLE IF NOT EXISTS AssetInstruments (
            asset_uid TEXT NOT NULL,
            uid TEXT NOT NULL,
            figi TEXT NOT NULL,
            instrument_type TEXT NOT NULL,
            ticker TEXT NOT NULL,
            class_code TEXT NOT NULL,
            instrument_kind INTEGER NOT NULL,
            position_uid TEXT NOT NULL,
            CONSTRAINT assert_instrument_pk PRIMARY KEY(asset_uid, uid),
            FOREIGN KEY (asset_uid) REFERENCES Assets(uid) ON DELETE CASCADE
            );''')
            exec_flag: bool = query.exec()
            assert exec_flag, query.lastError().text()
            '''-------------------------------------------------------------'''

            '''--------------Создание таблицы InstrumentLinks--------------'''
            query = QSqlQuery(db)
            query.prepare('''
            CREATE TABLE IF NOT EXISTS InstrumentLinks (
            asset_uid TEXT NOT NULL,
            uid TEXT NOT NULL,
            type TEXT NOT NULL,
            instrument_uid TEXT NOT NULL,
            UNIQUE (asset_uid, uid, type, instrument_uid),
            FOREIGN KEY (asset_uid, uid) REFERENCES AssetInstruments(asset_uid, uid) ON DELETE CASCADE
            );''')
            exec_flag: bool = query.exec()
            assert exec_flag, query.lastError().text()
            '''------------------------------------------------------------'''

            '''--------Добавление триггера перед обновлением актива--------'''
            assets_on_update_trigger_query = QSqlQuery(db)
            assets_on_update_trigger_query.prepare('''
            CREATE TRIGGER IF NOT EXISTS Assets_on_update_trigger BEFORE UPDATE ON Assets
            BEGIN               
                DELETE FROM AssetInstruments WHERE asset_uid = OLD.uid;
            END;
            ''')
            assets_on_update_trigger_exec_flag: bool = assets_on_update_trigger_query.exec()
            assert assets_on_update_trigger_exec_flag, assets_on_update_trigger_query.lastError().text()
            '''------------------------------------------------------------'''

            commit_flag: bool = db.commit()  # Фиксирует транзакцию в базу данных.
            assert commit_flag

    @classmethod
    def addNewToken(cls, token: TokenClass):
        """Добавляет новый токен в таблицу токенов."""
        db: QSqlDatabase = cls.getDatabase()

        transaction_flag: bool = db.transaction()  # Начинает транзакцию в базе данных.
        assert transaction_flag

        if transaction_flag:
            query = QSqlQuery(db)
            query.prepare('INSERT INTO Tokens (token, name) VALUES (:token, :name);')
            query.bindValue(':token', token.token)
            query.bindValue(':name', token.name)
            exec_flag: bool = query.exec()
            assert exec_flag, query.lastError().text()

            for unary_limit in token.unary_limits:
                query = QSqlQuery(db)
                query.prepare('''
                INSERT INTO UnaryLimits (token, limit_per_minute, methods) 
                VALUES (:token, :limit_per_minute, :methods);
                ''')
                query.bindValue(':token', token.token)
                query.bindValue(':limit_per_minute', unary_limit.limit_per_minute)
                query.bindValue(':methods', cls.convertStrListToStr([method.full_method for method in unary_limit.methods]))
                exec_flag: bool = query.exec()
                assert exec_flag, query.lastError().text()

            for stream_limit in token.stream_limits:
                query = QSqlQuery(db)
                query.prepare('''
                INSERT INTO StreamLimits (token, limit_count, streams, open) 
                VALUES (:token, :limit_count, :streams, :open);
                ''')
                query.bindValue(':token', token.token)
                query.bindValue(':limit_count', stream_limit.limit)
                query.bindValue(':streams', cls.convertStrListToStr([method.full_method for method in stream_limit.methods]))
                query.bindValue(':open', stream_limit.open)
                exec_flag: bool = query.exec()
                assert exec_flag, query.lastError().text()

            for account in token.accounts:
                query = QSqlQuery(db)
                query.prepare('''
                INSERT INTO Accounts (token, id, type, name, status, opened_date, closed_date, access_level)
                VALUES (:token, :id, :type, :name, :status, :opened_date, :closed_date, :access_level);
                ''')
                query.bindValue(':token', token.token)
                query.bindValue(':id', account.id)
                query.bindValue(':type', int(account.type))
                query.bindValue(':name', account.name)
                query.bindValue(':status', int(account.status))
                query.bindValue(':opened_date', MyConnection.convertDateTimeToText(account.opened_date))
                query.bindValue(':closed_date', MyConnection.convertDateTimeToText(account.closed_date))
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
        query.prepare('DELETE FROM Tokens WHERE token = :token;')
        query.bindValue(':token', token)
        exec_flag: bool = query.exec()
        assert exec_flag, query.lastError().text()

    # @staticmethod
    # def _partition(array: list, length: int):
    #     for i in range(0, len(array), length):
    #         yield array[i:(i + length)]

    @classmethod
    def addBonds(cls, bonds: list[Bond]):
        """Добавляет облигации в таблицу облигаций."""
        if bonds:  # Если список облигаций не пуст.
            VARIABLES_COUNT: int = 50  # Количество variables в каждом insert.
            bonds_in_pack: int = int(cls.VARIABLE_LIMIT / VARIABLES_COUNT)
            assert bonds_in_pack > 0

            def partition(array: list, length=bonds_in_pack):
                for j in range(0, len(array), length):
                    yield array[j:(j + length)]

            db: QSqlDatabase = cls.getDatabase()
            transaction_flag: bool = db.transaction()  # Начинает транзакцию в базе данных.
            assert transaction_flag

            if transaction_flag:
                bonds_packs: list[list[Bond]] = list(partition(bonds))
                for pack in bonds_packs:
                    query = QSqlQuery(db)
                    sql_command: str = 'INSERT INTO "Bonds"(' \
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

                    sql_command += ' ON CONFLICT(uid) DO ' \
                                   'UPDATE SET figi = excluded.figi, ticker = excluded.ticker, ' \
                                   'class_code = excluded.class_code, isin = excluded.isin, lot = excluded.lot, ' \
                                   'currency = excluded.currency, klong = excluded.klong, kshort = excluded.kshort, ' \
                                   'dlong = excluded.dlong, dshort = excluded.dshort, dlong_min = excluded.dlong_min, ' \
                                   'dshort_min = excluded.dshort_min, short_enabled_flag = excluded.short_enabled_flag, ' \
                                   'name = excluded.name, exchange = excluded.exchange, ' \
                                   'coupon_quantity_per_year = excluded.coupon_quantity_per_year, ' \
                                   'maturity_date = excluded.maturity_date, nominal = excluded.nominal, ' \
                                   'initial_nominal = excluded.initial_nominal, state_reg_date = excluded.state_reg_date, ' \
                                   'placement_date = excluded.placement_date, placement_price = excluded.placement_price, ' \
                                   'aci_value = excluded.aci_value, country_of_risk = excluded.country_of_risk, ' \
                                   'country_of_risk_name = excluded.country_of_risk_name, sector = excluded.sector, ' \
                                   'issue_kind = excluded.issue_kind, issue_size = excluded.issue_size, ' \
                                   'issue_size_plan = excluded.issue_size_plan, trading_status = excluded.trading_status, ' \
                                   'otc_flag = excluded.otc_flag, buy_available_flag = excluded.buy_available_flag, ' \
                                   'sell_available_flag = excluded.sell_available_flag, ' \
                                   'floating_coupon_flag = excluded.floating_coupon_flag, perpetual_flag = excluded.perpetual_flag, ' \
                                   'amortization_flag = excluded.amortization_flag, min_price_increment = excluded.min_price_increment, ' \
                                   'api_trade_available_flag = excluded.api_trade_available_flag, real_exchange = excluded.real_exchange, ' \
                                   'position_uid = excluded.position_uid, for_iis_flag = excluded.for_iis_flag, ' \
                                   'for_qual_investor_flag = excluded.for_qual_investor_flag, weekend_flag = excluded.weekend_flag, ' \
                                   'blocked_tca_flag = excluded.blocked_tca_flag, subordinated_flag = excluded.subordinated_flag, ' \
                                   'liquidity_flag = excluded.liquidity_flag, first_1min_candle_date = excluded.first_1min_candle_date, ' \
                                   'first_1day_candle_date = excluded.first_1day_candle_date, risk_level = excluded.risk_level;'

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
                        query.bindValue(':maturity_date{0}'.format(i), MyConnection.convertDateTimeToText(bond.maturity_date))
                        query.bindValue(':nominal{0}'.format(i), MyMoneyValue.__repr__(bond.nominal))
                        query.bindValue(':initial_nominal{0}'.format(i), MyMoneyValue.__repr__(bond.initial_nominal))
                        query.bindValue(':state_reg_date{0}'.format(i), MyConnection.convertDateTimeToText(bond.state_reg_date))
                        query.bindValue(':placement_date{0}'.format(i), MyConnection.convertDateTimeToText(bond.placement_date))
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
                        query.bindValue(':first_1min_candle_date{0}'.format(i), MyConnection.convertDateTimeToText(bond.first_1min_candle_date))
                        query.bindValue(':first_1day_candle_date{0}'.format(i), MyConnection.convertDateTimeToText(bond.first_1day_candle_date))
                        query.bindValue(':risk_level{0}'.format(i), int(bond.risk_level))

                    exec_flag: bool = query.exec()
                    assert exec_flag, query.lastError().text()

                commit_flag: bool = db.commit()  # Фиксирует транзакцию в базу данных.
                assert commit_flag

    @classmethod
    def addLastPrices(cls, last_prices: list[LastPrice]):
        """Добавляет последние цены в таблицу последних цен."""
        if last_prices:  # Если список последних цен не пуст.
            db: QSqlDatabase = cls.getDatabase()
            transaction_flag: bool = db.transaction()  # Начинает транзакцию в базе данных.
            assert transaction_flag

            if transaction_flag:
                query = QSqlQuery(db)
                sql_command: str = 'INSERT INTO "LastPrices"(figi, price, time, instrument_uid) VALUES '
                lp_count: int = len(last_prices)  # Количество последних цен.
                for i in range(lp_count):
                    if i > 0: sql_command += ', '  # Если добавляемая последняя цена не первая.
                    sql_command += '(:figi{0}, :price{0}, :time{0}, :instrument_uid{0})'.format(i)

                sql_command += ' ON CONFLICT(time, instrument_uid) DO ' \
                               'UPDATE SET figi = excluded.figi, price = excluded.price;'

                prepare_flag: bool = query.prepare(sql_command)
                assert prepare_flag, query.lastError().text()

                for i, lp in enumerate(last_prices):
                    query.bindValue(':figi{0}'.format(i), lp.figi)
                    query.bindValue(':price{0}'.format(i), MyQuotation.__repr__(lp.price))
                    query.bindValue(':time{0}'.format(i), MyConnection.convertDateTimeToText(lp.time))
                    query.bindValue(':instrument_uid{0}'.format(i), lp.instrument_uid)

                exec_flag: bool = query.exec()
                assert exec_flag, query.lastError().text()

                commit_flag: bool = db.commit()  # Фиксирует транзакцию в базу данных.
                assert commit_flag

    @staticmethod
    def addAssetInstrument(db: QSqlDatabase, asset_uid: str, instrument: AssetInstrument):
        """Добавляет идентификаторы инструмента актива в таблицу идентификаторов инструментов активов."""
        def addInstrumentLinks(instrument_uid: str, links: list[InstrumentLink]):
            """Добавляет связанные инструменты в таблицу связей инструментов."""
            if links:  # Если список связанных инструментов не пуст.
                insert_link_query = QSqlQuery(db)
                insert_link_sql_command: str = 'INSERT INTO InstrumentLinks (asset_uid, uid, type, instrument_uid) VALUES '
                links_count: int = len(links)  # Количество связей.
                for j in range(links_count):
                    if j > 0: insert_link_sql_command += ', '  # Если добавляемая связь не первая.
                    insert_link_sql_command += '(:asset_uid{0}, :uid{0}, :type{0}, :instrument_uid{0})'.format(j)
                insert_link_sql_command += ';'

                insert_link_prepare_flag: bool = insert_link_query.prepare(insert_link_sql_command)
                assert insert_link_prepare_flag, insert_link_query.lastError().text()

                for j, link in enumerate(links):
                    insert_link_query.bindValue(':asset_uid{0}'.format(j), asset_uid)
                    insert_link_query.bindValue(':uid{0}'.format(j), instrument_uid)
                    insert_link_query.bindValue(':type{0}'.format(j), link.type)
                    insert_link_query.bindValue(':instrument_uid{0}'.format(j), link.instrument_uid)

                insert_link_exec_flag: bool = insert_link_query.exec()
                assert insert_link_exec_flag, '\n{0}\n{1}\nasset_uid: {2}, instrument_uid: {3}\n'.format(insert_link_query.lastError().text(), insert_link_query.lastQuery(), asset_uid, instrument_uid)

        insert_ai_query = QSqlQuery(db)
        insert_ai_prepare_flag: bool = insert_ai_query.prepare('''
        INSERT INTO AssetInstruments (asset_uid, uid, figi, instrument_type, ticker, class_code, instrument_kind, position_uid) VALUES
        (:asset_uid, :uid, :figi, :instrument_type, :ticker, :class_code, :instrument_kind, :position_uid);
        ''')
        assert insert_ai_prepare_flag, insert_ai_query.lastError().text()

        insert_ai_query.bindValue(':asset_uid', asset_uid)
        insert_ai_query.bindValue(':uid', instrument.uid)
        insert_ai_query.bindValue(':figi', instrument.figi)
        insert_ai_query.bindValue(':instrument_type', instrument.instrument_type)
        insert_ai_query.bindValue(':ticker', instrument.ticker)
        insert_ai_query.bindValue(':class_code', instrument.class_code)
        insert_ai_query.bindValue(':instrument_kind', int(instrument.instrument_kind))
        insert_ai_query.bindValue(':position_uid', instrument.position_uid)

        insert_ai_exec_flag: bool = insert_ai_query.exec()
        assert insert_ai_exec_flag, insert_ai_query.lastError().text()

        addInstrumentLinks(instrument.uid, instrument.links)  # Добавляем связанные инструменты в таблицу связей инструментов.

    @classmethod
    def addAssets(cls, assets: list[Asset]):
        """Добавляет активы в таблицу активов."""
        if assets:  # Если список активов не пуст.
            db: QSqlDatabase = cls.getDatabase()
            transaction_flag: bool = db.transaction()  # Начинает транзакцию в базе данных.
            assert transaction_flag, db.lastError().text()

            if transaction_flag:
                def insertAsset(asset: Asset):
                    """Добавляет актив в таблицу активов."""
                    insert_asset_query = QSqlQuery(db)
                    insert_asset_prepare_flag: bool = insert_asset_query.prepare('''
                    INSERT INTO Assets(uid, type, name) VALUES (:uid, :type, :name)
                    ON CONFLICT(uid) DO UPDATE SET type = excluded.type, name = excluded.name;
                    ''')
                    assert insert_asset_prepare_flag, insert_asset_query.lastError().text()

                    insert_asset_query.bindValue(':uid', asset.uid)
                    insert_asset_query.bindValue(':type', int(asset.type))
                    insert_asset_query.bindValue(':name', asset.name)

                    insert_asset_exec_flag: bool = insert_asset_query.exec()
                    assert insert_asset_exec_flag, insert_asset_query.lastError().text()

                    for instrument in asset.instruments:
                        cls.addAssetInstrument(db, asset.uid, instrument)  # Добавляем идентификаторы инструмента актива в таблицу идентификаторов инструментов активов.

                for a in assets:
                    insertAsset(a)  # Добавляем актив в таблицу активов.

                commit_flag: bool = db.commit()  # Фиксирует транзакцию в базу данных.
                assert commit_flag, db.lastError().text()
