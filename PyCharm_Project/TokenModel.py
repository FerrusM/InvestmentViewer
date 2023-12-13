import typing
from PyQt6.QtCore import QObject, QAbstractItemModel, QModelIndex, Qt, QVariant, QIdentityProxyModel
from PyQt6.QtSql import QSqlQuery, QSqlDatabase
from tinkoff.invest import Account, UnaryLimit, StreamLimit
from Classes import TokenClass, MyConnection
from LimitClasses import MyUnaryLimit, MyStreamLimit
from MyDatabase import MainConnection


class TokenModel(QAbstractItemModel):
    """Модель токенов."""
    def __init__(self, parent: QObject | None = ...):
        super().__init__(parent)  # __init__() QAbstractItemModel.
        self._tokens: list[TokenClass] = []  # Список класса TokenClass.

        """===========================Заполняем список токенов==========================="""
        db: QSqlDatabase = MainConnection.getDatabase()

        tokens_sql_command: str = 'SELECT \"token\", \"name\" FROM {0};'.format('\"{0}\"'.format(MyConnection.TOKENS_TABLE))
        tokens_query = QSqlQuery(db)
        tokens_prepare_flag: bool = tokens_query.prepare(tokens_sql_command)
        assert tokens_prepare_flag, tokens_query.lastError().text()

        tokens_exec_flag: bool = tokens_query.exec()
        assert tokens_exec_flag, tokens_query.lastError().text()

        while tokens_query.next():
            token: str = tokens_query.value(0)  # Токен.
            name: str = tokens_query.value(1)  # Название токена.

            '''---------Получение счетов---------'''
            accounts_sql_command: str = '''
            SELECT \"id\", \"type\", \"name\", \"status\", \"opened_date\", \"closed_date\", \"access_level\" FROM {0} WHERE {0}.\"token\" = :token;
            '''.format('\"{0}\"'.format(MyConnection.ASSETS_TABLE))
            accounts_query = QSqlQuery(db)
            accounts_prepare_flag: bool = accounts_query.prepare(accounts_sql_command)
            assert accounts_prepare_flag, accounts_query.lastError().text()

            accounts_query.bindValue(':token', token)

            accounts_exec_flag: bool = accounts_query.exec()
            assert accounts_exec_flag, accounts_query.lastError().text()

            accounts: list[Account] = []  # Список аккаунтов.
            while accounts_query.next():
                account: Account = Account(
                    id=accounts_query.value(0),
                    type=accounts_query.value(1),
                    name=accounts_query.value(2),
                    status=accounts_query.value(3),
                    opened_date=MyConnection.convertTextToDateTime(accounts_query.value(4)),
                    closed_date=MyConnection.convertTextToDateTime(accounts_query.value(5)),
                    access_level=accounts_query.value(6)
                )
                accounts.append(account)
            '''----------------------------------'''

            '''---------Получение unary-лимитов---------'''
            unary_limits_query = QSqlQuery(db)

            unary_limits_sql_command: str = 'SELECT \"limit_per_minute\", \"methods\" FROM {0} WHERE \"token\" = :token;'.format('\"{0}\"'.format(MyConnection.UNARY_LIMITS_TABLE))
            unary_limits_prepare_flag: bool = unary_limits_query.prepare(unary_limits_sql_command)
            assert unary_limits_prepare_flag, unary_limits_query.lastError().text()

            unary_limits_query.bindValue(':token', token)

            unary_limits_exec_flag: bool = unary_limits_query.exec()
            assert unary_limits_exec_flag, unary_limits_query.lastError().text()

            unary_limits: list[UnaryLimit] = []  # Unary-лимиты.
            while unary_limits_query.next():
                unary_limit: UnaryLimit = UnaryLimit(
                    limit_per_minute=unary_limits_query.value(0),
                    methods=unary_limits_query.value(1).split(', ')
                )
                unary_limits.append(unary_limit)

            my_unary_limits: list[MyUnaryLimit] = [MyUnaryLimit(unary_limit) for unary_limit in unary_limits]  # Массив лимитов пользователя по unary-запросам.
            '''-----------------------------------------'''

            '''---------Получение stream-соединений---------'''
            stream_limits_query = QSqlQuery(db)

            stream_limits_sql_command: str = 'SELECT \"limit_count\", \"streams\", \"open\" FROM {0} WHERE \"token\" = :token;'.format('\"{0}\"'.format(MyConnection.STREAM_LIMITS_TABLE))
            stream_limits_prepare_flag: bool = stream_limits_query.prepare(stream_limits_sql_command)
            assert stream_limits_prepare_flag, stream_limits_query.lastError().text()

            stream_limits_query.bindValue(':token', token)

            stream_limits_exec_flag: bool = stream_limits_query.exec()
            assert stream_limits_exec_flag, stream_limits_query.lastError().text()

            stream_limits: list[StreamLimit] = []  # Stream-лимиты.
            while stream_limits_query.next():
                stream_limit: StreamLimit = StreamLimit(
                    limit=stream_limits_query.value(0),
                    streams=stream_limits_query.value(1).split(', '),
                    open=stream_limits_query.value(2)
                )
                stream_limits.append(stream_limit)

            my_stream_limits: list[MyStreamLimit] = [MyStreamLimit(stream_limit) for stream_limit in stream_limits]  # Массив лимитов пользователя по stream-соединениям.
            '''---------------------------------------------'''

            token_instance: TokenClass = TokenClass(
                token=token,
                name=name,
                accounts=accounts,
                unary_limits=my_unary_limits,
                stream_limits=my_stream_limits
            )
            self._tokens.append(token_instance)
        """=============================================================================="""

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

    def addToken(self, token: TokenClass):
        """Добавляет токен."""
        row_count: int = self.rowCount()
        self.beginInsertRows(QModelIndex(), row_count, row_count)
        MainConnection.addNewToken(token)  # Добавляет новый токен в базу данных.
        self._tokens.append(token)
        self.endInsertRows()
        new_index: QModelIndex = self.index(row_count, 0, QModelIndex())
        self.dataChanged.emit(new_index, new_index)  # Испускаем сигнал о том, что данные модели были изменены.

    def deleteToken(self, token_index: QModelIndex) -> TokenClass:
        """Удаляет токен."""
        token_row: int = token_index.row()
        self.beginRemoveRows(QModelIndex(), token_row, token_row)

        token: str = token_index.data(role=Qt.ItemDataRole.DisplayRole)
        MainConnection.deleteToken(token)  # Удаление токена из базы данных.

        model_token: TokenClass = self._tokens.pop(token_row)
        if not token == model_token.token:
            raise ValueError('Несоответствие удаляемого токена ({0} и {1})!'.format(token, model_token))
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
