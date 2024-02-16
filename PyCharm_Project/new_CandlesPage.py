import typing
from datetime import datetime, timedelta
from enum import Enum
from PyQt6 import QtCore, QtWidgets, QtSql
from tinkoff.invest import HistoricCandle, CandleInterval
from tinkoff.invest.utils import candle_interval_to_timedelta

from CandlesView import CandlesChartView
from Classes import TokenClass, MyConnection, TITLE_FONT, Column, print_slot, VERTICAL_SPACING
from LimitClasses import LimitPerMinuteSemaphore
from MyBondClass import MyBondClass
from MyDatabase import MainConnection
from MyDateTime import ifDateTimeIsEmpty, getUtcDateTime, getMoscowDateTime
from MyQuotation import MyQuotation
from MyRequests import MyResponse, RequestTryClass, getCandles
from MyShareClass import MyShareClass
from PagesClasses import GroupBox_InstrumentInfo, TitleLabel, ProgressBar_DataReceiving
from TokenModel import TokenListModel


class ComboBox_Token(QtWidgets.QComboBox):
    """ComboBox для выбора токена."""
    tokenSelected = QtCore.pyqtSignal(TokenClass)  # Сигнал испускается при выборе токена.
    tokenReset = QtCore.pyqtSignal()  # Сигнал испускается при сбросе токена.

    def __init__(self, token_model: TokenListModel, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)
        self.setEnabled(False)
        self.__token: TokenClass | None = None
        self.setModel(token_model)
        self.setCurrentIndex(0)  # "Не выбран".

        @QtCore.pyqtSlot(int)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
        def __setCurrentToken(index: int):
            self.token = self.model().getToken(index)

        self.currentIndexChanged.connect(__setCurrentToken)
        self.setEnabled(True)

    @property
    def token(self) -> TokenClass | None:
        return self.__token

    @token.setter
    def token(self, token: TokenClass | None):
        self.__token = token
        if self.__token is None:
            self.tokenReset.emit()
        else:
            self.tokenSelected.emit(self.__token)


class ComboBox_Interval(QtWidgets.QComboBox):
    """ComboBox для выбора интервала свечей."""
    intervalSelected = QtCore.pyqtSignal(CandleInterval)  # Сигнал испускается при выборе интервала свечей.
    DEFAULT_INDEX: int = 0

    class CandleIntervalModel(QtCore.QAbstractListModel):
        """Модель интервалов свечей."""

        def __init__(self, parent: QtCore.QObject | None = None):
            super().__init__(parent=parent)
            self.__intervals: tuple[tuple[str, CandleInterval], ...] = (
                ('Не определён', CandleInterval.CANDLE_INTERVAL_UNSPECIFIED),
                ('1 минута', CandleInterval.CANDLE_INTERVAL_1_MIN),
                ('2 минуты', CandleInterval.CANDLE_INTERVAL_2_MIN),
                ('3 минуты', CandleInterval.CANDLE_INTERVAL_3_MIN),
                ('5 минут', CandleInterval.CANDLE_INTERVAL_5_MIN),
                ('10 минут', CandleInterval.CANDLE_INTERVAL_10_MIN),
                ('15 минут', CandleInterval.CANDLE_INTERVAL_15_MIN),
                ('30 минут', CandleInterval.CANDLE_INTERVAL_30_MIN),
                ('1 час', CandleInterval.CANDLE_INTERVAL_HOUR),
                ('2 часа', CandleInterval.CANDLE_INTERVAL_2_HOUR),
                ('4 часа', CandleInterval.CANDLE_INTERVAL_4_HOUR),
                ('1 день', CandleInterval.CANDLE_INTERVAL_DAY),
                ('1 неделя', CandleInterval.CANDLE_INTERVAL_WEEK),
                ('1 месяц', CandleInterval.CANDLE_INTERVAL_MONTH)
            )

        def rowCount(self, parent: QtCore.QModelIndex = ...) -> int:
            return len(self.__intervals)

        def data(self, index: QtCore.QModelIndex, role: int = ...) -> typing.Any:
            if role == QtCore.Qt.ItemDataRole.DisplayRole:
                return self.__intervals[index.row()][0]
            elif role == QtCore.Qt.ItemDataRole.UserRole:
                return self.__intervals[index.row()][1]
            else:
                return QtCore.QVariant()

        def getInterval(self, index: int) -> CandleInterval:
            return self.__intervals[index][1]

    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)
        self.setEnabled(False)
        self.setModel(self.CandleIntervalModel(parent=self))
        self.setCurrentIndex(self.DEFAULT_INDEX)
        self.__interval: CandleInterval = self.model().getInterval(self.DEFAULT_INDEX)

        @QtCore.pyqtSlot(int)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
        def __setCurrentInterval(index: int):
            self.interval = self.model().getInterval(index)

        self.currentIndexChanged.connect(__setCurrentInterval)
        self.setEnabled(True)

    @property
    def interval(self) -> CandleInterval:
        return self.__interval

    @interval.setter
    def interval(self, interval: CandleInterval):
        self.__interval = interval
        self.intervalSelected.emit(self.interval)


