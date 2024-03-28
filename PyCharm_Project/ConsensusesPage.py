from __future__ import annotations
import typing
from PyQt6 import QtCore, QtWidgets, QtSql, QtGui
from tinkoff.invest.schemas import GetConsensusForecastsResponse, PageResponse, Page, Recommendation
from Classes import TokenClass, MyConnection, ColumnWithHeader, Header, print_function_runtime, MyConsensusForecastsItem
from DatabaseWidgets import TokenSelectionBar, ComboBox_Status, ComboBox_InstrumentType
from MyDatabase import MainConnection
from MyDateTime import reportSignificantInfoFromDateTime
from MyQuotation import MyQuotation
from MyRequests import getConsensusForecasts, MyResponse
from PagesClasses import TitleLabel
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

        # __select_consensuses_uids: str = 'SELECT DISTINCT \"uid\" FROM \"{0}\"'.format(
        #     MyConnection.CONSENSUS_FORECASTS_TABLE
        # )

        __select_consensuses_uids: str = '''SELECT \"uid\" FROM (SELECT \"asset_uid\", \"uid\" FROM \"{0}\") AS \"AI\" 
        WHERE \"AI\".\"asset_uid\" IN (SELECT DISTINCT \"asset_uid\" FROM \"{1}\")'''.format(
            MyConnection.ASSET_INSTRUMENTS_TABLE,
            MyConnection.CONSENSUS_FORECASTS_TABLE
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


class ForecastsRequest(QtWidgets.QGroupBox):
    def __init__(self, tokens_model: TokenListModel, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)

        verticalLayout_main = QtWidgets.QVBoxLayout(self)
        verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        verticalLayout_main.setSpacing(2)

        titlebar = TitleLabel(text='ЗАПРОС', parent=self)
        verticalLayout_main.addWidget(titlebar, 0)

        self.token_bar = TokenSelectionBar(tokens_model=tokens_model, parent=self)
        self.__token: TokenClass | None = self.token_bar.token

        @QtCore.pyqtSlot(TokenClass)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
        def __onTokenSelected(token: TokenClass):
            self.token = token

        @QtCore.pyqtSlot()  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
        def __onTokenReset():
            self.token = None

        self.token_bar.tokenSelected.connect(__onTokenSelected)
        self.token_bar.tokenReset.connect(__onTokenReset)
        verticalLayout_main.addLayout(self.token_bar, 0)

        horizontalLayout_limit = QtWidgets.QHBoxLayout(self)
        limit_label = QtWidgets.QLabel(text='Кол-во записей:', parent=self)
        horizontalLayout_limit.addWidget(limit_label, 0)
        horizontalLayout_limit.addSpacing(4)
        self.limit_box = QtWidgets.QSpinBox(parent=self)
        self.limit_box.setSpecialValueText('По умолчанию')
        self.limit_box.setMaximum(9999)
        horizontalLayout_limit.addWidget(self.limit_box, 0)
        horizontalLayout_limit.addStretch(1)
        verticalLayout_main.addLayout(horizontalLayout_limit, 0)

        horizontalLayout_page = QtWidgets.QHBoxLayout(self)
        page_label = QtWidgets.QLabel(text='Страница:', parent=self)
        horizontalLayout_page.addWidget(page_label, 0)
        horizontalLayout_page.addSpacing(4)
        self.page_box = QtWidgets.QSpinBox(parent=self)
        horizontalLayout_page.addWidget(self.page_box, 0)
        horizontalLayout_page.addStretch(1)
        verticalLayout_main.addLayout(horizontalLayout_page, 0)

        verticalLayout_main.addStretch(1)

        @QtCore.pyqtSlot()  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
        def __onClicked():
            limit: int = self.limit_box.value()
            page_number: int = self.page_box.value()

            page: Page | None
            if limit >= 0:
                if page_number >= 0:
                    page = Page(limit=limit, page_number=page_number)
                else:
                    page = Page(limit=limit)
            else:
                if page_number >= 0:
                    page = Page(page_number=page_number)
                else:
                    page = None

            response: MyResponse = getConsensusForecasts(token=self.token.token, page=page)
            data: GetConsensusForecastsResponse | None = response.response_data if response.ifDataSuccessfullyReceived() else None
            if data is not None:
                page: PageResponse = data.page
                print('page: limit = {0}, page_number = {1}, total_count = {2}, count = {3}'.format(page.limit, page.page_number, page.total_count, len(data.items)))
                MainConnection.insertConsensusForecasts(data.items)

            # '''---------------------------------------___---------------------------------------'''
            # response: MyResponse = getConsensusForecasts(token=self.token.token, page=Page(limit=3000, page_number=0))
            # data: GetConsensusForecastsResponse | None = response.response_data if response.ifDataSuccessfullyReceived() else None
            # if data is not None:
            #     page: PageResponse = data.page
            #     print('page: limit = {0}, page_number = {1}, total_count = {2}, count = {3}'.format(page.limit, page.page_number, page.total_count, len(data.items)))
            #     MainConnection.insertConsensusForecasts(data.items)
            #
            #     assert page.page_number == 0
            #     pages_count: int = ceil(page.total_count / page.limit)
            #     for i in range(1, pages_count):
            #         current_request_page: Page = Page(limit=page.limit, page_number=i)
            #         page_response: MyResponse = getConsensusForecasts(token=self.token.token, page=current_request_page)
            #         current_data: GetConsensusForecastsResponse | None = page_response.response_data if page_response.ifDataSuccessfullyReceived() else None
            #         if current_data is not None:
            #             response_page: PageResponse = current_data.page
            #             print('page: limit = {0}, page_number = {1}, total_count = {2}, count = {3}'.format(response_page.limit, response_page.page_number, response_page.total_count, len(current_data.items)))
            #             MainConnection.insertConsensusForecasts(current_data.items)
            # '''---------------------------------------------------------------------------------'''

        self.request_button = QtWidgets.QPushButton(text='ЗАПРОСИТЬ', parent=self)
        if self.token is None:
            self.request_button.setEnabled(False)
        self.request_button.clicked.connect(__onClicked)
        verticalLayout_main.addWidget(self.request_button, 0, QtCore.Qt.AlignmentFlag.AlignCenter)

    @property
    def token(self) -> TokenClass | None:
        return self.token_bar.token

    @token.setter
    def token(self, token: TokenClass | None):
        self.__token = token
        if self.token is None:
            self.request_button.setEnabled(False)
        else:
            self.request_button.setEnabled(True)


class InstrumentsSelectionGroupBox(QtWidgets.QGroupBox):
    """Панель выбора инструментов."""
    instrumentsListChanged: QtCore.pyqtSignal = QtCore.pyqtSignal(list)  # Сигнал испускается при изменении списка инструментов.

    def __init__(self, tokens_model: TokenListModel, parent: QtWidgets.QWidget | None = None):
        self.__instruments_uids: list[str] = []
        super().__init__(parent=parent)

        verticalLayout_main = QtWidgets.QVBoxLayout(self)
        verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        verticalLayout_main.setSpacing(2)

        '''------------------------------Заголовок------------------------------'''
        horizontalLayout_title = QtWidgets.QHBoxLayout(self)
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
        self.__token_bar = TokenSelectionBar(tokens_model=tokens_model, parent=self)
        verticalLayout_main.addLayout(self.__token_bar, 0)
        '''--------------------------------------------------------------'''

        '''---------------Строка выбора статуса инструмента---------------'''
        horizontalLayout_status = QtWidgets.QHBoxLayout(self)
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
        horizontalLayout_instrument_type = QtWidgets.QHBoxLayout(self)
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
        horizontalLayout_instrument = QtWidgets.QHBoxLayout(self)
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


class ConsensusesModel(QtCore.QAbstractTableModel):
    """Модель консенсус-прогнозов."""
    def __init__(self, instruments_uids: list[str], last_consensuses_flag: bool, parent: QtCore.QObject | None = None):
        super().__init__(parent=parent)
        self.__instruments_uids: list[str] = instruments_uids
        self.__last_consensuses_flag: bool = last_consensuses_flag  # Если True, то модель должна отображать только последние прогнозы.
        self.__consensuses: list[MyConsensusForecastsItem] = []

        POSITIVE_COLOR: QtGui.QBrush = QtGui.QBrush(QtCore.Qt.GlobalColor.darkGreen)
        NEUTRAL_COLOR: QtGui.QBrush = QtGui.QBrush(QtCore.Qt.GlobalColor.darkYellow)
        NEGATIVE_COLOR: QtGui.QBrush = QtGui.QBrush(QtCore.Qt.GlobalColor.darkRed)

        BUY: str = 'ПОКУПАТЬ'
        HOLD: str = 'ДЕРЖАТЬ'
        SELL: str = 'ПРОДАВАТЬ'

        self.columns: tuple[ColumnWithHeader, ...] = (
            ColumnWithHeader(
                header=Header(
                    title='consensus_uid',
                    tooltip='uid идентификатор'
                ),
                data_function=lambda cf: cf.uid
            ),
            ColumnWithHeader(
                header=Header(
                    title='asset_uid',
                    tooltip='uid идентификатор актива'
                ),
                data_function=lambda cf: cf.asset_uid
            ),
            ColumnWithHeader(
                header=Header(
                    title='Создание записи',
                    tooltip='Дата и время создания записи'
                ),
                data_function=lambda cf: cf.created_at,
                display_function=lambda cf: str(cf.created_at),
                sort_role=QtCore.Qt.ItemDataRole.UserRole,
                lessThan=lambda left, right, role: left.data(role=role) < right.data(role=role)
            ),
            ColumnWithHeader(
                header=Header(
                    title='Целевая цена',
                    tooltip='Целевая цена на 12 месяцев'
                ),
                data_function=lambda cf: cf.best_target_price,
                display_function=lambda cf: '{0} {1}'.format(MyQuotation.__str__(cf.best_target_price, ndigits=8, delete_decimal_zeros=True), cf.currency)
            ),
            ColumnWithHeader(
                header=Header(
                    title='Мин. цена',
                    tooltip='Минимальная прогнозная цена'
                ),
                data_function=lambda cf: cf.best_target_low,
                display_function=lambda cf: '{0} {1}'.format(MyQuotation.__str__(cf.best_target_low, ndigits=8, delete_decimal_zeros=True), cf.currency)
            ),
            ColumnWithHeader(
                header=Header(
                    title='Макс. цена',
                    tooltip='Максимальная прогнозная цена'
                ),
                data_function=lambda cf: cf.best_target_high,
                display_function=lambda cf: '{0} {1}'.format(MyQuotation.__str__(cf.best_target_high, ndigits=8, delete_decimal_zeros=True), cf.currency)
            ),
            ColumnWithHeader(
                header=Header(
                    title='Покупать',
                    tooltip='Количество аналитиков рекомендующих покупать'
                ),
                data_function=lambda cf: cf.total_buy_recommend,
                display_function=lambda cf: str(cf.total_buy_recommend),
                sort_role=QtCore.Qt.ItemDataRole.UserRole,
                lessThan=lambda left, right, role: left.data(role=role) < right.data(role=role)
            ),
            ColumnWithHeader(
                header=Header(
                    title='Держать',
                    tooltip='Количество аналитиков рекомендующих держать'
                ),
                data_function=lambda cf: cf.total_hold_recommend,
                display_function=lambda cf: str(cf.total_hold_recommend),
                sort_role=QtCore.Qt.ItemDataRole.UserRole,
                lessThan=lambda left, right, role: left.data(role=role) < right.data(role=role)
            ),
            ColumnWithHeader(
                header=Header(
                    title='Продавать',
                    tooltip='Количество аналитиков рекомендующих продавать'
                ),
                data_function=lambda cf: cf.total_sell_recommend,
                display_function=lambda cf: str(cf.total_sell_recommend),
                sort_role=QtCore.Qt.ItemDataRole.UserRole,
                lessThan=lambda left, right, role: left.data(role=role) < right.data(role=role)
            ),
            ColumnWithHeader(
                header=Header(
                    title='Консенсус',
                    tooltip='Консенсус-прогноз'
                ),
                data_function=lambda cf: cf.consensus,
                display_function=lambda cf: BUY if cf.consensus == Recommendation.RECOMMENDATION_BUY else SELL if cf.consensus == Recommendation.RECOMMENDATION_SELL else HOLD if cf.consensus == Recommendation.RECOMMENDATION_HOLD else cf.consensus.name,
                foreground_function=lambda cf: POSITIVE_COLOR if cf.consensus == Recommendation.RECOMMENDATION_BUY else NEGATIVE_COLOR if cf.consensus == Recommendation.RECOMMENDATION_SELL else NEUTRAL_COLOR if cf.consensus == Recommendation.RECOMMENDATION_HOLD else QtCore.QVariant()
            ),
            ColumnWithHeader(
                header=Header(
                    title='Дата прогноза',
                    tooltip='Дата прогноза'
                ),
                data_function=lambda cf: cf.prognosis_date,
                display_function=lambda cf: reportSignificantInfoFromDateTime(cf.prognosis_date),
                sort_role=QtCore.Qt.ItemDataRole.UserRole,
                lessThan=lambda left, right, role: left.data(role=role) < right.data(role=role)
            )
        )
        self.__update()

    @print_function_runtime
    def __update(self):
        """Обновляет модель."""
        self.beginResetModel()

        self.__consensuses.clear()

        if self.__last_consensuses_flag:
            self.__consensuses = MainConnection.getLastConsensusesForecastsItems(self.__instruments_uids)
        else:
            self.__consensuses = MainConnection.getConsensusesForecastsItems(self.__instruments_uids)

        self.endResetModel()

    def rowCount(self, parent: QtCore.QModelIndex = ...) -> int:
        return len(self.__consensuses)

    def columnCount(self, parent: QtCore.QModelIndex = ...) -> int:
        return len(self.columns)

    def data(self, index: QtCore.QModelIndex, role: int = ...) -> typing.Any:
        column: ColumnWithHeader = self.columns[index.column()]
        consensus: MyConsensusForecastsItem = self.__consensuses[index.row()]
        return column(role, consensus)

    def headerData(self, section: int, orientation: QtCore.Qt.Orientation, role: int = ...) -> typing.Any:
        if orientation == QtCore.Qt.Orientation.Horizontal:
            column: ColumnWithHeader = self.columns[section]
            return column.header(role=role)
        else:
            return super().headerData(section, orientation, role)

    def setInstrumentsUids(self, instruments_uids: list[str]):
        self.__instruments_uids = instruments_uids
        self.__update()

    def setOnlyLastFlag(self, flag: bool):
        if self.__last_consensuses_flag != flag:
            self.__last_consensuses_flag = flag
            self.__update()


class ConsensusesProxyModel(QtCore.QSortFilterProxyModel):
    def __init__(self, source_model: ConsensusesModel, parent: QtCore.QObject | None = None):
        super().__init__(parent=parent)
        self.setSourceModel(source_model)

    def lessThan(self, left: QtCore.QModelIndex, right: QtCore.QModelIndex) -> bool:
        assert left.column() == right.column()
        column: ColumnWithHeader = self.sourceModel().columns[left.column()]

        if column.lessThan is None:
            return super().lessThan(left, right)  # Сортировка по умолчанию.
        else:
            return column.lessThan(left, right, column.getSortRole)


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


class ConsensusesPage(QtWidgets.QWidget):
    """Страница консенсус-прогнозов."""
    def __init__(self, tokens_model: TokenListModel, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)

        verticalLayout_main = QtWidgets.QVBoxLayout(self)
        verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        verticalLayout_main.setSpacing(2)

        horizontalLayout_top = QtWidgets.QHBoxLayout()
        horizontalLayout_top.setSpacing(2)

        self.groupBox_instruments_selection = InstrumentsSelectionGroupBox(tokens_model=tokens_model, parent=self)
        horizontalLayout_top.addWidget(self.groupBox_instruments_selection, 1)

        request_bar = ForecastsRequest(tokens_model=tokens_model, parent=self)
        horizontalLayout_top.addWidget(request_bar, 1)

        verticalLayout_main.addLayout(horizontalLayout_top, 0)

        '''---------------------------------------Нижняя часть---------------------------------------'''
        bottom_groupBox = QtWidgets.QGroupBox(parent=self)

        verticalLayout_forecasts_view = QtWidgets.QVBoxLayout(bottom_groupBox)
        verticalLayout_forecasts_view.setContentsMargins(2, 2, 2, 2)
        verticalLayout_forecasts_view.setSpacing(2)

        __titlebar = ForecastsTitle(title='КОНСЕНСУС-ПРОГНОЗЫ', count_text='0', parent=bottom_groupBox)
        verticalLayout_forecasts_view.addLayout(__titlebar, 0)

        self.forecasts_view = QtWidgets.QTableView(parent=bottom_groupBox)
        self.forecasts_view.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.forecasts_view.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.forecasts_view.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.forecasts_view.setSortingEnabled(True)
        consensuses_model = ConsensusesModel(instruments_uids=self.uids, last_consensuses_flag=__titlebar.isChecked(), parent=self.forecasts_view)
        consensuses_proxy_model = ConsensusesProxyModel(source_model=consensuses_model, parent=self.forecasts_view)
        self.forecasts_view.setModel(consensuses_proxy_model)  # Подключаем модель к таблице.
        verticalLayout_forecasts_view.addWidget(self.forecasts_view, 1)

        verticalLayout_main.addWidget(bottom_groupBox, 1)
        '''------------------------------------------------------------------------------------------'''

        def __onModelUpdated():
            """Выполняется при изменении модели."""
            __titlebar.setCount(str(consensuses_model.rowCount(parent=QtCore.QModelIndex())))
            self.forecasts_view.resizeColumnsToContents()  # Авторазмер столбцов под содержимое.

        __onModelUpdated()
        consensuses_model.modelReset.connect(__onModelUpdated)

        __titlebar.stateChanged.connect(consensuses_model.setOnlyLastFlag)

        self.groupBox_instruments_selection.instrumentsListChanged.connect(consensuses_model.setInstrumentsUids)

    @property
    def uids(self) -> list[str]:
        return self.groupBox_instruments_selection.uids
