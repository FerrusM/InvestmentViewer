from datetime import datetime
from PyQt6.QtCore import QThread, pyqtSignal, QObject
from PyQt6.QtSql import QSqlDatabase, QSqlQuery
from tinkoff.invest import Asset, AssetFull, Brand, AssetCurrency, AssetType, AssetSecurity
from Classes import TokenClass, MyConnection
from LimitClasses import LimitPerMinuteSemaphore
from MyDatabase import MainConnection
from MyDateTime import getUtcDateTime
from MyRequests import MyResponse, getAssetBy, RequestTryClass


class AssetClass(QObject):
    """Класс, содержащий всю доступную информацию об активе."""
    setAssetFull_signal: pyqtSignal = pyqtSignal()  # Сигнал, испускаемый при изменении информации об активе.

    def __init__(self, asset: Asset):
        super().__init__()  # __init__() QObject.
        self.asset: Asset = asset
        self.full_asset: AssetFull | None = None

    def setAssetFull(self, assetfull: AssetFull):
        """Заполняет информацию об активе."""
        self.full_asset = assetfull
        self.setAssetFull_signal.emit()  # Испускаем сигнал о том, что информация об активе была изменена.


class AssetsThread(QThread):
    """Поток получения полной информации об активах."""
    class DatabaseConnection(MyConnection):
        CONNECTION_NAME: str = 'InvestmentViewer_AssetsThread'

        @classmethod
        def insertBrand(cls, brand: Brand):
            """Добавляет брэнд в таблицу брэндов."""
            insert_brands_sql_command: str = '''
            INSERT INTO \"{0}\" (\"uid\", \"name\", \"description\", \"info\", \"company\", \"sector\", 
            \"country_of_risk\", \"country_of_risk_name\") VALUES (:uid, :name, :description, :info, :company, :sector, 
            :country_of_risk, :country_of_risk_name) ON CONFLICT (\"uid\") DO UPDATE SET \"name\" = {1}.\"name\", 
            \"description\" = {1}.\"description\", \"info\" = {1}.\"info\", \"company\" = {1}.\"company\", 
            \"sector\" = {1}.\"sector\", \"country_of_risk\" = {1}.\"country_of_risk\", \"country_of_risk_name\" = 
            {1}.\"country_of_risk_name\";'''.format(MyConnection.BRANDS_TABLE, '\"excluded\"')
            db: QSqlDatabase = cls.getDatabase()
            insert_brands_query = QSqlQuery(db)
            insert_brands_prepare_flag: bool = insert_brands_query.prepare(insert_brands_sql_command)
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

        @classmethod
        def insertAssetCurrency(cls, asset_uid: str, asset_currency: AssetCurrency):
            """Добавляет валюту в таблицу валют активов."""
            insert_asset_currency_sql_command: str = '''INSERT INTO \"{0}\" (\"asset_uid\", \"base_currency\") 
            VALUES (:asset_uid, :asset_currency) ON CONFLICT(\"asset_uid\") DO UPDATE SET 
            \"base_currency\" = {1}.\"base_currency\";'''.format(MyConnection.ASSET_CURRENCIES_TABLE, '\"excluded\"')
            db: QSqlDatabase = cls.getDatabase()
            insert_asset_currency_query = QSqlQuery(db)
            insert_asset_currency_prepare_flag: bool = insert_asset_currency_query.prepare(insert_asset_currency_sql_command)
            assert insert_asset_currency_prepare_flag, insert_asset_currency_query.lastError().text()
            insert_asset_currency_query.bindValue(':asset_uid', asset_uid)
            insert_asset_currency_query.bindValue(':asset_currency', asset_currency.base_currency)
            insert_asset_currency_exec_flag: bool = insert_asset_currency_query.exec()
            assert insert_asset_currency_exec_flag, insert_asset_currency_query.lastError().text()

        @classmethod
        def insertAssetFull(cls, assetfull: AssetFull):
            """Добавляет AssetFull в таблицу активов."""
            insert_asset_sql_command: str = '''
            INSERT INTO \"{0}\" (\"uid\", \"type\", \"name\", \"name_brief\", \"description\", \"deleted_at\", 
            \"required_tests\", \"gos_reg_code\", \"cfi\", \"code_nsd\", \"status\", \"brand_uid\", \"updated_at\", 
            \"br_code\", \"br_code_name\") VALUES (:uid, :type, :name, :name_brief, :description, :deleted_at, 
            :required_tests, :gos_reg_code, :cfi, :code_nsd, :status, :brand_uid, :updated_at, :br_code, :br_code_name)
            ON CONFLICT(\"uid\") DO UPDATE SET \"type\" = {1}.\"type\", \"name\" = {1}.\"name\", 
            \"name_brief\" = {1}.\"name_brief\", \"description\" = {1}.\"description\", 
            \"deleted_at\" = {1}.\"deleted_at\", \"required_tests\" = {1}.\"required_tests\", 
            \"gos_reg_code\" = {1}.\"gos_reg_code\", \"cfi\" = {1}.\"cfi\", \"code_nsd\" = {1}.\"code_nsd\",
            \"status\" = {1}.\"status\", \"brand_uid\" = {1}.\"brand_uid\", \"updated_at\" = {1}.\"updated_at\", 
            \"br_code\" = {1}.\"br_code\", \"br_code_name\" = {1}.\"br_code_name\";
            '''.format(MyConnection.ASSETS_TABLE, '\"excluded\"')
            db: QSqlDatabase = cls.getDatabase()
            transaction_flag: bool = db.transaction()  # Начинает транзакцию в базе данных.
            if transaction_flag:
                cls.insertBrand(assetfull.brand)  # Добавляем брэнд в таблицу брэндов.

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
                    cls.insertAssetCurrency(assetfull.uid, assetfull.currency)  # Добавляем валюту в таблицу валют активов.
                else:
                    assert assetfull.currency is None, 'Если тип актива не соответствует валюте, то поле \"currency\" должно иметь значение None, а получено {0}!'.format(assetfull.currency)
                '''---------------------------------------------------------------------------------------'''

                '''--Если тип актива соответствует ценной бумаге, то добавляем ценную бумагу в таблицу ценных бумаг--'''
                if assetfull.type is AssetType.ASSET_TYPE_SECURITY:
                    def insertAssetSecurity(asset_uid: str, security: AssetSecurity):
                        """Добавляет ценную бумагу в таблицу ценных бумаг активов."""
                        insert_asset_security_sql_command: str = '''INSERT INTO \"{0}\" (\"asset_uid\", \"isin\", 
                        \"type\", \"instrument_kind\") VALUES (:asset_uid, :isin, :type, :instrument_kind) ON 
                        CONFLICT(\"asset_uid\") DO UPDATE SET \"isin\" = {1}.\"isin\", \"type\" = {1}.\"type\", 
                        \"instrument_kind\" = {1}.\"instrument_kind\";'''.format(
                            MyConnection.ASSET_SECURITIES_TABLE,
                            '\"excluded\"'
                        )
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
                assert transaction_flag, db.lastError().text()

    receive_assetfulls_method_name: str = 'GetAssetBy'

    '''------------------------Сигналы------------------------'''
    printText_signal: pyqtSignal = pyqtSignal(str)  # Сигнал для отображения сообщений в консоли.
    releaseSemaphore_signal: pyqtSignal = pyqtSignal(LimitPerMinuteSemaphore, int)  # Сигнал для освобождения ресурсов семафора из основного потока.
    '''-------------------------------------------------------'''

    '''-----------------Сигналы progressBar'а-----------------'''
    setProgressBarRange_signal: pyqtSignal = pyqtSignal(int, int)  # Сигнал для установления минимума и максимума progressBar'а заполнения купонов.
    setProgressBarValue_signal: pyqtSignal = pyqtSignal(int)  # Сигнал для изменения прогресса в progressBar'е.
    '''-------------------------------------------------------'''

    def __init__(self, token_class: TokenClass, assets: list[AssetClass]):
        super().__init__()  # __init__() QThread.
        self.token: TokenClass = token_class
        self.semaphore: LimitPerMinuteSemaphore | None = self.token.unary_limits_manager.getSemaphore(self.receive_assetfulls_method_name)
        self.assets: list[AssetClass] = assets

        '''------------Статистические переменные------------'''
        self.request_count: int = 0  # Общее количество запросов.
        self.control_point: datetime | None = None  # Начальная точка отсчёта времени.
        '''-------------------------------------------------'''

    def run(self) -> None:
        def printInConsole(text: str):
            self.printText_signal.emit('{0}: {1}'.format(AssetsThread.__name__, text))

        def ifFirstIteration() -> bool:
            """Возвращает True, если поток не сделал ни одного запроса. Иначе возвращает False."""
            return self.request_count > 0

        if self.semaphore is None:
            printInConsole('Лимит для метода {0} не найден.'.format(self.receive_assetfulls_method_name))
        else:
            self.DatabaseConnection.open()  # Открываем соединение с БД.

            assets_count: int = len(self.assets)  # Количество активов.
            self.setProgressBarRange_signal.emit(0, assets_count)  # Задаёт минимум и максимум progressBar'а.

            for i, asset_class in enumerate(self.assets):
                if self.isInterruptionRequested():
                    printInConsole('Поток прерван.')
                    break

                asset_number: int = i + 1  # Номер текущего актива.
                self.setProgressBarValue_signal.emit(asset_number)  # Отображаем прогресс в progressBar.

                assetfull_try_count: RequestTryClass = RequestTryClass()
                assetfull_response: MyResponse = MyResponse()
                while assetfull_try_count and not assetfull_response.ifDataSuccessfullyReceived():
                    if self.isInterruptionRequested():
                        printInConsole('Поток прерван.')
                        break

                    """------------------------------Выполнение запроса------------------------------"""
                    self.semaphore.acquire(1)  # Блокирует вызов до тех пор, пока не будет доступно достаточно ресурсов.

                    '''----------------Подсчёт статистических параметров----------------'''
                    if ifFirstIteration():  # Не выполняется до второго запроса.
                        delta: float = (getUtcDateTime() - self.control_point).total_seconds()  # Секунд прошло с последнего запроса.
                        printInConsole('{0} из {1} ({2:.2f}с)'.format(asset_number, assets_count, delta))
                    else:
                        printInConsole('{0} из {1}'.format(asset_number, assets_count))
                    self.control_point = getUtcDateTime()  # Промежуточная точка отсчёта времени.
                    '''-----------------------------------------------------------------'''

                    assetfull_response = getAssetBy(self.token.token, asset_class.asset.uid)
                    assert assetfull_response.request_occurred, 'Запрос информации об активе не был произведён.'
                    self.request_count += 1  # Подсчитываем запрос.
                    self.releaseSemaphore_signal.emit(self.semaphore, 1)  # Освобождаем ресурсы семафора из основного потока.

                    '''------------------------Сообщаем об ошибке------------------------'''
                    if assetfull_response.request_error_flag:
                        printInConsole('RequestError {0}'.format(assetfull_response.request_error))
                    elif assetfull_response.exception_flag:
                        printInConsole('Exception {0}'.format(assetfull_response.exception))
                    '''------------------------------------------------------------------'''
                    """------------------------------------------------------------------------------"""
                    assetfull_try_count += 1

                assetfull: AssetFull | None = assetfull_response.response_data.asset if assetfull_response.ifDataSuccessfullyReceived() else None
                if assetfull is None: continue  # Если поток был прерван или если информация не была получена.
                asset_class.setAssetFull(assetfull)  # Записываем информацию об активе в AssetClass.
                self.DatabaseConnection.insertAssetFull(assetfull)  # Добавляем AssetFull в таблицу активов.

            self.DatabaseConnection.removeConnection()  # Удаляем соединение с БД.