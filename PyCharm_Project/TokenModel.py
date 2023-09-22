"""
Новая модель для замены QAbstractListModel на QAbstractItemModel в модуле TokensListModel и
QAbstractItemModel на QAbstractProxyModel в модуле AccessModel.
"""

from __future__ import annotations
import typing

from PyQt6.QtCore import QAbstractItemModel, QModelIndex, QVariant, Qt, QIdentityProxyModel

from Classes import TokenClass
from LimitClasses import MyUnaryLimit, MyStreamLimit
from MyRequests import MyResponse, getAccounts, getUserTariff
from TokenManager import TokenManager


def getTokenClass(token: str, show_unauthenticated_error=False) -> TokenClass:
    """Создаёт класс TokenClass из токена."""

    accounts: MyResponse = getAccounts(token, show_unauthenticated_error)  # Получаем список счетов.

    unary_limits, stream_limits = getUserTariff(token, show_unauthenticated_error).response_data
    my_unary_limits: list[MyUnaryLimit] = [MyUnaryLimit(unary_limit) for unary_limit in unary_limits]  # Массив лимитов пользователя по unary-запросам.
    my_stream_limits: list[MyStreamLimit] = [MyStreamLimit(stream_limit) for stream_limit in stream_limits]  # Массив лимитов пользователя по stream-соединениям.

    return TokenClass(token, accounts.response_data, my_unary_limits, my_stream_limits)


class TokenModel(QAbstractItemModel):
    """Модель токенов."""
    def __init__(self):
        super().__init__()  # __init__() QAbstractListModel.
        self.token_manager: TokenManager = TokenManager()
        token_list: list[str] = self.token_manager.getTokens()
        token_class_list: list[TokenClass] = [getTokenClass(token) for token in token_list]  # Получение списка класса TokenClass.
        self._tokens: list[TokenClass] = token_class_list

    def rowCount(self, parent: QModelIndex = ...) -> int:
        """Возвращает количество токенов в модели."""
        return len(self._tokens)

    def columnCount(self, parent: QModelIndex = ...) -> int:
        """Возвращает количество столбцов."""
        return 1

    def parent(self, child: QModelIndex) -> QModelIndex:
        return QModelIndex()

    def data(self, index: QModelIndex, role: int = ...) -> typing.Any:
        if role == Qt.ItemDataRole.UserRole:
            token_class: TokenClass = self._tokens[index.row()]
            return QVariant(token_class)
        elif role == Qt.ItemDataRole.DisplayRole:
            token_class: TokenClass = self._tokens[index.row()]
            return QVariant(token_class.token)
        else:
            return QVariant()

    def index(self, row: int, column: int, parent: QModelIndex = ...) -> QModelIndex:
        assert column == 0
        return self.createIndex(row, column)

    def getTokenClass(self, row: int) -> TokenClass:
        """Возвращает TokenClass, соответствующий переданному номеру."""
        if 0 <= row < self.rowCount():
            return self._tokens[row]
        else:
            raise ValueError('Некорректное значение row в getTokenClass() ({0})!'.format(row))

    def getTokens(self) -> list[TokenClass]:
        return self._tokens

    def addToken(self, token_class: TokenClass):
        """Добавляет токен."""
        row_count: int = self.rowCount()
        self.beginInsertRows(QModelIndex(), row_count, row_count)
        self.token_manager.addToken(token_class.token)
        self._tokens.append(token_class)
        self.endInsertRows()
        new_index: QModelIndex = self.index(row_count, 0, QModelIndex())
        self.dataChanged.emit(new_index, new_index)  # Испускаем сигнал о том, что данные модели были изменены.

    def deleteToken(self, token_index: QModelIndex) -> TokenClass:
        """Удаляет токен."""
        token_row: int = token_index.row()
        self.beginRemoveRows(QModelIndex(), token_row, token_row)
        manager_token: str = self.token_manager.deleteToken(token_row)
        model_token: TokenClass = self._tokens.pop(token_row)
        if not manager_token == model_token.token:
            raise ValueError('Удалён неверный токен из менеджера ({0} вместо {1})!'.format(manager_token, model_token))
        self.endRemoveRows()
        self.dataChanged.emit(token_index, token_index)  # Испускаем сигнал о том, что данные модели были изменены.
        return model_token


