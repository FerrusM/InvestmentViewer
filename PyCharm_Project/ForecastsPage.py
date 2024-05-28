from __future__ import annotations
import typing
from datetime import datetime
from enum import Enum, StrEnum
from PyQt6 import QtCore, QtWidgets, QtGui, QtSql
from grpc import StatusCode
from tinkoff.invest.schemas import GetForecastResponse, TargetItem, Quotation, Recommendation
from Classes import TokenClass, MyTreeView, ColumnWithoutHeader, ConsensusFull, MyConnection
from common.pyqt6_columns import Header
from DatabaseWidgets import TokenSelectionBar, ComboBox_Status, ComboBox_InstrumentType
from MyDatabase import MainConnection
from common.datetime_functions import getUtcDateTime, reportSignificantInfoFromDateTime, print_function_runtime
from MyQuotation import MyQuotation
from MyRequests import MyResponse, RequestTryClass, getForecast
from PagesClasses import ProgressBar_DataReceiving
from common.pyqt6_widgets import TitleLabel, TitleWithCount
from ReceivingThread import ManagedReceivingThread
from TokenModel import TokenListModel


class InstrumentItem:
    def __init__(self, uid: str, name: str):
        self.uid: str = uid
        self.name: str = name

    def __eq__(self, other: InstrumentItem) -> bool:
        if type(other) is InstrumentItem:
            return self.uid == other.uid and self.name == other.name
        else:
            raise TypeError('Класс {0} нельзя сравнивать с другими классами!'.format(self.__class__.__name__))


class InstrumentsModel(QtCore.QAbstractListModel):
    """Модель инструментов."""
    __EMPTY: str = 'Не выбран'

    def __init__(self, token: TokenClass | None = None, status: str | None = None, instrument_type: str | None = None,
                 only_with_forecasts_flag: bool = False, parent: QtCore.QObject | None = None):
        super().__init__(parent=parent)
        self.__instruments: list[InstrumentItem] = []
        '''----Параметры поиска инструментов----'''
        self.__token: TokenClass | None = None
        self.__status: str | None = None
        self.__type: str | None = None
        self.__only_with_forecasts: bool = False
        '''-------------------------------------'''
        self.__update(token=token, status=status, instrument_type=instrument_type, only_with_forecasts=only_with_forecasts_flag)

    def rowCount(self, parent: QtCore.QModelIndex = ...) -> int:
        return len(self.__instruments) + 1

    def getInstrumentsCount(self) -> int:
        """Возвращает количество инструментов в модели."""
        return len(self.__instruments)

    def data(self, index: QtCore.QModelIndex, role: int = ...) -> typing.Any:
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            def __show(item: InstrumentItem) -> str:
                return '{0} | {1}'.format(item.uid, item.name)

            row: int = index.row()
            return self.__EMPTY if row == 0 else __show(self.__instruments[row - 1])

    def __update(self, token: TokenClass | None, status: str | None, instrument_type: str | None, only_with_forecasts: bool):
        """Обновляет данные модели."""
        self.beginResetModel()

        '''--------Параметры поиска инструментов--------'''
        self.__token = token
        self.__status = status
        self.__type = instrument_type
        self.__only_with_forecasts = only_with_forecasts
        '''---------------------------------------------'''

        self.__instruments.clear()

        __select_consensuses_uids: str = 'SELECT DISTINCT \"instrument_uid\" AS \"uid\" FROM \"{0}\"'.format(
            MyConnection.CONSENSUS_ITEMS_TABLE
        )
        __select_all_uids_and_names: str = '''SELECT \"name\", \"uid\" FROM \"{0}\" UNION ALL SELECT \"name\", \"uid\" 
        FROM \"{1}\"'''.format(
            MyConnection.SHARES_TABLE,
            MyConnection.BONDS_TABLE
        )

        if self.__token is None:
            if self.__status is None:
                if self.__type is None:
                    __select_uids_and_names: str = '({0})'.format(__select_all_uids_and_names)
                else:
                    if self.__type == 'share':
                        __select_uids_and_names: str = '\"{0}\"'.format(MyConnection.SHARES_TABLE)
                    elif self.__type == 'bond':
                        __select_uids_and_names: str = '\"{0}\"'.format(MyConnection.BONDS_TABLE)
                    else:
                        raise ValueError('Неизвестный тип инструмента ({0})!'.format(self.__type))

                if self.__only_with_forecasts:
                    select_instruments_command: str = '''SELECT \"name\", \"uid\" FROM {0} WHERE \"uid\" IN {1} 
                    ORDER BY \"name\";'''.format(
                        __select_uids_and_names,
                        '({0})'.format(__select_consensuses_uids)
                    )
                else:
                    select_instruments_command: str = 'SELECT \"name\", \"uid\" FROM {0} ORDER BY \"name\";'.format(
                        __select_uids_and_names
                    )

                db: QtSql.QSqlDatabase = MainConnection.getDatabase()
                if db.transaction():
                    instruments_query = QtSql.QSqlQuery(db)
                    instruments_query.setForwardOnly(True)  # Возможно, это ускоряет извлечение данных.
                    instruments_prepare_flag: bool = instruments_query.prepare(select_instruments_command)
                    assert instruments_prepare_flag, instruments_query.lastError().text()
                    instruments_exec_flag: bool = instruments_query.exec()
                    assert instruments_exec_flag, instruments_query.lastError().text()

                    while instruments_query.next():
                        name: str = instruments_query.value('name')
                        uid: str = instruments_query.value('uid')
                        self.__instruments.append(InstrumentItem(uid=uid, name=name))

                    commit_flag: bool = db.commit()  # Фиксирует транзакцию в базу данных.
                    assert commit_flag, db.lastError().text()
                else:
                    raise SystemError('Не получилось начать транзакцию! db.lastError().text(): \'{0}\'.'.format(db.lastError().text()))
            else:
                if self.__type is None:
                    __select_uids_and_names: str = '({0})'.format(__select_all_uids_and_names)
                else:
                    if self.__type == 'share':
                        __select_uids_and_names: str = '\"{0}\"'.format(MyConnection.SHARES_TABLE)
                    elif self.__type == 'bond':
                        __select_uids_and_names: str = '\"{0}\"'.format(MyConnection.BONDS_TABLE)
                    else:
                        raise ValueError('Неизвестный тип инструмента ({0})!'.format(self.__type))

                __select_statuses_uids: str = 'SELECT \"uid\" FROM \"{0}\" WHERE \"status\" = :status'.format(
                    MyConnection.INSTRUMENT_STATUS_TABLE
                )

                if self.__only_with_forecasts:
                    select_instruments_command: str = '''SELECT \"name\", \"uid\" FROM {0} WHERE \"uid\" IN 
                    (SELECT \"a\".\"uid\" FROM {1} AS \"a\" INNER JOIN {2} AS \"b\" ON \"a\".\"uid\" = \"b\".\"uid\") 
                    ORDER BY \"name\";'''.format(
                        __select_uids_and_names,
                        '({0})'.format(__select_statuses_uids),
                        '({0})'.format(__select_consensuses_uids)
                    )
                else:
                    select_instruments_command: str = '''SELECT \"name\", \"uid\" FROM {0} WHERE \"uid\" IN {1} 
                    ORDER BY \"name\";'''.format(
                        __select_uids_and_names,
                        '({0})'.format(__select_statuses_uids)
                    )

                db: QtSql.QSqlDatabase = MainConnection.getDatabase()
                if db.transaction():
                    instruments_query = QtSql.QSqlQuery(db)
                    instruments_query.setForwardOnly(True)  # Возможно, это ускоряет извлечение данных.
                    instruments_prepare_flag: bool = instruments_query.prepare(select_instruments_command)
                    assert instruments_prepare_flag, instruments_query.lastError().text()
                    instruments_query.bindValue(':status', self.__status)
                    instruments_exec_flag: bool = instruments_query.exec()
                    assert instruments_exec_flag, instruments_query.lastError().text()

                    while instruments_query.next():
                        name: str = instruments_query.value('name')
                        uid: str = instruments_query.value('uid')
                        self.__instruments.append(InstrumentItem(uid=uid, name=name))

                    commit_flag: bool = db.commit()  # Фиксирует транзакцию в базу данных.
                    assert commit_flag, db.lastError().text()
                else:
                    raise SystemError('Не получилось начать транзакцию! db.lastError().text(): \'{0}\'.'.format(db.lastError().text()))
        else:
            if status is None:
                if self.__type is None:
                    __select_uids_and_names: str = '({0})'.format(__select_all_uids_and_names)
                else:
                    if self.__type == 'share':
                        __select_uids_and_names: str = '\"{0}\"'.format(MyConnection.SHARES_TABLE)
                    elif self.__type == 'bond':
                        __select_uids_and_names: str = '\"{0}\"'.format(MyConnection.BONDS_TABLE)
                    else:
                        raise ValueError('Неизвестный тип инструмента ({0})!'.format(self.__type))

                __select_statuses_uids: str = 'SELECT \"uid\" FROM \"{0}\" WHERE \"token\" = :token'.format(
                    MyConnection.INSTRUMENT_STATUS_TABLE
                )

                if self.__only_with_forecasts:
                    select_instruments_command: str = '''SELECT \"name\", \"uid\" FROM {0} WHERE \"uid\" IN 
                    (SELECT \"a\".\"uid\" FROM {1} AS \"a\" INNER JOIN {2} AS \"b\" ON \"a\".\"uid\" = \"b\".\"uid\") 
                    ORDER BY \"name\";'''.format(
                        __select_uids_and_names,
                        '({0})'.format(__select_statuses_uids),
                        '({0})'.format(__select_consensuses_uids)
                    )
                else:
                    select_instruments_command: str = '''SELECT \"name\", \"uid\" FROM {0} WHERE \"uid\" IN 
                    {1} ORDER BY \"name\";'''.format(
                        __select_uids_and_names,
                        '({0})'.format(__select_statuses_uids)
                    )

                db: QtSql.QSqlDatabase = MainConnection.getDatabase()
                if db.transaction():
                    instruments_query = QtSql.QSqlQuery(db)
                    instruments_query.setForwardOnly(True)  # Возможно, это ускоряет извлечение данных.
                    instruments_prepare_flag: bool = instruments_query.prepare(select_instruments_command)
                    assert instruments_prepare_flag, instruments_query.lastError().text()
                    instruments_query.bindValue(':token', self.__token.token)
                    instruments_exec_flag: bool = instruments_query.exec()
                    assert instruments_exec_flag, instruments_query.lastError().text()

                    while instruments_query.next():
                        name: str = instruments_query.value('name')
                        uid: str = instruments_query.value('uid')
                        self.__instruments.append(InstrumentItem(uid=uid, name=name))

                    commit_flag: bool = db.commit()  # Фиксирует транзакцию в базу данных.
                    assert commit_flag, db.lastError().text()
                else:
                    raise SystemError('Не получилось начать транзакцию! db.lastError().text(): \'{0}\'.'.format(db.lastError().text()))
            else:
                if self.__type is None:
                    __select_uids_and_names: str = '({0})'.format(__select_all_uids_and_names)
                else:
                    if self.__type == 'share':
                        __select_uids_and_names: str = '\"{0}\"'.format(MyConnection.SHARES_TABLE)
                    elif self.__type == 'bond':
                        __select_uids_and_names: str = '\"{0}\"'.format(MyConnection.BONDS_TABLE)
                    else:
                        raise ValueError('Неизвестный тип инструмента ({0})!'.format(self.__type))

                __select_statuses_uids: str = '''SELECT \"uid\" FROM \"{0}\" WHERE \"token\" = :token AND 
                \"status\" = :status'''.format(
                    MyConnection.INSTRUMENT_STATUS_TABLE
                )

                if self.__only_with_forecasts:
                    select_instruments_command: str = '''SELECT \"name\", \"uid\" FROM {0} WHERE \"uid\" IN 
                    (SELECT \"a\".\"uid\" FROM {1} AS \"a\" INNER JOIN {2} AS \"b\" ON \"a\".\"uid\" = \"b\".\"uid\") 
                    ORDER BY \"name\";'''.format(
                        __select_uids_and_names,
                        '({0})'.format(__select_statuses_uids),
                        '({0})'.format(__select_consensuses_uids)
                    )
                else:
                    select_instruments_command: str = '''SELECT \"name\", \"uid\" FROM {0} WHERE \"uid\" IN 
                    {1} ORDER BY \"name\";'''.format(
                        __select_uids_and_names,
                        '({0})'.format(__select_statuses_uids)
                    )

                db: QtSql.QSqlDatabase = MainConnection.getDatabase()
                if db.transaction():
                    instruments_query = QtSql.QSqlQuery(db)
                    instruments_query.setForwardOnly(True)  # Возможно, это ускоряет извлечение данных.
                    instruments_prepare_flag: bool = instruments_query.prepare(select_instruments_command)
                    assert instruments_prepare_flag, instruments_query.lastError().text()
                    instruments_query.bindValue(':token', self.__token.token)
                    instruments_query.bindValue(':status', self.__status)
                    instruments_exec_flag: bool = instruments_query.exec()
                    assert instruments_exec_flag, instruments_query.lastError().text()

                    while instruments_query.next():
                        name: str = instruments_query.value('name')
                        uid: str = instruments_query.value('uid')
                        self.__instruments.append(InstrumentItem(uid=uid, name=name))

                    commit_flag: bool = db.commit()  # Фиксирует транзакцию в базу данных.
                    assert commit_flag, db.lastError().text()
                else:
                    raise SystemError('Не получилось начать транзакцию! db.lastError().text(): \'{0}\'.'.format(db.lastError().text()))

        self.endResetModel()

    def getUid(self, index: int) -> str | None:
        return None if index == 0 else self.__instruments[index - 1].uid

    def getItem(self, index: int) -> InstrumentItem | None:
        return None if index == 0 else self.__instruments[index - 1]

    def getItemIndex(self, item: InstrumentItem) -> int | None:
        indexes_list: list[int] = [i for i, itm in enumerate(self.__instruments) if itm.uid == item.uid and itm.name == item.name]
        items_count: int = len(indexes_list)
        if items_count == 0:
            return None
        elif items_count == 1:
            return indexes_list[0] + 1
        else:
            raise SystemError('Список инструментов модели содержит несколько искомых элементов (uid = \'{0}\', name = \'{1}\')!'.format(item.uid, item.name))

    def setToken(self, token: TokenClass | None):
        self.__update(token=token, status=self.__status, instrument_type=self.__type, only_with_forecasts=self.__only_with_forecasts)

    def setStatus(self, status: str | None):
        self.__update(token=self.__token, status=status, instrument_type=self.__type, only_with_forecasts=self.__only_with_forecasts)

    def setType(self, instrument_type: str | None):
        self.__update(token=self.__token, status=self.__status, instrument_type=instrument_type, only_with_forecasts=self.__only_with_forecasts)

    def setOnlyForecastsFlag(self, flag: bool):
        self.__update(token=self.__token, status=self.__status, instrument_type=self.__type, only_with_forecasts=flag)

    @property
    def uids(self) -> list[str]:
        return [item.uid for item in self.__instruments]


