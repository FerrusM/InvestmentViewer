import typing
from datetime import datetime
from enum import Enum
from PyQt6 import QtWidgets, QtCore
from tinkoff.invest.schemas import GetForecastResponse, ConsensusItem
from Classes import TokenClass, print_slot, Column
from DatabaseWidgets import GroupBox_InstrumentSelection, TokenSelectionBar
from LimitClasses import LimitPerMinuteSemaphore
from MyDatabase import MainConnection
from MyDateTime import getMoscowDateTime, getUtcDateTime
from MyQuotation import MyQuotation
from MyRequests import MyResponse, RequestTryClass, getForecast
from PagesClasses import ProgressBar_DataReceiving, TitleWithCount
from TokenModel import TokenListModel


class ConsensusItemsModel(QtCore.QAbstractTableModel):
    """Модель консенсус-прогнозов инструментов."""
    def __init__(self, instrument_uid: str | None = None, parent: QtCore.QObject | None = None):
        super().__init__(parent=parent)
        self.__instrument_uid: str | None = instrument_uid
        self.__consensus_items: list[ConsensusItem] = []
        self.__columns: tuple[Column, ...] = (
            Column(header='Тикер',
                   header_tooltip='Тикер инструмента',
                   data_function=lambda cf: cf.ticker),
            Column(header='Прогноз',
                   header_tooltip='Прогноз',
                   data_function=lambda cf: cf.recommendation.name),
            Column(header='Валюта',
                   header_tooltip='Валюта',
                   data_function=lambda cf: cf.currency),
            Column(header='Текущая цена',
                   header_tooltip='Текущая цена',
                   data_function=lambda cf: MyQuotation.__str__(cf.current_price, ndigits=8, delete_decimal_zeros=True)),
            Column(header='Прогнозируемая цена',
                   header_tooltip='Прогнозируемая цена',
                   data_function=lambda cf: MyQuotation.__str__(cf.consensus, ndigits=8, delete_decimal_zeros=True)),
            Column(header='Минимальная цена',
                   header_tooltip='Минимальная цена прогноза',
                   data_function=lambda cf: MyQuotation.__str__(cf.min_target, ndigits=8, delete_decimal_zeros=True)),
            Column(header='Максимальная цена',
                   header_tooltip='Максимальная цена прогноза',
                   data_function=lambda cf: MyQuotation.__str__(cf.max_target, ndigits=8, delete_decimal_zeros=True)),
            Column(header='Изменение',
                   header_tooltip='Изменение цены',
                   data_function=lambda cf: MyQuotation.__str__(cf.price_change, ndigits=8, delete_decimal_zeros=True)),
            Column(header='Относительное изменение',
                   header_tooltip='Относительное изменение цены',
                   data_function=lambda cf: MyQuotation.__str__(cf.price_change_rel, ndigits=8, delete_decimal_zeros=True))
        )
        self.__update()

    def rowCount(self, parent: QtCore.QModelIndex = ...) -> int:
        return len(self.__consensus_items)

    def columnCount(self, parent: QtCore.QModelIndex = ...) -> int:
        return len(self.__columns)

    def __update(self):
        """Обновляет модель."""
        self.beginResetModel()
        if self.__instrument_uid is None:
            self.__consensus_items.clear()
        else:
            self.__consensus_items = MainConnection.getConsensusItems(instrument_uid=self.__instrument_uid)
        self.endResetModel()

    def data(self, index: QtCore.QModelIndex, role: int = ...) -> typing.Any:
        column = self.__columns[index.column()]
        return column(role, self.__consensus_items[index.row()])

    def resetInstrument(self):
        if self.__instrument_uid is not None:
            self.__instrument_uid = None
            self.__update()

    def setInstrument(self, instrument_uid: str | None):
        if instrument_uid is None:
            self.resetInstrument()
        else:
            self.__instrument_uid = instrument_uid
            self.__update()

    def headerData(self, section: int, orientation: QtCore.Qt.Orientation, role: int = ...) -> typing.Any:
        if orientation == QtCore.Qt.Orientation.Vertical:
            if role == QtCore.Qt.ItemDataRole.DisplayRole:
                return section + 1  # Проставляем номера строк.
        elif orientation == QtCore.Qt.Orientation.Horizontal:
            if role == QtCore.Qt.ItemDataRole.DisplayRole:
                return self.__columns[section].header
            elif role == QtCore.Qt.ItemDataRole.ToolTipRole:  # Подсказки.
                return self.__columns[section].header_tooltip


