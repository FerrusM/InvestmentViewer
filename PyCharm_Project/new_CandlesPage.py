from __future__ import annotations
import typing
from datetime import datetime, timedelta
from enum import Enum
from PyQt6 import QtCore, QtWidgets, QtCharts, QtGui
from tinkoff.invest import HistoricCandle, CandleInterval
from tinkoff.invest.utils import candle_interval_to_timedelta
from CandlesChart import CandlesChart
from Classes import TokenClass, print_slot, print_function_runtime
from DatabaseWidgets import GroupBox_InstrumentSelection, TokenSelectionBar
from LimitClasses import LimitPerMinuteSemaphore
from MyBondClass import MyBondClass
from MyDatabase import MainConnection
from MyDateTime import ifDateTimeIsEmpty, getUtcDateTime, getMoscowDateTime
from MyQuotation import MyQuotation
from MyRequests import MyResponse, RequestTryClass, getCandles
from MyShareClass import MyShareClass
from PagesClasses import GroupBox_InstrumentInfo, TitleLabel, ProgressBar_DataReceiving
from TokenModel import TokenListModel


class ComboBox_Interval(QtWidgets.QComboBox):
    """ComboBox для выбора интервала свечей."""
    intervalSelected = QtCore.pyqtSignal(CandleInterval)  # Сигнал испускается при выборе интервала свечей.
    __DEFAULT_INDEX: int = 0

    class CandleIntervalModel(QtCore.QAbstractListModel):
        """Модель интервалов свечей."""
        def __init__(self, parent: QtCore.QObject | None = None):
            super().__init__(parent=parent)
            self.__intervals: tuple[tuple[str, CandleInterval], ...] = (
                ('Не определён', CandleInterval.CANDLE_INTERVAL_UNSPECIFIED),
                ('1 минута', CandleInterval.CANDLE_INTERVAL_1_MIN),
                ('2 минуты', CandleInterval.CANDLE_INTERVAL_2_MIN),
                ('3 минуты', CandleInterval.CANDLE_INTERVAL_3_MIN),
                ('5 минут', CandleInterval.CANDLE_INTERVAL_5_MIN),
                ('10 минут', CandleInterval.CANDLE_INTERVAL_10_MIN),
                ('15 минут', CandleInterval.CANDLE_INTERVAL_15_MIN),
                ('30 минут', CandleInterval.CANDLE_INTERVAL_30_MIN),
                ('1 час', CandleInterval.CANDLE_INTERVAL_HOUR),
                ('2 часа', CandleInterval.CANDLE_INTERVAL_2_HOUR),
                ('4 часа', CandleInterval.CANDLE_INTERVAL_4_HOUR),
                ('1 день', CandleInterval.CANDLE_INTERVAL_DAY),
                ('1 неделя', CandleInterval.CANDLE_INTERVAL_WEEK),
                ('1 месяц', CandleInterval.CANDLE_INTERVAL_MONTH)
            )

        def rowCount(self, parent: QtCore.QModelIndex = ...) -> int:
            return len(self.__intervals)

        def data(self, index: QtCore.QModelIndex, role: int = ...) -> typing.Any:
            if role == QtCore.Qt.ItemDataRole.DisplayRole:
                return self.__intervals[index.row()][0]
            elif role == QtCore.Qt.ItemDataRole.UserRole:
                return self.__intervals[index.row()][1]
            else:
                return QtCore.QVariant()

        def getInterval(self, index: int) -> CandleInterval:
            return self.__intervals[index][1]

    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)
        self.setEnabled(False)
        self.setModel(self.CandleIntervalModel(parent=self))
        self.setCurrentIndex(self.__DEFAULT_INDEX)
        self.__interval: CandleInterval = self.model().getInterval(self.__DEFAULT_INDEX)

        @QtCore.pyqtSlot(int)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
        def __setCurrentInterval(index: int):
            self.interval = self.model().getInterval(index)

        self.currentIndexChanged.connect(__setCurrentInterval)
        self.setEnabled(True)

    @property
    def interval(self) -> CandleInterval:
        return self.__interval

    @interval.setter
    def interval(self, interval: CandleInterval):
        self.__interval = interval
        self.intervalSelected.emit(self.interval)