class ComboBox_Instrument(QtWidgets.QComboBox):
    """ComboBox для выбора инструмента."""
    instrumentsListChanged: QtCore.pyqtSignal = QtCore.pyqtSignal(list)  # Сигнал испускается при изменении списка инструментов.

    def __init__(self, token: TokenClass | None, status: str | None, instrument_type: str | None,
                 only_with_forecasts_flag: bool, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)
        self.instruments_model = InstrumentsModel(token=token, status=status, instrument_type=instrument_type,
                                                  only_with_forecasts_flag=only_with_forecasts_flag, parent=self)
        self.setModel(self.instruments_model)
        self.__current_item: InstrumentItem | None = self.instruments_model.getItem(self.currentIndex())
        self.__instrument_changed_connection: QtCore.QMetaObject.Connection = self.currentIndexChanged.connect(self.__onInstrumentChanged)

    @QtCore.pyqtSlot(int)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
    def __onInstrumentChanged(self, index: int):
        new_current_item: InstrumentItem | None = self.instruments_model.getItem(index)
        if new_current_item is None:
            if self.__current_item is not None:
                self.__current_item = None
                self.instrumentsListChanged.emit(self.uids)
        else:
            if self.__current_item is None:
                self.__current_item = new_current_item
                self.instrumentsListChanged.emit([self.__current_item.uid])
            else:
                if new_current_item != self.__current_item:
                    self.__current_item = new_current_item
                    self.instrumentsListChanged.emit([self.__current_item.uid])

    @staticmethod
    def __model_update(decorated_function):
        def wrapper_function(self: ComboBox_Instrument, parameter=None):
            self.currentIndexChanged.disconnect(self.__instrument_changed_connection)
            decorated_function(self, parameter)
            '''---------------Устанавливаем текущий элемент---------------'''
            if self.__current_item is None:
                self.setCurrentIndex(0)
                self.instrumentsListChanged.emit(self.uids)  # Испускается при изменении списка инструментов.
            else:
                index: int | None = self.instruments_model.getItemIndex(self.__current_item)
                if index is None:
                    self.setCurrentIndex(0)
                    self.__current_item = None
                    self.instrumentsListChanged.emit(self.uids)  # Испускается при изменении списка инструментов.
                else:
                    self.setCurrentIndex(index)
            '''-----------------------------------------------------------'''
            self.__instrument_changed_connection = self.currentIndexChanged.connect(self.__onInstrumentChanged)

        return wrapper_function

    @__model_update
    def setToken(self, token: TokenClass | None = None):
        self.instruments_model.setToken(token)

    @__model_update
    def setStatus(self, status: str | None = None):
        self.instruments_model.setStatus(status)

    @__model_update
    def setType(self, instrument_type: str | None = None):
        self.instruments_model.setType(instrument_type)

    @__model_update
    def setOnlyWithForecastsFlag(self, flag: bool):
        self.instruments_model.setOnlyForecastsFlag(flag)

    @property
    def instruments_count(self) -> int:
        return self.instruments_model.getInstrumentsCount()

    @property
    def uids(self) -> list[str]:
        return self.instruments_model.uids


