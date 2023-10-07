from datetime import datetime
from PyQt6.QtCore import QThread, pyqtSignal
from tinkoff.invest import Client, Coupon, RequestError
from Classes import TokenClass
from LimitClasses import LimitPerMinuteSemaphore
from MyDateTime import getCurrentDateTime, ifDateTimeIsEmpty
from MyBondClass import MyBondClass


class CouponsThread(QThread):
    """Поток получения купонов."""
    thread_name: str = 'CouponsThread'
    receive_coupons_method_name: str = 'GetBondCoupons'

    """------------------------Сигналы------------------------"""
    printText_signal: pyqtSignal = pyqtSignal(str)  # Сигнал для отображения сообщений в консоли.
    """-------------------------------------------------------"""

    """-----------------Сигналы progressBar'а-----------------"""
    # Сигнал для установления минимума и максимума progressBar'а заполнения купонов.
    setProgressBarRange_signal: pyqtSignal = pyqtSignal(int, int)
    setProgressBarValue_signal: pyqtSignal = pyqtSignal(int)  # Сигнал для изменения прогресса в progressBar'е.
    """-------------------------------------------------------"""

    """---------------------Сигналы ошибок---------------------"""
    showRequestError_signal: pyqtSignal = pyqtSignal(str, RequestError)  # Сигнал для отображения исключения RequestError.
    showException_signal: pyqtSignal = pyqtSignal(str, Exception)  # Сигнал для отображения исключения.
    clearStatusBar_signal: pyqtSignal = pyqtSignal()  # Сигнал выключения отображения ошибки.
    """--------------------------------------------------------"""

    releaseSemaphore_signal: pyqtSignal = pyqtSignal(LimitPerMinuteSemaphore, int)  # Сигнал для освобождения ресурсов семафора из основного потока.

    def __init__(self, token_class: TokenClass, bond_class_list: list[MyBondClass]):
        super().__init__()  # __init__() QThread.
        self.token: TokenClass = token_class
        self.semaphore: LimitPerMinuteSemaphore | None = self.token.unary_limits_manager.getSemaphore(self.receive_coupons_method_name)
        self.bonds: list[MyBondClass] = bond_class_list

        """------------Статистические переменные------------"""
        self.request_count: int = 0  # Общее количество запросов.
        self.exception_count: int = 0  # Количество исключений.
        self.request_error_count: int = 0  # Количество RequestError.
        self.control_point: datetime | None = None  # Начальная точка отсчёта времени.
        """-------------------------------------------------"""

    def run(self) -> None:
        def printInConsole(text: str):
            self.printText_signal.emit('{0}: {1}'.format(self.thread_name, text))

        def ifFirstIteration() -> bool:
            """Возвращает True, если поток не сделал ни одного запроса. Иначе возвращает False."""
            return self.request_count > 0

        bonds_count: int = len(self.bonds)  # Количество облигаций.
        self.setProgressBarRange_signal.emit(0, bonds_count)  # Задаёт минимум и максимум progressBar'а заполнения купонов.

        if self.semaphore is None:
            printInConsole('Лимит для метода {0} не найден.'.format(self.receive_coupons_method_name))
        else:
            # bonds_count: int = len(self.bonds)  # Количество облигаций.
            # self.setProgressBarRange_signal.emit(0, bonds_count)  # Задаёт минимум и максимум progressBar'а заполнения купонов.
            for i, bond_class in enumerate(self.bonds):
                if self.isInterruptionRequested():
                    printInConsole('Поток прерван.')
                    break

                bond_number: int = i + 1  # Номер текущей облигации.
                self.setProgressBarValue_signal.emit(bond_number)  # Отображаем прогресс в progressBar.

                '------------Выбор временного интервала------------'
                qdt_from: datetime = bond_class.bond.state_reg_date
                qdt_to: datetime = getCurrentDateTime() if ifDateTimeIsEmpty(bond_class.bond.maturity_date) else bond_class.bond.maturity_date
                '--------------------------------------------------'

                exception_flag = True  # Индикатор наличия исключения.
                while exception_flag:
                    if self.isInterruptionRequested():
                        printInConsole('Поток прерван.')
                        break

                    """---------------------------Выполнение запроса---------------------------"""
                    self.semaphore.acquire(1)  # Блокирует вызов до тех пор, пока не будет доступно достаточно ресурсов.

                    """----------------Подсчёт статистических параметров----------------"""
                    if ifFirstIteration():  # Не выполняется до второго запроса.
                        delta: float = (getCurrentDateTime() - self.control_point).total_seconds()  # Секунд прошло с последнего запроса.
                        printInConsole('{0} из {1} ({2:.2f}с)'.format(bond_number, bonds_count, delta))
                    else:
                        printInConsole('{0} из {1}'.format(bond_number, bonds_count))
                    self.control_point = getCurrentDateTime()  # Промежуточная точка отсчёта времени.
                    """-----------------------------------------------------------------"""

                    with Client(self.token.token) as client:
                        try:
                            coupons: list[Coupon] = client.instruments.get_bond_coupons(figi=bond_class.bond.figi, from_=qdt_from, to=qdt_to).events
                        except RequestError as error:
                            self.request_error_count += 1  # Количество RequestError.
                            self.showRequestError_signal.emit('{0} ({1})'.format('get_bond_coupons()', self.thread_name), error)
                        except Exception as error:
                            self.exception_count += 1  # Количество исключений.
                            self.showException_signal.emit('{0} ({1})'.format('get_bond_coupons()', self.thread_name), error)
                        else:  # Если исключения не было.
                            exception_flag = False
                            self.clearStatusBar_signal.emit()
                        finally:  # Выполняется в любом случае.
                            self.request_count += 1  # Подсчитываем запрос.

                    self.releaseSemaphore_signal.emit(self.semaphore, 1)  # Освобождаем ресурсы семафора из основного потока.
                    """------------------------------------------------------------------------"""
                if exception_flag: break  # Если поток был прерван.
                bond_class.setCoupons(coupons)  # Записываем список купонов в облигацию.
        # printInConsole('Поток завершён. ({0})'.format(getCurrentDateTime()))