def getMaxInterval(interval: CandleInterval) -> timedelta:
    """Возвращает максимальный временной интервал, соответствующий переданному интервалу."""
    match interval:
        case CandleInterval.CANDLE_INTERVAL_UNSPECIFIED:
            raise ValueError('Интервал не определён.')
        case CandleInterval.CANDLE_INTERVAL_1_MIN:
            return timedelta(days=1)
        case CandleInterval.CANDLE_INTERVAL_5_MIN:
            return timedelta(days=1)
        case CandleInterval.CANDLE_INTERVAL_15_MIN:
            return timedelta(days=1)
        case CandleInterval.CANDLE_INTERVAL_HOUR:
            return timedelta(weeks=1)
        case CandleInterval.CANDLE_INTERVAL_DAY:
            '''В timedelta нельзя указать один год, можно указать 365 дней. Но как быть с високосным годом?'''
            return timedelta(days=365)
        case CandleInterval.CANDLE_INTERVAL_2_MIN:
            return timedelta(days=1)
        case CandleInterval.CANDLE_INTERVAL_3_MIN:
            return timedelta(days=1)
        case CandleInterval.CANDLE_INTERVAL_10_MIN:
            return timedelta(days=1)
        case CandleInterval.CANDLE_INTERVAL_30_MIN:
            return timedelta(days=2)
        case CandleInterval.CANDLE_INTERVAL_2_HOUR:
            '''В timedelta нельзя указать один месяц, можно указать 31 дней. Но как быть с более короткими месяцами?'''
            return timedelta(days=31)
        case CandleInterval.CANDLE_INTERVAL_4_HOUR:
            '''В timedelta нельзя указать один месяц, можно указать 31 дней. Но как быть с более короткими месяцами?'''
            return timedelta(days=31)
        case CandleInterval.CANDLE_INTERVAL_WEEK:
            '''В timedelta нельзя указать два года, можно указать 2x365 дней. Но как быть с високосными годами?'''
            return timedelta(days=(2 * 365))
        case CandleInterval.CANDLE_INTERVAL_MONTH:
            '''В timedelta нельзя указать десять лет, можно указать 10x365 дней. Но как быть с високосными годами?'''
            return timedelta(days=(10 * 365))
        case _:
            raise ValueError('Некорректный временной интервал свечей!')


