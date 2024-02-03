from PyQt6.QtSql import QSqlDatabase, QSqlQuery, QSqlDriver
from tinkoff.invest import Bond, LastPrice, Asset, InstrumentLink, AssetInstrument, Share, InstrumentStatus, AssetType, \
    InstrumentType
from Classes import TokenClass, MyConnection, partition
from MyMoneyValue import MyMoneyValue
from MyQuotation import MyQuotation


class MainConnection(MyConnection):
    CONNECTION_NAME: str = 'InvestmentViewer'

    def __init__(self):
        self.open()  # Открываем соединение с базой данных.
        self.createDataBase()  # Создаёт базу данных.

        def notificationSlot(name: str, source: QSqlDriver.NotificationSource, payload):
            print('notificationSlot: name = {0}, source = {1}, payload = {2}'.format(name, source, payload))
            assert name == self.BONDS_TABLE, 'Неверный параметр name ({0}).'.format(name)

        db: QSqlDatabase = self.getDatabase()
        driver = db.driver()
        subscribe_flag: bool = driver.subscribeToNotification(self.BONDS_TABLE)
        assert subscribe_flag, 'Не удалось подписаться на уведомления об изменении таблицы {0}.'.format(self.BONDS_TABLE)
        driver.notification.connect(notificationSlot)

    @classmethod  # Привязывает метод к классу, а не к конкретному экземпляру этого класса.
    def createDataBase(cls):
        """Создаёт базу данных."""
        db: QSqlDatabase = cls.getDatabase()
        transaction_flag: bool = db.transaction()  # Начинает транзакцию в базе данных.
        assert transaction_flag

        if transaction_flag:
            '''------------Создание таблицы токенов------------'''
            tokens_query = QSqlQuery(db)
            tokens_prepare_flag: bool = tokens_query.prepare('''
            CREATE TABLE IF NOT EXISTS \"{0}\" (
            \"token\" TEXT NOT NULL,
            \"name\" TEXT NULL,
            PRIMARY KEY (\"token\")
            );'''.format(MyConnection.TOKENS_TABLE))
            assert tokens_prepare_flag, tokens_query.lastError().text()
            tokens_exec_flag: bool = tokens_query.exec()
            assert tokens_exec_flag, tokens_query.lastError().text()
            '''------------------------------------------------'''

            '''------------Создание таблиц лимитов------------'''
            unary_limits_query = QSqlQuery(db)
            unary_limits_prepare_flag: bool = unary_limits_query.prepare('''
            CREATE TABLE IF NOT EXISTS \"{0}\" (
            \"token\" TEXT NOT NULL,
            \"limit_per_minute\" INTEGER NOT NULL,
            \"methods\" TEXT NOT NULL,
            FOREIGN KEY (\"token\") REFERENCES \"{1}\"(\"token\") ON DELETE CASCADE
            );'''.format(MyConnection.UNARY_LIMITS_TABLE, MyConnection.TOKENS_TABLE))
            assert unary_limits_prepare_flag, unary_limits_query.lastError().text()
            unary_limits_exec_flag: bool = unary_limits_query.exec()
            assert unary_limits_exec_flag, unary_limits_query.lastError().text()

            stream_limits_query = QSqlQuery(db)
            stream_limits_prepare_flag: bool = stream_limits_query.prepare('''
            CREATE TABLE IF NOT EXISTS \"{0}\" (
            \"token\" TEXT NOT NULL,
            \"limit_count\" INTEGER NOT NULL,
            \"streams\" TEXT NOT NULL,
            \"open\" INTEGER NOT NULL,
            FOREIGN KEY (\"token\") REFERENCES \"{1}\"(\"token\") ON DELETE CASCADE
            );'''.format(MyConnection.STREAM_LIMITS_TABLE, MyConnection.TOKENS_TABLE))
            assert stream_limits_prepare_flag, stream_limits_query.lastError().text()
            stream_limits_exec_flag: bool = stream_limits_query.exec()
            assert stream_limits_exec_flag, stream_limits_query.lastError().text()
            '''-----------------------------------------------'''

            '''------------------Создание таблицы счетов------------------'''
            accounts_query = QSqlQuery(db)
            accounts_prepare_flag: bool = accounts_query.prepare('''
            CREATE TABLE IF NOT EXISTS \"{0}\" (
            \"token\" TEXT NOT NULL,
            \"id\" TEXT NOT NULL,
            \"type\" INTEGER NOT NULL,
            \"name\" TEXT NOT NULL,
            \"status\" INTEGER NOT NULL,
            \"opened_date\" TEXT NOT NULL,
            \"closed_date\" TEXT NOT NULL,
            \"access_level\" INTEGER NOT NULL,
            PRIMARY KEY (\"token\", \"id\"),
            FOREIGN KEY (\"token\") REFERENCES \"{1}\"(\"token\") ON DELETE CASCADE
            );'''.format(MyConnection.ACCOUNTS_TABLE, MyConnection.TOKENS_TABLE))
            assert accounts_prepare_flag, accounts_query.lastError().text()
            accounts_exec_flag: bool = accounts_query.exec()
            assert accounts_exec_flag, accounts_query.lastError().text()
            '''-----------------------------------------------------------'''

            '''----Создание таблицы ассоциаций uid-идентификаторов инструментов----'''
            instruments_uids_query_str: str = '''
            CREATE TABLE IF NOT EXISTS \"{0}\" (
            \"uid\" TEXT NOT NULL,
            \"instrument_type\" TEXT NOT NULL,
            PRIMARY KEY (\"uid\")
            );'''.format(MyConnection.INSTRUMENT_UIDS_TABLE)
            instruments_uids_query = QSqlQuery(db)
            instruments_uids_prepare_flag: bool = instruments_uids_query.prepare(instruments_uids_query_str)
            assert instruments_uids_prepare_flag, instruments_uids_query.lastError().text()
            instruments_uids_exec_flag: bool = instruments_uids_query.exec()
            assert instruments_uids_exec_flag, instruments_uids_query.lastError().text()
            '''--------------------------------------------------------------------'''

            '''------Триггер перед обновлением таблицы InstrumentUniqueIdentifiers------'''
            instr_bef_up_trigger_query_str: str = '''
            CREATE TRIGGER IF NOT EXISTS \"{0}\" BEFORE UPDATE
            ON \"{1}\"
            BEGIN               	
                SELECT 
                    CASE 
                        WHEN \"NEW\".\"instrument_type\" != \"OLD\".\"instrument_type\"
                            THEN RAISE(FAIL, 'Таблица {1} уже содержит такой же uid, но для другого типа инструмента!')
                    END;
            END;
            '''.format(MyConnection.INSTRUMENT_UIDS_BEFORE_UPDATE_TRIGGER, MyConnection.INSTRUMENT_UIDS_TABLE)
            instr_bef_up_trigger_query = QSqlQuery(db)
            instr_bef_up_trigger_prepare_flag: bool = instr_bef_up_trigger_query.prepare(instr_bef_up_trigger_query_str)
            assert instr_bef_up_trigger_prepare_flag, instr_bef_up_trigger_query.lastError().text()
            instr_bef_up_trigger_exec_flag: bool = instr_bef_up_trigger_query.exec()
            assert instr_bef_up_trigger_exec_flag, instr_bef_up_trigger_query.lastError().text()
            '''-------------------------------------------------------------------------'''

            '''------------------Создание таблицы облигаций------------------'''
            bonds_query_str: str = '''
            CREATE TABLE IF NOT EXISTS \"{0}\" (
            \"figi\" TEXT NOT NULL,
            \"ticker\" TEXT NOT NULL,
            \"class_code\" TEXT NOT NULL,
            \"isin\" TEXT NOT NULL,
            \"lot\" INTEGER NOT NULL,
            \"currency\" TEXT NOT NULL,
            \"klong\" TEXT NOT NULL,
            \"kshort\" TEXT NOT NULL,
            \"dlong\" TEXT NOT NULL,
            \"dshort\" TEXT NOT NULL,
            \"dlong_min\" TEXT NOT NULL,
            \"dshort_min\" TEXT NOT NULL,
            \"short_enabled_flag\" BLOB NOT NULL,
            \"name\" TEXT NOT NULL,
            \"exchange\" TEXT NOT NULL,
            \"coupon_quantity_per_year\" INTEGER NOT NULL,
            \"maturity_date\" TEXT NOT NULL,
            \"nominal\" TEXT NOT NULL,
            \"initial_nominal\" TEXT NOT NULL,
            \"state_reg_date\" TEXT NOT NULL,
            \"placement_date\" TEXT NOT NULL,
            \"placement_price\" TEXT NOT NULL,
            \"aci_value\" TEXT NOT NULL,
            \"country_of_risk\" TEXT NOT NULL,
            \"country_of_risk_name\" TEXT NOT NULL,
            \"sector\" TEXT NOT NULL,
            \"issue_kind\" TEXT NOT NULL,
            \"issue_size\" INTEGER NOT NULL,
            \"issue_size_plan\" INTEGER NOT NULL,
            \"trading_status\" INTEGER NOT NULL,
            \"otc_flag\" BLOB NOT NULL,
            \"buy_available_flag\" BLOB NOT NULL,
            \"sell_available_flag\" BLOB NOT NULL,
            \"floating_coupon_flag\" BLOB NOT NULL,
            \"perpetual_flag\" BLOB NOT NULL,
            \"amortization_flag\" BLOB NOT NULL,
            \"min_price_increment\" TEXT NOT NULL,
            \"api_trade_available_flag\" BLOB NOT NULL,
            \"uid\" TEXT NOT NULL,
            \"real_exchange\" INTEGER NOT NULL,
            \"position_uid\" TEXT NOT NULL,
            \"for_iis_flag\" BLOB NOT NULL,
            \"for_qual_investor_flag\" BLOB NOT NULL,
            \"weekend_flag\" BLOB NOT NULL,
            \"blocked_tca_flag\" BLOB NOT NULL,
            \"subordinated_flag\" BLOB NOT NULL,
            \"liquidity_flag\" BLOB NOT NULL,
            \"first_1min_candle_date\" TEXT NOT NULL,
            \"first_1day_candle_date\" TEXT NOT NULL,
            \"risk_level\" INTEGER NOT NULL,
            \"coupons\" TEXT CHECK(\"coupons\" = \'Yes\' OR \"coupons\" = \'No\'),
            UNIQUE (\"uid\"),
            FOREIGN KEY (\"uid\") REFERENCES \"{1}\"(\"uid\") ON DELETE CASCADE
            );'''.format(MyConnection.BONDS_TABLE, MyConnection.INSTRUMENT_UIDS_TABLE)
            bonds_query = QSqlQuery(db)
            bonds_prepare_flag: bool = bonds_query.prepare(bonds_query_str)
            assert bonds_prepare_flag, bonds_query.lastError().text()
            bonds_exec_flag: bool = bonds_query.exec()
            assert bonds_exec_flag, bonds_query.lastError().text()
            '''--------------------------------------------------------------'''

            '''---------------Триггер перед добавлением облигации---------------'''
            bonds_bef_ins_trigger_query_str: str = '''
            CREATE TRIGGER IF NOT EXISTS \"{0}\" BEFORE INSERT ON \"{1}\"
            BEGIN             
                INSERT INTO \"{2}\"(\"uid\", \"instrument_type\") VALUES (\"NEW\".\"uid\", \'{3}\') ON CONFLICT(\"uid\") DO UPDATE SET \"instrument_type\" = \'{3}\';
            END;
            '''.format(
                MyConnection.BONDS_TRIGGER_BEFORE_INSERT,
                MyConnection.BONDS_TABLE,
                MyConnection.INSTRUMENT_UIDS_TABLE,
                'bond'
            )
            bonds_bef_ins_trigger_query = QSqlQuery(db)
            bonds_bef_ins_trigger_prepare_flag: bool = bonds_bef_ins_trigger_query.prepare(bonds_bef_ins_trigger_query_str)
            assert bonds_bef_ins_trigger_prepare_flag, bonds_bef_ins_trigger_query.lastError().text()
            bonds_bef_ins_trigger_exec_flag: bool = bonds_bef_ins_trigger_query.exec()
            assert bonds_bef_ins_trigger_exec_flag, bonds_bef_ins_trigger_query.lastError().text()
            '''-----------------------------------------------------------------'''

            '''-------------------Создание таблицы купонов-------------------'''
            coupons_query_str: str = '''
            CREATE TABLE IF NOT EXISTS \"{0}\" (
            \"instrument_uid\" TEXT NOT NULL,
            \"figi\" TEXT NOT NULL,
            \"coupon_date\" TEXT NOT NULL,
            \"coupon_number\" INTEGER NOT NULL,
            \"fix_date\" TEXT NOT NULL,
            \"pay_one_bond\" TEXT NOT NULL,
            \"coupon_type\" INTEGER NOT NULL,
            \"coupon_start_date\" TEXT NOT NULL,
            \"coupon_end_date\" TEXT NOT NULL,
            \"coupon_period\" INTEGER NOT NULL,
            UNIQUE (\"instrument_uid\", \"coupon_number\"),
            FOREIGN KEY (\"instrument_uid\") REFERENCES \"{1}\"(\"uid\") ON DELETE CASCADE
            );'''.format(MyConnection.COUPONS_TABLE, MyConnection.BONDS_TABLE)
            coupons_query = QSqlQuery(db)
            coupons_prepare_flag: bool = coupons_query.prepare(coupons_query_str)
            assert coupons_prepare_flag, coupons_query.lastError().text()
            coupons_exec_flag: bool = coupons_query.exec()
            assert coupons_exec_flag, coupons_query.lastError().text()
            '''--------------------------------------------------------------'''

            '''--------------------Создание таблицы акций--------------------'''
            shares_query_str: str = '''
            CREATE TABLE IF NOT EXISTS \"{0}\" (
            \"figi\" TEXT NOT NULL,
            \"ticker\" TEXT NOT NULL,
            \"class_code\" TEXT NOT NULL,
            \"isin\" TEXT NOT NULL,
            \"lot\" INTEGER NOT NULL,
            \"currency\" TEXT NOT NULL,
            \"klong\" TEXT NOT NULL,
            \"kshort\" TEXT NOT NULL,
            \"dlong\" TEXT NOT NULL,
            \"dshort\" TEXT NOT NULL,
            \"dlong_min\" TEXT NOT NULL,
            \"dshort_min\" TEXT NOT NULL,
            \"short_enabled_flag\" BLOB NOT NULL,
            \"name\" TEXT NOT NULL,
            \"exchange\" TEXT NOT NULL, 
            \"ipo_date\" TEXT NOT NULL,
            \"issue_size\" INTEGER NOT NULL,
            \"country_of_risk\" TEXT NOT NULL,
            \"country_of_risk_name\" TEXT NOT NULL,
            \"sector\" TEXT NOT NULL,
            \"issue_size_plan\" INTEGER NOT NULL,
            \"nominal\" TEXT NOT NULL,
            \"trading_status\" INTEGER NOT NULL,
            \"otc_flag\" BLOB NOT NULL,
            \"buy_available_flag\" BLOB NOT NULL,
            \"sell_available_flag\" BLOB NOT NULL,
            \"div_yield_flag\" BLOB NOT NULL,
            \"share_type\" INTEGER NOT NULL,
            \"min_price_increment\" TEXT NOT NULL,
            \"api_trade_available_flag\" BLOB NOT NULL,
            \"uid\" TEXT NOT NULL,
            \"real_exchange\" INTEGER NOT NULL,
            \"position_uid\" TEXT NOT NULL,
            \"for_iis_flag\" BLOB NOT NULL,
            \"for_qual_investor_flag\" BLOB NOT NULL,
            \"weekend_flag\" BLOB NOT NULL,
            \"blocked_tca_flag\" BLOB NOT NULL,
            \"liquidity_flag\" BLOB NOT NULL,
            \"first_1min_candle_date\" TEXT NOT NULL,
            \"first_1day_candle_date\" TEXT NOT NULL,
            \"dividends\" TEXT CHECK(\"dividends\" = \'Yes\' OR \"dividends\" = \'No\'),
            UNIQUE (\"uid\"),
            FOREIGN KEY (\"uid\") REFERENCES \"{1}\"(\"uid\") ON DELETE CASCADE
            );'''.format(MyConnection.SHARES_TABLE, MyConnection.INSTRUMENT_UIDS_TABLE)
            shares_query = QSqlQuery(db)
            shares_prepare_flag: bool = shares_query.prepare(shares_query_str)
            assert shares_prepare_flag, shares_query.lastError().text()
            shares_exec_flag: bool = shares_query.exec()
            assert shares_exec_flag, shares_query.lastError().text()
            '''--------------------------------------------------------------'''

            '''--------------------Триггер перед добавлением акции--------------------'''
            shares_bef_ins_trigger_query_str: str = '''
            CREATE TRIGGER IF NOT EXISTS \"{0}\" BEFORE INSERT ON \"{1}\"
            BEGIN             
                INSERT INTO \"{2}\"(\"uid\", \"instrument_type\") VALUES (\"NEW\".\"uid\", \'{3}\') ON CONFLICT(\"uid\") DO UPDATE SET \"instrument_type\" = \'{3}\';
            END;
            '''.format(
                MyConnection.SHARES_TRIGGER_BEFORE_INSERT,
                MyConnection.SHARES_TABLE,
                MyConnection.INSTRUMENT_UIDS_TABLE,
                'share'
            )
            shares_bef_ins_trigger_query = QSqlQuery(db)
            shares_bef_ins_trigger_prepare_flag: bool = shares_bef_ins_trigger_query.prepare(shares_bef_ins_trigger_query_str)
            assert shares_bef_ins_trigger_prepare_flag, shares_bef_ins_trigger_query.lastError().text()
            shares_before_insert_trigger_exec_flag: bool = shares_bef_ins_trigger_query.exec()
            assert shares_before_insert_trigger_exec_flag, shares_bef_ins_trigger_query.lastError().text()
            '''-----------------------------------------------------------------------'''

            '''-------------------Создание таблицы дивидендов-------------------'''
            dividends_query_str: str = '''
            CREATE TABLE IF NOT EXISTS \"{0}\" (
            \"instrument_uid\" TEXT NOT NULL,
            \"dividend_net\" TEXT NOT NULL,
            \"payment_date\" TEXT NOT NULL,
            \"declared_date\" TEXT NOT NULL,
            \"last_buy_date\" TEXT NOT NULL,
            \"dividend_type\" TEXT NOT NULL,
            \"record_date\" TEXT NOT NULL,
            \"regularity\" TEXT NOT NULL,
            \"close_price\" TEXT NOT NULL,
            \"yield_value\" TEXT NOT NULL,
            \"created_at\" TEXT NOT NULL,
            UNIQUE (\"instrument_uid\", \"dividend_net\", \"payment_date\", \"declared_date\", \"last_buy_date\", \"dividend_type\", \"record_date\", \"regularity\", \"close_price\", \"yield_value\", \"created_at\"),
            FOREIGN KEY (\"instrument_uid\") REFERENCES \"{1}\"(\"uid\") ON DELETE CASCADE
            );'''.format(MyConnection.DIVIDENDS_TABLE, MyConnection.SHARES_TABLE)
            dividends_query = QSqlQuery(db)
            dividends_prepare_flag: bool = dividends_query.prepare(dividends_query_str)
            assert dividends_prepare_flag, dividends_query.lastError().text()
            dividends_exec_flag: bool = dividends_query.exec()
            assert dividends_exec_flag, dividends_query.lastError().text()
            '''-----------------------------------------------------------------'''

            '''----------------Создание таблицы последних цен----------------'''
            last_prices_query_str: str = '''
            CREATE TABLE IF NOT EXISTS \"{0}\" (
            \"figi\" TEXT NOT NULL,
            \"price\" TEXT NOT NULL,
            \"time\" TEXT NOT NULL,
            \"instrument_uid\" TEXT NOT NULL,
            PRIMARY KEY (\"time\", \"instrument_uid\"),
            FOREIGN KEY (\"instrument_uid\") REFERENCES \"{1}\"(\"uid\") ON DELETE CASCADE
            );'''.format(MyConnection.LAST_PRICES_TABLE, MyConnection.INSTRUMENT_UIDS_TABLE)
            last_prices_query = QSqlQuery(db)
            last_prices_prepare_flag: bool = last_prices_query.prepare(last_prices_query_str)
            assert last_prices_prepare_flag, last_prices_query.lastError().text()
            last_prices_exec_flag: bool = last_prices_query.exec()
            assert last_prices_exec_flag, last_prices_query.lastError().text()
            '''--------------------------------------------------------------'''

            '''---------------Создание представления последних цен---------------'''
            last_prices_view_query_str: str = '''
            CREATE VIEW IF NOT EXISTS \"{0}\" (\"figi\", \"price\", \"time\", \"instrument_uid\") AS
            SELECT {1}.\"figi\" AS \"figi\", {1}.\"price\" AS \"price\", MAX({1}.\"time\") AS \"time\", {1}.\"instrument_uid\" AS \"instrument_uid\" 
            FROM {1} GROUP BY {1}.\"instrument_uid\"
            ;'''.format(MyConnection.LAST_PRICES_VIEW, '\"{0}\"'.format(MyConnection.LAST_PRICES_TABLE))
            last_prices_view_query = QSqlQuery(db)
            last_prices_view_prepare_flag: bool = last_prices_view_query.prepare(last_prices_view_query_str)
            assert last_prices_view_prepare_flag, last_prices_view_query.lastError().text()
            last_prices_view_exec_flag: bool = last_prices_view_query.exec()
            assert last_prices_view_exec_flag, last_prices_view_query.lastError().text()
            '''------------------------------------------------------------------'''

            '''---------------------Создание таблицы свечей---------------------'''
            candles_query_str: str = '''
            CREATE TABLE IF NOT EXISTS \"{0}\" (
            \"instrument_id\" TEXT NOT NULL,
            \"interval\" TEXT NOT NULL,
            \"open\" TEXT NOT NULL,
            \"high\" TEXT NOT NULL,
            \"low\" TEXT NOT NULL,
            \"close\" TEXT NOT NULL,
            \"volume\" INTEGER NOT NULL,
            \"time\" TEXT NOT NULL,
            \"is_complete\"	BLOB NOT NULL,
            UNIQUE (\"instrument_id\", \"interval\", \"time\"),
            FOREIGN KEY (\"instrument_id\") REFERENCES \"{1}\"(\"uid\") ON DELETE CASCADE
            );'''.format(MyConnection.CANDLES_TABLE, MyConnection.INSTRUMENT_UIDS_TABLE)
            candles_query = QSqlQuery(db)
            candles_prepare_flag: bool = candles_query.prepare(candles_query_str)
            assert candles_prepare_flag, candles_query.lastError().text()
            candles_exec_flag: bool = candles_query.exec()
            assert candles_exec_flag, candles_query.lastError().text()
            '''-----------------------------------------------------------------'''

            # '''------------Триггер перед добавлением исторической свечи------------'''
            # candles_before_insert_trigger_query = QSqlQuery(db)
            # candles_before_insert_trigger_query.prepare('''
            # CREATE TRIGGER IF NOT EXISTS {0} BEFORE INSERT ON {1}
            # BEGIN
            #
            # END;
            # '''.format(
            #     '\"{0}\"'.format(MyConnection.CANDLES_TRIGGER_BEFORE_INSERT),
            #     '\"{0}\"'.format(MyConnection.CANDLES_TABLE)
            # ))
            # candles_before_insert_trigger_exec_flag: bool = candles_before_insert_trigger_query.exec()
            # assert candles_before_insert_trigger_exec_flag, candles_before_insert_trigger_query.lastError().text()
            # '''--------------------------------------------------------------------'''

            '''-------------------Создание таблицы брэндов-------------------'''
            brands_sql_command: str = '''
            CREATE TABLE IF NOT EXISTS \"{0}\" (
            \"uid\" TEXT NOT NULL,
            \"name\" TEXT NOT NULL,
            \"description\" TEXT NOT NULL,
            \"info\" TEXT NOT NULL,
            \"company\" TEXT NOT NULL,
            \"sector\" TEXT NOT NULL,
            \"country_of_risk\" TEXT NOT NULL,
            \"country_of_risk_name\" TEXT NOT NULL,         
            PRIMARY KEY (\"uid\")
            );'''.format(MyConnection.BRANDS_TABLE)
            brands_query = QSqlQuery(db)
            brands_prepare_flag: bool = brands_query.prepare(brands_sql_command)
            assert brands_prepare_flag, brands_query.lastError().text()
            brands_exec_flag: bool = brands_query.exec()
            assert brands_exec_flag, brands_query.lastError().text()
            '''--------------------------------------------------------------'''

            '''-------------------Создание таблицы активов-------------------'''
            assets_sql_command: str = '''
            CREATE TABLE IF NOT EXISTS \"{0}\" (
            \"uid\" TEXT NOT NULL PRIMARY KEY,
            \"type\" TEXT NOT NULL CHECK(\"type\" = \'ASSET_TYPE_UNSPECIFIED\' OR \"type\" = \'ASSET_TYPE_CURRENCY\' OR \"type\" = \'ASSET_TYPE_COMMODITY\' OR \"type\" = \'ASSET_TYPE_INDEX\' OR \"type\" = \'ASSET_TYPE_SECURITY\'),
            \"name\" TEXT NOT NULL,
            \"name_brief\" TEXT, 
            \"description\" TEXT,
            \"deleted_at\" TEXT,
            \"required_tests\" TEXT,
            \"security\",
            \"gos_reg_code\" TEXT,
            \"cfi\" TEXT,
            \"code_nsd\" TEXT,
            \"status\" TEXT,
            \"brand_uid\" TEXT,
            \"updated_at\" TEXT,
            \"br_code\" TEXT,
            \"br_code_name\" TEXT,
            FOREIGN KEY (\"brand_uid\") REFERENCES \"{1}\"(\"uid\")
            );'''.format(MyConnection.ASSETS_TABLE, MyConnection.BRANDS_TABLE)
            assets_query = QSqlQuery(db)
            assets_prepare_flag: bool = assets_query.prepare(assets_sql_command)
            assert assets_prepare_flag, assets_query.lastError().text()
            assets_exec_flag: bool = assets_query.exec()
            assert assets_exec_flag, assets_query.lastError().text()
            '''--------------------------------------------------------------'''

            '''--------------Создание таблицы AssetInstruments--------------'''
            instrument_kind_column_name: str = '\"instrument_kind\"'
            instrument_kind_keys = InstrumentType.__members__.keys()
            instrument_kind_check_str: str = ''
            if len(instrument_kind_keys) > 0:
                instrument_kind_check_str += ' CHECK('
                for i, key in enumerate(instrument_kind_keys):
                    if i > 0: instrument_kind_check_str += ' OR '
                    instrument_kind_check_str += '{0} = \'{1}\''.format(instrument_kind_column_name, key)
                instrument_kind_check_str += ')'

            asset_instruments_sql_command: str = '''
            CREATE TABLE IF NOT EXISTS \"{0}\" (
            \"asset_uid\" TEXT NOT NULL,
            \"uid\" TEXT NOT NULL,
            \"figi\" TEXT NOT NULL,
            \"instrument_type\" TEXT NOT NULL,
            \"ticker\" TEXT NOT NULL,
            \"class_code\" TEXT NOT NULL,
            {2} TEXT NOT NULL{3},
            \"position_uid\" TEXT NOT NULL,
            CONSTRAINT \"asset_instrument_pk\" PRIMARY KEY(\"asset_uid\", \"uid\"),
            FOREIGN KEY (\"asset_uid\") REFERENCES \"{1}\"(\"uid\") ON DELETE CASCADE
            );'''.format(
                MyConnection.ASSET_INSTRUMENTS_TABLE,
                MyConnection.ASSETS_TABLE,
                instrument_kind_column_name,
                instrument_kind_check_str
            )
            asset_instruments_query = QSqlQuery(db)
            asset_instruments_prepare_flag: bool = asset_instruments_query.prepare(asset_instruments_sql_command)
            assert asset_instruments_prepare_flag, asset_instruments_query.lastError().text()
            asset_instruments_exec_flag: bool = asset_instruments_query.exec()
            assert asset_instruments_exec_flag, asset_instruments_query.lastError().text()
            '''-------------------------------------------------------------'''

            '''----------------Создание таблицы InstrumentLinks----------------'''
            instrument_links_query_str: str = '''
            CREATE TABLE IF NOT EXISTS \"{0}\" (
            \"asset_uid\" TEXT NOT NULL,
            \"asset_instrument_uid\" TEXT NOT NULL,
            \"type\" TEXT NOT NULL,
            \"linked_instrument_uid\" TEXT NOT NULL,
            UNIQUE (\"asset_uid\", \"asset_instrument_uid\", \"type\", \"linked_instrument_uid\"),
            FOREIGN KEY (\"asset_uid\", \"asset_instrument_uid\") REFERENCES \"{1}\"(\"asset_uid\", \"uid\") ON DELETE CASCADE
            );'''.format(MyConnection.INSTRUMENT_LINKS_TABLE, MyConnection.ASSET_INSTRUMENTS_TABLE)
            instrument_links_query = QSqlQuery(db)
            instrument_links_prepare_flag: bool = instrument_links_query.prepare(instrument_links_query_str)
            assert instrument_links_prepare_flag, instrument_links_query.lastError().text()
            instrument_links_exec_flag: bool = instrument_links_query.exec()
            assert instrument_links_exec_flag, instrument_links_query.lastError().text()
            '''----------------------------------------------------------------'''

            '''------------------Создание таблицы AssetCurrencies------------------'''
            asset_currencies_sql_command: str = '''
            CREATE TABLE IF NOT EXISTS \"{0}\" (
            \"asset_uid\" TEXT NOT NULL,
            \"base_currency\" TEXT NOT NULL,
            UNIQUE (\"asset_uid\"),
            FOREIGN KEY (\"asset_uid\") REFERENCES \"{1}\"(\"uid\") ON DELETE CASCADE
            );'''.format(MyConnection.ASSET_CURRENCIES_TABLE, MyConnection.ASSETS_TABLE)
            asset_currencies_query = QSqlQuery(db)
            asset_currencies_prepare_flag: bool = asset_currencies_query.prepare(asset_currencies_sql_command)
            assert asset_currencies_prepare_flag, asset_currencies_query.lastError().text()
            asset_currencies_exec_flag: bool = asset_currencies_query.exec()
            assert asset_currencies_exec_flag, asset_currencies_query.lastError().text()
            '''--------------------------------------------------------------------'''

            '''-----------Добавление триггера перед обновлением актива-----------'''
            # '''
            # SELECT
            # CASE
            #     WHEN \"NEW\".\"type\" != \"OLD\".\"type\" AND \"OLD\".\"type\" = \'{3}\'
            #         THEN DELETE FROM \"{4}\" WHERE \"asset_uid\" = \"OLD\".\"uid\"
            # END;
            # '''

            # '''
            # DELETE FROM \"{4}\" WHERE \"asset_uid\" = \"OLD\".\"uid\" AND \"OLD\".\"uid\" IN (SELECT
            #     CASE
            #         WHEN \"NEW\".\"type\" != \"OLD\".\"type\" AND \"OLD\".\"type\" = \'{3}\'
            #             THEN \"OLD\".\"uid\"
            #     END);
            # '''

            assets_on_update_trigger_query_str: str = '''
            CREATE TRIGGER IF NOT EXISTS \"{0}\" BEFORE UPDATE ON \"{1}\"
            BEGIN 
                DELETE FROM \"{4}\" WHERE \"asset_uid\" = \"OLD\".\"uid\" AND \"OLD\".\"uid\" IN (SELECT
                    CASE
                        WHEN \"NEW\".\"type\" != \"OLD\".\"type\" AND \"OLD\".\"type\" = \'{3}\'
                            THEN \"OLD\".\"uid\"
                    END);
                  
                DELETE FROM \"{2}\" WHERE \"asset_uid\" = \"OLD\".\"uid\";
            END;'''.format(
                MyConnection.ASSETS_BEFORE_UPDATE_TRIGGER,
                MyConnection.ASSETS_TABLE,
                MyConnection.ASSET_INSTRUMENTS_TABLE,
                AssetType.ASSET_TYPE_CURRENCY.name,
                MyConnection.ASSET_CURRENCIES_TABLE
            )
            assets_on_update_trigger_query = QSqlQuery(db)
            assets_on_update_trigger_prepare_flag: bool = assets_on_update_trigger_query.prepare(assets_on_update_trigger_query_str)
            assert assets_on_update_trigger_prepare_flag, assets_on_update_trigger_query.lastError().text()
            assets_on_update_trigger_exec_flag: bool = assets_on_update_trigger_query.exec()
            assert assets_on_update_trigger_exec_flag, assets_on_update_trigger_query.lastError().text()
            '''------------------------------------------------------------------'''

            '''--------------------Создание таблицы AssetSecurities--------------------'''
            asset_securities_sql_command: str = '''
            CREATE TABLE IF NOT EXISTS \"{0}\" (
            \"asset_uid\" TEXT NOT NULL,
            \"isin\" TEXT NOT NULL,
            \"type\" TEXT NOT NULL,
            {1} TEXT NOT NULL{2},
            UNIQUE (\"asset_uid\"),
            FOREIGN KEY (\"asset_uid\") REFERENCES \"{3}\"(\"uid\") ON DELETE CASCADE
            );'''.format(
                MyConnection.ASSET_SECURITIES_TABLE,
                instrument_kind_column_name,
                instrument_kind_check_str,
                MyConnection.ASSETS_TABLE
            )
            asset_securities_query = QSqlQuery(db)
            asset_securities_prepare_flag: bool = asset_securities_query.prepare(asset_securities_sql_command)
            assert asset_securities_prepare_flag, asset_securities_query.lastError().text()
            asset_securities_exec_flag: bool = asset_securities_query.exec()
            assert asset_securities_exec_flag, asset_securities_query.lastError().text()
            '''------------------------------------------------------------------------'''

            '''--------------------Создание таблицы запросов инструментов--------------------'''
            instruments_status_query_str: str = '''
            CREATE TABLE IF NOT EXISTS \"{0}\" (
            \"token\" TEXT NOT NULL,
            \"status\" TEXT NOT NULL CHECK(\"status\" = 'INSTRUMENT_STATUS_UNSPECIFIED' OR \"status\" = 'INSTRUMENT_STATUS_BASE' OR \"status\" = 'INSTRUMENT_STATUS_ALL'),
            \"uid\" TEXT NOT NULL,
            UNIQUE (\"token\", \"status\", \"uid\"),
            FOREIGN KEY (\"token\") REFERENCES \"{1}\"(\"token\") ON DELETE CASCADE,
            FOREIGN KEY (\"uid\") REFERENCES \"{2}\"(\"uid\") ON DELETE CASCADE
            );'''.format(MyConnection.INSTRUMENT_STATUS_TABLE, MyConnection.TOKENS_TABLE, MyConnection.INSTRUMENT_UIDS_TABLE)
            instruments_status_query = QSqlQuery(db)
            instruments_status_prepare_flag: bool = instruments_status_query.prepare(instruments_status_query_str)
            assert instruments_status_prepare_flag, instruments_status_query.lastError().text()
            instruments_status_exec_flag: bool = instruments_status_query.exec()
            assert instruments_status_exec_flag, instruments_status_query.lastError().text()
            '''------------------------------------------------------------------------------'''

            '''------------------------Создание таблицы прогнозов------------------------'''
            target_items_query_str: str = '''
            CREATE TABLE IF NOT EXISTS \"{0}\" (
            \"uid\" TEXT NOT NULL,
            \"ticker\" TEXT NOT NULL,
            \"company\" TEXT NOT NULL,
            \"recommendation\" TEXT NOT NULL CHECK(\"recommendation\" = 'RECOMMENDATION_UNSPECIFIED' OR \"recommendation\" = 'RECOMMENDATION_BUY' OR \"recommendation\" = 'RECOMMENDATION_HOLD' OR \"recommendation\" = 'RECOMMENDATION_SELL'),
            \"recommendation_date\" TEXT NOT NULL,
            \"currency\" TEXT NOT NULL,
            \"current_price\" TEXT NOT NULL,
            \"target_price\" TEXT NOT NULL,
            \"price_change\" TEXT NOT NULL,
            \"price_change_rel\" TEXT NOT NULL,
            \"show_name\" TEXT NOT NULL,
            UNIQUE (\"uid\", \"company\", \"recommendation_date\"),
            FOREIGN KEY (\"uid\") REFERENCES \"{1}\"(\"uid\") ON DELETE CASCADE
            );'''.format(MyConnection.TARGET_ITEMS_TABLE, MyConnection.INSTRUMENT_UIDS_TABLE)
            target_items_query = QSqlQuery(db)
            target_items_prepare_flag: bool = target_items_query.prepare(target_items_query_str)
            assert target_items_prepare_flag, target_items_query.lastError().text()
            target_items_exec_flag: bool = target_items_query.exec()
            assert target_items_exec_flag, target_items_query.lastError().text()
            '''--------------------------------------------------------------------------'''

            '''-------------------Создание таблицы консенсус-прогнозов-------------------'''
            consensus_items_query_str: str = '''
            CREATE TABLE IF NOT EXISTS \"{0}\" (
            \"uid\" TEXT NOT NULL,
            \"ticker\" TEXT NOT NULL,
            \"recommendation\" TEXT NOT NULL CHECK(\"recommendation\" = 'RECOMMENDATION_UNSPECIFIED' OR \"recommendation\" = 'RECOMMENDATION_BUY' OR \"recommendation\" = 'RECOMMENDATION_HOLD' OR \"recommendation\" = 'RECOMMENDATION_SELL'),
            \"currency\" TEXT NOT NULL,
            \"current_price\" TEXT NOT NULL,
            \"consensus\" TEXT NOT NULL,
            \"min_target\" TEXT NOT NULL,
            \"max_target\" TEXT NOT NULL,
            \"price_change\" TEXT NOT NULL,
            \"price_change_rel\" TEXT NOT NULL,
            UNIQUE (\"uid\"),
            FOREIGN KEY (\"uid\") REFERENCES \"{1}\"(\"uid\") ON DELETE CASCADE
            );'''.format(MyConnection.CONSENSUS_ITEMS_TABLE, MyConnection.INSTRUMENT_UIDS_TABLE)
            consensus_items_query = QSqlQuery(db)
            consensus_items_prepare_flag: bool = consensus_items_query.prepare(consensus_items_query_str)
            assert consensus_items_prepare_flag, consensus_items_query.lastError().text()
            consensus_items_exec_flag: bool = consensus_items_query.exec()
            assert consensus_items_exec_flag, consensus_items_query.lastError().text()
            '''--------------------------------------------------------------------------'''

            commit_flag: bool = db.commit()  # Фиксирует транзакцию в базу данных.
            assert commit_flag, db.lastError().text()

    @classmethod
    def addNewToken(cls, token: TokenClass):
        """Добавляет новый токен в таблицу токенов."""
        db: QSqlDatabase = cls.getDatabase()

        transaction_flag: bool = db.transaction()  # Начинает транзакцию в базе данных.
        assert transaction_flag, db.lastError().text()

        if transaction_flag:
            tokens_query = QSqlQuery(db)
            tokens_prepare_flag: bool = tokens_query.prepare('INSERT INTO {0} (\"token\", \"name\") VALUES (:token, :name);'.format('\"{0}\"'.format(MyConnection.TOKENS_TABLE)))
            assert tokens_prepare_flag, tokens_query.lastError().text()
            tokens_query.bindValue(':token', token.token)
            tokens_query.bindValue(':name', token.name)
            tokens_exec_flag: bool = tokens_query.exec()
            assert tokens_exec_flag, tokens_query.lastError().text()

            for unary_limit in token.unary_limits:
                unary_limit_query = QSqlQuery(db)
                unary_limit_prepare_flag: bool = unary_limit_query.prepare('''
                INSERT INTO \"{0}\" (\"token\", \"limit_per_minute\", \"methods\") 
                VALUES (:token, :limit_per_minute, :methods);
                '''.format(MyConnection.UNARY_LIMITS_TABLE))
                assert unary_limit_prepare_flag, unary_limit_query.lastError().text()
                unary_limit_query.bindValue(':token', token.token)
                unary_limit_query.bindValue(':limit_per_minute', unary_limit.limit_per_minute)
                unary_limit_query.bindValue(':methods', cls.convertStrListToStr([method.full_method for method in unary_limit.methods]))
                unary_limit_exec_flag: bool = unary_limit_query.exec()
                assert unary_limit_exec_flag, unary_limit_query.lastError().text()

            for stream_limit in token.stream_limits:
                stream_limit_query = QSqlQuery(db)
                stream_limit_prepare_flag: bool = stream_limit_query.prepare('''
                INSERT INTO \"{0}\" (\"token\", \"limit_count\", \"streams\", \"open\") 
                VALUES (:token, :limit_count, :streams, :open);
                '''.format(MyConnection.STREAM_LIMITS_TABLE))
                assert stream_limit_prepare_flag, stream_limit_query.lastError().text()
                stream_limit_query.bindValue(':token', token.token)
                stream_limit_query.bindValue(':limit_count', stream_limit.limit)
                stream_limit_query.bindValue(':streams', cls.convertStrListToStr([method.full_method for method in stream_limit.methods]))
                stream_limit_query.bindValue(':open', stream_limit.open)
                stream_limit_exec_flag: bool = stream_limit_query.exec()
                assert stream_limit_exec_flag, stream_limit_query.lastError().text()

            for account in token.accounts:
                query = QSqlQuery(db)
                query.prepare('''
                INSERT INTO "Accounts" ("token", "id", "type", "name", "status", "opened_date", "closed_date", "access_level")
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
            assert commit_flag, db.lastError().text()

    @classmethod
    def deleteToken(cls, token: str):
        """Удаляет токен и все связанные с ним данные."""
        db: QSqlDatabase = cls.getDatabase()
        query = QSqlQuery(db)
        prepare_flag: bool = query.prepare('DELETE FROM \"{0}\" WHERE \"token\" = :token;'.format(MyConnection.TOKENS_TABLE))
        assert prepare_flag, query.lastError().text()
        query.bindValue(':token', token)
        exec_flag: bool = query.exec()
        assert exec_flag, query.lastError().text()

    @classmethod
    def addBonds(cls, token: str, instrument_status: InstrumentStatus, bonds: list[Bond]):
        """Добавляет облигации в таблицу облигаций."""
        if bonds:  # Если список облигаций не пуст.
            db: QSqlDatabase = cls.getDatabase()
            transaction_flag: bool = db.transaction()  # Начинает транзакцию в базе данных.
            if transaction_flag:
                VARIABLES_COUNT: int = 50  # Количество variables в каждом insert.
                bonds_in_pack: int = int(cls.VARIABLE_LIMIT / VARIABLES_COUNT)
                assert bonds_in_pack > 0

                bonds_insert_sql_command_begin: str = '''INSERT INTO \"{0}\"(
                \"figi\", \"ticker\", \"class_code\", \"isin\", \"lot\", \"currency\", \"klong\", \"kshort\", \"dlong\", 
                \"dshort\", \"dlong_min\", \"dshort_min\", \"short_enabled_flag\", \"name\", \"exchange\", 
                \"coupon_quantity_per_year\", \"maturity_date\", \"nominal\", \"initial_nominal\", \"state_reg_date\", 
                \"placement_date\", \"placement_price\", \"aci_value\", \"country_of_risk\", \"country_of_risk_name\", 
                \"sector\", \"issue_kind\", \"issue_size\", \"issue_size_plan\", \"trading_status\", \"otc_flag\", 
                \"buy_available_flag\", \"sell_available_flag\", \"floating_coupon_flag\", \"perpetual_flag\", 
                \"amortization_flag\", \"min_price_increment\", \"api_trade_available_flag\", \"uid\", 
                \"real_exchange\", \"position_uid\", \"for_iis_flag\", \"for_qual_investor_flag\", \"weekend_flag\", 
                \"blocked_tca_flag\", \"subordinated_flag\", \"liquidity_flag\", \"first_1min_candle_date\", 
                \"first_1day_candle_date\", \"risk_level\") VALUES '''.format(MyConnection.BONDS_TABLE)

                bonds_insert_sql_command_middle: str = '''(
                :figi{0}, :ticker{0}, :class_code{0}, :isin{0}, :lot{0}, :currency{0}, :klong{0}, :kshort{0}, 
                :dlong{0}, :dshort{0}, :dlong_min{0}, :dshort_min{0}, :short_enabled_flag{0}, :name{0}, 
                :exchange{0}, :coupon_quantity_per_year{0}, :maturity_date{0}, :nominal{0}, :initial_nominal{0}, 
                :state_reg_date{0}, :placement_date{0}, :placement_price{0}, :aci_value{0}, :country_of_risk{0}, 
                :country_of_risk_name{0}, :sector{0}, :issue_kind{0}, :issue_size{0}, :issue_size_plan{0}, 
                :trading_status{0}, :otc_flag{0}, :buy_available_flag{0}, :sell_available_flag{0}, 
                :floating_coupon_flag{0}, :perpetual_flag{0}, :amortization_flag{0}, :min_price_increment{0}, 
                :api_trade_available_flag{0}, :uid{0}, :real_exchange{0}, :position_uid{0}, :for_iis_flag{0}, 
                :for_qual_investor_flag{0}, :weekend_flag{0}, :blocked_tca_flag{0}, :subordinated_flag{0}, 
                :liquidity_flag{0}, :first_1min_candle_date{0}, :first_1day_candle_date{0}, :risk_level{0}
                )'''

                bonds_insert_sql_command_end: str = ''' ON CONFLICT(\"uid\") DO UPDATE SET \"figi\" = {0}.\"figi\", 
                \"ticker\" = {0}.\"ticker\", \"class_code\" = {0}.\"class_code\", \"isin\" = {0}.\"isin\", 
                \"lot\" = {0}.\"lot\", \"currency\" = {0}.\"currency\", \"klong\" = {0}.\"klong\", 
                \"kshort\" = {0}.\"kshort\", \"dlong\" = {0}.\"dlong\", \"dshort\" = {0}.\"dshort\", 
                \"dlong_min\" = {0}.\"dlong_min\", \"dshort_min\" = {0}.\"dshort_min\", 
                \"short_enabled_flag\" = {0}.\"short_enabled_flag\", \"name\" = {0}.\"name\", 
                \"exchange\" = {0}.\"exchange\", \"coupon_quantity_per_year\" = {0}.\"coupon_quantity_per_year\", 
                \"maturity_date\" = {0}.\"maturity_date\", \"nominal\" = {0}.\"nominal\", 
                \"initial_nominal\" = {0}.\"initial_nominal\", \"state_reg_date\" = {0}.\"state_reg_date\", 
                \"placement_date\" = {0}.\"placement_date\", \"placement_price\" = {0}.\"placement_price\", 
                \"aci_value\" = {0}.\"aci_value\", \"country_of_risk\" = {0}.\"country_of_risk\", 
                \"country_of_risk_name\" = {0}.\"country_of_risk_name\", \"sector\" = {0}.\"sector\", 
                \"issue_kind\" = {0}.\"issue_kind\", \"issue_size\" = {0}.\"issue_size\", 
                \"issue_size_plan\" = {0}.\"issue_size_plan\", \"trading_status\" = {0}.\"trading_status\", 
                \"otc_flag\" = {0}.\"otc_flag\", \"buy_available_flag\" = {0}.\"buy_available_flag\", 
                \"sell_available_flag\" = {0}.\"sell_available_flag\", 
                \"floating_coupon_flag\" = {0}.\"floating_coupon_flag\", 
                \"perpetual_flag\" = {0}.\"perpetual_flag\", \"amortization_flag\" = {0}.\"amortization_flag\", 
                \"min_price_increment\" = {0}.\"min_price_increment\", 
                \"api_trade_available_flag\" = {0}.\"api_trade_available_flag\", 
                \"real_exchange\" = {0}.\"real_exchange\", \"position_uid\" = {0}.\"position_uid\", 
                \"for_iis_flag\" = {0}.\"for_iis_flag\", \"for_qual_investor_flag\" = {0}.\"for_qual_investor_flag\", 
                \"weekend_flag\" = {0}.\"weekend_flag\", \"blocked_tca_flag\" = {0}.\"blocked_tca_flag\", 
                \"subordinated_flag\" = {0}.\"subordinated_flag\", \"liquidity_flag\" = {0}.\"liquidity_flag\", 
                \"first_1min_candle_date\" = {0}.\"first_1min_candle_date\", 
                \"first_1day_candle_date\" = {0}.\"first_1day_candle_date\", \"risk_level\" = {0}.\"risk_level\"
                ;'''.format('\"excluded\"')

                bonds_packs: list[list[Bond]] = partition(bonds, bonds_in_pack)
                for pack in bonds_packs:
                    '''-----------Создание sql-запроса для текущей части вставляемых облигаций-----------'''
                    bonds_insert_sql_command: str = bonds_insert_sql_command_begin
                    for i in range(len(pack)):
                        if i > 0: bonds_insert_sql_command += ', '  # Если добавляемая облигация не первая.
                        bonds_insert_sql_command += bonds_insert_sql_command_middle.format(i)
                    bonds_insert_sql_command += bonds_insert_sql_command_end
                    '''----------------------------------------------------------------------------------'''

                    query = QSqlQuery(db)
                    bonds_insert_prepare_flag: bool = query.prepare(bonds_insert_sql_command)
                    assert bonds_insert_prepare_flag, query.lastError().text()

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

                    bonds_insert_exec_flag: bool = query.exec()
                    assert bonds_insert_exec_flag, query.lastError().text()

                """===============Добавляем облигации в таблицу запросов инструментов==============="""
                '''--------------Удаляем облигации из таблицы запросов инструментов--------------'''
                bonds_uids_select: str = '''
                SELECT \"uid\" FROM \"{0}\" WHERE \"{0}\".\"instrument_type\" = \'{1}\'
                '''.format(MyConnection.INSTRUMENT_UIDS_TABLE, 'bond')

                instruments_status_delete_sql_command: str = '''
                DELETE FROM \"{0}\" WHERE \"token\" = :token AND \"status\" = :status AND \"uid\" in ({1});
                '''.format(MyConnection.INSTRUMENT_STATUS_TABLE, bonds_uids_select)

                instruments_status_delete_query = QSqlQuery(db)
                instruments_status_delete_prepare_flag: bool = instruments_status_delete_query.prepare(instruments_status_delete_sql_command)
                assert instruments_status_delete_prepare_flag, instruments_status_delete_query.lastError().text()
                instruments_status_delete_query.bindValue(':token', token)
                instruments_status_delete_query.bindValue(':status', instrument_status.name)
                instruments_status_delete_exec_flag: bool = instruments_status_delete_query.exec()
                assert instruments_status_delete_exec_flag, instruments_status_delete_query.lastError().text()
                '''------------------------------------------------------------------------------'''

                '''-------------Добавляем облигации в таблицу запросов инструментов-------------'''
                instruments_status_insert_sql_command: str = '''
                INSERT INTO \"{0}\" (\"token\", \"status\", \"uid\") VALUES (:token, :status, :uid);
                '''.format(MyConnection.INSTRUMENT_STATUS_TABLE)

                for bond in bonds:
                    instruments_status_insert_query = QSqlQuery(db)
                    instruments_status_insert_prepare_flag: bool = instruments_status_insert_query.prepare(instruments_status_insert_sql_command)
                    assert instruments_status_insert_prepare_flag, instruments_status_insert_query.lastError().text()

                    instruments_status_insert_query.bindValue(':token', token)
                    instruments_status_insert_query.bindValue(':status', instrument_status.name)
                    instruments_status_insert_query.bindValue(':uid', bond.uid)

                    instruments_status_insert_exec_flag: bool = instruments_status_insert_query.exec()
                    assert instruments_status_insert_exec_flag, instruments_status_insert_query.lastError().text()
                '''-----------------------------------------------------------------------------'''
                """================================================================================="""

                commit_flag: bool = db.commit()  # Фиксирует транзакцию в базу данных.
                assert commit_flag, db.lastError().text()
            else:
                assert transaction_flag, db.lastError().text()

    @classmethod
    def addShares(cls, token: str, instrument_status: InstrumentStatus, shares: list[Share]):
        """Добавляет акции в таблицу акций."""
        if shares:  # Если список акций не пуст.
            sql_command: str = '''INSERT INTO \"{0}\" (
            \"figi\", \"ticker\", \"class_code\", \"isin\", \"lot\", \"currency\", \"klong\", \"kshort\", 
            \"dlong\", \"dshort\", \"dlong_min\", \"dshort_min\", \"short_enabled_flag\", \"name\", 
            \"exchange\", \"ipo_date\", \"issue_size\", \"country_of_risk\", \"country_of_risk_name\", 
            \"sector\", \"issue_size_plan\", \"nominal\", \"trading_status\", \"otc_flag\", 
            \"buy_available_flag\", \"sell_available_flag\", \"div_yield_flag\", \"share_type\", 
            \"min_price_increment\", \"api_trade_available_flag\", \"uid\", \"real_exchange\", 
            \"position_uid\", \"for_iis_flag\", \"for_qual_investor_flag\", \"weekend_flag\", 
            \"blocked_tca_flag\", \"liquidity_flag\", \"first_1min_candle_date\", \"first_1day_candle_date\") 
            VALUES (
            :figi, :ticker, :class_code, :isin, :lot, :currency, :klong, :kshort, :dlong, :dshort, :dlong_min, 
            :dshort_min, :short_enabled_flag, :name, :exchange, :ipo_date, :issue_size, :country_of_risk, 
            :country_of_risk_name, :sector, :issue_size_plan, :nominal, :trading_status, :otc_flag, 
            :buy_available_flag, :sell_available_flag, :div_yield_flag, :share_type, :min_price_increment, 
            :api_trade_available_flag, :uid, :real_exchange, :position_uid, :for_iis_flag, 
            :for_qual_investor_flag, :weekend_flag, :blocked_tca_flag, :liquidity_flag, 
            :first_1min_candle_date, :first_1day_candle_date 
            ) ON CONFLICT(\"uid\") DO 
            UPDATE SET \"figi\" = {1}.\"figi\", \"ticker\" = {1}.\"ticker\", \"class_code\" = {1}.\"class_code\", 
            \"isin\" = {1}.\"isin\", \"lot\" = {1}.\"lot\", \"currency\" = {1}.\"currency\", \"klong\" = {1}.\"klong\", 
            \"kshort\" = {1}.\"kshort\", \"dlong\" = {1}.\"dlong\", \"dshort\" = {1}.\"dshort\", 
            \"dlong_min\" = {1}.\"dlong_min\", \"dshort_min\" = {1}.\"dshort_min\", 
            \"short_enabled_flag\" = {1}.\"short_enabled_flag\", \"name\" = {1}.\"name\", 
            \"exchange\" = {1}.\"exchange\", \"exchange\" = {1}.\"exchange\", \"ipo_date\" = {1}.\"ipo_date\", 
            \"issue_size\" = {1}.\"issue_size\", \"country_of_risk\" = {1}.\"country_of_risk\", 
            \"country_of_risk_name\" = {1}.\"country_of_risk_name\", \"sector\" = {1}.\"sector\", 
            \"issue_size_plan\" = {1}.\"issue_size_plan\", \"nominal\" = {1}.\"nominal\", 
            \"trading_status\" = {1}.\"trading_status\", \"otc_flag\" = {1}.\"otc_flag\", 
            \"buy_available_flag\" = {1}.\"buy_available_flag\", \"sell_available_flag\" = {1}.\"sell_available_flag\", 
            \"div_yield_flag\" = {1}.\"div_yield_flag\", \"share_type\" = {1}.\"share_type\", 
            \"min_price_increment\" = {1}.\"min_price_increment\", 
            \"api_trade_available_flag\" = {1}.\"api_trade_available_flag\", \"real_exchange\" = {1}.\"real_exchange\", 
            \"position_uid\" = {1}.\"position_uid\", \"for_iis_flag\" = {1}.\"for_iis_flag\", 
            \"for_qual_investor_flag\" = {1}.\"for_qual_investor_flag\", \"weekend_flag\" = {1}.\"weekend_flag\", 
            \"blocked_tca_flag\" = {1}.\"blocked_tca_flag\", \"liquidity_flag\" = {1}.\"liquidity_flag\", 
            \"first_1min_candle_date\" = {1}.\"first_1min_candle_date\", 
            \"first_1day_candle_date\" = {1}.\"first_1day_candle_date\";
            '''.format(MyConnection.SHARES_TABLE, '\"excluded\"')

            db: QSqlDatabase = cls.getDatabase()
            transaction_flag: bool = db.transaction()  # Начинает транзакцию в базе данных.
            if transaction_flag:
                for share in shares:
                    query = QSqlQuery(db)
                    prepare_flag: bool = query.prepare(sql_command)
                    assert prepare_flag, query.lastError().text()

                    query.bindValue(':figi', share.figi)
                    query.bindValue(':ticker', share.ticker)
                    query.bindValue(':class_code', share.class_code)
                    query.bindValue(':isin', share.isin)
                    query.bindValue(':lot', share.lot)
                    query.bindValue(':currency', share.currency)
                    query.bindValue(':klong', MyQuotation.__repr__(share.klong))
                    query.bindValue(':kshort', MyQuotation.__repr__(share.kshort))
                    query.bindValue(':dlong', MyQuotation.__repr__(share.dlong))
                    query.bindValue(':dshort', MyQuotation.__repr__(share.dshort))
                    query.bindValue(':dlong_min', MyQuotation.__repr__(share.dlong_min))
                    query.bindValue(':dshort_min', MyQuotation.__repr__(share.dshort_min))
                    query.bindValue(':short_enabled_flag', share.short_enabled_flag)
                    query.bindValue(':name', share.name)
                    query.bindValue(':exchange', share.exchange)
                    query.bindValue(':ipo_date', MyConnection.convertDateTimeToText(share.ipo_date))
                    query.bindValue(':issue_size', share.issue_size)
                    query.bindValue(':country_of_risk', share.country_of_risk)
                    query.bindValue(':country_of_risk_name', share.country_of_risk_name)
                    query.bindValue(':sector', share.sector)
                    query.bindValue(':issue_size_plan', share.issue_size_plan)
                    query.bindValue(':nominal', MyMoneyValue.__repr__(share.nominal))
                    query.bindValue(':trading_status', int(share.trading_status))
                    query.bindValue(':otc_flag', share.otc_flag)
                    query.bindValue(':buy_available_flag', share.buy_available_flag)
                    query.bindValue(':sell_available_flag', share.sell_available_flag)
                    query.bindValue(':div_yield_flag', share.div_yield_flag)
                    query.bindValue(':share_type', int(share.share_type))
                    query.bindValue(':min_price_increment', MyQuotation.__repr__(share.min_price_increment))
                    query.bindValue(':api_trade_available_flag', share.api_trade_available_flag)
                    query.bindValue(':uid', share.uid)
                    query.bindValue(':real_exchange', int(share.real_exchange))
                    query.bindValue(':position_uid', share.position_uid)
                    query.bindValue(':for_iis_flag', share.for_iis_flag)
                    query.bindValue(':for_qual_investor_flag', share.for_qual_investor_flag)
                    query.bindValue(':weekend_flag', share.weekend_flag)
                    query.bindValue(':blocked_tca_flag', share.blocked_tca_flag)
                    query.bindValue(':liquidity_flag', share.liquidity_flag)
                    query.bindValue(':first_1min_candle_date', MyConnection.convertDateTimeToText(share.first_1min_candle_date))
                    query.bindValue(':first_1day_candle_date', MyConnection.convertDateTimeToText(share.first_1day_candle_date))

                    exec_flag: bool = query.exec()
                    assert exec_flag, query.lastError().text()

                """=================Добавляем акции в таблицу запросов инструментов================="""
                '''----------------Удаляем акции из таблицы запросов инструментов----------------'''
                shares_uids_select: str = '''
                SELECT \"uid\" FROM \"{0}\" WHERE \"{0}\".\"instrument_type\" = \'{1}\'
                '''.format(MyConnection.INSTRUMENT_UIDS_TABLE, 'share')

                instruments_status_delete_sql_command: str = '''
                DELETE FROM \"{0}\" WHERE \"token\" = :token AND \"status\" = :status AND \"uid\" in ({1});
                '''.format(MyConnection.INSTRUMENT_STATUS_TABLE, shares_uids_select)

                instruments_status_delete_query = QSqlQuery(db)
                instruments_status_delete_prepare_flag: bool = instruments_status_delete_query.prepare(instruments_status_delete_sql_command)
                assert instruments_status_delete_prepare_flag, instruments_status_delete_query.lastError().text()

                instruments_status_delete_query.bindValue(':token', token)
                instruments_status_delete_query.bindValue(':status', instrument_status.name)

                instruments_status_delete_exec_flag: bool = instruments_status_delete_query.exec()
                assert instruments_status_delete_exec_flag, instruments_status_delete_query.lastError().text()
                '''------------------------------------------------------------------------------'''

                '''---------------Добавляем акции в таблицу запросов инструментов---------------'''
                instruments_status_insert_sql_command: str = '''
                INSERT INTO \"{0}\" (\"token\", \"status\", \"uid\") VALUES (:token, :status, :uid);
                '''.format(MyConnection.INSTRUMENT_STATUS_TABLE)

                for share in shares:
                    instruments_status_insert_query = QSqlQuery(db)
                    instruments_status_insert_prepare_flag: bool = instruments_status_insert_query.prepare(instruments_status_insert_sql_command)
                    assert instruments_status_insert_prepare_flag, instruments_status_insert_query.lastError().text()

                    instruments_status_insert_query.bindValue(':token', token)
                    instruments_status_insert_query.bindValue(':status', instrument_status.name)
                    instruments_status_insert_query.bindValue(':uid', share.uid)

                    instruments_status_insert_exec_flag: bool = instruments_status_insert_query.exec()
                    assert instruments_status_insert_exec_flag, instruments_status_insert_query.lastError().text()
                '''-----------------------------------------------------------------------------'''
                """================================================================================="""

                commit_flag: bool = db.commit()  # Фиксирует транзакцию в базу данных.
                assert commit_flag, db.lastError().text()
            else:
                assert transaction_flag, db.lastError().text()


    @classmethod
    def addLastPrices(cls, last_prices: list[LastPrice]):
        """Добавляет последние цены в таблицу последних цен."""
        if last_prices:  # Если список последних цен не пуст.
            '''---------------------Создание SQL-строки---------------------'''
            sql_command_middle: str = '(:figi{0}, :price{0}, :time{0}, :instrument_uid{0})'
            sql_command: str = 'INSERT INTO \"{0}\" (\"figi\", \"price\", \"time\", \"instrument_uid\") VALUES '.format(MyConnection.LAST_PRICES_TABLE)
            for i in range(len(last_prices)):
                if i > 0: sql_command += ', '  # Если добавляемая последняя цена не первая.
                sql_command += sql_command_middle.format(i)
            sql_command += ' ON CONFLICT(\"time\", \"instrument_uid\") DO UPDATE SET \"figi\" = \"excluded\".\"figi\", \"price\" = \"excluded\".\"price\";'
            '''-------------------------------------------------------------'''

            db: QSqlDatabase = cls.getDatabase()
            transaction_flag: bool = db.transaction()  # Начинает транзакцию в базе данных.
            if transaction_flag:
                query = QSqlQuery(db)
                prepare_flag: bool = query.prepare(sql_command)
                assert prepare_flag, query.lastError().text()

                for i, lp in enumerate(last_prices):
                    query.bindValue(':figi{0}'.format(i), lp.figi)
                    query.bindValue(':price{0}'.format(i), MyQuotation.__repr__(lp.price))
                    query.bindValue(':time{0}'.format(i), MyConnection.convertDateTimeToText(dt=lp.time, timespec='microseconds'))
                    query.bindValue(':instrument_uid{0}'.format(i), lp.instrument_uid)

                exec_flag: bool = query.exec()
                assert exec_flag, query.lastError().text()

                commit_flag: bool = db.commit()  # Фиксирует транзакцию в базу данных.
                assert commit_flag, db.lastError().text()
            else:
                assert transaction_flag, db.lastError().text()

    @staticmethod
    def addAssetInstrument(db: QSqlDatabase, asset_uid: str, instrument: AssetInstrument):
        """Добавляет идентификаторы инструмента актива в таблицу идентификаторов инструментов активов."""

        def addInstrumentLinks(instrument_uid: str, links: list[InstrumentLink]):
            """Добавляет связанные инструменты в таблицу связей инструментов."""
            if links:  # Если список связанных инструментов не пуст.
                '''---------------------Создание SQL-запроса---------------------'''
                insert_link_sql_command: str = 'INSERT INTO \"{0}\" (\"asset_uid\", \"asset_instrument_uid\", \"type\", \"linked_instrument_uid\") VALUES '.format(MyConnection.INSTRUMENT_LINKS_TABLE)
                for j in range(len(links)):
                    if j > 0: insert_link_sql_command += ', '  # Если добавляемая связь не первая.
                    insert_link_sql_command += '(:asset_uid{0}, :asset_instrument_uid{0}, :type{0}, :linked_instrument_uid{0})'.format(j)
                insert_link_sql_command += ';'
                '''--------------------------------------------------------------'''

                insert_link_query = QSqlQuery(db)
                insert_link_prepare_flag: bool = insert_link_query.prepare(insert_link_sql_command)
                assert insert_link_prepare_flag, insert_link_query.lastError().text()

                for j, link in enumerate(links):
                    insert_link_query.bindValue(':asset_uid{0}'.format(j), asset_uid)
                    insert_link_query.bindValue(':asset_instrument_uid{0}'.format(j), instrument_uid)
                    insert_link_query.bindValue(':type{0}'.format(j), link.type)
                    insert_link_query.bindValue(':linked_instrument_uid{0}'.format(j), link.instrument_uid)

                insert_link_exec_flag: bool = insert_link_query.exec()
                assert insert_link_exec_flag, insert_link_query.lastError().text()

        insert_ai_query_str: str = '''INSERT INTO \"{0}\" (\"asset_uid\", \"uid\", \"figi\", \"instrument_type\", 
            \"ticker\", \"class_code\", \"instrument_kind\", \"position_uid\") VALUES (:asset_uid, :uid, :figi, 
            :instrument_type, :ticker, :class_code, :instrument_kind, :position_uid);
            '''.format(MyConnection.ASSET_INSTRUMENTS_TABLE)

        insert_ai_query = QSqlQuery(db)
        insert_ai_prepare_flag: bool = insert_ai_query.prepare(insert_ai_query_str)
        assert insert_ai_prepare_flag, insert_ai_query.lastError().text()

        insert_ai_query.bindValue(':asset_uid', asset_uid)
        insert_ai_query.bindValue(':uid', instrument.uid)
        insert_ai_query.bindValue(':figi', instrument.figi)
        insert_ai_query.bindValue(':instrument_type', instrument.instrument_type)
        insert_ai_query.bindValue(':ticker', instrument.ticker)
        insert_ai_query.bindValue(':class_code', instrument.class_code)
        insert_ai_query.bindValue(':instrument_kind', instrument.instrument_kind.name)
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
            if transaction_flag:
                def insertAsset(asset: Asset):
                    """Добавляет актив в таблицу активов."""
                    insert_asset_sql_command: str = '''
                    INSERT INTO \"{0}\" (\"uid\", \"type\", \"name\") VALUES (:uid, :type, :name) 
                    ON CONFLICT(\"uid\") DO UPDATE SET \"type\" = {1}.\"type\", \"name\" = {1}.\"name\";
                    '''.format(MyConnection.ASSETS_TABLE, '\"excluded\"')

                    insert_asset_query = QSqlQuery(db)
                    insert_asset_prepare_flag: bool = insert_asset_query.prepare(insert_asset_sql_command)
                    assert insert_asset_prepare_flag, insert_asset_query.lastError().text()

                    insert_asset_query.bindValue(':uid', asset.uid)
                    insert_asset_query.bindValue(':type', asset.type.name)
                    insert_asset_query.bindValue(':name', asset.name)

                    insert_asset_exec_flag: bool = insert_asset_query.exec()
                    assert insert_asset_exec_flag, insert_asset_query.lastError().text()

                    for instrument in asset.instruments:
                        MainConnection.addAssetInstrument(db, asset.uid, instrument)  # Добавляем идентификаторы инструмента актива в таблицу идентификаторов инструментов активов.

                for a in assets:
                    insertAsset(a)  # Добавляем актив в таблицу активов.

                commit_flag: bool = db.commit()  # Фиксирует транзакцию в базу данных.
                assert commit_flag, db.lastError().text()
            else:
                assert transaction_flag, db.lastError().text()
