from enum import EnumType
from PyQt6 import QtSql
from PyQt6.QtSql import QSqlDatabase, QSqlQuery
from tinkoff.invest import Bond, LastPrice, Asset, InstrumentLink, AssetInstrument, Share, InstrumentStatus, AssetType, \
    InstrumentType, Coupon, Dividend, AccountType, AccountStatus, AccessLevel, SecurityTradingStatus, RealExchange
from tinkoff.invest.schemas import RiskLevel, ShareType, CouponType, HistoricCandle, CandleInterval, AssetFull, Brand, \
    AssetCurrency, AssetSecurity
from Classes import TokenClass, MyConnection, partition
from MyBondClass import MyBondClass
from MyMoneyValue import MyMoneyValue
from MyQuotation import MyQuotation
from MyShareClass import MyShareClass


class MainConnection(MyConnection):
    CONNECTION_NAME: str = 'InvestmentViewer'

    def __init__(self):
        self.open()  # Открываем соединение с базой данных.
        self.createDataBase()  # Создаёт базу данных.

    @classmethod  # Привязывает метод к классу, а не к конкретному экземпляру этого класса.
    def createDataBase(cls):
        """Создаёт базу данных."""
        db: QSqlDatabase = cls.getDatabase()
        if db.transaction():
            def getCheckConstraintForColumnFromEnum(column_name: str, enum_class: EnumType) -> str | None:
                """Возвращает CHECK-ограничение для столбца в соответствии с переданным перечислением."""
                enum_keys = enum_class.__members__.keys()
                if len(enum_keys) > 0:
                    check_str: str = 'CHECK('
                    for i, key in enumerate(enum_keys):
                        if i > 0: check_str += ' OR '
                        check_str += '{0} = \'{1}\''.format(column_name, key)
                    check_str += ')'
                    return check_str
                else:
                    return None

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
            account_type_column_name: str = '\"type\"'
            account_type_check_str: str | None = getCheckConstraintForColumnFromEnum(account_type_column_name, AccountType)

            account_status_column_name: str = '\"status\"'
            account_status_check_str: str | None = getCheckConstraintForColumnFromEnum(account_status_column_name, AccountStatus)

            account_access_level_column_name: str = '\"access_level\"'
            account_access_level_check_str: str | None = getCheckConstraintForColumnFromEnum(account_access_level_column_name, AccessLevel)

            accounts_table_str: str = '''
            CREATE TABLE IF NOT EXISTS \"{0}\" (
            \"token\" TEXT NOT NULL,
            \"id\" TEXT NOT NULL,
            {2} TEXT NOT NULL{3},
            \"name\" TEXT NOT NULL,
            {4} TEXT NOT NULL{5},
            \"opened_date\" TEXT NOT NULL,
            \"closed_date\" TEXT NOT NULL,
            {6} TEXT NOT NULL{7},
            PRIMARY KEY (\"token\", \"id\"),
            FOREIGN KEY (\"token\") REFERENCES \"{1}\"(\"token\") ON DELETE CASCADE
            );'''.format(
                MyConnection.ACCOUNTS_TABLE,
                MyConnection.TOKENS_TABLE,
                account_type_column_name,
                '' if account_type_check_str is None else ' {0}'.format(account_type_check_str),
                account_status_column_name,
                '' if account_status_check_str is None else ' {0}'.format(account_status_check_str),
                account_access_level_column_name,
                '' if account_access_level_check_str is None else ' {0}'.format(account_access_level_check_str)
            )

            accounts_query = QSqlQuery(db)
            accounts_prepare_flag: bool = accounts_query.prepare(accounts_table_str)
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
                            THEN RAISE(FAIL, \'Таблица {1} уже содержит такой же uid, но для другого типа инструмента!\')
                    END;
            END;
            '''.format(MyConnection.INSTRUMENT_UIDS_BEFORE_UPDATE_TRIGGER, MyConnection.INSTRUMENT_UIDS_TABLE)
            instr_bef_up_trigger_query = QSqlQuery(db)
            instr_bef_up_trigger_prepare_flag: bool = instr_bef_up_trigger_query.prepare(instr_bef_up_trigger_query_str)
            assert instr_bef_up_trigger_prepare_flag, instr_bef_up_trigger_query.lastError().text()
            instr_bef_up_trigger_exec_flag: bool = instr_bef_up_trigger_query.exec()
            assert instr_bef_up_trigger_exec_flag, instr_bef_up_trigger_query.lastError().text()
            '''-------------------------------------------------------------------------'''

            '''--------------------Создание таблицы данных о бренде--------------------'''
            brands_data_command: str = '''CREATE TABLE IF NOT EXISTS \"{0}\" (
            \"instrument_uid\" TEXT NOT NULL, 
            \"logo_name\" TEXT NOT NULL, 
            \"logo_base_color\" TEXT NOT NULL, 
            \"text_color\" TEXT NOT NULL,
            UNIQUE (\"instrument_uid\"),
            FOREIGN KEY (\"instrument_uid\") REFERENCES \"{1}\"(\"uid\") ON DELETE CASCADE
            );'''.format(
                MyConnection.BRANDS_DATA_TABLE,
                MyConnection.INSTRUMENT_UIDS_TABLE
            )
            brands_data_query = QSqlQuery(db)
            brands_data_prepare_flag: bool = brands_data_query.prepare(brands_data_command)
            assert brands_data_prepare_flag, brands_data_query.lastError().text()
            brands_data_exec_flag: bool = brands_data_query.exec()
            assert brands_data_exec_flag, brands_data_query.lastError().text()
            '''------------------------------------------------------------------------'''

            trading_status_column_name: str = '\"trading_status\"'
            trading_status_check_str: str | None = getCheckConstraintForColumnFromEnum(trading_status_column_name, SecurityTradingStatus)
            trading_status_column: str = '{0} TEXT NOT NULL{1}'.format(trading_status_column_name, '' if trading_status_check_str is None else ' {0}'.format(trading_status_check_str))

            real_exchange_column_name: str = '\"real_exchange\"'
            real_exchange_check_str: str | None = getCheckConstraintForColumnFromEnum(real_exchange_column_name, RealExchange)
            real_exchange_column: str = '{0} TEXT NOT NULL{1}'.format(real_exchange_column_name, '' if real_exchange_check_str is None else ' {0}'.format(real_exchange_check_str))

            '''------------------Создание таблицы облигаций------------------'''
            risk_level_column_name: str = '\"risk_level\"'
            risk_level_check_str: str | None = getCheckConstraintForColumnFromEnum(risk_level_column_name, RiskLevel)
            risk_level_column: str = '{0} TEXT NOT NULL{1}'.format(risk_level_column_name, '' if risk_level_check_str is None else ' {0}'.format(risk_level_check_str))

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
            {2},
            \"otc_flag\" BLOB NOT NULL,
            \"buy_available_flag\" BLOB NOT NULL,
            \"sell_available_flag\" BLOB NOT NULL,
            \"floating_coupon_flag\" BLOB NOT NULL,
            \"perpetual_flag\" BLOB NOT NULL,
            \"amortization_flag\" BLOB NOT NULL,
            \"min_price_increment\" TEXT NOT NULL,
            \"api_trade_available_flag\" BLOB NOT NULL,
            \"uid\" TEXT NOT NULL,
            {3},
            \"position_uid\" TEXT NOT NULL,
            \"asset_uid\" TEXT NOT NULL,
            \"for_iis_flag\" BLOB NOT NULL,
            \"for_qual_investor_flag\" BLOB NOT NULL,
            \"weekend_flag\" BLOB NOT NULL,
            \"blocked_tca_flag\" BLOB NOT NULL,
            \"subordinated_flag\" BLOB NOT NULL,
            \"liquidity_flag\" BLOB NOT NULL,
            \"first_1min_candle_date\" TEXT NOT NULL,
            \"first_1day_candle_date\" TEXT NOT NULL,
            {4},
            \"coupons\" TEXT CHECK(\"coupons\" = \'Yes\' OR \"coupons\" = \'No\'),
            UNIQUE (\"uid\"),
            FOREIGN KEY (\"uid\") REFERENCES \"{1}\"(\"uid\") ON DELETE CASCADE
            );'''.format(
                MyConnection.BONDS_TABLE,
                MyConnection.INSTRUMENT_UIDS_TABLE,
                trading_status_column,
                real_exchange_column,
                risk_level_column
            )
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
            coupon_type_column_name: str = '\"coupon_type\"'
            coupon_type_check_str: str | None = getCheckConstraintForColumnFromEnum(coupon_type_column_name, CouponType)
            coupon_type_column: str = '{0} TEXT NOT NULL{1}'.format(coupon_type_column_name, '' if coupon_type_check_str is None else ' {0}'.format(coupon_type_check_str))

            coupons_query_str: str = '''
            CREATE TABLE IF NOT EXISTS \"{0}\" (
            \"instrument_uid\" TEXT NOT NULL,
            \"figi\" TEXT NOT NULL,
            \"coupon_date\" TEXT NOT NULL,
            \"coupon_number\" INTEGER NOT NULL,
            \"fix_date\" TEXT NOT NULL,
            \"pay_one_bond\" TEXT NOT NULL,
            {2},
            \"coupon_start_date\" TEXT NOT NULL,
            \"coupon_end_date\" TEXT NOT NULL,
            \"coupon_period\" INTEGER NOT NULL,
            UNIQUE (\"instrument_uid\", \"coupon_number\"),
            FOREIGN KEY (\"instrument_uid\") REFERENCES \"{1}\"(\"uid\") ON DELETE CASCADE
            );'''.format(
                MyConnection.COUPONS_TABLE,
                MyConnection.BONDS_TABLE,
                coupon_type_column
            )
            coupons_query = QSqlQuery(db)
            coupons_prepare_flag: bool = coupons_query.prepare(coupons_query_str)
            assert coupons_prepare_flag, coupons_query.lastError().text()
            coupons_exec_flag: bool = coupons_query.exec()
            assert coupons_exec_flag, coupons_query.lastError().text()
            '''--------------------------------------------------------------'''

            '''--------------------Создание таблицы акций--------------------'''
            share_type_column_name: str = '\"share_type\"'
            share_type_check_str: str | None = getCheckConstraintForColumnFromEnum(share_type_column_name, ShareType)
            share_type_column: str = '{0} TEXT NOT NULL{1}'.format(share_type_column_name, '' if share_type_check_str is None else ' {0}'.format(share_type_check_str))

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
            {2},
            \"otc_flag\" BLOB NOT NULL,
            \"buy_available_flag\" BLOB NOT NULL,
            \"sell_available_flag\" BLOB NOT NULL,
            \"div_yield_flag\" BLOB NOT NULL,
            {4},
            \"min_price_increment\" TEXT NOT NULL,
            \"api_trade_available_flag\" BLOB NOT NULL,
            \"uid\" TEXT NOT NULL,
            {3},
            \"position_uid\" TEXT NOT NULL,
            \"asset_uid\" TEXT NOT NULL,
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
            );'''.format(
                MyConnection.SHARES_TABLE,
                MyConnection.INSTRUMENT_UIDS_TABLE,
                trading_status_column,
                real_exchange_column,
                share_type_column
            )
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
            SELECT {1}.\"figi\" AS \"figi\", {1}.\"price\" AS \"price\", 
            MAX({1}.\"time\") AS \"time\", {1}.\"instrument_uid\" AS \"instrument_uid\" 
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
            asset_type_column_name: str = '\"type\"'
            asset_type_check_str: str | None = getCheckConstraintForColumnFromEnum(asset_type_column_name, AssetType)

            assets_sql_command: str = '''
            CREATE TABLE IF NOT EXISTS \"{0}\" (
            \"uid\" TEXT NOT NULL PRIMARY KEY,
            {2} TEXT NOT NULL{3},
            \"name\" TEXT NOT NULL,
            \"name_brief\" TEXT, 
            \"description\" TEXT,
            \"deleted_at\" TEXT,
            \"required_tests\" TEXT,
            \"gos_reg_code\" TEXT,
            \"cfi\" TEXT,
            \"code_nsd\" TEXT,
            \"status\" TEXT,
            \"brand_uid\" TEXT,
            \"updated_at\" TEXT,
            \"br_code\" TEXT,
            \"br_code_name\" TEXT,
            FOREIGN KEY (\"brand_uid\") REFERENCES \"{1}\"(\"uid\")
            );'''.format(
                MyConnection.ASSETS_TABLE,
                MyConnection.BRANDS_TABLE,
                asset_type_column_name,
                '' if asset_type_check_str is None else ' {0}'.format(asset_type_check_str)
            )
            assets_query = QSqlQuery(db)
            assets_prepare_flag: bool = assets_query.prepare(assets_sql_command)
            assert assets_prepare_flag, assets_query.lastError().text()
            assets_exec_flag: bool = assets_query.exec()
            assert assets_exec_flag, assets_query.lastError().text()
            '''--------------------------------------------------------------'''

            instrument_kind_column_name: str = '\"instrument_kind\"'
            instrument_kind_check_str: str | None = getCheckConstraintForColumnFromEnum(instrument_kind_column_name, InstrumentType)

            '''--------------Создание таблицы AssetInstruments--------------'''
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
                '' if instrument_kind_check_str is None else ' {0}'.format(instrument_kind_check_str)
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
                '' if instrument_kind_check_str is None else ' {0}'.format(instrument_kind_check_str),
                MyConnection.ASSETS_TABLE
            )
            asset_securities_query = QSqlQuery(db)
            asset_securities_prepare_flag: bool = asset_securities_query.prepare(asset_securities_sql_command)
            assert asset_securities_prepare_flag, asset_securities_query.lastError().text()
            asset_securities_exec_flag: bool = asset_securities_query.exec()
            assert asset_securities_exec_flag, asset_securities_query.lastError().text()
            '''------------------------------------------------------------------------'''

            '''--------------------Создание таблицы запросов инструментов--------------------'''
            status_column_name: str = '\"status\"'
            status_check_str: str | None = getCheckConstraintForColumnFromEnum(status_column_name, InstrumentStatus)

            instruments_status_query_str: str = '''
            CREATE TABLE IF NOT EXISTS \"{0}\" (
            \"token\" TEXT NOT NULL,
            {3} TEXT NOT NULL{4},
            \"uid\" TEXT NOT NULL,
            UNIQUE (\"token\", \"status\", \"uid\"),
            FOREIGN KEY (\"token\") REFERENCES \"{1}\"(\"token\") ON DELETE CASCADE,
            FOREIGN KEY (\"uid\") REFERENCES \"{2}\"(\"uid\") ON DELETE CASCADE
            );'''.format(
                MyConnection.INSTRUMENT_STATUS_TABLE,
                MyConnection.TOKENS_TABLE,
                MyConnection.INSTRUMENT_UIDS_TABLE,
                status_column_name,
                '' if status_check_str is None else ' {0}'.format(status_check_str)
            )
            instruments_status_query = QSqlQuery(db)
            instruments_status_prepare_flag: bool = instruments_status_query.prepare(instruments_status_query_str)
            assert instruments_status_prepare_flag, instruments_status_query.lastError().text()
            instruments_status_exec_flag: bool = instruments_status_query.exec()
            assert instruments_status_exec_flag, instruments_status_query.lastError().text()
            '''------------------------------------------------------------------------------'''

            recommendation_column_name: str = '\"recommendation\"'
            recommendation_check_str: str = ' CHECK({0} = \'RECOMMENDATION_UNSPECIFIED\' OR {0} = \'RECOMMENDATION_BUY\' OR {0} = \'RECOMMENDATION_HOLD\' OR {0} = \'RECOMMENDATION_SELL\')'.format(recommendation_column_name)

            '''------------------------Создание таблицы прогнозов------------------------'''
            target_items_query_str: str = '''
            CREATE TABLE IF NOT EXISTS \"{0}\" (
            \"uid\" TEXT NOT NULL,
            \"ticker\" TEXT NOT NULL,
            \"company\" TEXT NOT NULL,
            {2} TEXT NOT NULL{3},
            \"recommendation_date\" TEXT NOT NULL,
            \"currency\" TEXT NOT NULL,
            \"current_price\" TEXT NOT NULL,
            \"target_price\" TEXT NOT NULL,
            \"price_change\" TEXT NOT NULL,
            \"price_change_rel\" TEXT NOT NULL,
            \"show_name\" TEXT NOT NULL,
            UNIQUE (\"uid\", \"company\", \"recommendation_date\"),
            FOREIGN KEY (\"uid\") REFERENCES \"{1}\"(\"uid\") ON DELETE CASCADE
            );'''.format(
                MyConnection.TARGET_ITEMS_TABLE,
                MyConnection.INSTRUMENT_UIDS_TABLE,
                recommendation_column_name,
                recommendation_check_str
            )
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
            {2} TEXT NOT NULL{3},
            \"currency\" TEXT NOT NULL,
            \"current_price\" TEXT NOT NULL,
            \"consensus\" TEXT NOT NULL,
            \"min_target\" TEXT NOT NULL,
            \"max_target\" TEXT NOT NULL,
            \"price_change\" TEXT NOT NULL,
            \"price_change_rel\" TEXT NOT NULL,
            UNIQUE (\"uid\"),
            FOREIGN KEY (\"uid\") REFERENCES \"{1}\"(\"uid\") ON DELETE CASCADE
            );'''.format(
                MyConnection.CONSENSUS_ITEMS_TABLE,
                MyConnection.INSTRUMENT_UIDS_TABLE,
                recommendation_column_name,
                recommendation_check_str
            )
            consensus_items_query = QSqlQuery(db)
            consensus_items_prepare_flag: bool = consensus_items_query.prepare(consensus_items_query_str)
            assert consensus_items_prepare_flag, consensus_items_query.lastError().text()
            consensus_items_exec_flag: bool = consensus_items_query.exec()
            assert consensus_items_exec_flag, consensus_items_query.lastError().text()
            '''--------------------------------------------------------------------------'''

            commit_flag: bool = db.commit()  # Фиксирует транзакцию в базу данных.
            assert commit_flag, db.lastError().text()
        else:
            raise SystemError('Не получилось начать транзакцию! db.lastError().text(): \'{0}\'.'.format(db.lastError().text()))

    @classmethod
    def addNewToken(cls, token: TokenClass):
        """Добавляет новый токен в таблицу токенов."""
        db: QSqlDatabase = cls.getDatabase()
        if db.transaction():
            tokens_query = QSqlQuery(db)
            tokens_prepare_flag: bool = tokens_query.prepare('INSERT INTO \"{0}\" (\"token\", \"name\") VALUES (:token, :name);'.format(MyConnection.TOKENS_TABLE))
            assert tokens_prepare_flag, tokens_query.lastError().text()
            tokens_query.bindValue(':token', token.token)
            tokens_query.bindValue(':name', token.name)
            tokens_exec_flag: bool = tokens_query.exec()
            assert tokens_exec_flag, tokens_query.lastError().text()

            insert_unary_limit_command: str = '''INSERT INTO \"{0}\" (\"token\", \"limit_per_minute\", \"methods\") 
            VALUES (:token, :limit_per_minute, :methods);'''.format(MyConnection.UNARY_LIMITS_TABLE)
            for unary_limit in token.unary_limits:
                unary_limit_query = QSqlQuery(db)
                unary_limit_prepare_flag: bool = unary_limit_query.prepare(insert_unary_limit_command)
                assert unary_limit_prepare_flag, unary_limit_query.lastError().text()
                unary_limit_query.bindValue(':token', token.token)
                unary_limit_query.bindValue(':limit_per_minute', unary_limit.limit_per_minute)
                unary_limit_query.bindValue(':methods', cls.convertStrListToStr([method.full_method for method in unary_limit.methods]))
                unary_limit_exec_flag: bool = unary_limit_query.exec()
                assert unary_limit_exec_flag, unary_limit_query.lastError().text()

            insert_stream_limit_command: str = '''INSERT INTO \"{0}\" (\"token\", \"limit_count\", \"streams\", 
            \"open\") VALUES (:token, :limit_count, :streams, :open);'''.format(MyConnection.STREAM_LIMITS_TABLE)
            for stream_limit in token.stream_limits:
                stream_limit_query = QSqlQuery(db)
                stream_limit_prepare_flag: bool = stream_limit_query.prepare(insert_stream_limit_command)
                assert stream_limit_prepare_flag, stream_limit_query.lastError().text()
                stream_limit_query.bindValue(':token', token.token)
                stream_limit_query.bindValue(':limit_count', stream_limit.limit)
                stream_limit_query.bindValue(':streams', cls.convertStrListToStr([method.full_method for method in stream_limit.methods]))
                stream_limit_query.bindValue(':open', stream_limit.open)
                stream_limit_exec_flag: bool = stream_limit_query.exec()
                assert stream_limit_exec_flag, stream_limit_query.lastError().text()

            insert_account_command: str = '''INSERT INTO \"{0}\" (\"token\", \"id\", \"type\", \"name\", \"status\", 
            \"opened_date\", \"closed_date\", \"access_level\") VALUES (:token, :id, :type, :name, :status, 
            :opened_date, :closed_date, :access_level);'''.format(MyConnection.ACCOUNTS_TABLE)
            for account in token.accounts:
                account_query = QSqlQuery(db)
                account_prepare_flag: bool = account_query.prepare(insert_account_command)
                assert account_prepare_flag, account_query.lastError().text()
                account_query.bindValue(':token', token.token)
                account_query.bindValue(':id', account.id)
                account_query.bindValue(':type', account.type.name)
                account_query.bindValue(':name', account.name)
                account_query.bindValue(':status', account.status.name)
                account_query.bindValue(':opened_date', MyConnection.convertDateTimeToText(account.opened_date))
                account_query.bindValue(':closed_date', MyConnection.convertDateTimeToText(account.closed_date))
                account_query.bindValue(':access_level', account.access_level.name)
                account_exec_flag: bool = account_query.exec()
                assert account_exec_flag, account_query.lastError().text()

            commit_flag: bool = db.commit()  # Фиксирует транзакцию в базу данных.
            assert commit_flag, db.lastError().text()
        else:
            raise SystemError('Не получилось начать транзакцию! db.lastError().text(): \'{0}\'.'.format(db.lastError().text()))

    @classmethod
    def deleteToken(cls, token: str):
        """Удаляет токен и все связанные с ним данные."""
        db: QSqlDatabase = cls.getDatabase()
        if db.transaction():
            query = QSqlQuery(db)
            prepare_flag: bool = query.prepare('DELETE FROM \"{0}\" WHERE \"token\" = :token;'.format(MyConnection.TOKENS_TABLE))
            assert prepare_flag, query.lastError().text()
            query.bindValue(':token', token)
            exec_flag: bool = query.exec()
            assert exec_flag, query.lastError().text()

            commit_flag: bool = db.commit()  # Фиксирует транзакцию в базу данных.
            assert commit_flag, db.lastError().text()
        else:
            raise SystemError('Не получилось начать транзакцию! db.lastError().text(): \'{0}\'.'.format(db.lastError().text()))

    @classmethod
    def addBonds(cls, token: str, instrument_status: InstrumentStatus, bonds: list[Bond]):
        """Добавляет облигации в таблицу облигаций."""
        if bonds:  # Если список облигаций не пуст.
            db: QSqlDatabase = cls.getDatabase()
            if db.transaction():
                VARIABLES_COUNT: int = 51  # Количество variables в каждом insert.
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
                \"real_exchange\", \"position_uid\", \"asset_uid\", \"for_iis_flag\", \"for_qual_investor_flag\", 
                \"weekend_flag\", \"blocked_tca_flag\", \"subordinated_flag\", \"liquidity_flag\", 
                \"first_1min_candle_date\", \"first_1day_candle_date\", \"risk_level\") VALUES '''.format(
                    MyConnection.BONDS_TABLE
                )

                bonds_insert_sql_command_middle: str = '''(:figi{0}, :ticker{0}, :class_code{0}, :isin{0}, :lot{0}, 
                :currency{0}, :klong{0}, :kshort{0}, :dlong{0}, :dshort{0}, :dlong_min{0}, :dshort_min{0}, 
                :short_enabled_flag{0}, :name{0}, :exchange{0}, :coupon_quantity_per_year{0}, :maturity_date{0}, 
                :nominal{0}, :initial_nominal{0}, :state_reg_date{0}, :placement_date{0}, :placement_price{0}, 
                :aci_value{0}, :country_of_risk{0}, :country_of_risk_name{0}, :sector{0}, :issue_kind{0}, 
                :issue_size{0}, :issue_size_plan{0}, :trading_status{0}, :otc_flag{0}, :buy_available_flag{0}, 
                :sell_available_flag{0}, :floating_coupon_flag{0}, :perpetual_flag{0}, :amortization_flag{0}, 
                :min_price_increment{0}, :api_trade_available_flag{0}, :uid{0}, :real_exchange{0}, :position_uid{0}, 
                :asset_uid{0}, :for_iis_flag{0}, :for_qual_investor_flag{0}, :weekend_flag{0}, :blocked_tca_flag{0}, 
                :subordinated_flag{0}, :liquidity_flag{0}, :first_1min_candle_date{0}, :first_1day_candle_date{0}, 
                :risk_level{0})'''

                bonds_insert_sql_command_end: str = ''' ON CONFLICT(\"uid\") DO UPDATE SET \"figi\" = {0}.\"figi\", 
                \"ticker\" = {0}.\"ticker\", \"class_code\" = {0}.\"class_code\", \"isin\" = {0}.\"isin\", \"lot\" = 
                {0}.\"lot\", \"currency\" = {0}.\"currency\", \"klong\" = {0}.\"klong\", \"kshort\" = {0}.\"kshort\", 
                \"dlong\" = {0}.\"dlong\", \"dshort\" = {0}.\"dshort\", \"dlong_min\" = {0}.\"dlong_min\", 
                \"dshort_min\" = {0}.\"dshort_min\", \"short_enabled_flag\" = {0}.\"short_enabled_flag\", \"name\" = 
                {0}.\"name\", \"exchange\" = {0}.\"exchange\", \"coupon_quantity_per_year\" = 
                {0}.\"coupon_quantity_per_year\", \"maturity_date\" = {0}.\"maturity_date\", \"nominal\" = 
                {0}.\"nominal\", \"initial_nominal\" = {0}.\"initial_nominal\", \"state_reg_date\" = 
                {0}.\"state_reg_date\", \"placement_date\" = {0}.\"placement_date\", \"placement_price\" = 
                {0}.\"placement_price\", \"aci_value\" = {0}.\"aci_value\", \"country_of_risk\" = 
                {0}.\"country_of_risk\", \"country_of_risk_name\" = {0}.\"country_of_risk_name\", \"sector\" = 
                {0}.\"sector\", \"issue_kind\" = {0}.\"issue_kind\", \"issue_size\" = {0}.\"issue_size\", 
                \"issue_size_plan\" = {0}.\"issue_size_plan\", \"trading_status\" = {0}.\"trading_status\", 
                \"otc_flag\" = {0}.\"otc_flag\", \"buy_available_flag\" = {0}.\"buy_available_flag\", 
                \"sell_available_flag\" = {0}.\"sell_available_flag\", \"floating_coupon_flag\" = 
                {0}.\"floating_coupon_flag\", \"perpetual_flag\" = {0}.\"perpetual_flag\", \"amortization_flag\" = 
                {0}.\"amortization_flag\", \"min_price_increment\" = {0}.\"min_price_increment\", 
                \"api_trade_available_flag\" = {0}.\"api_trade_available_flag\", \"real_exchange\" = 
                {0}.\"real_exchange\", \"position_uid\" = {0}.\"position_uid\", \"asset_uid\" = {0}.\"asset_uid\", 
                \"for_iis_flag\" = {0}.\"for_iis_flag\", \"for_qual_investor_flag\" = {0}.\"for_qual_investor_flag\", 
                \"weekend_flag\" = {0}.\"weekend_flag\", \"blocked_tca_flag\" = {0}.\"blocked_tca_flag\", 
                \"subordinated_flag\" = {0}.\"subordinated_flag\", \"liquidity_flag\" = {0}.\"liquidity_flag\", 
                \"first_1min_candle_date\" = {0}.\"first_1min_candle_date\", \"first_1day_candle_date\" = 
                {0}.\"first_1day_candle_date\", \"risk_level\" = {0}.\"risk_level\" WHERE \"figi\" != {0}.\"figi\" OR 
                \"ticker\" != {0}.\"ticker\" OR \"class_code\" != {0}.\"class_code\" OR \"isin\" != {0}.\"isin\" OR 
                \"lot\" != {0}.\"lot\" OR \"currency\" != {0}.\"currency\" OR \"klong\" != {0}.\"klong\" OR 
                \"kshort\" != {0}.\"kshort\" OR \"dlong\" != {0}.\"dlong\" OR \"dshort\" != {0}.\"dshort\" OR 
                \"dlong_min\" != {0}.\"dlong_min\" OR \"dshort_min\" != {0}.\"dshort_min\" OR \"short_enabled_flag\" != 
                {0}.\"short_enabled_flag\" OR \"name\" != {0}.\"name\" OR \"exchange\" != {0}.\"exchange\" OR 
                \"coupon_quantity_per_year\" != {0}.\"coupon_quantity_per_year\" OR \"maturity_date\" != 
                {0}.\"maturity_date\" OR \"nominal\" != {0}.\"nominal\" OR \"initial_nominal\" != 
                {0}.\"initial_nominal\" OR \"state_reg_date\" != {0}.\"state_reg_date\" OR \"placement_date\" != 
                {0}.\"placement_date\" OR \"placement_price\" != {0}.\"placement_price\" OR \"aci_value\" != 
                {0}.\"aci_value\" OR \"country_of_risk\" != {0}.\"country_of_risk\" OR \"country_of_risk_name\" != 
                {0}.\"country_of_risk_name\" OR \"sector\" != {0}.\"sector\" OR \"issue_kind\" != {0}.\"issue_kind\" OR 
                \"issue_size\" != {0}.\"issue_size\" OR \"issue_size_plan\" != {0}.\"issue_size_plan\" OR 
                \"trading_status\" != {0}.\"trading_status\" OR \"otc_flag\" != {0}.\"otc_flag\" OR 
                \"buy_available_flag\" != {0}.\"buy_available_flag\" OR \"sell_available_flag\" != 
                {0}.\"sell_available_flag\" OR \"floating_coupon_flag\" != {0}.\"floating_coupon_flag\" OR 
                \"perpetual_flag\" != {0}.\"perpetual_flag\" OR \"amortization_flag\" != {0}.\"amortization_flag\" OR 
                \"min_price_increment\" != {0}.\"min_price_increment\" OR \"api_trade_available_flag\" != 
                {0}.\"api_trade_available_flag\" OR \"real_exchange\" != {0}.\"real_exchange\" OR \"position_uid\" != 
                {0}.\"position_uid\" OR \"asset_uid\" != {0}.\"asset_uid\" OR \"for_iis_flag\" != {0}.\"for_iis_flag\" 
                OR \"for_qual_investor_flag\" != {0}.\"for_qual_investor_flag\" OR \"weekend_flag\" != 
                {0}.\"weekend_flag\" OR \"blocked_tca_flag\" != {0}.\"blocked_tca_flag\" OR \"subordinated_flag\" != 
                {0}.\"subordinated_flag\" OR \"liquidity_flag\" != {0}.\"liquidity_flag\" OR \"first_1min_candle_date\" 
                != {0}.\"first_1min_candle_date\" OR \"first_1day_candle_date\" != {0}.\"first_1day_candle_date\" OR 
                \"risk_level\" != {0}.\"risk_level\";'''.format('\"excluded\"')

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
                        query.bindValue(':trading_status{0}'.format(i), bond.trading_status.name)
                        query.bindValue(':otc_flag{0}'.format(i), bond.otc_flag)
                        query.bindValue(':buy_available_flag{0}'.format(i), bond.buy_available_flag)
                        query.bindValue(':sell_available_flag{0}'.format(i), bond.sell_available_flag)
                        query.bindValue(':floating_coupon_flag{0}'.format(i), bond.floating_coupon_flag)
                        query.bindValue(':perpetual_flag{0}'.format(i), bond.perpetual_flag)
                        query.bindValue(':amortization_flag{0}'.format(i), bond.amortization_flag)
                        query.bindValue(':min_price_increment{0}'.format(i), MyQuotation.__repr__(bond.min_price_increment))
                        query.bindValue(':api_trade_available_flag{0}'.format(i), bond.api_trade_available_flag)
                        query.bindValue(':uid{0}'.format(i), bond.uid)
                        query.bindValue(':real_exchange{0}'.format(i), bond.real_exchange.name)
                        query.bindValue(':position_uid{0}'.format(i), bond.position_uid)
                        query.bindValue(':asset_uid{0}'.format(i), bond.asset_uid)
                        query.bindValue(':for_iis_flag{0}'.format(i), bond.for_iis_flag)
                        query.bindValue(':for_qual_investor_flag{0}'.format(i), bond.for_qual_investor_flag)
                        query.bindValue(':weekend_flag{0}'.format(i), bond.weekend_flag)
                        query.bindValue(':blocked_tca_flag{0}'.format(i), bond.blocked_tca_flag)
                        query.bindValue(':subordinated_flag{0}'.format(i), bond.subordinated_flag)
                        query.bindValue(':liquidity_flag{0}'.format(i), bond.liquidity_flag)
                        query.bindValue(':first_1min_candle_date{0}'.format(i), MyConnection.convertDateTimeToText(bond.first_1min_candle_date))
                        query.bindValue(':first_1day_candle_date{0}'.format(i), MyConnection.convertDateTimeToText(bond.first_1day_candle_date))
                        query.bindValue(':risk_level{0}'.format(i), bond.risk_level.name)

                    bonds_insert_exec_flag: bool = query.exec()
                    assert bonds_insert_exec_flag, query.lastError().text()

                """===============Добавляем данные о бренде в таблицу данных о брендах==============="""
                brand_data_command: str = '''INSERT INTO {0} (\"instrument_uid\", \"logo_name\", \"logo_base_color\", 
                \"text_color\") VALUES (:uid, :logo_name, :logo_base_color, :text_color) ON CONFLICT(\"instrument_uid\") 
                DO UPDATE SET \"logo_name\" = {1}.\"logo_name\", \"logo_base_color\" = {1}.\"logo_base_color\", 
                \"text_color\" = {1}.\"text_color\" WHERE \"logo_name\" != {1}.\"logo_name\" OR \"logo_base_color\" != 
                {1}.\"logo_base_color\" OR \"text_color\" != {1}.\"text_color\";'''.format(
                    '\"{0}\"'.format(MyConnection.BRANDS_DATA_TABLE),
                    '\"excluded\"'
                )

                for bond in bonds:
                    brand_data_query = QSqlQuery(db)
                    brand_data_prepare_flag: bool = brand_data_query.prepare(brand_data_command)
                    assert brand_data_prepare_flag, brand_data_query.lastError().text()
                    brand_data_query.bindValue(':uid', bond.uid)
                    brand_data_query.bindValue(':logo_name', bond.brand.logo_name)
                    brand_data_query.bindValue(':logo_base_color', bond.brand.logo_base_color)
                    brand_data_query.bindValue(':text_color', bond.brand.text_color)
                    brand_data_exec_flag: bool = brand_data_query.exec()
                    assert brand_data_exec_flag, brand_data_query.lastError().text()
                """=================================================================================="""

                """===============Добавляем облигации в таблицу запросов инструментов==============="""
                '''--------------Удаляем облигации из таблицы запросов инструментов--------------'''
                bonds_uids_select: str = 'SELECT \"uid\" FROM \"{0}\" WHERE \"{0}\".\"instrument_type\" = \'{1}\''.format(
                    MyConnection.INSTRUMENT_UIDS_TABLE,
                    'bond'
                )

                instruments_status_delete_sql_command: str = '''DELETE FROM \"{0}\" WHERE \"token\" = :token AND 
                \"status\" = :status AND \"uid\" in ({1});'''.format(
                    MyConnection.INSTRUMENT_STATUS_TABLE,
                    bonds_uids_select
                )

                instruments_status_delete_query = QSqlQuery(db)
                instruments_status_delete_prepare_flag: bool = instruments_status_delete_query.prepare(instruments_status_delete_sql_command)
                assert instruments_status_delete_prepare_flag, instruments_status_delete_query.lastError().text()
                instruments_status_delete_query.bindValue(':token', token)
                instruments_status_delete_query.bindValue(':status', instrument_status.name)
                instruments_status_delete_exec_flag: bool = instruments_status_delete_query.exec()
                assert instruments_status_delete_exec_flag, instruments_status_delete_query.lastError().text()
                '''------------------------------------------------------------------------------'''

                '''-------------Добавляем облигации в таблицу запросов инструментов-------------'''
                instruments_status_insert_sql_command: str = '''INSERT INTO \"{0}\" (\"token\", \"status\", \"uid\") 
                VALUES (:token, :status, :uid);'''.format(MyConnection.INSTRUMENT_STATUS_TABLE)

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
                raise SystemError('Не получилось начать транзакцию! db.lastError().text(): \'{0}\'.'.format(db.lastError().text()))

    @classmethod
    def getMyInstrument(cls, uid: str) -> MyShareClass | MyBondClass | None:
        type_sql_command: str = 'SELECT {0}.\"instrument_type\" FROM {0} WHERE {0}.\"uid\" = :uid;'.format(
            '\"{0}\"'.format(MyConnection.INSTRUMENT_UIDS_TABLE)
        )
        db: QtSql.QSqlDatabase = cls.getDatabase()
        if db.transaction():
            type_query = QtSql.QSqlQuery(db)
            type_query.setForwardOnly(True)  # Возможно, это ускоряет извлечение данных.
            type_prepare_flag: bool = type_query.prepare(type_sql_command)
            assert type_prepare_flag, type_query.lastError().text()
            type_query.bindValue(':uid', uid)
            type_exec_flag: bool = type_query.exec()
            assert type_exec_flag, type_query.lastError().text()

            instrument_type: str
            types_count: int = 0
            while type_query.next():
                types_count += 1
                instrument_type = type_query.value('instrument_type')

            if types_count == 0:
                commit_flag: bool = db.commit()  # Фиксирует транзакцию в базу данных.
                assert commit_flag, db.lastError().text()
                return None
            elif types_count == 1:
                def getCurrentLastPrice(instrument_uid: str) -> LastPrice | None:
                    last_price_sql_command: str = '''SELECT {0}.\"figi\", {0}.\"price\", {0}.\"time\", 
                    {0}.\"instrument_uid\" FROM {0} WHERE {0}.\"instrument_uid\" = :instrument_uid;
                    '''.format('\"{0}\"'.format(MyConnection.LAST_PRICES_VIEW))

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
                        assert last_price_rows_count < 2, 'Не должно быть нескольких строк с одним и тем же instrument_uid (\'{0}\')!'.format(uid)
                        last_price = MyConnection.getCurrentLastPrice(last_price_query)

                    return last_price

                if instrument_type == 'share':
                    share_sql_command: str = '''SELECT {0}.\"figi\", {0}.\"ticker\", {0}.\"class_code\", {0}.\"isin\", 
                    {0}.\"lot\", {0}.\"currency\", {0}.\"klong\", {0}.\"kshort\", {0}.\"dlong\", {0}.\"dshort\", 
                    {0}.\"dlong_min\", {0}.\"dshort_min\", {0}.\"short_enabled_flag\", {0}.\"name\", {0}.\"exchange\", 
                    {0}.\"ipo_date\", {0}.\"issue_size\", {0}.\"country_of_risk\", {0}.\"country_of_risk_name\", 
                    {0}.\"sector\", {0}.\"issue_size_plan\", {0}.\"nominal\", {0}.\"trading_status\", {0}.\"otc_flag\", 
                    {0}.\"buy_available_flag\", {0}.\"sell_available_flag\", {0}.\"div_yield_flag\", {0}.\"share_type\", 
                    {0}.\"min_price_increment\", {0}.\"api_trade_available_flag\", {0}.\"uid\", {0}.\"real_exchange\", 
                    {0}.\"position_uid\", {0}.\"asset_uid\", {0}.\"for_iis_flag\", {0}.\"for_qual_investor_flag\",
                    {0}.\"weekend_flag\", {0}.\"blocked_tca_flag\", {0}.\"liquidity_flag\", 
                    {0}.\"first_1min_candle_date\", {0}.\"first_1day_candle_date\", {0}.\"dividends\" 
                    FROM {0} WHERE {0}.\"uid\" = :uid;'''.format('\"{0}\"'.format(MyConnection.SHARES_TABLE))

                    share_query = QtSql.QSqlQuery(db)
                    share_query.setForwardOnly(True)  # Возможно, это ускоряет извлечение данных.
                    share_prepare_flag: bool = share_query.prepare(share_sql_command)
                    assert share_prepare_flag, share_query.lastError().text()
                    share_query.bindValue(':uid', uid)
                    share_exec_flag: bool = share_query.exec()
                    assert share_exec_flag, share_query.lastError().text()

                    share: Share
                    shares_count: int = 0
                    while share_query.next():
                        shares_count += 1
                        share = MyConnection.getCurrentShare(share_query)
                        dividends_flag = MyConnection.convertDividendsFlagToBool(share_query.value('dividends'))

                    if shares_count != 1:
                        commit_flag: bool = db.commit()  # Фиксирует транзакцию в базу данных.
                        assert commit_flag, db.lastError().text()
                        raise SystemError('Таблица {0} должна содержать одну акцию с uid = \'{1}\'!'.format(MyConnection.SHARES_TABLE, uid))

                    '''--------------------------Получаем дивиденды акций--------------------------'''
                    if dividends_flag:
                        dividends_sql_command: str = '''SELECT \"dividend_net\", \"payment_date\", \"declared_date\", 
                        \"last_buy_date\", \"dividend_type\", \"record_date\", \"regularity\", \"close_price\", 
                        \"yield_value\", \"created_at\" FROM {0} WHERE {0}.\"instrument_uid\" = :share_uid;
                        '''.format('\"{0}\"'.format(MyConnection.DIVIDENDS_TABLE))

                        dividends_query = QtSql.QSqlQuery(db)
                        dividends_query.setForwardOnly(True)  # Возможно, это ускоряет извлечение данных.
                        dividends_prepare_flag: bool = dividends_query.prepare(dividends_sql_command)
                        assert dividends_prepare_flag, dividends_query.lastError().text()
                        dividends_query.bindValue(':share_uid', uid)
                        dividends_exec_flag: bool = dividends_query.exec()
                        assert dividends_exec_flag, dividends_query.lastError().text()

                        dividends: list[Dividend] = []
                        while dividends_query.next():
                            dividends.append(MyConnection.getCurrentDividend(dividends_query))
                        assert len(dividends) > 0
                    else:
                        dividends: None = None
                    '''----------------------------------------------------------------------------'''

                    last_price: LastPrice | None = getCurrentLastPrice(uid)

                    commit_flag: bool = db.commit()  # Фиксирует транзакцию в базу данных.
                    assert commit_flag, db.lastError().text()

                    return MyShareClass(share=share, last_price=last_price, dividends=dividends)
                elif instrument_type == 'bond':
                    bond_sql_command: str = '''SELECT {0}.\"figi\", {0}.\"ticker\", {0}.\"class_code\", {0}.\"isin\", 
                    {0}.\"lot\", {0}.\"currency\", {0}.\"klong\", {0}.\"kshort\", {0}.\"dlong\", {0}.\"dshort\", 
                    {0}.\"dlong_min\", {0}.\"dshort_min\", {0}.\"short_enabled_flag\", {0}.\"name\", {0}.\"exchange\", 
                    {0}.\"coupon_quantity_per_year\", {0}.\"maturity_date\", {0}.\"nominal\", {0}.\"initial_nominal\", 
                    {0}.\"state_reg_date\", {0}.\"placement_date\", {0}.\"placement_price\", {0}.\"aci_value\", 
                    {0}.\"country_of_risk\", {0}.\"country_of_risk_name\", {0}.\"sector\", {0}.\"issue_kind\", 
                    {0}.\"issue_size\", {0}.\"issue_size_plan\", {0}.\"trading_status\", {0}.\"otc_flag\", 
                    {0}.\"buy_available_flag\", {0}.\"sell_available_flag\", {0}.\"floating_coupon_flag\", 
                    {0}.\"perpetual_flag\", {0}.\"amortization_flag\", {0}.\"min_price_increment\", 
                    {0}.\"api_trade_available_flag\", {0}.\"uid\", {0}.\"real_exchange\", {0}.\"position_uid\", 
                    {0}.\"asset_uid\", {0}.\"for_iis_flag\", {0}.\"for_qual_investor_flag\", {0}.\"weekend_flag\", 
                    {0}.\"blocked_tca_flag\", {0}.\"subordinated_flag\", {0}.\"liquidity_flag\",
                    {0}.\"first_1min_candle_date\", {0}.\"first_1day_candle_date\", {0}.\"risk_level\", {0}.\"coupons\" 
                    FROM {0} WHERE {0}.\"uid\" = :uid;'''.format('\"{0}\"'.format(MyConnection.BONDS_TABLE))

                    bond_query = QtSql.QSqlQuery(db)
                    bond_query.setForwardOnly(True)  # Возможно, это ускоряет извлечение данных.
                    bond_prepare_flag: bool = bond_query.prepare(bond_sql_command)
                    assert bond_prepare_flag, bond_query.lastError().text()
                    bond_query.bindValue(':uid', uid)
                    bond_exec_flag: bool = bond_query.exec()
                    assert bond_exec_flag, bond_query.lastError().text()

                    bond: Bond
                    coupons_flag: bool
                    bonds_count: int = 0
                    while bond_query.next():
                        bonds_count += 1
                        bond = MyConnection.getCurrentBond(bond_query)
                        coupons_flag = MyConnection.convertCouponsFlagToBool(bond_query.value('coupons'))

                    if bonds_count != 1:
                        commit_flag: bool = db.commit()  # Фиксирует транзакцию в базу данных.
                        assert commit_flag, db.lastError().text()
                        raise SystemError('Таблица {0} должна содержать одну облигацию с uid = \'{1}\'!'.format(MyConnection.BONDS_TABLE, uid))

                    '''--------------------------Получаем купоны облигации--------------------------'''
                    if coupons_flag:
                        coupons_sql_command: str = '''SELECT {0}.\"figi\", {0}.\"coupon_date\", {0}.\"coupon_number\", 
                        {0}.\"fix_date\", {0}.\"pay_one_bond\", {0}.\"coupon_type\", {0}.\"coupon_start_date\", 
                        {0}.\"coupon_end_date\", {0}.\"coupon_period\" 
                        FROM {0} WHERE {0}.\"instrument_uid\" = :bond_uid;
                        '''.format('\"{0}\"'.format(MyConnection.COUPONS_TABLE))

                        coupons_query = QtSql.QSqlQuery(db)
                        coupons_query.setForwardOnly(True)  # Возможно, это ускоряет извлечение данных.
                        coupons_prepare_flag: bool = coupons_query.prepare(coupons_sql_command)
                        assert coupons_prepare_flag, coupons_query.lastError().text()
                        coupons_query.bindValue(':bond_uid', uid)
                        coupons_exec_flag: bool = coupons_query.exec()
                        assert coupons_exec_flag, coupons_query.lastError().text()

                        coupons: list[Coupon] = []
                        while coupons_query.next():
                            coupons.append(MyConnection.getCurrentCoupon(coupons_query))
                        assert len(coupons) > 0
                    else:
                        coupons: None = None
                    '''-----------------------------------------------------------------------------'''

                    last_price: LastPrice | None = getCurrentLastPrice(uid)

                    commit_flag: bool = db.commit()  # Фиксирует транзакцию в базу данных.
                    assert commit_flag, db.lastError().text()

                    return MyBondClass(bond=bond, last_price=last_price, coupons=coupons)
                else:
                    raise ValueError('Неизвестный тип инструмента ({0})!'.format(instrument_type))
            else:
                commit_flag: bool = db.commit()  # Фиксирует транзакцию в базу данных.
                assert commit_flag, db.lastError().text()
                raise SystemError('В таблице {0} не должно быть несколько одинаковых uid (\'{1}\')!'.format(MyConnection.INSTRUMENT_UIDS_TABLE, uid))
        else:
            raise SystemError('Не получилось начать транзакцию! db.lastError().text(): \'{0}\'.'.format(db.lastError().text()))

    @classmethod
    def addShares(cls, token: str, instrument_status: InstrumentStatus, shares: list[Share]):
        """Добавляет акции в таблицу акций."""
        if shares:  # Если список акций не пуст.
            sql_command: str = '''INSERT INTO \"{0}\" (\"figi\", \"ticker\", \"class_code\", \"isin\", \"lot\", 
            \"currency\", \"klong\", \"kshort\", \"dlong\", \"dshort\", \"dlong_min\", \"dshort_min\", 
            \"short_enabled_flag\", \"name\", \"exchange\", \"ipo_date\", \"issue_size\", \"country_of_risk\", 
            \"country_of_risk_name\", \"sector\", \"issue_size_plan\", \"nominal\", \"trading_status\", \"otc_flag\", 
            \"buy_available_flag\", \"sell_available_flag\", \"div_yield_flag\", \"share_type\", 
            \"min_price_increment\", \"api_trade_available_flag\", \"uid\", \"real_exchange\", \"position_uid\", 
            \"asset_uid\", \"for_iis_flag\", \"for_qual_investor_flag\", \"weekend_flag\", \"blocked_tca_flag\", 
            \"liquidity_flag\", \"first_1min_candle_date\", \"first_1day_candle_date\") VALUES (:figi, :ticker, 
            :class_code, :isin, :lot, :currency, :klong, :kshort, :dlong, :dshort, :dlong_min, :dshort_min, 
            :short_enabled_flag, :name, :exchange, :ipo_date, :issue_size, :country_of_risk, :country_of_risk_name, 
            :sector, :issue_size_plan, :nominal, :trading_status, :otc_flag, :buy_available_flag, :sell_available_flag, 
            :div_yield_flag, :share_type, :min_price_increment, :api_trade_available_flag, :uid, :real_exchange, 
            :position_uid, :asset_uid, :for_iis_flag, :for_qual_investor_flag, :weekend_flag, :blocked_tca_flag, 
            :liquidity_flag, :first_1min_candle_date, :first_1day_candle_date) ON CONFLICT(\"uid\") DO UPDATE SET 
            \"figi\" = {1}.\"figi\", \"ticker\" = {1}.\"ticker\", \"class_code\" = {1}.\"class_code\", \"isin\" = 
            {1}.\"isin\", \"lot\" = {1}.\"lot\", \"currency\" = {1}.\"currency\", \"klong\" = {1}.\"klong\", \"kshort\" 
            = {1}.\"kshort\", \"dlong\" = {1}.\"dlong\", \"dshort\" = {1}.\"dshort\", \"dlong_min\" = {1}.\"dlong_min\", 
            \"dshort_min\" = {1}.\"dshort_min\", \"short_enabled_flag\" = {1}.\"short_enabled_flag\", \"name\" = 
            {1}.\"name\", \"exchange\" = {1}.\"exchange\", \"exchange\" = {1}.\"exchange\", \"ipo_date\" = 
            {1}.\"ipo_date\", \"issue_size\" = {1}.\"issue_size\", \"country_of_risk\" = {1}.\"country_of_risk\", 
            \"country_of_risk_name\" = {1}.\"country_of_risk_name\", \"sector\" = {1}.\"sector\", \"issue_size_plan\" = 
            {1}.\"issue_size_plan\", \"nominal\" = {1}.\"nominal\", \"trading_status\" = {1}.\"trading_status\", 
            \"otc_flag\" = {1}.\"otc_flag\", \"buy_available_flag\" = {1}.\"buy_available_flag\", 
            \"sell_available_flag\" = {1}.\"sell_available_flag\", \"div_yield_flag\" = {1}.\"div_yield_flag\", 
            \"share_type\" = {1}.\"share_type\", \"min_price_increment\" = {1}.\"min_price_increment\", 
            \"api_trade_available_flag\" = {1}.\"api_trade_available_flag\", \"real_exchange\" = {1}.\"real_exchange\", 
            \"position_uid\" = {1}.\"position_uid\", \"asset_uid\" = {1}.\"asset_uid\", \"for_iis_flag\" = 
            {1}.\"for_iis_flag\", \"for_qual_investor_flag\" = {1}.\"for_qual_investor_flag\", \"weekend_flag\" = 
            {1}.\"weekend_flag\", \"blocked_tca_flag\" = {1}.\"blocked_tca_flag\", \"liquidity_flag\" = 
            {1}.\"liquidity_flag\", \"first_1min_candle_date\" = {1}.\"first_1min_candle_date\", 
            \"first_1day_candle_date\" = {1}.\"first_1day_candle_date\";'''.format(
                MyConnection.SHARES_TABLE,
                '\"excluded\"'
            )

            brand_data_command: str = '''INSERT INTO {0} (\"instrument_uid\", \"logo_name\", \"logo_base_color\", 
            \"text_color\") VALUES (:uid, :logo_name, :logo_base_color, :text_color) ON CONFLICT(\"instrument_uid\") 
            DO UPDATE SET \"logo_name\" = {1}.\"logo_name\", \"logo_base_color\" = {1}.\"logo_base_color\", 
            \"text_color\" = {1}.\"text_color\" WHERE \"logo_name\" != {1}.\"logo_name\" OR \"logo_base_color\" != 
            {1}.\"logo_base_color\" OR \"text_color\" != {1}.\"text_color\";'''.format(
                '\"{0}\"'.format(MyConnection.BRANDS_DATA_TABLE),
                '\"excluded\"'
            )

            db: QSqlDatabase = cls.getDatabase()
            if db.transaction():
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
                    query.bindValue(':trading_status', share.trading_status.name)
                    query.bindValue(':otc_flag', share.otc_flag)
                    query.bindValue(':buy_available_flag', share.buy_available_flag)
                    query.bindValue(':sell_available_flag', share.sell_available_flag)
                    query.bindValue(':div_yield_flag', share.div_yield_flag)
                    query.bindValue(':share_type', share.share_type.name)
                    query.bindValue(':min_price_increment', MyQuotation.__repr__(share.min_price_increment))
                    query.bindValue(':api_trade_available_flag', share.api_trade_available_flag)
                    query.bindValue(':uid', share.uid)
                    query.bindValue(':real_exchange', share.real_exchange.name)
                    query.bindValue(':position_uid', share.position_uid)
                    query.bindValue(':asset_uid', share.asset_uid)
                    query.bindValue(':for_iis_flag', share.for_iis_flag)
                    query.bindValue(':for_qual_investor_flag', share.for_qual_investor_flag)
                    query.bindValue(':weekend_flag', share.weekend_flag)
                    query.bindValue(':blocked_tca_flag', share.blocked_tca_flag)
                    query.bindValue(':liquidity_flag', share.liquidity_flag)
                    query.bindValue(':first_1min_candle_date', MyConnection.convertDateTimeToText(share.first_1min_candle_date))
                    query.bindValue(':first_1day_candle_date', MyConnection.convertDateTimeToText(share.first_1day_candle_date))

                    exec_flag: bool = query.exec()
                    assert exec_flag, query.lastError().text()

                    """===============Добавляем данные о бренде в таблицу данных о брендах==============="""
                    brand_data_query = QSqlQuery(db)
                    brand_data_prepare_flag: bool = brand_data_query.prepare(brand_data_command)
                    assert brand_data_prepare_flag, brand_data_query.lastError().text()
                    brand_data_query.bindValue(':uid', share.uid)
                    brand_data_query.bindValue(':logo_name', share.brand.logo_name)
                    brand_data_query.bindValue(':logo_base_color', share.brand.logo_base_color)
                    brand_data_query.bindValue(':text_color', share.brand.text_color)
                    brand_data_exec_flag: bool = brand_data_query.exec()
                    assert brand_data_exec_flag, brand_data_query.lastError().text()
                    """=================================================================================="""

                """=================Добавляем акции в таблицу запросов инструментов================="""
                '''----------------Удаляем акции из таблицы запросов инструментов----------------'''
                shares_uids_select: str = '''SELECT \"uid\" FROM \"{0}\" WHERE \"{0}\".\"instrument_type\" = \'{1}\'
                '''.format(MyConnection.INSTRUMENT_UIDS_TABLE, 'share')

                instruments_status_delete_sql_command: str = '''DELETE FROM \"{0}\" WHERE \"token\" = :token AND 
                \"status\" = :status AND \"uid\" in ({1});'''.format(
                    MyConnection.INSTRUMENT_STATUS_TABLE,
                    shares_uids_select
                )

                instruments_status_delete_query = QSqlQuery(db)
                instruments_status_delete_prepare_flag: bool = instruments_status_delete_query.prepare(instruments_status_delete_sql_command)
                assert instruments_status_delete_prepare_flag, instruments_status_delete_query.lastError().text()
                instruments_status_delete_query.bindValue(':token', token)
                instruments_status_delete_query.bindValue(':status', instrument_status.name)
                instruments_status_delete_exec_flag: bool = instruments_status_delete_query.exec()
                assert instruments_status_delete_exec_flag, instruments_status_delete_query.lastError().text()
                '''------------------------------------------------------------------------------'''

                '''---------------Добавляем акции в таблицу запросов инструментов---------------'''
                instruments_status_insert_sql_command: str = '''INSERT INTO \"{0}\" (\"token\", \"status\", \"uid\") 
                VALUES (:token, :status, :uid);'''.format(MyConnection.INSTRUMENT_STATUS_TABLE)

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
                raise SystemError('Не получилось начать транзакцию! db.lastError().text(): \'{0}\'.'.format(db.lastError().text()))

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
            sql_command += ''' ON CONFLICT(\"time\", \"instrument_uid\") DO UPDATE SET \"figi\" = \"excluded\".\"figi\", \"price\" = \"excluded\".\"price\" 
            WHERE \"figi\" != \"excluded\".\"figi\" OR \"price\" != \"excluded\".\"price\";'''
            '''-------------------------------------------------------------'''

            db: QSqlDatabase = cls.getDatabase()
            if db.transaction():
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
                raise SystemError('Не получилось начать транзакцию! db.lastError().text(): \'{0}\'.'.format(db.lastError().text()))

    @staticmethod
    def addAssetInstrument(db: QSqlDatabase, asset_uid: str, instrument: AssetInstrument):
        """Добавляет идентификаторы инструмента актива в таблицу идентификаторов инструментов активов."""

        def addInstrumentLinks(instrument_uid: str, links: list[InstrumentLink]):
            """Добавляет связанные инструменты в таблицу связей инструментов."""
            if links:  # Если список связанных инструментов не пуст.
                '''---------------------Создание SQL-запроса---------------------'''
                insert_link_sql_command: str = 'INSERT OR IGNORE INTO \"{0}\" (\"asset_uid\", \"asset_instrument_uid\", \"type\", \"linked_instrument_uid\") VALUES '.format(MyConnection.INSTRUMENT_LINKS_TABLE)
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
        :instrument_type, :ticker, :class_code, :instrument_kind, :position_uid);'''.format(
            MyConnection.ASSET_INSTRUMENTS_TABLE
        )

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
            if db.transaction():
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
                raise SystemError('Не получилось начать транзакцию! db.lastError().text(): \'{0}\'.'.format(db.lastError().text()))

    @classmethod
    def getCandles(cls, uid: str, interval: CandleInterval) -> list[HistoricCandle]:
        db: QtSql.QSqlDatabase = cls.getDatabase()
        if db.transaction():
            __select_candles_command: str = '''SELECT \"open\", \"high\", \"low\", \"close\", \"volume\", \"time\", 
            \"is_complete\" FROM \"{0}\" WHERE \"instrument_id\" = :uid and \"interval\" = :interval;'''.format(
                MyConnection.CANDLES_TABLE
            )

            candles_query = QtSql.QSqlQuery(db)
            candles_query.setForwardOnly(True)  # Возможно, это ускоряет извлечение данных.
            candles_prepare_flag: bool = candles_query.prepare(__select_candles_command)
            assert candles_prepare_flag, candles_query.lastError().text()
            candles_query.bindValue(':uid', uid)
            candles_query.bindValue(':interval', interval.name)
            candles_exec_flag: bool = candles_query.exec()
            assert candles_exec_flag, candles_query.lastError().text()

            candles: list[HistoricCandle] = []
            while candles_query.next():
                candles.append(MyConnection.getHistoricCandle(candles_query))

            commit_flag: bool = db.commit()  # Фиксирует транзакцию в базу данных.
            assert commit_flag, db.lastError().text()

            return candles
        else:
            raise SystemError('Не получилось начать транзакцию! db.lastError().text(): \'{0}\'.'.format(db.lastError().text()))

    @classmethod
    def insertHistoricCandles(cls, uid: str, interval: CandleInterval, candles: list[HistoricCandle]):
        """Добавляет свечи в таблицу исторических свечей."""
        if candles:  # Если список не пуст.
            sql_command: str = '''INSERT INTO \"{0}\" (\"instrument_id\", \"interval\", \"open\", \"high\", \"low\", 
            \"close\", \"volume\", \"time\", \"is_complete\") VALUES '''.format(MyConnection.CANDLES_TABLE)
            for i in range(len(candles)):
                if i > 0: sql_command += ', '  # Если добавляемая свеча не первая.
                sql_command += '(:uid, :interval, :open{0}, :high{0}, :low{0}, :close{0}, :volume{0}, :time{0}, :is_complete{0})'.format(i)
            sql_command += ''' ON CONFLICT (\"instrument_id\", \"interval\", \"time\") DO UPDATE SET \"open\" = 
            \"excluded\".\"open\", \"high\" = \"excluded\".\"high\", \"low\" = \"excluded\".\"low\", \"close\" = 
            \"excluded\".\"close\", \"volume\" = \"excluded\".\"volume\", \"is_complete\" = 
            \"excluded\".\"is_complete\" WHERE \"excluded\".\"open\" != \"open\" OR \"excluded\".\"high\" != \"high\" 
            OR \"excluded\".\"low\" != \"low\" OR \"excluded\".\"close\" != \"close\" OR \"excluded\".\"volume\" != 
            \"volume\" OR \"excluded\".\"is_complete\" != \"is_complete\";'''

            db: QtSql.QSqlDatabase = cls.getDatabase()
            if db.transaction():
                query = QtSql.QSqlQuery(db)
                prepare_flag: bool = query.prepare(sql_command)
                assert prepare_flag, query.lastError().text()

                query.bindValue(':uid', uid)
                query.bindValue(':interval', interval.name)
                for i, candle in enumerate(candles):
                    query.bindValue(':open{0}'.format(i), MyQuotation.__repr__(candle.open))
                    query.bindValue(':high{0}'.format(i), MyQuotation.__repr__(candle.high))
                    query.bindValue(':low{0}'.format(i), MyQuotation.__repr__(candle.low))
                    query.bindValue(':close{0}'.format(i), MyQuotation.__repr__(candle.close))
                    query.bindValue(':volume{0}'.format(i), candle.volume)
                    query.bindValue(':time{0}'.format(i), MyConnection.convertDateTimeToText(candle.time))
                    query.bindValue(':is_complete{0}'.format(i), MyConnection.convertBoolToBlob(candle.is_complete))

                exec_flag: bool = query.exec()
                assert exec_flag, query.lastError().text()

                commit_flag: bool = db.commit()  # Фиксирует транзакцию в базу данных.
                assert commit_flag, db.lastError().text()
            else:
                raise SystemError('Не получилось начать транзакцию! db.lastError().text(): \'{0}\'.'.format(db.lastError().text()))

    @classmethod
    def setDividends(cls, uid: str, dividends: list[Dividend]):
        """Обновляет купоны с переданным instrument_uid в таблице купонов."""
        db: QtSql.QSqlDatabase = cls.getDatabase()
        if db.transaction():
            def setDividendsColumnValue(value: str):
                """Заполняет столбец dividends значением."""
                update_dividends_command: str = 'UPDATE \"{0}\" SET \"dividends\" = :dividends WHERE \"uid\" = :uid;'.format(MyConnection.SHARES_TABLE)
                dividends_query = QtSql.QSqlQuery(db)
                dividends_prepare_flag: bool = dividends_query.prepare(update_dividends_command)
                assert dividends_prepare_flag, dividends_query.lastError().text()
                dividends_query.bindValue(':dividends', value)
                dividends_query.bindValue(':uid', uid)
                dividends_exec_flag: bool = dividends_query.exec()
                assert dividends_exec_flag, dividends_query.lastError().text()

            if dividends:  # Если список дивидендов не пуст.
                '''----Удаляет из таблицы дивидендов все дивиденды, имеющие переданный uid----'''
                delete_dividends_command: str = 'DELETE FROM \"{0}\" WHERE \"instrument_uid\" = :share_uid;'.format(MyConnection.DIVIDENDS_TABLE)
                delete_dividends_query = QtSql.QSqlQuery(db)
                delete_dividends_prepare_flag: bool = delete_dividends_query.prepare(delete_dividends_command)
                assert delete_dividends_prepare_flag, delete_dividends_query.lastError().text()
                delete_dividends_query.bindValue(':share_uid', uid)
                delete_dividends_exec_flag: bool = delete_dividends_query.exec()
                assert delete_dividends_exec_flag, delete_dividends_query.lastError().text()
                '''---------------------------------------------------------------------------'''

                '''-------------------------Добавляет дивиденды в таблицу дивидендов-------------------------'''
                add_dividends_command: str = '''INSERT INTO \"{0}\" (\"instrument_uid\", \"dividend_net\", 
                \"payment_date\", \"declared_date\", \"last_buy_date\", \"dividend_type\", \"record_date\", 
                \"regularity\", \"close_price\", \"yield_value\", \"created_at\") VALUES (:share_uid, :dividend_net, 
                :payment_date, :declared_date, :last_buy_date, :dividend_type, :record_date, :regularity, 
                :close_price, :yield_value, :created_at);'''.format(MyConnection.DIVIDENDS_TABLE)

                for dividend in dividends:
                    add_dividends_query = QtSql.QSqlQuery(db)
                    add_dividends_prepare_flag: bool = add_dividends_query.prepare(add_dividends_command)
                    assert add_dividends_prepare_flag, add_dividends_query.lastError().text()

                    add_dividends_query.bindValue(':share_uid', uid)
                    add_dividends_query.bindValue(':dividend_net', MyMoneyValue.__repr__(dividend.dividend_net))
                    add_dividends_query.bindValue(':payment_date', MyConnection.convertDateTimeToText(dividend.payment_date))
                    add_dividends_query.bindValue(':declared_date', MyConnection.convertDateTimeToText(dividend.declared_date))
                    add_dividends_query.bindValue(':last_buy_date', MyConnection.convertDateTimeToText(dividend.last_buy_date))
                    add_dividends_query.bindValue(':dividend_type', dividend.dividend_type)
                    add_dividends_query.bindValue(':record_date', MyConnection.convertDateTimeToText(dividend.record_date))
                    add_dividends_query.bindValue(':regularity', dividend.regularity)
                    add_dividends_query.bindValue(':close_price', MyMoneyValue.__repr__(dividend.close_price))
                    add_dividends_query.bindValue(':yield_value', MyQuotation.__repr__(dividend.yield_value))
                    add_dividends_query.bindValue(':created_at', MyConnection.convertDateTimeToText(dt=dividend.created_at, timespec='microseconds'))

                    add_dividends_exec_flag: bool = add_dividends_query.exec()
                    assert add_dividends_exec_flag, add_dividends_query.lastError().text()
                '''------------------------------------------------------------------------------------------'''

                setDividendsColumnValue('Yes')  # Заполняем столбец dividends значением.
            else:
                setDividendsColumnValue('No')  # Заполняем столбец dividends значением.

            commit_flag: bool = db.commit()  # Фиксирует транзакцию в базу данных.
            assert commit_flag, db.lastError().text()
        else:
            raise SystemError('Не получилось начать транзакцию! db.lastError().text(): \'{0}\'.'.format(db.lastError().text()))

    @classmethod
    def setCoupons(cls, uid: str, coupons: list[Coupon]):
        """Обновляет купоны с переданным figi в таблице купонов."""
        db: QtSql.QSqlDatabase = cls.getDatabase()
        if db.transaction():
            def setCouponsColumnValue(value: str):
                """Заполняет столбец coupons значением."""
                update_coupons_query_str: str = 'UPDATE \"{0}\" SET \"coupons\" = :coupons WHERE \"uid\" = :bond_uid;'.format(MyConnection.BONDS_TABLE)
                coupons_query = QtSql.QSqlQuery(db)
                coupons_prepare_flag: bool = coupons_query.prepare(update_coupons_query_str)
                assert coupons_prepare_flag, coupons_query.lastError().text()
                coupons_query.bindValue(':coupons', value)
                coupons_query.bindValue(':bond_uid', uid)
                coupons_exec_flag: bool = coupons_query.exec()
                assert coupons_exec_flag, coupons_query.lastError().text()

            if coupons:  # Если список купонов не пуст.
                '''----Удаляет из таблицы купонов все купоны, имеющие переданный uid----'''
                delete_coupons_query_str: str = 'DELETE FROM \"{0}\" WHERE \"instrument_uid\" = :bond_uid;'.format(MyConnection.COUPONS_TABLE)
                delete_coupons_query = QtSql.QSqlQuery(db)
                delete_coupons_prepare_flag: bool = delete_coupons_query.prepare(delete_coupons_query_str)
                assert delete_coupons_prepare_flag, delete_coupons_query.lastError().text()
                delete_coupons_query.bindValue(':bond_uid', uid)
                delete_coupons_exec_flag: bool = delete_coupons_query.exec()
                assert delete_coupons_exec_flag, delete_coupons_query.lastError().text()
                '''---------------------------------------------------------------------'''

                '''---------------------------Добавляет купоны в таблицу купонов---------------------------'''
                add_coupons_command: str = '''INSERT INTO \"{0}\" (\"instrument_uid\", \"figi\", \"coupon_date\", 
                \"coupon_number\", \"fix_date\", \"pay_one_bond\", \"coupon_type\", \"coupon_start_date\", 
                \"coupon_end_date\", \"coupon_period\") VALUES '''.format(MyConnection.COUPONS_TABLE)
                for i in range(len(coupons)):
                    if i > 0: add_coupons_command += ', '  # Если добавляемый купон не первый.
                    add_coupons_command += '''(:bond_uid{0}, :figi{0}, :coupon_date{0}, :coupon_number{0}, 
                    :fix_date{0}, :pay_one_bond{0}, :coupon_type{0}, :coupon_start_date{0}, :coupon_end_date{0}, 
                    :coupon_period{0})'''.format(i)
                add_coupons_command += ';'

                add_coupons_query = QtSql.QSqlQuery(db)
                add_coupons_prepare_flag: bool = add_coupons_query.prepare(add_coupons_command)
                assert add_coupons_prepare_flag, add_coupons_query.lastError().text()

                for i, coupon in enumerate(coupons):
                    add_coupons_query.bindValue(':bond_uid{0}'.format(i), uid)
                    add_coupons_query.bindValue(':figi{0}'.format(i), coupon.figi)
                    add_coupons_query.bindValue(':coupon_date{0}'.format(i), MyConnection.convertDateTimeToText(coupon.coupon_date))
                    add_coupons_query.bindValue(':coupon_number{0}'.format(i), coupon.coupon_number)
                    add_coupons_query.bindValue(':fix_date{0}'.format(i), MyConnection.convertDateTimeToText(coupon.fix_date))
                    add_coupons_query.bindValue(':pay_one_bond{0}'.format(i), MyMoneyValue.__repr__(coupon.pay_one_bond))
                    add_coupons_query.bindValue(':coupon_type{0}'.format(i), coupon.coupon_type.name)
                    add_coupons_query.bindValue(':coupon_start_date{0}'.format(i), MyConnection.convertDateTimeToText(coupon.coupon_start_date))
                    add_coupons_query.bindValue(':coupon_end_date{0}'.format(i), MyConnection.convertDateTimeToText(coupon.coupon_end_date))
                    add_coupons_query.bindValue(':coupon_period{0}'.format(i), coupon.coupon_period)

                add_coupons_exec_flag: bool = add_coupons_query.exec()
                assert add_coupons_exec_flag, add_coupons_query.lastError().text()
                '''----------------------------------------------------------------------------------------'''

                setCouponsColumnValue('Yes')  # Заполняем столбец coupons значением.
            else:
                setCouponsColumnValue('No')  # Заполняем столбец coupons значением.

            commit_flag: bool = db.commit()  # Фиксирует транзакцию в базу данных.
            assert commit_flag, db.lastError().text()
        else:
            raise SystemError('Не получилось начать транзакцию! db.lastError().text(): \'{0}\'.'.format(db.lastError().text()))

    @classmethod
    def insertAssetFull(cls, assetfull: AssetFull):
        """Добавляет AssetFull в таблицу активов."""
        insert_asset_sql_command: str = '''INSERT INTO \"{0}\" (\"uid\", \"type\", \"name\", \"name_brief\", 
        \"description\", \"deleted_at\", \"required_tests\", \"gos_reg_code\", \"cfi\", \"code_nsd\", \"status\", 
        \"brand_uid\", \"updated_at\", \"br_code\", \"br_code_name\") VALUES (:uid, :type, :name, :name_brief, 
        :description, :deleted_at, :required_tests, :gos_reg_code, :cfi, :code_nsd, :status, :brand_uid, 
        :updated_at, :br_code, :br_code_name) ON CONFLICT(\"uid\") DO UPDATE SET \"type\" = {1}.\"type\", \"name\" 
        = {1}.\"name\", \"name_brief\" = {1}.\"name_brief\", \"description\" = {1}.\"description\", \"deleted_at\" = 
        {1}.\"deleted_at\", \"required_tests\" = {1}.\"required_tests\", \"gos_reg_code\" = {1}.\"gos_reg_code\", 
        \"cfi\" = {1}.\"cfi\", \"code_nsd\" = {1}.\"code_nsd\", \"status\" = {1}.\"status\", \"brand_uid\" = 
        {1}.\"brand_uid\", \"updated_at\" = {1}.\"updated_at\", \"br_code\" = {1}.\"br_code\", \"br_code_name\" = 
        {1}.\"br_code_name\";'''.format(MyConnection.ASSETS_TABLE, '\"excluded\"')

        insert_brands_command: str = '''INSERT INTO \"{0}\" (\"uid\", \"name\", \"description\", \"info\", \"company\", 
        \"sector\", \"country_of_risk\", \"country_of_risk_name\") VALUES (:uid, :name, :description, :info, :company, 
        :sector, :country_of_risk, :country_of_risk_name) ON CONFLICT (\"uid\") DO UPDATE SET \"name\" = {1}.\"name\", 
        \"description\" = {1}.\"description\", \"info\" = {1}.\"info\", \"company\" = {1}.\"company\", \"sector\" = 
        {1}.\"sector\", \"country_of_risk\" = {1}.\"country_of_risk\", \"country_of_risk_name\" = 
        {1}.\"country_of_risk_name\";'''.format(MyConnection.BRANDS_TABLE, '\"excluded\"')

        insert_asset_currency_command: str = '''INSERT INTO \"{0}\" (\"asset_uid\", \"base_currency\") VALUES 
        (:asset_uid, :asset_currency) ON CONFLICT(\"asset_uid\") DO UPDATE SET \"base_currency\" = 
        {1}.\"base_currency\";'''.format(
            MyConnection.ASSET_CURRENCIES_TABLE,
            '\"excluded\"'
        )

        db: QSqlDatabase = cls.getDatabase()
        if db.transaction():
            def insertBrand(brand: Brand):
                """Добавляет брэнд в таблицу брэндов."""
                insert_brands_query = QSqlQuery(db)
                insert_brands_prepare_flag: bool = insert_brands_query.prepare(insert_brands_command)
                assert insert_brands_prepare_flag, insert_brands_query.lastError().text()
                insert_brands_query.bindValue(':uid', brand.uid)
                insert_brands_query.bindValue(':name', brand.name)
                insert_brands_query.bindValue(':description', brand.description)
                insert_brands_query.bindValue(':info', brand.info)
                insert_brands_query.bindValue(':company', brand.company)
                insert_brands_query.bindValue(':sector', brand.sector)
                insert_brands_query.bindValue(':country_of_risk', brand.country_of_risk)
                insert_brands_query.bindValue(':country_of_risk_name', brand.country_of_risk_name)
                insert_brands_exec_flag: bool = insert_brands_query.exec()
                assert insert_brands_exec_flag, insert_brands_query.lastError().text()

            insertBrand(assetfull.brand)  # Добавляем брэнд в таблицу брэндов.

            '''------------------Добавляем AssetFull в таблицу активов------------------'''
            insert_asset_query = QSqlQuery(db)
            insert_asset_prepare_flag: bool = insert_asset_query.prepare(insert_asset_sql_command)
            assert insert_asset_prepare_flag, insert_asset_query.lastError().text()

            insert_asset_query.bindValue(':uid', assetfull.uid)
            insert_asset_query.bindValue(':type', assetfull.type.name)
            insert_asset_query.bindValue(':name', assetfull.name)
            insert_asset_query.bindValue(':name_brief', assetfull.name_brief)
            insert_asset_query.bindValue(':description', assetfull.description)
            insert_asset_query.bindValue(':deleted_at', MyConnection.convertDateTimeToText(assetfull.deleted_at))
            insert_asset_query.bindValue(':required_tests', MyConnection.convertStrListToStr(assetfull.required_tests))
            insert_asset_query.bindValue(':gos_reg_code', assetfull.gos_reg_code)
            insert_asset_query.bindValue(':cfi', assetfull.cfi)
            insert_asset_query.bindValue(':code_nsd', assetfull.code_nsd)
            insert_asset_query.bindValue(':status', assetfull.status)
            insert_asset_query.bindValue(':brand_uid', assetfull.brand.uid)
            insert_asset_query.bindValue(':updated_at', MyConnection.convertDateTimeToText(dt=assetfull.updated_at, timespec='microseconds'))
            insert_asset_query.bindValue(':br_code', assetfull.br_code)
            insert_asset_query.bindValue(':br_code_name', assetfull.br_code_name)

            insert_asset_exec_flag: bool = insert_asset_query.exec()
            assert insert_asset_exec_flag, insert_asset_query.lastError().text()
            '''-------------------------------------------------------------------------'''

            '''---Если тип актива соответствует валюте, то добавляем валюту в таблицу валют активов---'''
            if assetfull.type is AssetType.ASSET_TYPE_CURRENCY:
                def insertAssetCurrency(asset_uid: str, asset_currency: AssetCurrency):
                    """Добавляет валюту в таблицу валют активов."""
                    insert_asset_currency_query = QSqlQuery(db)
                    insert_asset_currency_prepare_flag: bool = insert_asset_currency_query.prepare(insert_asset_currency_command)
                    assert insert_asset_currency_prepare_flag, insert_asset_currency_query.lastError().text()
                    insert_asset_currency_query.bindValue(':asset_uid', asset_uid)
                    insert_asset_currency_query.bindValue(':asset_currency', asset_currency.base_currency)
                    insert_asset_currency_exec_flag: bool = insert_asset_currency_query.exec()
                    assert insert_asset_currency_exec_flag, insert_asset_currency_query.lastError().text()

                insertAssetCurrency(assetfull.uid, assetfull.currency)  # Добавляем валюту в таблицу валют активов.
            else:
                assert assetfull.currency is None, 'Если тип актива не соответствует валюте, то поле \"currency\" должно иметь значение None, а получено {0}!'.format(assetfull.currency)
            '''---------------------------------------------------------------------------------------'''

            '''--Если тип актива соответствует ценной бумаге, то добавляем ценную бумагу в таблицу ценных бумаг--'''
            if assetfull.type is AssetType.ASSET_TYPE_SECURITY:
                def insertAssetSecurity(asset_uid: str, security: AssetSecurity):
                    """Добавляет ценную бумагу в таблицу ценных бумаг активов."""
                    insert_asset_security_sql_command: str = '''INSERT INTO \"{0}\" (\"asset_uid\", \"isin\", \"type\", 
                    \"instrument_kind\") VALUES (:asset_uid, :isin, :type, :instrument_kind) ON CONFLICT(\"asset_uid\") 
                    DO UPDATE SET \"isin\" = {1}.\"isin\", \"type\" = {1}.\"type\", \"instrument_kind\" = 
                    {1}.\"instrument_kind\";'''.format(MyConnection.ASSET_SECURITIES_TABLE, '\"excluded\"')
                    insert_asset_security_query = QSqlQuery(db)
                    insert_asset_security_prepare_flag: bool = insert_asset_security_query.prepare(insert_asset_security_sql_command)
                    assert insert_asset_security_prepare_flag, insert_asset_security_query.lastError().text()
                    insert_asset_security_query.bindValue(':asset_uid', asset_uid)
                    insert_asset_security_query.bindValue(':isin', security.isin)
                    insert_asset_security_query.bindValue(':type', security.type)
                    insert_asset_security_query.bindValue(':instrument_kind', security.instrument_kind.name)
                    insert_asset_security_exec_flag: bool = insert_asset_security_query.exec()
                    assert insert_asset_security_exec_flag, insert_asset_security_query.lastError().text()

                insertAssetSecurity(assetfull.uid, assetfull.security)
            else:
                assert assetfull.security is None, 'Если тип актива не соответствует ценной бумаге, то поле \"security\" должно иметь значение None, а получено {0}!'.format(assetfull.security)
            '''--------------------------------------------------------------------------------------------------'''

            for instrument in assetfull.instruments:
                MainConnection.addAssetInstrument(db, assetfull.uid, instrument)  # Добавляем идентификаторы инструмента актива в таблицу идентификаторов инструментов активов.

            commit_flag: bool = db.commit()  # Фиксирует транзакцию в базу данных.
            assert commit_flag, db.lastError().text()
        else:
            raise SystemError('Не получилось начать транзакцию! db.lastError().text(): \'{0}\'.'.format(db.lastError().text()))