class GroupBox_CandlesReceiving(QtWidgets.QGroupBox):
    class CandlesThread(QtCore.QThread):
        """Поток получения исторических свечей."""

        receive_candles_method_name: str = 'GetCandles'

        candlesReceived: QtCore.pyqtSignal = QtCore.pyqtSignal(str, CandleInterval, list)

        printText_signal: QtCore.pyqtSignal = QtCore.pyqtSignal(str)  # Сигнал для отображения сообщений в консоли.
        releaseSemaphore_signal: QtCore.pyqtSignal = QtCore.pyqtSignal(LimitPerMinuteSemaphore, int)  # Сигнал для освобождения ресурсов семафора из основного потока.

        '''-----------------Сигналы progressBar'а-----------------'''
        setProgressBarRange_signal: QtCore.pyqtSignal = QtCore.pyqtSignal(int, int)  # Сигнал для установления минимума и максимума progressBar'а заполнения купонов.
        setProgressBarValue_signal: QtCore.pyqtSignal = QtCore.pyqtSignal(int)  # Сигнал для изменения прогресса в progressBar'е.
        '''-------------------------------------------------------'''

        def __init__(self, token_class: TokenClass, instrument: MyBondClass | MyShareClass, interval: CandleInterval, parent: QtCore.QObject | None = None):
            super().__init__(parent=parent)
            self.__mutex: QtCore.QMutex = QtCore.QMutex()
            self.__token: TokenClass = token_class
            self.__instrument: MyBondClass | MyShareClass = instrument
            self.__interval: CandleInterval = interval
            self.semaphore: LimitPerMinuteSemaphore | None = self.token.unary_limits_manager.getSemaphore(self.receive_candles_method_name)

            if self.semaphore is not None:
                @QtCore.pyqtSlot(LimitPerMinuteSemaphore, int)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
                def __releaseSemaphore(semaphore: LimitPerMinuteSemaphore, n: int):
                    semaphore.release(n)

                self.releaseSemaphore_signal.connect(__releaseSemaphore)  # Освобождаем ресурсы семафора из основного потока.

            '''------------Статистические переменные------------'''
            self.request_count: int = 0  # Общее количество запросов.
            self._success_request_count: int = 0  # Количество успешных запросов.
            self.control_point: datetime | None = None  # Начальная точка отсчёта времени.
            '''-------------------------------------------------'''

            self.__pause: bool = False
            self.__pause_condition: QtCore.QWaitCondition = QtCore.QWaitCondition()

            self.printText_signal.connect(print_slot)  # Сигнал для отображения сообщений в консоли.
            self.started.connect(lambda: print('{0}: Поток запущен. ({1})'.format(GroupBox_CandlesReceiving.CandlesThread.__name__, getMoscowDateTime())))
            self.finished.connect(lambda: print('{0}: Поток завершён. ({1})'.format(GroupBox_CandlesReceiving.CandlesThread.__name__, getMoscowDateTime())))

        @property
        def token(self) -> TokenClass:
            return self.__token

        @property
        def instrument(self) -> MyShareClass | MyBondClass:
            return self.__instrument

        @property
        def interval(self) -> CandleInterval:
            return self.__interval

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

        def run(self) -> None:
            def printInConsole(text: str):
                self.printText_signal.emit('{0}: {1}'.format(GroupBox_CandlesReceiving.CandlesThread.__name__, text))

            def ifFirstIteration() -> bool:
                """Возвращает True, если поток не сделал ни одного запроса. Иначе возвращает False."""
                return self.request_count > 0

            def checkPause():
                """Проверка на необходимость поставить поток на паузу."""
                self.__mutex.lock()
                if self.__pause:
                    printInConsole('Поток приостановлен.')
                    self.__pause_condition.wait(self.__mutex)
                self.__mutex.unlock()

            if self.semaphore is None:
                printInConsole('Лимит для метода {0} не найден.'.format(self.receive_candles_method_name))
            else:
                match self.interval:
                    case CandleInterval.CANDLE_INTERVAL_1_MIN:
                        dt_from: datetime = self.instrument.instrument().first_1min_candle_date
                    case CandleInterval.CANDLE_INTERVAL_DAY:
                        dt_from: datetime = self.instrument.instrument().first_1day_candle_date
                    case _:
                        printInConsole('Получение исторических свечей для выбранного интервала ещё не реализовано.')
                        return

                if ifDateTimeIsEmpty(dt_from):
                    printInConsole('Время первой минутной свечи инструмента {0} пустое. Получение исторических свечей для таких инструментов пока не реализовано.'.format(self.instrument.uid))
                    return
                else:
                    max_interval: timedelta = getMaxInterval(self.interval)
                    request_number: int = 0

                    def requestCandles(from_: datetime, to: datetime, interval: CandleInterval):
                        try_count: RequestTryClass = RequestTryClass()
                        response: MyResponse = MyResponse()
                        while try_count and not response.ifDataSuccessfullyReceived():
                            if self.isInterruptionRequested():
                                printInConsole('Поток прерван.')
                                break

                            checkPause()

                            """==============================Выполнение запроса=============================="""
                            self.semaphore.acquire(1)  # Блокирует вызов до тех пор, пока не будет доступно достаточно ресурсов.

                            '''----------------Подсчёт статистических параметров----------------'''
                            if ifFirstIteration():  # Не выполняется до второго запроса.
                                delta: float = (getUtcDateTime() - self.control_point).total_seconds()  # Секунд прошло с последнего запроса.
                                printInConsole('{0} из {1} Период: {3} - {4} ({2:.2f}с)'.format(request_number, requests_count, delta, from_, to))
                            else:
                                printInConsole('{0} из {1} Период: {2} - {3}'.format(request_number, requests_count, from_, to))
                            self.control_point = getUtcDateTime()  # Промежуточная точка отсчёта времени.
                            '''-----------------------------------------------------------------'''

                            response = getCandles(token=self.token.token,
                                                  uid=self.instrument.uid,
                                                  interval=interval,
                                                  from_=from_,
                                                  to=to)
                            assert response.request_occurred, 'Запрос свечей не был произведён.'
                            self.request_count += 1  # Подсчитываем запрос.

                            self.releaseSemaphore_signal.emit(self.semaphore, 1)  # Освобождаем ресурсы семафора из основного потока.

                            '''-----------------------Сообщаем об ошибке-----------------------'''
                            if response.request_error_flag:
                                printInConsole('RequestError {0}'.format(response.request_error))
                            elif response.exception_flag:
                                printInConsole('Exception {0}'.format(response.exception))
                            '''----------------------------------------------------------------'''
                            """=============================================================================="""
                            try_count += 1

                        if response.ifDataSuccessfullyReceived():
                            self._success_request_count += 1  # Подсчитываем успешный запрос.
                            candles: list[HistoricCandle] = response.response_data
                            self.candlesReceived.emit(self.instrument.uid, self.interval, candles)

                        self.setProgressBarValue_signal.emit(request_number)  # Отображаем прогресс в progressBar.

                    current_dt: datetime = getUtcDateTime()
                    '''--Рассчитываем требуемое количество запросов--'''
                    dt_delta: timedelta = current_dt - dt_from
                    requests_count: int = dt_delta // max_interval
                    if dt_delta % max_interval > candle_interval_to_timedelta(self.interval):
                        requests_count += 1
                    '''----------------------------------------------'''
                    self.setProgressBarRange_signal.emit(0, requests_count)  # Задаёт минимум и максимум progressBar'а.
                    dt_to: datetime = dt_from + max_interval

                    while dt_to < current_dt:
                        if self.isInterruptionRequested():
                            printInConsole('Поток прерван.')
                            break

                        request_number += 1
                        requestCandles(dt_from, dt_to, self.interval)

                        dt_from = dt_to
                        dt_to += max_interval
                    else:
                        current_dt = getUtcDateTime()
                        while dt_to < current_dt:
                            if self.isInterruptionRequested():
                                printInConsole('Поток прерван.')
                                break

                            request_number += 1
                            if request_number > requests_count:
                                requests_count = request_number
                                self.setProgressBarRange_signal.emit(0, request_number)  # Увеличиваем максимум progressBar'а.
                            requestCandles(dt_from, dt_to, self.interval)

                            dt_from = dt_to
                            dt_to += max_interval
                            current_dt = getUtcDateTime()
                        else:
                            request_number += 1
                            if request_number > requests_count:
                                requests_count = request_number
                                self.setProgressBarRange_signal.emit(0, request_number)  # Увеличиваем максимум progressBar'а.
                            requestCandles(dt_from, current_dt, self.interval)

    class ThreadStatus(Enum):
        """Статус потока."""
        START_NOT_POSSIBLE = 0  # Поток не запущен. Запуск потока невозможен.
        START_POSSIBLE = 1  # Поток не запущен. Возможен запуск потока.
        RUNNING = 2  # Поток запущен.
        PAUSE = 3  # Поток приостановлен.
        FINISHED = 4  # Поток завершился.

    STOP: str = 'Стоп'
    PLAY: str = 'Пуск'
    PAUSE: str = 'Пауза'

    def setStatus(self, token: TokenClass | None, instrument: MyShareClass | MyBondClass | None, interval: CandleInterval, status: ThreadStatus):
        def stopThread():
            self.__candles_receiving_thread.requestInterruption()  # Сообщаем потоку о том, что надо завершиться.
            self.__candles_receiving_thread.wait()  # Ждём завершения потока.
            self.__candles_receiving_thread = None

        print('Статус: {0} -> {1}.'.format(self.__thread_status.name, status.name))
        match status:
            case self.ThreadStatus.START_NOT_POSSIBLE:
                assert token is None or instrument is None

                match self.__thread_status:
                    case self.ThreadStatus.START_NOT_POSSIBLE:
                        return
                    case self.ThreadStatus.START_POSSIBLE:
                        self.play_button.setEnabled(False)
                        disconnect_flag: bool = self.play_button.disconnect(self.start_thread_connection)
                        assert disconnect_flag, 'Не удалось отключить слот!'
                    case self.ThreadStatus.RUNNING:
                        self.play_button.setEnabled(False)
                        self.stop_button.setEnabled(False)

                        '''-------------------------Останавливаем поток-------------------------'''
                        assert self.__candles_receiving_thread is not None
                        disconnect_flag: bool = self.__candles_receiving_thread.disconnect(self.thread_finished_connection)
                        assert disconnect_flag, 'Не удалось отключить слот!'
                        stopThread()
                        '''---------------------------------------------------------------------'''

                        disconnect_flag: bool = self.play_button.disconnect(self.pause_thread_connection)
                        assert disconnect_flag, 'Не удалось отключить слот!'

                        disconnect_flag: bool = self.stop_button.disconnect(self.stop_thread_connection)
                        assert disconnect_flag, 'Не удалось отключить слот!'

                        self.progressBar.reset()  # Сбрасываем progressBar.
                        self.play_button.setText(self.PLAY)
                    case self.ThreadStatus.PAUSE:
                        self.play_button.setEnabled(False)
                        self.stop_button.setEnabled(False)

                        '''-------------------------Останавливаем поток-------------------------'''
                        assert self.__candles_receiving_thread is not None
                        self.__candles_receiving_thread.resume()  # Возобновляем работу потока, чтобы он мог безопасно завершиться.
                        stopThread()
                        '''---------------------------------------------------------------------'''

                        self.progressBar.reset()  # Сбрасываем progressBar.
                        self.play_button.setText(self.PLAY)

                        disconnect_flag: bool = self.play_button.disconnect(self.resume_thread_connection)
                        assert disconnect_flag, 'Не удалось отключить слот!'

                    case self.ThreadStatus.FINISHED:
                        self.play_button.setEnabled(False)

                        assert self.__candles_receiving_thread is None
                        self.progressBar.reset()  # Сбрасываем progressBar.

                        disconnect_flag: bool = self.play_button.disconnect(self.start_thread_connection)
                        assert disconnect_flag, 'Не удалось отключить слот!'
                    case _:
                        raise ValueError('Неверный статус потока!')

                self.__thread_status = self.ThreadStatus.START_NOT_POSSIBLE
            case self.ThreadStatus.START_POSSIBLE:
                assert token is not None and instrument is not None
                match self.__thread_status:
                    case self.ThreadStatus.START_NOT_POSSIBLE:
                        pass  # Ничего не требуется делать.
                    case self.ThreadStatus.START_POSSIBLE:
                        return
                    case self.ThreadStatus.RUNNING:
                        self.play_button.setEnabled(False)
                        self.stop_button.setEnabled(False)

                        '''-------------------------Останавливаем поток-------------------------'''
                        assert self.__candles_receiving_thread is not None
                        disconnect_flag: bool = self.__candles_receiving_thread.disconnect(self.thread_finished_connection)
                        assert disconnect_flag, 'Не удалось отключить слот!'
                        stopThread()
                        '''---------------------------------------------------------------------'''

                        self.progressBar.reset()  # Сбрасываем progressBar.
                        self.play_button.setText(self.PLAY)

                        disconnect_flag: bool = self.play_button.disconnect(self.pause_thread_connection)
                        assert disconnect_flag, 'Не удалось отключить слот!'

                        disconnect_flag: bool = self.stop_button.disconnect(self.stop_thread_connection)
                        assert disconnect_flag, 'Не удалось отключить слот!'
                    case self.ThreadStatus.PAUSE:
                        self.play_button.setEnabled(False)
                        self.stop_button.setEnabled(False)

                        '''-------------------------Останавливаем поток-------------------------'''
                        assert self.__candles_receiving_thread is not None
                        disconnect_flag: bool = self.__candles_receiving_thread.disconnect(self.thread_finished_connection)
                        assert disconnect_flag, 'Не удалось отключить слот!'
                        self.__candles_receiving_thread.resume()  # Возобновляем работу потока, чтобы он мог безопасно завершиться.
                        stopThread()
                        '''---------------------------------------------------------------------'''

                        self.progressBar.reset()  # Сбрасываем progressBar.
                        self.play_button.setText(self.PLAY)

                        disconnect_flag: bool = self.play_button.disconnect(self.resume_thread_connection)
                        assert disconnect_flag, 'Не удалось отключить слот!'
                    case self.ThreadStatus.FINISHED:
                        self.play_button.setEnabled(False)

                        assert self.__candles_receiving_thread is None
                        self.progressBar.reset()  # Сбрасываем progressBar.

                        disconnect_flag: bool = self.play_button.disconnect(self.start_thread_connection)
                        assert disconnect_flag, 'Не удалось отключить слот!'
                    case _:
                        raise ValueError('Неверный статус потока!')

                @QtCore.pyqtSlot()  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
                def __startThread():
                    """Запускает поток получения исторических свечей."""
                    self.setStatus(token=self.token, instrument=self.instrument, interval=self.interval, status=self.ThreadStatus.RUNNING)

                self.start_thread_connection = self.play_button.clicked.connect(__startThread)

                self.__thread_status = self.ThreadStatus.START_POSSIBLE

                self.play_button.setEnabled(True)
            case self.ThreadStatus.RUNNING:
                assert token is not None and instrument is not None
                match self.__thread_status:
                    case self.ThreadStatus.START_POSSIBLE:
                        self.play_button.setEnabled(False)

                        disconnect_flag: bool = self.play_button.disconnect(self.start_thread_connection)
                        assert disconnect_flag, 'Не удалось отключить слот!'

                        """==========================Поток необходимо запустить=========================="""
                        assert self.__candles_receiving_thread is None, 'Поток получения исторических свечей должен быть завершён!'
                        self.__candles_receiving_thread = GroupBox_CandlesReceiving.CandlesThread(token_class=token,
                                                                                                  instrument=instrument,
                                                                                                  interval=interval,
                                                                                                  parent=self)

                        '''---------------------Подключаем сигналы потока к слотам---------------------'''
                        @QtCore.pyqtSlot(int, int)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
                        def __setRange(minimum: int, maximum: int):
                            if self.__candles_receiving_thread is not None:
                                self.progressBar.setRange(minimum, maximum)

                        self.__candles_receiving_thread.setProgressBarRange_signal.connect(__setRange)

                        @QtCore.pyqtSlot(int)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
                        def __setValue(value: int):
                            if self.__candles_receiving_thread is not None:
                                self.progressBar.setValue(value)

                        self.__candles_receiving_thread.setProgressBarValue_signal.connect(__setValue)

                        self.__candles_receiving_thread.candlesReceived.connect(MainConnection.insertHistoricCandles)

                        self.thread_finished_connection = self.__candles_receiving_thread.finished.connect(lambda: self.setStatus(token=self.token, instrument=self.instrument, interval=self.interval, status=self.ThreadStatus.FINISHED))
                        '''----------------------------------------------------------------------------'''

                        self.__candles_receiving_thread.start()  # Запускаем поток.
                        """=============================================================================="""
                    case self.ThreadStatus.PAUSE:
                        self.play_button.setEnabled(False)
                        self.stop_button.setEnabled(False)

                        self.__candles_receiving_thread.resume()

                        disconnect_flag: bool = self.play_button.disconnect(self.resume_thread_connection)
                        assert disconnect_flag, 'Не удалось отключить слот!'
                    case _:
                        raise ValueError('Неверный статус потока!')

                '''------------------------------Левая кнопка------------------------------'''
                self.play_button.setText(self.PAUSE)

                @QtCore.pyqtSlot()  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
                def __pauseThread():
                    """Приостанавливает поток получения исторических свечей."""
                    self.setStatus(token=self.token, instrument=self.instrument, interval=self.interval, status=self.ThreadStatus.PAUSE)

                self.pause_thread_connection = self.play_button.clicked.connect(__pauseThread)
                '''------------------------------------------------------------------------'''

                '''------------------------------Правая кнопка------------------------------'''
                @QtCore.pyqtSlot()  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
                def __stopThread():
                    """Останавливает поток получения исторических свечей."""
                    self.setStatus(token=self.token, instrument=self.instrument, interval=self.interval, status=self.ThreadStatus.START_POSSIBLE)

                self.stop_thread_connection = self.stop_button.clicked.connect(__stopThread)
                '''-------------------------------------------------------------------------'''

                self.__thread_status = self.ThreadStatus.RUNNING

                self.play_button.setEnabled(True)
                self.stop_button.setEnabled(True)
            case self.ThreadStatus.PAUSE:
                assert self.__thread_status is self.ThreadStatus.RUNNING, 'Поток получения свечей переходит в статус PAUSE из статуса {0} минуя статус RUNNING.'.format(self.__thread_status.name)
                self.play_button.setEnabled(False)
                self.stop_button.setEnabled(False)

                self.__candles_receiving_thread.pause()

                self.play_button.setText(self.PLAY)

                disconnect_flag: bool = self.play_button.disconnect(self.pause_thread_connection)
                assert disconnect_flag, 'Не удалось отключить слот!'

                @QtCore.pyqtSlot()  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
                def __resumeThread():
                    """Возобновляет работу потока получения исторических свечей."""
                    self.setStatus(token=self.token, instrument=self.instrument, interval=self.interval, status=self.ThreadStatus.RUNNING)

                self.resume_thread_connection = self.play_button.clicked.connect(__resumeThread)

                self.__thread_status = self.ThreadStatus.PAUSE

                self.play_button.setEnabled(True)
                self.stop_button.setEnabled(True)
            case self.ThreadStatus.FINISHED:
                assert self.__thread_status is self.ThreadStatus.RUNNING, 'Поток получения свечей переходит в статус FINISHED из статуса {0} минуя статус RUNNING.'.format(self.__thread_status.name)
                self.play_button.setEnabled(False)
                self.stop_button.setEnabled(False)

                assert self.__candles_receiving_thread.isFinished()
                self.__candles_receiving_thread = None

                self.play_button.setText(self.PLAY)

                disconnect_flag: bool = self.play_button.disconnect(self.pause_thread_connection)
                assert disconnect_flag, 'Не удалось отключить слот!'

                disconnect_flag: bool = self.stop_button.disconnect(self.stop_thread_connection)
                assert disconnect_flag, 'Не удалось отключить слот!'

                @QtCore.pyqtSlot()  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
                def __startThread():
                    """Запускает поток получения исторических свечей."""
                    self.setStatus(token=self.token, instrument=self.instrument, interval=self.interval, status=self.ThreadStatus.START_POSSIBLE)
                    self.setStatus(token=self.token, instrument=self.instrument, interval=self.interval, status=self.ThreadStatus.RUNNING)

                self.start_thread_connection = self.play_button.clicked.connect(__startThread)

                self.__thread_status = self.ThreadStatus.FINISHED

                self.play_button.setEnabled(True)
            case _:
                raise ValueError('Неверный статус потока!')

    def __init__(self, token_model: TokenListModel, parent: QtWidgets.QWidget | None = None):
        self.__instrument: MyBondClass | MyShareClass | None = None

        self.__candles_receiving_thread: GroupBox_CandlesReceiving.CandlesThread | None = None
        self.__thread_status: GroupBox_CandlesReceiving.ThreadStatus = self.ThreadStatus.START_NOT_POSSIBLE

        super().__init__(parent=parent)

        verticalLayout_main = QtWidgets.QVBoxLayout(self)
        verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        verticalLayout_main.setSpacing(2)

        verticalLayout_main.addWidget(TitleLabel(text='ПОЛУЧЕНИЕ ИСТОРИЧЕСКИХ СВЕЧЕЙ', parent=self), 0)

        '''-----------Выбор токена для получения исторических свечей-----------'''
        self.token_bar = TokenSelectionBar(tokens_model=token_model, parent=self)
        verticalLayout_main.addLayout(self.token_bar, 0)
        '''--------------------------------------------------------------------'''

        '''-----------------------Выбор интервала свечей-----------------------'''
        horizontalLayout_interval = QtWidgets.QHBoxLayout(self)
        horizontalLayout_interval.addWidget(QtWidgets.QLabel(text='Интервал:', parent=self), 0)
        horizontalLayout_interval.addSpacing(4)
        self.comboBox_interval = ComboBox_Interval(parent=self)
        horizontalLayout_interval.addWidget(self.comboBox_interval, 0)
        horizontalLayout_interval.addStretch(1)
        verticalLayout_main.addLayout(horizontalLayout_interval, 0)
        '''--------------------------------------------------------------------'''

        '''---------------Прогресс получения исторических свечей---------------'''
        horizontalLayout = QtWidgets.QHBoxLayout(self)

        self.play_button = QtWidgets.QPushButton(text=self.PLAY, parent=self)
        self.play_button.setEnabled(False)
        horizontalLayout.addWidget(self.play_button, 0)

        self.stop_button = QtWidgets.QPushButton(text=self.STOP, parent=self)
        self.stop_button.setEnabled(False)
        horizontalLayout.addWidget(self.stop_button, 0)

        self.progressBar = ProgressBar_DataReceiving(parent=self)
        horizontalLayout.addWidget(self.progressBar, 1)

        verticalLayout_main.addLayout(horizontalLayout, 0)
        '''--------------------------------------------------------------------'''

        verticalLayout_main.addStretch(1)

        self.start_thread_connection: QtCore.QMetaObject.Connection = QtCore.QMetaObject.Connection()
        self.pause_thread_connection: QtCore.QMetaObject.Connection = QtCore.QMetaObject.Connection()
        self.resume_thread_connection: QtCore.QMetaObject.Connection = QtCore.QMetaObject.Connection()
        self.stop_thread_connection: QtCore.QMetaObject.Connection = QtCore.QMetaObject.Connection()

        self.thread_finished_connection: QtCore.QMetaObject.Connection = QtCore.QMetaObject.Connection()

        @QtCore.pyqtSlot(TokenClass)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
        def __onTokenSelected(token: TokenClass):
            self.token = token

        @QtCore.pyqtSlot()  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
        def __onTokenReset():
            self.token = None

        @QtCore.pyqtSlot(CandleInterval)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
        def __onIntervalSelected(interval: CandleInterval):
            self.interval = interval

        self.token_bar.tokenSelected.connect(__onTokenSelected)
        self.token_bar.tokenReset.connect(__onTokenReset)
        self.comboBox_interval.intervalSelected.connect(__onIntervalSelected)

    def __onParameterChanged(self, token: TokenClass | None, instrument: MyShareClass | MyBondClass | None, interval: CandleInterval):
        status = self.ThreadStatus.START_NOT_POSSIBLE if self.token is None or self.instrument is None else self.ThreadStatus.START_POSSIBLE
        self.setStatus(token=token, instrument=instrument, interval=interval, status=status)

    @property
    def token(self) -> TokenClass | None:
        return self.token_bar.token

    @token.setter
    def token(self, token: TokenClass | None):
        self.__onParameterChanged(token=token, instrument=self.instrument, interval=self.interval)

    @property
    def interval(self) -> CandleInterval:
        return self.comboBox_interval.interval

    @interval.setter
    def interval(self, interval: CandleInterval):
        self.__onParameterChanged(token=self.token, instrument=self.instrument, interval=interval)

    @property
    def instrument(self) -> MyBondClass | MyShareClass | None:
        return self.__instrument

    @instrument.setter
    def instrument(self, instrument: MyBondClass | MyShareClass | None):
        self.__instrument = instrument
        self.__onParameterChanged(token=self.token, instrument=instrument, interval=self.interval)

    def setInstrument(self, instrument: MyBondClass | MyShareClass | None = None):
        """Устанавливает текущий инструмент."""
        self.instrument = instrument