class ForecastsInstrumentSelectionGroupBox(QtWidgets.QGroupBox):
    """Панель выбора инструментов."""
    instrumentsListChanged: QtCore.pyqtSignal = QtCore.pyqtSignal(list)  # Сигнал испускается при изменении списка инструментов.

    def __init__(self, tokens_model: TokenListModel, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)

        verticalLayout_main = QtWidgets.QVBoxLayout(self)
        verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        verticalLayout_main.setSpacing(2)

        '''------------------------------Заголовок------------------------------'''
        horizontalLayout_title = QtWidgets.QHBoxLayout()
        horizontalLayout_title.setSpacing(0)

        horizontalLayout_title.addSpacing(10)

        self.__checkBox = QtWidgets.QCheckBox(text='Только с прогнозами', parent=self)
        horizontalLayout_title.addWidget(self.__checkBox, 1)

        horizontalLayout_title.addWidget(TitleLabel(text='ВЫБОР ИНСТРУМЕНТОВ', parent=self), 0)

        self.__label_count = QtWidgets.QLabel(text='0', parent=self)
        self.__label_count.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        horizontalLayout_title.addWidget(self.__label_count, 1)

        horizontalLayout_title.addSpacing(10)
        verticalLayout_main.addLayout(horizontalLayout_title, 0)
        '''---------------------------------------------------------------------'''

        '''---------------------Строка выбора токена---------------------'''
        self.__token_bar = TokenSelectionBar(tokens_model=tokens_model)
        verticalLayout_main.addLayout(self.__token_bar, 0)
        '''--------------------------------------------------------------'''

        '''---------------Строка выбора статуса инструмента---------------'''
        horizontalLayout_status = QtWidgets.QHBoxLayout()
        horizontalLayout_status.setSpacing(0)

        horizontalLayout_status.addWidget(QtWidgets.QLabel(text='Статус:', parent=self), 0)
        horizontalLayout_status.addSpacing(4)

        self.__comboBox_status = ComboBox_Status(token=self.token, parent=self)
        self.__token_bar.tokenSelected.connect(self.__comboBox_status.setToken)
        self.__token_bar.tokenReset.connect(self.__comboBox_status.setToken)
        horizontalLayout_status.addWidget(self.__comboBox_status, 0)

        horizontalLayout_status.addStretch(1)

        verticalLayout_main.addLayout(horizontalLayout_status, 0)
        '''---------------------------------------------------------------'''

        '''--------------Строка выбора типа инструмента--------------'''
        horizontalLayout_instrument_type = QtWidgets.QHBoxLayout()
        horizontalLayout_instrument_type.setSpacing(0)

        horizontalLayout_instrument_type.addWidget(QtWidgets.QLabel(text='Тип инструмента:', parent=self), 0)
        horizontalLayout_instrument_type.addSpacing(4)

        self.__comboBox_instrument_type = ComboBox_InstrumentType(token=self.token, status=self.status, parent=self)
        self.__token_bar.tokenSelected.connect(self.__comboBox_instrument_type.setToken)
        self.__token_bar.tokenReset.connect(self.__comboBox_instrument_type.setToken)
        self.__comboBox_status.statusSelected.connect(self.__comboBox_instrument_type.setStatus)
        self.__comboBox_status.statusReset.connect(self.__comboBox_instrument_type.setStatus)
        horizontalLayout_instrument_type.addWidget(self.__comboBox_instrument_type, 0)

        horizontalLayout_instrument_type.addStretch(1)

        verticalLayout_main.addLayout(horizontalLayout_instrument_type, 0)
        '''----------------------------------------------------------'''

        '''---------------Строка выбора инструмента---------------'''
        horizontalLayout_instrument = QtWidgets.QHBoxLayout()
        horizontalLayout_instrument.setSpacing(0)

        horizontalLayout_instrument.addWidget(QtWidgets.QLabel(text='Инструмент:', parent=self), 0)
        horizontalLayout_instrument.addSpacing(4)

        self.__comboBox_instrument = ComboBox_Instrument(token=self.token,
                                                         status=self.status,
                                                         instrument_type=self.instrument_type,
                                                         only_with_forecasts_flag=self.only_with_forecasts_flag,
                                                         parent=self)
        self.__label_count.setText(str(self.__comboBox_instrument.instruments_count))

        @QtCore.pyqtSlot(int)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
        def __stateChanged(state: int):
            match state:
                case 2:  # QtCore.Qt.CheckState.Checked
                    self.__comboBox_instrument.setOnlyWithForecastsFlag(True)
                case 0:  # QtCore.Qt.CheckState.Unchecked
                    self.__comboBox_instrument.setOnlyWithForecastsFlag(False)
                case _:
                    raise ValueError('Неизвестное значение checkBox\'а!')

        self.__comboBox_instrument.instrumentsListChanged.connect(self.__onInstrumentsListChanged)
        self.__token_bar.tokenSelected.connect(self.__comboBox_instrument.setToken)
        self.__token_bar.tokenReset.connect(self.__comboBox_instrument.setToken)
        self.__comboBox_status.statusSelected.connect(self.__comboBox_instrument.setStatus)
        self.__comboBox_status.statusReset.connect(self.__comboBox_instrument.setStatus)
        self.__comboBox_instrument_type.typeChanged.connect(self.__comboBox_instrument.setType)
        self.__comboBox_instrument_type.typeReset.connect(self.__comboBox_instrument.setType)
        self.__checkBox.stateChanged.connect(__stateChanged)
        horizontalLayout_instrument.addWidget(self.__comboBox_instrument, 0)

        horizontalLayout_instrument.addStretch(1)

        verticalLayout_main.addLayout(horizontalLayout_instrument, 0)
        '''-------------------------------------------------------'''

        verticalLayout_main.addStretch(1)

    @property
    def token(self) -> TokenClass | None:
        return self.__token_bar.token

    @property
    def status(self) -> str | None:
        return self.__comboBox_status.status

    @property
    def instrument_type(self) -> str | None:
        return self.__comboBox_instrument_type.instrument_type

    @property
    def only_with_forecasts_flag(self) -> bool:
        return self.__checkBox.isChecked()

    @QtCore.pyqtSlot(list)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
    def __onInstrumentsListChanged(self, uids: list[str]):
        self.__label_count.setText(str(len(uids)))
        self.instrumentsListChanged.emit(uids)

    @property
    def uids(self) -> list[str]:
        return self.__comboBox_instrument.uids


class TreeItem:
    def __init__(self, row: int, parent_item: TreeItem | None = None, children: list[TreeItem] | None = None):
        self.__row: int = row  # Номер строки элемента.
        self.__parent: TreeItem | None = parent_item  # Родительский элемент.
        self.__children: list[TreeItem] = [] if children is None else children  # Список дочерних элементов.
        self.__hierarchy_level: int = -1 if parent_item is None else (parent_item.getHierarchyLevel() + 1)

    def row(self) -> int:
        """Возвращает номер строки элемента."""
        return self.__row

    def parent(self) -> TreeItem | None:
        """Возвращает родительский элемент."""
        return self.__parent

    def setChildren(self, children: list[TreeItem] | None):
        if children is None:
            self.__children.clear()
        else:
            self.__children = children

    def child(self, row: int) -> TreeItem:
        return self.__children[row]

    @property
    def children_count(self) -> int:
        """Возвращает количество дочерних элементов."""
        return len(self.__children)

    def getHierarchyLevel(self) -> int:
        """Возвращает уровень иерархии элемента."""
        return self.__hierarchy_level