class GroupBox_InstrumentSelection(QtWidgets.QGroupBox):
    """Панель выбора инструмента."""
    bondSelected: QtCore.pyqtSignal = QtCore.pyqtSignal(MyBondClass)  # Сигнал испускается при выборе облигации.
    shareSelected: QtCore.pyqtSignal = QtCore.pyqtSignal(MyShareClass)  # Сигнал испускается при выборе акции.
    instrumentReset: QtCore.pyqtSignal = QtCore.pyqtSignal()  # Сигнал испускается при сбросе выбранного инструмента.

    class ComboBox_Status(QtWidgets.QComboBox):
        """ComboBox для выбора статуса инструмента."""
        statusSelected = QtCore.pyqtSignal(str)  # Сигнал испускается при выборе статуса инструментов.
        statusReset = QtCore.pyqtSignal()  # Сигнал испускается при сбросе статуса инструментов.

        class TokenStatusesModel(QtCore.QAbstractListModel):
            """Модель статусов инструментов."""
            ANY_STATUS: str = 'Любой'
            PARAMETER: str = 'status'
            sql_command: str = '''SELECT DISTINCT \"{1}\" FROM \"{0}\" WHERE \"{0}\".\"token\" = :token;'''.format(
                MyConnection.INSTRUMENT_STATUS_TABLE,
                PARAMETER
            )

            def __init__(self, token: TokenClass | None = None, parent: QtCore.QObject | None = None):
                super().__init__(parent=parent)
                self.__instrument_statuses: list[str] = []
                self.__token: TokenClass | None = None
                self._update(token)

            def _update(self, token: TokenClass | None = None):
                """Обновляет данные модели."""
                self.beginResetModel()
                self.__token = token
                self.__instrument_statuses.clear()
                if self.__token is not None:
                    db: QtSql.QSqlDatabase = MainConnection.getDatabase()
                    transaction_flag: bool = db.transaction()  # Начинает транзакцию в базе данных.
                    if transaction_flag:
                        '''---------------Получение статусов инструментов из бд---------------'''
                        statuses_query = QtSql.QSqlQuery(db)
                        statuses_prepare_flag: bool = statuses_query.prepare(self.sql_command)
                        assert statuses_prepare_flag, statuses_query.lastError().text()
                        statuses_query.bindValue(':token', self.__token.token)
                        statuses_exec_flag: bool = statuses_query.exec()
                        assert statuses_exec_flag, statuses_query.lastError().text()
                        '''-------------------------------------------------------------------'''

                        while statuses_query.next():
                            self.__instrument_statuses.append(statuses_query.value(self.PARAMETER))

                        commit_flag: bool = db.commit()  # Фиксирует транзакцию в базу данных.
                        assert commit_flag, db.lastError().text()
                    else:
                        assert transaction_flag, db.lastError().text()
                self.endResetModel()

            def setToken(self, token: TokenClass | None):
                """Задаёт токен, который определяет отображаемый список статусов инструментов."""
                self._update(token)

            def rowCount(self, parent: QtCore.QModelIndex = ...) -> int:
                return len(self.__instrument_statuses) + 1

            def data(self, index: QtCore.QModelIndex, role: int = ...) -> typing.Any:
                if role == QtCore.Qt.ItemDataRole.DisplayRole:
                    row: int = index.row()
                    return self.ANY_STATUS if row == 0 else self.__instrument_statuses[row - 1]

            def getStatus(self, index: int) -> str | None:
                return None if index == 0 else self.__instrument_statuses[index - 1]

            def getStatusIndex(self, status: str) -> int | None:
                indexes_list: list[int] = [i for i, i_s in enumerate(self.__instrument_statuses) if i_s == status]
                indexes_count: int = len(indexes_list)
                if indexes_count == 0:
                    return None
                elif indexes_count == 1:
                    return indexes_list[0]
                else:
                    raise SystemError('Список статусов инструментов содержит несколько искомых элементов!')

        def __init__(self, token: TokenClass | None = None, parent: QtWidgets.QWidget | None = None):
            super().__init__(parent=parent)
            self.__current_status: str | None = None
            self.setModel(self.TokenStatusesModel(token=token, parent=self))
            self.__status_changed_connection: QtCore.QMetaObject.Connection = self.currentIndexChanged.connect(self.__onCurrentStatusChanged)
            self.__setCurrentStatus(None)

        @QtCore.pyqtSlot(int)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
        def __onCurrentStatusChanged(self, index: int):
            self.__current_status = self.model().getStatus(index)
            if self.__current_status is None:
                self.statusReset.emit()
            else:
                self.statusSelected.emit(self.__current_status)

        def __setCurrentStatus(self, status: str | None = None) -> bool:
            if status is None:
                self.setCurrentIndex(0)
                return True
            else:
                index: int | None = self.model().getStatusIndex(status)
                if index is None:
                    self.setCurrentIndex(0)
                    return False
                else:
                    self.setCurrentIndex(index)
                    return True

        def setToken(self, token: TokenClass | None = None):
            self.currentIndexChanged.disconnect(self.__status_changed_connection)
            self.model().setToken(token)
            if not self.__setCurrentStatus(self.__current_status):
                self.__current_status = None
                self.statusReset.emit()
            self.__status_changed_connection = self.currentIndexChanged.connect(self.__onCurrentStatusChanged)

        @property
        def status(self) -> str | None:
            return self.__current_status

    class ComboBox_InstrumentType(QtWidgets.QComboBox):
        """ComboBox для выбора типа инструментов."""
        typeChanged: QtCore.pyqtSignal = QtCore.pyqtSignal(str)  # Сигнал испускается при изменении выбранного типа.
        typeReset: QtCore.pyqtSignal = QtCore.pyqtSignal()  # Сигнал испускается при сбросе выбранного типа.

        class InstrumentsTypeModel(QtCore.QAbstractListModel):
            """Модель типов инструментов."""
            ANY_TYPE: str = 'Любой'
            PARAMETER: str = 'instrument_type'

            def __init__(self, token: TokenClass | None = None, status: str | None = None, parent: QtCore.QObject | None = None):
                super().__init__(parent=parent)
                self.__types: list[str] = []
                self.__token: TokenClass | None = token
                self.__status: str | None = status
                self._update()

            def rowCount(self, parent: QtCore.QModelIndex = ...) -> int:
                return len(self.__types) + 1

            def data(self, index: QtCore.QModelIndex, role: int = ...) -> typing.Any:
                if role == QtCore.Qt.ItemDataRole.DisplayRole:
                    row: int = index.row()
                    return self.ANY_TYPE if row == 0 else self.__types[row - 1]

            def getInstrumentType(self, index: int) -> str | None:
                return None if index == 0 else self.__types[index - 1]

            def getInstrumentTypeIndex(self, instrument_type: str) -> int | None:
                indexes_list: list[int] = [i for i, i_type in enumerate(self.__types) if i_type == instrument_type]
                indexes_count: int = len(indexes_list)
                if indexes_count == 0:
                    return None
                elif indexes_count == 1:
                    return indexes_list[0]
                else:
                    raise SystemError('Список типов инструментов содержит несколько искомых элементов!')

            def _update(self):
                """Обновляет данные модели."""
                self.beginResetModel()

                self.__types.clear()
                if self.__token is None:
                    assert self.__status is None
                    '''Находим типы всех имеющихся инструментов.'''
                    sql_command: str = '''SELECT DISTINCT \"{1}\" FROM \"{0}\";'''.format(
                        MyConnection.INSTRUMENT_UIDS_TABLE,
                        self.PARAMETER
                    )

                    db: QtSql.QSqlDatabase = MainConnection.getDatabase()
                    transaction_flag: bool = db.transaction()  # Начинает транзакцию в базе данных.
                    if transaction_flag:
                        types_query = QtSql.QSqlQuery(db)
                        types_prepare_flag: bool = types_query.prepare(sql_command)
                        assert types_prepare_flag, types_query.lastError().text()
                        types_exec_flag: bool = types_query.exec()
                        assert types_exec_flag, types_query.lastError().text()

                        while types_query.next():
                            self.__types.append(types_query.value(self.PARAMETER))

                        commit_flag: bool = db.commit()  # Фиксирует транзакцию в базу данных.
                        assert commit_flag, db.lastError().text()
                    else:
                        assert transaction_flag, db.lastError().text()
                else:
                    if self.__status is None:
                        """Находим все типы инструментов, полученных с помощью переданного токена."""
                        select_uids_str: str = '''SELECT DISTINCT {0}.\"uid\" FROM {0} WHERE {0}.\"token\" = :token'''.format(
                            '\"{0}\"'.format(MyConnection.INSTRUMENT_STATUS_TABLE)
                        )
                        sql_command: str = '''SELECT DISTINCT {0}.\"{1}\" FROM {0}, ({2}) AS {3} WHERE {0}.\"uid\" = {3}.\"uid\";'''.format(
                            '\"{0}\"'.format(MyConnection.INSTRUMENT_UIDS_TABLE),
                            self.PARAMETER,
                            select_uids_str,
                            '\"S\"'
                        )

                        db: QtSql.QSqlDatabase = MainConnection.getDatabase()
                        transaction_flag: bool = db.transaction()  # Начинает транзакцию в базе данных.
                        if transaction_flag:
                            types_query = QtSql.QSqlQuery(db)
                            types_prepare_flag: bool = types_query.prepare(sql_command)
                            assert types_prepare_flag, types_query.lastError().text()
                            types_query.bindValue(':token', self.__token.token)
                            types_exec_flag: bool = types_query.exec()
                            assert types_exec_flag, types_query.lastError().text()

                            while types_query.next():
                                self.__types.append(types_query.value(self.PARAMETER))

                            commit_flag: bool = db.commit()  # Фиксирует транзакцию в базу данных.
                            assert commit_flag, db.lastError().text()
                        else:
                            assert transaction_flag, db.lastError().text()
                    else:
                        """Находим все типы инструментов, соответствующих текущим токену и статусу."""
                        select_uids_str: str = '''SELECT {0}.\"uid\" FROM {0} WHERE {0}.\"token\" = :token AND {0}.\"status\" = :status'''.format(
                            '\"{0}\"'.format(MyConnection.INSTRUMENT_STATUS_TABLE)
                        )
                        sql_command: str = '''SELECT DISTINCT {0}.\"{1}\" FROM {0}, ({2}) AS {3} WHERE {0}.\"uid\" = {3}.\"uid\";'''.format(
                            '\"{0}\"'.format(MyConnection.INSTRUMENT_UIDS_TABLE),
                            self.PARAMETER,
                            select_uids_str,
                            '\"S\"'
                        )

                        db: QtSql.QSqlDatabase = MainConnection.getDatabase()
                        transaction_flag: bool = db.transaction()  # Начинает транзакцию в базе данных.
                        if transaction_flag:
                            types_query = QtSql.QSqlQuery(db)
                            types_prepare_flag: bool = types_query.prepare(sql_command)
                            assert types_prepare_flag, types_query.lastError().text()
                            types_query.bindValue(':token', self.__token.token)
                            types_query.bindValue(':status', self.__status)
                            types_exec_flag: bool = types_query.exec()
                            assert types_exec_flag, types_query.lastError().text()

                            while types_query.next():
                                self.__types.append(types_query.value(self.PARAMETER))

                            commit_flag: bool = db.commit()  # Фиксирует транзакцию в базу данных.
                            assert commit_flag, db.lastError().text()
                        else:
                            assert transaction_flag, db.lastError().text()

                self.endResetModel()

            def setToken(self, token: TokenClass | None):
                self.__token = token
                self._update()

            def setStatus(self, status: str | None):
                self.__status = status
                self._update()

        def __init__(self, token: TokenClass | None = None, status: str | None = None, parent: QtWidgets.QWidget | None = None):
            super().__init__(parent=parent)
            self.__current_instrument_type: str | None = None
            self.setModel(self.InstrumentsTypeModel(token=token, status=status, parent=self))
            self.__type_changed_connection: QtCore.QMetaObject.Connection = self.currentIndexChanged.connect(self.__onInstrumentTypeChanged)
            self.__setCurrentType(None)

        @QtCore.pyqtSlot(int)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
        def __onInstrumentTypeChanged(self, index: int):
            self.__current_instrument_type = self.model().getInstrumentType(index)
            if self.__current_instrument_type is None:
                self.typeReset.emit()
            else:
                self.typeChanged.emit(self.__current_instrument_type)

        def __setCurrentType(self, instrument_type: str | None = None) -> bool:
            if instrument_type is None:
                self.setCurrentIndex(0)
                return True
            else:
                index: int | None = self.model().getInstrumentTypeIndex(instrument_type)
                if index is None:
                    self.setCurrentIndex(0)
                    return False
                else:
                    self.setCurrentIndex(index)
                    return True

        def setToken(self, token: TokenClass | None = None):
            self.currentIndexChanged.disconnect(self.__type_changed_connection)
            self.model().setToken(token)
            if not self.__setCurrentType(self.__current_instrument_type):
                self.__current_instrument_type = None
                self.typeReset.emit()
            self.__type_changed_connection = self.currentIndexChanged.connect(self.__onInstrumentTypeChanged)

        def setStatus(self, status: str | None = None):
            self.currentIndexChanged.disconnect(self.__type_changed_connection)
            self.model().setStatus(status)
            if not self.__setCurrentType(self.__current_instrument_type):
                self.__current_instrument_type = None
                self.typeReset.emit()
            self.__type_changed_connection = self.currentIndexChanged.connect(self.__onInstrumentTypeChanged)

        @property
        def instrument_type(self) -> str | None:
            return self.__current_instrument_type

    class ComboBox_Instrument(QtWidgets.QComboBox):
        """ComboBox для выбора инструмента."""
        instrumentChanged: QtCore.pyqtSignal = QtCore.pyqtSignal(str)  # Сигнал испускается при изменении выбранного типа.
        instrumentReset: QtCore.pyqtSignal = QtCore.pyqtSignal()  # Сигнал испускается при сбросе выбранного типа.
        instrumentsCountChanged: QtCore.pyqtSignal = QtCore.pyqtSignal(int)

        class InstrumentsModel(QtCore.QAbstractListModel):
            """Модель инструментов."""
            EMPTY: str = 'Не выбран'

            def __init__(self, token: TokenClass | None = None, status: str | None = None, instrument_type: str | None = None, parent: QtCore.QObject | None = None):
                super().__init__(parent=parent)
                self.__instruments: list[(str, str)] = []
                self.__token: TokenClass | None = None
                self.__status: str | None = None
                self.__type: str | None = None
                self._update(token, status, instrument_type)

            def rowCount(self, parent: QtCore.QModelIndex = ...) -> int:
                return len(self.__instruments) + 1

            def getInstrumentsCount(self) -> int:
                """Возвращает количество инструментов в модели."""
                return len(self.__instruments)

            @staticmethod
            def __show(item: (str, str)) -> str:
                return '{0} | {1}'.format(item[0], item[1])

            def data(self, index: QtCore.QModelIndex, role: int = ...) -> typing.Any:
                if role == QtCore.Qt.ItemDataRole.DisplayRole:
                    row: int = index.row()
                    return self.EMPTY if row == 0 else self.__show(self.__instruments[row - 1])

            def _update(self, token: TokenClass | None, status: str | None, instrument_type: str | None):
                """Обновляет данные модели."""
                self.beginResetModel()

                self.__token = token
                self.__status = status
                self.__type = instrument_type

                self.__instruments.clear()
                if instrument_type is None:
                    if token is None:
                        assert status is None
                        """Если токен не выбран (статус, соответственно, тоже), то получаем все инструменты."""
                        sql_command: str = '''SELECT \"name\", \"uid\" FROM \"{0}\" UNION ALL SELECT \"name\", \"uid\" 
                        FROM \"{1}\" ORDER BY \"name\";'''.format(MyConnection.SHARES_TABLE, MyConnection.BONDS_TABLE)

                        db: QtSql.QSqlDatabase = MainConnection.getDatabase()
                        if db.transaction():
                            instruments_query = QtSql.QSqlQuery(db)
                            instruments_prepare_flag: bool = instruments_query.prepare(sql_command)
                            assert instruments_prepare_flag, instruments_query.lastError().text()
                            instruments_exec_flag: bool = instruments_query.exec()
                            assert instruments_exec_flag, instruments_query.lastError().text()

                            while instruments_query.next():
                                name: str = instruments_query.value('name')
                                uid: str = instruments_query.value('uid')
                                self.__instruments.append((uid, name))

                            commit_flag: bool = db.commit()  # Фиксирует транзакцию в базу данных.
                            assert commit_flag, db.lastError().text()
                        else:
                            raise SystemError('Не получилось начать транзакцию! db.lastError().text(): \'{0}\'.'.format(db.lastError().text()))
                    else:
                        if status is None:
                            uids_command_str: str = '''SELECT \"SIUT\".\"uid\" FROM 
                            (SELECT \"uid\" FROM {0} WHERE \"instrument_type\" = {2}) AS \"SIUT\", 
                            (SELECT DISTINCT \"uid\" FROM {1} WHERE \"token\" = :token) AS \"SIST\"
                            WHERE \"SIUT\".\"uid\" = \"SIST\".\"uid\"'''

                            share_uids_command: str = uids_command_str.format(
                                '\"{0}\"'.format(MyConnection.INSTRUMENT_UIDS_TABLE),
                                '\"{0}\"'.format(MyConnection.INSTRUMENT_STATUS_TABLE),
                                '\'share\''
                            )

                            shares_command: str = 'SELECT {1}.\"name\", {2}.\"uid\" FROM ({0}) AS {2} INNER JOIN {1} ON {1}.\"uid\" = {2}.\"uid\"'.format(
                                share_uids_command,
                                '\"{0}\"'.format(MyConnection.SHARES_TABLE),
                                '\"SU\"'
                            )

                            bond_uids_command: str = uids_command_str.format(
                                '\"{0}\"'.format(MyConnection.INSTRUMENT_UIDS_TABLE),
                                '\"{0}\"'.format(MyConnection.INSTRUMENT_STATUS_TABLE),
                                '\'bond\''
                            )

                            bonds_command: str = 'SELECT {1}.\"name\", {2}.\"uid\" FROM ({0}) AS {2} INNER JOIN {1} ON {1}.\"uid\" = {2}.\"uid\"'.format(
                                bond_uids_command,
                                '\"{0}\"'.format(MyConnection.BONDS_TABLE),
                                '\"BU\"'
                            )

                            sql_command: str = '{0} UNION ALL {1} ORDER BY \"name\";'.format(
                                shares_command,
                                bonds_command
                            )

                            db: QtSql.QSqlDatabase = MainConnection.getDatabase()
                            if db.transaction():
                                instruments_query = QtSql.QSqlQuery(db)
                                instruments_prepare_flag: bool = instruments_query.prepare(sql_command)
                                assert instruments_prepare_flag, instruments_query.lastError().text()
                                instruments_query.bindValue(':token', token.token)
                                instruments_exec_flag: bool = instruments_query.exec()
                                assert instruments_exec_flag, instruments_query.lastError().text()

                                while instruments_query.next():
                                    name: str = instruments_query.value('name')
                                    uid: str = instruments_query.value('uid')
                                    self.__instruments.append((uid, name))

                                commit_flag: bool = db.commit()  # Фиксирует транзакцию в базу данных.
                                assert commit_flag, db.lastError().text()
                            else:
                                raise SystemError('Не получилось начать транзакцию! db.lastError().text(): \'{0}\'.'.format(db.lastError().text()))
                        else:
                            uids_command_str: str = '''SELECT \"SIUT\".\"uid\" FROM 
                            (SELECT {0}.\"uid\" FROM {0} WHERE {0}.\"instrument_type\" = {2}) AS \"SIUT\", 
                            (SELECT DISTINCT {1}.\"uid\" FROM {1} WHERE {1}.\"token\" = :token AND {1}.\"status\" = :status) AS \"SIST\"
                            WHERE \"SIUT\".\"uid\" = \"SIST\".\"uid\"'''

                            share_uids_command: str = uids_command_str.format(
                                '\"{0}\"'.format(MyConnection.INSTRUMENT_UIDS_TABLE),
                                '\"{0}\"'.format(MyConnection.INSTRUMENT_STATUS_TABLE),
                                '\'share\''
                            )

                            shares_command: str = 'SELECT {1}.\"name\", {2}.\"uid\" FROM ({0}) AS {2} INNER JOIN {1} ON {1}.\"uid\" = {2}.\"uid\"'.format(
                                share_uids_command,
                                '\"{0}\"'.format(MyConnection.SHARES_TABLE),
                                '\"SU\"'
                            )

                            bond_uids_command: str = uids_command_str.format(
                                '\"{0}\"'.format(MyConnection.INSTRUMENT_UIDS_TABLE),
                                '\"{0}\"'.format(MyConnection.INSTRUMENT_STATUS_TABLE),
                                '\'bond\''
                            )

                            bonds_command: str = 'SELECT {1}.\"name\", {2}.\"uid\" FROM ({0}) AS {2} INNER JOIN {1} ON {1}.\"uid\" = {2}.\"uid\"'.format(
                                bond_uids_command,
                                '\"{0}\"'.format(MyConnection.BONDS_TABLE),
                                '\"BU\"'
                            )

                            sql_command: str = '{0} UNION ALL {1} ORDER BY \"name\";'.format(
                                shares_command,
                                bonds_command
                            )

                            db: QtSql.QSqlDatabase = MainConnection.getDatabase()
                            if db.transaction():
                                instruments_query = QtSql.QSqlQuery(db)
                                instruments_prepare_flag: bool = instruments_query.prepare(sql_command)
                                assert instruments_prepare_flag, instruments_query.lastError().text()
                                instruments_query.bindValue(':token', token.token)
                                instruments_query.bindValue(':status', status)
                                instruments_exec_flag: bool = instruments_query.exec()
                                assert instruments_exec_flag, instruments_query.lastError().text()

                                while instruments_query.next():
                                    name: str = instruments_query.value('name')
                                    uid: str = instruments_query.value('uid')
                                    self.__instruments.append((uid, name))

                                commit_flag: bool = db.commit()  # Фиксирует транзакцию в базу данных.
                                assert commit_flag, db.lastError().text()
                            else:
                                raise SystemError('Не получилось начать транзакцию! db.lastError().text(): \'{0}\'.'.format(db.lastError().text()))
                else:
                    if token is None:
                        assert status is None
                        """Если токен не выбран (статус, соответственно, тоже), то получаем все инструменты выбранного типа."""
                        instruments_select: str = 'SELECT \"name\", \"uid\" FROM \"{0}\" ORDER BY \"name\";'
                        if instrument_type == 'share':
                            sql_command: str = instruments_select.format(MyConnection.SHARES_TABLE)
                        elif instrument_type == 'bond':
                            sql_command: str = instruments_select.format(MyConnection.BONDS_TABLE)
                        else:
                            raise ValueError('Неизвестный тип инструмента ({0})!'.format(instrument_type))

                        db: QtSql.QSqlDatabase = MainConnection.getDatabase()
                        if db.transaction():
                            instruments_query = QtSql.QSqlQuery(db)
                            instruments_prepare_flag: bool = instruments_query.prepare(sql_command)
                            assert instruments_prepare_flag, instruments_query.lastError().text()
                            instruments_exec_flag: bool = instruments_query.exec()
                            assert instruments_exec_flag, instruments_query.lastError().text()

                            while instruments_query.next():
                                name: str = instruments_query.value('name')
                                uid: str = instruments_query.value('uid')
                                self.__instruments.append((uid, name))

                            commit_flag: bool = db.commit()  # Фиксирует транзакцию в базу данных.
                            assert commit_flag, db.lastError().text()
                        else:
                            raise SystemError('Не получилось начать транзакцию! db.lastError().text(): \'{0}\'.'.format(db.lastError().text()))
                    else:
                        if status is None:
                            uids_select: str = 'SELECT DISTINCT \"uid\" FROM \"{0}\" WHERE \"token\" = :token'.format(MyConnection.INSTRUMENT_STATUS_TABLE)
                            instruments_select: str = 'SELECT {2}.\"name\", {2}.\"uid\" FROM ({0}) AS {1}, {2} WHERE {1}.\"uid\" = {2}.\"uid\" ORDER BY \"name\";'

                            if instrument_type == 'share':
                                sql_command: str = instruments_select.format(
                                    uids_select,
                                    '\"S\"',
                                    '\"{0}\"'.format(MyConnection.SHARES_TABLE)
                                )
                            elif instrument_type == 'bond':
                                sql_command: str = instruments_select.format(
                                    uids_select,
                                    '\"B\"',
                                    '\"{0}\"'.format(MyConnection.BONDS_TABLE)
                                )
                            else:
                                raise ValueError('Неизвестный тип инструмента ({0})!'.format(instrument_type))

                            db: QtSql.QSqlDatabase = MainConnection.getDatabase()
                            if db.transaction():
                                instruments_query = QtSql.QSqlQuery(db)
                                instruments_prepare_flag: bool = instruments_query.prepare(sql_command)
                                assert instruments_prepare_flag, instruments_query.lastError().text()
                                instruments_query.bindValue(':token', token.token)
                                instruments_exec_flag: bool = instruments_query.exec()
                                assert instruments_exec_flag, instruments_query.lastError().text()

                                while instruments_query.next():
                                    name: str = instruments_query.value('name')
                                    uid: str = instruments_query.value('uid')
                                    self.__instruments.append((uid, name))

                                commit_flag: bool = db.commit()  # Фиксирует транзакцию в базу данных.
                                assert commit_flag, db.lastError().text()
                            else:
                                raise SystemError('Не получилось начать транзакцию! db.lastError().text(): \'{0}\'.'.format(db.lastError().text()))
                        else:
                            uids_select: str = 'SELECT \"uid\" FROM \"{0}\" WHERE \"token\" = :token AND \"status\" = :status'.format(MyConnection.INSTRUMENT_STATUS_TABLE)
                            instruments_select: str = 'SELECT {2}.\"name\", {2}.\"uid\" FROM ({0}) AS {1}, {2} WHERE {2}.\"uid\" = {1}.\"uid\" ORDER BY \"name\";'

                            if instrument_type == 'share':
                                sql_command: str = instruments_select.format(
                                    uids_select,
                                    '\"S\"',
                                    '\"{0}\"'.format(MyConnection.SHARES_TABLE)
                                )
                            elif instrument_type == 'bond':
                                sql_command: str = instruments_select.format(
                                    uids_select,
                                    '\"B\"',
                                    '\"{0}\"'.format(MyConnection.BONDS_TABLE)
                                )
                            else:
                                raise ValueError('Неизвестный тип инструмента ({0})!'.format(instrument_type))

                            db: QtSql.QSqlDatabase = MainConnection.getDatabase()
                            if db.transaction():
                                instruments_query = QtSql.QSqlQuery(db)
                                instruments_prepare_flag: bool = instruments_query.prepare(sql_command)
                                assert instruments_prepare_flag, instruments_query.lastError().text()
                                instruments_query.bindValue(':token', token.token)
                                instruments_query.bindValue(':status', status)
                                instruments_exec_flag: bool = instruments_query.exec()
                                assert instruments_exec_flag, instruments_query.lastError().text()

                                while instruments_query.next():
                                    name: str = instruments_query.value('name')
                                    uid: str = instruments_query.value('uid')
                                    self.__instruments.append((uid, name))

                                commit_flag: bool = db.commit()  # Фиксирует транзакцию в базу данных.
                                assert commit_flag, db.lastError().text()
                            else:
                                raise SystemError('Не получилось начать транзакцию! db.lastError().text(): \'{0}\'.'.format(db.lastError().text()))

                self.endResetModel()

            def getUid(self, index: int) -> str | None:
                return None if index == 0 else self.__instruments[index - 1][0]

            def getItem(self, index: int) -> tuple[str, str] | None:
                return None if index == 0 else self.__instruments[index - 1]

            def getItemIndex(self, item: tuple[str, str]) -> int | None:
                indexes_list: list[int] = [i for i, itm in enumerate(self.__instruments) if itm[0] == item[0] and itm[1] == item[1]]
                items_count: int = len(indexes_list)
                if items_count == 0:
                    return None
                elif items_count == 1:
                    return indexes_list[0] + 1
                else:
                    raise SystemError('Список инструментов модели содержит несколько искомых элементов (uid = \'{0}\', name = \'{1}\')!'.format(item[0], item[1]))

            def setToken(self, token: TokenClass | None):
                self._update(token, self.__status, self.__type)

            def setStatus(self, status: str | None):
                self._update(self.__token, status, self.__type)

            def setType(self, instrument_type: str | None):
                self._update(self.__token, self.__status, instrument_type)

        def __init__(self, token: TokenClass | None = None, status: str | None = None, instrument_type: str | None = None, parent: QtWidgets.QWidget | None = None):
            super().__init__(parent=parent)
            self.__current_item: tuple[str, str] | None = None
            self.__instruments_count: int = 0  # Количество инструментов.
            self.setModel(self.InstrumentsModel(token=token, status=status, instrument_type=instrument_type, parent=self))
            self.__instrument_changed_connection: QtCore.QMetaObject.Connection = self.currentIndexChanged.connect(self.__onInstrumentChanged)
            self.instruments_count = self.model().getInstrumentsCount()
            self.__setCurrentItem(None)

        @QtCore.pyqtSlot(int)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
        def __onInstrumentChanged(self, index: int):
            self.__current_item = self.model().getItem(index)
            if self.__current_item is None:
                self.instrumentReset.emit()
            else:
                self.instrumentChanged.emit(self.__current_item[0])

        def __setCurrentItem(self, item: tuple[str, str] | None = None) -> bool:
            if item is None:
                self.setCurrentIndex(0)
                return True
            else:
                index: int | None = self.model().getItemIndex(item)
                if index is None:
                    self.setCurrentIndex(0)
                    return False
                else:
                    self.setCurrentIndex(index)
                    return True

        def setToken(self, token: TokenClass | None = None):
            self.currentIndexChanged.disconnect(self.__instrument_changed_connection)
            self.model().setToken(token)
            if not self.__setCurrentItem(self.__current_item):
                self.__current_item = None
                self.instrumentReset.emit()
            self.instruments_count = self.model().getInstrumentsCount()
            self.__instrument_changed_connection = self.currentIndexChanged.connect(self.__onInstrumentChanged)

        def setStatus(self, status: str | None = None):
            self.currentIndexChanged.disconnect(self.__instrument_changed_connection)
            self.model().setStatus(status)
            if not self.__setCurrentItem(self.__current_item):
                self.__current_item = None
                self.instrumentReset.emit()
            self.instruments_count = self.model().getInstrumentsCount()
            self.__instrument_changed_connection = self.currentIndexChanged.connect(self.__onInstrumentChanged)

        def setType(self, instrument_type: str | None = None):
            self.currentIndexChanged.disconnect(self.__instrument_changed_connection)
            self.model().setType(instrument_type)
            if not self.__setCurrentItem(self.__current_item):
                self.__current_item = None
                self.instrumentReset.emit()
            self.instruments_count = self.model().getInstrumentsCount()
            self.__instrument_changed_connection = self.currentIndexChanged.connect(self.__onInstrumentChanged)

        @property
        def instruments_count(self) -> int:
            return self.__instruments_count

        @instruments_count.setter
        def instruments_count(self, count: int):
            if self.__instruments_count != count:
                self.__instruments_count = count
                self.instrumentsCountChanged.emit(self.__instruments_count)

        @property
        def uid(self) -> str | None:
            return None if self.__current_item is None else self.__current_item[0]

    def __init__(self, token_model: TokenListModel, parent: QtWidgets.QWidget | None = None):
        self.__current_instrument: MyShareClass | MyBondClass | None = None
        super().__init__(parent=parent)

        verticalLayout_main = QtWidgets.QVBoxLayout(self)
        verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        verticalLayout_main.setSpacing(2)

        '''-----------------------Строка заголовка-----------------------'''
        horizontalLayout_title = QtWidgets.QHBoxLayout(self)
        horizontalLayout_title.setSpacing(0)

        horizontalLayout_title.addItem(QtWidgets.QSpacerItem(10, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum))
        horizontalLayout_title.addItem(QtWidgets.QSpacerItem(0, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum))

        label_title = QtWidgets.QLabel(text='ВЫБОР ИНСТРУМЕНТА', parent=self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(label_title.sizePolicy().hasHeightForWidth())
        label_title.setSizePolicy(sizePolicy)
        label_title.setFont(TITLE_FONT)
        label_title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)
        horizontalLayout_title.addWidget(label_title)

        self.label_count = QtWidgets.QLabel(parent=self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_count.sizePolicy().hasHeightForWidth())
        self.label_count.setSizePolicy(sizePolicy)
        self.label_count.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        horizontalLayout_title.addWidget(self.label_count)

        horizontalLayout_title.addItem(QtWidgets.QSpacerItem(10, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum))

        verticalLayout_main.addLayout(horizontalLayout_title)
        '''--------------------------------------------------------------'''

        '''---------------------Строка выбора токена---------------------'''
        horizontalLayout_token = QtWidgets.QHBoxLayout(self)
        horizontalLayout_token.setSpacing(0)

        horizontalLayout_token.addWidget(QtWidgets.QLabel(text='Токен:', parent=self))
        horizontalLayout_token.addSpacerItem(QtWidgets.QSpacerItem(4, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum))

        self.comboBox_token = ComboBox_Token(token_model=token_model, parent=self)
        horizontalLayout_token.addWidget(self.comboBox_token)

        horizontalLayout_token.addSpacerItem(QtWidgets.QSpacerItem(0, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum))

        verticalLayout_main.addLayout(horizontalLayout_token)
        '''--------------------------------------------------------------'''

        '''---------------Строка выбора статуса инструмента---------------'''
        horizontalLayout_status = QtWidgets.QHBoxLayout(self)
        horizontalLayout_status.setSpacing(0)

        horizontalLayout_status.addWidget(QtWidgets.QLabel(text='Статус:', parent=self))
        horizontalLayout_status.addSpacerItem(QtWidgets.QSpacerItem(4, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum))

        self.comboBox_status = self.ComboBox_Status(token=self.token, parent=self)
        self.comboBox_token.tokenSelected.connect(self.comboBox_status.setToken)
        self.comboBox_token.tokenReset.connect(self.comboBox_status.setToken)
        horizontalLayout_status.addWidget(self.comboBox_status)

        horizontalLayout_status.addSpacerItem(QtWidgets.QSpacerItem(0, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum))

        verticalLayout_main.addLayout(horizontalLayout_status)
        '''---------------------------------------------------------------'''

        '''------------Строка выбора типа инструмента------------'''
        horizontalLayout_instrument_type = QtWidgets.QHBoxLayout(self)
        horizontalLayout_instrument_type.setSpacing(0)

        horizontalLayout_instrument_type.addWidget(QtWidgets.QLabel(text='Тип инструмента:', parent=self))
        horizontalLayout_instrument_type.addSpacerItem(QtWidgets.QSpacerItem(4, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum))

        self.comboBox_instrument_type = self.ComboBox_InstrumentType(token=self.token, status=self.status, parent=self)
        self.comboBox_token.tokenSelected.connect(self.comboBox_instrument_type.setToken)
        self.comboBox_token.tokenReset.connect(self.comboBox_instrument_type.setToken)
        self.comboBox_status.statusSelected.connect(self.comboBox_instrument_type.setStatus)
        self.comboBox_status.statusReset.connect(self.comboBox_instrument_type.setStatus)
        horizontalLayout_instrument_type.addWidget(self.comboBox_instrument_type)

        horizontalLayout_instrument_type.addSpacerItem(QtWidgets.QSpacerItem(0, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum))

        verticalLayout_main.addLayout(horizontalLayout_instrument_type)
        '''------------------------------------------------------'''

        '''---------------Строка выбора инструмента---------------'''
        horizontalLayout_instrument = QtWidgets.QHBoxLayout(self)
        horizontalLayout_instrument.setSpacing(0)

        horizontalLayout_instrument.addWidget(QtWidgets.QLabel(text='Инструмент:', parent=self))
        horizontalLayout_instrument.addSpacerItem(QtWidgets.QSpacerItem(4, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum))

        self.comboBox_instrument = self.ComboBox_Instrument(token=self.token, status=self.status, instrument_type=self.instrument_type, parent=self)
        self.label_count.setText(str(self.comboBox_instrument.instruments_count))
        self.comboBox_instrument.instrumentChanged.connect(self.__onCurrentInstrumentChanged)
        self.comboBox_instrument.instrumentReset.connect(self.__onCurrentInstrumentChanged)
        self.comboBox_instrument.instrumentsCountChanged.connect(lambda count: self.label_count.setText(str(count)))
        self.comboBox_token.tokenSelected.connect(self.comboBox_instrument.setToken)
        self.comboBox_token.tokenReset.connect(self.comboBox_instrument.setToken)
        self.comboBox_status.statusSelected.connect(self.comboBox_instrument.setStatus)
        self.comboBox_status.statusReset.connect(self.comboBox_instrument.setStatus)
        self.comboBox_instrument_type.typeChanged.connect(self.comboBox_instrument.setType)
        self.comboBox_instrument_type.typeReset.connect(self.comboBox_instrument.setType)
        horizontalLayout_instrument.addWidget(self.comboBox_instrument)

        horizontalLayout_instrument.addSpacerItem(QtWidgets.QSpacerItem(0, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum))

        verticalLayout_main.addLayout(horizontalLayout_instrument)
        '''-------------------------------------------------------'''

        verticalLayout_main.addStretch(1)

    @property
    def token(self) -> TokenClass | None:
        return self.comboBox_token.token

    @property
    def status(self) -> str | None:
        return self.comboBox_status.status

    @property
    def instrument_type(self) -> str | None:
        return self.comboBox_instrument_type.instrument_type

    @property
    def uid(self) -> str | None:
        return self.comboBox_instrument.uid

    @property
    def instrument(self) -> MyShareClass | MyBondClass | None:
        return self.__current_instrument

    def __onCurrentInstrumentChanged(self, uid: str | None = None):
        if uid is None:
            if self.__current_instrument is not None:
                self.__current_instrument = None
                self.instrumentReset.emit()
        else:
            instrument: MyShareClass | MyBondClass | None = MainConnection.getMyInstrument(uid)
            self.__current_instrument = instrument
            if type(self.__current_instrument) == MyBondClass:
                self.bondSelected.emit(self.__current_instrument)
            elif type(self.__current_instrument) == MyShareClass:
                self.shareSelected.emit(self.__current_instrument)
            else:
                '''Такого не должно происходить.'''
                if self.__current_instrument is not None:
                    self.__current_instrument = None
                    self.instrumentReset.emit()


