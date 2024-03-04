from __future__ import annotations
import typing
from datetime import datetime
from PyQt6 import QtCore
from tinkoff.invest import AssetInstrument, AssetType, InstrumentType, Asset, AssetFull
from Classes import Column, TokenClass, print_slot
from LimitClasses import LimitPerMinuteSemaphore
from MyDatabase import MainConnection
from MyDateTime import getMoscowDateTime, getUtcDateTime
from MyRequests import MyResponse, getAssetBy, RequestTryClass


class AssetClass(QtCore.QObject):
    """Класс, содержащий всю доступную информацию об активе."""
    onAssetFullChanged: QtCore.pyqtSignal = QtCore.pyqtSignal()  # Сигнал, испускаемый при изменении информации об активе.

    def __init__(self, asset: Asset, parent: QtCore.QObject | None = None):
        super().__init__(parent=parent)
        self.asset: Asset = asset
        self.full_asset: AssetFull | None = None

    def setAssetFull(self, assetfull: AssetFull):
        """Заполняет информацию об активе."""
        self.full_asset = assetfull
        self.onAssetFullChanged.emit()  # Испускаем сигнал о том, что информация об активе была изменена.


class AssetsThread(QtCore.QThread):
    """Поток получения полной информации об активах."""

    receive_assetfulls_method_name: str = 'GetAssetBy'

    assetFullReceived: QtCore.pyqtSignal = QtCore.pyqtSignal(AssetFull)

    '''------------------------Сигналы------------------------'''
    printText_signal: QtCore.pyqtSignal = QtCore.pyqtSignal(str)  # Сигнал для отображения сообщений в консоли.
    releaseSemaphore_signal: QtCore.pyqtSignal = QtCore.pyqtSignal(LimitPerMinuteSemaphore, int)  # Сигнал для освобождения ресурсов семафора из основного потока.
    '''-------------------------------------------------------'''

    '''-----------------Сигналы progressBar'а-----------------'''
    setProgressBarRange_signal: QtCore.pyqtSignal = QtCore.pyqtSignal(int, int)  # Сигнал для установления минимума и максимума progressBar'а заполнения купонов.
    setProgressBarValue_signal: QtCore.pyqtSignal = QtCore.pyqtSignal(int)  # Сигнал для изменения прогресса в progressBar'е.
    '''-------------------------------------------------------'''

    def __init__(self, token_class: TokenClass, assets: list[AssetClass], parent: QtCore.QObject | None = None):
        super().__init__(parent=parent)
        self.__token: TokenClass = token_class
        self.__assets: list[AssetClass] = assets

        '''------------Статистические переменные------------'''
        self.__request_count: int = 0  # Общее количество запросов.
        self.__control_point: datetime | None = None  # Начальная точка отсчёта времени.
        '''-------------------------------------------------'''

        self.releaseSemaphore_signal.connect(lambda semaphore, n: semaphore.release(n))  # Освобождаем ресурсы семафора из основного потока.
        self.assetFullReceived.connect(MainConnection.insertAssetFull)
        self.printText_signal.connect(print_slot)  # Сигнал для отображения сообщений в консоли.
        self.started.connect(lambda: print('{0}: Поток запущен. ({1})'.format(self.__class__.__name__, getMoscowDateTime())))
        self.finished.connect(lambda: print('{0}: Поток завершён. ({1})'.format(self.__class__.__name__, getMoscowDateTime())))

    def run(self) -> None:
        def printInConsole(text: str):
            self.printText_signal.emit('{0}: {1}'.format(self.__class__.__name__, text))

        def ifFirstIteration() -> bool:
            """Возвращает True, если поток не сделал ни одного запроса. Иначе возвращает False."""
            return self.__request_count > 0

        semaphore: LimitPerMinuteSemaphore | None = self.__token.unary_limits_manager.getSemaphore(self.receive_assetfulls_method_name)
        if semaphore is None:
            printInConsole('Лимит для метода {0} не найден.'.format(self.receive_assetfulls_method_name))
        else:
            assets_count: int = len(self.__assets)  # Количество активов.
            self.setProgressBarRange_signal.emit(0, assets_count)  # Задаёт минимум и максимум progressBar'а.

            for i, asset_class in enumerate(self.__assets):
                if self.isInterruptionRequested():
                    printInConsole('Поток прерван.')
                    break

                asset_number: int = i + 1  # Номер текущего актива.
                self.setProgressBarValue_signal.emit(asset_number)  # Отображаем прогресс в progressBar.

                assetfull_try_count: RequestTryClass = RequestTryClass()
                assetfull_response: MyResponse = MyResponse()
                while assetfull_try_count and not assetfull_response.ifDataSuccessfullyReceived():
                    if self.isInterruptionRequested():
                        printInConsole('Поток прерван.')
                        break

                    """------------------------------Выполнение запроса------------------------------"""
                    semaphore.acquire(1)  # Блокирует вызов до тех пор, пока не будет доступно достаточно ресурсов.

                    '''----------------Подсчёт статистических параметров----------------'''
                    if ifFirstIteration():  # Не выполняется до второго запроса.
                        delta: float = (getUtcDateTime() - self.__control_point).total_seconds()  # Секунд прошло с последнего запроса.
                        printInConsole('{0} из {1} ({2:.2f}с)'.format(asset_number, assets_count, delta))
                    else:
                        printInConsole('{0} из {1}'.format(asset_number, assets_count))
                    self.__control_point = getUtcDateTime()  # Промежуточная точка отсчёта времени.
                    '''-----------------------------------------------------------------'''

                    assetfull_response = getAssetBy(self.__token.token, asset_class.asset.uid)
                    assert assetfull_response.request_occurred, 'Запрос информации об активе не был произведён!'
                    self.__request_count += 1  # Подсчитываем запрос.
                    self.releaseSemaphore_signal.emit(semaphore, 1)  # Освобождаем ресурсы семафора из основного потока.

                    '''------------------------Сообщаем об ошибке------------------------'''
                    if assetfull_response.request_error_flag:
                        printInConsole('RequestError {0}'.format(assetfull_response.request_error))
                    elif assetfull_response.exception_flag:
                        printInConsole('Exception {0}'.format(assetfull_response.exception))
                    '''------------------------------------------------------------------'''
                    """------------------------------------------------------------------------------"""
                    assetfull_try_count += 1

                assetfull: AssetFull | None = assetfull_response.response_data.asset if assetfull_response.ifDataSuccessfullyReceived() else None
                if assetfull is None: continue  # Если поток был прерван или если информация не была получена.
                asset_class.setAssetFull(assetfull)  # Записываем информацию об активе в AssetClass.
                self.assetFullReceived.emit(assetfull)


