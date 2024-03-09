from __future__ import annotations
import typing
from datetime import datetime
from enum import Enum, StrEnum
from PyQt6 import QtCore, QtWidgets, QtGui
from grpc import StatusCode
from tinkoff.invest.schemas import GetForecastResponse, TargetItem, Quotation, Recommendation
from tinkoff.invest.services import InstrumentsService
from Classes import TokenClass, Header, MyTreeView, ColumnWithoutHeader, ConsensusFull
from DatabaseWidgets import GroupBox_InstrumentSelection, TokenSelectionBar
from MyDatabase import MainConnection
from MyDateTime import getUtcDateTime
from MyQuotation import MyQuotation
from MyRequests import MyResponse, RequestTryClass, getForecast
from PagesClasses import TitleWithCount, ProgressBar_DataReceiving, TitleLabel
from ReceivingThread import ManagedReceivingThread
from TokenModel import TokenListModel


class TreeItem:
    def __init__(self, row: int, parent_item: TreeItem | None = None, children: list[TreeItem] | None = None):
        self.__row: int = row  # Номер строки элемента.
        self.__parent: TreeItem | None = parent_item  # Родительский элемент.
        self.__children: list[TreeItem] = [] if children is None else children  # Список дочерних элементов.
        self.__hierarchy_level: int = -1 if parent_item is None else (parent_item.getHierarchyLevel() + 1)

    def row(self) -> int:
        """Возвращает номер строки элемента."""
        return self.__row

    def parent(self) -> TreeItem | None:
        """Возвращает родительский элемент."""
        return self.__parent

    def setChildren(self, children: list[TreeItem] | None):
        if children is None:
            self.__children.clear()
        else:
            self.__children = children

    def child(self, row: int) -> TreeItem:
        return self.__children[row]

    @property
    def children_count(self) -> int:
        """Возвращает количество дочерних элементов."""
        return len(self.__children)

    def getHierarchyLevel(self) -> int:
        """Возвращает уровень иерархии элемента."""
        return self.__hierarchy_level


