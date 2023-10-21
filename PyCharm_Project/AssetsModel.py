from __future__ import annotations
import enum
import typing
from PyQt6.QtCore import QAbstractItemModel, QModelIndex, Qt
from tinkoff.invest import AssetInstrument, AssetType, InstrumentType
from AssetsThread import AssetClass
from Classes import Column, update_class


class AssetColumn(Column):
    """Класс столбца таблицы активов."""
    def __init__(self, header: str | None = None, header_tooltip: str | None = None,
                 data_function=None, display_function=None, tooltip_function=None,
                 background_function=None, foreground_function=None,
                 lessThan=None, sort_role: Qt.ItemDataRole = Qt.ItemDataRole.UserRole,
                 full_dependence: bool = False):
        super().__init__(header, header_tooltip, data_function, display_function, tooltip_function,
                         background_function, foreground_function, lessThan, sort_role)
        self._full_dependence: bool = full_dependence  # Флаг зависимости от AssetFull.

    def dependsOnFull(self) -> bool:
        """Возвращает True, если значение столбца зависит от AssetFull."""
        return self._full_dependence


class TreeItem:
    def __init__(self, parent: TreeItem | None, data: AssetClass | AssetInstrument | None, children: list[TreeItem], row: int, hierarchy_level: int):
        self._parent: TreeItem | None = parent  # Родительский элемент.
        self.__data: AssetClass | AssetInstrument | None = data
        self._children: list[TreeItem] = children  # Список дочерних элементов.
        self._row: int = row  # Номер строки элемента.
        self._hierarchy_level: int = hierarchy_level

    @property
    def data(self) -> AssetClass | AssetInstrument | None:
        return self.__data

    def parent(self) -> TreeItem | None:
        """Возвращает родительский элемент."""
        return self._parent

    def setChildren(self, children: list[TreeItem]):
        self._children = children

    def childrenCount(self) -> int:
        """Возвращает количество дочерних элементов."""
        return len(self._children)

    def child(self, row: int) -> TreeItem | None:
        if 0 <= row < self.childrenCount():
            return self._children[row]
        else:
            return None

    def getChildren(self) -> list[TreeItem]:
        """Возвращает список дочерних элементов."""
        return self._children

    def row(self) -> int:
        """Возвращает номер строки элемента."""
        return self._row

    def getHierarchyLevel(self) -> int:
        """Возвращает уровень иерархии элемента."""
        return self._hierarchy_level


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