class AssetColumn(Column):
    """Класс столбца таблицы активов."""
    def __init__(self, header: str | None = None, header_tooltip: str | None = None,
                 data_function=None, display_function=None, tooltip_function=None,
                 background_function=None, foreground_function=None,
                 lessThan=None, sort_role: QtCore.Qt.ItemDataRole = QtCore.Qt.ItemDataRole.UserRole,
                 full_dependence: bool = False):
        super().__init__(header, header_tooltip, data_function, display_function, tooltip_function,
                         background_function, foreground_function, lessThan, sort_role)
        self._full_dependence: bool = full_dependence  # Флаг зависимости от AssetFull.

    def dependsOnFull(self) -> bool:
        """Возвращает True, если значение столбца зависит от AssetFull."""
        return self._full_dependence


class TreeItem:
    def __init__(self, row: int, parent_item: TreeItem | None = None, data: AssetClass | AssetInstrument | None = None, children: list[TreeItem] | None = None):
        self.__parent: TreeItem | None = parent_item  # Родительский элемент.
        self.__data: AssetClass | AssetInstrument | None = data
        self.__children: list[TreeItem] = [] if children is None else children  # Список дочерних элементов.
        self.__row: int = row  # Номер строки элемента.
        self.__hierarchy_level: int = -1 if parent_item is None else (parent_item.getHierarchyLevel() + 1)

    @property
    def data(self) -> AssetClass | AssetInstrument | None:
        return self.__data

    def parent(self) -> TreeItem | None:
        """Возвращает родительский элемент."""
        return self.__parent

    def setChildren(self, children: list[TreeItem] | None):
        if children is None:
            self.__children.clear()
        else:
            self.__children = children

    @property
    def children_count(self) -> int:
        """Возвращает количество дочерних элементов."""
        return len(self.__children)

    def child(self, row: int) -> TreeItem | None:
        return None if row >= self.children_count or row < 0 else self.__children[row]

    def row(self) -> int:
        """Возвращает номер строки элемента."""
        return self.__row

    def getHierarchyLevel(self) -> int:
        """Возвращает уровень иерархии элемента."""
        return self.__hierarchy_level