def getMaxInterval(interval: CandleInterval) -> timedelta:
    """Возвращает максимальный временной интервал, соответствующий переданному интервалу."""
    match interval:
        case CandleInterval.CANDLE_INTERVAL_UNSPECIFIED:
            raise ValueError('Интервал не определён.')
        case CandleInterval.CANDLE_INTERVAL_1_MIN:
            return timedelta(days=1)
        case CandleInterval.CANDLE_INTERVAL_5_MIN:
            return timedelta(days=1)
        case CandleInterval.CANDLE_INTERVAL_15_MIN:
            return timedelta(days=1)
        case CandleInterval.CANDLE_INTERVAL_HOUR:
            return timedelta(weeks=1)
        case CandleInterval.CANDLE_INTERVAL_DAY:
            '''В timedelta нельзя указать один год, можно указать 365 дней. Но как быть с високосным годом?'''
            return timedelta(days=365)
        case CandleInterval.CANDLE_INTERVAL_2_MIN:
            return timedelta(days=1)
        case CandleInterval.CANDLE_INTERVAL_3_MIN:
            return timedelta(days=1)
        case CandleInterval.CANDLE_INTERVAL_10_MIN:
            return timedelta(days=1)
        case CandleInterval.CANDLE_INTERVAL_30_MIN:
            return timedelta(days=2)
        case CandleInterval.CANDLE_INTERVAL_2_HOUR:
            '''В timedelta нельзя указать один месяц, можно указать 31 дней. Но как быть с более короткими месяцами?'''
            return timedelta(days=31)
        case CandleInterval.CANDLE_INTERVAL_4_HOUR:
            '''В timedelta нельзя указать один месяц, можно указать 31 дней. Но как быть с более короткими месяцами?'''
            return timedelta(days=31)
        case CandleInterval.CANDLE_INTERVAL_WEEK:
            '''В timedelta нельзя указать два года, можно указать 2x365 дней. Но как быть с високосными годами?'''
            return timedelta(days=(2 * 365))
        case CandleInterval.CANDLE_INTERVAL_MONTH:
            '''В timedelta нельзя указать десять лет, можно указать 10x365 дней. Но как быть с високосными годами?'''
            return timedelta(days=(10 * 365))
        case _:
            raise ValueError('Некорректный временной интервал свечей!')


