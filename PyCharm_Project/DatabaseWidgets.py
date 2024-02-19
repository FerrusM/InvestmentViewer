import typing
from datetime import datetime
from PyQt6 import QtCore, QtWidgets, QtSql
from tinkoff.invest import Bond, Quotation, MoneyValue, SecurityTradingStatus, RealExchange
from tinkoff.invest.schemas import RiskLevel, Share, ShareType
from Classes import MyConnection, TITLE_FONT
from MyBondClass import MyBondClass
from MyDatabase import MainConnection
from MyShareClass import MyShareClass
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


class GroupBox_InstrumentSelection(QtWidgets.QGroupBox):
    """Панель выбора инструмента в локальной базе данных."""
    bondSelected: QtCore.pyqtSignal = QtCore.pyqtSignal(MyBondClass)  # Сигнал испускается при выборе облигации.
    shareSelected: QtCore.pyqtSignal = QtCore.pyqtSignal(MyShareClass)  # Сигнал испускается при выборе акции.
    instrumentReset: QtCore.pyqtSignal = QtCore.pyqtSignal()  # Сигнал испускается при сбросе выбранного инструмента.

    class ComboBox_InstrumentType(QtWidgets.QComboBox):
        typeChanged: QtCore.pyqtSignal = QtCore.pyqtSignal(str)  # Сигнал испускается при изменении выбранного типа.
        typeReset: QtCore.pyqtSignal = QtCore.pyqtSignal()  # Сигнал испускается при сбросе выбранного типа.

        class InstrumentsTypeModel(QtCore.QAbstractListModel):
            """Модель типов инструментов."""
            EMPTY: str = 'Не выбран'
            PARAMETER: str = 'instrument_type'

            def __init__(self, parent: QtCore.QObject | None = None):
                super().__init__(parent=parent)
                self._types: list[str] = [self.EMPTY]
                self.update()

            def rowCount(self, parent: QtCore.QModelIndex = ...) -> int:
                return len(self._types)

            def getInstrumentType(self, row: int) -> str | None:
                if row == 0:
                    return None
                else:
                    return self._types[row]

            def data(self, index: QtCore.QModelIndex, role: int = ...) -> typing.Any:
                if role == QtCore.Qt.ItemDataRole.DisplayRole:
                    return QtCore.QVariant(self._types[index.row()])
                elif role == QtCore.Qt.ItemDataRole.UserRole:
                    return QtCore.QVariant(self.getInstrumentType(index.row()))
                else:
                    return QtCore.QVariant()

            def update(self):
                """Обновляет модель."""
                self.beginResetModel()
                self._types = [self.EMPTY]

                db: QtSql.QSqlDatabase = MainConnection.getDatabase()
                query = QtSql.QSqlQuery(db)
                query.setForwardOnly(True)  # Возможно, это ускоряет извлечение данных.
                prepare_flag: bool = query.prepare('SELECT DISTINCT \"{0}\" FROM \"{1}\" ORDER BY \"{0}\";'.format(self.PARAMETER, MyConnection.INSTRUMENT_UIDS_TABLE))
                assert prepare_flag, query.lastError().text()
                exec_flag: bool = query.exec()
                assert exec_flag, query.lastError().text()

                while query.next():
                    instrument_type: str = query.value(self.PARAMETER)
                    self._types.append(instrument_type)

                self.endResetModel()

        def __init__(self, parent: QtWidgets.QWidget | None = ...):
            super().__init__(parent)
            self.setModel(self.InstrumentsTypeModel(self))
            self.currentIndexChanged.connect(self.setInstrumentType)

        @QtCore.pyqtSlot(int)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
        def setInstrumentType(self, index: int):
            instrument_type: str | None = self.model().getInstrumentType(index)
            if instrument_type is None:
                self.typeReset.emit()
            else:
                self.typeChanged.emit(instrument_type)

    class ComboBox_Instrument(QtWidgets.QComboBox):
        instrumentChanged: QtCore.pyqtSignal = QtCore.pyqtSignal(str)  # Сигнал испускается при изменении выбранного инструмента.
        instrumentReset: QtCore.pyqtSignal = QtCore.pyqtSignal()  # Сигнал испускается при сбросе выбранного инструмента.

        class InstrumentsUidModel(QtCore.QAbstractListModel):
            """Модель инструментов выбранного типа."""
            def __init__(self, instrument_type: str | None, parent: QtCore.QObject | None = ...):
                super().__init__(parent)
                self.__instrument_type: str | None = instrument_type
                self.__instruments: list[tuple[str, str]] = []
                self.setInstrumentType(instrument_type)

            def rowCount(self, parent: QtCore.QModelIndex = ...) -> int:
                return len(self.__instruments) + 1

            def data(self, index: QtCore.QModelIndex, role: int = ...) -> typing.Any:
                if role == QtCore.Qt.ItemDataRole.DisplayRole:
                    row: int = index.row()
                    if row == 0:
                        return QtCore.QVariant('Не выбран')
                    else:
                        item: (str, str) = self.__instruments[row - 1]
                        return QtCore.QVariant('{0} | {1}'.format(item[0], item[1]))
                elif role == QtCore.Qt.ItemDataRole.UserRole:
                    return QtCore.QVariant(self.getInstrumentUid(index.row()))
                else:
                    return QtCore.QVariant()

            @staticmethod
            def getInstrumentTableName(instrument_type: str | None) -> str | None:
                """Возвращает название таблицы, хранящей инструменты выбранного типа."""
                if instrument_type == 'bond':
                    return MyConnection.BONDS_TABLE
                elif instrument_type == 'share':
                    return MyConnection.SHARES_TABLE
                else:
                    return None

            def setInstrumentType(self, instrument_type: str | None):
                self.beginResetModel()
                self.__instrument_type = instrument_type
                self.__instruments = []

                table_name: str | None = self.getInstrumentTableName(self.__instrument_type)
                if table_name is None:
                    self.endResetModel()
                    return

                db: QtSql.QSqlDatabase = MainConnection.getDatabase()
                query = QtSql.QSqlQuery(db)
                query.setForwardOnly(True)  # Возможно, это ускоряет извлечение данных.
                prepare_flag: bool = query.prepare('SELECT \"uid\", \"name\" FROM \"{0}\" ORDER BY \"name\";'.format(table_name))
                assert prepare_flag, query.lastError().text()
                exec_flag: bool = query.exec()
                assert exec_flag, query.lastError().text()

                while query.next():
                    uid: str = query.value('uid')
                    name: str = query.value('name')
                    self.__instruments.append((uid, name))

                self.endResetModel()

            def getInstrumentUid(self, row: int) -> str | None:
                if row == 0:
                    return None
                else:
                    return self.__instruments[row - 1][0]

            def getInstrumentName(self, row: int) -> str | None:
                if row == 0:
                    return None
                else:
                    return self.__instruments[row - 1][1]

        def __init__(self, instrument_type: str | None, parent: QtWidgets.QWidget | None = ...):
            super().__init__(parent)
            self.setModel(self.InstrumentsUidModel(instrument_type, self))
            self.__instrument_uid: str | None = self.currentData(QtCore.Qt.ItemDataRole.UserRole)
            self.currentIndexChanged.connect(self.setInstrumentUid)

        @QtCore.pyqtSlot(int)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
        def setInstrumentUid(self, index: int):
            self.__instrument_uid = self.model().getInstrumentUid(index)
            if self.__instrument_uid is None:
                self.instrumentReset.emit()
            else:
                self.instrumentChanged.emit(self.__instrument_uid)

    def __init__(self, tokens_model: TokenListModel, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.setSizePolicy(sizePolicy)

        self.verticalLayout_main = QtWidgets.QVBoxLayout(self)
        self.verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        self.verticalLayout_main.setSpacing(2)

        '''---------------------------Заголовок---------------------------'''
        self.label_title = QtWidgets.QLabel(self)
        self.label_title.setFont(TITLE_FONT)
        self.label_title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.label_title.setText('ВЫБОР ИНСТРУМЕНТА')
        self.verticalLayout_main.addWidget(self.label_title)
        '''---------------------------------------------------------------'''

        '''------------------------Строка выбора токена------------------------'''
        self.horizontalLayout_token = QtWidgets.QHBoxLayout(self)
        self.horizontalLayout_token.setSpacing(0)

        self.label_token = QtWidgets.QLabel(self)
        self.label_token.setText('Токен:')
        self.horizontalLayout_token.addWidget(self.label_token)

        spacerItem_token_1 = QtWidgets.QSpacerItem(4, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_token.addItem(spacerItem_token_1)

        self.comboBox_token = QtWidgets.QComboBox(parent=self)
        self.comboBox_token.setModel(tokens_model)
        self.horizontalLayout_token.addWidget(self.comboBox_token)

        spacerItem_token_2 = QtWidgets.QSpacerItem(0, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_token.addItem(spacerItem_token_2)

        self.verticalLayout_main.addLayout(self.horizontalLayout_token)
        '''--------------------------------------------------------------------'''

        '''------------------Строка выбора статуса инструмента------------------'''
        self.horizontalLayout_status = QtWidgets.QHBoxLayout(self)
        self.horizontalLayout_status.setSpacing(0)

        self.label_status = QtWidgets.QLabel(self)
        self.label_status.setText('Статус:')
        self.horizontalLayout_status.addWidget(self.label_status)

        spacerItem_status_1 = QtWidgets.QSpacerItem(4, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_status.addItem(spacerItem_status_1)

        self.comboBox_status = QtWidgets.QComboBox(parent=self)
        self.comboBox_status.setModel(InstrumentsStatusModel(parent=self.comboBox_token))
        self.horizontalLayout_status.addWidget(self.comboBox_status)

        spacerItem_status_2 = QtWidgets.QSpacerItem(0, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_status.addItem(spacerItem_status_2)

        self.verticalLayout_main.addLayout(self.horizontalLayout_status)
        '''---------------------------------------------------------------------'''

        '''-------------------Строка выбора типа инструмента-------------------'''
        self.horizontalLayout_instrument_type = QtWidgets.QHBoxLayout(self)
        self.horizontalLayout_instrument_type.setSpacing(0)

        self.label_instrument_type = QtWidgets.QLabel(self)
        self.label_instrument_type.setText('Тип инструмента:')
        self.horizontalLayout_instrument_type.addWidget(self.label_instrument_type)

        spacerItem_type_1 = QtWidgets.QSpacerItem(4, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_instrument_type.addItem(spacerItem_type_1)

        self.comboBox_instrument_type = self.ComboBox_InstrumentType(self)
        self.__instrument_type: str | None = self.comboBox_instrument_type.currentData(QtCore.Qt.ItemDataRole.DisplayRole)
        self.horizontalLayout_instrument_type.addWidget(self.comboBox_instrument_type)

        spacerItem_type_2 = QtWidgets.QSpacerItem(0, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_instrument_type.addItem(spacerItem_type_2)

        self.verticalLayout_main.addLayout(self.horizontalLayout_instrument_type)
        '''--------------------------------------------------------------------'''

        '''----------------------Строка выбора инструмента----------------------'''
        self.horizontalLayout_instrument = QtWidgets.QHBoxLayout(self)
        self.horizontalLayout_instrument.setSpacing(0)

        self.label_instrument = QtWidgets.QLabel(self)
        self.label_instrument.setText('Инструмент:')
        self.horizontalLayout_instrument.addWidget(self.label_instrument)

        spacerItem_instrument_1 = QtWidgets.QSpacerItem(4, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_instrument.addItem(spacerItem_instrument_1)

        self.comboBox_instrument = self.ComboBox_Instrument(self.instrument_type, self)
        self.horizontalLayout_instrument.addWidget(self.comboBox_instrument)

        spacerItem_instrument_2 = QtWidgets.QSpacerItem(0, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_instrument.addItem(spacerItem_instrument_2)

        self.verticalLayout_main.addLayout(self.horizontalLayout_instrument)
        '''---------------------------------------------------------------------'''

        spacerItem_bottom = QtWidgets.QSpacerItem(0, 0, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        self.verticalLayout_main.addSpacerItem(spacerItem_bottom)

        @QtCore.pyqtSlot(str)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
        def onInstrumentTypeChanged(instrument_type: str):
            self.instrument_type = instrument_type

        self.comboBox_instrument_type.typeChanged.connect(onInstrumentTypeChanged)

        @QtCore.pyqtSlot()  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
        def onInstrumentTypeReset():
            self.instrument_type = None

        self.comboBox_instrument_type.typeReset.connect(onInstrumentTypeReset)

        @QtCore.pyqtSlot(str)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
        def onInstrumentChanged(instrument_uid: str):
            table_name: str | None = self.ComboBox_Instrument.InstrumentsUidModel.getInstrumentTableName(self.instrument_type)
            if table_name is None:
                assert table_name is None
                return

            db: QtSql.QSqlDatabase = MainConnection.getDatabase()
            query = QtSql.QSqlQuery(db)
            query.setForwardOnly(True)  # Возможно, это ускоряет извлечение данных.
            prepare_flag: bool = query.prepare('SELECT * FROM \"{0}\" WHERE \"uid\" = \'{1}\';'.format(table_name, instrument_uid))
            assert prepare_flag, query.lastError().text()
            exec_flag: bool = query.exec()
            assert exec_flag, query.lastError().text()

            if table_name == MyConnection.BONDS_TABLE:
                bond: Bond
                rows_count: int = 0
                while query.next():
                    rows_count += 1
                    bond = MyConnection.getCurrentBond(query)
                assert rows_count == 1

                bond_class: MyBondClass = MyBondClass(bond)
                self.bondSelected.emit(bond_class)
            elif table_name == MyConnection.SHARES_TABLE:
                share: Share
                rows_count: int = 0
                while query.next():
                    rows_count += 1
                    share = MyConnection.getCurrentShare(query)
                assert rows_count == 1

                share_class: MyShareClass = MyShareClass(share)
                self.shareSelected.emit(share_class)
            else:
                self.instrumentReset.emit()
                assert False

        self.comboBox_instrument.instrumentChanged.connect(onInstrumentChanged)
        self.comboBox_instrument.instrumentReset.connect(self.instrumentReset.emit)

    @property
    def instrument_type(self) -> str | None:
        return self.__instrument_type

    @instrument_type.setter
    def instrument_type(self, instrument_type: str | None):
        self.__instrument_type = instrument_type
        self.comboBox_instrument.model().setInstrumentType(self.instrument_type)
        self.comboBox_instrument.setSizeAdjustPolicy(QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToContents)
