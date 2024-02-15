from datetime import datetime
from PyQt6 import QtCore, QtSql
# from grpc import StatusCode
from tinkoff.invest import Dividend, RequestError
from Classes import TokenClass, MyConnection
from LimitClasses import LimitPerMinuteSemaphore
from MyDateTime import getUtcDateTime
from MyMoneyValue import MyMoneyValue
from MyQuotation import MyQuotation
from MyRequests import MyResponse, getDividends, RequestTryClass
from MyShareClass import MyShareClass


class DividendsThread(QtCore.QThread):
    """Поток получения дивидендов."""
    class DatabaseConnection(MyConnection):
        CONNECTION_NAME: str = 'InvestmentViewer_DividendsThread'

        @classmethod
        def setDividends(cls, uid: str, dividends: list[Dividend]):
            """Обновляет купоны с переданным figi в таблице купонов."""
            db: QtSql.QSqlDatabase = cls.getDatabase()
            if db.transaction():
                def setDividendsColumnValue(value: str):
                    """Заполняет столбец dividends значением."""
                    update_dividends_query_str: str = 'UPDATE \"{0}\" SET \"dividends\" = :dividends WHERE \"uid\" = :uid;'.format(MyConnection.SHARES_TABLE)
                    dividends_query = QtSql.QSqlQuery(db)
                    dividends_prepare_flag: bool = dividends_query.prepare(update_dividends_query_str)
                    assert dividends_prepare_flag, dividends_query.lastError().text()
                    dividends_query.bindValue(':dividends', value)
                    dividends_query.bindValue(':uid', uid)
                    dividends_exec_flag: bool = dividends_query.exec()
                    assert dividends_exec_flag, dividends_query.lastError().text()

                if dividends:  # Если список дивидендов не пуст.
                    '''----Удаляет из таблицы дивидендов все дивиденды, имеющие переданный uid----'''
                    delete_dividends_query_str: str = 'DELETE FROM \"{0}\" WHERE \"instrument_uid\" = :share_uid;'.format(MyConnection.DIVIDENDS_TABLE)
                    delete_dividends_query = QtSql.QSqlQuery(db)
                    delete_dividends_prepare_flag: bool = delete_dividends_query.prepare(delete_dividends_query_str)
                    assert delete_dividends_prepare_flag, delete_dividends_query.lastError().text()
                    delete_dividends_query.bindValue(':share_uid', uid)
                    delete_dividends_exec_flag: bool = delete_dividends_query.exec()
                    assert delete_dividends_exec_flag, delete_dividends_query.lastError().text()
                    '''---------------------------------------------------------------------------'''

                    '''-------------------------Добавляет дивиденды в таблицу дивидендов-------------------------'''
                    add_dividends_sql_command: str = '''INSERT INTO \"{0}\" (\"instrument_uid\", \"dividend_net\", 
                    \"payment_date\", \"declared_date\", \"last_buy_date\", \"dividend_type\", \"record_date\", 
                    \"regularity\", \"close_price\", \"yield_value\", \"created_at\") VALUES (:share_uid, :dividend_net, 
                    :payment_date, :declared_date, :last_buy_date, :dividend_type, :record_date, :regularity, 
                    :close_price, :yield_value, :created_at);'''.format(MyConnection.DIVIDENDS_TABLE)

                    for dividend in dividends:
                        add_dividends_query = QtSql.QSqlQuery(db)
                        add_dividends_prepare_flag: bool = add_dividends_query.prepare(add_dividends_sql_command)
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

    receive_dividends_method_name: str = 'GetDividends'

    """------------------------Сигналы------------------------"""
    printText_signal: QtCore.pyqtSignal = QtCore.pyqtSignal(str)  # Сигнал для отображения сообщений в консоли.
    """-------------------------------------------------------"""

    """-----------------Сигналы progressBar'а-----------------"""
    # Сигнал для установления минимума и максимума progressBar'а заполнения купонов.
    setProgressBarRange_signal: QtCore.pyqtSignal = QtCore.pyqtSignal(int, int)
    setProgressBarValue_signal: QtCore.pyqtSignal = QtCore.pyqtSignal(int)  # Сигнал для изменения прогресса в progressBar'е.
    """-------------------------------------------------------"""

    """--------------------Сигналы ошибок--------------------"""
    showRequestError_signal: QtCore.pyqtSignal = QtCore.pyqtSignal(str, RequestError)  # Сигнал для отображения исключения RequestError.
    showException_signal: QtCore.pyqtSignal = QtCore.pyqtSignal(str, Exception)  # Сигнал для отображения исключения.
    """------------------------------------------------------"""

    releaseSemaphore_signal: QtCore.pyqtSignal = QtCore.pyqtSignal(LimitPerMinuteSemaphore, int)  # Сигнал для освобождения ресурсов семафора из основного потока.

    def __init__(self, token_class: TokenClass, share_class_list: list[MyShareClass], parent: QtCore.QObject | None = None):
        super().__init__(parent=parent)
        self.token: TokenClass = token_class
        self.semaphore: LimitPerMinuteSemaphore | None = token_class.unary_limits_manager.getSemaphore(self.receive_dividends_method_name)
        self.shares: list[MyShareClass] = share_class_list

        """------------Статистические переменные------------"""
        self.request_count: int = 0  # Общее количество запросов.
        self.exception_count: int = 0  # Количество исключений.
        self.request_error_count: int = 0  # Количество RequestError.

        self.start_time: datetime | None = None  # Время начала потока.
        self.end_time: datetime | None = None  # Время завершения потока.

        self.control_point: datetime | None = None  # Начальная точка отсчёта времени.

        self.requests_time: float = 0.0
        """-------------------------------------------------"""

    def run(self) -> None:
        def printInConsole(text: str):
            self.printText_signal.emit('{0}: {1}'.format(DividendsThread.__name__, text))

        if self.semaphore is None:
            printInConsole('Лимит для метода {0} не найден.'.format(self.receive_dividends_method_name))
        else:
            shares_count: int = len(self.shares)  # Количество акций.
            self.setProgressBarRange_signal.emit(0, shares_count)  # Задаёт минимум и максимум progressBar'а заполнения дивидендов.

            self.DatabaseConnection.open()  # Открываем соединение с БД.
            for i, share_class in enumerate(self.shares):
                if self.isInterruptionRequested():
                    printInConsole('Поток прерван.')
                    break

                share_number: int = i + 1  # Номер текущей акции.
                self.setProgressBarValue_signal.emit(share_number)  # Отображаем прогресс в progressBar.

                dividends_try_count: RequestTryClass = RequestTryClass()
                dividends_response: MyResponse = MyResponse()
                while dividends_try_count and not dividends_response.ifDataSuccessfullyReceived():
                    if self.isInterruptionRequested():
                        printInConsole('Поток прерван.')
                        break

                    """---------------------------Выполнение запроса---------------------------"""
                    self.semaphore.acquire(1)  # Блокирует вызов до тех пор, пока не будет доступно достаточно ресурсов.

                    '''----------------Подсчёт статистических параметров----------------'''
                    if self.request_count > 0:  # Не выполняется до второго запроса.
                        delta: float = (getUtcDateTime() - self.control_point).total_seconds()  # Секунд прошло с последнего запроса.
                        printInConsole('{0} из {1} ({2:.2f}c)'.format(share_number, shares_count, delta))
                    else:
                        printInConsole('{0} из {1}'.format(share_number, shares_count))
                    self.control_point = getUtcDateTime()  # Промежуточная точка отсчёта времени.
                    '''-----------------------------------------------------------------'''

                    before_dt: datetime = getUtcDateTime()
                    dividends_response = getDividends(token=self.token.token, instrument_id=share_class.share.uid)
                    delta: float = (getUtcDateTime() - before_dt).total_seconds()
                    self.requests_time += delta
                    printInConsole('delta: {0} с.'.format(delta))

                    assert dividends_response.request_occurred, 'Запрос дивидендов не был произведён!'
                    self.request_count += 1  # Подсчитываем запрос.
                    self.releaseSemaphore_signal.emit(self.semaphore, 1)  # Освобождаем ресурсы семафора.

                    '''------------------------Сообщаем об ошибке------------------------'''
                    if dividends_response.request_error_flag:
                        self.request_error_count += 1  # Количество RequestError.
                        printInConsole('RequestError {0}'.format(dividends_response.request_error))
                    elif dividends_response.exception_flag:
                        self.exception_count += 1  # Количество исключений.
                        printInConsole('Exception {0}'.format(dividends_response.exception))
                    '''------------------------------------------------------------------'''
                    """------------------------------------------------------------------------"""
                    dividends_try_count += 1

                dividends: list[Dividend] | None = dividends_response.response_data if dividends_response.ifDataSuccessfullyReceived() else None
                if dividends is None: continue  # Если поток был прерван или если информация не была получена.

                share_class.setDividends(dividends)  # Записываем список дивидендов.
                self.DatabaseConnection.setDividends(share_class.share.uid, dividends)  # Добавляем дивиденды в таблицу дивидендов.

            self.DatabaseConnection.removeConnection()  # Удаляем соединение с БД.

            printInConsole('seconds: {0}'.format(self.requests_time / shares_count))