class GroupBox_CandlesReceiving(QtWidgets.QGroupBox):
    class CandlesThread(QtCore.QThread):
        """Поток получения исторических свечей."""
        class CandlesConnection(MyConnection):
            CONNECTION_NAME: str = 'InvestmentViewer_CandlesThread'

            @classmethod
            def insertHistoricCandles(cls, uid: str, interval: CandleInterval, candles: list[HistoricCandle]):
                """Добавляет свечи в таблицу исторических свечей."""
                if candles:  # Если список не пуст.
                    '''------------------------Добавляем свечи в таблицу исторических свечей------------------------'''
                    db: QtSql.QSqlDatabase = cls.getDatabase()
                    if db.transaction():
                        query = QtSql.QSqlQuery(db)

                        sql_command: str = '''INSERT OR IGNORE INTO \"{0}\" (\"instrument_id\", \"interval\", \"open\", 
                        \"high\", \"low\", \"close\", \"volume\", \"time\", \"is_complete\") VALUES '''.format(
                            MyConnection.CANDLES_TABLE
                        )
                        for i in range(len(candles)):
                            if i > 0: sql_command += ', '  # Если добавляемая свеча не первая.
                            sql_command += '(:uid, :interval, :open{0}, :high{0}, :low{0}, :close{0}, :volume{0}, :time{0}, :is_complete{0})'.format(i)
                        sql_command += ''' ON CONFLICT (\"instrument_id\", \"interval\", \"time\") DO UPDATE SET \"open\" = 
                        \"excluded\".\"open\", \"high\" = \"excluded\".\"high\", \"low\" = \"excluded\".\"low\", \"close\" = 
                        \"excluded\".\"close\", \"volume\" = \"excluded\".\"volume\", \"is_complete\" = 
                        \"excluded\".\"is_complete\";'''

                        prepare_flag: bool = query.prepare(sql_command)
                        assert prepare_flag, query.lastError().text()

                        query.bindValue(':uid', uid)
                        query.bindValue(':interval', interval.name)
                        for i, candle in enumerate(candles):
                            query.bindValue(':open{0}'.format(i), MyQuotation.__repr__(candle.open))
                            query.bindValue(':high{0}'.format(i), MyQuotation.__repr__(candle.high))
                            query.bindValue(':low{0}'.format(i), MyQuotation.__repr__(candle.low))
                            query.bindValue(':close{0}'.format(i), MyQuotation.__repr__(candle.close))
                            query.bindValue(':volume{0}'.format(i), candle.volume)
                            query.bindValue(':time{0}'.format(i), MyConnection.convertDateTimeToText(candle.time))
                            query.bindValue(':is_complete{0}'.format(i), MyConnection.convertBoolToBlob(candle.is_complete))

                        exec_flag: bool = query.exec()
                        assert exec_flag, query.lastError().text()

                        commit_flag: bool = db.commit()  # Фиксирует транзакцию в базу данных.
                        assert commit_flag, db.lastError().text()
                    else:
                        raise SystemError('Не получилось начать транзакцию! db.lastError().text(): \'{0}\'.'.format(db.lastError().text()))
                    '''---------------------------------------------------------------------------------------------'''

        receive_candles_method_name: str = 'GetCandles'

        printText_signal: QtCore.pyqtSignal = QtCore.pyqtSignal(str)  # Сигнал для отображения сообщений в консоли.
        releaseSemaphore_signal: QtCore.pyqtSignal = QtCore.pyqtSignal(LimitPerMinuteSemaphore, int)  # Сигнал для освобождения ресурсов семафора из основного потока.

        '''-----------------Сигналы progressBar'а-----------------'''
        setProgressBarRange_signal: QtCore.pyqtSignal = QtCore.pyqtSignal(int, int)  # Сигнал для установления минимума и максимума progressBar'а заполнения купонов.
        setProgressBarValue_signal: QtCore.pyqtSignal = QtCore.pyqtSignal(int)  # Сигнал для изменения прогресса в progressBar'е.
        '''-------------------------------------------------------'''

        def __init__(self, token_class: TokenClass, instrument: MyBondClass | MyShareClass, interval: CandleInterval, parent: QtCore.QObject | None = None):
            super().__init__(parent=parent)
            self.__mutex: QtCore.QMutex = QtCore.QMutex()
            self.token: TokenClass = token_class
            self.instrument: MyBondClass | MyShareClass = instrument
            self._interval: CandleInterval = interval
            self.semaphore: LimitPerMinuteSemaphore | None = self.token.unary_limits_manager.getSemaphore(self.receive_candles_method_name)

            if self.semaphore is not None:
                @QtCore.pyqtSlot(LimitPerMinuteSemaphore, int)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
                def __releaseSemaphore(semaphore: LimitPerMinuteSemaphore, n: int):
                    semaphore.release(n)

                self.releaseSemaphore_signal.connect(__releaseSemaphore)  # Освобождаем ресурсы семафора из основного потока.

            '''------------Статистические переменные------------'''
            self.request_count: int = 0  # Общее количество запросов.
            self._success_request_count: int = 0  # Количество успешных запросов.
            self.control_point: datetime | None = None  # Начальная точка отсчёта времени.
            '''-------------------------------------------------'''

            self.__pause: bool = False
            self.__pause_condition: QtCore.QWaitCondition = QtCore.QWaitCondition()

            self.printText_signal.connect(print_slot)  # Сигнал для отображения сообщений в консоли.
            self.started.connect(lambda: print('{0}: Поток запущен. ({1})'.format(GroupBox_CandlesReceiving.CandlesThread.__name__, getMoscowDateTime())))
            self.finished.connect(lambda: print('{0}: Поток завершён. ({1})'.format(GroupBox_CandlesReceiving.CandlesThread.__name__, getMoscowDateTime())))

        def pause(self):
            """Приостанавливает прогресс."""
            self.__mutex.lock()
            assert not self.__pause
            self.__pause = True
            self.__mutex.unlock()

        def resume(self):
            """Возобновляет работу потока, поставленного на паузу."""
            self.__mutex.lock()
            assert self.__pause
            self.__pause = False
            self.__mutex.unlock()
            self.__pause_condition.wakeAll()

        def run(self) -> None:
            def printInConsole(text: str):
                self.printText_signal.emit('{0}: {1}'.format(GroupBox_CandlesReceiving.CandlesThread.__name__, text))

            def ifFirstIteration() -> bool:
                """Возвращает True, если поток не сделал ни одного запроса. Иначе возвращает False."""
                return self.request_count > 0

            def checkPause():
                """Проверка на необходимость поставить поток на паузу."""
                self.__mutex.lock()
                if self.__pause:
                    printInConsole('Поток приостановлен.')
                    self.__pause_condition.wait(self.__mutex)
                self.__mutex.unlock()

            if self.semaphore is None:
                printInConsole('Лимит для метода {0} не найден.'.format(self.receive_candles_method_name))
            else:
                match self._interval:
                    case CandleInterval.CANDLE_INTERVAL_1_MIN:
                        dt_from: datetime = self.instrument.instrument().first_1min_candle_date
                    case CandleInterval.CANDLE_INTERVAL_DAY:
                        dt_from: datetime = self.instrument.instrument().first_1day_candle_date
                    case _:
                        printInConsole('Получение исторических свечей для выбранного интервала ещё не реализовано.')
                        return

                uid: str = self.instrument.instrument().uid
                if ifDateTimeIsEmpty(dt_from):
                    printInConsole('Время первой минутной свечи инструмента {0} пустое. Получение исторических свечей для таких инструментов пока не реализовано.'.format(uid))
                    return
                else:
                    max_interval: timedelta = getMaxInterval(self._interval)
                    request_number: int = 0

                    def requestCandles(from_: datetime, to: datetime, interval: CandleInterval):
                        try_count: RequestTryClass = RequestTryClass()
                        response: MyResponse = MyResponse()
                        while try_count and not response.ifDataSuccessfullyReceived():
                            if self.isInterruptionRequested():
                                printInConsole('Поток прерван.')
                                break

                            checkPause()

                            """==============================Выполнение запроса=============================="""
                            self.semaphore.acquire(1)  # Блокирует вызов до тех пор, пока не будет доступно достаточно ресурсов.

                            '''----------------Подсчёт статистических параметров----------------'''
                            if ifFirstIteration():  # Не выполняется до второго запроса.
                                delta: float = (getUtcDateTime() - self.control_point).total_seconds()  # Секунд прошло с последнего запроса.
                                printInConsole('{0} из {1} Период: {3} - {4} ({2:.2f}с)'.format(request_number, requests_count, delta, from_, to))
                            else:
                                printInConsole('{0} из {1} Период: {2} - {3}'.format(request_number, requests_count, from_, to))
                            self.control_point = getUtcDateTime()  # Промежуточная точка отсчёта времени.
                            '''-----------------------------------------------------------------'''

                            response = getCandles(token=self.token.token,
                                                  uid=uid,
                                                  interval=interval,
                                                  from_=from_,
                                                  to=to)
                            assert response.request_occurred, 'Запрос свечей не был произведён.'
                            self.request_count += 1  # Подсчитываем запрос.

                            self.releaseSemaphore_signal.emit(self.semaphore, 1)  # Освобождаем ресурсы семафора из основного потока.

                            '''-----------------------Сообщаем об ошибке-----------------------'''
                            if response.request_error_flag:
                                printInConsole('RequestError {0}'.format(response.request_error))
                            elif response.exception_flag:
                                printInConsole('Exception {0}'.format(response.exception))
                            '''----------------------------------------------------------------'''
                            """=============================================================================="""
                            try_count += 1

                        candles: list[HistoricCandle] | None
                        if response.ifDataSuccessfullyReceived():
                            self._success_request_count += 1  # Подсчитываем успешный запрос.
                            candles = response.response_data
                        else:
                            candles = None

                        if candles is not None:  # Если поток был прерван или если информация не была получена.
                            if self.instrument.candles is None:
                                self.instrument.candles = candles
                            else:
                                self.instrument.candles.extend(candles)
                            self.CandlesConnection.insertHistoricCandles(uid, self._interval, candles)

                        self.setProgressBarValue_signal.emit(request_number)  # Отображаем прогресс в progressBar.

                    current_dt: datetime = getUtcDateTime()
                    '''--Рассчитываем требуемое количество запросов--'''
                    dt_delta: timedelta = current_dt - dt_from
                    requests_count: int = dt_delta // max_interval
                    if dt_delta % max_interval > candle_interval_to_timedelta(self._interval):
                        requests_count += 1
                    '''----------------------------------------------'''
                    self.setProgressBarRange_signal.emit(0, requests_count)  # Задаёт минимум и максимум progressBar'а.
                    dt_to: datetime = dt_from + max_interval

                    self.CandlesConnection.open()  # Открываем соединение с БД.

                    while dt_to < current_dt:
                        if self.isInterruptionRequested():
                            printInConsole('Поток прерван.')
                            break

                        request_number += 1
                        requestCandles(dt_from, dt_to, self._interval)

                        dt_from = dt_to
                        dt_to += max_interval
                    else:
                        current_dt = getUtcDateTime()
                        while dt_to < current_dt:
                            if self.isInterruptionRequested():
                                printInConsole('Поток прерван.')
                                break

                            request_number += 1
                            if request_number > requests_count:
                                requests_count = request_number
                                self.setProgressBarRange_signal.emit(0, request_number)  # Увеличиваем максимум progressBar'а.
                            requestCandles(dt_from, dt_to, self._interval)

                            dt_from = dt_to
                            dt_to += max_interval
                            current_dt = getUtcDateTime()
                        else:
                            request_number += 1
                            if request_number > requests_count:
                                requests_count = request_number
                                self.setProgressBarRange_signal.emit(0, request_number)  # Увеличиваем максимум progressBar'а.
                            requestCandles(dt_from, current_dt, self._interval)

                    self.CandlesConnection.removeConnection()  # Удаляем соединение с БД.

    class ThreadStatus(Enum):
        """Статус потока."""
        START_NOT_POSSIBLE = 0  # Поток не запущен. Запуск потока невозможен.
        START_POSSIBLE = 1  # Поток не запущен. Возможен запуск потока.
        RUNNING = 2  # Поток запущен.
        PAUSE = 3  # Поток приостановлен.
        FINISHED = 4  # Поток завершился.

    STOP: str = 'Стоп'
    PLAY: str = 'Пуск'
    PAUSE: str = 'Пауза'

    def setStatus(self, token: TokenClass | None, instrument: MyShareClass | MyBondClass | None, interval: CandleInterval, status: ThreadStatus):
        def stopThread():
            self.__candles_receiving_thread.requestInterruption()  # Сообщаем потоку о том, что надо завершиться.
            self.__candles_receiving_thread.wait()  # Ждём завершения потока.
            self.__candles_receiving_thread = None

        print('Статус: {0} -> {1}.'.format(self.__thread_status.name, status.name))
        match status:
            case self.ThreadStatus.START_NOT_POSSIBLE:
                assert token is None or instrument is None

                match self.__thread_status:
                    case self.ThreadStatus.START_NOT_POSSIBLE:
                        return
                    case self.ThreadStatus.START_POSSIBLE:
                        self.play_button.setEnabled(False)
                        disconnect_flag: bool = self.play_button.disconnect(self.start_thread_connection)
                        assert disconnect_flag, 'Не удалось отключить слот!'
                    case self.ThreadStatus.RUNNING:
                        self.play_button.setEnabled(False)
                        self.stop_button.setEnabled(False)

                        '''-------------------------Останавливаем поток-------------------------'''
                        assert self.__candles_receiving_thread is not None
                        disconnect_flag: bool = self.__candles_receiving_thread.disconnect(self.thread_finished_connection)
                        assert disconnect_flag, 'Не удалось отключить слот!'
                        stopThread()
                        '''---------------------------------------------------------------------'''

                        disconnect_flag: bool = self.play_button.disconnect(self.pause_thread_connection)
                        assert disconnect_flag, 'Не удалось отключить слот!'

                        disconnect_flag: bool = self.stop_button.disconnect(self.stop_thread_connection)
                        assert disconnect_flag, 'Не удалось отключить слот!'

                        self.progressBar.reset()  # Сбрасываем progressBar.
                        self.play_button.setText(self.PLAY)
                    case self.ThreadStatus.PAUSE:
                        self.play_button.setEnabled(False)
                        self.stop_button.setEnabled(False)

                        '''-------------------------Останавливаем поток-------------------------'''
                        assert self.__candles_receiving_thread is not None
                        self.__candles_receiving_thread.resume()  # Возобновляем работу потока, чтобы он мог безопасно завершиться.
                        stopThread()
                        '''---------------------------------------------------------------------'''

                        self.progressBar.reset()  # Сбрасываем progressBar.
                        self.play_button.setText(self.PLAY)

                        disconnect_flag: bool = self.play_button.disconnect(self.resume_thread_connection)
                        assert disconnect_flag, 'Не удалось отключить слот!'

                    case self.ThreadStatus.FINISHED:
                        self.play_button.setEnabled(False)

                        assert self.__candles_receiving_thread is None
                        self.progressBar.reset()  # Сбрасываем progressBar.

                        disconnect_flag: bool = self.play_button.disconnect(self.start_thread_connection)
                        assert disconnect_flag, 'Не удалось отключить слот!'
                    case _:
                        raise ValueError('Неверный статус потока!')

                self.__thread_status = self.ThreadStatus.START_NOT_POSSIBLE
            case self.ThreadStatus.START_POSSIBLE:
                assert token is not None and instrument is not None
                match self.__thread_status:
                    case self.ThreadStatus.START_NOT_POSSIBLE:
                        pass  # Ничего не требуется делать.
                    case self.ThreadStatus.START_POSSIBLE:
                        return
                    case self.ThreadStatus.RUNNING:
                        self.play_button.setEnabled(False)
                        self.stop_button.setEnabled(False)

                        '''-------------------------Останавливаем поток-------------------------'''
                        assert self.__candles_receiving_thread is not None
                        disconnect_flag: bool = self.__candles_receiving_thread.disconnect(self.thread_finished_connection)
                        assert disconnect_flag, 'Не удалось отключить слот!'
                        stopThread()
                        '''---------------------------------------------------------------------'''

                        self.progressBar.reset()  # Сбрасываем progressBar.
                        self.play_button.setText(self.PLAY)

                        disconnect_flag: bool = self.play_button.disconnect(self.pause_thread_connection)
                        assert disconnect_flag, 'Не удалось отключить слот!'

                        disconnect_flag: bool = self.stop_button.disconnect(self.stop_thread_connection)
                        assert disconnect_flag, 'Не удалось отключить слот!'
                    case self.ThreadStatus.PAUSE:
                        self.play_button.setEnabled(False)
                        self.stop_button.setEnabled(False)

                        '''-------------------------Останавливаем поток-------------------------'''
                        assert self.__candles_receiving_thread is not None
                        disconnect_flag: bool = self.__candles_receiving_thread.disconnect(self.thread_finished_connection)
                        assert disconnect_flag, 'Не удалось отключить слот!'
                        self.__candles_receiving_thread.resume()  # Возобновляем работу потока, чтобы он мог безопасно завершиться.
                        stopThread()
                        '''---------------------------------------------------------------------'''

                        self.progressBar.reset()  # Сбрасываем progressBar.
                        self.play_button.setText(self.PLAY)

                        disconnect_flag: bool = self.play_button.disconnect(self.resume_thread_connection)
                        assert disconnect_flag, 'Не удалось отключить слот!'
                    case self.ThreadStatus.FINISHED:
                        self.play_button.setEnabled(False)

                        assert self.__candles_receiving_thread is None
                        self.progressBar.reset()  # Сбрасываем progressBar.

                        disconnect_flag: bool = self.play_button.disconnect(self.start_thread_connection)
                        assert disconnect_flag, 'Не удалось отключить слот!'
                    case _:
                        raise ValueError('Неверный статус потока!')

                @QtCore.pyqtSlot()  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
                def __startThread():
                    """Запускает поток получения исторических свечей."""
                    self.setStatus(token=self.token, instrument=self.instrument, interval=self.interval, status=self.ThreadStatus.RUNNING)

                self.start_thread_connection = self.play_button.clicked.connect(__startThread)

                self.__thread_status = self.ThreadStatus.START_POSSIBLE

                self.play_button.setEnabled(True)
            case self.ThreadStatus.RUNNING:
                assert token is not None and instrument is not None
                match self.__thread_status:
                    case self.ThreadStatus.START_POSSIBLE:
                        self.play_button.setEnabled(False)

                        disconnect_flag: bool = self.play_button.disconnect(self.start_thread_connection)
                        assert disconnect_flag, 'Не удалось отключить слот!'

                        """==========================Поток необходимо запустить=========================="""
                        assert self.__candles_receiving_thread is None, 'Поток получения исторических свечей должен быть завершён!'
                        self.__candles_receiving_thread = GroupBox_CandlesReceiving.CandlesThread(token_class=token,
                                                                                                  instrument=instrument,
                                                                                                  interval=interval,
                                                                                                  parent=self)

                        '''---------------------Подключаем сигналы потока к слотам---------------------'''
                        @QtCore.pyqtSlot(int, int)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
                        def __setRange(minimum: int, maximum: int):
                            if self.__candles_receiving_thread is not None:
                                self.progressBar.setRange(minimum, maximum)

                        self.__candles_receiving_thread.setProgressBarRange_signal.connect(__setRange)

                        @QtCore.pyqtSlot(int)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
                        def __setValue(value: int):
                            if self.__candles_receiving_thread is not None:
                                self.progressBar.setValue(value)

                        self.__candles_receiving_thread.setProgressBarValue_signal.connect(__setValue)

                        self.thread_finished_connection = self.__candles_receiving_thread.finished.connect(lambda: self.setStatus(token=self.token, instrument=self.instrument, interval=self.interval, status=self.ThreadStatus.FINISHED))
                        '''----------------------------------------------------------------------------'''

                        self.__candles_receiving_thread.start()  # Запускаем поток.
                        """=============================================================================="""
                    case self.ThreadStatus.PAUSE:
                        self.play_button.setEnabled(False)
                        self.stop_button.setEnabled(False)

                        self.__candles_receiving_thread.resume()

                        disconnect_flag: bool = self.play_button.disconnect(self.resume_thread_connection)
                        assert disconnect_flag, 'Не удалось отключить слот!'
                    case _:
                        raise ValueError('Неверный статус потока!')

                '''------------------------------Левая кнопка------------------------------'''
                self.play_button.setText(self.PAUSE)

                @QtCore.pyqtSlot()  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
                def __pauseThread():
                    """Приостанавливает поток получения исторических свечей."""
                    self.setStatus(token=self.token, instrument=self.instrument, interval=self.interval, status=self.ThreadStatus.PAUSE)

                self.pause_thread_connection = self.play_button.clicked.connect(__pauseThread)
                '''------------------------------------------------------------------------'''

                '''------------------------------Правая кнопка------------------------------'''
                @QtCore.pyqtSlot()  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
                def __stopThread():
                    """Останавливает поток получения исторических свечей."""
                    self.setStatus(token=self.token, instrument=self.instrument, interval=self.interval, status=self.ThreadStatus.START_POSSIBLE)

                self.stop_thread_connection = self.stop_button.clicked.connect(__stopThread)
                '''-------------------------------------------------------------------------'''

                self.__thread_status = self.ThreadStatus.RUNNING

                self.play_button.setEnabled(True)
                self.stop_button.setEnabled(True)
            case self.ThreadStatus.PAUSE:
                assert self.__thread_status is self.ThreadStatus.RUNNING, 'Поток получения свечей переходит в статус PAUSE из статуса {0} минуя статус RUNNING.'.format(self.__thread_status.name)
                self.play_button.setEnabled(False)
                self.stop_button.setEnabled(False)

                self.__candles_receiving_thread.pause()

                self.play_button.setText(self.PLAY)

                disconnect_flag: bool = self.play_button.disconnect(self.pause_thread_connection)
                assert disconnect_flag, 'Не удалось отключить слот!'

                @QtCore.pyqtSlot()  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
                def __resumeThread():
                    """Возобновляет работу потока получения исторических свечей."""
                    self.setStatus(token=self.token, instrument=self.instrument, interval=self.interval, status=self.ThreadStatus.RUNNING)

                self.resume_thread_connection = self.play_button.clicked.connect(__resumeThread)

                self.__thread_status = self.ThreadStatus.PAUSE

                self.play_button.setEnabled(True)
                self.stop_button.setEnabled(True)
            case self.ThreadStatus.FINISHED:
                assert self.__thread_status is self.ThreadStatus.RUNNING, 'Поток получения свечей переходит в статус FINISHED из статуса {0} минуя статус RUNNING.'.format(self.__thread_status.name)
                self.play_button.setEnabled(False)
                self.stop_button.setEnabled(False)

                assert self.__candles_receiving_thread.isFinished()
                self.__candles_receiving_thread = None

                self.play_button.setText(self.PLAY)

                disconnect_flag: bool = self.play_button.disconnect(self.pause_thread_connection)
                assert disconnect_flag, 'Не удалось отключить слот!'

                disconnect_flag: bool = self.stop_button.disconnect(self.stop_thread_connection)
                assert disconnect_flag, 'Не удалось отключить слот!'

                @QtCore.pyqtSlot()  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
                def __startThread():
                    """Запускает поток получения исторических свечей."""
                    self.setStatus(token=self.token, instrument=self.instrument, interval=self.interval, status=self.ThreadStatus.START_POSSIBLE)
                    self.setStatus(token=self.token, instrument=self.instrument, interval=self.interval, status=self.ThreadStatus.RUNNING)

                self.start_thread_connection = self.play_button.clicked.connect(__startThread)

                self.__thread_status = self.ThreadStatus.FINISHED

                self.play_button.setEnabled(True)
            case _:
                raise ValueError('Неверный статус потока!')

    def __init__(self, token_model: TokenListModel, parent: QtWidgets.QWidget | None = None):
        self.__instrument: MyBondClass | MyShareClass | None = None

        self.__candles_receiving_thread: GroupBox_CandlesReceiving.CandlesThread | None = None
        self.__thread_status: GroupBox_CandlesReceiving.ThreadStatus = self.ThreadStatus.START_NOT_POSSIBLE

        super().__init__(parent=parent)

        verticalLayout_main = QtWidgets.QVBoxLayout(self)
        verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        verticalLayout_main.setSpacing(2)

        verticalLayout_main.addWidget(TitleLabel(text='ПОЛУЧЕНИЕ ИСТОРИЧЕСКИХ СВЕЧЕЙ', parent=self))

        '''-----------Выбор токена для получения исторических свечей-----------'''
        horizontalLayout_token = QtWidgets.QHBoxLayout(self)
        horizontalLayout_token.addWidget(QtWidgets.QLabel(text='Токен:', parent=self))
        horizontalLayout_token.addSpacerItem(QtWidgets.QSpacerItem(4, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum))
        self.comboBox_token = ComboBox_Token(token_model=token_model, parent=self)
        horizontalLayout_token.addWidget(self.comboBox_token)
        horizontalLayout_token.addSpacerItem(QtWidgets.QSpacerItem(0, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum))
        verticalLayout_main.addLayout(horizontalLayout_token)
        '''--------------------------------------------------------------------'''

        '''-----------------------Выбор интервала свечей-----------------------'''
        horizontalLayout_interval = QtWidgets.QHBoxLayout(self)
        horizontalLayout_interval.addWidget(QtWidgets.QLabel(text='Интервал:', parent=self))
        horizontalLayout_interval.addSpacerItem(QtWidgets.QSpacerItem(4, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum))
        self.comboBox_interval = ComboBox_Interval(parent=self)
        horizontalLayout_interval.addWidget(self.comboBox_interval)
        horizontalLayout_interval.addSpacerItem(QtWidgets.QSpacerItem(0, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum))
        verticalLayout_main.addLayout(horizontalLayout_interval)
        '''--------------------------------------------------------------------'''

        '''---------------Прогресс получения исторических свечей---------------'''
        horizontalLayout = QtWidgets.QHBoxLayout(self)

        self.play_button = QtWidgets.QPushButton(text=self.PLAY, parent=self)
        self.play_button.setEnabled(False)
        horizontalLayout.addWidget(self.play_button)

        self.stop_button = QtWidgets.QPushButton(text=self.STOP, parent=self)
        self.stop_button.setEnabled(False)
        horizontalLayout.addWidget(self.stop_button)

        self.progressBar = ProgressBar_DataReceiving('progressBar_candles', self)
        horizontalLayout.addWidget(self.progressBar)

        verticalLayout_main.addLayout(horizontalLayout)
        '''--------------------------------------------------------------------'''

        verticalLayout_main.addStretch(1)

        self.start_thread_connection: QtCore.QMetaObject.Connection = QtCore.QMetaObject.Connection()
        self.pause_thread_connection: QtCore.QMetaObject.Connection = QtCore.QMetaObject.Connection()
        self.resume_thread_connection: QtCore.QMetaObject.Connection = QtCore.QMetaObject.Connection()
        self.stop_thread_connection: QtCore.QMetaObject.Connection = QtCore.QMetaObject.Connection()

        self.thread_finished_connection: QtCore.QMetaObject.Connection = QtCore.QMetaObject.Connection()

        @QtCore.pyqtSlot(TokenClass)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
        def __onTokenSelected(token: TokenClass):
            self.token = token

        @QtCore.pyqtSlot()  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
        def __onTokenReset():
            self.token = None

        @QtCore.pyqtSlot(CandleInterval)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
        def __onIntervalSelected(interval: CandleInterval):
            self.interval = interval

        self.comboBox_token.tokenSelected.connect(__onTokenSelected)
        self.comboBox_token.tokenReset.connect(__onTokenReset)
        self.comboBox_interval.intervalSelected.connect(__onIntervalSelected)

    def __onParameterChanged(self, token: TokenClass | None, instrument: MyShareClass | MyBondClass | None, interval: CandleInterval):
        status = self.ThreadStatus.START_NOT_POSSIBLE if self.token is None or self.instrument is None else self.ThreadStatus.START_POSSIBLE
        self.setStatus(token=token, instrument=instrument, interval=interval, status=status)

    @property
    def token(self) -> TokenClass:
        return self.comboBox_token.token

    @token.setter
    def token(self, token: TokenClass | None):
        self.__onParameterChanged(token=token, instrument=self.instrument, interval=self.interval)

    @property
    def interval(self) -> CandleInterval:
        return self.comboBox_interval.interval

    @interval.setter
    def interval(self, interval: CandleInterval):
        self.__onParameterChanged(token=self.token, instrument=self.instrument, interval=interval)

    @property
    def instrument(self) -> MyBondClass | MyShareClass | None:
        return self.__instrument

    @instrument.setter
    def instrument(self, instrument: MyBondClass | MyShareClass | None):
        self.__instrument = instrument
        self.__onParameterChanged(token=self.token, instrument=instrument, interval=self.interval)

    def setInstrument(self, instrument: MyBondClass | MyShareClass | None = None):
        """Устанавливает текущий инструмент."""
        self.instrument = instrument