class ForecastsModel(QtCore.QAbstractItemModel):
    """Модель прогнозов."""
    class ColumnItem:
        def __init__(self, header: Header, consensus_column: ColumnWithoutHeader, target_column: ColumnWithoutHeader):
            self.__header: Header = header
            self.consensus_column: ColumnWithoutHeader = consensus_column
            self.target_column: ColumnWithoutHeader = target_column

        def header(self, role: int = QtCore.Qt.ItemDataRole.UserRole):
            return self.__header(role=role)

    def __init__(self, instruments_uids: list[str], last_fulls_flag: bool, parent: QtCore.QObject | None = None):
        super().__init__(parent=parent)
        self.__instruments_uids: list[str] = instruments_uids
        self.__last_fulls_flag: bool = last_fulls_flag  # Если True, то модель должна отображать только последние прогнозы.
        self.__consensus_fulls: list[ConsensusFull] = []
        self.__root_item: TreeItem = TreeItem(row=0, parent_item=None, children=None)

        POSITIVE_COLOR: QtGui.QBrush = QtGui.QBrush(QtCore.Qt.GlobalColor.darkGreen)
        NEUTRAL_COLOR: QtGui.QBrush = QtGui.QBrush(QtCore.Qt.GlobalColor.darkYellow)
        NEGATIVE_COLOR: QtGui.QBrush = QtGui.QBrush(QtCore.Qt.GlobalColor.darkRed)

        BUY: str = 'ПОКУПАТЬ'
        HOLD: str = 'ДЕРЖАТЬ'
        SELL: str = 'ПРОДАВАТЬ'

        def __getQuotationColor(quotation: Quotation) -> QtGui.QBrush:
            """Возвращает цвет Quotation."""
            zero_quotation = Quotation(units=0, nano=0)
            if quotation > zero_quotation:
                return POSITIVE_COLOR
            elif quotation < zero_quotation:
                return NEGATIVE_COLOR
            else:
                return NEUTRAL_COLOR

        self.columns: tuple[ForecastsModel.ColumnItem, ...] = (
            ForecastsModel.ColumnItem(
                header=Header(
                    title='uid',
                    tooltip='Уникальный идентификатор инструмента'
                ),
                consensus_column=ColumnWithoutHeader(
                    data_function=lambda cf: cf.consensus.uid
                ),
                target_column=ColumnWithoutHeader(
                    data_function=lambda ti: ti.uid
                )
            ),
            ForecastsModel.ColumnItem(
                header=Header(
                    title='Тикер',
                    tooltip='Тикер инструмента'
                ),
                consensus_column=ColumnWithoutHeader(
                    data_function=lambda cf: cf.consensus.ticker,
                    sort_role=QtCore.Qt.ItemDataRole.UserRole
                ),
                target_column=ColumnWithoutHeader(
                    data_function=lambda ti: ti.ticker,
                    sort_role=QtCore.Qt.ItemDataRole.UserRole
                )
            ),
            ForecastsModel.ColumnItem(
                header=Header(
                    title='Прогноз',
                    tooltip='Прогноз'
                ),
                consensus_column=ColumnWithoutHeader(
                    data_function=lambda cf: cf.consensus.recommendation,
                    display_function=lambda cf: BUY if cf.consensus.recommendation == Recommendation.RECOMMENDATION_BUY else SELL if cf.consensus.recommendation == Recommendation.RECOMMENDATION_SELL else HOLD if cf.consensus.recommendation == Recommendation.RECOMMENDATION_HOLD else cf.consensus.recommendation.name,
                    foreground_function=lambda cf: POSITIVE_COLOR if cf.consensus.recommendation == Recommendation.RECOMMENDATION_BUY else NEGATIVE_COLOR if cf.consensus.recommendation == Recommendation.RECOMMENDATION_SELL else NEUTRAL_COLOR if cf.consensus.recommendation == Recommendation.RECOMMENDATION_HOLD else QtCore.QVariant()
                ),
                target_column=ColumnWithoutHeader(
                    data_function=lambda ti: ti.recommendation,
                    display_function=lambda ti: BUY if ti.recommendation == Recommendation.RECOMMENDATION_BUY else SELL if ti.recommendation == Recommendation.RECOMMENDATION_SELL else HOLD if ti.recommendation == Recommendation.RECOMMENDATION_HOLD else ti.recommendation.name,
                    foreground_function=lambda ti: POSITIVE_COLOR if ti.recommendation == Recommendation.RECOMMENDATION_BUY else NEGATIVE_COLOR if ti.recommendation == Recommendation.RECOMMENDATION_SELL else NEUTRAL_COLOR if ti.recommendation == Recommendation.RECOMMENDATION_HOLD else QtCore.QVariant()
                )
            ),
            ForecastsModel.ColumnItem(
                header=Header(
                    title='Дата прогноза',
                    tooltip='Дата прогноза'
                ),
                consensus_column=ColumnWithoutHeader(
                    data_function=lambda cf: cf.number,
                    display_function=lambda cf: str(cf.number),
                    sort_role=QtCore.Qt.ItemDataRole.UserRole,
                    lessThan=lambda left, right, role: left.data(role=role) < right.data(role=role)
                ),
                target_column=ColumnWithoutHeader(
                    data_function=lambda ti: ti.recommendation_date,
                    display_function=lambda ti: reportSignificantInfoFromDateTime(ti.recommendation_date),
                    sort_role=QtCore.Qt.ItemDataRole.UserRole,
                    lessThan=lambda left, right, role: left.data(role=role) < right.data(role=role)
                )
            ),
            ForecastsModel.ColumnItem(
                header=Header(
                    title='Компания',
                    tooltip='Название компании, давшей прогноз'
                ),
                consensus_column=ColumnWithoutHeader(),
                target_column=ColumnWithoutHeader(
                    data_function=lambda ti: ti.company
                )
            ),
            ForecastsModel.ColumnItem(
                header=Header(
                    title='Текущая цена',
                    tooltip='Текущая цена'
                ),
                consensus_column=ColumnWithoutHeader(
                    data_function=lambda cf: cf.consensus.current_price,
                    display_function=lambda cf: '{0} {1}'.format(MyQuotation.__str__(cf.consensus.current_price, ndigits=8, delete_decimal_zeros=True), cf.consensus.currency)
                ),
                target_column=ColumnWithoutHeader(
                    data_function=lambda ti: ti.current_price,
                    display_function=lambda ti: '{0} {1}'.format(MyQuotation.__str__(ti.current_price, ndigits=8, delete_decimal_zeros=True), ti.currency)
                )
            ),
            ForecastsModel.ColumnItem(
                header=Header(
                    title='Прогноз. цена',
                    tooltip='Прогнозируемая цена'
                ),
                consensus_column=ColumnWithoutHeader(
                    data_function=lambda cf: cf.consensus.consensus,
                    display_function=lambda cf: '{0} {1}'.format(MyQuotation.__str__(cf.consensus.consensus, ndigits=8, delete_decimal_zeros=True), cf.consensus.currency),
                    foreground_function=lambda cf: POSITIVE_COLOR if cf.consensus.consensus > cf.consensus.current_price else NEGATIVE_COLOR if cf.consensus.consensus < cf.consensus.current_price else NEUTRAL_COLOR
                ),
                target_column=ColumnWithoutHeader(
                    data_function=lambda ti: ti.target_price,
                    display_function=lambda ti: '{0} {1}'.format(MyQuotation.__str__(ti.target_price, ndigits=8, delete_decimal_zeros=True), ti.currency),
                    foreground_function=lambda ti: POSITIVE_COLOR if ti.target_price > ti.current_price else NEGATIVE_COLOR if ti.target_price < ti.current_price else NEUTRAL_COLOR
                )
            ),
            ForecastsModel.ColumnItem(
                header=Header(
                    title='Мин. цена',
                    tooltip='Минимальная цена прогноза'
                ),
                consensus_column=ColumnWithoutHeader(
                    data_function=lambda cf: '{0} {1}'.format(MyQuotation.__str__(cf.consensus.min_target, ndigits=8, delete_decimal_zeros=True), cf.consensus.currency),
                    foreground_function=lambda cf: POSITIVE_COLOR if cf.consensus.min_target > cf.consensus.current_price else NEGATIVE_COLOR if cf.consensus.min_target < cf.consensus.current_price else NEUTRAL_COLOR
                ),
                target_column=ColumnWithoutHeader()
            ),
            ForecastsModel.ColumnItem(
                header=Header(
                    title='Макс. цена',
                    tooltip='Максимальная цена прогноза'
                ),
                consensus_column=ColumnWithoutHeader(
                    data_function=lambda cf: '{0} {1}'.format(MyQuotation.__str__(cf.consensus.max_target, ndigits=8, delete_decimal_zeros=True), cf.consensus.currency),
                    foreground_function=lambda cf: POSITIVE_COLOR if cf.consensus.max_target > cf.consensus.current_price else NEGATIVE_COLOR if cf.consensus.max_target < cf.consensus.current_price else NEUTRAL_COLOR
                ),
                target_column=ColumnWithoutHeader()
            ),
            ForecastsModel.ColumnItem(
                header=Header(
                    title='Относ. изменение',
                    tooltip='Относительное изменение цены'
                ),
                consensus_column=ColumnWithoutHeader(
                    data_function=lambda cf: cf.consensus.price_change_rel,
                    display_function=lambda cf: '{0}{1}%'.format('+' if cf.consensus.price_change_rel > Quotation(units=0, nano=0) else '', MyQuotation.__str__(cf.consensus.price_change_rel, ndigits=8, delete_decimal_zeros=True)),
                    foreground_function=lambda cf: __getQuotationColor(cf.consensus.price_change_rel),
                    sort_role=QtCore.Qt.ItemDataRole.UserRole,
                    lessThan=lambda left, right, role: left.data(role=role) < right.data(role=role)
                ),
                target_column=ColumnWithoutHeader(
                    data_function=lambda ti: ti.price_change_rel,
                    display_function=lambda ti: '{0}{1}%'.format('+' if ti.price_change_rel > Quotation(units=0, nano=0) else '', MyQuotation.__str__(ti.price_change_rel, ndigits=8, delete_decimal_zeros=True)),
                    foreground_function=lambda ti: __getQuotationColor(ti.price_change_rel),
                    sort_role=QtCore.Qt.ItemDataRole.UserRole,
                    lessThan=lambda left, right, role: left.data(role=role) < right.data(role=role)
                )
            ),
            ForecastsModel.ColumnItem(
                header=Header(
                    title='Кол-во таргетов',
                    tooltip='Кол-во таргет-прогнозов'
                ),
                consensus_column=ColumnWithoutHeader(
                    data_function=lambda cf: len(cf.targets),
                    display_function=lambda cf: str(len(cf.targets)),
                    sort_role=QtCore.Qt.ItemDataRole.UserRole,
                    lessThan=lambda left, right, role: left.data(role=role) < right.data(role=role)
                ),
                target_column=ColumnWithoutHeader()
            )
        )
        self.__update()

    def __update(self):
        """Обновляет модель."""
        self.beginResetModel()
        self.__root_item.setChildren(None)

        self.__consensus_fulls.clear()
        if self.__last_fulls_flag:
            for uid in self.__instruments_uids:
                self.__consensus_fulls.extend(MainConnection.getLastConsensusFulls(instrument_uid=uid))
        else:
            for uid in self.__instruments_uids:
                self.__consensus_fulls.extend(MainConnection.getConsensusFulls(instrument_uid=uid))

        items: list[TreeItem] = []
        for i, consensus_full in enumerate(self.__consensus_fulls):
            parent_item: TreeItem = TreeItem(row=i, parent_item=None, children=None)
            parent_item.setChildren([TreeItem(row=j, parent_item=parent_item, children=None) for j, target in enumerate(consensus_full.targets)])
            items.append(parent_item)
        self.__root_item.setChildren(items)

        self.endResetModel()

    def rowCount(self, parent: QtCore.QModelIndex = ...) -> int:
        if parent.column() > 0:
            return 0  # Общее соглашение, используемое в моделях, предоставляющих древовидные структуры данных, заключается в том, что только элементы в первом столбце имеют дочерние элементы.
        if parent.isValid():  # Если индекс parent действителен.
            # return len(self.__consensus_fulls[parent.row()].targets)
            tree_item: TreeItem = parent.internalPointer()  # Указатель на внутреннюю структуру данных.
            return tree_item.children_count
        else:
            # return len(self.__consensus_fulls)
            tree_item: TreeItem = self.__root_item
            return tree_item.children_count

    def columnCount(self, parent: QtCore.QModelIndex = ...) -> int:
        return len(self.columns)

    def index(self, row: int, column: int, parent: QtCore.QModelIndex = ...) -> QtCore.QModelIndex:
        if parent.isValid():  # Если индекс parent действителен.
            parent_item: TreeItem = parent.internalPointer()  # Указатель на внутреннюю структуру данных.
            child_item: TreeItem = parent_item.child(row)
            return self.createIndex(row, column, child_item)
        else:
            return self.createIndex(row, column, self.__root_item.child(row))

    def parent(self, child: QtCore.QModelIndex) -> QtCore.QModelIndex:
        # assert not child.isValid(), 'А может ли запрашиваться parent недействительного элемента?'
        if child.isValid():  # Если индекс child действителен.
            child_item: TreeItem = child.internalPointer()  # Указатель на внутреннюю структуру данных.
            parent_item: TreeItem | None = child_item.parent()
            if parent_item is None:
                return QtCore.QModelIndex()
            elif parent_item == self.__root_item:
                return QtCore.QModelIndex()
            else:
                return self.index(row=parent_item.row(), column=0, parent=QtCore.QModelIndex())
        else:
            return QtCore.QModelIndex()

    def data(self, index: QtCore.QModelIndex, role: int = ...) -> typing.Any:
        column: ForecastsModel.ColumnItem = self.columns[index.column()]
        if index.parent().isValid():
            parent_tree_item: TreeItem = index.parent().internalPointer()  # Указатель на внутреннюю структуру данных.
            target_item: TargetItem = self.__consensus_fulls[parent_tree_item.row()].targets[index.row()]
            return column.target_column(role, target_item)
        else:
            consensus_full: ConsensusFull = self.__consensus_fulls[index.row()]
            return column.consensus_column(role, consensus_full)

    def headerData(self, section: int, orientation: QtCore.Qt.Orientation, role: int = ...) -> typing.Any:
        if orientation == QtCore.Qt.Orientation.Horizontal:
            column: ForecastsModel.ColumnItem = self.columns[section]
            return column.header(role=role)

    def setOnlyLastFlag(self, flag: bool):
        if self.__last_fulls_flag != flag:
            self.__last_fulls_flag = flag
            self.__update()

    def setInstrumentsUids(self, instruments_uids: list[str]):
        self.__instruments_uids = instruments_uids
        self.__update()


