from __future__ import annotations
import typing
from datetime import datetime, timedelta
from enum import Enum
from PyQt6 import QtCore, QtWidgets, QtSql, QtCharts
from tinkoff.invest import HistoricCandle, CandleInterval
from tinkoff.invest.utils import candle_interval_to_timedelta
from CandlesChart import GroupBox_Chart
from Classes import TokenClass, MyConnection, Column, print_slot
from DatabaseWidgets import GroupBox_InstrumentSelection, TokenSelectionBar
from LimitClasses import LimitPerMinuteSemaphore
from MyBondClass import MyBondClass
from MyDatabase import MainConnection
from MyDateTime import ifDateTimeIsEmpty, getUtcDateTime, getMoscowDateTime
from MyQuotation import MyQuotation
from MyRequests import MyResponse, RequestTryClass, getCandles
from MyShareClass import MyShareClass
from PagesClasses import GroupBox_InstrumentInfo, TitleLabel, ProgressBar_DataReceiving, TitleWithCount
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


class CandlesChart(QtCharts.QChart):
    def __init__(self, interval: CandleInterval = CandleInterval.CANDLE_INTERVAL_UNSPECIFIED, parent: QtWidgets.QGraphicsItem | None = None):
        super().__init__(parent=parent)

        self.setAnimationOptions(QtCharts.QChart.AnimationOption.SeriesAnimations)

        self.setContentsMargins(-10.0, -10.0, -10.0, -10.0)  # Скрываем поля содержимого виджета.
        self.layout().setContentsMargins(0, 0, 0, 0)  # Раздвигаем поля содержимого макета.
        self.legend().hide()  # Скрываем легенду диаграммы.

        self.max_data = getMoscowDateTime()
        self.min_data = self.max_data - self.__getInterval(interval)

        axisY: QtCharts.QValueAxis = self.__createAxisY()
        self.addAxis(axisY, QtCore.Qt.AlignmentFlag.AlignLeft)

        axisX: QtCharts.QDateTimeAxis = self.__createAxisX(self.min_data, self.max_data)
        self.addAxis(axisX, QtCore.Qt.AlignmentFlag.AlignBottom)

    @staticmethod
    def __getInterval(interval: CandleInterval) -> timedelta:
        """Возвращает временной интервал, отображаемый на графике."""
        minute_td: timedelta = timedelta(hours=2)
        day_td: timedelta = timedelta(days=60)

        match interval:
            case CandleInterval.CANDLE_INTERVAL_UNSPECIFIED:
                return day_td
            case CandleInterval.CANDLE_INTERVAL_1_MIN:
                return minute_td
            case CandleInterval.CANDLE_INTERVAL_5_MIN:
                return minute_td * 5
            case CandleInterval.CANDLE_INTERVAL_15_MIN:
                return minute_td * 15
            case CandleInterval.CANDLE_INTERVAL_HOUR:
                return minute_td * 60
            case CandleInterval.CANDLE_INTERVAL_DAY:
                return day_td
            case CandleInterval.CANDLE_INTERVAL_2_MIN:
                return minute_td * 2
            case CandleInterval.CANDLE_INTERVAL_3_MIN:
                return minute_td * 3
            case CandleInterval.CANDLE_INTERVAL_10_MIN:
                return minute_td * 10
            case CandleInterval.CANDLE_INTERVAL_30_MIN:
                return minute_td * 30
            case CandleInterval.CANDLE_INTERVAL_2_HOUR:
                return minute_td * 120
            case CandleInterval.CANDLE_INTERVAL_4_HOUR:
                return minute_td * 240
            case CandleInterval.CANDLE_INTERVAL_WEEK:
                return day_td * 7
            case CandleInterval.CANDLE_INTERVAL_MONTH:
                return day_td * 31
            case _:
                raise ValueError('Некорректный временной интервал свечей!')

    def removeAllAxes(self):
        """Удаляет все оси диаграммы."""
        for axis in self.axes(QtCore.Qt.Orientation.Vertical, None):
            self.removeAxis(axis)
        for axis in self.axes(QtCore.Qt.Orientation.Horizontal, None):
            self.removeAxis(axis)

    def __createAxisX(self, min_: QtCore.QDateTime | datetime, max_: QtCore.QDateTime | datetime) -> QtCharts.QDateTimeAxis:
        axisX = QtCharts.QDateTimeAxis(parent=self)
        # axisX.setFormat()
        axisX.setRange(min_, max_)
        axisX.setTitleText('Дата и время')
        return axisX

    def __createAxisY(self, min_: float = 0, max_: float = 110) -> QtCharts.QValueAxis:
        axisY = QtCharts.QValueAxis(parent=self)
        axisY.setRange(min_, max_)
        # axisY.setTickCount(11)
        axisY.setTitleText('Цена')
        return axisY

    # def setCandles(self, candles: list[HistoricCandle], interval: CandleInterval):
    #     """Обновляем данные графика."""
    #     self.removeAllSeries()
    #     self.removeAllAxes()  # Удаляет все оси диаграммы.
    #
    #     candlestick_series = QtCharts.QCandlestickSeries(self)
    #     candlestick_series.setDecreasingColor(QtCore.Qt.GlobalColor.red)
    #     candlestick_series.setIncreasingColor(QtCore.Qt.GlobalColor.green)
    #
    #     self.max_data = getMoscowDateTime()
    #     self.min_data = self.max_data - self.__getInterval(interval)
    #
    #     '''==============================Если надо отображать все свечи=============================='''
    #     # if candles:
    #     #     min_timestamp: float = self.min_data.timestamp()
    #     #     max_timestamp: float = self.max_data.timestamp()
    #     #     interval_candles: list[QtCharts.QCandlestickSet] = []
    #     #
    #     #     '''------------------------------------Заполняем серию свечей------------------------------------'''
    #     #     for candle in candles:
    #     #         assert candle.low <= candle.open and candle.low <= candle.close and candle.low <= candle.high
    #     #         assert candle.high >= candle.open and candle.high >= candle.close
    #     #
    #     #         candlestick = getQCandlestickSetFromHistoricCandle(candle=candle, parent=self)
    #     #         candlestick_series.append(candlestick)
    #     #
    #     #         if min_timestamp <= candle.time.timestamp() <= max_timestamp:
    #     #             interval_candles.append(candlestick)
    #     #     '''----------------------------------------------------------------------------------------------'''
    #     #
    #     #     if interval_candles:
    #     #         '''---Определяем минимальную цену на выбранном отрезке времени---'''
    #     #         min_price: float = min(candle.low() for candle in interval_candles)
    #     #         max_price: float = max(candle.high() for candle in interval_candles)
    #     #         '''--------------------------------------------------------------'''
    #     #         axisY: QtCharts.QValueAxis = self.__createAxisY(min_price, max_price)
    #     #     else:
    #     #         axisY: QtCharts.QValueAxis = self.__createAxisY()
    #     # else:
    #     #     axisY: QtCharts.QValueAxis = self.__createAxisY()
    #     '''=========================================================================================='''
    #
    #     '''========================Если надо отображать только последние свечи========================'''
    #     if candles:
    #         min_timestamp: float = self.min_data.timestamp()
    #         max_timestamp: float = self.max_data.timestamp()
    #
    #         '''------------------------------------Заполняем серию свечей------------------------------------'''
    #         for candle in candles:
    #             assert candle.low <= candle.open and candle.low <= candle.close and candle.low <= candle.high
    #             assert candle.high >= candle.open and candle.high >= candle.close
    #
    #             if min_timestamp <= candle.time.timestamp() <= max_timestamp:
    #                 candlestick = getQCandlestickSetFromHistoricCandle(candle=candle, parent=self)
    #                 candlestick_series.append(candlestick)
    #         '''----------------------------------------------------------------------------------------------'''
    #
    #         if candlestick_series.sets():
    #             '''---Определяем минимальную цену на выбранном отрезке времени---'''
    #             min_price: float = min(candle.low() for candle in candlestick_series.sets())
    #             max_price: float = max(candle.high() for candle in candlestick_series.sets())
    #             '''--------------------------------------------------------------'''
    #             axisY: QtCharts.QValueAxis = self.__createAxisY(min_price, max_price)
    #         else:
    #             axisY: QtCharts.QValueAxis = self.__createAxisY()
    #     else:
    #         axisY: QtCharts.QValueAxis = self.__createAxisY()
    #     '''==========================================================================================='''
    #
    #     self.addAxis(axisY, QtCore.Qt.AlignmentFlag.AlignLeft)
    #
    #     axisX: QtCharts.QDateTimeAxis = self.__createAxisX(self.min_data, self.max_data)
    #     self.addAxis(axisX, QtCore.Qt.AlignmentFlag.AlignBottom)
    #
    #     self.addSeries(candlestick_series)
    #
    #     attachAxisX_flag: bool = candlestick_series.attachAxis(axisX)
    #     assert attachAxisX_flag, 'Не удалось прикрепить ось X к series.'
    #     attachAxisY_flag: bool = candlestick_series.attachAxis(axisY)
    #     assert attachAxisY_flag, 'Не удалось прикрепить ось Y к series.'