class ForecastsModel(QtCore.QAbstractItemModel):
    """Модель прогнозов."""
    class ColumnItem:
        def __init__(self, header: Header, consensus_column: ColumnWithoutHeader, target_column: ColumnWithoutHeader):
            self.__header: Header = header
            self.__consensus_column: ColumnWithoutHeader = consensus_column
            self.__target_column: ColumnWithoutHeader = target_column

        def consensus_column(self, consensus_full: ConsensusFull, role: int = QtCore.Qt.ItemDataRole.UserRole):
            return self.__consensus_column(role, consensus_full)

        def target_column(self, target_item: TargetItem, role: int = QtCore.Qt.ItemDataRole.UserRole):
            return self.__target_column(role, target_item)

        def header(self, role: int = QtCore.Qt.ItemDataRole.UserRole):
            return self.__header(role=role)

    def __init__(self, instrument_uid: str | None, last_fulls_flag: bool, parent: QtCore.QObject | None = None):
        super().__init__(parent=parent)
        self.__instrument_uid: str | None = instrument_uid
        self.__last_fulls_flag: bool = last_fulls_flag  # Если True, то модель должна отображать только последние прогнозы.
        self.__consensus_fulls: list[ConsensusFull] = []
        self.__root_item: TreeItem = TreeItem(row=0, parent_item=None, children=None)

        POSITIVE_COLOR: QtGui.QBrush = QtGui.QBrush(QtCore.Qt.GlobalColor.darkGreen)
        NEUTRAL_COLOR: QtGui.QBrush = QtGui.QBrush(QtCore.Qt.GlobalColor.darkYellow)
        NEGATIVE_COLOR: QtGui.QBrush = QtGui.QBrush(QtCore.Qt.GlobalColor.darkRed)

        BUY: str = 'ПОКУПАТЬ'
        HOLD: str = 'ДЕРЖАТЬ'
        SELL: str = 'ПРОДАВАТЬ'

        def __getQuotationColor(quotation: Quotation) -> QtGui.QBrush:
            """Возвращает цвет Quotation."""
            zero_quotation = Quotation(units=0, nano=0)
            if quotation > zero_quotation:
                return POSITIVE_COLOR
            elif quotation < zero_quotation:
                return NEGATIVE_COLOR
            else:
                return NEUTRAL_COLOR

        self.__columns: tuple[ForecastsModel.ColumnItem, ...] = (
            ForecastsModel.ColumnItem(
                header=Header(
                    title='uid',
                    tooltip='Уникальный идентификатор инструмента'
                ),
                consensus_column=ColumnWithoutHeader(
                    data_function=lambda cf: cf.consensus.uid
                ),
                target_column=ColumnWithoutHeader(
                    data_function=lambda ti: ti.uid
                )
            ),
            ForecastsModel.ColumnItem(
                header=Header(
                    title='Тикер',
                    tooltip='Тикер инструмента'
                ),
                consensus_column=ColumnWithoutHeader(
                    data_function=lambda cf: cf.consensus.ticker
                ),
                target_column=ColumnWithoutHeader(
                    data_function=lambda ti: ti.ticker
                )
            ),
            ForecastsModel.ColumnItem(
                header=Header(
                    title='Прогноз',
                    tooltip='Прогноз'
                ),
                consensus_column=ColumnWithoutHeader(
                    data_function=lambda cf: cf.consensus.recommendation,
                    display_function=lambda cf: BUY if cf.consensus.recommendation == Recommendation.RECOMMENDATION_BUY else SELL if cf.consensus.recommendation == Recommendation.RECOMMENDATION_SELL else HOLD if cf.consensus.recommendation == Recommendation.RECOMMENDATION_HOLD else cf.consensus.recommendation.name,
                    foreground_function=lambda cf: POSITIVE_COLOR if cf.consensus.recommendation == Recommendation.RECOMMENDATION_BUY else NEGATIVE_COLOR if cf.consensus.recommendation == Recommendation.RECOMMENDATION_SELL else NEUTRAL_COLOR if cf.consensus.recommendation == Recommendation.RECOMMENDATION_HOLD else QtCore.QVariant()
                ),
                target_column=ColumnWithoutHeader(
                    data_function=lambda ti: ti.recommendation,
                    display_function=lambda ti: BUY if ti.recommendation == Recommendation.RECOMMENDATION_BUY else SELL if ti.recommendation == Recommendation.RECOMMENDATION_SELL else HOLD if ti.recommendation == Recommendation.RECOMMENDATION_HOLD else ti.recommendation.name,
                    foreground_function=lambda ti: POSITIVE_COLOR if ti.recommendation == Recommendation.RECOMMENDATION_BUY else NEGATIVE_COLOR if ti.recommendation == Recommendation.RECOMMENDATION_SELL else NEUTRAL_COLOR if ti.recommendation == Recommendation.RECOMMENDATION_HOLD else QtCore.QVariant()
                )
            ),
            ForecastsModel.ColumnItem(
                header=Header(
                    title='Дата прогноза',
                    tooltip='Дата прогноза'
                ),
                consensus_column=ColumnWithoutHeader(
                    data_function=lambda cf: cf.number,
                    display_function=lambda cf: str(cf.number)
                ),
                target_column=ColumnWithoutHeader(
                    data_function=lambda ti: ti.recommendation_date,
                    display_function=lambda ti: str(ti.recommendation_date)
                )
            ),
            ForecastsModel.ColumnItem(
                header=Header(
                    title='Компания',
                    tooltip='Название компании, давшей прогноз'
                ),
                consensus_column=ColumnWithoutHeader(),
                target_column=ColumnWithoutHeader(
                    data_function=lambda ti: ti.company
                )
            ),
            ForecastsModel.ColumnItem(
                header=Header(
                    title='Текущая цена',
                    tooltip='Текущая цена'
                ),
                consensus_column=ColumnWithoutHeader(
                    data_function=lambda cf: cf.consensus.current_price,
                    display_function=lambda cf: '{0} {1}'.format(MyQuotation.__str__(cf.consensus.current_price, ndigits=8, delete_decimal_zeros=True), cf.consensus.currency)
                ),
                target_column=ColumnWithoutHeader(
                    data_function=lambda ti: ti.current_price,
                    display_function=lambda ti: '{0} {1}'.format(MyQuotation.__str__(ti.current_price, ndigits=8, delete_decimal_zeros=True), ti.currency)
                )
            ),
            ForecastsModel.ColumnItem(
                header=Header(
                    title='Прогноз. цена',
                    tooltip='Прогнозируемая цена'
                ),
                consensus_column=ColumnWithoutHeader(
                    data_function=lambda cf: cf.consensus.consensus,
                    display_function=lambda cf: '{0} {1}'.format(MyQuotation.__str__(cf.consensus.consensus, ndigits=8, delete_decimal_zeros=True), cf.consensus.currency),
                    foreground_function=lambda cf: POSITIVE_COLOR if cf.consensus.consensus > cf.consensus.current_price else NEGATIVE_COLOR if cf.consensus.consensus < cf.consensus.current_price else NEUTRAL_COLOR
                ),
                target_column=ColumnWithoutHeader(
                    data_function=lambda ti: ti.target_price,
                    display_function=lambda ti: '{0} {1}'.format(MyQuotation.__str__(ti.target_price, ndigits=8, delete_decimal_zeros=True), ti.currency),
                    foreground_function=lambda ti: POSITIVE_COLOR if ti.target_price > ti.current_price else NEGATIVE_COLOR if ti.target_price < ti.current_price else NEUTRAL_COLOR
                )
            ),
            ForecastsModel.ColumnItem(
                header=Header(
                    title='Мин. цена',
                    tooltip='Минимальная цена прогноза'
                ),
                consensus_column=ColumnWithoutHeader(
                    data_function=lambda cf: '{0} {1}'.format(MyQuotation.__str__(cf.consensus.min_target, ndigits=8, delete_decimal_zeros=True), cf.consensus.currency),
                    foreground_function=lambda cf: POSITIVE_COLOR if cf.consensus.min_target > cf.consensus.current_price else NEGATIVE_COLOR if cf.consensus.min_target < cf.consensus.current_price else NEUTRAL_COLOR
                ),
                target_column=ColumnWithoutHeader()
            ),
            ForecastsModel.ColumnItem(
                header=Header(
                    title='Макс. цена',
                    tooltip='Максимальная цена прогноза'
                ),
                consensus_column=ColumnWithoutHeader(
                    data_function=lambda cf: '{0} {1}'.format(MyQuotation.__str__(cf.consensus.max_target, ndigits=8, delete_decimal_zeros=True), cf.consensus.currency),
                    foreground_function=lambda cf: POSITIVE_COLOR if cf.consensus.max_target > cf.consensus.current_price else NEGATIVE_COLOR if cf.consensus.max_target < cf.consensus.current_price else NEUTRAL_COLOR
                ),
                target_column=ColumnWithoutHeader()
            ),
            ForecastsModel.ColumnItem(
                header=Header(
                    title='Относ. изменение',
                    tooltip='Относительное изменение цены'
                ),
                consensus_column=ColumnWithoutHeader(
                    data_function=lambda cf: cf.consensus.price_change_rel,
                    display_function=lambda cf: '{0}{1}%'.format('+' if cf.consensus.price_change_rel > Quotation(units=0, nano=0) else '', MyQuotation.__str__(cf.consensus.price_change_rel, ndigits=8, delete_decimal_zeros=True)),
                    foreground_function=lambda cf: __getQuotationColor(cf.consensus.price_change_rel)
                ),
                target_column=ColumnWithoutHeader(
                    data_function=lambda ti: ti.price_change_rel,
                    display_function=lambda ti: '{0}{1}%'.format('+' if ti.price_change_rel > Quotation(units=0, nano=0) else '', MyQuotation.__str__(ti.price_change_rel, ndigits=8, delete_decimal_zeros=True)),
                    foreground_function=lambda ti: __getQuotationColor(ti.price_change_rel)
                )
            ),
            ForecastsModel.ColumnItem(
                header=Header(
                    title='Кол-во таргетов',
                    tooltip='Кол-во таргет-прогнозов'
                ),
                consensus_column=ColumnWithoutHeader(
                    data_function=lambda cf: len(cf.targets),
                    display_function=lambda cf: str(len(cf.targets))
                ),
                target_column=ColumnWithoutHeader()
            )
        )
        self.__update()

    def __update(self):
        """Обновляет модель."""
        self.beginResetModel()
        self.__root_item.setChildren(None)
        if self.__instrument_uid is None:
            self.__consensus_fulls.clear()
        else:
            if self.__last_fulls_flag:
                self.__consensus_fulls = MainConnection.getLastConsensusFulls(instrument_uid=self.__instrument_uid)
            else:
                self.__consensus_fulls = MainConnection.getConsensusFulls(instrument_uid=self.__instrument_uid)

            items: list[TreeItem] = []
            for i, consensus_full in enumerate(self.__consensus_fulls):
                parent_item: TreeItem = TreeItem(row=i, parent_item=None, children=None)
                parent_item.setChildren([TreeItem(row=j, parent_item=parent_item, children=None) for j, target in enumerate(consensus_full.targets)])
                items.append(parent_item)
            self.__root_item.setChildren(items)

        self.endResetModel()

    def rowCount(self, parent: QtCore.QModelIndex = ...) -> int:
        if parent.column() > 0:
            return 0  # Общее соглашение, используемое в моделях, предоставляющих древовидные структуры данных, заключается в том, что только элементы в первом столбце имеют дочерние элементы.
        if parent.isValid():  # Если индекс parent действителен.
            # return len(self.__consensus_fulls[parent.row()].targets)
            tree_item: TreeItem = parent.internalPointer()  # Указатель на внутреннюю структуру данных.
            return tree_item.children_count
        else:
            # return len(self.__consensus_fulls)
            tree_item: TreeItem = self.__root_item
            return tree_item.children_count

    def columnCount(self, parent: QtCore.QModelIndex = ...) -> int:
        return len(self.__columns)

    def index(self, row: int, column: int, parent: QtCore.QModelIndex = ...) -> QtCore.QModelIndex:
        if parent.isValid():  # Если индекс parent действителен.
            parent_item: TreeItem = parent.internalPointer()  # Указатель на внутреннюю структуру данных.
            child_item: TreeItem = parent_item.child(row)
            return self.createIndex(row, column, child_item)
        else:
            return self.createIndex(row, column, self.__root_item.child(row))

    def parent(self, child: QtCore.QModelIndex) -> QtCore.QModelIndex:
        # assert not child.isValid(), 'А может ли запрашиваться parent недействительного элемента?'
        if child.isValid():  # Если индекс child действителен.
            child_item: TreeItem = child.internalPointer()  # Указатель на внутреннюю структуру данных.
            parent_item: TreeItem | None = child_item.parent()
            if parent_item is None:
                return QtCore.QModelIndex()
            elif parent_item == self.__root_item:
                return QtCore.QModelIndex()
            else:
                return self.index(row=parent_item.row(), column=0, parent=QtCore.QModelIndex())
        else:
            return QtCore.QModelIndex()

    def data(self, index: QtCore.QModelIndex, role: int = ...) -> typing.Any:
        column: ForecastsModel.ColumnItem = self.__columns[index.column()]
        if index.parent().isValid():
            parent_tree_item: TreeItem = index.parent().internalPointer()  # Указатель на внутреннюю структуру данных.
            target_item: TargetItem = self.__consensus_fulls[parent_tree_item.row()].targets[index.row()]
            return column.target_column(target_item=target_item, role=role)
        else:
            consensus_full: ConsensusFull = self.__consensus_fulls[index.row()]
            return column.consensus_column(consensus_full=consensus_full, role=role)

    def headerData(self, section: int, orientation: QtCore.Qt.Orientation, role: int = ...) -> typing.Any:
        if orientation == QtCore.Qt.Orientation.Horizontal:
            column: ForecastsModel.ColumnItem = self.__columns[section]
            return column.header(role=role)

    def setOnlyLastFlag(self, flag: bool):
        if self.__last_fulls_flag != flag:
            self.__last_fulls_flag = flag
            self.__update()

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