class MyTableViewGroupBox(QtWidgets.QGroupBox):
    def __init__(self, title: str, model: QtCore.QAbstractItemModel | None = None, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)

        verticalLayout_main = QtWidgets.QVBoxLayout(self)
        verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        verticalLayout_main.setSpacing(2)

        '''------------------------------Заголовок------------------------------'''
        self.title_widget = TitleWithCount(title=title, count_text='0', parent=self)
        verticalLayout_main.addLayout(self.title_widget, 0)
        '''---------------------------------------------------------------------'''

        '''------------------------------Отображение------------------------------'''
        self.tableView = QtWidgets.QTableView(parent=self)
        self.tableView.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tableView.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.tableView.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.tableView.setSortingEnabled(True)

        self.setModel(model)  # Подключаем модель к таблице.

        verticalLayout_main.addWidget(self.tableView, 1)
        '''-----------------------------------------------------------------------'''

    def setModel(self, model: QtCore.QAbstractItemModel | None):
        self.tableView.setModel(model)  # Подключаем модель к таблице.
        self.tableView.resizeColumnsToContents()  # Авторазмер столбцов под содержимое.


class ProgressThreadManagerBar(QtWidgets.QHBoxLayout):
    """Строка progressBar'а с кнопками управления потоком."""

    STOP: str = 'Стоп'
    PLAY: str = 'Пуск'
    PAUSE: str = 'Пауза'

    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self.setContentsMargins(0, 0, 0, 0)
        self.setSpacing(4)

        self.play_button = QtWidgets.QPushButton(text=self.PLAY, parent=parent)
        self.play_button.setEnabled(False)
        self.addWidget(self.play_button, 0)

        self.stop_button = QtWidgets.QPushButton(text=self.STOP, parent=parent)
        self.stop_button.setEnabled(False)
        self.addWidget(self.stop_button, 0)

        self.progressBar = ProgressBar_DataReceiving(parent=parent)
        self.addWidget(self.progressBar, 1)