class ForecastsProxyModel(QtCore.QSortFilterProxyModel):
    def __init__(self, source_model: ForecastsModel, parent: QtCore.QObject | None = None):
        super().__init__(parent=parent)
        self.setSourceModel(source_model)

    def lessThan(self, left: QtCore.QModelIndex, right: QtCore.QModelIndex) -> bool:
        assert left.column() == right.column()
        column: ForecastsModel.ColumnItem = self.sourceModel().columns[left.column()]

        if left.parent().isValid() and right.parent().isValid():
            if column.target_column.lessThan is None:
                return super().lessThan(left, right)  # Сортировка по умолчанию.
            else:
                return column.target_column.lessThan(left, right, column.consensus_column.getSortRole)
        elif not left.parent().isValid() and not right.parent().isValid():
            if column.consensus_column.lessThan is None:
                return super().lessThan(left, right)  # Сортировка по умолчанию.
            else:
                return column.consensus_column.lessThan(left, right, column.consensus_column.getSortRole)
        else:
            raise SystemError('Элементы находятся на разных уровнях иерархии!')


class ForecastsThread(ManagedReceivingThread):
    """Поток получения прогнозов."""
    forecastsReceived: QtCore.pyqtSignal = QtCore.pyqtSignal(GetForecastResponse)

    '''-----------------Сигналы progressBar'а-----------------'''
    setProgressBarRange_signal: QtCore.pyqtSignal = QtCore.pyqtSignal(int, int)  # Сигнал для установления минимума и максимума progressBar'а заполнения купонов.
    setProgressBarValue_signal: QtCore.pyqtSignal = QtCore.pyqtSignal(int)  # Сигнал для изменения прогресса в progressBar'е.
    '''-------------------------------------------------------'''

    def __init__(self, token: TokenClass, uids: list[str], parent: QtCore.QObject | None = None):
        # super().__init__(token=token, receive_method=InstrumentsService.get_forecast_by.__name__, parent=parent)
        super().__init__(token=token, receive_method='GetForecastBy', parent=parent)
        self.__instruments_uids: list[str] = uids

        '''------------Статистические переменные------------'''
        self.request_count: int = 0  # Общее количество запросов.
        self.control_point: datetime | None = None  # Начальная точка отсчёта времени.
        self.consensuses_count: int = 0  # Количество полученных прогнозов.
        '''-------------------------------------------------'''

    def receivingFunction(self):
        instruments_count: int = len(self.__instruments_uids)  # Количество инструментов.
        self.setProgressBarRange_signal.emit(0, instruments_count)  # Задаёт минимум и максимум progressBar'а.

        def __ifFirstIteration() -> bool:
            """Возвращает True, если поток не сделал ни одного запроса. Иначе возвращает False."""
            return self.request_count > 0

        for i, uid in enumerate(self.__instruments_uids):
            instrument_number: int = i + 1  # Номер текущего инструмента.
            self.setProgressBarValue_signal.emit(instrument_number)  # Отображаем прогресс в progressBar.

            try_count: RequestTryClass = RequestTryClass(max_request_try_count=1)
            response: MyResponse = MyResponse()
            while try_count and not response.ifDataSuccessfullyReceived():
                if self.isInterruptionRequested():
                    break

                self.checkPause()

                """==============================Выполнение запроса=============================="""
                self.semaphore.acquire(1)  # Блокирует вызов до тех пор, пока не будет доступно достаточно ресурсов.

                '''----------------Подсчёт статистических параметров----------------'''
                if __ifFirstIteration():  # Не выполняется до второго запроса.
                    delta: float = (getUtcDateTime() - self.control_point).total_seconds()  # Секунд прошло с последнего запроса.
                    self.printInConsole('{0} из {1} ({2:.2f}с)'.format(instrument_number, instruments_count, delta))
                else:
                    self.printInConsole('{0} из {1}'.format(instrument_number, instruments_count))
                self.control_point = getUtcDateTime()  # Промежуточная точка отсчёта времени.
                '''-----------------------------------------------------------------'''

                response = getForecast(token=self.token.token, uid=uid)
                assert response.request_occurred, 'Запрос прогнозов не был произведён!'
                self.request_count += 1  # Подсчитываем запрос.

                self.releaseSemaphore_signal.emit(self.semaphore, 1)  # Освобождаем ресурсы семафора из основного потока.

                '''-----------------------Сообщаем об ошибке-----------------------'''
                if response.request_error_flag:
                    if not response.request_error.code == StatusCode.NOT_FOUND:
                        self.printInConsole('RequestError {0}'.format(response.request_error))
                elif response.exception_flag:
                    self.printInConsole('Exception {0}'.format(response.exception))
                elif response.ifDataSuccessfullyReceived():
                    self.consensuses_count += 1  # Подсчитываем полученный прогноз.
                '''----------------------------------------------------------------'''
                """=============================================================================="""
                try_count += 1

            forecasts: GetForecastResponse | None = response.response_data if response.ifDataSuccessfullyReceived() else None
            if forecasts is None:
                if self.isInterruptionRequested():
                    self.printInConsole('Поток прерван.')
                    break
                continue  # Если поток был прерван или если информация не была получена.
            self.forecastsReceived.emit(forecasts)

    @property
    def instruments_count(self) -> int:
        """Количество инструментов."""
        return len(self.__instruments_uids)