class ForecastsThread(ManagedReceivingThread):
    """Поток получения прогнозов."""
    forecastsReceived: QtCore.pyqtSignal = QtCore.pyqtSignal(GetForecastResponse)

    '''-----------------Сигналы progressBar'а-----------------'''
    setProgressBarRange_signal: QtCore.pyqtSignal = QtCore.pyqtSignal(int, int)  # Сигнал для установления минимума и максимума progressBar'а заполнения купонов.
    setProgressBarValue_signal: QtCore.pyqtSignal = QtCore.pyqtSignal(int)  # Сигнал для изменения прогресса в progressBar'е.
    '''-------------------------------------------------------'''

    def __init__(self, token: TokenClass, uids: list[str], parent: QtCore.QObject | None = None):
        # super().__init__(token=token, receive_method=InstrumentsService.get_forecast_by.__name__, parent=parent)
        super().__init__(token=token, receive_method='GetForecastBy', parent=parent)
        self.__instruments_uids: list[str] = uids

        '''------------Статистические переменные------------'''
        self.request_count: int = 0  # Общее количество запросов.
        self.control_point: datetime | None = None  # Начальная точка отсчёта времени.
        '''-------------------------------------------------'''

    def receivingFunction(self):
        instruments_count: int = len(self.__instruments_uids)  # Количество инструментов.
        self.setProgressBarRange_signal.emit(0, instruments_count)  # Задаёт минимум и максимум progressBar'а.

        def __ifFirstIteration() -> bool:
            """Возвращает True, если поток не сделал ни одного запроса. Иначе возвращает False."""
            return self.request_count > 0

        for i, uid in enumerate(self.__instruments_uids):
            instrument_number: int = i + 1  # Номер текущего инструмента.
            self.setProgressBarValue_signal.emit(instrument_number)  # Отображаем прогресс в progressBar.

            try_count: RequestTryClass = RequestTryClass(max_request_try_count=1)
            response: MyResponse = MyResponse()
            while try_count and not response.ifDataSuccessfullyReceived():
                if self.isInterruptionRequested():
                    break

                self.checkPause()

                """==============================Выполнение запроса=============================="""
                self.semaphore.acquire(1)  # Блокирует вызов до тех пор, пока не будет доступно достаточно ресурсов.

                '''----------------Подсчёт статистических параметров----------------'''
                if __ifFirstIteration():  # Не выполняется до второго запроса.
                    delta: float = (getUtcDateTime() - self.control_point).total_seconds()  # Секунд прошло с последнего запроса.
                    self.printInConsole('{0} из {1} ({2:.2f}с)'.format(instrument_number, instruments_count, delta))
                else:
                    self.printInConsole('{0} из {1}'.format(instrument_number, instruments_count))
                self.control_point = getUtcDateTime()  # Промежуточная точка отсчёта времени.
                '''-----------------------------------------------------------------'''

                response = getForecast(token=self.token.token, uid=uid)
                assert response.request_occurred, 'Запрос прогнозов не был произведён.'
                self.request_count += 1  # Подсчитываем запрос.

                self.releaseSemaphore_signal.emit(self.semaphore, 1)  # Освобождаем ресурсы семафора из основного потока.

                '''-----------------------Сообщаем об ошибке-----------------------'''
                if response.request_error_flag:
                    if not response.request_error.code == StatusCode.NOT_FOUND:
                        self.printInConsole('RequestError {0}'.format(response.request_error))
                elif response.exception_flag:
                    self.printInConsole('Exception {0}'.format(response.exception))
                '''----------------------------------------------------------------'''
                """=============================================================================="""
                try_count += 1

            forecasts: GetForecastResponse | None = response.response_data if response.ifDataSuccessfullyReceived() else None
            if forecasts is None:
                if self.isInterruptionRequested():
                    self.printInConsole('Поток прерван.')
                    break
                continue  # Если поток был прерван или если информация не была получена.
            self.forecastsReceived.emit(forecasts)


