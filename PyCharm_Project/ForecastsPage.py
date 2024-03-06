from __future__ import annotations
import typing
from datetime import datetime
from enum import Enum
from PyQt6 import QtWidgets, QtCore
from tinkoff.invest.schemas import GetForecastResponse, ConsensusItem, TargetItem
from Classes import TokenClass, print_slot, ColumnWithHeader, Header, ColumnWithoutHeader, ConsensusFull
from DatabaseWidgets import GroupBox_InstrumentSelection, TokenSelectionBar
from LimitClasses import LimitPerMinuteSemaphore
from MyDatabase import MainConnection
from MyDateTime import getMoscowDateTime, getUtcDateTime
from MyQuotation import MyQuotation
from MyRequests import MyResponse, RequestTryClass, getForecast
from PagesClasses import ProgressBar_DataReceiving, TitleWithCount
from TokenModel import TokenListModel


# class TreeItem:
#     def __init__(self, row: int, parent_item: TreeItem | None = None, data: AssetClass | AssetInstrument | None = None, children: list[TreeItem] | None = None):
#         self.__parent: TreeItem | None = parent_item  # Родительский элемент.
#         self.__data: AssetClass | AssetInstrument | None = data
#         self.__children: list[TreeItem] = [] if children is None else children  # Список дочерних элементов.
#         self.__row: int = row  # Номер строки элемента.
#         self.__hierarchy_level: int = -1 if parent_item is None else (parent_item.getHierarchyLevel() + 1)
#
#     @property
#     def data(self) -> AssetClass | AssetInstrument | None:
#         return self.__data
#
#     def parent(self) -> TreeItem | None:
#         """Возвращает родительский элемент."""
#         return self.__parent
#
#     def setChildren(self, children: list[TreeItem] | None):
#         if children is None:
#             self.__children.clear()
#         else:
#             self.__children = children
#
#     @property
#     def children_count(self) -> int:
#         """Возвращает количество дочерних элементов."""
#         return len(self.__children)
#
#     def child(self, row: int) -> TreeItem | None:
#         return None if row >= self.children_count or row < 0 else self.__children[row]
#
#     def row(self) -> int:
#         """Возвращает номер строки элемента."""
#         return self.__row
#
#     def getHierarchyLevel(self) -> int:
#         """Возвращает уровень иерархии элемента."""
#         return self.__hierarchy_level


# class ForecastsModel(QtCore.QAbstractItemModel):
#     """Модель прогнозов."""
#     class ColumnItem:
#         def __init__(self, header: Header, consensus_column: ColumnWithoutHeader, target_column: ColumnWithoutHeader):
#             self.__header: Header = header
#             self.__consensus_column: ColumnWithoutHeader = consensus_column
#             self.__target_column: ColumnWithoutHeader = target_column
#
#         def consensus_column(self, role: int = QtCore.Qt.ItemDataRole.UserRole):
#             return self.__consensus_column(role=role)
#
#     def __init__(self, instrument_uid: str | None = None, parent: QtCore.QObject | None = None):
#         super().__init__(parent=parent)
#         self.__instrument_uid: str | None = instrument_uid
#         self.__consensus_fulls: list[ConsensusFull] = []
#         self.__columns: tuple[ForecastsModel.ColumnItem, ...] = (
#             ForecastsModel.ColumnItem(
#                 header=Header(
#                     title='Тикер',
#                     tooltip='Тикер инструмента'
#                 ),
#                 consensus_column=ColumnWithoutHeader(
#                     data_function=lambda ci: ci.ticker
#                 ),
#                 target_column=ColumnWithoutHeader(
#                     data_function=lambda ti: ti.ticker
#                 )
#             ),
#             ForecastsModel.ColumnItem(
#                 header=Header(
#                     title='Прогноз',
#                     tooltip='Прогноз'
#                 ),
#                 consensus_column=ColumnWithoutHeader(
#                     data_function=lambda ci: ci.recommendation.name
#                 ),
#                 target_column=ColumnWithoutHeader(
#                     data_function=lambda ti: ti.recommendation.name
#                 )
#             ),
#             ForecastsModel.ColumnItem(
#                 header=Header(
#                     title='Дата прогноза',
#                     tooltip='Дата прогноза'
#                 ),
#                 consensus_column=ColumnWithoutHeader(
#                     data_function=lambda ci: ci.consensus_number,
#                     display_function=lambda ci: str(ci.consensus_number)
#                 ),
#                 target_column=ColumnWithoutHeader(
#                     data_function=lambda ti: ti.recommendation_date,
#                     display_function=lambda ti: str(ti.recommendation_date)
#                 )
#             )
#         )
#         self.__update()
#
#     def __update(self):
#         """Обновляет модель."""
#         self.beginResetModel()
#         if self.__instrument_uid is None:
#             self.__items.clear()
#         else:
#             self.__items = MainConnection.getConsensusFulls(instrument_uid=self.__instrument_uid)
#         self.endResetModel()
#
#     def index(self, row: int, column: int, parent: QtCore.QModelIndex = ...) -> QtCore.QModelIndex:
#         if parent.isValid():  # Если индекс parent действителен.
#             consensus_full: ConsensusFull = parent.internalPointer()  # Указатель на внутреннюю структуру данных.
#             return self.createIndex(row, column, consensus_full.targets[row])
#         else:
#             return self.createIndex(row, column, self.__consensus_fulls[row])
#
#     def rowCount(self, parent: QtCore.QModelIndex = ...) -> int:
#         if parent.isValid():  # Если индекс parent действителен.
#             consensus_full: ConsensusFull = parent.internalPointer()  # Указатель на внутреннюю структуру данных.
#             return len(consensus_full.targets)
#         else:
#             return len(self.__consensus_fulls)
#
#     def columnCount(self, parent: QtCore.QModelIndex = ...) -> int:
#         return len(self.__columns)
#
#     def parent(self, child: QtCore.QModelIndex) -> QtCore.QModelIndex:
#         if child.isValid():  # Если индекс child действителен.
#             target_item: TargetItem = child.internalPointer()  # Указатель на внутреннюю структуру данных.
#             ...
#         else:
#             ...