class Candlestick(QtCharts.QCandlestickSet):
    def __init__(self, candle: HistoricCandle, parent: QtCore.QObject | None = None):
        self.__historic_candle: HistoricCandle = candle
        super().__init__(open=MyQuotation.getFloat(candle.open),
                         high=MyQuotation.getFloat(candle.high),
                         low=MyQuotation.getFloat(candle.low),
                         close=MyQuotation.getFloat(candle.close),
                         timestamp=(candle.time.timestamp() * 1000),
                         parent=parent)

    @property
    def historic_candle(self) -> HistoricCandle:
        return self.__historic_candle


class MyChartView(QtCharts.QChartView):
    """Отображение графика."""
    def __init__(self, parent: QtWidgets.QWidget | None = None):
        self.__lastMousePos: QtCore.QPoint
        super().__init__(parent=parent)
        self.setDragMode(QtWidgets.QGraphicsView.DragMode.NoDrag)
        self.setRubberBand(QtCharts.QChartView.RubberBand.NoRubberBand)

    def mousePressEvent(self, event: QtGui.QMouseEvent | None = None) -> None:
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            QtWidgets.QApplication.setOverrideCursor(QtGui.QCursor(QtCore.Qt.CursorShape.SizeHorCursor))
            self.__lastMousePos = event.pos()  # Положение курсора основного экрана в глобальных координатах экрана.
            event.accept()

    def mouseMoveEvent(self, event: QtGui.QMouseEvent | None = None) -> None:
        if event.buttons() & QtCore.Qt.MouseButton.LeftButton:
            # bounds: QtCore.QRectF = QtCore.QRectF(0, 0, 0, 0)
            # for series in self.chart().series():
            #     bounds.united(series.bounds)

            dPos: QtCore.QPoint = event.pos() - self.__lastMousePos
            # self.chart().scroll(-dPos.x(), dPos.y())
            self.chart().scroll(-dPos.x(), 0)

            self.__lastMousePos = event.pos()
            event.accept()  # Устанавливает флаг принятия объекта события.

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent | None = None) -> None:
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            QtWidgets.QApplication.restoreOverrideCursor()


