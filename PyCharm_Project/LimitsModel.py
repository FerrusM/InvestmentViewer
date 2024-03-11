from __future__ import annotations
import enum
import typing
from PyQt6.QtCore import QAbstractItemModel, QModelIndex, Qt
from Classes import Column, TokenClass
from LimitClasses import MyUnaryLimit, MyStreamLimit, MyMethod, LimitPerMinuteSemaphore


class TreeItem:
    def __init__(self, parent: TreeItem | None, data, children: list[TreeItem], row: int):
        self._parent: TreeItem | None = parent
        self.data: tuple[list[MyUnaryLimit], list[MyStreamLimit]] | MyUnaryLimit | MyStreamLimit | MyMethod | None = data
        self._children: list[TreeItem] = children  # Список дочерних элементов.
        self._row: int = row  # Номер строки элемента.

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


@enum.unique  # Декоратор, требующий, чтобы все элементы имели разные значения.
class TreeLevel(enum.IntEnum):
    """Уровень элемента в иерархической структуре."""
    LIMIT_TYPE = 0
    LIMIT_NUMBER = 1
    LIMIT_METHOD = 2


class LimitsTreeModel(QAbstractItemModel):
    """Класс модели лимитов пользователя."""
    @enum.unique  # Декоратор, требующий, чтобы все элементы имели разные значения.
    class RowOrderOfLimitTypes(enum.IntEnum):
        """Перечисление типов лимитов."""
        UNARY_REQUESTS_ROW = 0
        STREAM_CONNECTIONS_ROW = 1

    @enum.unique  # Декоратор, требующий, чтобы все элементы имели разные значения.
    class Columns(enum.IntEnum):
        """Перечисление столбцов."""
        LIMIT_FIRST = 0
        LIMIT_SECOND = 1
        LIMIT_THIRD = 2
        LIMIT_FOURTH = 3
        LIMIT_FIFTH = 4

    def __init__(self, token: TokenClass | None = None):
        super().__init__()  # __init__() QAbstractItemModel.
        self.columns: dict[int, (Column, Column, Column)] = {
            self.Columns.LIMIT_FIRST:
                (Column(header='Тип',
                        header_tooltip='Тип лимитов.',
                        # data_function=lambda item: None if not item.data else 'Unary-запросы' if all(map(lambda p: isinstance(p, MyUnaryLimit), item.data)) else 'Stream-соединения' if all(map(lambda p: isinstance(p, MyStreamLimit), item.data)) else None),
                        data_function=lambda item: 'Unary-запросы' if item.row() == self.RowOrderOfLimitTypes.UNARY_REQUESTS_ROW else 'Stream-соединения' if item.row() == self.RowOrderOfLimitTypes.STREAM_CONNECTIONS_ROW else None),
                 Column(),
                 Column()),
            self.Columns.LIMIT_SECOND:
                (Column(header='Лимиты',
                        header_tooltip='Лимиты.',
                        data_function=lambda item: 'Количество лимитов: {0}'.format(item.childrenCount())),
                 Column(data_function=lambda item: 'Лимит {0} ({1})'.format((item.row() + 1), item.data.limit_per_minute) if isinstance(item.data, MyUnaryLimit) else 'Лимит {0} ({1})'.format((item.row() + 1), item.data.limit) if isinstance(item.data, MyStreamLimit) else None),
                 Column()),
            self.Columns.LIMIT_THIRD:
                (Column(header='Методы',
                        header_tooltip='Методы.',
                        data_function=lambda item: 'Количество методов: {0}'.format(sum([len(limit.methods) for limit in item.data]))),
                 Column(data_function=lambda item: 'Количество методов: {0}'.format(item.childrenCount())),
                 Column(data_function=lambda item: item.data.full_method)),
            self.Columns.LIMIT_FOURTH:
                (Column(header='Сервис',
                        header_tooltip='Сервис.'),
                 Column(data_function=lambda item: item.data.methods[0].service if len(set([method.service for method in item.data.methods])) == 1 else None),
                 Column(data_function=lambda item: item.data.service)),
            self.Columns.LIMIT_FIFTH:
                (Column(header='Имя метода',
                        header_tooltip='Имя метода.'),
                 Column(data_function=lambda item: 'Доступно: {0}'.format(item.data.semaphore.available())),
                 Column(data_function=lambda item: item.data.method_name)),
        }
        self._root_item: TreeItem = TreeItem(None, None, [], 0)
        self._token: TokenClass | None = None
        self.setToken(token)

    def setToken(self, token: TokenClass | None):
        """Устанавливает токен для отображения лимитов."""
        # def addLimitsChildren(limits_item: TreeItem):
        #     """Создаёт и возвращает элемент TreeItem первого уровня."""
        #     limits_items_list: list[TreeItem] = []
        #     for row, limit in enumerate(limits_item.data):
        #         limit_item: TreeItem = TreeItem(limits_item, limit, [], row)
        #         limit_item.setChildren([TreeItem(limit_item, method, [], j) for j, method in enumerate(limit_item.data.methods)])
        #         limits_items_list.append(limit_item)
        #     limits_item.setChildren(limits_items_list)

        self.beginResetModel()  # Начинает операцию сброса модели.
        self._token = token
        if self._token is None:
            self._root_item.setChildren([])
        else:
            unary_limits_item: TreeItem = TreeItem(self._root_item, self._token.unary_limits, [], self.RowOrderOfLimitTypes.UNARY_REQUESTS_ROW)
            unary_limits_list: list[TreeItem] = []
            for row, limit in enumerate(unary_limits_item.data):
                limit_item: TreeItem = TreeItem(unary_limits_item, limit, [], row)
                limit_item.setChildren([TreeItem(limit_item, method, [], j) for j, method in enumerate(limit_item.data.methods)])
                unary_limits_list.append(limit_item)
            unary_limits_item.setChildren(unary_limits_list)

            stream_limits_item: TreeItem = TreeItem(self._root_item, self._token.stream_limits, [], self.RowOrderOfLimitTypes.STREAM_CONNECTIONS_ROW)
            stream_limits_list: list[TreeItem] = []
            for row, limit in enumerate(stream_limits_item.data):
                limit_item: TreeItem = TreeItem(stream_limits_item, limit, [], row)
                limit_item.setChildren([TreeItem(limit_item, method, [], j) for j, method in enumerate(limit_item.data.methods)])
                stream_limits_list.append(limit_item)
            stream_limits_item.setChildren(stream_limits_list)

            self._root_item.setChildren([unary_limits_item, stream_limits_item])

            '''---------------Подключение слотов для обновления ячеек---------------'''
            for unary_limit_item in self._root_item.child(self.RowOrderOfLimitTypes.UNARY_REQUESTS_ROW).getChildren():
                index: QModelIndex = self.index(unary_limit_item.row(), self.Columns.LIMIT_FIFTH, QModelIndex())
                semaphore: LimitPerMinuteSemaphore = unary_limit_item.data.semaphore
                semaphore.availableChanged_signal.connect(lambda: self.dataChanged.emit(index, index))
            '''---------------------------------------------------------------------'''

        self.endResetModel()  # Завершает операцию сброса модели.

    def rowCount(self, parent: QModelIndex = ...) -> int:
        """Возвращает количество дочерних строк в текущем элементе."""
        if parent.column() > 0: return 0
        if parent.isValid():  # Если индекс parent действителен.
            tree_item: TreeItem = parent.internalPointer()  # Указатель на внутреннюю структуру данных.
            assert type(tree_item) is TreeItem
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
            assert type(child_item) is TreeItem
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
            assert type(parent_item) is TreeItem
        else:
            parent_item: TreeItem = self._root_item
        tree_item: TreeItem | None = parent_item.child(row)
        if tree_item is None:
            return QModelIndex()
        else:
            return self.createIndex(row, column, tree_item)

    @staticmethod  # Преобразует метод класса в статический метод этого класса.
    def _checkDataType(data) -> int | None:
        """Проверка типа внутренней структуры данных."""
        if isinstance(data, list):
            if all(map(lambda p: isinstance(p, MyUnaryLimit), data)) or all(map(lambda p: isinstance(p, MyStreamLimit), data)):
                return TreeLevel.LIMIT_TYPE
            else:
                return None
        elif isinstance(data, MyUnaryLimit | MyStreamLimit):
            return TreeLevel.LIMIT_NUMBER
        elif isinstance(data, MyMethod):
            return TreeLevel.LIMIT_METHOD
        else:
            return None

    def data(self, index: QModelIndex, role: int = ...) -> typing.Any:
        """Возвращает данные, на которые ссылается index."""
        tree_item: TreeItem = index.internalPointer()  # Указатель на внутреннюю структуру данных.
        assert type(tree_item) is TreeItem
        item_data: list[MyUnaryLimit] | list[MyStreamLimit] | MyUnaryLimit | MyStreamLimit | MyMethod = tree_item.data
        data_type: int | None = self._checkDataType(item_data)
        if data_type is None: return None
        current_column: Column | None = self.columns[index.column()][data_type]
        if current_column is None: return None
        return current_column(role, tree_item)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = ...) -> typing.Any:
        """Возвращает данные заголовка."""
        if orientation == Qt.Orientation.Horizontal:
            if role == Qt.ItemDataRole.DisplayRole:
                columns_tuple: tuple[Column, Column, Column] | None = self.columns.get(section, None)
                if columns_tuple is None: return None  # Если в словаре нет подходящего столбца.
                for column in columns_tuple:
                    if column.header is not None:
                        return column.header
            elif role == Qt.ItemDataRole.ToolTipRole:
                columns_tuple: tuple[Column, Column, Column] | None = self.columns.get(section, None)
                if columns_tuple is None: return None  # Если в словаре нет подходящего столбца.
                for column in columns_tuple:
                    if column.header_tooltip is not None:
                        return column.header_tooltip
        # elif orientation == Qt.Orientation.Vertical:
        #     if role == Qt.ItemDataRole.DisplayRole:
        #         return section + 1  # Проставляем номера строк.
