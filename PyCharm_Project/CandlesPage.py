import datetime
import typing
from PyQt6 import QtWidgets, QtCore, QtCharts, QtGui, QtSql
from PyQt6.QtCore import pyqtSignal
from tinkoff.invest import Bond, Quotation, MoneyValue, SecurityTradingStatus, RealExchange
from tinkoff.invest.schemas import RiskLevel, Share, ShareType
from Classes import MyConnection
from MyBondClass import MyBondClass
from MyDatabase import MainConnection
from MyShareClass import MyShareClass


TITLE_FONT = QtGui.QFont()
TITLE_FONT.setPointSize(9)
TITLE_FONT.setBold(True)


class GroupBox_InstrumentSelection(QtWidgets.QGroupBox):
    """GroupBox для выбора инструмента."""
    bondSelected: pyqtSignal = pyqtSignal(MyBondClass)  # Сигнал испускается при выборе облигации.
    shareSelected: pyqtSignal = pyqtSignal(MyShareClass)  # Сигнал испускается при выборе акции.
    instrumentReset: pyqtSignal = pyqtSignal()  # Сигнал испускается при сбросе выбранного инструмента.

    class ComboBox_InstrumentType(QtWidgets.QComboBox):
        typeChanged: pyqtSignal = pyqtSignal(str)  # Сигнал испускается при изменении выбранного типа.
        typeReset: pyqtSignal = pyqtSignal()  # Сигнал испускается при сбросе выбранного типа.

        class InstrumentsTypeModel(QtCore.QAbstractListModel):
            """Модель типов инструментов."""
            EMPTY: str = 'Не выбран'
            PARAMETER: str = 'instrument_type'

            def __init__(self, parent: QtCore.QObject | None = ...):
                super().__init__(parent)
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
                    # row: int = index.row()
                    # if row == 0:
                    #     return QtCore.QVariant(None)
                    # else:
                    #     return QtCore.QVariant('\"{0}\".\"{1}\" = \'{2}\''.format(MyConnection.INSTRUMENT_UIDS_TABLE, self.PARAMETER, self._types[index.row()]))

                    return QtCore.QVariant(self.getInstrumentType(index.row()))
                else:
                    return QtCore.QVariant()

            def update(self):
                """Обновляет модель."""
                self.beginResetModel()
                self._types = [self.EMPTY]

                db: QtSql.QSqlDatabase = MainConnection.getDatabase()
                query = QtSql.QSqlQuery(db)
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
        instrumentChanged: pyqtSignal = pyqtSignal(str)  # Сигнал испускается при изменении выбранного инструмента.
        instrumentReset: pyqtSignal = pyqtSignal()  # Сигнал испускается при сбросе выбранного инструмента.

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

            def getInstrumentType(self) -> str | None:
                return self.__instrument_type

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

    def __init__(self, parent: QtWidgets.QWidget | None = ...):
        super().__init__(parent)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(sizePolicy)

        self.verticalLayout_main = QtWidgets.QVBoxLayout(self)
        self.verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        self.verticalLayout_main.setSpacing(2)

        '''------------Строка выбора типа инструмента------------'''
        self.horizontalLayout_instrument_type = QtWidgets.QHBoxLayout()
        self.horizontalLayout_instrument_type.setSpacing(0)

        self.label_instrument_type = QtWidgets.QLabel(self)
        self.label_instrument_type.setText('Тип инструмента:')
        self.horizontalLayout_instrument_type.addWidget(self.label_instrument_type)

        self.comboBox_instrument_type = self.ComboBox_InstrumentType(self)
        self.horizontalLayout_instrument_type.addWidget(self.comboBox_instrument_type)

        self.verticalLayout_main.addLayout(self.horizontalLayout_instrument_type)
        '''------------------------------------------------------'''

        self.__instrument_type: str | None = self.comboBox_instrument_type.currentData(QtCore.Qt.ItemDataRole.DisplayRole)

        '''---------------Строка выбора инструмента---------------'''
        self.horizontalLayout_instrument = QtWidgets.QHBoxLayout()
        self.horizontalLayout_instrument.setSpacing(0)

        self.label_instrument = QtWidgets.QLabel(self)
        self.label_instrument.setText('Инструмент:')
        self.horizontalLayout_instrument.addWidget(self.label_instrument)

        self.comboBox_instrument = self.ComboBox_Instrument(self.instrument_type, self)
        self.horizontalLayout_instrument.addWidget(self.comboBox_instrument)

        self.verticalLayout_main.addLayout(self.horizontalLayout_instrument)
        '''-------------------------------------------------------'''

        self.__instrument: MyBondClass | MyShareClass | None = ...

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
            prepare_flag: bool = query.prepare('SELECT * FROM \"{0}\" WHERE \"uid\" = \'{1}\';'.format(table_name, instrument_uid))
            assert prepare_flag, query.lastError().text()
            exec_flag: bool = query.exec()
            assert exec_flag, query.lastError().text()

            if table_name == MyConnection.BONDS_TABLE:
                bond: Bond
                rows_count: int = 0
                while query.next():
                    rows_count += 1

                    def getBond() -> Bond:
                        """Создаёт и возвращает экземпляр класса Bond."""
                        figi: str = query.value('figi')
                        ticker: str = query.value('ticker')
                        class_code: str = query.value('class_code')
                        isin: str = query.value('isin')
                        lot: int = query.value('lot')
                        currency: str = query.value('currency')
                        klong: Quotation = MyConnection.convertTextToQuotation(query.value('klong'))
                        kshort: Quotation = MyConnection.convertTextToQuotation(query.value('kshort'))
                        dlong: Quotation = MyConnection.convertTextToQuotation(query.value('dlong'))
                        dshort: Quotation = MyConnection.convertTextToQuotation(query.value('dshort'))
                        dlong_min: Quotation = MyConnection.convertTextToQuotation(query.value('dlong_min'))
                        dshort_min: Quotation = MyConnection.convertTextToQuotation(query.value('dshort_min'))
                        short_enabled_flag: bool = MyConnection.convertBlobToBool(query.value('short_enabled_flag'))
                        name: str = query.value('name')
                        exchange: str = query.value('exchange')
                        coupon_quantity_per_year: int = query.value('coupon_quantity_per_year')
                        maturity_date: datetime = MyConnection.convertTextToDateTime(query.value('maturity_date'))
                        nominal: MoneyValue = MyConnection.convertTextToMoneyValue(query.value('nominal'))
                        initial_nominal: MoneyValue = MyConnection.convertTextToMoneyValue(query.value('initial_nominal'))
                        state_reg_date: datetime = MyConnection.convertTextToDateTime(query.value('state_reg_date'))
                        placement_date: datetime = MyConnection.convertTextToDateTime(query.value('placement_date'))
                        placement_price: MoneyValue = MyConnection.convertTextToMoneyValue(query.value('placement_price'))
                        aci_value: MoneyValue = MyConnection.convertTextToMoneyValue(query.value('aci_value'))
                        country_of_risk: str = query.value('country_of_risk')
                        country_of_risk_name: str = query.value('country_of_risk_name')
                        sector: str = query.value('sector')
                        issue_kind: str = query.value('issue_kind')
                        issue_size: int = query.value('issue_size')
                        issue_size_plan: int = query.value('issue_size_plan')
                        trading_status: SecurityTradingStatus = SecurityTradingStatus(query.value('trading_status'))
                        otc_flag: bool = MyConnection.convertBlobToBool(query.value('otc_flag'))
                        buy_available_flag: bool = MyConnection.convertBlobToBool(query.value('buy_available_flag'))
                        sell_available_flag: bool = MyConnection.convertBlobToBool(query.value('sell_available_flag'))
                        floating_coupon_flag: bool = MyConnection.convertBlobToBool(query.value('floating_coupon_flag'))
                        perpetual_flag: bool = MyConnection.convertBlobToBool(query.value('perpetual_flag'))
                        amortization_flag: bool = MyConnection.convertBlobToBool(query.value('amortization_flag'))
                        min_price_increment: Quotation = MyConnection.convertTextToQuotation(query.value('min_price_increment'))
                        api_trade_available_flag: bool = MyConnection.convertBlobToBool(query.value('api_trade_available_flag'))
                        uid: str = query.value('uid')
                        real_exchange: RealExchange = RealExchange(query.value('real_exchange'))
                        position_uid: str = query.value('position_uid')
                        for_iis_flag: bool = MyConnection.convertBlobToBool(query.value('for_iis_flag'))
                        for_qual_investor_flag: bool = MyConnection.convertBlobToBool(query.value('for_qual_investor_flag'))
                        weekend_flag: bool = MyConnection.convertBlobToBool(query.value('weekend_flag'))
                        blocked_tca_flag: bool = MyConnection.convertBlobToBool(query.value('blocked_tca_flag'))
                        subordinated_flag: bool = MyConnection.convertBlobToBool(query.value('subordinated_flag'))
                        liquidity_flag: bool = MyConnection.convertBlobToBool(query.value('liquidity_flag'))
                        first_1min_candle_date: datetime = MyConnection.convertTextToDateTime(query.value('first_1min_candle_date'))
                        first_1day_candle_date: datetime = MyConnection.convertTextToDateTime(query.value('first_1day_candle_date'))
                        risk_level: RiskLevel = RiskLevel(query.value('risk_level'))
                        return Bond(figi=figi, ticker=ticker, class_code=class_code, isin=isin, lot=lot, currency=currency,
                                    klong=klong,
                                    kshort=kshort, dlong=dlong, dshort=dshort, dlong_min=dlong_min, dshort_min=dshort_min,
                                    short_enabled_flag=short_enabled_flag, name=name, exchange=exchange,
                                    coupon_quantity_per_year=coupon_quantity_per_year, maturity_date=maturity_date,
                                    nominal=nominal,
                                    initial_nominal=initial_nominal, state_reg_date=state_reg_date,
                                    placement_date=placement_date,
                                    placement_price=placement_price, aci_value=aci_value, country_of_risk=country_of_risk,
                                    country_of_risk_name=country_of_risk_name, sector=sector, issue_kind=issue_kind,
                                    issue_size=issue_size, issue_size_plan=issue_size_plan, trading_status=trading_status,
                                    otc_flag=otc_flag, buy_available_flag=buy_available_flag,
                                    sell_available_flag=sell_available_flag,
                                    floating_coupon_flag=floating_coupon_flag, perpetual_flag=perpetual_flag,
                                    amortization_flag=amortization_flag, min_price_increment=min_price_increment,
                                    api_trade_available_flag=api_trade_available_flag, uid=uid, real_exchange=real_exchange,
                                    position_uid=position_uid, for_iis_flag=for_iis_flag,
                                    for_qual_investor_flag=for_qual_investor_flag,
                                    weekend_flag=weekend_flag, blocked_tca_flag=blocked_tca_flag,
                                    subordinated_flag=subordinated_flag,
                                    liquidity_flag=liquidity_flag, first_1min_candle_date=first_1min_candle_date,
                                    first_1day_candle_date=first_1day_candle_date, risk_level=risk_level)

                    bond = getBond()
                assert rows_count == 1

                bond_class: MyBondClass = MyBondClass(bond)
                self.bondSelected.emit(bond_class)
                print('bondSelected.emit: {0}'.format(bond_class.bond.uid))
            elif table_name == MyConnection.SHARES_TABLE:
                share: Share
                rows_count: int = 0
                while query.next():
                    rows_count += 1

                    def getShare() -> Share:
                        """Создаёт и возвращает экземпляр класса Share."""
                        figi: str = query.value('figi')
                        ticker: str = query.value('ticker')
                        class_code: str = query.value('class_code')
                        isin: str = query.value('isin')
                        lot: int = query.value('lot')
                        currency: str = query.value('currency')
                        klong: Quotation = MyConnection.convertTextToQuotation(query.value('klong'))
                        kshort: Quotation = MyConnection.convertTextToQuotation(query.value('kshort'))
                        dlong: Quotation = MyConnection.convertTextToQuotation(query.value('dlong'))
                        dshort: Quotation = MyConnection.convertTextToQuotation(query.value('dshort'))
                        dlong_min: Quotation = MyConnection.convertTextToQuotation(query.value('dlong_min'))
                        dshort_min: Quotation = MyConnection.convertTextToQuotation(query.value('dshort_min'))
                        short_enabled_flag: bool = MyConnection.convertBlobToBool(query.value('short_enabled_flag'))
                        name: str = query.value('name')
                        exchange: str = query.value('exchange')
                        ipo_date: datetime = MyConnection.convertTextToDateTime(query.value('ipo_date'))
                        issue_size: int = query.value('issue_size')
                        country_of_risk: str = query.value('country_of_risk')
                        country_of_risk_name: str = query.value('country_of_risk_name')
                        sector: str = query.value('sector')
                        issue_size_plan: int = query.value('issue_size_plan')
                        nominal: MoneyValue = MyConnection.convertTextToMoneyValue(query.value('nominal'))
                        trading_status: SecurityTradingStatus = SecurityTradingStatus(query.value('trading_status'))
                        otc_flag: bool = MyConnection.convertBlobToBool(query.value('otc_flag'))
                        buy_available_flag: bool = MyConnection.convertBlobToBool(query.value('buy_available_flag'))
                        sell_available_flag: bool = MyConnection.convertBlobToBool(query.value('sell_available_flag'))
                        div_yield_flag: bool = MyConnection.convertBlobToBool(query.value('div_yield_flag'))
                        share_type: ShareType = ShareType(query.value('share_type'))
                        min_price_increment: Quotation = MyConnection.convertTextToQuotation(query.value('min_price_increment'))
                        api_trade_available_flag: bool = MyConnection.convertBlobToBool(query.value('api_trade_available_flag'))
                        uid: str = query.value('uid')
                        real_exchange: RealExchange = RealExchange(query.value('real_exchange'))
                        position_uid: str = query.value('position_uid')
                        for_iis_flag: bool = MyConnection.convertBlobToBool(query.value('for_iis_flag'))
                        for_qual_investor_flag: bool = MyConnection.convertBlobToBool(query.value('for_qual_investor_flag'))
                        weekend_flag: bool = MyConnection.convertBlobToBool(query.value('weekend_flag'))
                        blocked_tca_flag: bool = MyConnection.convertBlobToBool(query.value('blocked_tca_flag'))
                        liquidity_flag: bool = MyConnection.convertBlobToBool(query.value('liquidity_flag'))
                        first_1min_candle_date: datetime = MyConnection.convertTextToDateTime(query.value('first_1min_candle_date'))
                        first_1day_candle_date: datetime = MyConnection.convertTextToDateTime(query.value('first_1day_candle_date'))
                        return Share(figi=figi, ticker=ticker, class_code=class_code, isin=isin, lot=lot,
                                     currency=currency, klong=klong, kshort=kshort, dlong=dlong, dshort=dshort,
                                     dlong_min=dlong_min, dshort_min=dshort_min, short_enabled_flag=short_enabled_flag,
                                     name=name, exchange=exchange, ipo_date=ipo_date, issue_size=issue_size,
                                     country_of_risk=country_of_risk, country_of_risk_name=country_of_risk_name,
                                     sector=sector, issue_size_plan=issue_size_plan, nominal=nominal,
                                     trading_status=trading_status, otc_flag=otc_flag,
                                     buy_available_flag=buy_available_flag, sell_available_flag=sell_available_flag,
                                     div_yield_flag=div_yield_flag, share_type=share_type,
                                     min_price_increment=min_price_increment,
                                     api_trade_available_flag=api_trade_available_flag, uid=uid,
                                     real_exchange=real_exchange, position_uid=position_uid, for_iis_flag=for_iis_flag,
                                     for_qual_investor_flag=for_qual_investor_flag, weekend_flag=weekend_flag,
                                     blocked_tca_flag=blocked_tca_flag, liquidity_flag=liquidity_flag,
                                     first_1min_candle_date=first_1min_candle_date,
                                     first_1day_candle_date=first_1day_candle_date)

                    share = getShare()
                assert rows_count == 1

                share_class: MyShareClass = MyShareClass(share)
                self.shareSelected.emit(share_class)
                print('shareSelected.emit: {0}'.format('empty'))
            else:
                self.instrumentReset.emit()
                print('instrumentReset.emit: {0}'.format('empty'))
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