class ForecastsReceivingGroupBox(QtWidgets.QGroupBox):

    class ThreadStatus(Enum):
        """Статус потока."""
        START_NOT_POSSIBLE = 0  # Поток не запущен. Запуск потока невозможен.
        START_POSSIBLE = 1  # Поток не запущен. Возможен запуск потока.
        RUNNING = 2  # Поток запущен.
        PAUSE = 3  # Поток приостановлен.
        FINISHED = 4  # Поток завершился.

    class ForecastsThread(QtCore.QThread):
        """Поток получения прогнозов."""

        receive_forecasts_method_name: str = 'GetForecastBy'

        forecastsReceived: QtCore.pyqtSignal = QtCore.pyqtSignal(GetForecastResponse)

        printText_signal: QtCore.pyqtSignal = QtCore.pyqtSignal(str)  # Сигнал для отображения сообщений в консоли.
        releaseSemaphore_signal: QtCore.pyqtSignal = QtCore.pyqtSignal(LimitPerMinuteSemaphore, int)  # Сигнал для освобождения ресурсов семафора из основного потока.

        '''-----------------Сигналы progressBar'а-----------------'''
        setProgressBarRange_signal: QtCore.pyqtSignal = QtCore.pyqtSignal(int, int)  # Сигнал для установления минимума и максимума progressBar'а заполнения купонов.
        setProgressBarValue_signal: QtCore.pyqtSignal = QtCore.pyqtSignal(int)  # Сигнал для изменения прогресса в progressBar'е.
        '''-------------------------------------------------------'''

        def __init__(self, token_class: TokenClass, uids: list[str], parent: QtCore.QObject | None = None):
            super().__init__(parent=parent)
            self.__mutex: QtCore.QMutex = QtCore.QMutex()
            self.__token: TokenClass = token_class
            self.__instruments_uids: list[str] = uids
            self.semaphore: LimitPerMinuteSemaphore | None = self.token.unary_limits_manager.getSemaphore(self.receive_forecasts_method_name)

            if self.semaphore is not None:
                @QtCore.pyqtSlot(LimitPerMinuteSemaphore, int)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
                def __releaseSemaphore(semaphore: LimitPerMinuteSemaphore, n: int):
                    semaphore.release(n)

                self.releaseSemaphore_signal.connect(__releaseSemaphore)  # Освобождаем ресурсы семафора из основного потока.

            '''------------Статистические переменные------------'''
            self.request_count: int = 0  # Общее количество запросов.
            self.control_point: datetime | None = None  # Начальная точка отсчёта времени.
            '''-------------------------------------------------'''

            self.__pause: bool = False
            self.__pause_condition: QtCore.QWaitCondition = QtCore.QWaitCondition()

            self.printText_signal.connect(print_slot)  # Сигнал для отображения сообщений в консоли.
            self.started.connect(lambda: print('{0}: Поток запущен. ({1})'.format(self.__class__.__name__, getMoscowDateTime())))
            self.finished.connect(lambda: print('{0}: Поток завершён. ({1})'.format(self.__class__.__name__, getMoscowDateTime())))

        @property
        def token(self) -> TokenClass:
            return self.__token

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
                self.printText_signal.emit('{0}: {1}'.format(self.__class__.__name__, text))

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
                printInConsole('Лимит для метода {0} не найден.'.format(self.receive_forecasts_method_name))
            else:
                instruments_count: int = len(self.__instruments_uids)  # Количество инструментов.
                self.setProgressBarRange_signal.emit(0, instruments_count)  # Задаёт минимум и максимум progressBar'а.

                for i, uid in enumerate(self.__instruments_uids):
                    instrument_number: int = i + 1  # Номер текущего инструмента.
                    self.setProgressBarValue_signal.emit(instrument_number)  # Отображаем прогресс в progressBar.

                    try_count: RequestTryClass = RequestTryClass(max_request_try_count=1)
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
                            printInConsole('{0} из {1} ({2:.2f}с)'.format(instrument_number, instruments_count, delta))
                        else:
                            printInConsole('{0} из {1}'.format(instrument_number, instruments_count))
                        self.control_point = getUtcDateTime()  # Промежуточная точка отсчёта времени.
                        '''-----------------------------------------------------------------'''

                        response = getForecast(token=self.token.token, uid=uid)
                        assert response.request_occurred, 'Запрос прогнозов не был произведён.'
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

                    forecasts: GetForecastResponse | None = response.response_data if response.ifDataSuccessfullyReceived() else None
                    if forecasts is None: continue  # Если поток был прерван или если информация не была получена.
                    self.forecastsReceived.emit(forecasts)

    def __init__(self, tokens_model: TokenListModel, parent: QtWidgets.QWidget | None = None):
        self.__instruments_uids: list[str] = []

        self.__forecasts_receiving_thread: ForecastsReceivingGroupBox.ForecastsThread | None = None
        self.__thread_status: ForecastsReceivingGroupBox.ThreadStatus = self.ThreadStatus.START_NOT_POSSIBLE

        super().__init__(parent=parent)

        verticalLayout_main = QtWidgets.QVBoxLayout(self)
        verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        verticalLayout_main.setSpacing(2)

        self.titlebar = TitleWithCount(title='ПОЛУЧЕНИЕ ПРОГНОЗОВ', count_text='0', parent=self)
        verticalLayout_main.addLayout(self.titlebar, 0)

        self.token_bar = TokenSelectionBar(tokens_model=tokens_model, parent=self)
        verticalLayout_main.addLayout(self.token_bar, 0)

        self.progressBar = ProgressThreadManagerBar(parent=self)
        verticalLayout_main.addLayout(self.progressBar, 0)

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

        self.token_bar.tokenSelected.connect(__onTokenSelected)
        self.token_bar.tokenReset.connect(__onTokenReset)

    def setStatus(self, token: TokenClass | None, uids: list[str], status: ThreadStatus):
        def stopThread():
            self.__forecasts_receiving_thread.requestInterruption()  # Сообщаем потоку о том, что надо завершиться.
            self.__forecasts_receiving_thread.wait()  # Ждём завершения потока.
            self.__forecasts_receiving_thread = None

        print('Статус: {0} -> {1}.'.format(self.__thread_status.name, status.name))
        match status:
            case self.ThreadStatus.START_NOT_POSSIBLE:
                assert token is None or not uids
                match self.__thread_status:
                    case self.ThreadStatus.START_NOT_POSSIBLE:
                        return
                    case self.ThreadStatus.START_POSSIBLE:
                        self.progressBar.play_button.setEnabled(False)
                        disconnect_flag: bool = self.progressBar.play_button.disconnect(self.start_thread_connection)
                        assert disconnect_flag, 'Не удалось отключить слот!'
                    case self.ThreadStatus.RUNNING:
                        self.progressBar.play_button.setEnabled(False)
                        self.progressBar.stop_button.setEnabled(False)

                        '''-------------------------Останавливаем поток-------------------------'''
                        assert self.__forecasts_receiving_thread is not None
                        disconnect_flag: bool = self.__forecasts_receiving_thread.disconnect(self.thread_finished_connection)
                        assert disconnect_flag, 'Не удалось отключить слот!'
                        stopThread()
                        '''---------------------------------------------------------------------'''

                        disconnect_flag: bool = self.progressBar.play_button.disconnect(self.pause_thread_connection)
                        assert disconnect_flag, 'Не удалось отключить слот!'

                        disconnect_flag: bool = self.progressBar.stop_button.disconnect(self.stop_thread_connection)
                        assert disconnect_flag, 'Не удалось отключить слот!'

                        self.progressBar.progressBar.reset()  # Сбрасываем progressBar.
                        self.progressBar.play_button.setText(self.progressBar.PLAY)
                    case self.ThreadStatus.PAUSE:
                        self.progressBar.play_button.setEnabled(False)
                        self.progressBar.stop_button.setEnabled(False)

                        '''-------------------------Останавливаем поток-------------------------'''
                        assert self.__forecasts_receiving_thread is not None
                        self.__forecasts_receiving_thread.resume()  # Возобновляем работу потока, чтобы он мог безопасно завершиться.
                        stopThread()
                        '''---------------------------------------------------------------------'''

                        self.progressBar.progressBar.reset()  # Сбрасываем progressBar.
                        self.progressBar.play_button.setText(self.progressBar.PLAY)

                        disconnect_flag: bool = self.progressBar.play_button.disconnect(self.resume_thread_connection)
                        assert disconnect_flag, 'Не удалось отключить слот!'
                    case self.ThreadStatus.FINISHED:
                        self.progressBar.play_button.setEnabled(False)

                        assert self.__forecasts_receiving_thread is None
                        self.progressBar.progressBar.reset()  # Сбрасываем progressBar.

                        disconnect_flag: bool = self.progressBar.play_button.disconnect(self.start_thread_connection)
                        assert disconnect_flag, 'Не удалось отключить слот!'
                    case _:
                        raise ValueError('Неверный статус потока!')

                self.__thread_status = self.ThreadStatus.START_NOT_POSSIBLE
            case self.ThreadStatus.START_POSSIBLE:
                assert token is not None and uids
                match self.__thread_status:
                    case self.ThreadStatus.START_NOT_POSSIBLE:
                        pass  # Ничего не требуется делать.
                    case self.ThreadStatus.START_POSSIBLE:
                        return
                    case self.ThreadStatus.RUNNING:
                        self.progressBar.play_button.setEnabled(False)
                        self.progressBar.stop_button.setEnabled(False)

                        '''-------------------------Останавливаем поток-------------------------'''
                        assert self.__forecasts_receiving_thread is not None
                        disconnect_flag: bool = self.__forecasts_receiving_thread.disconnect(self.thread_finished_connection)
                        assert disconnect_flag, 'Не удалось отключить слот!'
                        stopThread()
                        '''---------------------------------------------------------------------'''

                        self.progressBar.progressBar.reset()  # Сбрасываем progressBar.
                        self.progressBar.play_button.setText(self.progressBar.PLAY)

                        disconnect_flag: bool = self.progressBar.play_button.disconnect(self.pause_thread_connection)
                        assert disconnect_flag, 'Не удалось отключить слот!'

                        disconnect_flag: bool = self.progressBar.stop_button.disconnect(self.stop_thread_connection)
                        assert disconnect_flag, 'Не удалось отключить слот!'
                    case self.ThreadStatus.PAUSE:
                        self.progressBar.play_button.setEnabled(False)
                        self.progressBar.stop_button.setEnabled(False)

                        '''-------------------------Останавливаем поток-------------------------'''
                        assert self.__forecasts_receiving_thread is not None
                        disconnect_flag: bool = self.__forecasts_receiving_thread.disconnect(self.thread_finished_connection)
                        assert disconnect_flag, 'Не удалось отключить слот!'
                        self.__forecasts_receiving_thread.resume()  # Возобновляем работу потока, чтобы он мог безопасно завершиться.
                        stopThread()
                        '''---------------------------------------------------------------------'''

                        self.progressBar.progressBar.reset()  # Сбрасываем progressBar.
                        self.progressBar.play_button.setText(self.progressBar.PLAY)

                        disconnect_flag: bool = self.progressBar.play_button.disconnect(self.resume_thread_connection)
                        assert disconnect_flag, 'Не удалось отключить слот!'
                    case self.ThreadStatus.FINISHED:
                        self.progressBar.play_button.setEnabled(False)

                        assert self.__forecasts_receiving_thread is None
                        self.progressBar.progressBar.reset()  # Сбрасываем progressBar.

                        disconnect_flag: bool = self.progressBar.play_button.disconnect(self.start_thread_connection)
                        assert disconnect_flag, 'Не удалось отключить слот!'
                    case _:
                        raise ValueError('Неверный статус потока!')

                @QtCore.pyqtSlot()  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
                def __startThread():
                    """Запускает поток получения исторических свечей."""
                    self.setStatus(token=self.token, uids=self.uids, status=self.ThreadStatus.RUNNING)

                self.start_thread_connection = self.progressBar.play_button.clicked.connect(__startThread)

                self.__thread_status = self.ThreadStatus.START_POSSIBLE

                self.progressBar.play_button.setEnabled(True)
            case self.ThreadStatus.RUNNING:
                assert token is not None and uids
                match self.__thread_status:
                    case self.ThreadStatus.START_POSSIBLE:
                        self.progressBar.play_button.setEnabled(False)

                        disconnect_flag: bool = self.progressBar.play_button.disconnect(self.start_thread_connection)
                        assert disconnect_flag, 'Не удалось отключить слот!'

                        """==========================Поток необходимо запустить=========================="""
                        assert self.__forecasts_receiving_thread is None, 'Поток получения исторических свечей должен быть завершён!'
                        self.__forecasts_receiving_thread = self.ForecastsThread(token_class=token, uids=uids, parent=self)

                        '''---------------------Подключаем сигналы потока к слотам---------------------'''
                        @QtCore.pyqtSlot(int, int)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
                        def __setRange(minimum: int, maximum: int):
                            if self.__forecasts_receiving_thread is not None:
                                self.progressBar.progressBar.setRange(minimum, maximum)

                        self.__forecasts_receiving_thread.setProgressBarRange_signal.connect(__setRange)

                        @QtCore.pyqtSlot(int)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
                        def __setValue(value: int):
                            if self.__forecasts_receiving_thread is not None:
                                self.progressBar.progressBar.setValue(value)

                        self.__forecasts_receiving_thread.setProgressBarValue_signal.connect(__setValue)

                        self.__forecasts_receiving_thread.forecastsReceived.connect(MainConnection.insertForecasts)

                        self.thread_finished_connection = self.__forecasts_receiving_thread.finished.connect(lambda: self.setStatus(token=self.token, uids=self.uids, status=self.ThreadStatus.FINISHED))
                        '''----------------------------------------------------------------------------'''

                        self.__forecasts_receiving_thread.start()  # Запускаем поток.
                        """=============================================================================="""
                    case self.ThreadStatus.PAUSE:
                        self.progressBar.play_button.setEnabled(False)
                        self.progressBar.stop_button.setEnabled(False)

                        self.__forecasts_receiving_thread.resume()

                        disconnect_flag: bool = self.progressBar.play_button.disconnect(self.resume_thread_connection)
                        assert disconnect_flag, 'Не удалось отключить слот!'
                    case _:
                        raise ValueError('Неверный статус потока!')

                '''------------------------------Левая кнопка------------------------------'''
                self.progressBar.play_button.setText(self.progressBar.PAUSE)

                @QtCore.pyqtSlot()  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
                def __pauseThread():
                    """Приостанавливает поток получения исторических свечей."""
                    self.setStatus(token=self.token, uids=self.uids, status=self.ThreadStatus.PAUSE)

                self.pause_thread_connection = self.progressBar.play_button.clicked.connect(__pauseThread)
                '''------------------------------------------------------------------------'''

                '''------------------------------Правая кнопка------------------------------'''
                @QtCore.pyqtSlot()  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
                def __stopThread():
                    """Останавливает поток получения исторических свечей."""
                    self.setStatus(token=self.token, uids=self.uids, status=self.ThreadStatus.START_POSSIBLE)

                self.stop_thread_connection = self.progressBar.stop_button.clicked.connect(__stopThread)
                '''-------------------------------------------------------------------------'''

                self.__thread_status = self.ThreadStatus.RUNNING

                self.progressBar.play_button.setEnabled(True)
                self.progressBar.stop_button.setEnabled(True)
            case self.ThreadStatus.PAUSE:
                assert self.__thread_status is self.ThreadStatus.RUNNING, 'Поток переходит в статус PAUSE из статуса {0} минуя статус RUNNING!'.format(self.__thread_status.name)
                self.progressBar.play_button.setEnabled(False)
                self.progressBar.stop_button.setEnabled(False)

                self.__forecasts_receiving_thread.pause()

                self.progressBar.play_button.setText(self.progressBar.PLAY)

                disconnect_flag: bool = self.progressBar.play_button.disconnect(self.pause_thread_connection)
                assert disconnect_flag, 'Не удалось отключить слот!'

                @QtCore.pyqtSlot()  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
                def __resumeThread():
                    """Возобновляет работу потока получения исторических свечей."""
                    self.setStatus(token=self.token, uids=self.uids, status=self.ThreadStatus.RUNNING)

                self.resume_thread_connection = self.progressBar.play_button.clicked.connect(__resumeThread)

                self.__thread_status = self.ThreadStatus.PAUSE

                self.progressBar.play_button.setEnabled(True)
                self.progressBar.stop_button.setEnabled(True)
            case self.ThreadStatus.FINISHED:
                assert self.__thread_status is self.ThreadStatus.RUNNING, 'Поток переходит в статус FINISHED из статуса {0} минуя статус RUNNING!'.format(self.__thread_status.name)
                self.progressBar.play_button.setEnabled(False)
                self.progressBar.stop_button.setEnabled(False)

                assert self.__forecasts_receiving_thread.isFinished()
                self.__forecasts_receiving_thread = None

                self.progressBar.play_button.setText(self.progressBar.PLAY)

                disconnect_flag: bool = self.progressBar.play_button.disconnect(self.pause_thread_connection)
                assert disconnect_flag, 'Не удалось отключить слот!'

                disconnect_flag: bool = self.progressBar.stop_button.disconnect(self.stop_thread_connection)
                assert disconnect_flag, 'Не удалось отключить слот!'

                @QtCore.pyqtSlot()  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
                def __startThread():
                    """Запускает поток получения исторических свечей."""
                    self.setStatus(token=self.token, uids=self.uids, status=self.ThreadStatus.START_POSSIBLE)
                    self.setStatus(token=self.token, uids=self.uids, status=self.ThreadStatus.RUNNING)

                self.start_thread_connection = self.progressBar.play_button.clicked.connect(__startThread)

                self.__thread_status = self.ThreadStatus.FINISHED

                self.progressBar.play_button.setEnabled(True)
            case _:
                raise ValueError('Неверный статус потока!')

    def __onParameterChanged(self, token: TokenClass | None, uids: list[str]):
        status = self.ThreadStatus.START_NOT_POSSIBLE if token is None or not uids else self.ThreadStatus.START_POSSIBLE
        self.setStatus(token=token, uids=uids, status=status)

    @property
    def token(self) -> TokenClass | None:
        return self.token_bar.token

    @token.setter
    def token(self, token: TokenClass | None):
        self.__onParameterChanged(token=token, uids=self.uids)

    @property
    def uids(self) -> list[str]:
        return self.__instruments_uids

    def setInstruments(self, instruments_uids: list[str]):
        self.__instruments_uids = instruments_uids
        self.__onParameterChanged(token=self.token, uids=self.uids)
        self.titlebar.setCount(str(len(self.uids)))


