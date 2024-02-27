import typing
from PyQt6 import QtCore, QtWidgets, QtSql
from Classes import MyConnection, TokenClass
from MyBondClass import MyBondClass
from MyDatabase import MainConnection
from MyShareClass import MyShareClass
from PagesClasses import TitleWithCount
from TokenModel import TokenListModel


class InstrumentsStatusModel(QtCore.QAbstractListModel):
    """Модель статусов инструментов. К имеющимся статусам добавлены варианты "-" и "Остальные".
    Вариант "-" соответствует всем имеющимся в БД инструментам.
    Вариант "Остальные" соответствует всем инструментам, которые не попали в таблицу статусов инструментов."""

    class Item:
        def __init__(self, value: str, name: str, tooltip: str | None = None):
            self.__value: str = value  # Значение.
            self.__name: str = name  # Обозначение.
            self.__tooltip: str | None = tooltip  # Подсказка.

        def getValue(self) -> str:
            return self.__value

        def getName(self) -> str:
            return self.__name

        def getTooltip(self) -> str | None:
            return self.__tooltip

    __items: tuple[Item] = (
        Item(value='\"Все инструменты\"',
             name='INSTRUMENT_STATUS_ALL',
             tooltip='Список всех инструментов.'),
        Item(value='\"Базовые инструменты\"',
             name='INSTRUMENT_STATUS_BASE',
             tooltip='Базовый список инструментов (по умолчанию). Инструменты доступные для торговли через TINKOFF INVEST API. Сейчас списки бумаг, доступных из api и других интерфейсах совпадают (за исключением внебиржевых бумаг), но в будущем возможны ситуации, когда списки инструментов будут отличаться.'),
        Item(value='\"Не определён\"',
             name='INSTRUMENT_STATUS_UNSPECIFIED',
             tooltip='Значение не определено.'),
        Item(value='Без статуса',
             name='OTHER_INSTRUMENTS',
             tooltip='Инструменты, которые не попали в таблицу статусов инструментов.'),
        Item(value='Все инструменты в БД',
             name='ALL_INSTRUMENTS_IN_DB',
             tooltip='Все имеющиеся в локальной базе данных инструменты.')
    )

    def rowCount(self, parent: QtCore.QModelIndex = ...) -> int:
        return len(self.__items)

    def data(self, index: QtCore.QModelIndex, role: int = ...) -> typing.Any:
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            return QtCore.QVariant(self.__items[index.row()].getValue())
        elif role == QtCore.Qt.ItemDataRole.UserRole:
            return QtCore.QVariant(self.__items[index.row()].getName())
        elif role == QtCore.Qt.ItemDataRole.ToolTipRole:
            return QtCore.QVariant(self.__items[index.row()].getTooltip())
        else:
            return QtCore.QVariant()


