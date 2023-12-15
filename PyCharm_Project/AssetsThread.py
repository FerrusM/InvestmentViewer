from datetime import datetime
from PyQt6.QtCore import QThread, pyqtSignal, QObject
from PyQt6.QtSql import QSqlDatabase, QSqlQuery
from tinkoff.invest import Asset, AssetFull, Brand
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
            db: QSqlDatabase = cls.getDatabase()
            query = QSqlQuery(db)
            query.prepare('''
            INSERT INTO "Brands" (uid, name, description, info, company, sector, country_of_risk, country_of_risk_name) 
            VALUES (:uid, :name, :description, :info, :company, :sector, :country_of_risk, :country_of_risk_name)
            ON CONFLICT (uid) DO UPDATE SET name = excluded.name, description = excluded.description, 
            info = excluded.info, company = excluded.company, sector = excluded.sector, 
            country_of_risk = excluded.country_of_risk, country_of_risk_name = excluded.country_of_risk_name;
            ''')
            query.bindValue(':uid', brand.uid)
            query.bindValue(':name', brand.name)
            query.bindValue(':description', brand.description)
            query.bindValue(':info', brand.info)
            query.bindValue(':company', brand.company)
            query.bindValue(':sector', brand.sector)
            query.bindValue(':country_of_risk', brand.country_of_risk)
            query.bindValue(':country_of_risk_name', brand.country_of_risk_name)
            exec_flag: bool = query.exec()
            assert exec_flag, query.lastError().text()

        @classmethod
        def insertAssetFull(cls, assetfull: AssetFull):
            """Добавляет AssetFull в таблицу активов."""
            db: QSqlDatabase = cls.getDatabase()

            transaction_flag: bool = db.transaction()  # Начинает транзакцию в базе данных.
            assert transaction_flag, db.lastError().text()

            if transaction_flag:
                cls.insertBrand(assetfull.brand)  # Добавляем брэнд в таблицу брэндов.

                query = QSqlQuery(db)
                query.prepare('''
                INSERT INTO "Assets" ("uid", "type", "name", "name_brief", "description", "deleted_at", "required_tests", "gos_reg_code", "cfi", "code_nsd", "status", "brand_uid", "updated_at", "br_code", "br_code_name") 
                VALUES (:uid, :type, :name, :name_brief, :description, :deleted_at, :required_tests, :gos_reg_code, :cfi, :code_nsd, :status, :brand_uid, :updated_at, :br_code, :br_code_name)
                ON CONFLICT("uid") DO UPDATE SET "type" = "excluded"."type", "name" = "excluded"."name", "name_brief" = "excluded"."name_brief", "description" = "excluded"."description", 
                "deleted_at" = "excluded"."deleted_at", "required_tests" = "excluded"."required_tests", "gos_reg_code" = "excluded"."gos_reg_code", "cfi" = "excluded"."cfi", "code_nsd" = "excluded"."code_nsd",
                "status" = "excluded"."status", "brand_uid" = "excluded"."brand_uid", "updated_at" = "excluded"."updated_at", "br_code" = "excluded"."br_code", "br_code_name" = "excluded"."br_code_name";
                ''')
                query.bindValue(':uid', assetfull.uid)
                query.bindValue(':type', int(assetfull.type))
                query.bindValue(':name', assetfull.name)
                query.bindValue(':name_brief', assetfull.name_brief)
                query.bindValue(':description', assetfull.description)
                query.bindValue(':deleted_at', MyConnection.convertDateTimeToText(assetfull.deleted_at))
                query.bindValue(':required_tests', MyConnection.convertStrListToStr(assetfull.required_tests))
                query.bindValue(':gos_reg_code', assetfull.gos_reg_code)
                query.bindValue(':cfi', assetfull.cfi)
                query.bindValue(':code_nsd', assetfull.code_nsd)
                query.bindValue(':status', assetfull.status)
                query.bindValue(':brand_uid', assetfull.brand.uid)
                query.bindValue(':updated_at', MyConnection.convertDateTimeToText(dt=assetfull.updated_at, timespec='microseconds'))
                query.bindValue(':br_code', assetfull.br_code)
                query.bindValue(':br_code_name', assetfull.br_code_name)
                exec_flag: bool = query.exec()
                assert exec_flag, query.lastError().text()

                for instrument in assetfull.instruments:
                    MainConnection.addAssetInstrument(db, assetfull.uid, instrument)  # Добавляем идентификаторы инструмента актива в таблицу идентификаторов инструментов активов.

                commit_flag: bool = db.commit()  # Фиксирует транзакцию в базу данных.
                assert commit_flag, db.lastError().text()

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