from __future__ import annotations
import enum
import typing
from PyQt6.QtCore import QAbstractItemModel, QModelIndex, Qt
from tinkoff.invest import Asset, AssetInstrument, AssetType, InstrumentType
from Classes import Column


class TreeItem:
    def __init__(self, parent: TreeItem | None, data: list[Asset] | Asset | AssetInstrument | None, children: list[TreeItem], row: int, hierarchy_level: int):
        self._parent: TreeItem | None = parent  # Родительский элемент.
        self.__data: Asset | AssetInstrument | None = data
        self._children: list[TreeItem] = children  # Список дочерних элементов.
        self._row: int = row  # Номер строки элемента.
        self._hierarchy_level: int = hierarchy_level

    @property
    def data(self) -> list[Asset] | Asset | AssetInstrument | None:
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

    def __init__(self):
        super().__init__()  # __init__() QAbstractItemModel.
        self.columns: dict[int, (Column, Column)] = {
            self.Columns.ASSET_FIRST:
                (Column(header='uid',
                        data_function=lambda item: item.data.uid),
                 Column(data_function=lambda item: item.data.uid)),
            self.Columns.ASSET_SECOND:
                (Column(header='Тип актива',
                        data_function=lambda item: item.data.type,
                        display_function=lambda item: reportAssetType(item.data.type)),
                 Column(data_function=lambda item: item.data.figi)),
            self.Columns.ASSET_THIRD:
                (Column(header='Наименование актива',
                        data_function=lambda item: item.data.name),
                 Column(data_function=lambda item: item.data.instrument_type)),
            self.Columns.ASSET_FOURTH:
                (Column(),
                 Column(header='Тикер',
                        data_function=lambda item: item.data.ticker)),
            self.Columns.ASSET_FIFTH:
                (Column(),
                 Column(header='Класс-код',
                        data_function=lambda item: item.data.class_code)),
            self.Columns.ASSET_SIXTH:
                (Column(),
                 Column(header='Тип инструмента',
                        data_function=lambda item: item.data.instrument_kind,
                        display_function=lambda item: reportInstrumentType(item.data.instrument_kind))),
            self.Columns.ASSET_SEVENTH:
                (Column(),
                 Column(header='Id позиции',
                        data_function=lambda item: item.data.position_uid))
        }
        self._root_item: TreeItem = TreeItem(None, None, [], 0, -1)
        self._assets: list[Asset] = []

    def setAssets(self, assets: list[Asset]):
        """Устанавливает данные модели."""
        self.beginResetModel()  # Начинает операцию сброса модели.
        self._assets = assets
        assets_items: list[TreeItem] = []
        for i, asset in enumerate(self._assets):
            asset_item: TreeItem = TreeItem(self._root_item, asset, [], i, 0)
            asset_instruments: list[TreeItem] = []
            for j, instrument in enumerate(asset.instruments):
                instrument_item: TreeItem = TreeItem(asset_item, instrument, [], j, 1)
                asset_instruments.append(instrument_item)
            asset_item.setChildren(asset_instruments)
            assets_items.append(asset_item)
        self._root_item.setChildren(assets_items)
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