# class GroupBox_InstrumentSelection(QtWidgets.QGroupBox):
#     """Панель выбора инструмента в локальной базе данных."""
#     bondSelected: QtCore.pyqtSignal = QtCore.pyqtSignal(MyBondClass)  # Сигнал испускается при выборе облигации.
#     shareSelected: QtCore.pyqtSignal = QtCore.pyqtSignal(MyShareClass)  # Сигнал испускается при выборе акции.
#     instrumentReset: QtCore.pyqtSignal = QtCore.pyqtSignal()  # Сигнал испускается при сбросе выбранного инструмента.
#
#     class ComboBox_InstrumentType(QtWidgets.QComboBox):
#         typeChanged: QtCore.pyqtSignal = QtCore.pyqtSignal(str)  # Сигнал испускается при изменении выбранного типа.
#         typeReset: QtCore.pyqtSignal = QtCore.pyqtSignal()  # Сигнал испускается при сбросе выбранного типа.
#
#         class InstrumentsTypeModel(QtCore.QAbstractListModel):
#             """Модель типов инструментов."""
#             EMPTY: str = 'Не выбран'
#             PARAMETER: str = 'instrument_type'
#
#             def __init__(self, parent: QtCore.QObject | None = None):
#                 super().__init__(parent=parent)
#                 self._types: list[str] = [self.EMPTY]
#                 self.update()
#
#             def rowCount(self, parent: QtCore.QModelIndex = ...) -> int:
#                 return len(self._types)
#
#             def getInstrumentType(self, row: int) -> str | None:
#                 if row == 0:
#                     return None
#                 else:
#                     return self._types[row]
#
#             def data(self, index: QtCore.QModelIndex, role: int = ...) -> typing.Any:
#                 if role == QtCore.Qt.ItemDataRole.DisplayRole:
#                     return QtCore.QVariant(self._types[index.row()])
#                 elif role == QtCore.Qt.ItemDataRole.UserRole:
#                     return QtCore.QVariant(self.getInstrumentType(index.row()))
#                 else:
#                     return QtCore.QVariant()
#
#             def update(self):
#                 """Обновляет модель."""
#                 self.beginResetModel()
#                 self._types = [self.EMPTY]
#
#                 db: QtSql.QSqlDatabase = MainConnection.getDatabase()
#                 query = QtSql.QSqlQuery(db)
#                 query.setForwardOnly(True)  # Возможно, это ускоряет извлечение данных.
#                 prepare_flag: bool = query.prepare('SELECT DISTINCT \"{0}\" FROM \"{1}\" ORDER BY \"{0}\";'.format(self.PARAMETER, MyConnection.INSTRUMENT_UIDS_TABLE))
#                 assert prepare_flag, query.lastError().text()
#                 exec_flag: bool = query.exec()
#                 assert exec_flag, query.lastError().text()
#
#                 while query.next():
#                     instrument_type: str = query.value(self.PARAMETER)
#                     self._types.append(instrument_type)
#
#                 self.endResetModel()
#
#         def __init__(self, parent: QtWidgets.QWidget | None = ...):
#             super().__init__(parent)
#             self.setModel(self.InstrumentsTypeModel(self))
#             self.currentIndexChanged.connect(self.setInstrumentType)
#
#         @QtCore.pyqtSlot(int)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
#         def setInstrumentType(self, index: int):
#             instrument_type: str | None = self.model().getInstrumentType(index)
#             if instrument_type is None:
#                 self.typeReset.emit()
#             else:
#                 self.typeChanged.emit(instrument_type)
#
#     class ComboBox_Instrument(QtWidgets.QComboBox):
#         instrumentChanged: QtCore.pyqtSignal = QtCore.pyqtSignal(str)  # Сигнал испускается при изменении выбранного инструмента.
#         instrumentReset: QtCore.pyqtSignal = QtCore.pyqtSignal()  # Сигнал испускается при сбросе выбранного инструмента.
#
#         class InstrumentsUidModel(QtCore.QAbstractListModel):
#             """Модель инструментов выбранного типа."""
#             def __init__(self, instrument_type: str | None, parent: QtCore.QObject | None = ...):
#                 super().__init__(parent)
#                 self.__instrument_type: str | None = instrument_type
#                 self.__instruments: list[tuple[str, str]] = []
#                 self.setInstrumentType(instrument_type)
#
#             def rowCount(self, parent: QtCore.QModelIndex = ...) -> int:
#                 return len(self.__instruments) + 1
#
#             def data(self, index: QtCore.QModelIndex, role: int = ...) -> typing.Any:
#                 if role == QtCore.Qt.ItemDataRole.DisplayRole:
#                     row: int = index.row()
#                     if row == 0:
#                         return QtCore.QVariant('Не выбран')
#                     else:
#                         item: (str, str) = self.__instruments[row - 1]
#                         return QtCore.QVariant('{0} | {1}'.format(item[0], item[1]))
#                 elif role == QtCore.Qt.ItemDataRole.UserRole:
#                     return QtCore.QVariant(self.getInstrumentUid(index.row()))
#                 else:
#                     return QtCore.QVariant()
#
#             @staticmethod
#             def getInstrumentTableName(instrument_type: str | None) -> str | None:
#                 """Возвращает название таблицы, хранящей инструменты выбранного типа."""
#                 if instrument_type == 'bond':
#                     return MyConnection.BONDS_TABLE
#                 elif instrument_type == 'share':
#                     return MyConnection.SHARES_TABLE
#                 else:
#                     return None
#
#             def setInstrumentType(self, instrument_type: str | None):
#                 self.beginResetModel()
#                 self.__instrument_type = instrument_type
#                 self.__instruments = []
#
#                 table_name: str | None = self.getInstrumentTableName(self.__instrument_type)
#                 if table_name is None:
#                     self.endResetModel()
#                     return
#
#                 db: QtSql.QSqlDatabase = MainConnection.getDatabase()
#                 query = QtSql.QSqlQuery(db)
#                 query.setForwardOnly(True)  # Возможно, это ускоряет извлечение данных.
#                 prepare_flag: bool = query.prepare('SELECT \"uid\", \"name\" FROM \"{0}\" ORDER BY \"name\";'.format(table_name))
#                 assert prepare_flag, query.lastError().text()
#                 exec_flag: bool = query.exec()
#                 assert exec_flag, query.lastError().text()
#
#                 while query.next():
#                     uid: str = query.value('uid')
#                     name: str = query.value('name')
#                     self.__instruments.append((uid, name))
#
#                 self.endResetModel()
#
#             def getInstrumentUid(self, row: int) -> str | None:
#                 if row == 0:
#                     return None
#                 else:
#                     return self.__instruments[row - 1][0]
#
#             def getInstrumentName(self, row: int) -> str | None:
#                 if row == 0:
#                     return None
#                 else:
#                     return self.__instruments[row - 1][1]
#
#         def __init__(self, instrument_type: str | None, parent: QtWidgets.QWidget | None = ...):
#             super().__init__(parent)
#             self.setModel(self.InstrumentsUidModel(instrument_type, self))
#             self.__instrument_uid: str | None = self.currentData(QtCore.Qt.ItemDataRole.UserRole)
#             self.currentIndexChanged.connect(self.setInstrumentUid)
#
#         @QtCore.pyqtSlot(int)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
#         def setInstrumentUid(self, index: int):
#             self.__instrument_uid = self.model().getInstrumentUid(index)
#             if self.__instrument_uid is None:
#                 self.instrumentReset.emit()
#             else:
#                 self.instrumentChanged.emit(self.__instrument_uid)
#
#     def __init__(self, tokens_model: TokenListModel, parent: QtWidgets.QWidget | None = None):
#         super().__init__(parent=parent)
#         sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
#         self.setSizePolicy(sizePolicy)
#
#         self.verticalLayout_main = QtWidgets.QVBoxLayout(self)
#         self.verticalLayout_main.setContentsMargins(2, 2, 2, 2)
#         self.verticalLayout_main.setSpacing(2)
#
#         '''---------------------------Заголовок---------------------------'''
#         self.label_title = QtWidgets.QLabel(self)
#         self.label_title.setFont(TITLE_FONT)
#         self.label_title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
#         self.label_title.setText('ВЫБОР ИНСТРУМЕНТА')
#         self.verticalLayout_main.addWidget(self.label_title)
#         '''---------------------------------------------------------------'''
#
#         '''------------------------Строка выбора токена------------------------'''
#         self.horizontalLayout_token = QtWidgets.QHBoxLayout(self)
#         self.horizontalLayout_token.setSpacing(0)
#
#         self.label_token = QtWidgets.QLabel(self)
#         self.label_token.setText('Токен:')
#         self.horizontalLayout_token.addWidget(self.label_token)
#
#         spacerItem_token_1 = QtWidgets.QSpacerItem(4, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum)
#         self.horizontalLayout_token.addItem(spacerItem_token_1)
#
#         self.comboBox_token = QtWidgets.QComboBox(parent=self)
#         self.comboBox_token.setModel(tokens_model)
#         self.horizontalLayout_token.addWidget(self.comboBox_token)
#
#         spacerItem_token_2 = QtWidgets.QSpacerItem(0, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
#         self.horizontalLayout_token.addItem(spacerItem_token_2)
#
#         self.verticalLayout_main.addLayout(self.horizontalLayout_token)
#         '''--------------------------------------------------------------------'''
#
#         '''------------------Строка выбора статуса инструмента------------------'''
#         self.horizontalLayout_status = QtWidgets.QHBoxLayout(self)
#         self.horizontalLayout_status.setSpacing(0)
#
#         self.label_status = QtWidgets.QLabel(self)
#         self.label_status.setText('Статус:')
#         self.horizontalLayout_status.addWidget(self.label_status)
#
#         spacerItem_status_1 = QtWidgets.QSpacerItem(4, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum)
#         self.horizontalLayout_status.addItem(spacerItem_status_1)
#
#         self.comboBox_status = QtWidgets.QComboBox(parent=self)
#         self.comboBox_status.setModel(InstrumentsStatusModel(parent=self.comboBox_token))
#         self.horizontalLayout_status.addWidget(self.comboBox_status)
#
#         spacerItem_status_2 = QtWidgets.QSpacerItem(0, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
#         self.horizontalLayout_status.addItem(spacerItem_status_2)
#
#         self.verticalLayout_main.addLayout(self.horizontalLayout_status)
#         '''---------------------------------------------------------------------'''
#
#         '''-------------------Строка выбора типа инструмента-------------------'''
#         self.horizontalLayout_instrument_type = QtWidgets.QHBoxLayout(self)
#         self.horizontalLayout_instrument_type.setSpacing(0)
#
#         self.label_instrument_type = QtWidgets.QLabel(self)
#         self.label_instrument_type.setText('Тип инструмента:')
#         self.horizontalLayout_instrument_type.addWidget(self.label_instrument_type)
#
#         spacerItem_type_1 = QtWidgets.QSpacerItem(4, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum)
#         self.horizontalLayout_instrument_type.addItem(spacerItem_type_1)
#
#         self.comboBox_instrument_type = self.ComboBox_InstrumentType(self)
#         self.__instrument_type: str | None = self.comboBox_instrument_type.currentData(QtCore.Qt.ItemDataRole.DisplayRole)
#         self.horizontalLayout_instrument_type.addWidget(self.comboBox_instrument_type)
#
#         spacerItem_type_2 = QtWidgets.QSpacerItem(0, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
#         self.horizontalLayout_instrument_type.addItem(spacerItem_type_2)
#
#         self.verticalLayout_main.addLayout(self.horizontalLayout_instrument_type)
#         '''--------------------------------------------------------------------'''
#
#         '''----------------------Строка выбора инструмента----------------------'''
#         self.horizontalLayout_instrument = QtWidgets.QHBoxLayout(self)
#         self.horizontalLayout_instrument.setSpacing(0)
#
#         self.label_instrument = QtWidgets.QLabel(self)
#         self.label_instrument.setText('Инструмент:')
#         self.horizontalLayout_instrument.addWidget(self.label_instrument)
#
#         spacerItem_instrument_1 = QtWidgets.QSpacerItem(4, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum)
#         self.horizontalLayout_instrument.addItem(spacerItem_instrument_1)
#
#         self.comboBox_instrument = self.ComboBox_Instrument(self.instrument_type, self)
#         self.horizontalLayout_instrument.addWidget(self.comboBox_instrument)
#
#         spacerItem_instrument_2 = QtWidgets.QSpacerItem(0, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
#         self.horizontalLayout_instrument.addItem(spacerItem_instrument_2)
#
#         self.verticalLayout_main.addLayout(self.horizontalLayout_instrument)
#         '''---------------------------------------------------------------------'''
#
#         spacerItem_bottom = QtWidgets.QSpacerItem(0, 0, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
#         self.verticalLayout_main.addSpacerItem(spacerItem_bottom)
#
#         @QtCore.pyqtSlot(str)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
#         def onInstrumentTypeChanged(instrument_type: str):
#             self.instrument_type = instrument_type
#
#         self.comboBox_instrument_type.typeChanged.connect(onInstrumentTypeChanged)
#
#         @QtCore.pyqtSlot()  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
#         def onInstrumentTypeReset():
#             self.instrument_type = None
#
#         self.comboBox_instrument_type.typeReset.connect(onInstrumentTypeReset)
#
#         @QtCore.pyqtSlot(str)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
#         def onInstrumentChanged(instrument_uid: str):
#             table_name: str | None = self.ComboBox_Instrument.InstrumentsUidModel.getInstrumentTableName(self.instrument_type)
#             if table_name is None:
#                 assert table_name is None
#                 return
#
#             db: QtSql.QSqlDatabase = MainConnection.getDatabase()
#             query = QtSql.QSqlQuery(db)
#             query.setForwardOnly(True)  # Возможно, это ускоряет извлечение данных.
#             prepare_flag: bool = query.prepare('SELECT * FROM \"{0}\" WHERE \"uid\" = \'{1}\';'.format(table_name, instrument_uid))
#             assert prepare_flag, query.lastError().text()
#             exec_flag: bool = query.exec()
#             assert exec_flag, query.lastError().text()
#
#             if table_name == MyConnection.BONDS_TABLE:
#                 bond: Bond
#                 rows_count: int = 0
#                 while query.next():
#                     rows_count += 1
#                     bond = MyConnection.getCurrentBond(query)
#                 assert rows_count == 1
#
#                 bond_class: MyBondClass = MyBondClass(bond)
#                 self.bondSelected.emit(bond_class)
#             elif table_name == MyConnection.SHARES_TABLE:
#                 share: Share
#                 rows_count: int = 0
#                 while query.next():
#                     rows_count += 1
#                     share = MyConnection.getCurrentShare(query)
#                 assert rows_count == 1
#
#                 share_class: MyShareClass = MyShareClass(share)
#                 self.shareSelected.emit(share_class)
#             else:
#                 self.instrumentReset.emit()
#                 assert False
#
#         self.comboBox_instrument.instrumentChanged.connect(onInstrumentChanged)
#         self.comboBox_instrument.instrumentReset.connect(self.instrumentReset.emit)
#
#     @property
#     def instrument_type(self) -> str | None:
#         return self.__instrument_type
#
#     @instrument_type.setter
#     def instrument_type(self, instrument_type: str | None):
#         self.__instrument_type = instrument_type
#         self.comboBox_instrument.model().setInstrumentType(self.instrument_type)
#         self.comboBox_instrument.setSizeAdjustPolicy(QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToContents)


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
                    if db.transaction():
                        '''---------------Получение статусов инструментов из бд---------------'''
                        statuses_query = QtSql.QSqlQuery(db)
                        statuses_query.setForwardOnly(True)  # Возможно, это ускоряет извлечение данных.
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
                        raise SystemError('Не получилось начать транзакцию! db.lastError().text(): \'{0}\'.'.format(db.lastError().text()))
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
                    return indexes_list[0] + 1
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
                    if db.transaction():
                        types_query = QtSql.QSqlQuery(db)
                        types_query.setForwardOnly(True)  # Возможно, это ускоряет извлечение данных.
                        types_prepare_flag: bool = types_query.prepare(sql_command)
                        assert types_prepare_flag, types_query.lastError().text()
                        types_exec_flag: bool = types_query.exec()
                        assert types_exec_flag, types_query.lastError().text()

                        while types_query.next():
                            self.__types.append(types_query.value(self.PARAMETER))

                        commit_flag: bool = db.commit()  # Фиксирует транзакцию в базу данных.
                        assert commit_flag, db.lastError().text()
                    else:
                        raise SystemError('Не получилось начать транзакцию! db.lastError().text(): \'{0}\'.'.format(db.lastError().text()))
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
                        if db.transaction():
                            types_query = QtSql.QSqlQuery(db)
                            types_query.setForwardOnly(True)  # Возможно, это ускоряет извлечение данных.
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
                            raise SystemError('Не получилось начать транзакцию! db.lastError().text(): \'{0}\'.'.format(db.lastError().text()))
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
                        if db.transaction():
                            types_query = QtSql.QSqlQuery(db)
                            types_query.setForwardOnly(True)  # Возможно, это ускоряет извлечение данных.
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
                            raise SystemError('Не получилось начать транзакцию! db.lastError().text(): \'{0}\'.'.format(db.lastError().text()))

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
                            instruments_query.setForwardOnly(True)  # Возможно, это ускоряет извлечение данных.
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
                                instruments_query.setForwardOnly(True)  # Возможно, это ускоряет извлечение данных.
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
                                instruments_query.setForwardOnly(True)  # Возможно, это ускоряет извлечение данных.
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
                            instruments_query.setForwardOnly(True)  # Возможно, это ускоряет извлечение данных.
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
                                instruments_query.setForwardOnly(True)  # Возможно, это ускоряет извлечение данных.
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
                                instruments_query.setForwardOnly(True)  # Возможно, это ускоряет извлечение данных.
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

            @property
            def uids(self) -> list[str]:
                return [item[0] for item in self.__instruments]

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

    def __init__(self, tokens_model: TokenListModel, parent: QtWidgets.QWidget | None = None):
        self.__current_instrument: MyShareClass | MyBondClass | None = None
        super().__init__(parent=parent)

        verticalLayout_main = QtWidgets.QVBoxLayout(self)
        verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        verticalLayout_main.setSpacing(2)

        '''-----------------------Строка заголовка-----------------------'''
        self.title_widget = TitleWithCount(title='ВЫБОР ИНСТРУМЕНТА', count_text='0', parent=self)
        verticalLayout_main.addLayout(self.title_widget, 0)
        '''--------------------------------------------------------------'''

        '''---------------------Строка выбора токена---------------------'''
        horizontalLayout_token = QtWidgets.QHBoxLayout(self)
        horizontalLayout_token.setSpacing(0)

        horizontalLayout_token.addWidget(QtWidgets.QLabel(text='Токен:', parent=self), 0)
        horizontalLayout_token.addSpacing(4)

        self.comboBox_token = ComboBox_Token(token_model=tokens_model, parent=self)
        horizontalLayout_token.addWidget(self.comboBox_token, 0)

        horizontalLayout_token.addStretch(1)

        verticalLayout_main.addLayout(horizontalLayout_token, 0)
        '''--------------------------------------------------------------'''

        '''---------------Строка выбора статуса инструмента---------------'''
        horizontalLayout_status = QtWidgets.QHBoxLayout(self)
        horizontalLayout_status.setSpacing(0)

        horizontalLayout_status.addWidget(QtWidgets.QLabel(text='Статус:', parent=self), 0)
        horizontalLayout_status.addSpacing(4)

        self.comboBox_status = self.ComboBox_Status(token=self.token, parent=self)
        self.comboBox_token.tokenSelected.connect(self.comboBox_status.setToken)
        self.comboBox_token.tokenReset.connect(self.comboBox_status.setToken)
        horizontalLayout_status.addWidget(self.comboBox_status, 0)

        horizontalLayout_status.addStretch(1)

        verticalLayout_main.addLayout(horizontalLayout_status, 0)
        '''---------------------------------------------------------------'''

        '''------------Строка выбора типа инструмента------------'''
        horizontalLayout_instrument_type = QtWidgets.QHBoxLayout(self)
        horizontalLayout_instrument_type.setSpacing(0)

        horizontalLayout_instrument_type.addWidget(QtWidgets.QLabel(text='Тип инструмента:', parent=self), 0)
        horizontalLayout_instrument_type.addSpacing(4)

        self.comboBox_instrument_type = self.ComboBox_InstrumentType(token=self.token, status=self.status, parent=self)
        self.comboBox_token.tokenSelected.connect(self.comboBox_instrument_type.setToken)
        self.comboBox_token.tokenReset.connect(self.comboBox_instrument_type.setToken)
        self.comboBox_status.statusSelected.connect(self.comboBox_instrument_type.setStatus)
        self.comboBox_status.statusReset.connect(self.comboBox_instrument_type.setStatus)
        horizontalLayout_instrument_type.addWidget(self.comboBox_instrument_type, 0)

        horizontalLayout_instrument_type.addStretch(1)

        verticalLayout_main.addLayout(horizontalLayout_instrument_type, 0)
        '''------------------------------------------------------'''

        '''---------------Строка выбора инструмента---------------'''
        horizontalLayout_instrument = QtWidgets.QHBoxLayout(self)
        horizontalLayout_instrument.setSpacing(0)

        horizontalLayout_instrument.addWidget(QtWidgets.QLabel(text='Инструмент:', parent=self), 0)
        horizontalLayout_instrument.addSpacing(4)

        self.comboBox_instrument = self.ComboBox_Instrument(token=self.token, status=self.status, instrument_type=self.instrument_type, parent=self)
        self.title_widget.setCount(str(self.comboBox_instrument.instruments_count))
        self.comboBox_instrument.instrumentChanged.connect(self.__onCurrentInstrumentChanged)
        self.comboBox_instrument.instrumentReset.connect(self.__onCurrentInstrumentChanged)
        self.comboBox_instrument.instrumentsCountChanged.connect(lambda count: self.title_widget.setCount(str(count)))
        self.comboBox_token.tokenSelected.connect(self.comboBox_instrument.setToken)
        self.comboBox_token.tokenReset.connect(self.comboBox_instrument.setToken)
        self.comboBox_status.statusSelected.connect(self.comboBox_instrument.setStatus)
        self.comboBox_status.statusReset.connect(self.comboBox_instrument.setStatus)
        self.comboBox_instrument_type.typeChanged.connect(self.comboBox_instrument.setType)
        self.comboBox_instrument_type.typeReset.connect(self.comboBox_instrument.setType)
        horizontalLayout_instrument.addWidget(self.comboBox_instrument, 0)

        horizontalLayout_instrument.addStretch(1)

        verticalLayout_main.addLayout(horizontalLayout_instrument, 0)
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