class ProgressThreadManagerBar(QtWidgets.QHBoxLayout):
    """Строка progressBar'а с кнопками управления потоком."""

    class PlayButtonNames(StrEnum):
        PLAY = 'Пуск'
        PAUSE = 'Пауза'

    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self.setContentsMargins(0, 0, 0, 0)
        self.setSpacing(4)

        self.play_button = QtWidgets.QPushButton(text=self.PlayButtonNames.PLAY, parent=parent)
        self.play_button.setEnabled(False)
        self.addWidget(self.play_button, 0)

        self.stop_button = QtWidgets.QPushButton(text='Стоп', parent=parent)
        self.stop_button.setEnabled(False)
        self.addWidget(self.stop_button, 0)

        self.__progressBar = ProgressBar_DataReceiving(parent=parent)
        self.addWidget(self.__progressBar, 1)

    def setPlayButtonName(self, name: ProgressThreadManagerBar.PlayButtonNames):
        self.play_button.setText(name)

    def setRange(self, minimum: int, maximum: int):
        """Устанавливает минимум и максимум для progressBar'а."""
        self.__progressBar.setRange(minimum, maximum)

    def setValue(self, value: int) -> None:
        self.__progressBar.setValue(value)

    def reset(self):
        """Сбрасывает progressBar."""
        self.__progressBar.reset()