class GroupBox_CandlesView(QtWidgets.QGroupBox):
    """Панель отображения свечей."""
    class CandlesModel(QtCore.QAbstractTableModel):
        def __init__(self, parent: QtCore.QObject | None = None):
            self.__columns: tuple[Column, ...] = (
                Column(header='Открытие',
                       header_tooltip='Цена открытия за 1 инструмент.',
                       data_function=lambda candle: candle.open,
                       display_function=lambda candle: MyQuotation.__str__(candle.open, ndigits=8, delete_decimal_zeros=True)),
                Column(header='Макс. цена',
                       header_tooltip='Максимальная цена за 1 инструмент.',
                       data_function=lambda candle: candle.high,
                       display_function=lambda candle: MyQuotation.__str__(candle.high, ndigits=8, delete_decimal_zeros=True)),
                Column(header='Мин. цена',
                       header_tooltip='Минимальная цена за 1 инструмент.',
                       data_function=lambda candle: candle.low,
                       display_function=lambda candle: MyQuotation.__str__(candle.low, ndigits=8, delete_decimal_zeros=True)),
                Column(header='Закрытие',
                       header_tooltip='Цена закрытия за 1 инструмент.',
                       data_function=lambda candle: candle.close,
                       display_function=lambda candle: MyQuotation.__str__(candle.close, ndigits=8, delete_decimal_zeros=True)),
                Column(header='Объём',
                       header_tooltip='Объём торгов в лотах.',
                       data_function=lambda candle: candle.volume,
                       display_function=lambda candle: str(candle.volume)),
                Column(header='Время',
                       header_tooltip='Время свечи в часовом поясе UTC.',
                       data_function=lambda candle: candle.time,
                       display_function=lambda candle: str(candle.time)),
                Column(header='Завершённость',
                       header_tooltip='Признак завершённости свечи. False значит, что свеча за текущий интервал ещё сформирована не полностью.',
                       data_function=lambda candle: candle.is_complete,
                       display_function=lambda candle: str(candle.is_complete))
            )
            self.__candles: list[HistoricCandle] = []
            super().__init__(parent=parent)

        def columnCount(self, parent: QtCore.QModelIndex = ...) -> int:
            return len(self.__columns)

        def rowCount(self, parent: QtCore.QModelIndex = ...) -> int:
            return len(self.candles)

        def data(self, index: QtCore.QModelIndex, role: int = ...) -> typing.Any:
            column: Column = self.__columns[index.column()]
            candle: HistoricCandle = self.candles[index.row()]
            return column(role, candle)

        def headerData(self, section: int, orientation: QtCore.Qt.Orientation, role: int = ...) -> typing.Any:
            if orientation == QtCore.Qt.Orientation.Vertical:
                if role == QtCore.Qt.ItemDataRole.DisplayRole:
                    return section + 1  # Проставляем номера строк.
            elif orientation == QtCore.Qt.Orientation.Horizontal:
                if role == QtCore.Qt.ItemDataRole.DisplayRole:
                    return self.__columns[section].header
                elif role == QtCore.Qt.ItemDataRole.ToolTipRole:  # Подсказки.
                    return self.__columns[section].header_tooltip

        def setCandles(self, candles: list[HistoricCandle]):
            self.beginResetModel()
            self.__candles = candles
            self.endResetModel()

        @property
        def candles(self) -> list[HistoricCandle]:
            return self.__candles

    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)

        verticalLayout_main = QtWidgets.QVBoxLayout(self)
        verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        verticalLayout_main.setSpacing(2)

        '''------------------------Заголовок------------------------'''
        horizontalLayout_title = QtWidgets.QHBoxLayout(self)
        horizontalLayout_title.setSpacing(0)

        horizontalLayout_title.addSpacerItem(QtWidgets.QSpacerItem(10, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum))
        horizontalLayout_title.addSpacerItem(QtWidgets.QSpacerItem(0, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum))
        horizontalLayout_title.addWidget(TitleLabel(text='СВЕЧИ', parent=self))

        self.label_count = QtWidgets.QLabel(text='0', parent=self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_count.sizePolicy().hasHeightForWidth())
        self.label_count.setSizePolicy(sizePolicy)
        self.label_count.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        horizontalLayout_title.addWidget(self.label_count)

        horizontalLayout_title.addSpacerItem(QtWidgets.QSpacerItem(10, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum))

        verticalLayout_main.addLayout(horizontalLayout_title)
        '''---------------------------------------------------------'''

        self.tableView = QtWidgets.QTableView(parent=self)
        self.tableView.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tableView.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.tableView.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.tableView.setSortingEnabled(True)
        self.tableView.setModel(self.CandlesModel(parent=self))
        verticalLayout_main.addWidget(self.tableView)

    def setCandles(self, candles: list[HistoricCandle]):
        self.tableView.model().setCandles(candles)
        self.tableView.resizeColumnsToContents()  # Авторазмер столбцов под содержимое.
        self.label_count.setText(str(self.tableView.model().rowCount()))  # Отображаем количество облигаций.

    @property
    def candles(self) -> list[HistoricCandle]:
        return self.tableView.model().candles