class ProgressThreadManagerBar(QtWidgets.QHBoxLayout):
    """Строка progressBar'а с кнопками управления потоком."""

    class PlayButtonNames(StrEnum):
        PLAY = 'Пуск'
        PAUSE = 'Пауза'

    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self.setContentsMargins(0, 0, 0, 0)
        self.setSpacing(4)

        self.play_button = QtWidgets.QPushButton(text=self.PlayButtonNames.PLAY, parent=parent)
        self.play_button.setEnabled(False)
        self.addWidget(self.play_button, 0)

        self.stop_button = QtWidgets.QPushButton(text='Стоп', parent=parent)
        self.stop_button.setEnabled(False)
        self.addWidget(self.stop_button, 0)

        self.__progressBar = ProgressBar_DataReceiving(parent=parent)
        self.addWidget(self.__progressBar, 1)

    def setPlayButtonName(self, name: ProgressThreadManagerBar.PlayButtonNames):
        self.play_button.setText(name)

    def setRange(self, minimum: int, maximum: int):
        """Устанавливает минимум и максимум для progressBar'а."""
        self.__progressBar.setRange(minimum, maximum)

    def setValue(self, value: int) -> None:
        self.__progressBar.setValue(value)

    def reset(self):
        """Сбрасывает progressBar."""
        self.__progressBar.reset()