class GroupBox_CandlesView(QtWidgets.QGroupBox):
    """Панель отображения свечей."""
    def __init__(self, parent: QtWidgets.QWidget | None = ...):
        super().__init__(parent)

        self.verticalLayout_main = QtWidgets.QVBoxLayout(self)
        self.verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        self.verticalLayout_main.setSpacing(2)

        '''------------------------Заголовок------------------------'''
        self.horizontalLayout_title = QtWidgets.QHBoxLayout(self)
        self.horizontalLayout_title.setSpacing(0)

        self.horizontalLayout_title.addItem(QtWidgets.QSpacerItem(10, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum))

        self.horizontalLayout_title.addItem(QtWidgets.QSpacerItem(0, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum))

        self.label_title = QtWidgets.QLabel(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_title.sizePolicy().hasHeightForWidth())
        self.label_title.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setPointSize(9)
        font.setBold(True)
        self.label_title.setFont(font)
        self.label_title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.label_title.setText('СВЕЧИ')
        self.horizontalLayout_title.addWidget(self.label_title)

        self.label_count = QtWidgets.QLabel(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_count.sizePolicy().hasHeightForWidth())
        self.label_count.setSizePolicy(sizePolicy)
        self.label_count.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.label_count.setText('0')
        self.horizontalLayout_title.addWidget(self.label_count)

        self.horizontalLayout_title.addItem(QtWidgets.QSpacerItem(10, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum))

        self.verticalLayout_main.addLayout(self.horizontalLayout_title)
        '''---------------------------------------------------------'''

        self.tableView = QtWidgets.QTableView(self)
        self.verticalLayout_main.addWidget(self.tableView)


