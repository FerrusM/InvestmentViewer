import typing
from PyQt6 import QtSql
from PyQt6.QtCore import QObject, QAbstractItemModel, QModelIndex, Qt, QVariant, QIdentityProxyModel
from tinkoff.invest import Account, UnaryLimit, StreamLimit
from Classes import TokenClass, MyConnection
from LimitClasses import MyUnaryLimit, MyStreamLimit
from MyDatabase import MainConnection


class TokenModel(QAbstractItemModel):
    """Модель токенов."""
    __select_tokens_command: str = 'SELECT \"token\", \"name\" FROM \"{0}\";'.format(MyConnection.TOKENS_TABLE)
    __select_accounts_command: str = '''SELECT \"id\", \"type\", \"name\", \"status\", \"opened_date\", \"closed_date\", 
    \"access_level\" FROM {0} WHERE {0}.\"token\" = :token;'''.format('\"{0}\"'.format(MyConnection.ACCOUNTS_TABLE))
    __select_unary_limits_command: str = '''SELECT \"limit_per_minute\", \"methods\" FROM \"{0}\" WHERE \"token\" = 
    :token;'''.format(MyConnection.UNARY_LIMITS_TABLE)
    __select_stream_limits_command: str = '''SELECT \"limit_count\", \"streams\", \"open\" FROM \"{0}\" WHERE \"token\" 
    = :token;'''.format(MyConnection.STREAM_LIMITS_TABLE)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent=parent)
        self.__tokens: list[TokenClass] = []  # Список класса TokenClass.
        self.update()

        def notificationSlot(name: str, source: QtSql.QSqlDriver.NotificationSource, payload: int):
            assert source == QtSql.QSqlDriver.NotificationSource.UnknownSource
            print('notificationSlot: name = {0}, payload = {1}.'.format(name, payload))

            if name == MyConnection.TOKENS_TABLE:
                rowid_select: str = '''SELECT \"token\", \"name\" FROM {0} WHERE {0}.\"rowid\" = :rowid;'''.format(
                    '\"{0}\"'.format(MyConnection.TOKENS_TABLE)
                )

                db: QtSql.QSqlDatabase = MainConnection.getDatabase()
                if db.transaction():
                    token_query = QtSql.QSqlQuery(db)
                    token_prepare_flag: bool = token_query.prepare(rowid_select)
                    assert token_prepare_flag, token_query.lastError().text()
                    token_query.bindValue(':rowid', payload)
                    token_exec_flag: bool = token_query.exec()
                    assert token_exec_flag, token_query.lastError().text()

                    rowid_count: int = 0
                    while token_query.next():
                        rowid_count += 1
                        token: str = token_query.value('token')  # Токен.
                        name: str = token_query.value('name')  # Название токена.

                    ...

                    commit_flag: bool = db.commit()  # Фиксирует транзакцию в базу данных.
                    assert commit_flag, db.lastError().text()
                else:
                    raise SystemError('Не получилось начать транзакцию! db.lastError().text(): \'{0}\'.'.format(db.lastError().text()))

                if rowid_count == 0:
                    """Если токен был удалён, то необходимо удалить соответствующий токен из модели (если он там есть)."""
                    self.update()
                elif rowid_count == 1:
                    """Если токен был обновлён или добавлен, то необходимо добавить или обновить имеющийся токен."""
                    self.update()
                else:
                    raise SystemError('Таблица {0} может содержать только 0 или 1 строку с rowid = \'{1}\', а получено {2} строк(-и)!'.format(MyConnection.TOKENS_TABLE, payload, rowid_count))

        db: QtSql.QSqlDatabase = MainConnection.getDatabase()
        driver = db.driver()
        driver.notification.connect(notificationSlot)

        subscribe_tokens_flag: bool = driver.subscribeToNotification(MyConnection.TOKENS_TABLE)
        assert subscribe_tokens_flag, 'Не удалось подписаться на уведомления об изменении таблицы {0}! driver.lastError().text(): \'{1}\'.'.format(MyConnection.TOKENS_TABLE, driver.lastError().text())

    def update(self):
        """Обновляет данные модели."""
        self.beginResetModel()
        self.__tokens.clear()
        db: QtSql.QSqlDatabase = MainConnection.getDatabase()
        if db.transaction():
            tokens_query = QtSql.QSqlQuery(db)
            tokens_prepare_flag: bool = tokens_query.prepare(self.__select_tokens_command)
            assert tokens_prepare_flag, tokens_query.lastError().text()
            tokens_exec_flag: bool = tokens_query.exec()
            assert tokens_exec_flag, tokens_query.lastError().text()

            while tokens_query.next():
                token: str = tokens_query.value('token')  # Токен.
                name: str = tokens_query.value('name')  # Название токена.

                '''------------------------Получение счетов------------------------'''
                accounts_query = QtSql.QSqlQuery(db)
                accounts_prepare_flag: bool = accounts_query.prepare(self.__select_accounts_command)
                assert accounts_prepare_flag, accounts_query.lastError().text()
                accounts_query.bindValue(':token', token)
                accounts_exec_flag: bool = accounts_query.exec()
                assert accounts_exec_flag, accounts_query.lastError().text()

                accounts: list[Account] = []  # Список аккаунтов.
                while accounts_query.next():
                    accounts.append(MyConnection.getCurrentAccount(accounts_query))
                '''----------------------------------------------------------------'''

                '''---------Получение unary-лимитов---------'''
                unary_limits_query = QtSql.QSqlQuery(db)
                unary_limits_prepare_flag: bool = unary_limits_query.prepare(self.__select_unary_limits_command)
                assert unary_limits_prepare_flag, unary_limits_query.lastError().text()
                unary_limits_query.bindValue(':token', token)
                unary_limits_exec_flag: bool = unary_limits_query.exec()
                assert unary_limits_exec_flag, unary_limits_query.lastError().text()

                unary_limits: list[UnaryLimit] = []  # Unary-лимиты.
                while unary_limits_query.next():
                    unary_limit: UnaryLimit = UnaryLimit(
                        limit_per_minute=unary_limits_query.value('limit_per_minute'),
                        methods=unary_limits_query.value('methods').split(', ')
                    )
                    unary_limits.append(unary_limit)
                '''-----------------------------------------'''

                '''---------Получение stream-соединений---------'''
                stream_limits_query = QtSql.QSqlQuery(db)
                stream_limits_prepare_flag: bool = stream_limits_query.prepare(self.__select_stream_limits_command)
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
                '''---------------------------------------------'''

                token_instance: TokenClass = TokenClass(
                    token=token,
                    name=name,
                    accounts=accounts,
                    unary_limits=[MyUnaryLimit(unary_limit) for unary_limit in unary_limits],
                    stream_limits=[MyStreamLimit(stream_limit) for stream_limit in stream_limits]
                )
                self.__tokens.append(token_instance)

            commit_flag: bool = db.commit()  # Фиксирует транзакцию в базу данных.
            assert commit_flag, db.lastError().text()
        else:
            raise SystemError('Не получилось начать транзакцию! db.lastError().text(): \'{0}\'.'.format(db.lastError().text()))
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = ...) -> int:
        return len(self.__tokens)

    def columnCount(self, parent: QModelIndex = ...) -> int:
        return 1

    def parent(self, child: QModelIndex) -> QModelIndex:
        return QModelIndex()

    def data(self, index: QModelIndex, role: int = ...) -> typing.Any:
        if role == Qt.ItemDataRole.UserRole:
            return self.__tokens[index.row()]
        elif role == Qt.ItemDataRole.DisplayRole:
            return self.__tokens[index.row()].token
        else:
            return QVariant()

    def index(self, row: int, column: int, parent: QModelIndex = ...) -> QModelIndex:
        return self.createIndex(row, column)

    def getTokenClass(self, row: int) -> TokenClass:
        """Возвращает TokenClass, соответствующий переданному номеру."""
        if 0 <= row < self.rowCount():
            return self.__tokens[row]
        else:
            raise ValueError('Некорректное значение row в getTokenClass() ({0})!'.format(row))

    def getTokens(self) -> list[TokenClass]:
        return self.__tokens

    # def addToken(self, token: TokenClass):
    #     """Добавляет токен."""
    #     row_count: int = self.rowCount()
    #     self.beginInsertRows(QModelIndex(), row_count, row_count)
    #     MainConnection.addNewToken(token)  # Добавляет новый токен в базу данных.
    #     self.__tokens.append(token)
    #     self.endInsertRows()
    #     new_index: QModelIndex = self.index(row=row_count, column=0, parent=QModelIndex())
    #     self.dataChanged.emit(new_index, new_index)  # Испускаем сигнал о том, что данные модели были изменены.

    # def deleteToken(self, token_index: QModelIndex) -> TokenClass:
    #     """Удаляет токен."""
    #     token_row: int = token_index.row()
    #     self.beginRemoveRows(QModelIndex(), token_row, token_row)
    #
    #     token: str = token_index.data(role=Qt.ItemDataRole.DisplayRole)
    #     MainConnection.deleteToken(token)  # Удаление токена из базы данных.
    #
    #     model_token: TokenClass = self.__tokens.pop(token_row)
    #     if not token == model_token.token:
    #         raise ValueError('Несоответствие удаляемого токена ({0} и {1})!'.format(token, model_token))
    #     self.endRemoveRows()
    #     self.dataChanged.emit(token_index, token_index)  # Испускаем сигнал о том, что данные модели были изменены.
    #     return model_token


class TokenListModel(QIdentityProxyModel):
    """Модель для отображения токенов в ComboBox'ах."""
    TOKEN_COMBOBOX_EMPTY_ELEMENT: str = 'Не выбран'

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
                return self.TOKEN_COMBOBOX_EMPTY_ELEMENT
            elif role == Qt.ItemDataRole.UserRole:
                return None
        else:
            source_row: int = index.row() - 1
            source_index: QModelIndex = self.sourceModel().index(source_row, 0)
            return source_index.data(role)

    def getToken(self, row: int) -> TokenClass | None:
        return None if row == 0 else self.sourceModel().getTokenClass(row - 1)