class ForecastsReceivingGroupBox(QtWidgets.QGroupBox):
    """Панель получения прогнозов."""
    class Status(Enum):
        """Статус потока."""
        START_NOT_POSSIBLE = 0  # Поток не запущен. Запуск потока невозможен.
        START_POSSIBLE = 1  # Поток не запущен. Возможен запуск потока.
        RUNNING = 2  # Поток запущен.
        PAUSE = 3  # Поток приостановлен.
        FINISHED = 4  # Поток завершился.

    def __init__(self, tokens_model: TokenListModel, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)

        verticalLayout_main = QtWidgets.QVBoxLayout(self)
        verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        verticalLayout_main.setSpacing(2)

        self.titlebar = TitleWithCount(title='ПОЛУЧЕНИЕ ПРОГНОЗОВ', count_text='0')
        verticalLayout_main.addLayout(self.titlebar, 0)

        self.token_bar = TokenSelectionBar(tokens_model=tokens_model)
        verticalLayout_main.addLayout(self.token_bar, 0)

        self.progressBar = ProgressThreadManagerBar()
        verticalLayout_main.addLayout(self.progressBar, 0)

        verticalLayout_main.addStretch(1)

        self.__instruments_uids: list[str] = []
        self.__forecasts_receiving_thread: ForecastsThread | None = None
        self.__current_status: ForecastsReceivingGroupBox.Status = self.Status.START_NOT_POSSIBLE

        '''------------------Дескрипторы соединений с кнопками управления потоком------------------'''
        self.thread_start_connection: QtCore.QMetaObject.Connection = QtCore.QMetaObject.Connection()
        self.thread_pause_connection: QtCore.QMetaObject.Connection = QtCore.QMetaObject.Connection()
        self.thread_resume_connection: QtCore.QMetaObject.Connection = QtCore.QMetaObject.Connection()
        self.thread_stop_connection: QtCore.QMetaObject.Connection = QtCore.QMetaObject.Connection()

        self.thread_finished_connection: QtCore.QMetaObject.Connection = QtCore.QMetaObject.Connection()
        '''----------------------------------------------------------------------------------------'''

        @QtCore.pyqtSlot(TokenClass)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
        def __onTokenSelected(token: TokenClass):
            self.token = token

        @QtCore.pyqtSlot()  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
        def __onTokenReset():
            self.token = None

        self.token_bar.tokenSelected.connect(__onTokenSelected)
        self.token_bar.tokenReset.connect(__onTokenReset)

    @property
    def uids(self) -> list[str]:
        return self.__instruments_uids

    def __onParameterChanged(self, token: TokenClass | None, uids: list[str]):
        self.current_status = self.Status.START_NOT_POSSIBLE if token is None or not uids else self.Status.START_POSSIBLE

    @property
    def token(self) -> TokenClass | None:
        return self.token_bar.token

    @token.setter
    def token(self, token: TokenClass | None):
        self.__onParameterChanged(token=token, uids=self.uids)

    @property
    def current_status(self) -> ForecastsReceivingGroupBox.Status:
        return self.__current_status

    '''--------------------------------Слоты контролирования потока--------------------------------'''
    @QtCore.pyqtSlot()  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
    def __startThread(self):
        """Запускает или возобновляет работу потока получения исторических свечей."""
        self.current_status = self.Status.RUNNING

    @QtCore.pyqtSlot()  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
    def __pauseThread(self):
        """Приостанавливает поток получения исторических свечей."""
        self.current_status = self.Status.PAUSE

    @QtCore.pyqtSlot()  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
    def __stopThread(self):
        """Останавливает поток получения исторических свечей."""
        self.current_status = self.Status.START_POSSIBLE

    @QtCore.pyqtSlot()  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
    def __onFinishedThread(self):
        """Выполняется после завершения потока."""
        print('{0}: Прогнозы получены по {1} инструментам из {2}.'.format(self.__forecasts_receiving_thread.__class__.__name__, self.__forecasts_receiving_thread.consensuses_count, self.__forecasts_receiving_thread.instruments_count))
        self.current_status = self.Status.FINISHED
    '''--------------------------------------------------------------------------------------------'''

    @current_status.setter
    def current_status(self, status: ForecastsReceivingGroupBox.Status):
        print('Статус: {0} -> {1}.'.format(self.current_status.name, status.name))

        def stopThread():
            self.__forecasts_receiving_thread.requestInterruption()  # Сообщаем потоку о том, что надо завершиться.
            self.__forecasts_receiving_thread.wait()  # Ждём завершения потока.
            self.__forecasts_receiving_thread = None

        match self.current_status:
            case self.Status.START_NOT_POSSIBLE:
                match status:
                    case self.Status.START_NOT_POSSIBLE:
                        return
                    case self.Status.START_POSSIBLE:
                        self.thread_start_connection = self.progressBar.play_button.clicked.connect(self.__startThread)
                        self.progressBar.play_button.setEnabled(True)
                    case self.Status.RUNNING:
                        raise SystemError('Поток не может перейти из состояния {0} в состояние {1}!'.format(self.current_status.name, status.name))
                    case self.Status.PAUSE:
                        raise SystemError('Поток не может перейти из состояния {0} в состояние {1}!'.format(self.current_status.name, status.name))
                    case self.Status.FINISHED:
                        raise SystemError('Поток не может перейти из состояния {0} в состояние {1}!'.format(self.current_status.name, status.name))
                    case _:
                        raise ValueError('Неверный статус потока!')
            case self.Status.START_POSSIBLE:
                match status:
                    case self.Status.START_NOT_POSSIBLE:
                        self.progressBar.play_button.setEnabled(False)
                        if not self.progressBar.play_button.disconnect(self.thread_start_connection):
                            raise SystemError('Не удалось отключить слот!')
                    case self.Status.START_POSSIBLE:
                        return
                    case self.Status.RUNNING:
                        self.progressBar.play_button.setEnabled(False)
                        self.progressBar.setPlayButtonName(name=ProgressThreadManagerBar.PlayButtonNames.PAUSE)

                        if not self.progressBar.play_button.disconnect(self.thread_start_connection):
                            raise SystemError('Не удалось отключить слот!')

                        '''------------------------------------Запуск потока------------------------------------'''
                        assert self.__forecasts_receiving_thread is None
                        self.__forecasts_receiving_thread = ForecastsThread(token=self.token, uids=self.uids, parent=self)

                        @QtCore.pyqtSlot(int, int)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
                        def __setRange(minimum: int, maximum: int):
                            if self.__forecasts_receiving_thread is not None:
                                self.progressBar.setRange(minimum, maximum)

                        self.__forecasts_receiving_thread.setProgressBarRange_signal.connect(__setRange)

                        @QtCore.pyqtSlot(int)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
                        def __setValue(value: int):
                            if self.__forecasts_receiving_thread is not None:
                                self.progressBar.setValue(value)

                        self.__forecasts_receiving_thread.setProgressBarValue_signal.connect(__setValue)

                        self.__forecasts_receiving_thread.forecastsReceived.connect(MainConnection.insertForecasts)
                        self.thread_finished_connection = self.__forecasts_receiving_thread.finished.connect(self.__onFinishedThread)

                        self.__forecasts_receiving_thread.start()  # Запускаем поток.
                        '''-------------------------------------------------------------------------------------'''

                        self.thread_pause_connection = self.progressBar.play_button.clicked.connect(self.__pauseThread)
                        self.thread_stop_connection = self.progressBar.stop_button.clicked.connect(self.__stopThread)

                        self.progressBar.stop_button.setEnabled(True)
                        self.progressBar.play_button.setEnabled(True)
                    case self.Status.PAUSE:
                        raise SystemError('Поток не может перейти из состояния {0} в состояние {1}!'.format(self.current_status.name, status.name))
                    case self.Status.FINISHED:
                        raise SystemError('Поток не может перейти из состояния {0} в состояние {1}!'.format(self.current_status.name, status.name))
                    case _:
                        raise ValueError('Неверный статус потока!')
            case self.Status.RUNNING:
                match status:
                    case self.Status.START_NOT_POSSIBLE:
                        self.progressBar.play_button.setEnabled(False)
                        self.progressBar.stop_button.setEnabled(False)

                        '''-------------------------Останавливаем поток-------------------------'''
                        assert self.__forecasts_receiving_thread is not None
                        if not self.__forecasts_receiving_thread.disconnect(self.thread_finished_connection):
                            raise SystemError('Не удалось отключить слот!')
                        stopThread()
                        '''---------------------------------------------------------------------'''

                        if not self.progressBar.play_button.disconnect(self.thread_pause_connection):
                            raise SystemError('Не удалось отключить слот!')

                        if not self.progressBar.stop_button.disconnect(self.thread_stop_connection):
                            raise SystemError('Не удалось отключить слот!')

                        self.progressBar.reset()  # Сбрасываем progressBar.
                        self.progressBar.setPlayButtonName(name=ProgressThreadManagerBar.PlayButtonNames.PLAY)
                    case self.Status.START_POSSIBLE:
                        self.progressBar.play_button.setEnabled(False)
                        self.progressBar.stop_button.setEnabled(False)

                        '''-------------------------Останавливаем поток-------------------------'''
                        assert self.__forecasts_receiving_thread is not None
                        if not self.__forecasts_receiving_thread.disconnect(self.thread_finished_connection):
                            raise SystemError('Не удалось отключить слот!')
                        stopThread()
                        '''---------------------------------------------------------------------'''

                        self.progressBar.setPlayButtonName(name=ProgressThreadManagerBar.PlayButtonNames.PLAY)
                        self.progressBar.reset()  # Сбрасываем progressBar.

                        if not self.progressBar.play_button.disconnect(self.thread_pause_connection):
                            raise SystemError('Не удалось отключить слот!')

                        if not self.progressBar.stop_button.disconnect(self.thread_stop_connection):
                            raise SystemError('Не удалось отключить слот!')

                        self.thread_start_connection = self.progressBar.play_button.clicked.connect(self.__startThread)
                        self.progressBar.play_button.setEnabled(True)
                    case self.Status.RUNNING:
                        return
                    case self.Status.PAUSE:
                        self.progressBar.play_button.setEnabled(False)
                        self.progressBar.stop_button.setEnabled(False)

                        self.__forecasts_receiving_thread.pause()

                        self.progressBar.setPlayButtonName(name=ProgressThreadManagerBar.PlayButtonNames.PLAY)

                        if not self.progressBar.play_button.disconnect(self.thread_pause_connection):
                            raise SystemError('Не удалось отключить слот!')

                        self.thread_resume_connection = self.progressBar.play_button.clicked.connect(self.__startThread)

                        self.progressBar.play_button.setEnabled(True)
                        self.progressBar.stop_button.setEnabled(True)
                    case self.Status.FINISHED:
                        self.progressBar.play_button.setEnabled(False)
                        self.progressBar.stop_button.setEnabled(False)
                        self.progressBar.setPlayButtonName(name=ProgressThreadManagerBar.PlayButtonNames.PLAY)

                        if not self.__forecasts_receiving_thread.isFinished():
                            raise SystemError('Поток должен был быть завершён!')
                        if not self.__forecasts_receiving_thread.disconnect(self.thread_finished_connection):
                            raise SystemError('Не удалось отключить слот!')
                        self.__forecasts_receiving_thread = None

                        if not self.progressBar.play_button.disconnect(self.thread_pause_connection):
                            raise SystemError('Не удалось отключить слот!')

                        if not self.progressBar.stop_button.disconnect(self.thread_stop_connection):
                            raise SystemError('Не удалось отключить слот!')

                        self.thread_start_connection = self.progressBar.play_button.clicked.connect(self.__startThread)
                        self.progressBar.play_button.setEnabled(True)
                    case _:
                        raise ValueError('Неверный статус потока!')
            case self.Status.PAUSE:
                match status:
                    case self.Status.START_NOT_POSSIBLE:
                        self.progressBar.play_button.setEnabled(False)
                        self.progressBar.stop_button.setEnabled(False)
                        self.progressBar.setPlayButtonName(name=ProgressThreadManagerBar.PlayButtonNames.PLAY)

                        '''-------------------------Останавливаем поток-------------------------'''
                        assert self.__forecasts_receiving_thread is not None
                        if not self.__forecasts_receiving_thread.disconnect(self.thread_finished_connection):
                            raise SystemError('Не удалось отключить слот!')
                        self.__forecasts_receiving_thread.resume()  # Возобновляем работу потока, чтобы он мог безопасно завершиться.
                        stopThread()
                        '''---------------------------------------------------------------------'''

                        self.progressBar.reset()  # Сбрасываем progressBar.

                        if not self.progressBar.play_button.disconnect(self.thread_resume_connection):
                            raise SystemError('Не удалось отключить слот!')
                    case self.Status.START_POSSIBLE:
                        self.progressBar.play_button.setEnabled(False)
                        self.progressBar.stop_button.setEnabled(False)

                        '''-------------------------Останавливаем поток-------------------------'''
                        assert self.__forecasts_receiving_thread is not None
                        if not self.__forecasts_receiving_thread.disconnect(self.thread_finished_connection):
                            raise SystemError('Не удалось отключить слот!')
                        self.__forecasts_receiving_thread.resume()  # Возобновляем работу потока, чтобы он мог безопасно завершиться.
                        stopThread()
                        '''---------------------------------------------------------------------'''

                        self.progressBar.reset()  # Сбрасываем progressBar.
                        self.progressBar.setPlayButtonName(name=ProgressThreadManagerBar.PlayButtonNames.PLAY)

                        if not self.progressBar.play_button.disconnect(self.thread_resume_connection):
                            raise SystemError('Не удалось отключить слот!')

                        self.thread_start_connection = self.progressBar.play_button.clicked.connect(self.__startThread)
                        self.progressBar.play_button.setEnabled(True)
                    case self.Status.RUNNING:
                        self.progressBar.play_button.setEnabled(False)
                        self.progressBar.stop_button.setEnabled(False)

                        self.__forecasts_receiving_thread.resume()

                        self.progressBar.setPlayButtonName(name=ProgressThreadManagerBar.PlayButtonNames.PAUSE)

                        if not self.progressBar.play_button.disconnect(self.thread_resume_connection):
                            raise SystemError('Не удалось отключить слот!')

                        self.thread_pause_connection = self.progressBar.play_button.clicked.connect(self.__pauseThread)

                        self.progressBar.stop_button.setEnabled(True)
                        self.progressBar.play_button.setEnabled(True)
                    case self.Status.PAUSE:
                        return
                    case self.Status.FINISHED:
                        # self.progressBar.play_button.setEnabled(False)
                        # self.progressBar.stop_button.setEnabled(False)
                        # self.progressBar.setPlayButtonName(name=ProgressThreadManagerBar.PlayButtonNames.PLAY)
                        #
                        # if not self.__forecasts_receiving_thread.isFinished():
                        #     raise SystemError('Поток должен был быть завершён!')
                        # if not self.__forecasts_receiving_thread.disconnect(self.thread_finished_connection):
                        #     raise SystemError('Не удалось отключить слот!')
                        # self.__forecasts_receiving_thread = None
                        #
                        # if not self.progressBar.play_button.disconnect(self.thread_start_connection):
                        #     raise SystemError('Не удалось отключить слот!')
                        #
                        # if not self.progressBar.stop_button.disconnect(self.thread_stop_connection):
                        #     raise SystemError('Не удалось отключить слот!')
                        #
                        # self.thread_start_connection = self.progressBar.play_button.clicked.connect(self.__startThread)
                        # self.progressBar.play_button.setEnabled(True)

                        raise SystemError('Поток не может перейти из состояния {0} в состояние {1}!'.format(self.current_status.name, status.name))
                    case _:
                        raise ValueError('Неверный статус потока!')
            case self.Status.FINISHED:
                match status:
                    case self.Status.START_NOT_POSSIBLE:
                        self.progressBar.play_button.setEnabled(False)

                        assert self.__forecasts_receiving_thread is None
                        self.progressBar.reset()  # Сбрасываем progressBar.

                        if not self.progressBar.play_button.disconnect(self.thread_start_connection):
                            raise SystemError('Не удалось отключить слот!')
                    case self.Status.START_POSSIBLE:
                        self.progressBar.play_button.setEnabled(False)

                        assert self.__forecasts_receiving_thread is None
                        self.progressBar.reset()  # Сбрасываем progressBar.

                        if not self.progressBar.play_button.disconnect(self.thread_start_connection):
                            raise SystemError('Не удалось отключить слот!')

                        self.thread_start_connection = self.progressBar.play_button.clicked.connect(self.__startThread)
                        self.progressBar.play_button.setEnabled(True)
                    case self.Status.RUNNING:
                        self.progressBar.play_button.setEnabled(False)
                        self.progressBar.setPlayButtonName(name=ProgressThreadManagerBar.PlayButtonNames.PAUSE)

                        if not self.progressBar.play_button.disconnect(self.thread_start_connection):
                            raise SystemError('Не удалось отключить слот!')

                        '''------------------------------------Запуск потока------------------------------------'''
                        assert self.__forecasts_receiving_thread is None
                        self.__forecasts_receiving_thread = ForecastsThread(token=self.token, uids=self.uids, parent=self)

                        @QtCore.pyqtSlot(int, int)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
                        def __setRange(minimum: int, maximum: int):
                            if self.__forecasts_receiving_thread is not None:
                                self.progressBar.setRange(minimum, maximum)

                        self.__forecasts_receiving_thread.setProgressBarRange_signal.connect(__setRange)

                        @QtCore.pyqtSlot(int)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
                        def __setValue(value: int):
                            if self.__forecasts_receiving_thread is not None:
                                self.progressBar.setValue(value)

                        self.__forecasts_receiving_thread.setProgressBarValue_signal.connect(__setValue)

                        self.__forecasts_receiving_thread.forecastsReceived.connect(MainConnection.insertForecasts)
                        self.thread_finished_connection = self.__forecasts_receiving_thread.finished.connect(self.__onFinishedThread)

                        self.__forecasts_receiving_thread.start()  # Запускаем поток.
                        '''-------------------------------------------------------------------------------------'''

                        self.thread_pause_connection = self.progressBar.play_button.clicked.connect(self.__pauseThread)
                        self.thread_stop_connection = self.progressBar.stop_button.clicked.connect(self.__stopThread)

                        self.progressBar.stop_button.setEnabled(True)
                        self.progressBar.play_button.setEnabled(True)
                    case self.Status.PAUSE:
                        raise SystemError('Поток не может перейти из состояния {0} в состояние {1}!'.format(self.current_status.name, status.name))
                    case self.Status.FINISHED:
                        return
                    case _:
                        raise ValueError('Неверный статус потока!')
            case _:
                raise ValueError('Неверный статус потока!')

        self.__current_status = status

    def setInstruments(self, instruments_uids: list[str]):
        self.__instruments_uids = instruments_uids
        self.__onParameterChanged(token=self.token, uids=self.uids)
        self.titlebar.setCount(str(len(self.uids)))