class AssetsTreeModel(QAbstractItemModel):
    """Класс модели активов."""
    @enum.unique  # Декоратор, требующий, чтобы все элементы имели разные значения.
    class Columns(enum.IntEnum):
        """Перечисление столбцов."""
        ASSET_FIRST = 0
        ASSET_SECOND = 1
        ASSET_THIRD = 2
        ASSET_FOURTH = 3
        ASSET_FIFTH = 4
        ASSET_SIXTH = 5
        ASSET_SEVENTH = 6
        ASSET_EIGHTH = 7

    def __init__(self):
        super().__init__()  # __init__() QAbstractItemModel.
        self.columns: dict[int, (AssetColumn, Column)] = {
            self.Columns.ASSET_FIRST:
                (AssetColumn(header='uid',
                             data_function=lambda item: item.data.asset.uid),
                 Column(data_function=lambda item: item.data.uid)),
            self.Columns.ASSET_SECOND:
                (AssetColumn(header='Тип актива',
                             data_function=lambda item: item.data.asset.type,
                             display_function=lambda item: reportAssetType(item.data.asset.type)),
                 Column(data_function=lambda item: item.data.figi)),
            self.Columns.ASSET_THIRD:
                (AssetColumn(header='Наименование актива',
                             data_function=lambda item: item.data.asset.name),
                 Column(data_function=lambda item: item.data.instrument_type)),
            self.Columns.ASSET_FOURTH:
                (AssetColumn(),
                 Column(header='Тикер',
                        data_function=lambda item: item.data.ticker)),
            self.Columns.ASSET_FIFTH:
                (AssetColumn(),
                 Column(header='Класс-код',
                        data_function=lambda item: item.data.class_code)),
            self.Columns.ASSET_SIXTH:
                (AssetColumn(),
                 Column(header='Тип инструмента',
                        data_function=lambda item: item.data.asset.instrument_kind,
                        display_function=lambda item: reportInstrumentType(item.data.instrument_kind))),
            self.Columns.ASSET_SEVENTH:
                (AssetColumn(header='Наименование бренда',
                             header_tooltip='Наименование бренда.',
                             data_function=lambda item: None if item.data.full_asset is None else item.data.full_asset.brand.name,
                             full_dependence=True),
                 Column()),
            self.Columns.ASSET_EIGHTH:
                (AssetColumn(header='Компания',
                             header_tooltip='Компания.',
                             data_function=lambda item: None if item.data.full_asset is None else item.data.full_asset.brand.company,
                             full_dependence=True),
                 Column())
        }
        self._root_item: TreeItem = TreeItem(None, None, [], 0, -1)
        self._assets: list[AssetClass] = []

    def setAssets(self, assets: list[AssetClass]):
        """Устанавливает данные модели."""
        self.beginResetModel()  # Начинает операцию сброса модели.
        self._assets = assets
        '''---------------Создание иерархической структуры---------------'''
        assets_items: list[TreeItem] = []
        for i, asset_class in enumerate(self._assets):
            asset_item: TreeItem = TreeItem(self._root_item, asset_class, [], i, 0)
            asset_instruments: list[TreeItem] = []
            for j, instrument in enumerate(asset_class.asset.instruments):
                instrument_item: TreeItem = TreeItem(asset_item, instrument, [], j, 1)
                asset_instruments.append(instrument_item)
            asset_item.setChildren(asset_instruments)
            assets_items.append(asset_item)
        self._root_item.setChildren(assets_items)
        '''--------------------------------------------------------------'''

        for row, asset_class in enumerate(self._assets):
            for column, (asset_column, instrument_column) in enumerate(self.columns.values()):
                if asset_column.dependsOnFull():
                    index: QModelIndex = self.index(row, column, QModelIndex())
                    # asset_class.setAssetFull_signal.connect(lambda: self.dataChanged.emit(index, index))  # Подключаем слот обновления.
                    asset_class.setAssetFull_signal.connect(update_class(self, index, index))  # Подключаем слот обновления.

        self.endResetModel()  # Завершает операцию сброса модели.

    def rowCount(self, parent: QModelIndex = ...) -> int:
        """Возвращает количество дочерних строк в текущем элементе."""
        if parent.column() > 0: return 0
        if parent.isValid():  # Если индекс parent действителен.
            tree_item: TreeItem = parent.internalPointer()  # Указатель на внутреннюю структуру данных.
            assert type(tree_item) == TreeItem
        else:  # Если parent недействителен, то parent - корневой элемент.
            tree_item: TreeItem = self._root_item
        return tree_item.childrenCount()

    def columnCount(self, parent: QModelIndex = ...) -> int:
        """Возвращает количество дочерних столбцов в текущем элементе."""
        return len(self.columns)

    def parent(self, child: QModelIndex) -> QModelIndex:
        """Возвращает родителя элемента."""
        if child.isValid():  # Если индекс child действителен.
            child_item: TreeItem = child.internalPointer()  # Указатель на внутреннюю структуру данных.
            assert type(child_item) == TreeItem
            parent_item: TreeItem | None = child_item.parent()
            if parent_item is None:
                return QModelIndex()
            elif parent_item == self._root_item:
                return QModelIndex()
            else:
                return self.createIndex(parent_item.row(), 0, parent_item)
        else:  # Если индекс child недействителен.
            return QModelIndex()

    def index(self, row: int, column: int, parent: QModelIndex = ...) -> QModelIndex:
        """Возвращает индекс элемента в модели."""
        if parent.isValid():  # Если индекс parent действителен.
            parent_item: TreeItem = parent.internalPointer()  # Указатель на внутреннюю структуру данных.
            assert type(parent_item) == TreeItem
        else:
            parent_item: TreeItem = self._root_item
        tree_item: TreeItem | None = parent_item.child(row)
        if tree_item is None:
            return QModelIndex()
        else:
            return self.createIndex(row, column, tree_item)

    def data(self, index: QModelIndex, role: int = ...) -> typing.Any:
        """Возвращает данные, на которые ссылается index."""
        tree_item: TreeItem = index.internalPointer()  # Указатель на внутреннюю структуру данных.
        assert type(tree_item) == TreeItem
        hierarchy_level: int = tree_item.getHierarchyLevel()
        if hierarchy_level >= 0:
            current_column: Column = self.columns[index.column()][hierarchy_level]
            return current_column(role, tree_item)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = ...) -> typing.Any:
        """Возвращает данные заголовка."""
        if orientation == Qt.Orientation.Horizontal:
            if role == Qt.ItemDataRole.DisplayRole:
                columns_tuple: tuple[Column, Column] | None = self.columns.get(section, None)
                if columns_tuple is None: return None  # Если в словаре нет подходящего столбца.
                for column in columns_tuple:
                    if column.header is not None:
                        return column.header
            elif role == Qt.ItemDataRole.ToolTipRole:
                columns_tuple: tuple[Column, Column] | None = self.columns.get(section, None)
                if columns_tuple is None: return None  # Если в словаре нет подходящего столбца.
                for column in columns_tuple:
                    if column.header_tooltip is not None:
                        return column.header_tooltip