class TokenListModel(QIdentityProxyModel):
    """Модель для отображения токенов в ComboBox'ах."""
    TOKEN_COMBOBOX_DEFAULT_ELEMENT: str = 'Не выбран'

    def sourceModel(self) -> TokenModel:
        source_model = super().sourceModel()
        assert type(source_model) == TokenModel
        return typing.cast(TokenModel, source_model)

    def rowCount(self, parent: QModelIndex = ...) -> int:
        return self.sourceModel().rowCount() + 1

    def index(self, row: int, column: int = 0, parent: QModelIndex = ...) -> QModelIndex:
        if row == self.rowCount() - 1:
            return self.createIndex(row, column)
        return super().index(row, column, parent)

    def data(self, index: QModelIndex, role: int = ...) -> typing.Any:
        assert index.row() >= 0
        if index.row() == 0:
            if role == Qt.ItemDataRole.DisplayRole:
                return QVariant(self.TOKEN_COMBOBOX_DEFAULT_ELEMENT)
            elif role == Qt.ItemDataRole.UserRole:
                return None
        else:
            source_row: int = index.row() - 1
            source_index: QModelIndex = self.sourceModel().index(source_row, 0)
            source_data = source_index.data(role)
            return QVariant(source_data)


# class TokenListModel(QAbstractProxyModel):
#     """Модель для отображения токенов в ComboBox'ах."""
#     TOKEN_COMBOBOX_DEFAULT_ELEMENT: str = 'Не выбран'
#
#     def sourceModel(self) -> TokenModel:
#         source_model = super().sourceModel()
#         assert type(source_model) == TokenModel
#         return typing.cast(TokenModel, source_model)
#
#     def parent(self, child: QModelIndex) -> QModelIndex:
#         return QModelIndex()
#
#     def rowCount(self, parent: QModelIndex = ...) -> int:
#         return self.sourceModel().rowCount() + 1
#
#     def columnCount(self, parent: QModelIndex = ...) -> int:
#         return self.sourceModel().columnCount()
#
#     def index(self, row: int, column: int, parent: QModelIndex = ...) -> QModelIndex:
#         # if not self.hasIndex(row, column):
#         #     return QModelIndex()
#         # assert column == 0
#         # if column < 0 or column >= self.columnCount():
#         #     return QModelIndex()
#         return self.createIndex(row, column)
#
#     def mapToSource(self, proxyIndex: QModelIndex) -> QModelIndex:
#         proxy_row: int = proxyIndex.row()
#         if proxy_row < 1:
#             return QModelIndex()
#         else:
#             return self.sourceModel().index(proxy_row - 1, proxyIndex.column())
#
#     def mapFromSource(self, sourceIndex: QModelIndex) -> QModelIndex:
#         # source_row: int = sourceIndex.row()
#         # if source_row < 0 or source_row >= self.sourceModel().rowCount():
#         #     return QModelIndex()
#         return self.index((sourceIndex.row() + 1), sourceIndex.column())
#
#     def data(self, index: QModelIndex, role: int = ...) -> typing.Any:
#         assert index.row() >= 0
#         if index.row() == 0:
#             if role == Qt.ItemDataRole.DisplayRole:
#                 return QVariant(self.TOKEN_COMBOBOX_DEFAULT_ELEMENT)
#             elif role == Qt.ItemDataRole.UserRole:
#                 return None
#         else:
#             source_row: int = index.row() - 1
#             source_index: QModelIndex = self.sourceModel().index(source_row, 0)
#             source_data = source_index.data(role)
#             return QVariant(source_data)