class ForecastsPage(QtWidgets.QWidget):
    """Страница прогнозов."""
    class ConsensusItemsModel(QtCore.QAbstractTableModel):
        def __init__(self, parent: QtCore.QObject | None = None):
            super().__init__(parent=parent)
            pass
            self.__items: list = []

        def rowCount(self, parent: QtCore.QModelIndex = ...) -> int:
            return len(self.__items)

        def columnCount(self, parent: QtCore.QModelIndex = ...) -> int:
            pass
            return 0

    def __init__(self, tokens_model: TokenListModel, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)

        verticalLayout_main = QtWidgets.QVBoxLayout(self)
        verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        verticalLayout_main.setSpacing(2)

        horizontalLayout_top = QtWidgets.QHBoxLayout()
        horizontalLayout_top.setSpacing(2)

        self.groupBox_instrument_selection = GroupBox_InstrumentSelection(tokens_model=tokens_model, parent=self)
        horizontalLayout_top.addWidget(self.groupBox_instrument_selection, 1)

        verticalLayout_progressBar = QtWidgets.QVBoxLayout(self)
        verticalLayout_progressBar.setSpacing(0)
        self.progressBar = ForecastsReceivingGroupBox(tokens_model=tokens_model, parent=self)
        self.progressBar.setInstruments(self.groupBox_instrument_selection.comboBox_instrument.model().uids)
        # self.groupBox_instrument_selection.comboBox_instrument.model().modelReset.connect(lambda: self.progressBar.setInstruments(self.groupBox_instrument_selection.comboBox_instrument.model().uids))
        self.groupBox_instrument_selection.comboBox_instrument.instrumentsListChanged.connect(self.progressBar.setInstruments)
        verticalLayout_progressBar.addWidget(self.progressBar, 0)
        verticalLayout_progressBar.addStretch(1)
        horizontalLayout_top.addLayout(verticalLayout_progressBar, 1)

        verticalLayout_main.addLayout(horizontalLayout_top, 0)

        horizontalLayout_bottom = QtWidgets.QHBoxLayout()
        horizontalLayout_bottom.setSpacing(2)

        self.consensuses_view = MyTableViewGroupBox(title='КОНСЕНСУС-ПРОГНОЗЫ', model=None, parent=self)
        consensuses_model = ConsensusItemsModel(instrument_uid=self.instrument_uid, parent=self.consensuses_view)

        @QtCore.pyqtSlot(str)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
        def __onInstrumentChanged(instrument_uid: str):
            consensuses_model.setInstrument(instrument_uid)
            self.consensuses_view.tableView.resizeColumnsToContents()

        self.groupBox_instrument_selection.comboBox_instrument.instrumentChanged.connect(__onInstrumentChanged)

        @QtCore.pyqtSlot()  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
        def __onInstrumentReset():
            consensuses_model.setInstrument(None)
            self.consensuses_view.tableView.resizeColumnsToContents()

        self.groupBox_instrument_selection.comboBox_instrument.instrumentReset.connect(__onInstrumentReset)

        self.consensuses_view.setModel(consensuses_model)
        horizontalLayout_bottom.addWidget(self.consensuses_view, 1)

        self.targets_view = MyTableViewGroupBox(title='ПРОГНОЗЫ', model=ForecastsPage.ConsensusItemsModel(self), parent=self)
        horizontalLayout_bottom.addWidget(self.targets_view, 1)

        verticalLayout_main.addLayout(horizontalLayout_bottom, 1)

    @property
    def instrument_uid(self) -> str | None:
        return self.groupBox_instrument_selection.uid