class CandlesGraphic(QtWidgets.QWidget):
    """Виджет, отображающий график свечей."""
    def __init__(self, instrument_uid: str | None, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)
        self.setEnabled(False)

        verticalLayout_main = QtWidgets.QVBoxLayout(self)
        verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        verticalLayout_main.setSpacing(2)

        '''------------------------------------Заголовок------------------------------------'''
        horizontalLayout_title = QtWidgets.QHBoxLayout(self)
        horizontalLayout_title.addSpacing(10)

        '''------------------Выбор интервала------------------'''
        horizontalLayout_interval = QtWidgets.QHBoxLayout(self)
        horizontalLayout_interval.addWidget(QtWidgets.QLabel(text='Интервал:', parent=self), 0)
        horizontalLayout_interval.addSpacing(4)
        self.comboBox_interval = ComboBox_Interval(parent=self)
        horizontalLayout_interval.addWidget(self.comboBox_interval, 0)
        horizontalLayout_interval.addStretch(1)
        horizontalLayout_title.addLayout(horizontalLayout_interval, 1)
        '''---------------------------------------------------'''

        horizontalLayout_title.addWidget(TitleLabel(text='ГРАФИК', parent=self), 0)
        horizontalLayout_title.addStretch(1)
        horizontalLayout_title.addSpacing(10)
        verticalLayout_main.addLayout(horizontalLayout_title, 0)
        '''---------------------------------------------------------------------------------'''

        '''---------------------QChartView---------------------'''
        # self.chart_view = QtCharts.QChartView(parent=self)
        # # self.chart_view.setRubberBand(QtCharts.QChartView.RubberBand.HorizontalRubberBand)
        # # self.chart_view.setDragMode(QtWidgets.QGraphicsView.DragMode.ScrollHandDrag)
        # self.chart = CandlesChart(instrument_uid=instrument_uid, interval=self.interval)
        # self.chart_view.setChart(self.chart)
        # verticalLayout_main.addWidget(self.chart_view, 1)

        self.chart_view = MyChartView(parent=self)
        self.chart = CandlesChart(instrument_uid=instrument_uid, interval=self.interval)
        self.chart_view.setChart(self.chart)
        verticalLayout_main.addWidget(self.chart_view, 1)
        '''----------------------------------------------------'''

        @QtCore.pyqtSlot(CandleInterval)
        def __onIntervalChanged(interval: CandleInterval):
            self.interval = interval

        self.comboBox_interval.intervalSelected.connect(__onIntervalChanged)

        self.setEnabled(True)

    @property
    def interval(self) -> CandleInterval:
        return self.comboBox_interval.interval

    @interval.setter
    def interval(self, interval: CandleInterval):
        self.chart.setInterval(interval)

    def setInstrumentUid(self, instrument_uid: str | None = None):
        """Задаёт отображаемый инструмент."""
        self.chart.setInstrument(instrument_uid)


