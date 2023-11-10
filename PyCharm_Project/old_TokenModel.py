from __future__ import annotations
import typing
from PyQt6.QtCore import QAbstractItemModel, QModelIndex, QVariant, Qt, QIdentityProxyModel, QSettings
from tinkoff.invest import Account, UnaryLimit, StreamLimit
from Classes import TokenClass
from LimitClasses import MyUnaryLimit, MyStreamLimit
from MyRequests import MyResponse, getAccounts, getUserTariff, RequestTryClass


class TokenManager:
    """Класс для управления токенами доступа."""
    def __init__(self):
        self.file_name: str = 'tokens'  # Имя файла.
        self.prefix: str = 'tokens'  # Префикс.
        self.key: str = 'token'  # Ключ.

        # Указываем расположение и формат (ini-файл) сохранения настроек.
        self.settings = QSettings(self.file_name, QSettings.Format.IniFormat)

        self._tokens_list: list[str] = self._extractTokens()  # Извлекаем список токенов из ini-файла.

    def _extractTokens(self) -> list[str]:
        """Извлекает токены из ini-файла."""
        size: int = self.settings.beginReadArray(self.prefix)  # Количество элементов в массиве.
        tokens_list: list[str] = []
        for i in range(size):
            self.settings.setArrayIndex(i)  # Устанавливает текущий индекс массива в i.
            tokens_list.append(self.settings.value(self.key))
        self.settings.endArray()
        return tokens_list

    def addToken(self, new_token: str):
        """Добавляет токен."""
        self._tokens_list.append(new_token)
        self._saveTokens()  # Перезаписывает массив токенов в ini-файле.

    def deleteToken(self, token_index: int) -> str:
        """Удаляет токен."""
        deleted_token: str = self._tokens_list.pop(token_index)
        self.settings.remove(self.prefix)
        self._saveTokens()  # Перезаписывает массив токенов в ini-файле.
        return deleted_token

    def _saveTokens(self):
        """Сохраняет все токены в ini-файл."""
        self.settings.beginWriteArray(self.prefix)  # Добавляет префикс в текущую группу и начинает запись массива.
        for i, token in enumerate(self._tokens_list):
            self.settings.setArrayIndex(i)  # Устанавливает текущий индекс массива в i.
            self.settings.setValue(self.key, token)
        self.settings.endArray()

    def getTokens(self) -> list[str]:
        """Возвращает список токенов."""
        return self._tokens_list


class TokenModel(QAbstractItemModel):
    """Модель токенов."""
    def __init__(self):
        def getTokenClass(token: str, show_unauthenticated_error=False) -> TokenClass:
            """Создаёт класс TokenClass из токена."""

            '''------------------------Получение счетов------------------------'''
            accounts_try_count: RequestTryClass = RequestTryClass(1)
            accounts_response: MyResponse = MyResponse()
            while accounts_try_count and not accounts_response.ifDataSuccessfullyReceived():
                accounts_response = getAccounts(token, show_unauthenticated_error)  # Получаем список счетов.
                assert accounts_response.request_occurred, 'Запрос счетов не был произведён.'
                accounts_try_count += 1
            accounts: list[Account] = accounts_response.response_data if accounts_response.ifDataSuccessfullyReceived() else []
            '''----------------------------------------------------------------'''

            '''---------------------------Получение лимитов---------------------------'''
            limits_try_count: RequestTryClass = RequestTryClass(1)
            limits_response: MyResponse = MyResponse()
            while limits_try_count and not limits_response.ifDataSuccessfullyReceived():
                limits_response = getUserTariff(token, show_unauthenticated_error)
                assert limits_response.request_occurred, 'Запрос лимитов не был произведён.'
                limits_try_count += 1

            if limits_response.ifDataSuccessfullyReceived():
                unary_limits: list[UnaryLimit]
                stream_limits: list[StreamLimit]
                unary_limits, stream_limits = limits_response.response_data
                my_unary_limits: list[MyUnaryLimit] = [MyUnaryLimit(unary_limit) for unary_limit in unary_limits]  # Массив лимитов пользователя по unary-запросам.
                my_stream_limits: list[MyStreamLimit] = [MyStreamLimit(stream_limit) for stream_limit in stream_limits]  # Массив лимитов пользователя по stream-соединениям.
            else:
                my_unary_limits: list[MyUnaryLimit] = []  # Массив лимитов пользователя по unary-запросам.
                my_stream_limits: list[MyStreamLimit] = []  # Массив лимитов пользователя по stream-соединениям.
            '''-----------------------------------------------------------------------'''

            return TokenClass(token, accounts, my_unary_limits, my_stream_limits)

            # accounts_response: MyResponse = getAccounts(token, show_unauthenticated_error)  # Получаем список счетов.
            # assert accounts_response.request_occurred, 'Запрос счетов не был произведён.'
            #
            # limits_response: MyResponse = getUserTariff(token, show_unauthenticated_error)
            # assert limits_response.request_occurred, 'Запрос лимитов не был произведён.'
            # unary_limits, stream_limits = limits_response.response_data
            # my_unary_limits: list[MyUnaryLimit] = [MyUnaryLimit(unary_limit) for unary_limit in unary_limits]  # Массив лимитов пользователя по unary-запросам.
            # my_stream_limits: list[MyStreamLimit] = [MyStreamLimit(stream_limit) for stream_limit in stream_limits]  # Массив лимитов пользователя по stream-соединениям.
            #
            # return TokenClass(token, accounts_response.response_data, my_unary_limits, my_stream_limits)

        super().__init__()  # __init__() QAbstractItemModel.
        self.token_manager: TokenManager = TokenManager()
        token_list: list[str] = self.token_manager.getTokens()
        self._tokens: list[TokenClass] = [getTokenClass(token) for token in token_list]  # Получение списка класса TokenClass.

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
