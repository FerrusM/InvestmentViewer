from __future__ import annotations
import enum
import typing
from PyQt6 import QtCore
from PyQt6.QtCore import QAbstractItemModel, QModelIndex, Qt, pyqtSignal, QCoreApplication
from PyQt6.QtGui import QBrush
from PyQt6.QtWidgets import QPushButton, QStyledItemDelegate, QAbstractItemView
from tinkoff.invest import Account
from Classes import TokenClass, reportAccountAccessLevel, reportAccountType, reportAccountStatus, Column
from MyDatabase import MainConnection
from MyDateTime import reportSignificantInfoFromDateTime
from TokenModel import TokenModel


class TreeItem:
    def __init__(self, row: int, parent: TreeItem | None = None, data: TokenClass | Account | None = None, children: list[TreeItem] | None = None):
        self.__parent: TreeItem | None = parent
        self.__data: TokenClass | Account | None = data
        self.__row: int = row
        self.__children: list[TreeItem] = [] if children is None else children

    def parent(self) -> TreeItem | None:
        """Возвращает родительский элемент."""
        return self.__parent

    @property
    def children(self) -> list[TreeItem]:
        return self.__children

    @children.setter
    def children(self, children: list[TreeItem]):
        self.__children = children

    def child(self, row: int) -> TreeItem | None:
        if 0 <= row < len(self.__children):
            return self.__children[row]
        else:
            return None

    @property
    def row(self) -> int:
        return self.__row

    @property
    def data(self):
        return self.__data


@enum.unique  # Декоратор, требующий, чтобы все элементы имели разные значения.
class TreeLevel(enum.IntEnum):
    """Уровень элемента в иерархической структуре."""
    TOKEN = 0
    ACCOUNT = 1