class GroupBox_Chart(QtWidgets.QGroupBox):
    """Панель с диаграммой."""
    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)

        verticalLayout_main = QtWidgets.QVBoxLayout(self)
        verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        verticalLayout_main.setSpacing(2)

        verticalLayout_main.addWidget(TitleLabel(text='ГРАФИК', parent=self))

        '''------------------QGraphicsScene------------------'''
        # self.chart_view = CandlesSceneView(parent=self)
        # self.verticalLayout_main.addWidget(self.chart_view)
        '''--------------------------------------------------'''

        '''---------------------QChartView---------------------'''
        self.chart_view = CandlesChartView(parent=self)

        # scrollBar = QtWidgets.QScrollBar(QtCore.Qt.Orientation.Horizontal)
        # scrollBar.setValue(0)

        verticalLayout_main.addWidget(self.chart_view)
        # self.verticalLayout_main.addWidget(scrollBar)
        '''----------------------------------------------------'''

    def setCandles(self, candles: list[HistoricCandle], interval: CandleInterval):
        self.chart_view.setCandles(candles, interval)


class CandlesViewAndGraphic(QtWidgets.QGroupBox):
    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)
        self.setEnabled(False)

        self.__instrument_uid: str | None = None
        self.__candles: list[HistoricCandle] = []

        verticalLayout_main = QtWidgets.QVBoxLayout(self)
        verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        verticalLayout_main.setSpacing(0)

        splitter_horizontal = QtWidgets.QSplitter(orientation=QtCore.Qt.Orientation.Horizontal, parent=self)

        layoutWidget = QtWidgets.QWidget(parent=splitter_horizontal)

        verticalLayout = QtWidgets.QVBoxLayout(layoutWidget)
        verticalLayout.setContentsMargins(0, 0, 0, 0)
        verticalLayout.setSpacing(VERTICAL_SPACING)

        '''-----------------------Выбор интервала свечей-----------------------'''
        horizontalLayout_interval = QtWidgets.QHBoxLayout(layoutWidget)
        horizontalLayout_interval.addSpacing(2)
        horizontalLayout_interval.addWidget(QtWidgets.QLabel(text='Интервал:', parent=layoutWidget), 0)
        horizontalLayout_interval.addSpacing(4)
        self.comboBox_interval = ComboBox_Interval(parent=layoutWidget)
        horizontalLayout_interval.addWidget(self.comboBox_interval, 0)
        horizontalLayout_interval.addStretch(1)
        verticalLayout.addLayout(horizontalLayout_interval, 0)
        '''--------------------------------------------------------------------'''

        # self.comboBox_interval = ComboBox_Interval(parent=layoutWidget)
        # verticalLayout.addWidget(self.comboBox_interval, 0)

        self.groupBox_view = GroupBox_CandlesView(parent=layoutWidget)
        verticalLayout.addWidget(self.groupBox_view, 1)

        # self.groupBox_view = GroupBox_CandlesView(parent=splitter_horizontal)

        self.groupBox_chart = GroupBox_Chart(parent=splitter_horizontal)

        verticalLayout_main.addWidget(splitter_horizontal)

        @QtCore.pyqtSlot(CandleInterval)
        def __onIntervalChanged(interval: CandleInterval):
            self.interval = interval

        self.comboBox_interval.intervalSelected.connect(__onIntervalChanged)

        self.setEnabled(True)

    @property
    def interval(self) -> CandleInterval:
        return self.comboBox_interval.interval

    @interval.setter
    def interval(self, interval: CandleInterval):
        self.candles = [] if self.instrument_uid is None else MainConnection.getCandles(uid=self.instrument_uid, interval=interval)

    @property
    def candles(self) -> list[HistoricCandle]:
        return self.__candles

    @candles.setter
    def candles(self, candles: list[HistoricCandle]):
        self.__candles = candles
        self.groupBox_view.setCandles(self.candles)
        self.groupBox_chart.setCandles(candles=self.candles, interval=self.interval)

    @property
    def instrument_uid(self) -> str | None:
        return self.__instrument_uid

    @instrument_uid.setter
    def instrument_uid(self, instrument_uid: str | None):
        self.__instrument_uid = instrument_uid
        self.candles = [] if self.instrument_uid is None else MainConnection.getCandles(uid=self.instrument_uid, interval=self.interval)

    def setInstrumentUid(self, instrument_uid: str | None = None):
        self.instrument_uid = instrument_uid