class ForecastsReceivingGroupBox(QtWidgets.QGroupBox):
    """Панель получения прогнозов."""
    class Status(Enum):
        """Статус потока."""
        START_NOT_POSSIBLE = 0  # Поток не запущен. Запуск потока невозможен.
        START_POSSIBLE = 1  # Поток не запущен. Возможен запуск потока.
        RUNNING = 2  # Поток запущен.
        PAUSE = 3  # Поток приостановлен.
        FINISHED = 4  # Поток завершился.

    def __init__(self, tokens_model: TokenListModel, parent: QtWidgets.QWidget | None = None):
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

        self.__instruments_uids: list[str] = []
        self.__forecasts_receiving_thread: ForecastsThread | None = None
        self.__current_status: ForecastsReceivingGroupBox.Status = self.Status.START_NOT_POSSIBLE

        '''------------------Дескрипторы соединений с кнопками управления потоком------------------'''
        self.thread_start_connection: QtCore.QMetaObject.Connection = QtCore.QMetaObject.Connection()
        self.thread_pause_connection: QtCore.QMetaObject.Connection = QtCore.QMetaObject.Connection()
        self.thread_resume_connection: QtCore.QMetaObject.Connection = QtCore.QMetaObject.Connection()
        self.thread_stop_connection: QtCore.QMetaObject.Connection = QtCore.QMetaObject.Connection()

        self.thread_finished_connection: QtCore.QMetaObject.Connection = QtCore.QMetaObject.Connection()
        '''----------------------------------------------------------------------------------------'''

        @QtCore.pyqtSlot(TokenClass)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
        def __onTokenSelected(token: TokenClass):
            self.token = token

        @QtCore.pyqtSlot()  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
        def __onTokenReset():
            self.token = None

        self.token_bar.tokenSelected.connect(__onTokenSelected)
        self.token_bar.tokenReset.connect(__onTokenReset)

    @property
    def uids(self) -> list[str]:
        return self.__instruments_uids

    def __onParameterChanged(self, token: TokenClass | None, uids: list[str]):
        self.current_status = self.Status.START_NOT_POSSIBLE if token is None or not uids else self.Status.START_POSSIBLE

    @property
    def token(self) -> TokenClass | None:
        return self.token_bar.token

    @token.setter
    def token(self, token: TokenClass | None):
        self.__onParameterChanged(token=token, uids=self.uids)

    @property
    def current_status(self) -> ForecastsReceivingGroupBox.Status:
        return self.__current_status

    '''--------------------------------Слоты контролирования потока--------------------------------'''
    @QtCore.pyqtSlot()  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
    def __startThread(self):
        """Запускает или возобновляет работу потока получения исторических свечей."""
        self.current_status = self.Status.RUNNING

    @QtCore.pyqtSlot()  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
    def __pauseThread(self):
        """Приостанавливает поток получения исторических свечей."""
        self.current_status = self.Status.PAUSE

    @QtCore.pyqtSlot()  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
    def __stopThread(self):
        """Останавливает поток получения исторических свечей."""
        self.current_status = self.Status.START_POSSIBLE

    @QtCore.pyqtSlot()  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
    def __onFinishedThread(self):
        """Выполняется после завершения потока."""
        self.current_status = self.Status.FINISHED
    '''--------------------------------------------------------------------------------------------'''

    @current_status.setter
    def current_status(self, status: ForecastsReceivingGroupBox.Status):
        print('Статус: {0} -> {1}.'.format(self.current_status.name, status.name))

        def stopThread():
            self.__forecasts_receiving_thread.requestInterruption()  # Сообщаем потоку о том, что надо завершиться.
            self.__forecasts_receiving_thread.wait()  # Ждём завершения потока.
            self.__forecasts_receiving_thread = None

        match self.current_status:
            case self.Status.START_NOT_POSSIBLE:
                match status:
                    case self.Status.START_NOT_POSSIBLE:
                        return
                    case self.Status.START_POSSIBLE:
                        self.thread_start_connection = self.progressBar.play_button.clicked.connect(self.__startThread)
                        self.progressBar.play_button.setEnabled(True)
                    case self.Status.RUNNING:
                        raise SystemError('Поток не может перейти из состояния {0} в состояние {1}!'.format(self.current_status.name, status.name))
                    case self.Status.PAUSE:
                        raise SystemError('Поток не может перейти из состояния {0} в состояние {1}!'.format(self.current_status.name, status.name))
                    case self.Status.FINISHED:
                        raise SystemError('Поток не может перейти из состояния {0} в состояние {1}!'.format(self.current_status.name, status.name))
                    case _:
                        raise ValueError('Неверный статус потока!')
            case self.Status.START_POSSIBLE:
                match status:
                    case self.Status.START_NOT_POSSIBLE:
                        self.progressBar.play_button.setEnabled(False)
                        if not self.progressBar.play_button.disconnect(self.thread_start_connection):
                            raise SystemError('Не удалось отключить слот!')
                    case self.Status.START_POSSIBLE:
                        return
                    case self.Status.RUNNING:
                        self.progressBar.play_button.setEnabled(False)
                        self.progressBar.setPlayButtonName(name=ProgressThreadManagerBar.PlayButtonNames.PAUSE)

                        if not self.progressBar.play_button.disconnect(self.thread_start_connection):
                            raise SystemError('Не удалось отключить слот!')

                        '''------------------------------------Запуск потока------------------------------------'''
                        assert self.__forecasts_receiving_thread is None
                        self.__forecasts_receiving_thread = ForecastsThread(token=self.token, uids=self.uids, parent=self)

                        @QtCore.pyqtSlot(int, int)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
                        def __setRange(minimum: int, maximum: int):
                            if self.__forecasts_receiving_thread is not None:
                                self.progressBar.setRange(minimum, maximum)

                        self.__forecasts_receiving_thread.setProgressBarRange_signal.connect(__setRange)

                        @QtCore.pyqtSlot(int)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
                        def __setValue(value: int):
                            if self.__forecasts_receiving_thread is not None:
                                self.progressBar.setValue(value)

                        self.__forecasts_receiving_thread.setProgressBarValue_signal.connect(__setValue)

                        self.__forecasts_receiving_thread.forecastsReceived.connect(MainConnection.insertForecasts)
                        self.thread_finished_connection = self.__forecasts_receiving_thread.finished.connect(self.__onFinishedThread)

                        self.__forecasts_receiving_thread.start()  # Запускаем поток.
                        '''-------------------------------------------------------------------------------------'''

                        self.thread_pause_connection = self.progressBar.play_button.clicked.connect(self.__pauseThread)
                        self.thread_stop_connection = self.progressBar.stop_button.clicked.connect(self.__stopThread)

                        self.progressBar.stop_button.setEnabled(True)
                        self.progressBar.play_button.setEnabled(True)
                    case self.Status.PAUSE:
                        raise SystemError('Поток не может перейти из состояния {0} в состояние {1}!'.format(self.current_status.name, status.name))
                    case self.Status.FINISHED:
                        raise SystemError('Поток не может перейти из состояния {0} в состояние {1}!'.format(self.current_status.name, status.name))
                    case _:
                        raise ValueError('Неверный статус потока!')
            case self.Status.RUNNING:
                match status:
                    case self.Status.START_NOT_POSSIBLE:
                        self.progressBar.play_button.setEnabled(False)
                        self.progressBar.stop_button.setEnabled(False)

                        '''-------------------------Останавливаем поток-------------------------'''
                        assert self.__forecasts_receiving_thread is not None
                        if not self.__forecasts_receiving_thread.disconnect(self.thread_finished_connection):
                            raise SystemError('Не удалось отключить слот!')
                        stopThread()
                        '''---------------------------------------------------------------------'''

                        if not self.progressBar.play_button.disconnect(self.thread_pause_connection):
                            raise SystemError('Не удалось отключить слот!')

                        if not self.progressBar.stop_button.disconnect(self.thread_stop_connection):
                            raise SystemError('Не удалось отключить слот!')

                        self.progressBar.reset()  # Сбрасываем progressBar.
                        self.progressBar.setPlayButtonName(name=ProgressThreadManagerBar.PlayButtonNames.PLAY)
                    case self.Status.START_POSSIBLE:
                        self.progressBar.play_button.setEnabled(False)
                        self.progressBar.stop_button.setEnabled(False)

                        '''-------------------------Останавливаем поток-------------------------'''
                        assert self.__forecasts_receiving_thread is not None
                        if not self.__forecasts_receiving_thread.disconnect(self.thread_finished_connection):
                            raise SystemError('Не удалось отключить слот!')
                        stopThread()
                        '''---------------------------------------------------------------------'''

                        self.progressBar.setPlayButtonName(name=ProgressThreadManagerBar.PlayButtonNames.PLAY)
                        self.progressBar.reset()  # Сбрасываем progressBar.

                        if not self.progressBar.play_button.disconnect(self.thread_pause_connection):
                            raise SystemError('Не удалось отключить слот!')

                        if not self.progressBar.stop_button.disconnect(self.thread_stop_connection):
                            raise SystemError('Не удалось отключить слот!')

                        self.thread_start_connection = self.progressBar.play_button.clicked.connect(self.__startThread)
                        self.progressBar.play_button.setEnabled(True)
                    case self.Status.RUNNING:
                        return
                    case self.Status.PAUSE:
                        self.progressBar.play_button.setEnabled(False)
                        self.progressBar.stop_button.setEnabled(False)

                        self.__forecasts_receiving_thread.pause()

                        self.progressBar.setPlayButtonName(name=ProgressThreadManagerBar.PlayButtonNames.PLAY)

                        if not self.progressBar.play_button.disconnect(self.thread_pause_connection):
                            raise SystemError('Не удалось отключить слот!')

                        self.thread_resume_connection = self.progressBar.play_button.clicked.connect(self.__startThread)

                        self.progressBar.play_button.setEnabled(True)
                        self.progressBar.stop_button.setEnabled(True)
                    case self.Status.FINISHED:
                        self.progressBar.play_button.setEnabled(False)
                        self.progressBar.stop_button.setEnabled(False)
                        self.progressBar.setPlayButtonName(name=ProgressThreadManagerBar.PlayButtonNames.PLAY)

                        if not self.__forecasts_receiving_thread.isFinished():
                            raise SystemError('Поток должен был быть завершён!')
                        if not self.__forecasts_receiving_thread.disconnect(self.thread_finished_connection):
                            raise SystemError('Не удалось отключить слот!')
                        self.__forecasts_receiving_thread = None

                        if not self.progressBar.play_button.disconnect(self.thread_pause_connection):
                            raise SystemError('Не удалось отключить слот!')

                        if not self.progressBar.stop_button.disconnect(self.thread_stop_connection):
                            raise SystemError('Не удалось отключить слот!')

                        self.thread_start_connection = self.progressBar.play_button.clicked.connect(self.__startThread)
                        self.progressBar.play_button.setEnabled(True)
                    case _:
                        raise ValueError('Неверный статус потока!')
            case self.Status.PAUSE:
                match status:
                    case self.Status.START_NOT_POSSIBLE:
                        self.progressBar.play_button.setEnabled(False)
                        self.progressBar.stop_button.setEnabled(False)
                        self.progressBar.setPlayButtonName(name=ProgressThreadManagerBar.PlayButtonNames.PLAY)

                        '''-------------------------Останавливаем поток-------------------------'''
                        assert self.__forecasts_receiving_thread is not None
                        if not self.__forecasts_receiving_thread.disconnect(self.thread_finished_connection):
                            raise SystemError('Не удалось отключить слот!')
                        self.__forecasts_receiving_thread.resume()  # Возобновляем работу потока, чтобы он мог безопасно завершиться.
                        stopThread()
                        '''---------------------------------------------------------------------'''

                        self.progressBar.reset()  # Сбрасываем progressBar.

                        if not self.progressBar.play_button.disconnect(self.thread_resume_connection):
                            raise SystemError('Не удалось отключить слот!')
                    case self.Status.START_POSSIBLE:
                        self.progressBar.play_button.setEnabled(False)
                        self.progressBar.stop_button.setEnabled(False)

                        '''-------------------------Останавливаем поток-------------------------'''
                        assert self.__forecasts_receiving_thread is not None
                        if not self.__forecasts_receiving_thread.disconnect(self.thread_finished_connection):
                            raise SystemError('Не удалось отключить слот!')
                        self.__forecasts_receiving_thread.resume()  # Возобновляем работу потока, чтобы он мог безопасно завершиться.
                        stopThread()
                        '''---------------------------------------------------------------------'''

                        self.progressBar.reset()  # Сбрасываем progressBar.
                        self.progressBar.setPlayButtonName(name=ProgressThreadManagerBar.PlayButtonNames.PLAY)

                        if not self.progressBar.play_button.disconnect(self.thread_resume_connection):
                            raise SystemError('Не удалось отключить слот!')

                        self.thread_start_connection = self.progressBar.play_button.clicked.connect(self.__startThread)
                        self.progressBar.play_button.setEnabled(True)
                    case self.Status.RUNNING:
                        self.progressBar.play_button.setEnabled(False)
                        self.progressBar.stop_button.setEnabled(False)

                        self.__forecasts_receiving_thread.resume()

                        self.progressBar.setPlayButtonName(name=ProgressThreadManagerBar.PlayButtonNames.PAUSE)

                        if not self.progressBar.play_button.disconnect(self.thread_resume_connection):
                            raise SystemError('Не удалось отключить слот!')

                        self.thread_pause_connection = self.progressBar.play_button.clicked.connect(self.__pauseThread)

                        self.progressBar.stop_button.setEnabled(True)
                        self.progressBar.play_button.setEnabled(True)
                    case self.Status.PAUSE:
                        return
                    case self.Status.FINISHED:
                        # self.progressBar.play_button.setEnabled(False)
                        # self.progressBar.stop_button.setEnabled(False)
                        # self.progressBar.setPlayButtonName(name=ProgressThreadManagerBar.PlayButtonNames.PLAY)
                        #
                        # if not self.__forecasts_receiving_thread.isFinished():
                        #     raise SystemError('Поток должен был быть завершён!')
                        # if not self.__forecasts_receiving_thread.disconnect(self.thread_finished_connection):
                        #     raise SystemError('Не удалось отключить слот!')
                        # self.__forecasts_receiving_thread = None
                        #
                        # if not self.progressBar.play_button.disconnect(self.thread_start_connection):
                        #     raise SystemError('Не удалось отключить слот!')
                        #
                        # if not self.progressBar.stop_button.disconnect(self.thread_stop_connection):
                        #     raise SystemError('Не удалось отключить слот!')
                        #
                        # self.thread_start_connection = self.progressBar.play_button.clicked.connect(self.__startThread)
                        # self.progressBar.play_button.setEnabled(True)

                        raise SystemError('Поток не может перейти из состояния {0} в состояние {1}!'.format(self.current_status.name, status.name))
                    case _:
                        raise ValueError('Неверный статус потока!')
            case self.Status.FINISHED:
                match status:
                    case self.Status.START_NOT_POSSIBLE:
                        self.progressBar.play_button.setEnabled(False)

                        assert self.__forecasts_receiving_thread is None
                        self.progressBar.reset()  # Сбрасываем progressBar.

                        if not self.progressBar.play_button.disconnect(self.thread_start_connection):
                            raise SystemError('Не удалось отключить слот!')
                    case self.Status.START_POSSIBLE:
                        self.progressBar.play_button.setEnabled(False)

                        assert self.__forecasts_receiving_thread is None
                        self.progressBar.reset()  # Сбрасываем progressBar.

                        if not self.progressBar.play_button.disconnect(self.thread_start_connection):
                            raise SystemError('Не удалось отключить слот!')

                        self.thread_start_connection = self.progressBar.play_button.clicked.connect(self.__startThread)
                        self.progressBar.play_button.setEnabled(True)
                    case self.Status.RUNNING:
                        self.progressBar.play_button.setEnabled(False)
                        self.progressBar.setPlayButtonName(name=ProgressThreadManagerBar.PlayButtonNames.PAUSE)

                        if not self.progressBar.play_button.disconnect(self.thread_start_connection):
                            raise SystemError('Не удалось отключить слот!')

                        '''------------------------------------Запуск потока------------------------------------'''
                        assert self.__forecasts_receiving_thread is None
                        self.__forecasts_receiving_thread = ForecastsThread(token=self.token, uids=self.uids, parent=self)

                        @QtCore.pyqtSlot(int, int)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
                        def __setRange(minimum: int, maximum: int):
                            if self.__forecasts_receiving_thread is not None:
                                self.progressBar.setRange(minimum, maximum)

                        self.__forecasts_receiving_thread.setProgressBarRange_signal.connect(__setRange)

                        @QtCore.pyqtSlot(int)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
                        def __setValue(value: int):
                            if self.__forecasts_receiving_thread is not None:
                                self.progressBar.setValue(value)

                        self.__forecasts_receiving_thread.setProgressBarValue_signal.connect(__setValue)

                        self.__forecasts_receiving_thread.forecastsReceived.connect(MainConnection.insertForecasts)
                        self.thread_finished_connection = self.__forecasts_receiving_thread.finished.connect(self.__onFinishedThread)

                        self.__forecasts_receiving_thread.start()  # Запускаем поток.
                        '''-------------------------------------------------------------------------------------'''

                        self.thread_pause_connection = self.progressBar.play_button.clicked.connect(self.__pauseThread)
                        self.thread_stop_connection = self.progressBar.stop_button.clicked.connect(self.__stopThread)

                        self.progressBar.stop_button.setEnabled(True)
                        self.progressBar.play_button.setEnabled(True)
                    case self.Status.PAUSE:
                        raise SystemError('Поток не может перейти из состояния {0} в состояние {1}!'.format(self.current_status.name, status.name))
                    case self.Status.FINISHED:
                        return
                    case _:
                        raise ValueError('Неверный статус потока!')
            case _:
                raise ValueError('Неверный статус потока!')

        self.__current_status = status

    def setInstruments(self, instruments_uids: list[str]):
        self.__instruments_uids = instruments_uids
        self.__onParameterChanged(token=self.token, uids=self.uids)
        self.titlebar.setCount(str(len(self.uids)))