class ConsensusItemsModel(QtCore.QAbstractTableModel):
    """Модель консенсус-прогнозов."""
    def __init__(self, instrument_uid: str | None = None, parent: QtCore.QObject | None = None):
        super().__init__(parent=parent)
        self.__instrument_uid: str | None = instrument_uid
        self.__consensus_items: list[ConsensusItem] = []
        self.__columns: tuple[ColumnWithHeader, ...] = (
            ColumnWithHeader(header=Header(title='Тикер', tooltip='Тикер инструмента'),
                             data_function=lambda cf: cf.ticker),
            ColumnWithHeader(header=Header(title='Прогноз', tooltip='Прогноз'),
                             data_function=lambda cf: cf.recommendation.name),
            ColumnWithHeader(header=Header(title='Валюта', tooltip='Валюта'),
                             data_function=lambda cf: cf.currency),
            ColumnWithHeader(header=Header(title='Текущая цена', tooltip='Текущая цена'),
                             data_function=lambda cf: MyQuotation.__str__(cf.current_price, ndigits=8, delete_decimal_zeros=True)),
            ColumnWithHeader(header=Header(title='Прогноз. цена', tooltip='Прогнозируемая цена'),
                             data_function=lambda cf: MyQuotation.__str__(cf.consensus, ndigits=8, delete_decimal_zeros=True)),
            ColumnWithHeader(header=Header(title='Мин. цена', tooltip='Минимальная цена прогноза'),
                             data_function=lambda cf: MyQuotation.__str__(cf.min_target, ndigits=8, delete_decimal_zeros=True)),
            ColumnWithHeader(header=Header(title='Макс. цена', tooltip='Максимальная цена прогноза'),
                             data_function=lambda cf: MyQuotation.__str__(cf.max_target, ndigits=8, delete_decimal_zeros=True)),
            ColumnWithHeader(header=Header(title='Изменение', tooltip='Изменение цены'),
                             data_function=lambda cf: MyQuotation.__str__(cf.price_change, ndigits=8, delete_decimal_zeros=True)),
            ColumnWithHeader(header=Header(title='Относ. изменение', tooltip='Относительное изменение цены'),
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
        column: ColumnWithHeader = self.__columns[index.column()]
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
            return self.__columns[section].header(role=role)


class TargetItemsModel(QtCore.QAbstractTableModel):
    """Модель прогнозов."""
    def __init__(self, instrument_uid: str | None = None, parent: QtCore.QObject | None = None):
        super().__init__(parent=parent)
        self.__instrument_uid: str | None = instrument_uid
        self.__target_items: list[TargetItem] = []
        self.__columns: tuple[ColumnWithHeader, ...] = (
            ColumnWithHeader(header=Header(title='Тикер', tooltip='Тикер инструмента'),
                             data_function=lambda ti: ti.ticker),
            ColumnWithHeader(header=Header(title='Компания', tooltip='Название компании, давшей прогноз'),
                             data_function=lambda ti: ti.company),
            ColumnWithHeader(header=Header(title='Прогноз', tooltip='Прогноз'),
                             data_function=lambda ti: ti.recommendation.name),
            ColumnWithHeader(header=Header(title='Дата прогноза', tooltip='Дата прогноза'),
                             display_function=lambda ti: str(ti.recommendation_date),
                             data_function=lambda ti: ti.recommendation_date),
            ColumnWithHeader(header=Header(title='Валюта', tooltip='Валюта'),
                             data_function=lambda ti: ti.currency),
            ColumnWithHeader(header=Header(title='Текущая цена', tooltip='Текущая цена'),
                             data_function=lambda ti: MyQuotation.__str__(ti.current_price, ndigits=8, delete_decimal_zeros=True)),
            ColumnWithHeader(header=Header(title='Прогноз. цена', tooltip='Прогнозируемая цена'),
                             data_function=lambda ti: MyQuotation.__str__(ti.target_price, ndigits=8, delete_decimal_zeros=True)),
            ColumnWithHeader(header=Header(title='Изменение', tooltip='Изменение цены'),
                             data_function=lambda ti: MyQuotation.__str__(ti.price_change, ndigits=8, delete_decimal_zeros=True)),
            ColumnWithHeader(header=Header(title='Относ. изменение', tooltip='Относительное изменение цены'),
                             data_function=lambda ti: MyQuotation.__str__(ti.price_change_rel, ndigits=8, delete_decimal_zeros=True)),
            # ColumnWithHeader(header=Header(title='Имя', tooltip='Наименование инструмента'),
            #                  data_function=lambda ti: ti.show_name)
        )
        self.__update()

    def rowCount(self, parent: QtCore.QModelIndex = ...) -> int:
        return len(self.__target_items)

    def columnCount(self, parent: QtCore.QModelIndex = ...) -> int:
        return len(self.__columns)

    def __update(self):
        """Обновляет модель."""
        self.beginResetModel()
        if self.__instrument_uid is None:
            self.__target_items.clear()
        else:
            self.__target_items = MainConnection.getTargetItems(instrument_uid=self.__instrument_uid)
        self.endResetModel()

    def data(self, index: QtCore.QModelIndex, role: int = ...) -> typing.Any:
        column: ColumnWithHeader = self.__columns[index.column()]
        return column(role, self.__target_items[index.row()])

    def headerData(self, section: int, orientation: QtCore.Qt.Orientation, role: int = ...) -> typing.Any:
        if orientation == QtCore.Qt.Orientation.Vertical:
            if role == QtCore.Qt.ItemDataRole.DisplayRole:
                return section + 1  # Проставляем номера строк.
        elif orientation == QtCore.Qt.Orientation.Horizontal:
            return self.__columns[section].header(role=role)

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


class MyTableViewGroupBox(QtWidgets.QGroupBox):
    def __init__(self, title: str, model: QtCore.QAbstractItemModel | None = None, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)

        verticalLayout_main = QtWidgets.QVBoxLayout(self)
        verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        verticalLayout_main.setSpacing(2)

        '''------------------------------Заголовок------------------------------'''
        self.__titlebar = TitleWithCount(title=title, count_text='0', parent=self)
        verticalLayout_main.addLayout(self.__titlebar, 0)
        '''---------------------------------------------------------------------'''

        '''------------------------------Отображение------------------------------'''
        self.__tableView = QtWidgets.QTableView(parent=self)
        self.__tableView.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.__tableView.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.__tableView.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.__tableView.setSortingEnabled(True)

        self.__model_reset_connection: QtCore.QMetaObject.Connection

        self.setModel(model)  # Подключаем модель к таблице.

        verticalLayout_main.addWidget(self.__tableView, 1)
        '''-----------------------------------------------------------------------'''

    def setModel(self, model: QtCore.QAbstractItemModel | None):
        old_model: QtCore.QAbstractItemModel | None = self.__tableView.model()
        if old_model is not None:
            disconnect_flag: bool = old_model.disconnect(self.__model_reset_connection)
            assert disconnect_flag, 'Не удалось отключить слот!'

        self.__tableView.setModel(model)  # Подключаем модель к таблице.

        if model is not None:
            def __onModelUpdated():
                """Выполняется при изменении модели."""
                self.__titlebar.setCount(str(model.rowCount()))
                self.__tableView.resizeColumnsToContents()  # Авторазмер столбцов под содержимое.

            __onModelUpdated()
            self.__model_reset_connection = model.modelReset.connect(__onModelUpdated)


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

        '''------------------------------------------Нижняя часть------------------------------------------'''
        splitter_bottom = QtWidgets.QSplitter(orientation=QtCore.Qt.Orientation.Horizontal, parent=self)

        self.consensuses_view = MyTableViewGroupBox(title='КОНСЕНСУС-ПРОГНОЗЫ', model=None, parent=splitter_bottom)
        consensuses_model = ConsensusItemsModel(instrument_uid=self.instrument_uid, parent=self.consensuses_view)
        self.consensuses_view.setModel(consensuses_model)

        self.targets_view = MyTableViewGroupBox(title='ПРОГНОЗЫ', model=None, parent=splitter_bottom)
        targets_model = TargetItemsModel(instrument_uid=self.instrument_uid, parent=self.targets_view)
        self.targets_view.setModel(targets_model)

        @QtCore.pyqtSlot(str)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
        def __onInstrumentChanged(instrument_uid: str):
            consensuses_model.setInstrument(instrument_uid)
            targets_model.setInstrument(instrument_uid)

        self.groupBox_instrument_selection.comboBox_instrument.instrumentChanged.connect(__onInstrumentChanged)

        @QtCore.pyqtSlot()  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
        def __onInstrumentReset():
            consensuses_model.setInstrument(None)
            targets_model.setInstrument(None)

        self.groupBox_instrument_selection.comboBox_instrument.instrumentReset.connect(__onInstrumentReset)

        verticalLayout_main.addWidget(splitter_bottom, 1)
        '''------------------------------------------------------------------------------------------------'''

    @property
    def instrument_uid(self) -> str | None:
        return self.groupBox_instrument_selection.uid