class ForecastsTitle(QtWidgets.QHBoxLayout):
    stateChanged: QtCore.pyqtSignal = QtCore.pyqtSignal(bool)

    def __init__(self, title: str, count_text: str = '0', parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self.setSpacing(0)
        self.addSpacing(10)

        def __stateChanged(state: int):
            match state:
                case 2:  # QtCore.Qt.CheckState.Checked
                    return self.stateChanged.emit(True)
                case 0:  # QtCore.Qt.CheckState.Unchecked
                    return self.stateChanged.emit(False)
                case _:
                    raise ValueError('Неизвестное значение checkBox\'а!')

        self.__checkBox = QtWidgets.QCheckBox(text='Только последние', parent=parent)
        self.__checkBox.setChecked(True)
        self.__checkBox.stateChanged.connect(__stateChanged)
        self.addWidget(self.__checkBox, 1)

        self.addWidget(TitleLabel(text=title, parent=parent), 0)

        self.__label_count = QtWidgets.QLabel(text=count_text, parent=parent)
        self.__label_count.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.addWidget(self.__label_count, 1)

        self.addSpacing(10)

    def isChecked(self) -> bool:
        return self.__checkBox.isChecked()

    def setCount(self, count_text: str | None):
        self.__label_count.setText(count_text)


class ForecastsPage(QtWidgets.QWidget):
    """Страница прогнозов."""

    @print_function_runtime
    def __init__(self, tokens_model: TokenListModel, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)

        verticalLayout_main = QtWidgets.QVBoxLayout(self)
        verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        verticalLayout_main.setSpacing(2)

        horizontalLayout_top = QtWidgets.QHBoxLayout()
        horizontalLayout_top.setSpacing(2)

        self.groupBox_instrument_selection = ForecastsInstrumentSelectionGroupBox(tokens_model=tokens_model, parent=self)
        horizontalLayout_top.addWidget(self.groupBox_instrument_selection, 1)

        verticalLayout_progressBar = QtWidgets.QVBoxLayout()
        verticalLayout_progressBar.setSpacing(0)
        self.progressBar = ForecastsReceivingGroupBox(tokens_model=tokens_model, parent=self)
        self.progressBar.setInstruments(self.groupBox_instrument_selection.uids)
        self.groupBox_instrument_selection.instrumentsListChanged.connect(self.progressBar.setInstruments)
        verticalLayout_progressBar.addWidget(self.progressBar, 0)
        verticalLayout_progressBar.addStretch(1)
        horizontalLayout_top.addLayout(verticalLayout_progressBar, 1)

        verticalLayout_main.addLayout(horizontalLayout_top, 0)

        '''---------------------------------------Нижняя часть---------------------------------------'''
        layoutWidget = QtWidgets.QGroupBox()

        verticalLayout_forecasts_view = QtWidgets.QVBoxLayout(layoutWidget)
        verticalLayout_forecasts_view.setContentsMargins(2, 2, 2, 2)
        verticalLayout_forecasts_view.setSpacing(2)

        __titlebar = ForecastsTitle(title='ПРОГНОЗЫ', count_text='0')
        verticalLayout_forecasts_view.addLayout(__titlebar, 0)

        self.forecasts_view = MyTreeView(parent=layoutWidget)
        forecasts_model = ForecastsModel(instruments_uids=self.uids, last_fulls_flag=__titlebar.isChecked(), parent=self.forecasts_view)
        forecasts_proxy_model = ForecastsProxyModel(source_model=forecasts_model, parent=self.forecasts_view)
        self.forecasts_view.setModel(forecasts_proxy_model)  # Подключаем модель к таблице.
        self.forecasts_view.setSortingEnabled(True)  # Разрешаем сортировку.

        verticalLayout_forecasts_view.addWidget(self.forecasts_view, 1)

        verticalLayout_main.addWidget(layoutWidget, 1)
        '''------------------------------------------------------------------------------------------'''

        def __onModelUpdated():
            """Выполняется при изменении модели."""
            __titlebar.setCount(str(forecasts_model.rowCount(parent=QtCore.QModelIndex())))
            # self.forecasts_view.expandAll()  # Разворачивает все элементы.
            self.forecasts_view.resizeColumnsToContents()  # Авторазмер столбцов под содержимое.

        __onModelUpdated()
        forecasts_model.modelReset.connect(__onModelUpdated)

        __titlebar.stateChanged.connect(forecasts_model.setOnlyLastFlag)

        self.groupBox_instrument_selection.instrumentsListChanged.connect(forecasts_model.setInstrumentsUids)

        @QtCore.pyqtSlot(QtCore.QModelIndex)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
        def __onExpanded(index: QtCore.QModelIndex):
            self.forecasts_view.resizeColumnsToContents()  # Авторазмер столбцов под содержимое.

        self.forecasts_view.expanded.connect(__onExpanded)

    @property
    def uids(self) -> list[str]:
        return self.groupBox_instrument_selection.uids
