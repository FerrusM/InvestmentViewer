from PyQt6 import QtCore
from Classes import print_slot, TokenClass
from LimitClasses import LimitPerMinuteSemaphore
from common.datetime_functions import getMoscowDateTime


class ReceivingThread(QtCore.QThread):
    """Поток получения данных."""

    printText_signal: QtCore.pyqtSignal = QtCore.pyqtSignal(str)  # Сигнал для отображения сообщений в консоли.
    releaseSemaphore_signal: QtCore.pyqtSignal = QtCore.pyqtSignal(LimitPerMinuteSemaphore, int)  # Сигнал для освобождения ресурсов семафора из основного потока.

    def __init__(self, token: TokenClass, receive_method: str, parent: QtCore.QObject | None = None):
        super().__init__(parent=parent)

        self.__token: TokenClass = token
        self.__receive_method: str = receive_method

        '''---------------------------------Семафор---------------------------------'''
        self.semaphore: LimitPerMinuteSemaphore | None = self.__token.unary_limits_manager.getSemaphore(self.__receive_method)

        if self.semaphore is not None:
            @QtCore.pyqtSlot(LimitPerMinuteSemaphore, int)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
            def __releaseSemaphore(semaphore: LimitPerMinuteSemaphore, n: int):
                semaphore.release(n)

            self.releaseSemaphore_signal.connect(__releaseSemaphore)  # Освобождаем ресурсы семафора из основного потока.
        '''-------------------------------------------------------------------------'''

        self.printText_signal.connect(print_slot)  # Сигнал для отображения сообщений в консоли.
        self.started.connect(lambda: print('{0}: Поток запущен. ({1})'.format(self.__class__.__name__, getMoscowDateTime())))
        self.finished.connect(lambda: print('{0}: Поток завершён. ({1})'.format(self.__class__.__name__, getMoscowDateTime())))

    @property
    def token(self) -> TokenClass:
        return self.__token

    def printInConsole(self, text: str):
        self.printText_signal.emit('{0}: {1}'.format(self.__class__.__name__, text))

    def receivingFunction(self):
        """Функция, которая выполняется в цикле потока."""
        ...

    def run(self) -> None:
        if self.semaphore is None:
            self.printInConsole('Лимит для метода {0} не найден!'.format(self.__receive_method))
        else:
            self.receivingFunction()


class ManagedReceivingThread(ReceivingThread):
    """Управляемый поток получения данных."""
    def __init__(self, token: TokenClass, receive_method: str, parent: QtCore.QObject | None = None):
        super().__init__(token=token, receive_method=receive_method, parent=parent)

        self.__mutex: QtCore.QMutex = QtCore.QMutex()

        self.__pause: bool = False
        self.__pause_condition: QtCore.QWaitCondition = QtCore.QWaitCondition()

    def pause(self):
        """Приостанавливает прогресс."""
        self.__mutex.lock()
        assert not self.__pause
        self.__pause = True
        self.__mutex.unlock()

    def resume(self):
        """Возобновляет работу потока, поставленного на паузу."""
        self.__mutex.lock()
        assert self.__pause
        self.__pause = False
        self.__mutex.unlock()
        self.__pause_condition.wakeAll()

    def checkPause(self):
        """Проверяет необходимость поставить поток на паузу и, при необходимости, ставит на паузу."""
        self.__mutex.lock()
        if self.__pause:
            self.printInConsole('Поток приостановлен.')
            self.__pause_condition.wait(self.__mutex)
        self.__mutex.unlock()
