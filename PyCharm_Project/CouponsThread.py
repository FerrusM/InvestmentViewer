from datetime import datetime
from PyQt6 import QtCore
from tinkoff.invest import Coupon, RequestError
from Classes import TokenClass
from LimitClasses import LimitPerMinuteSemaphore
from common.datetime_functions import getUtcDateTime
from MyBondClass import MyBondClass
from MyRequests import getCoupons, MyResponse, RequestTryClass


class CouponsThread(QtCore.QThread):
    """Поток получения купонов."""

    receive_coupons_method_name: str = 'GetBondCoupons'

    """------------------------Сигналы------------------------"""
    printText_signal: QtCore.pyqtSignal = QtCore.pyqtSignal(str)  # Сигнал для отображения сообщений в консоли.
    """-------------------------------------------------------"""

    couponsReceived: QtCore.pyqtSignal = QtCore.pyqtSignal(str, list)

    """-----------------Сигналы progressBar'а-----------------"""
    setProgressBarRange_signal: QtCore.pyqtSignal = QtCore.pyqtSignal(int, int)  # Сигнал для установления минимума и максимума progressBar'а заполнения купонов.
    setProgressBarValue_signal: QtCore.pyqtSignal = QtCore.pyqtSignal(int)  # Сигнал для изменения прогресса в progressBar'е.
    """-------------------------------------------------------"""

    """---------------------Сигналы ошибок---------------------"""
    showRequestError_signal: QtCore.pyqtSignal = QtCore.pyqtSignal(str, RequestError)  # Сигнал для отображения исключения RequestError.
    showException_signal: QtCore.pyqtSignal = QtCore.pyqtSignal(str, Exception)  # Сигнал для отображения исключения.
    """--------------------------------------------------------"""

    releaseSemaphore_signal: QtCore.pyqtSignal = QtCore.pyqtSignal(LimitPerMinuteSemaphore, int)  # Сигнал для освобождения ресурсов семафора из основного потока.

    def __init__(self, token_class: TokenClass, bond_class_list: list[MyBondClass], parent: QtCore.QObject | None = None):
        super().__init__(parent=parent)
        self.token: TokenClass = token_class
        self.semaphore: LimitPerMinuteSemaphore | None = self.token.unary_limits_manager.getSemaphore(self.receive_coupons_method_name)
        self.bonds: list[MyBondClass] = bond_class_list

        """------------Статистические переменные------------"""
        self.request_count: int = 0  # Общее количество запросов.
        self.exception_count: int = 0  # Количество исключений.
        self.request_error_count: int = 0  # Количество RequestError.
        self.control_point: datetime | None = None  # Начальная точка отсчёта времени.

        self.requests_time: float = 0.0
        """-------------------------------------------------"""

    def run(self) -> None:
        def printInConsole(text: str):
            self.printText_signal.emit('{0}: {1}'.format(CouponsThread.__name__, text))

        def ifFirstIteration() -> bool:
            """Возвращает True, если поток не сделал ни одного запроса. Иначе возвращает False."""
            return self.request_count > 0

        if self.semaphore is None:
            printInConsole('Лимит для метода {0} не найден.'.format(self.receive_coupons_method_name))
        else:
            bonds_count: int = len(self.bonds)  # Количество облигаций.
            self.setProgressBarRange_signal.emit(0, bonds_count)  # Задаёт минимум и максимум progressBar'а заполнения купонов.

            for i, bond_class in enumerate(self.bonds):
                if self.isInterruptionRequested():
                    printInConsole('Поток прерван.')
                    break

                bond_number: int = i + 1  # Номер текущей облигации.
                self.setProgressBarValue_signal.emit(bond_number)  # Отображаем прогресс в progressBar.

                # '------------Выбор временного интервала------------'
                # qdt_from: datetime = bond_class.bond.state_reg_date
                # qdt_to: datetime = getUtcDateTime() if ifDateTimeIsEmpty(bond_class.bond.maturity_date) else bond_class.bond.maturity_date
                # '--------------------------------------------------'

                coupons_try_count: RequestTryClass = RequestTryClass()
                coupons_response: MyResponse = MyResponse()
                while coupons_try_count and not coupons_response.ifDataSuccessfullyReceived():
                    if self.isInterruptionRequested():
                        printInConsole('Поток прерван.')
                        break

                    """---------------------------Выполнение запроса---------------------------"""
                    self.semaphore.acquire(1)  # Блокирует вызов до тех пор, пока не будет доступно достаточно ресурсов.

                    '''----------------Подсчёт статистических параметров----------------'''
                    if ifFirstIteration():  # Не выполняется до второго запроса.
                        delta: float = (getUtcDateTime() - self.control_point).total_seconds()  # Секунд прошло с последнего запроса.
                        printInConsole('{0} из {1} ({2:.2f}с)'.format(bond_number, bonds_count, delta))
                    else:
                        printInConsole('{0} из {1}'.format(bond_number, bonds_count))
                    self.control_point = getUtcDateTime()  # Промежуточная точка отсчёта времени.
                    '''-----------------------------------------------------------------'''

                    before_dt: datetime = getUtcDateTime()
                    # coupons_response = getCoupons(token=self.token.token,
                    #                               from_=qdt_from,
                    #                               to=qdt_to,
                    #                               instrument_id=bond_class.bond.uid)
                    coupons_response = getCoupons(token=self.token.token, instrument_id=bond_class.bond.uid)
                    delta: float = (getUtcDateTime() - before_dt).total_seconds()
                    self.requests_time += delta
                    # printInConsole('delta: {0} с.'.format(delta))

                    assert coupons_response.request_occurred, 'Запрос купонов не был произведён!'
                    self.request_count += 1  # Подсчитываем запрос.
                    self.releaseSemaphore_signal.emit(self.semaphore, 1)  # Освобождаем ресурсы семафора из основного потока.

                    '''------------------------Сообщаем об ошибке------------------------'''
                    if coupons_response.request_error_flag:
                        self.request_error_count += 1  # Количество RequestError.
                        printInConsole('RequestError {0}'.format(coupons_response.request_error))
                    elif coupons_response.exception_flag:
                        self.exception_count += 1  # Количество исключений.
                        printInConsole('Exception {0}'.format(coupons_response.exception))
                    '''------------------------------------------------------------------'''
                    """------------------------------------------------------------------------"""
                    coupons_try_count += 1

                coupons: list[Coupon] | None = coupons_response.response_data if coupons_response.ifDataSuccessfullyReceived() else None
                if coupons is None: continue  # Если поток был прерван или если информация не была получена.

                bond_class.setCoupons(coupons)  # Записываем список купонов в облигацию.
                self.couponsReceived.emit(bond_class.bond.uid, coupons)  # Добавляем купоны в таблицу купонов.

            printInConsole('seconds: {0}'.format(self.requests_time / bonds_count))