class CandlesPage_new(QtWidgets.QWidget):
    """Страница свечей."""
    @print_function_runtime
    def __init__(self, token_model: TokenListModel, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)
        self.setEnabled(False)

        verticalLayout_main = QtWidgets.QVBoxLayout(self)
        verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        verticalLayout_main.setSpacing(0)

        splitter_vertical = QtWidgets.QSplitter(orientation=QtCore.Qt.Orientation.Vertical, parent=self)

        """========================Верхняя часть========================"""
        splitter_horizontal = QtWidgets.QSplitter(orientation=QtCore.Qt.Orientation.Horizontal, parent=splitter_vertical)
        splitter_vertical.setStretchFactor(0, 0)

        '''------------------------Левая часть------------------------'''
        layoutWidget = QtWidgets.QWidget(parent=splitter_horizontal)
        splitter_horizontal.setStretchFactor(0, 0)

        verticalLayout = QtWidgets.QVBoxLayout(layoutWidget)
        verticalLayout.setContentsMargins(0, 0, 0, 0)
        verticalLayout.setSpacing(2)

        self.groupBox_instrument = GroupBox_InstrumentSelection(tokens_model=token_model, parent=layoutWidget)
        verticalLayout.addWidget(self.groupBox_instrument, 0)

        self.groupBox_candles_receiving = GroupBox_CandlesReceiving(token_model=token_model, parent=layoutWidget)
        verticalLayout.addWidget(self.groupBox_candles_receiving, 0)

        verticalLayout.addStretch(1)
        '''-----------------------------------------------------------'''

        self.groupBox_instrument_info = GroupBox_InstrumentInfo(parent=splitter_horizontal)
        splitter_horizontal.setStretchFactor(1, 1)
        """============================================================="""

        """========================Нижняя часть========================"""
        self.candles_graphic = CandlesGraphic(instrument_uid=self.instrument_uid, parent=splitter_vertical)
        splitter_vertical.setStretchFactor(1, 1)
        """============================================================"""

        verticalLayout_main.addWidget(splitter_vertical)

        def __onInstrumentSelected(instrument: MyBondClass | MyShareClass | None = None):
            self.instrument = instrument

        self.groupBox_instrument.bondSelected.connect(__onInstrumentSelected)
        self.groupBox_instrument.shareSelected.connect(__onInstrumentSelected)
        self.groupBox_instrument.instrumentReset.connect(__onInstrumentSelected)

        self.setEnabled(True)

    @property
    def instrument(self) -> MyShareClass | MyBondClass | None:
        return self.groupBox_instrument.instrument

    @property
    def instrument_uid(self) -> str | None:
        return None if self.instrument is None else self.instrument.uid

    @instrument.setter
    def instrument(self, instrument: MyShareClass | MyBondClass | None):
        self.groupBox_instrument_info.setInstrument(instrument)
        self.groupBox_candles_receiving.setInstrument(instrument)
        self.candles_graphic.setInstrumentUid(self.instrument_uid)