class CandlesPage_new(QtWidgets.QWidget):
    """Страница свечей."""
    def __init__(self, token_model: TokenListModel, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)
        self.setEnabled(False)

        verticalLayout_main = QtWidgets.QVBoxLayout(self)
        verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        verticalLayout_main.setSpacing(2)

        splitter_vertical = QtWidgets.QSplitter(orientation=QtCore.Qt.Orientation.Vertical, parent=self)

        """========================Верхняя часть========================"""
        splitter_horizontal = QtWidgets.QSplitter(orientation=QtCore.Qt.Orientation.Horizontal, parent=splitter_vertical)
        splitter_vertical.setStretchFactor(0, 0)

        '''------------------------Левая часть------------------------'''
        layoutWidget = QtWidgets.QWidget(parent=splitter_horizontal)
        splitter_horizontal.setStretchFactor(0, 0)

        verticalLayout = QtWidgets.QVBoxLayout(layoutWidget)
        verticalLayout.setContentsMargins(0, 0, 0, 0)
        verticalLayout.setSpacing(2)

        self.groupBox_instrument = GroupBox_InstrumentSelection(token_model=token_model, parent=layoutWidget)
        verticalLayout.addWidget(self.groupBox_instrument, 0)

        self.groupBox_candles_receiving = GroupBox_CandlesReceiving(token_model=token_model, parent=layoutWidget)
        verticalLayout.addWidget(self.groupBox_candles_receiving, 0)

        verticalLayout.addStretch(1)
        '''-----------------------------------------------------------'''

        self.groupBox_instrument_info = GroupBox_InstrumentInfo(parent=splitter_horizontal)
        splitter_horizontal.setStretchFactor(1, 1)
        """============================================================="""

        """========================Нижняя часть========================"""
        # self.groupBox_candles_view = GroupBox_CandlesView(parent=splitter_vertical)
        self.groupBox_candles_view = CandlesViewAndGraphic(parent=splitter_vertical)
        splitter_vertical.setStretchFactor(1, 1)
        """============================================================"""

        verticalLayout_main.addWidget(splitter_vertical)

        def __onInstrumentSelected(instrument: MyBondClass | MyShareClass | None = None):
            self.instrument = instrument

        self.groupBox_instrument.bondSelected.connect(__onInstrumentSelected)
        self.groupBox_instrument.shareSelected.connect(__onInstrumentSelected)
        self.groupBox_instrument.instrumentReset.connect(__onInstrumentSelected)

        self.setEnabled(True)

    @property
    def candles(self) -> list[HistoricCandle]:
        return self.groupBox_candles_view.candles

    @property
    def instrument(self) -> MyShareClass | MyBondClass | None:
        return self.groupBox_instrument.instrument

    @instrument.setter
    def instrument(self, instrument: MyShareClass | MyBondClass | None):
        self.groupBox_candles_view.setInstrumentUid(instrument.uid)
        self.groupBox_instrument_info.setInstrument(instrument)
        self.groupBox_candles_receiving.setInstrument(instrument)