class GroupBox_InstrumentInfo(QtWidgets.QGroupBox):
    """Панель отображения информации об инструменте."""
    class Label_InstrumentInfo(QtWidgets.QLabel):
        def __init__(self, parent: QtWidgets.QWidget | None = ...):
            super().__init__(parent)
            sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Expanding)
            sizePolicy.setHorizontalStretch(0)
            sizePolicy.setVerticalStretch(0)
            sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
            self.setSizePolicy(sizePolicy)

        def setInstrument(self, instrument: MyBondClass | MyShareClass):
            if isinstance(instrument, MyBondClass):
                self.__reportBond(instrument)
            elif isinstance(instrument, MyShareClass):
                self.__reportShare(instrument)
            else:
                raise TypeError('Некорректный тип параметра!')

        def reset(self):
            self.setText(None)

        def __reportBond(self, bond: MyBondClass):
            text: str = 'Тип: {0}\nНазвание: {1}\nuid: {2}\nfigi: {3}\nisin: {4}'.format(
                'Облигация',
                bond.bond.name,
                bond.bond.uid,
                bond.bond.figi,
                bond.bond.isin
            )
            self.setText(text)

        def __reportShare(self, share: MyShareClass):
            text: str = 'Тип: {0}\nНазвание: {1}\nuid: {2}\nfigi: {3}\nisin: {4}'.format(
                'Акция',
                share.share.name,
                share.share.uid,
                share.share.figi,
                share.share.isin
            )
            self.setText(text)

    def __init__(self, parent: QtWidgets.QWidget | None = ...):
        super().__init__(parent)

        self.verticalLayout_main = QtWidgets.QVBoxLayout(self)
        self.verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        self.verticalLayout_main.setSpacing(2)

        self.label_title = QtWidgets.QLabel(self)
        self.label_title.setFont(TITLE_FONT)
        self.label_title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.label_title.setText('ИНФОРМАЦИЯ ОБ ИНСТРУМЕНТЕ')
        self.verticalLayout_main.addWidget(self.label_title)

        self.label_info = self.Label_InstrumentInfo(self)
        self.verticalLayout_main.addWidget(self.label_info)

    def setInstrument(self, instrument: MyBondClass | MyShareClass):
        self.label_info.setInstrument(instrument)

    def reset(self):
        self.label_info.reset()