def reportAssetType(asset_type: AssetType) -> str:
    """Расшифровывает тип актива."""
    match asset_type:
        case AssetType.ASSET_TYPE_UNSPECIFIED: return 'Тип не определён.'
        case AssetType.ASSET_TYPE_CURRENCY: return 'Валюта.'
        case AssetType.ASSET_TYPE_COMMODITY: return 'Товар.'
        case AssetType.ASSET_TYPE_INDEX: return 'Индекс.'
        case AssetType.ASSET_TYPE_SECURITY: return 'Ценная бумага.'
        case _:
            assert False, 'Некорректное значение типа актива: {0}!'.format(asset_type)
            return ''


def reportInstrumentType(instrument_type: InstrumentType) -> str:
    """Расшифровывает тип инструмента."""
    match instrument_type:
        case InstrumentType.INSTRUMENT_TYPE_UNSPECIFIED: return 'Тип инструмента не определён'
        case InstrumentType.INSTRUMENT_TYPE_BOND: return 'Облигация'
        case InstrumentType.INSTRUMENT_TYPE_SHARE: return 'Акция'
        case InstrumentType.INSTRUMENT_TYPE_CURRENCY: return 'Валюта'
        case InstrumentType.INSTRUMENT_TYPE_ETF: return 'Exchange-traded fund'
        case InstrumentType.INSTRUMENT_TYPE_FUTURES: return 'Фьючерс'
        case InstrumentType.INSTRUMENT_TYPE_SP: return 'Структурная нота'
        case InstrumentType.INSTRUMENT_TYPE_OPTION: return 'Опцион'
        case InstrumentType.INSTRUMENT_TYPE_CLEARING_CERTIFICATE: return 'Clearing certificate'
        case _:
            assert False, 'Некорректное значение типа инструмента: {0}!'.format(instrument_type)
            return ''


