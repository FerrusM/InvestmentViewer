from datetime import datetime, timedelta
import typing
from enum import Enum
from PyQt6 import QtWidgets, QtCore, QtCharts, QtGui, QtSql
from tinkoff.invest import Bond, Quotation, MoneyValue, SecurityTradingStatus, RealExchange
from tinkoff.invest.schemas import RiskLevel, Share, ShareType, HistoricCandle, CandleInterval
from tinkoff.invest.utils import candle_interval_to_timedelta
from Classes import MyConnection, TokenClass, print_slot, Column
from LimitClasses import LimitPerMinuteSemaphore
from MyBondClass import MyBondClass
from MyDatabase import MainConnection
from MyDateTime import getUtcDateTime, getMoscowDateTime, ifDateTimeIsEmpty
from MyQuotation import MyQuotation
from MyRequests import getCandles, MyResponse, RequestTryClass
from MyShareClass import MyShareClass
from PagesClasses import ProgressBar_DataReceiving
from TokenModel import TokenListModel

TITLE_FONT = QtGui.QFont()
TITLE_FONT.setPointSize(9)
TITLE_FONT.setBold(True)


class GroupBox_InstrumentSelection(QtWidgets.QGroupBox):
    """GroupBox для выбора инструмента."""
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
        self.__instrument_type: str | None = self.comboBox_instrument_type.currentData(QtCore.Qt.ItemDataRole.DisplayRole)
        self.horizontalLayout_instrument_type.addWidget(self.comboBox_instrument_type)

        self.verticalLayout_main.addLayout(self.horizontalLayout_instrument_type)
        '''------------------------------------------------------'''

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


