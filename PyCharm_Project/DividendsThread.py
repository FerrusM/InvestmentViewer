from datetime import datetime
from PyQt6 import QtCore
# from grpc import StatusCode
from tinkoff.invest import Dividend, RequestError
from Classes import TokenClass
from LimitClasses import LimitPerMinuteSemaphore
from MyDateTime import getUtcDateTime
from MyRequests import MyResponse, getDividends, RequestTryClass
from MyShareClass import MyShareClass


class DividendsThread(QtCore.QThread):
    """Поток получения дивидендов."""

    receive_dividends_method_name: str = 'GetDividends'

    """------------------------Сигналы------------------------"""
    printText_signal: QtCore.pyqtSignal = QtCore.pyqtSignal(str)  # Сигнал для отображения сообщений в консоли.
    """-------------------------------------------------------"""

    dividendsReceived: QtCore.pyqtSignal = QtCore.pyqtSignal(str, list)

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
                    # printInConsole('delta: {0} с.'.format(delta))

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
                self.dividendsReceived.emit(share_class.share.uid, dividends)  # Добавляем дивиденды в таблицу дивидендов.

            printInConsole('seconds: {0}'.format(self.requests_time / shares_count))