class TreeProxyModel(QAbstractItemModel):
    """Иерархическая модель токенов."""
    TOKEN_BACKGROUND_COLOR: QBrush = QBrush(0xe0e8ef)  # Цвет фона токена.
    ACCOUNT_BACKGROUND_COLOR: QBrush = QBrush(0xffffe0)  # Цвет фона счёта.
    TOKEN_FOREGROUND_COLOR: QBrush = QBrush(0xbf0000)  # Цвет текста неверного токена.

    class DeleteButtonDelegate(QStyledItemDelegate):
        """Делегат кнопок удаления."""
        clicked = pyqtSignal(QModelIndex)

        @staticmethod  # Преобразует метод класса в статический метод этого класса.
        def _check(index: QModelIndex) -> bool:
            def checkDataType(data) -> int | None:
                """Проверка типа внутренней структуры данных."""
                if isinstance(data, TokenClass):
                    return TreeLevel.TOKEN
                elif isinstance(data, Account):
                    return TreeLevel.ACCOUNT
                else:
                    return None
            tree_item: TreeItem = index.internalPointer()  # Указатель на внутреннюю структуру данных.
            assert type(tree_item) is TreeItem
            item_data: TokenClass | Account = tree_item.data
            data_type: int | None = checkDataType(item_data)
            assert data_type is not None, 'Недопустимый тип элемента: Тип: {0}, Значение: {1}!'.format(type(item_data), item_data)
            return data_type == TreeLevel.TOKEN

        def createEditor(self, parent, option, index: QModelIndex) -> QPushButton:
            """Возвращает виджет, используемый для редактирования элемента."""
            if self._check(index):
                button = QPushButton(parent)
                _translate = QCoreApplication.translate
                button.setText(_translate('MainWindow', 'Удалить'))
                button.clicked.connect(lambda *args, ix=index: self.clicked.emit(ix))
                return button
            else:
                return QStyledItemDelegate.createEditor(self, parent, option, index)

        def paint(self, painter, option, index: QModelIndex) -> None:
            """Отображает делегат."""
            if self._check(index):
                parent = self.parent()
                if isinstance(parent, QAbstractItemView) and parent.model() is index.model():
                    parent.openPersistentEditor(index)
            QStyledItemDelegate.paint(self, painter, option, index)

        # def setEditorData(self, editor: QPushButton, index: QModelIndex) -> None:
        #     """Устанавливает данные, которые будут отображаться и редактироваться editor'ом."""
        #     if self._check(index):
        #         # value = index.model().data(index, Qt.ItemDataRole.DisplayRole)
        #         # editor.clicked.connect(lambda ix=index: print('Номер строки: {0}'.format(str(ix.row()))))
        #
        #         editor.setText('Удалить')
        #     else:
        #         QStyledItemDelegate.setEditorData(self, editor, index)

        # def updateEditorGeometry(self, editor: QPushButton, option, index: QModelIndex) -> None:
        #     """Обновляет editor для элемента."""
        #     editor.setGeometry(option.rect)

    @enum.unique  # Декоратор, требующий, чтобы все элементы имели разные значения.
    class Columns(enum.IntEnum):
        """Перечисление столбцов."""
        TOKEN_NUMBER = 0
        TOKEN_TOKEN = 1
        ACCOUNT_ACCESS_LEVEL = 2
        ACCOUNT_ID = 3
        ACCOUNT_TYPE = 4
        ACCOUNT_NAME = 5
        ACCOUNT_STATUS = 6
        ACCOUNT_OPENED_DATE = 7
        ACCOUNT_CLOSED_DATE = 8
        TOKEN_DELETE_BUTTON = 9

    def __init__(self, sourceModel: TokenModel, parent: QtCore.QObject | None = None):
        super().__init__(parent=parent)
        self.columns: dict[int, (Column, Column)] = {
            self.Columns.TOKEN_NUMBER:
                (Column(background_function=lambda token_class: self.TOKEN_BACKGROUND_COLOR),
                 Column()),
            self.Columns.TOKEN_TOKEN:
                (Column(header='Токен',
                        header_tooltip='Токен.',
                        data_function=lambda token_class: token_class.token,
                        foreground_function=lambda token_class: self.TOKEN_FOREGROUND_COLOR if len(token_class.accounts) < 1 else None,
                        background_function=lambda token_class: self.TOKEN_BACKGROUND_COLOR),
                 Column(background_function=lambda account: self.ACCOUNT_BACKGROUND_COLOR)
                 ),
            self.Columns.ACCOUNT_ACCESS_LEVEL:
                (Column(header='Уровень доступа',
                        header_tooltip='Уровень доступа к текущему счёту (определяется токеном).',
                        background_function=lambda token_class: self.TOKEN_BACKGROUND_COLOR),
                 Column(data_function=lambda account: account.access_level,
                        display_function=lambda account: reportAccountAccessLevel(account.access_level),
                        background_function=lambda account: self.ACCOUNT_BACKGROUND_COLOR)
                 ),
            self.Columns.ACCOUNT_ID:
                (Column(header='Идентификатор',
                        header_tooltip='Идентификатор счёта.',
                        background_function=lambda token_class: self.TOKEN_BACKGROUND_COLOR),
                 Column(data_function=lambda account: account.id,
                        background_function=lambda account: self.ACCOUNT_BACKGROUND_COLOR)
                 ),
            self.Columns.ACCOUNT_TYPE:
                (Column(header='Тип счёта',
                        header_tooltip='Тип счёта.',
                        background_function=lambda token_class: self.TOKEN_BACKGROUND_COLOR),
                 Column(data_function=lambda account: account.type,
                        display_function=lambda account: reportAccountType(account.type),
                        background_function=lambda account: self.ACCOUNT_BACKGROUND_COLOR)
                 ),
            self.Columns.ACCOUNT_NAME:
                (Column(header='Название счёта',
                        header_tooltip='Название счёта.',
                        background_function=lambda token_class: self.TOKEN_BACKGROUND_COLOR),
                 Column(data_function=lambda account: account.name,
                        background_function=lambda account: self.ACCOUNT_BACKGROUND_COLOR)
                 ),
            self.Columns.ACCOUNT_STATUS:
                (Column(header='Статус счёта',
                        header_tooltip='Статус счёта.',
                        background_function=lambda token_class: self.TOKEN_BACKGROUND_COLOR),
                 Column(data_function=lambda account: account.status,
                        display_function=lambda account: reportAccountStatus(account.status),
                        background_function=lambda account: self.ACCOUNT_BACKGROUND_COLOR)
                 ),
            self.Columns.ACCOUNT_OPENED_DATE:
                (Column(header='Дата открытия',
                        header_tooltip='Дата открытия счёта в часовом поясе UTC.',
                        background_function=lambda token_class: self.TOKEN_BACKGROUND_COLOR),
                 Column(data_function=lambda account: account.opened_date,
                        display_function=lambda account: reportSignificantInfoFromDateTime(account.opened_date),
                        background_function=lambda account: self.ACCOUNT_BACKGROUND_COLOR)
                 ),
            self.Columns.ACCOUNT_CLOSED_DATE:
                (Column(header='Дата закрытия',
                        header_tooltip='Дата закрытия счёта в часовом поясе UTC.',
                        background_function=lambda token_class: self.TOKEN_BACKGROUND_COLOR),
                 Column(data_function=lambda account: account.closed_date,
                        display_function=lambda account: reportSignificantInfoFromDateTime(account.closed_date),
                        background_function=lambda account: self.ACCOUNT_BACKGROUND_COLOR)
                 ),
            self.Columns.TOKEN_DELETE_BUTTON:
                # (Column(header='',
                #         data_function=lambda token_class: 'Удалить',
                #         foreground_function=lambda token_class: self.TOKEN_FOREGROUND_COLOR if len(token_class.accounts) < 1 else None,
                #         background_function=lambda token_class: self.TOKEN_BACKGROUND_COLOR),
                #  Column(background_function=lambda account: self.ACCOUNT_BACKGROUND_COLOR))
                (Column(header='',
                        data_function=lambda token_class: QPushButton(text='Удалить'),
                        foreground_function=lambda token_class: self.TOKEN_FOREGROUND_COLOR if len(token_class.accounts) < 1 else None,
                        background_function=lambda token_class: self.TOKEN_BACKGROUND_COLOR),
                 Column(background_function=lambda account: self.ACCOUNT_BACKGROUND_COLOR))
        }
        self.__root_item: TreeItem = TreeItem(0)  # Корневой элемент.
        self.__source_model: TokenModel = sourceModel
        self.__setTokens()
        self.__source_model.dataChanged.connect(self.__setTokens)
        self.__source_model.modelReset.connect(self.__setTokens)

    def __setTokens(self):
        self.beginResetModel()
        token_list: list[TreeItem] = []
        for row, token in enumerate(self.__source_model.getTokens()):
            token_item: TreeItem = TreeItem(row, self.__root_item, token)
            token_item.children = [TreeItem(j, token_item, account) for j, account in enumerate(token.accounts)]
            token_list.append(token_item)
        self.__root_item.children = token_list
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = ...) -> int:
        """Возвращает количество дочерних строк в текущем элементе."""
        if parent.column() > 0: return 0
        if parent.isValid():  # Если индекс parent действителен, то текущий элемент - это счёт или токен.
            tree_item: TreeItem = parent.internalPointer()
            assert type(tree_item) is TreeItem
        else:  # Если parent недействителен, то parent - корневой элемент.
            tree_item: TreeItem = self.__root_item
        return len(tree_item.children)

    def columnCount(self, parent: QModelIndex = ...) -> int:
        """Возвращает количество дочерних столбцов в текущем элементе."""
        return len(self.columns)

    @staticmethod  # Преобразует метод класса в статический метод этого класса.
    def _checkDataType(data) -> int | None:
        """Проверка типа внутренней структуры данных."""
        if isinstance(data, TokenClass):
            return TreeLevel.TOKEN
        elif isinstance(data, Account):
            return TreeLevel.ACCOUNT
        else:
            return None

    def data(self, index: QModelIndex, role: int = ...) -> typing.Any:
        """Возвращает данные, на которые ссылается index."""
        tree_item: TreeItem = index.internalPointer()  # Указатель на внутреннюю структуру данных.
        assert type(tree_item) is TreeItem
        item_data: TokenClass | Account = tree_item.data
        data_type: int | None = self._checkDataType(item_data)
        assert data_type is not None, 'Недопустимый тип элемента: Тип: {0}, Значение: {1}!'.format(type(item_data), item_data)
        current_column: Column | None = self.columns[index.column()][data_type]
        return None if current_column is None else current_column(role, item_data)

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
                columns_tuple: tuple[Column, Column, Column] | None = self.columns.get(section, None)
                if columns_tuple is None: return None  # Если в словаре нет подходящего столбца.
                for column in columns_tuple:
                    if column.header_tooltip is not None:
                        return column.header_tooltip
        # elif orientation == Qt.Orientation.Vertical:
        #     if role == Qt.ItemDataRole.DisplayRole:
        #         return section + 1  # Проставляем номера строк.

    def index(self, row: int, column: int, parent: QModelIndex = ...) -> QModelIndex:
        """Возвращает индекс элемента в модели."""
        if parent.isValid():  # Если индекс parent действителен, то parent - это токен.
            token_item: TreeItem = parent.internalPointer()
            assert type(token_item) is TreeItem and token_item.parent() == self.__root_item
            account_item: TreeItem | None = token_item.child(row)
            if account_item is None:
                return QModelIndex()
            else:
                return self.createIndex(row, column, account_item)
        else:  # Если parent недействителен, то элемент это - корневой элемент.
            token_item: TreeItem | None = self.__root_item.child(row)
            if token_item is None:
                return QModelIndex()
            else:
                return self.createIndex(row, column, token_item)

    def parent(self, child: QModelIndex) -> QModelIndex:
        """Возвращает родителя элемента."""
        if child.isValid():  # Если индекс child действителен, то parent - это корневой элемент или токен.
            tree_item: TreeItem = child.internalPointer()
            assert type(tree_item) is TreeItem
            parent_item: TreeItem | None = tree_item.parent()
            if parent_item is None:
                return QModelIndex()
            elif parent_item == self.__root_item:
                return QModelIndex()
            else:
                return self.createIndex(parent_item.row, 0, parent_item)
        else:  # Если индекс child недействителен.
            return QModelIndex()

    def getTokensCount(self) -> int:
        """Возвращает количество токенов в модели."""
        return self.__source_model.rowCount()

    # def mapToSource(self, index: QModelIndex) -> QModelIndex | None:
    #     """Находит и возвращает индекс исходной модели, соответствующий переданному индексу текущей модели."""
    #     tree_item: TreeItem = index.internalPointer()  # Указатель на внутреннюю структуру данных.
    #     assert type(tree_item) is TreeItem
    #     item_data: TokenClass | Account = tree_item.data
    #     data_type: int | None = self._checkDataType(item_data)
    #     if data_type != TreeLevel.TOKEN: return None
    #     return self.__source_model.index(tree_item.row(), 0)

    def deleteToken(self, token_index: QModelIndex) -> bool:
        """Удаляет токен."""

        """---Определяем индекс соответствующего элемента в исходной модели---"""
        tree_item: TreeItem = token_index.internalPointer()  # Указатель на внутреннюю структуру данных.
        assert type(tree_item) is TreeItem
        item_data: TokenClass | Account | None = tree_item.data
        data_type: int | None = self._checkDataType(item_data)
        if data_type != TreeLevel.TOKEN: return False
        assert type(item_data) is TokenClass
        """-------------------------------------------------------------------"""

        MainConnection.deleteToken(item_data.token)  # Удаление токена из базы данных.
        return True