class AssetsTreeModel(QtCore.QAbstractItemModel):
    """Класс модели активов."""
    '''-----------------Сигналы progressBar'а-----------------'''
    setProgressBarRange_signal: QtCore.pyqtSignal = QtCore.pyqtSignal(int, int)  # Сигнал для установления минимума и максимума progressBar'а заполнения купонов.
    setProgressBarValue_signal: QtCore.pyqtSignal = QtCore.pyqtSignal(int)  # Сигнал для изменения прогресса в progressBar'е.
    '''-------------------------------------------------------'''

    def __init__(self, parent: QtCore.QObject | None = None):
        self.__columns: tuple[tuple[AssetColumn, Column], ...] = (
            (AssetColumn(header='uid',
                         data_function=lambda item: item.data.asset.uid),
             Column(data_function=lambda item: item.data.uid)),
            (AssetColumn(header='Тип актива',
                         data_function=lambda item: item.data.asset.type,
                         display_function=lambda item: reportAssetType(item.data.asset.type)),
             Column(data_function=lambda item: item.data.figi)),
            (AssetColumn(header='Наименование актива',
                         data_function=lambda item: item.data.asset.name),
             Column(data_function=lambda item: item.data.instrument_type)),
            (AssetColumn(header='Тикер'),
             Column(data_function=lambda item: item.data.ticker)),
            (AssetColumn(header='Класс-код'),
             Column(data_function=lambda item: item.data.class_code)),
            (AssetColumn(header='Тип инструмента'),
             Column(data_function=lambda item: item.data.asset.instrument_kind,
                    display_function=lambda item: reportInstrumentType(item.data.instrument_kind))),
            (AssetColumn(header='Наименование бренда',
                         header_tooltip='Наименование бренда.',
                         data_function=lambda item: None if item.data.full_asset is None else item.data.full_asset.brand.name,
                         full_dependence=True),
             Column()),
            (AssetColumn(header='Компания',
                         header_tooltip='Компания.',
                         data_function=lambda item: None if item.data.full_asset is None else item.data.full_asset.brand.company,
                         full_dependence=True),
             Column())
        )
        self.__root_item: TreeItem = TreeItem(0, None, None)
        self.__assets: list[AssetClass] = []
        self.__update_connections: list[QtCore.QMetaObject.Connection] = []

        self.__progressbar_range_connection: QtCore.QMetaObject.Connection = QtCore.QMetaObject.Connection()
        self.__progressbar_value_connection: QtCore.QMetaObject.Connection = QtCore.QMetaObject.Connection()

        self.__full_assets_thread: AssetsThread | None = None  # Поток получения AssetFull'ов.
        super().__init__(parent=parent)

    def __stopThread(self):
        if self.__full_assets_thread is not None:
            self.__full_assets_thread.requestInterruption()
            self.__full_assets_thread.wait()

            range_disconnect_flag: bool = self.__full_assets_thread.disconnect(self.__progressbar_range_connection)
            assert range_disconnect_flag, 'Не удалось отключить слот!'
            value_disconnect_flag: bool = self.__full_assets_thread.disconnect(self.__progressbar_value_connection)
            assert value_disconnect_flag, 'Не удалось отключить слот!'

            self.__full_assets_thread = None

        def __disconnectUpdateConnections():
            print('len: {0}'.format(len(self.__update_connections)))
            num: int = 0
            for asset_instance in self.__assets:
                for (asset_column, instrument_column) in self.__columns:
                    if asset_column.dependsOnFull():
                        disconnect_flag: bool = asset_instance.disconnect(self.__update_connections[num])
                        assert disconnect_flag, 'Не удалось отключить слот!'
                        num += 1
            print('num: {0}'.format(num))
            self.__update_connections.clear()

        __disconnectUpdateConnections()  # Отключение соединений.

    def reset(self):
        self.beginResetModel()  # Начинает операцию сброса модели.
        self.__stopThread()

        self.__assets.clear()
        self.__root_item.setChildren(None)

        self.endResetModel()  # Завершает операцию сброса модели.

    def setAssets(self, token: TokenClass, assets: list[AssetClass]):
        """Устанавливает данные модели."""
        self.beginResetModel()  # Начинает операцию сброса модели.
        self.__stopThread()

        self.__assets = assets

        '''---------------Создание иерархической структуры---------------'''
        assets_items: list[TreeItem] = []
        for i, asset_instance in enumerate(self.__assets):
            asset_item: TreeItem = TreeItem(i, self.__root_item, asset_instance)
            asset_item.setChildren([TreeItem(j, asset_item, instrument) for j, instrument in enumerate(asset_instance.asset.instruments)])
            assets_items.append(asset_item)
        self.__root_item.setChildren(assets_items)
        '''--------------------------------------------------------------'''

        for row, asset_class in enumerate(self.__assets):
            for column, (asset_column, instrument_column) in enumerate(self.__columns):
                if asset_column.dependsOnFull():
                    def __dataChanged(row_: int, column_: int):
                        ind: QtCore.QModelIndex = self.index(row_, column_, QtCore.QModelIndex())
                        self.dataChanged.emit(ind, ind)

                    self.__update_connections.append(asset_class.onAssetFullChanged.connect(lambda row_=row, column_=column: __dataChanged(row_, column_)))  # Подключаем слот обновления.
                    # index: QtCore.QModelIndex = self.index(row, column, QtCore.QModelIndex())
                    # self.__update_connections.append(asset_class.onAssetFullChanged.connect(lambda ind=index: self.dataChanged.emit(ind, ind)))  # Подключаем слот обновления.
                    # asset_class.setAssetFull_signal.connect(update_class(self, index, index))  # Подключаем слот обновления.

        self.__full_assets_thread = AssetsThread(token_class=token, assets=self.__assets, parent=self)
        self.__progressbar_range_connection = self.__full_assets_thread.setProgressBarRange_signal.connect(self.setProgressBarRange_signal.emit)
        self.__progressbar_value_connection = self.__full_assets_thread.setProgressBarValue_signal.connect(self.setProgressBarValue_signal.emit)

        self.endResetModel()  # Завершает операцию сброса модели.
        self.__full_assets_thread.start()

    def rowCount(self, parent: QtCore.QModelIndex = ...) -> int:
        """Возвращает количество дочерних строк в текущем элементе."""
        if parent.column() > 0: return 0
        if parent.isValid():  # Если индекс parent действителен.
            tree_item: TreeItem = parent.internalPointer()  # Указатель на внутреннюю структуру данных.
            assert type(tree_item) == TreeItem
        else:  # Если parent недействителен, то parent - корневой элемент.
            tree_item: TreeItem = self.__root_item
        return tree_item.children_count

    def columnCount(self, parent: QtCore.QModelIndex = ...) -> int:
        """Возвращает количество дочерних столбцов в текущем элементе."""
        return len(self.__columns)

    def parent(self, child: QtCore.QModelIndex) -> QtCore.QModelIndex:
        """Возвращает родителя элемента."""
        if child.isValid():  # Если индекс child действителен.
            child_item: TreeItem = child.internalPointer()  # Указатель на внутреннюю структуру данных.
            assert type(child_item) == TreeItem
            parent_item: TreeItem | None = child_item.parent()
            if parent_item is None:
                return QtCore.QModelIndex()
            elif parent_item == self.__root_item:
                return QtCore.QModelIndex()
            else:
                return self.createIndex(parent_item.row(), 0, parent_item)
        else:  # Если индекс child недействителен.
            return QtCore.QModelIndex()

    def index(self, row: int, column: int, parent: QtCore.QModelIndex = ...) -> QtCore.QModelIndex:
        """Возвращает индекс элемента в модели."""
        if parent.isValid():  # Если индекс parent действителен.
            parent_item: TreeItem = parent.internalPointer()  # Указатель на внутреннюю структуру данных.
            assert type(parent_item) == TreeItem
        else:
            parent_item: TreeItem = self.__root_item
        tree_item: TreeItem | None = parent_item.child(row)
        return QtCore.QModelIndex() if tree_item is None else self.createIndex(row, column, tree_item)

    def data(self, index: QtCore.QModelIndex, role: int = ...) -> typing.Any:
        """Возвращает данные, на которые ссылается index."""
        tree_item: TreeItem = index.internalPointer()  # Указатель на внутреннюю структуру данных.
        assert type(tree_item) == TreeItem
        hierarchy_level: int = tree_item.getHierarchyLevel()
        if hierarchy_level >= 0:
            current_column: Column = self.__columns[index.column()][hierarchy_level]
            return current_column(role, tree_item)

    def headerData(self, section: int, orientation: QtCore.Qt.Orientation, role: int = ...) -> typing.Any:
        """Возвращает данные заголовка."""
        if orientation == QtCore.Qt.Orientation.Horizontal:
            if role == QtCore.Qt.ItemDataRole.DisplayRole:
                for column in self.__columns[section]:
                    if column.header is not None:
                        return column.header
            elif role == QtCore.Qt.ItemDataRole.ToolTipRole:
                for column in self.__columns[section]:
                    if column.header_tooltip is not None:
                        return column.header_tooltip