class ForecastsTitle(QtWidgets.QHBoxLayout):
    stateChanged: QtCore.pyqtSignal = QtCore.pyqtSignal(bool)

    def __init__(self, title: str, count_text: str = '0', parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self.setSpacing(0)

        self.addSpacing(10)

        def __stateChanged(state: int):
            match state:
                case 2:  # QtCore.Qt.CheckState.Checked
                    return self.stateChanged.emit(True)
                case 0:  # QtCore.Qt.CheckState.Unchecked
                    return self.stateChanged.emit(False)
                case _:
                    raise ValueError('Неизвестное значение checkBox\'а!')

        self.__checkBox = QtWidgets.QCheckBox(text='Только последние', parent=parent)
        self.__checkBox.stateChanged.connect(__stateChanged)
        self.addWidget(self.__checkBox, 1)

        self.addWidget(TitleLabel(text=title, parent=parent), 0)

        self.__label_count = QtWidgets.QLabel(text=count_text, parent=parent)
        self.__label_count.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.addWidget(self.__label_count, 1)

        self.addSpacing(10)

    def isChecked(self) -> bool:
        return self.__checkBox.isChecked()

    def setCount(self, count_text: str | None):
        self.__label_count.setText(count_text)


class new_ForecastsPage(QtWidgets.QWidget):
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
        self.groupBox_instrument_selection.comboBox_instrument.instrumentsListChanged.connect(self.progressBar.setInstruments)
        verticalLayout_progressBar.addWidget(self.progressBar, 0)
        verticalLayout_progressBar.addStretch(1)
        horizontalLayout_top.addLayout(verticalLayout_progressBar, 1)

        verticalLayout_main.addLayout(horizontalLayout_top, 0)

        '''---------------------------------------Нижняя часть---------------------------------------'''
        layoutWidget = QtWidgets.QGroupBox(parent=self)

        verticalLayout_forecasts_view = QtWidgets.QVBoxLayout(layoutWidget)
        verticalLayout_forecasts_view.setContentsMargins(2, 2, 2, 2)
        verticalLayout_forecasts_view.setSpacing(2)

        __titlebar = ForecastsTitle(title='ПРОГНОЗЫ', count_text='0', parent=layoutWidget)
        verticalLayout_forecasts_view.addLayout(__titlebar, 0)

        self.forecasts_view = MyTreeView(parent=layoutWidget)
        forecasts_model = ForecastsModel(instrument_uid=self.instrument_uid, last_fulls_flag=__titlebar.isChecked(), parent=self.forecasts_view)
        self.forecasts_view.setModel(forecasts_model)  # Подключаем модель к таблице.

        verticalLayout_forecasts_view.addWidget(self.forecasts_view, 1)

        verticalLayout_main.addWidget(layoutWidget, 1)
        '''------------------------------------------------------------------------------------------'''

        def __onModelUpdated():
            """Выполняется при изменении модели."""
            __titlebar.setCount(str(forecasts_model.rowCount(parent=QtCore.QModelIndex())))
            # self.forecasts_view.expandAll()  # Разворачивает все элементы.
            self.forecasts_view.resizeColumnsToContents()  # Авторазмер столбцов под содержимое.

        __onModelUpdated()
        forecasts_model.modelReset.connect(__onModelUpdated)

        __titlebar.stateChanged.connect(forecasts_model.setOnlyLastFlag)

        self.groupBox_instrument_selection.comboBox_instrument.instrumentChanged.connect(forecasts_model.setInstrument)
        self.groupBox_instrument_selection.comboBox_instrument.instrumentReset.connect(forecasts_model.resetInstrument)

        @QtCore.pyqtSlot()  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
        def __onExpanded(index: QtCore.QModelIndex):
            self.forecasts_view.resizeColumnsToContents()  # Авторазмер столбцов под содержимое.

        self.forecasts_view.expanded.connect(__onExpanded)

    @property
    def instrument_uid(self) -> str | None:
        return self.groupBox_instrument_selection.uid