class CandlesViewAndGraphic(QtWidgets.QWidget):
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

    class __CandlesQueryModel(QtSql.QSqlQueryModel):
        __select_candles_command: str = 'SELECT \"open\", \"high\", \"low\", \"close\", \"volume\", \"time\", \"is_complete\" FROM \"'+MyConnection.CANDLES_TABLE+'\" WHERE \"instrument_id\" = \'{uid}\' and \"interval\" = \'{interval}\';'

        def __init__(self, instrument_uid: str | None, interval: CandleInterval, parent: QtCore.QObject | None = None):
            # self.__columns: tuple[Column, ...] = (
            #     Column(header='Открытие',
            #            header_tooltip='Цена открытия за 1 инструмент.',
            #            data_function=lambda candle: candle.open,
            #            display_function=lambda candle: MyQuotation.__str__(candle.open, ndigits=8, delete_decimal_zeros=True)),
            #     Column(header='Макс. цена',
            #            header_tooltip='Максимальная цена за 1 инструмент.',
            #            data_function=lambda candle: candle.high,
            #            display_function=lambda candle: MyQuotation.__str__(candle.high, ndigits=8, delete_decimal_zeros=True)),
            #     Column(header='Мин. цена',
            #            header_tooltip='Минимальная цена за 1 инструмент.',
            #            data_function=lambda candle: candle.low,
            #            display_function=lambda candle: MyQuotation.__str__(candle.low, ndigits=8, delete_decimal_zeros=True)),
            #     Column(header='Закрытие',
            #            header_tooltip='Цена закрытия за 1 инструмент.',
            #            data_function=lambda candle: candle.close,
            #            display_function=lambda candle: MyQuotation.__str__(candle.close, ndigits=8, delete_decimal_zeros=True)),
            #     Column(header='Объём',
            #            header_tooltip='Объём торгов в лотах.',
            #            data_function=lambda candle: candle.volume,
            #            display_function=lambda candle: str(candle.volume)),
            #     Column(header='Время',
            #            header_tooltip='Время свечи в часовом поясе UTC.',
            #            data_function=lambda candle: candle.time,
            #            display_function=lambda candle: str(candle.time)),
            #     Column(header='Завершённость',
            #            header_tooltip='Признак завершённости свечи. False значит, что свеча за текущий интервал ещё сформирована не полностью.',
            #            data_function=lambda candle: candle.is_complete,
            #            display_function=lambda candle: str(candle.is_complete))
            # )
            super().__init__(parent=parent)
            self.__interval: CandleInterval = interval
            self.instrument_uid = instrument_uid

        def __updateQuery(self):
            if self.instrument_uid is None:
                self.clear()
            else:
                self.setQuery(
                    self.__select_candles_command.format(uid=self.instrument_uid, interval=self.interval.name),
                    MainConnection.getDatabase()
                )
                assert not self.lastError().isValid(), 'Не получилось выполнить setQuery! lastError().text(): \'{0}\'.'.format(self.lastError().text())

        @property
        def instrument_uid(self) -> str | None:
            return self.__instrument_uid

        @instrument_uid.setter
        def instrument_uid(self, instrument_uid: str | None):
            self.__instrument_uid = instrument_uid
            self.__updateQuery()

        @property
        def interval(self) -> CandleInterval:
            return self.__interval

        @interval.setter
        def interval(self, interval: CandleInterval):
            self.__interval = interval
            self.__updateQuery()

        # def columnCount(self, parent: QtCore.QModelIndex = ...) -> int:
        #     return len(self.__columns)
        #
        # def data(self, index: QtCore.QModelIndex, role: int = ...) -> typing.Any:
        #     column: Column = self.__columns[index.column()]
        #
        #     row: int = index.row()
        #     open_: Quotation = MyConnection.convertTextToQuotation(self.record(row).value('open'))
        #     high: Quotation = MyConnection.convertTextToQuotation(self.record(row).value('high'))
        #     low: Quotation = MyConnection.convertTextToQuotation(self.record(row).value('low'))
        #     close: Quotation = MyConnection.convertTextToQuotation(self.record(row).value('close'))
        #     volume: int = self.record(row).value('volume')
        #     time: datetime = MyConnection.convertTextToDateTime(self.record(row).value('time'))
        #     is_complete: bool = MyConnection.convertBlobToBool(self.record(row).value('is_complete'))
        #     candle: HistoricCandle = HistoricCandle(open=open_, high=high, low=low, close=close, volume=volume,
        #                                             time=time, is_complete=is_complete)
        #
        #     return column(role, candle)

        # def headerData(self, section: int, orientation: QtCore.Qt.Orientation, role: int = ...) -> typing.Any:
        #     if orientation == QtCore.Qt.Orientation.Vertical:
        #         if role == QtCore.Qt.ItemDataRole.DisplayRole:
        #             return section + 1  # Проставляем номера строк.
        #     elif orientation == QtCore.Qt.Orientation.Horizontal:
        #         if role == QtCore.Qt.ItemDataRole.DisplayRole:
        #             return self.__columns[section].header
        #         elif role == QtCore.Qt.ItemDataRole.ToolTipRole:  # Подсказки.
        #             return self.__columns[section].header_tooltip

    class __CandlesModel(QtCore.QAbstractTableModel):
        def __init__(self, parent: QtCore.QObject | None = None):
            self.__columns: tuple[Column, ...] = (
                Column(header='Открытие',
                       header_tooltip='Цена открытия за 1 инструмент.',
                       data_function=lambda candle: candle.open,
                       display_function=lambda candle: MyQuotation.__str__(candle.open, ndigits=8, delete_decimal_zeros=True)),
                Column(header='Макс. цена',
                       header_tooltip='Максимальная цена за 1 инструмент.',
                       data_function=lambda candle: candle.high,
                       display_function=lambda candle: MyQuotation.__str__(candle.high, ndigits=8, delete_decimal_zeros=True)),
                Column(header='Мин. цена',
                       header_tooltip='Минимальная цена за 1 инструмент.',
                       data_function=lambda candle: candle.low,
                       display_function=lambda candle: MyQuotation.__str__(candle.low, ndigits=8, delete_decimal_zeros=True)),
                Column(header='Закрытие',
                       header_tooltip='Цена закрытия за 1 инструмент.',
                       data_function=lambda candle: candle.close,
                       display_function=lambda candle: MyQuotation.__str__(candle.close, ndigits=8, delete_decimal_zeros=True)),
                Column(header='Объём',
                       header_tooltip='Объём торгов в лотах.',
                       data_function=lambda candle: candle.volume,
                       display_function=lambda candle: str(candle.volume)),
                Column(header='Время',
                       header_tooltip='Время свечи в часовом поясе UTC.',
                       data_function=lambda candle: candle.time,
                       display_function=lambda candle: str(candle.time)),
                Column(header='Завершённость',
                       header_tooltip='Признак завершённости свечи. False значит, что свеча за текущий интервал ещё сформирована не полностью.',
                       data_function=lambda candle: candle.is_complete,
                       display_function=lambda candle: str(candle.is_complete))
            )
            super().__init__(parent=parent)
            self.__candlestick_series: QtCharts.QCandlestickSeries = QtCharts.QCandlestickSeries(parent=self)
            self.__candlestick_series.setDecreasingColor(QtCore.Qt.GlobalColor.red)
            self.__candlestick_series.setIncreasingColor(QtCore.Qt.GlobalColor.green)

        def columnCount(self, parent: QtCore.QModelIndex = ...) -> int:
            return len(self.__columns)

        def rowCount(self, parent: QtCore.QModelIndex = ...) -> int:
            return len(self.__candlestick_series.sets())

        def data(self, index: QtCore.QModelIndex, role: int = ...) -> typing.Any:
            column: Column = self.__columns[index.column()]
            candlestick: CandlesViewAndGraphic.Candlestick = self.candles[index.row()]
            return column(role, candlestick.historic_candle)

        def headerData(self, section: int, orientation: QtCore.Qt.Orientation, role: int = ...) -> typing.Any:
            if orientation == QtCore.Qt.Orientation.Vertical:
                if role == QtCore.Qt.ItemDataRole.DisplayRole:
                    return section + 1  # Проставляем номера строк.
            elif orientation == QtCore.Qt.Orientation.Horizontal:
                if role == QtCore.Qt.ItemDataRole.DisplayRole:
                    return self.__columns[section].header
                elif role == QtCore.Qt.ItemDataRole.ToolTipRole:  # Подсказки.
                    return self.__columns[section].header_tooltip

        def setCandles(self, candles: list[HistoricCandle]):
            self.beginResetModel()
            self.__candlestick_series.clear()
            self.__candlestick_series.append(CandlesViewAndGraphic.Candlestick(candle=candle, parent=self) for candle in candles)
            self.endResetModel()

        @property
        def candles(self) -> list[CandlesViewAndGraphic.Candlestick]:
            return self.__candlestick_series.sets()

        def appendCandle(self, candle: HistoricCandle):
            candles_count: int = self.__candlestick_series.count()
            self.beginInsertRows(QtCore.QModelIndex(), candles_count, candles_count)
            self.__candlestick_series.append(CandlesViewAndGraphic.Candlestick(candle=candle, parent=self))
            self.endInsertRows()

    class GroupBox_CandlesView(QtWidgets.QGroupBox):
        """Панель отображения свечей."""
        def __init__(self, candles_model, parent: QtWidgets.QWidget | None = None):
            super().__init__(parent=parent)
            self.setEnabled(False)

            verticalLayout_main = QtWidgets.QVBoxLayout(self)
            verticalLayout_main.setContentsMargins(2, 2, 2, 2)
            verticalLayout_main.setSpacing(2)

            '''------------------------Заголовок------------------------'''
            self.titlebar = TitleWithCount(title='СВЕЧИ', count_text='0', parent=self)
            verticalLayout_main.addLayout(self.titlebar, 0)
            '''---------------------------------------------------------'''

            self.tableView = QtWidgets.QTableView(parent=self)
            self.tableView.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
            self.tableView.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
            self.tableView.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
            self.tableView.setSortingEnabled(True)
            self.tableView.setModel(candles_model)
            verticalLayout_main.addWidget(self.tableView, 1)
            self.setEnabled(True)

    class GroupBox_Chart(QtWidgets.QGroupBox):
        """Панель с диаграммой."""
        def __init__(self, parent: QtWidgets.QWidget | None = None):
            super().__init__(parent=parent)
            self.setEnabled(False)

            verticalLayout_main = QtWidgets.QVBoxLayout(self)
            verticalLayout_main.setContentsMargins(2, 2, 2, 2)
            verticalLayout_main.setSpacing(2)

            verticalLayout_main.addWidget(TitleLabel(text='ГРАФИК', parent=self), 0)

            '''---------------------QChartView---------------------'''
            self.chart_view = QtCharts.QChartView(parent=self)
            self.chart_view.setRubberBand(QtCharts.QChartView.RubberBand.RectangleRubberBand)
            chart = CandlesChart()
            self.chart_view.setChart(chart)
            verticalLayout_main.addWidget(self.chart_view, 1)
            '''----------------------------------------------------'''

            self.setEnabled(True)

    def __init__(self, instrument_uid: str | None, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)
        self.setEnabled(False)

        # self.__instrument_uid: str | None = None
        # self.__candles_model = self.__CandlesModel(parent=self)
        # self.__candles_model = self.__CandlesQueryModel(instrument_uid=None, interval=CandleInterval.CANDLE_INTERVAL_UNSPECIFIED, parent=self)

        verticalLayout_main = QtWidgets.QVBoxLayout(self)
        verticalLayout_main.setContentsMargins(0, 0, 0, 0)
        verticalLayout_main.setSpacing(0)

        splitter_horizontal = QtWidgets.QSplitter(orientation=QtCore.Qt.Orientation.Horizontal, parent=self)

        '''---------------------------------Левая часть---------------------------------'''
        layoutWidget = QtWidgets.QWidget(parent=splitter_horizontal)

        verticalLayout = QtWidgets.QVBoxLayout(layoutWidget)
        verticalLayout.setContentsMargins(0, 3, 0, 0)
        verticalLayout.setSpacing(3)

        '''--------------------Выбор интервала свечей--------------------'''
        horizontalLayout_interval = QtWidgets.QHBoxLayout(layoutWidget)
        horizontalLayout_interval.addSpacing(2)
        horizontalLayout_interval.addWidget(QtWidgets.QLabel(text='Интервал:', parent=layoutWidget), 0)
        horizontalLayout_interval.addSpacing(4)
        self.comboBox_interval = ComboBox_Interval(parent=layoutWidget)
        horizontalLayout_interval.addWidget(self.comboBox_interval, 0)
        horizontalLayout_interval.addStretch(1)
        verticalLayout.addLayout(horizontalLayout_interval, 0)
        '''--------------------------------------------------------------'''

        self.__candles_model = self.__CandlesQueryModel(instrument_uid=instrument_uid,
                                                        interval=self.interval,
                                                        parent=self)
        self.groupBox_view = self.GroupBox_CandlesView(candles_model=self.__candles_model, parent=layoutWidget)
        verticalLayout.addWidget(self.groupBox_view, 1)
        '''-----------------------------------------------------------------------------'''

        # self.groupBox_chart = self.GroupBox_Chart(parent=splitter_horizontal)
        self.groupBox_chart = GroupBox_Chart(instrument_uid=instrument_uid, interval=self.interval, parent=splitter_horizontal)

        verticalLayout_main.addWidget(splitter_horizontal)

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
        self.__candles_model.interval = interval
        # self.candles = [] if self.instrument_uid is None else MainConnection.getCandles(uid=self.instrument_uid, interval=interval)
        self.groupBox_chart.setInterval(interval)

    # @property
    # def candles(self) -> list[HistoricCandle]:
    #     return self.__candles_model.candles

    # @candles.setter
    # def candles(self, candles: list[HistoricCandle]):
    #     self.__candles_model.setCandles(candles)
    #
    #     self.groupBox_view.tableView.resizeColumnsToContents()  # Авторазмер столбцов под содержимое.
    #     self.groupBox_view.label_count.setText(str(self.groupBox_view.tableView.model().rowCount()))  # Отображаем количество облигаций.
    #
    #     # self.groupBox_chart.setCandles(candles=self.candles, interval=self.interval)

    # def appendCandle(self, candle: HistoricCandle):
    #     self.__candles_model.appendCandle(candle)
    #
    #     # self.groupBox_view.tableView.resizeColumnsToContents()  # Авторазмер столбцов под содержимое.
    #     # self.groupBox_view.label_count.setText(str(self.groupBox_view.tableView.model().rowCount()))  # Отображаем количество облигаций.
    #
    #     # self.groupBox_chart.setCandles(candles=self.candles, interval=self.interval)

    @property
    def instrument_uid(self) -> str | None:
        return self.__candles_model.instrument_uid

    @instrument_uid.setter
    def instrument_uid(self, instrument_uid: str | None):
        # self.__instrument_uid = instrument_uid
        self.__candles_model.instrument_uid = instrument_uid
        # self.candles = [] if self.instrument_uid is None else MainConnection.getCandles(uid=self.instrument_uid, interval=self.interval)
        self.groupBox_chart.setInstrument(instrument_uid)

    def setInstrumentUid(self, instrument_uid: str | None = None):
        self.instrument_uid = instrument_uid

    # @QtCore.pyqtSlot(int)
    # def onCandlesChanges(self, rowid: int):
    #     db: QtSql.QSqlDatabase = MainConnection.getDatabase()
    #     if db.transaction():
    #         __select_candle: str = '''SELECT \"instrument_id\", \"interval\", \"open\", \"high\", \"low\", \"close\",
    #         \"volume\", \"time\", \"is_complete\" FROM \"{0}\" WHERE \"rowid\" = :rowid;'''.format(
    #             MyConnection.CANDLES_TABLE
    #         )
    #
    #         select_candle_query = QtSql.QSqlQuery(db)
    #         select_candle_prepare_flag: bool = select_candle_query.prepare(__select_candle)
    #         assert select_candle_prepare_flag, select_candle_query.lastError().text()
    #         select_candle_query.bindValue(':rowid', rowid)
    #         select_candle_exec_flag: bool = select_candle_query.exec()
    #         assert select_candle_exec_flag, select_candle_query.lastError().text()
    #
    #         candle: HistoricCandle
    #         candles_count: int = 0
    #         while select_candle_query.next():
    #             candles_count += 1
    #             if candles_count > 1:
    #                 raise SystemError('Таблица {0} не должна содержать больше одной строки с rowid = \'{1}\'!'.format(MyConnection.CANDLES_TABLE, rowid))
    #
    #             if select_candle_query.value('instrument_id') != self.instrument_uid:
    #                 commit_flag: bool = db.commit()  # Фиксирует транзакцию в базу данных.
    #                 assert commit_flag, db.lastError().text()
    #                 return
    #
    #             interval: CandleInterval = CandleInterval.from_string(select_candle_query.value('interval'))
    #             if interval != self.interval:
    #                 commit_flag: bool = db.commit()  # Фиксирует транзакцию в базу данных.
    #                 assert commit_flag, db.lastError().text()
    #                 return
    #
    #             candle = MyConnection.getHistoricCandle(select_candle_query)
    #
    #         commit_flag: bool = db.commit()  # Фиксирует транзакцию в базу данных.
    #         assert commit_flag, db.lastError().text()
    #
    #         if candles_count == 0:
    #             """Свеча была удалена."""
    #             ...
    #         else:
    #             """Свеча была добавлена или обновлена."""
    #             time_indexes: list[int] = [i for i, cndl in enumerate(self.candles) if cndl.time == candle.time]
    #             indexes_count: int = len(time_indexes)
    #             if indexes_count == 0:
    #                 """Свеча была добавлена."""
    #                 self.appendCandle(candle)
    #             elif indexes_count == 1:
    #                 """Свеча была обновлена."""
    #                 new_candles: list[HistoricCandle] = self.candles.copy()
    #                 new_candles[time_indexes[0]] = candle
    #                 self.candles = new_candles
    #             else:
    #                 raise SystemError('Список свечей не должен содержать несколько свечей, относящихся к одному и тому же времени!')
    #     else:
    #         raise SystemError('Не получилось начать транзакцию! db.lastError().text(): \'{0}\'!'.format(db.lastError().text()))


class CandlesPage_new(QtWidgets.QWidget):
    """Страница свечей."""
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
        # self.groupBox_candles_view = GroupBox_CandlesView(parent=splitter_vertical)
        self.groupBox_candles_view = CandlesViewAndGraphic(instrument_uid=self.instrument_uid, parent=splitter_vertical)
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
        self.groupBox_candles_view.setInstrumentUid(None if instrument is None else instrument.uid)
        self.groupBox_instrument_info.setInstrument(instrument)
        self.groupBox_candles_receiving.setInstrument(instrument)
        self.groupBox_candles_view.setInstrumentUid(self.instrument_uid)