class GroupBox_Chart(QtWidgets.QGroupBox):
    """Панель с диаграммой."""
    def __init__(self, parent: QtWidgets.QWidget | None = ...):
        super().__init__(parent)

        self.verticalLayout_main = QtWidgets.QVBoxLayout(self)
        self.verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        self.verticalLayout_main.setSpacing(2)

        self.label_title = QtWidgets.QLabel(self)
        self.label_title.setFont(TITLE_FONT)
        self.label_title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.label_title.setText('ГРАФИК')
        self.verticalLayout_main.addWidget(self.label_title)

        self.candlestick_series = QtCharts.QChartView(self)
        self.verticalLayout_main.addWidget(self.candlestick_series)


class CandlesPage(QtWidgets.QWidget):
    """Страница свечей."""
    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)

        self.verticalLayout_main = QtWidgets.QVBoxLayout(self)
        self.verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        self.verticalLayout_main.setSpacing(2)

        """========================Верхняя часть========================"""
        self.horizontalLayout_top = QtWidgets.QHBoxLayout(self)
        self.horizontalLayout_top.setContentsMargins(2, 2, 2, 2)
        self.horizontalLayout_top.setSpacing(2)

        '''-----Выбор инструмента и отображение информации об инструменте-----'''
        self.verticalLayout_instrument = QtWidgets.QVBoxLayout(self)
        self.verticalLayout_instrument.setSpacing(2)

        self.groupBox_instrument = GroupBox_InstrumentSelection(self)  # Панель выбора инструмента.
        self.verticalLayout_instrument.addWidget(self.groupBox_instrument)

        self.groupBox_info = GroupBox_InstrumentInfo(self)  # Отображение информации об инструменте.
        self.groupBox_instrument.bondSelected.connect(self.groupBox_info.setInstrument)
        self.groupBox_instrument.shareSelected.connect(self.groupBox_info.setInstrument)
        self.groupBox_instrument.instrumentReset.connect(self.groupBox_info.reset)
        self.verticalLayout_instrument.addWidget(self.groupBox_info)

        self.horizontalLayout_top.addLayout(self.verticalLayout_instrument)
        '''-------------------------------------------------------------------'''

        self.groupBox_candles = GroupBox_CandlesView(self)
        self.horizontalLayout_top.addWidget(self.groupBox_candles)
        self.verticalLayout_main.addLayout(self.horizontalLayout_top)
        """============================================================="""

        """========================Нижняя часть========================"""
        self.groupBox_chart = GroupBox_Chart(self)
        self.verticalLayout_main.addWidget(self.groupBox_chart)
        """============================================================"""