class GroupBox_CandlesView(QtWidgets.QGroupBox):
    """Панель отображения свечей."""
    class CandlesModel(QtCore.QAbstractTableModel):
        def __init__(self, parent: QtCore.QObject | None = ...):
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
            super().__init__(parent)

        def columnCount(self, parent: QtCore.QModelIndex = ...) -> int:
            return len(self.__columns)

        def rowCount(self, parent: QtCore.QModelIndex = ...) -> int:
            return len(self.__candles)

        def data(self, index: QtCore.QModelIndex, role: int = ...) -> typing.Any:
            column: Column = self.__columns[index.column()]
            candle: HistoricCandle = self.__candles[index.row()]
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
        self.tableView.setModel(self.CandlesModel(self))
        self.verticalLayout_main.addWidget(self.tableView)

    def setCandles(self, candles: list[HistoricCandle]):
        self.tableView.model().setCandles(candles)
        self.tableView.resizeColumnsToContents()  # Авторазмер столбцов под содержимое.
        self.label_count.setText(str(self.tableView.model().rowCount()))  # Отображаем количество облигаций.


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
            self.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)

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
            text: str = 'Тип: {0}\nНазвание: {1}\nuid: {2}\nfigi: {3}\nisin: {4}\nПервая минутная свеча: {5}\nПервая дневная свеча: {6}'.format(
                'Облигация',
                bond.bond.name,
                bond.bond.uid,
                bond.bond.figi,
                bond.bond.isin,
                bond.bond.first_1min_candle_date,
                bond.bond.first_1day_candle_date
            )
            self.setText(text)

        def __reportShare(self, share: MyShareClass):
            text: str = 'Тип: {0}\nНазвание: {1}\nuid: {2}\nfigi: {3}\nisin: {4}\nПервая минутная свеча: {5}\nПервая дневная свеча: {6}'.format(
                'Акция',
                share.share.name,
                share.share.uid,
                share.share.figi,
                share.share.isin,
                share.share.first_1min_candle_date,
                share.share.first_1day_candle_date
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

    @QtCore.pyqtSlot()  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
    def reset(self):
        self.label_info.reset()


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


class CandleIntervalModel(QtCore.QAbstractListModel):
    """Модель интервалов свечей."""
    def __init__(self, parent: QtCore.QObject | None = ...):
        super().__init__(parent)
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
            return QtCore.QVariant(self.__intervals[index.row()][0])
        elif role == QtCore.Qt.ItemDataRole.UserRole:
            return QtCore.QVariant(self.__intervals[index.row()][1])
        else:
            return QtCore.QVariant()

    def getInterval(self, row: int) -> CandleInterval:
        return self.__intervals[row][1]


class GroupBox_CandlesReceiving(QtWidgets.QGroupBox):
    intervalChanged: QtCore.pyqtSignal = QtCore.pyqtSignal(CandleInterval)  # Сигнал испускается при изменении выбранного интервала.

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
                    query = QtSql.QSqlQuery(db)

                    sql_command: str = 'INSERT OR IGNORE INTO \"{0}\" (\"instrument_id\", \"interval\", \"open\", \"high\", \"low\", \"close\", \"volume\", \"time\", \"is_complete\") VALUES '.format(MyConnection.CANDLES_TABLE)
                    candles_count: int = len(candles)
                    for i in range(candles_count):
                        if i > 0: sql_command += ', '  # Если добавляемая свеча не первая.
                        sql_command += '(:uid, :interval, :open{0}, :high{0}, :low{0}, :close{0}, :volume{0}, :time{0}, :is_complete{0})'.format(i)
                    sql_command += ' ON CONFLICT (\"instrument_id\", \"interval\", \"time\") DO UPDATE SET ' \
                                   '\"open\" = \"excluded\".\"open\", \"high\" = \"excluded\".\"high\", ' \
                                   '\"low\" = \"excluded\".\"low\", \"close\" = \"excluded\".\"close\", ' \
                                   '\"volume\" = \"excluded\".\"volume\", \"is_complete\" = \"excluded\".\"is_complete\";'

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
                        query.bindValue(':time{0}'.format(i), MyConnection.convertDateTimeToText(candle.time, sep='T'))
                        query.bindValue(':is_complete{0}'.format(i), MyConnection.convertBoolToBlob(candle.is_complete))

                    exec_flag: bool = query.exec()
                    assert exec_flag, query.lastError().text()
                    '''---------------------------------------------------------------------------------------------'''

        receive_candles_method_name: str = 'GetCandles'

        printText_signal: QtCore.pyqtSignal = QtCore.pyqtSignal(str)  # Сигнал для отображения сообщений в консоли.
        releaseSemaphore_signal: QtCore.pyqtSignal = QtCore.pyqtSignal(LimitPerMinuteSemaphore, int)  # Сигнал для освобождения ресурсов семафора из основного потока.

        '''-----------------Сигналы progressBar'а-----------------'''
        setProgressBarRange_signal: QtCore.pyqtSignal = QtCore.pyqtSignal(int, int)  # Сигнал для установления минимума и максимума progressBar'а заполнения купонов.
        setProgressBarValue_signal: QtCore.pyqtSignal = QtCore.pyqtSignal(int)  # Сигнал для изменения прогресса в progressBar'е.
        '''-------------------------------------------------------'''

        def __init__(self, token_class: TokenClass, instrument: MyBondClass | MyShareClass, interval: CandleInterval, parent: QtCore.QObject | None = ...):
            super().__init__(parent)
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
                    # min_interval: timedelta = getMinInterval(self._interval)
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
                    # if dt_delta % max_interval > min_interval:
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

    def setStatus(self, status: ThreadStatus):
        print('Статус: {0} -> {1}.'.format(self.__thread_status.name, status.name))
        match status:
            case self.ThreadStatus.START_NOT_POSSIBLE:
                assert self.__token is None or self.__instrument is None

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
                        self.__candles_receiving_thread.requestInterruption()  # Сообщаем потоку о том, что надо завершиться.
                        self.__candles_receiving_thread.wait()  # Ждём завершения потока.
                        self.__candles_receiving_thread = None
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
                        self.__candles_receiving_thread.requestInterruption()  # Сообщаем потоку о том, что надо завершиться.
                        self.__candles_receiving_thread.wait()  # Ждём завершения потока.
                        self.__candles_receiving_thread = None
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
                assert self.__token is not None and self.__instrument is not None
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
                        self.__candles_receiving_thread.requestInterruption()  # Сообщаем потоку о том, что надо завершиться.
                        self.__candles_receiving_thread.wait()  # Ждём завершения потока.
                        self.__candles_receiving_thread = None
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
                        self.__candles_receiving_thread.requestInterruption()  # Сообщаем потоку о том, что надо завершиться.
                        self.__candles_receiving_thread.wait()  # Ждём завершения потока.
                        self.__candles_receiving_thread = None
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
                    self.setStatus(self.ThreadStatus.RUNNING)

                self.start_thread_connection = self.play_button.clicked.connect(__startThread)

                self.__thread_status = self.ThreadStatus.START_POSSIBLE

                self.play_button.setEnabled(True)
            case self.ThreadStatus.RUNNING:
                assert self.__token is not None and self.__instrument is not None
                match self.__thread_status:
                    case self.ThreadStatus.START_POSSIBLE:
                        self.play_button.setEnabled(False)

                        disconnect_flag: bool = self.play_button.disconnect(self.start_thread_connection)
                        assert disconnect_flag, 'Не удалось отключить слот!'

                        """==========================Поток необходимо запустить=========================="""
                        assert self.__candles_receiving_thread is None, 'Поток получения исторических свечей должен быть завершён!'
                        self.__candles_receiving_thread = GroupBox_CandlesReceiving.CandlesThread(token_class=self.__token,
                                                                                                  instrument=self.__instrument,
                                                                                                  interval=self.__interval,
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

                        self.thread_finished_connection = self.__candles_receiving_thread.finished.connect(lambda: self.setStatus(self.ThreadStatus.FINISHED))
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
                    self.setStatus(self.ThreadStatus.PAUSE)

                self.pause_thread_connection = self.play_button.clicked.connect(__pauseThread)
                '''------------------------------------------------------------------------'''

                '''------------------------------Правая кнопка------------------------------'''
                @QtCore.pyqtSlot()  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
                def __stopThread():
                    """Останавливает поток получения исторических свечей."""
                    self.setStatus(self.ThreadStatus.START_POSSIBLE)

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
                    self.setStatus(self.ThreadStatus.RUNNING)

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
                    self.setStatus(self.ThreadStatus.START_POSSIBLE)
                    self.setStatus(self.ThreadStatus.RUNNING)

                self.start_thread_connection = self.play_button.clicked.connect(__startThread)

                self.__thread_status = self.ThreadStatus.FINISHED

                self.play_button.setEnabled(True)
            case _:
                raise ValueError('Неверный статус потока!')

    def __init__(self, parent: QtWidgets.QWidget | None = ...):
        self.__token: TokenClass | None = None
        self.__instrument: MyBondClass | MyShareClass | None = None
        self.__candles_receiving_thread: GroupBox_CandlesReceiving.CandlesThread | None = None
        self.__thread_status: GroupBox_CandlesReceiving.ThreadStatus = self.ThreadStatus.START_NOT_POSSIBLE

        super().__init__(parent)

        self.verticalLayout_main = QtWidgets.QVBoxLayout(self)
        self.verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        self.verticalLayout_main.setSpacing(2)

        self.label_title = QtWidgets.QLabel(self)
        self.label_title.setFont(TITLE_FONT)
        self.label_title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.label_title.setText('ПОЛУЧЕНИЕ ИСТОРИЧЕСКИХ СВЕЧЕЙ')
        self.verticalLayout_main.addWidget(self.label_title)

        '''-----------Выбор токена для получения исторических свечей-----------'''
        self.horizontalLayout_token = QtWidgets.QHBoxLayout(self)

        self.label_token = QtWidgets.QLabel(self)
        self.label_token.setText('Токен:')
        self.horizontalLayout_token.addWidget(self.label_token)

        self.horizontalLayout_token.addItem(QtWidgets.QSpacerItem(4, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum))

        self.comboBox_token = QtWidgets.QComboBox(self)
        self.horizontalLayout_token.addWidget(self.comboBox_token)

        self.horizontalLayout_token.addItem(QtWidgets.QSpacerItem(0, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum))

        self.verticalLayout_main.addLayout(self.horizontalLayout_token)
        '''--------------------------------------------------------------------'''

        '''-----------------------Выбор интервала свечей-----------------------'''
        self.horizontalLayout_interval = QtWidgets.QHBoxLayout(self)

        self.label_interval = QtWidgets.QLabel(self)
        self.label_interval.setText('Интервал:')
        self.horizontalLayout_interval.addWidget(self.label_interval)

        self.horizontalLayout_interval.addItem(QtWidgets.QSpacerItem(4, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum))

        self.comboBox_interval = QtWidgets.QComboBox(self)
        self.comboBox_interval.setModel(CandleIntervalModel(self.comboBox_interval))
        self.__interval: CandleInterval = self.comboBox_interval.currentData(role=QtCore.Qt.ItemDataRole.UserRole)

        @QtCore.pyqtSlot(int)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
        def onIntervalChanged(index: int):
            self.__interval = self.comboBox_interval.model().getInterval(index)
            if self.__token is None or self.__instrument is None:
                self.setStatus(self.ThreadStatus.START_NOT_POSSIBLE)
            else:
                self.setStatus(self.ThreadStatus.START_POSSIBLE)
            self.intervalChanged.emit(self.__interval)

        self.comboBox_interval.currentIndexChanged.connect(onIntervalChanged)
        self.horizontalLayout_interval.addWidget(self.comboBox_interval)
        self.horizontalLayout_interval.addItem(QtWidgets.QSpacerItem(0, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum))

        self.verticalLayout_main.addLayout(self.horizontalLayout_interval)
        '''--------------------------------------------------------------------'''

        '''---------------Прогресс получения исторических свечей---------------'''
        self.horizontalLayout = QtWidgets.QHBoxLayout(self)

        self.play_button = QtWidgets.QPushButton(self)
        self.play_button.setEnabled(False)
        self.play_button.setText(self.PLAY)
        self.horizontalLayout.addWidget(self.play_button)

        self.stop_button = QtWidgets.QPushButton(self)
        self.stop_button.setEnabled(False)
        self.stop_button.setText(self.STOP)
        self.horizontalLayout.addWidget(self.stop_button)

        self.progressBar = ProgressBar_DataReceiving('progressBar_candles', self)
        self.horizontalLayout.addWidget(self.progressBar)

        self.verticalLayout_main.addLayout(self.horizontalLayout)
        '''--------------------------------------------------------------------'''

        self.start_thread_connection: QtCore.QMetaObject.Connection = QtCore.QMetaObject.Connection()
        self.pause_thread_connection: QtCore.QMetaObject.Connection = QtCore.QMetaObject.Connection()
        self.resume_thread_connection: QtCore.QMetaObject.Connection = QtCore.QMetaObject.Connection()
        self.stop_thread_connection: QtCore.QMetaObject.Connection = QtCore.QMetaObject.Connection()

        self.thread_finished_connection: QtCore.QMetaObject.Connection = QtCore.QMetaObject.Connection()

    def setToken(self, token: TokenClass | None):
        self.__token = token
        if self.__token is None or self.__instrument is None:
            self.setStatus(self.ThreadStatus.START_NOT_POSSIBLE)
        else:
            self.setStatus(self.ThreadStatus.START_POSSIBLE)

    def setInstrument(self, instrument: MyBondClass | MyShareClass):
        self.__instrument = instrument
        if self.__token is None or self.__instrument is None:
            self.setStatus(self.ThreadStatus.START_NOT_POSSIBLE)
        else:
            self.setStatus(self.ThreadStatus.START_POSSIBLE)

    @QtCore.pyqtSlot()  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
    def reset(self):
        self.__instrument = None
        self.setStatus(self.ThreadStatus.START_NOT_POSSIBLE)

    def setTokensModel(self, token_list_model: TokenListModel):
        """Устанавливает модель токенов для ComboBox'а."""
        self.comboBox_token.setModel(token_list_model)

        @QtCore.pyqtSlot(int)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
        def onTokenChanged(index: int):
            self.__token = self.comboBox_token.model().getToken(index)
            if self.__token is None or self.__instrument is None:
                self.setStatus(self.ThreadStatus.START_NOT_POSSIBLE)
            else:
                self.setStatus(self.ThreadStatus.START_POSSIBLE)

        self.comboBox_token.currentIndexChanged.connect(onTokenChanged)

    def currentInterval(self) -> CandleInterval:
        return self.__interval


class GroupBox_Chart(QtWidgets.QGroupBox):
    """Панель с диаграммой."""
    def __init__(self, parent: QtWidgets.QWidget | None = ...):
        self.__candles: list[HistoricCandle] = []
        super().__init__(parent)

        self.verticalLayout_main = QtWidgets.QVBoxLayout(self)
        self.verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        self.verticalLayout_main.setSpacing(2)

        self.label_title = QtWidgets.QLabel(self)
        self.label_title.setFont(TITLE_FONT)
        self.label_title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.label_title.setText('ГРАФИК')
        self.verticalLayout_main.addWidget(self.label_title)

        # '''------------------------------График------------------------------'''
        # self.chart_view = QtCharts.QChartView(self)
        #
        # self.candlestick_series = QtCharts.QCandlestickSeries(self.chart_view)
        # # self.candlestick_series.setName('Свечи')
        # self.candlestick_series.setDecreasingColor(QtCore.Qt.GlobalColor.red)
        # self.candlestick_series.setIncreasingColor(QtCore.Qt.GlobalColor.green)
        #
        # # self.chart = QtCharts.QChart()
        # # self.chart.addSeries(self.candlestick_series)
        # # self.chart.setTitle('График')
        # # self.chart.setAnimationOptions(QtCharts.QChart.AnimationOption.SeriesAnimations)
        # # self.chart.createDefaultAxes()
        #
        #
        # # self.chart_view.chart().setTitle('График')
        # self.chart_view.chart().setAnimationOptions(QtCharts.QChart.AnimationOption.SeriesAnimations)
        # self.chart_view.chart().addSeries(self.candlestick_series)
        # # self.chart_view.chart().createDefaultAxes()
        #
        # # axisY = QtCharts.QValueAxis()
        # # axisY.setRange(0, 110)
        # # axisY.setTickCount(11)
        # # axisY.setTitleText('Цена')
        # # # # self.chart.addAxis(axisY, QtCore.Qt.AlignmentFlag.AlignLeft)
        # # self.chart_view.chart().addAxis(axisY, QtCore.Qt.AlignmentFlag.AlignLeft)
        # # self.candlestick_series.attachAxis(axisY)
        # #
        # # axisX = QtCharts.QDateTimeAxis()
        # # # axisX.setFormat()
        # # current_dt: datetime = getMoscowDateTime()
        # # min_dt: datetime = current_dt - timedelta(days=365)
        # # axisX.setRange(min_dt, current_dt)
        # # # axisX.setTickCount(8)
        # # axisX.setTitleText('Дата и время')
        # # # self.chart.addAxis(axisX, QtCore.Qt.AlignmentFlag.AlignBottom)
        # # self.chart_view.chart().addAxis(axisX, QtCore.Qt.AlignmentFlag.AlignBottom)
        # # self.candlestick_series.attachAxis(axisX)
        #
        # # self.chart_view.setChart(self.chart)
        # self.verticalLayout_main.addWidget(self.chart_view)
        #
        # # self.graphics_scene = QtWidgets.QGraphicsScene(self)
        # # self.graphics_scene.setActiveWindow(self.chart)
        # # self.graphics_view = QtWidgets.QGraphicsView(self.graphics_scene, self)
        # # self.verticalLayout_main.addWidget(self.graphics_view)
        # '''------------------------------------------------------------------'''

        '''------------------------------График------------------------------'''
        self.chart_view = QtCharts.QChartView(self)

        self.candlestick_series = QtCharts.QCandlestickSeries(self.chart_view)
        self.candlestick_series.setDecreasingColor(QtCore.Qt.GlobalColor.red)
        self.candlestick_series.setIncreasingColor(QtCore.Qt.GlobalColor.green)

        self.chart = QtCharts.QChart()
        self.chart.addSeries(self.candlestick_series)
        self.chart.setTitle('График')
        self.chart.setAnimationOptions(QtCharts.QChart.AnimationOption.SeriesAnimations)
        # self.chart.createDefaultAxes()

        # auto axisY = qobject_cast < QValueAxis * > (chart->axes(Qt::Vertical).at(0));
        # axisY->setMax(axisY->max() * 1.01);
        # axisY->setMin(axisY->min() * 0.99);
        #
        # axisY = self.chart.axes(QtCore.Qt.Orientation.Vertical, self.candlestick_series)[0]
        # axisY.setMax(axisY)

        axisY = QtCharts.QValueAxis()
        axisY.setRange(0, 110)
        # axisY.setTickCount(11)
        axisY.setTitleText('Цена')
        self.chart.addAxis(axisY, QtCore.Qt.AlignmentFlag.AlignLeft)
        self.candlestick_series.attachAxis(axisY)

        axisX = QtCharts.QDateTimeAxis()
        current_dt: datetime = getMoscowDateTime()
        min_dt: datetime = current_dt - timedelta(days=31)
        axisX.setRange(min_dt, current_dt)
        axisX.setTitleText('Дата и время')
        self.chart.addAxis(axisX, QtCore.Qt.AlignmentFlag.AlignBottom)
        self.candlestick_series.attachAxis(axisX)

        self.chart_view.setChart(self.chart)
        self.verticalLayout_main.addWidget(self.chart_view)
        '''------------------------------------------------------------------'''

    def setCandles(self, candles: list[HistoricCandle]):
        self.__candles = candles

        '''-------------------------------Удаляем имеющиеся оси-------------------------------'''
        for axis in self.chart.axes(QtCore.Qt.Orientation.Vertical, self.candlestick_series):
            self.chart.removeAxis(axis)
        for axis in self.chart.axes(QtCore.Qt.Orientation.Horizontal, self.candlestick_series):
            self.chart.removeAxis(axis)
        '''-----------------------------------------------------------------------------------'''

        self.chart.removeSeries(self.candlestick_series)
        self.candlestick_series = QtCharts.QCandlestickSeries(self.chart_view)
        self.candlestick_series.setDecreasingColor(QtCore.Qt.GlobalColor.red)
        self.candlestick_series.setIncreasingColor(QtCore.Qt.GlobalColor.green)

        for candle in self.__candles:
            candlestick = QtCharts.QCandlestickSet(open=MyQuotation.getFloat(candle.open),
                                                   high=MyQuotation.getFloat(candle.high),
                                                   low=MyQuotation.getFloat(candle.low),
                                                   close=MyQuotation.getFloat(candle.close),
                                                   timestamp=(candle.time.timestamp()*1000), parent=self)
            self.candlestick_series.append(candlestick)

        self.chart.addSeries(self.candlestick_series)
        self.chart.createDefaultAxes()

        # axisY = QtCharts.QValueAxis()
        # axisY.setRange(94, 98)
        # # axisY.setTickCount(11)
        # axisY.setTitleText('Цена')
        # self.chart.addAxis(axisY, QtCore.Qt.AlignmentFlag.AlignLeft)
        # self.candlestick_series.attachAxis(axisY)

        for axis in self.chart.axes(QtCore.Qt.Orientation.Horizontal, self.candlestick_series):
            self.chart.removeAxis(axis)

        axisX = QtCharts.QDateTimeAxis()
        current_dt: datetime = getMoscowDateTime()
        min_dt: datetime = current_dt - timedelta(days=90)
        axisX.setRange(min_dt, current_dt)
        axisX.setTitleText('Дата и время')
        self.chart.addAxis(axisX, QtCore.Qt.AlignmentFlag.AlignBottom)
        self.candlestick_series.attachAxis(axisX)


class CandlesPage(QtWidgets.QWidget):
    """Страница свечей."""
    def __init__(self, parent: QtWidgets.QWidget | None = None):
        self.__instrument: MyBondClass | MyShareClass | None = None
        self.__candles: list[HistoricCandle] = []

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

        '''---------------Панели получения и отображения свечей---------------'''
        self.verticalLayout_candles = QtWidgets.QVBoxLayout(self)
        self.verticalLayout_candles.setSpacing(2)

        self.groupBox_candles_receiving = GroupBox_CandlesReceiving(self)
        self.__interval: CandleInterval = self.groupBox_candles_receiving.currentInterval()
        self.groupBox_instrument.bondSelected.connect(self.groupBox_candles_receiving.setInstrument)
        self.groupBox_instrument.shareSelected.connect(self.groupBox_candles_receiving.setInstrument)
        self.groupBox_instrument.instrumentReset.connect(self.groupBox_candles_receiving.reset)
        self.verticalLayout_candles.addWidget(self.groupBox_candles_receiving)

        self.groupBox_candles_view = GroupBox_CandlesView(self)
        self.verticalLayout_candles.addWidget(self.groupBox_candles_view)

        self.horizontalLayout_top.addLayout(self.verticalLayout_candles)
        '''-------------------------------------------------------------------'''

        self.verticalLayout_main.addLayout(self.horizontalLayout_top)
        """============================================================="""

        """========================Нижняя часть========================"""
        self.groupBox_chart = GroupBox_Chart(self)
        self.verticalLayout_main.addWidget(self.groupBox_chart)
        """============================================================"""

        def getCandlesFromDb() -> list[HistoricCandle]:
            uid: str = self.__instrument.instrument().uid
            db: QtSql.QSqlDatabase = MainConnection.getDatabase()
            query = QtSql.QSqlQuery(db)
            prepare_flag: bool = query.prepare(
                'SELECT \"open\", \"high\", \"low\", \"close\", \"volume\", \"time\", \"is_complete\" FROM \"{0}\" '
                'WHERE \"instrument_id\" = :uid and \"interval\" = :interval;'.format(MyConnection.CANDLES_TABLE)
            )
            assert prepare_flag, query.lastError().text()

            query.bindValue(':uid', uid)
            query.bindValue(':interval', self.__interval.name)

            exec_flag: bool = query.exec()
            assert exec_flag, query.lastError().text()

            candles: list[HistoricCandle] = []
            while query.next():
                def getHistoricCandle() -> HistoricCandle:
                    """Создаёт и возвращает экземпляр класса HistoricCandle."""
                    open_: Quotation = MyConnection.convertTextToQuotation(query.value('open'))
                    high: Quotation = MyConnection.convertTextToQuotation(query.value('high'))
                    low: Quotation = MyConnection.convertTextToQuotation(query.value('low'))
                    close: Quotation = MyConnection.convertTextToQuotation(query.value('close'))
                    volume: int = query.value('volume')
                    time: datetime = MyConnection.convertTextToDateTime(query.value('time'))
                    is_complete: bool = MyConnection.convertBlobToBool(query.value('is_complete'))
                    return HistoricCandle(open=open_, high=high, low=low, close=close, volume=volume, time=time,
                                          is_complete=is_complete)

                candles.append(getHistoricCandle())
            return candles

        def onInstrumentChanged(instrument: MyBondClass | MyShareClass):
            self.__instrument = instrument
            self.candles = getCandlesFromDb()

        self.groupBox_instrument.bondSelected.connect(onInstrumentChanged)
        self.groupBox_instrument.shareSelected.connect(onInstrumentChanged)

        @QtCore.pyqtSlot()  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
        def onInstrumentReset():
            self.__instrument = None
            self.candles = []

        self.groupBox_instrument.instrumentReset.connect(onInstrumentReset)

        @QtCore.pyqtSlot(CandleInterval)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
        def onIntervalChanged(interval: CandleInterval):
            self.__interval = interval
            if self.__instrument is None:
                assert not self.candles
            else:
                self.candles = getCandlesFromDb()

        self.groupBox_candles_receiving.intervalChanged.connect(onIntervalChanged)

    @property
    def candles(self) -> list[HistoricCandle]:
        return self.__candles

    @candles.setter
    def candles(self, candles: list[HistoricCandle]):
        self.__candles = candles
        self.groupBox_candles_view.setCandles(self.candles)
        self.groupBox_chart.setCandles(self.candles)

    def setTokensModel(self, token_list_model: TokenListModel):
        """Устанавливает модель токенов для ComboBox'а."""
        self.groupBox_candles_receiving.setTokensModel(token_list_model)
