import typing
from datetime import datetime
from PyQt6.QtCore import QAbstractTableModel, QObject, QModelIndex, QSortFilterProxyModel, Qt, QVariant
from PyQt6.QtGui import QBrush
from PyQt6.QtSql import QSqlDatabase, QSqlQuery
from tinkoff.invest import InstrumentStatus, Bond, Quotation, SecurityTradingStatus, RealExchange
from tinkoff.invest.schemas import RiskLevel
from Classes import MyConnection, Column, TokenClass, reportTradingStatus
from MyBondClass import MyBondClass, MyBond
from MyDatabase import MainConnection
from MyDateTime import reportSignificantInfoFromDateTime, ifDateTimeIsEmpty
from MyMoneyValue import MyMoneyValue
from MyQuotation import MyQuotation


class BondColumn(Column):
    """Класс столбца таблицы облигаций."""
    # MATURITY_COLOR: QBrush = QBrush(Qt.GlobalColor.magenta)  # Цвет фона строк погашенных облигаций.
    def __init__(self, header: str | None = None, header_tooltip: str | None = None, data_function=None, display_function=None, tooltip_function=None,
                 background_function=lambda bond_class, *args: QBrush(Qt.GlobalColor.magenta) if bond_class.bond.perpetual_flag and ifDateTimeIsEmpty(bond_class.bond.maturity_date) else QBrush(Qt.GlobalColor.lightGray) if MyBond.ifBondIsMaturity(bond_class.bond) else QVariant(),
                 foreground_function=None, lessThan=None, sort_role: Qt.ItemDataRole = Qt.ItemDataRole.UserRole):
        super().__init__(header, header_tooltip, data_function, display_function, tooltip_function,
                         background_function, foreground_function, lessThan, sort_role)


class BondsModel(QAbstractTableModel):
    """Модель облигаций."""
    def __init__(self, token: TokenClass | None, instrument_status: InstrumentStatus, sql_condition: str | None, parent: QObject | None = None):
        super().__init__(parent)  # __init__() QAbstractTableModel.

        '''---------------------Функции, используемые в столбцах модели---------------------'''
        def reportRiskLevel(risk_level: RiskLevel) -> str:
            """Расшифровывает уровень риска облигации."""
            match risk_level:
                case RiskLevel.RISK_LEVEL_UNSPECIFIED: return '-'
                case RiskLevel.RISK_LEVEL_LOW: return 'Низкий'
                case RiskLevel.RISK_LEVEL_MODERATE: return 'Средний'
                case RiskLevel.RISK_LEVEL_HIGH: return 'Высокий'
                case _:
                    assert False, 'Неизвестное значение переменной класса RiskLevel ({0}) в функции {1}!'.format(risk_level, reportRiskLevel.__name__)
                    return ''
        '''---------------------------------------------------------------------------------'''

        self.columns: tuple[BondColumn, ...] = (
            BondColumn(header='figi',
                       header_tooltip='Figi-идентификатор инструмента.',
                       data_function=lambda bond_class: bond_class.bond.figi),
            BondColumn(header='isin',
                       header_tooltip='Isin-идентификатор инструмента.',
                       data_function=lambda bond_class: bond_class.bond.isin),
            BondColumn(header='Название',
                       header_tooltip='Название инструмента.',
                       data_function=lambda bond_class: bond_class.bond.name),
            BondColumn(header='Лотность',
                       header_tooltip='Лотность инструмента.',
                       data_function=lambda bond_class: bond_class.bond.lot,
                       display_function=lambda bond_class: str(bond_class.bond.lot)),
            BondColumn(header='Цена лота',
                       header_tooltip='Цена последней сделки по лоту облигации.',
                       data_function=lambda bond_class: bond_class.getLotLastPrice(),
                       display_function=lambda bond_class: bond_class.reportLotLastPrice(),
                       tooltip_function=lambda bond_class: 'Нет данных.' if bond_class.last_price is None else 'last_price:\nfigi = {0},\nprice = {1},\ntime = {2},\ninstrument_uid = {3}.\n\nlot = {4}'.format(bond_class.last_price.figi, MyQuotation.__str__(bond_class.last_price.price, 2), bond_class.last_price.time, bond_class.last_price.instrument_uid, bond_class.bond.lot)),
            BondColumn(header='НКД',
                       header_tooltip='Значение НКД (накопленного купонного дохода) на дату.',
                       data_function=lambda bond_class: bond_class.bond.aci_value,
                       display_function=lambda bond_class: MyMoneyValue.__str__(bond_class.bond.aci_value)),
            BondColumn(header='Номинал',
                       header_tooltip='Номинал облигации.',
                       data_function=lambda bond_class: bond_class.bond.nominal,
                       display_function=lambda bond_class: MyMoneyValue.__str__(bond_class.bond.nominal, 2)),
            BondColumn(header='Шаг цены',
                       header_tooltip='Минимальное изменение цены определённого инструмента.',
                       data_function=lambda bond_class: bond_class.bond.min_price_increment,
                       display_function=lambda bond_class: MyQuotation.__str__(bond_class.bond.min_price_increment, ndigits=9, delete_decimal_zeros=True)),
            BondColumn(header='Амортизация',
                       header_tooltip='Признак облигации с амортизацией долга.',
                       data_function=lambda bond_class: bond_class.bond.amortization_flag,
                       display_function=lambda bond_class: "Да" if bond_class.bond.amortization_flag else "Нет"),
            BondColumn(header='Дней до погашения',
                       header_tooltip='Количество дней до погашения облигации.',
                       data_function=lambda bond_class: MyBond.getDaysToMaturityCount(bond_class.bond),
                       display_function=lambda bond_class: 'Нет данных' if ifDateTimeIsEmpty(bond_class.bond.maturity_date) else MyBond.getDaysToMaturityCount(bond_class.bond)),
            BondColumn(header='Дата погашения',
                       header_tooltip='Дата погашения облигации в часовом поясе UTC.',
                       data_function=lambda bond_class: bond_class.bond.maturity_date,
                       display_function=lambda bond_class: reportSignificantInfoFromDateTime(bond_class.bond.maturity_date),
                       tooltip_function=lambda bond_class: str(bond_class.bond.maturity_date)),
            BondColumn(header='Валюта',
                       header_tooltip='Валюта расчётов.',
                       data_function=lambda bond_class: bond_class.bond.currency),
            BondColumn(header='Страна риска',
                       header_tooltip='Наименование страны риска, т.е. страны, в которой компания ведёт основной бизнес.',
                       data_function=lambda bond_class: bond_class.bond.country_of_risk_name),
            BondColumn(header='Риск',
                       header_tooltip='Уровень риска.',
                       data_function=lambda bond_class: bond_class.bond.risk_level,
                       display_function=lambda bond_class: reportRiskLevel(bond_class.bond.risk_level)),
            BondColumn(header='Режим торгов',
                       header_tooltip='Текущий режим торгов инструмента.',
                       data_function=lambda bond_class: bond_class.bond.trading_status,
                       display_function=lambda bond_class: reportTradingStatus(bond_class.bond.trading_status))
        )
        self._bonds: list[MyBondClass] = []

        '''------------------Параметры запроса к БД------------------'''
        self.__token: TokenClass | None = None
        self.__instrument_status: InstrumentStatus = instrument_status
        self.__sql_condition: str | None = sql_condition
        '''----------------------------------------------------------'''

        self.update(token, instrument_status, sql_condition)  # Обновляем данные модели.

    # @property
    # def token(self) -> TokenClass | None:
    #     return self.__token
    #
    # @token.setter
    # def token(self, token: TokenClass | None):
    #     self.__token = token
    #     self.update()  # Обновляем данные модели.
    #
    # @property
    # def instrument_status(self) -> InstrumentStatus:
    #     return self.__instrument_status
    #
    # @instrument_status.setter
    # def instrument_status(self, instrument_status: InstrumentStatus):
    #     self.__instrument_status = instrument_status
    #     self.update()  # Обновляем данные модели.
    #
    # @property
    # def sql_condition(self) -> str | None:
    #     return self.__sql_condition
    #
    # @sql_condition.setter
    # def sql_condition(self, sql_condition: str | None):
    #     self.__sql_condition = sql_condition
    #     self.update()  # Обновляем данные модели.

    def update(self, token: TokenClass | None, instrument_status: InstrumentStatus, sql_condition: str | None):
        """Обновляет данные модели в соответствии с переданными параметрами запроса к БД."""
        self.beginResetModel()  # Начинает операцию сброса модели.

        '''------------------Параметры запроса к БД------------------'''
        self.__token = token
        self.__instrument_status = instrument_status
        self.__sql_condition = sql_condition
        '''----------------------------------------------------------'''

        if token is None:
            self._bonds = []
        else:
            '''---------------------------Создание запроса к БД---------------------------'''
            # sql_command: str = '''
            # SELECT "figi", "ticker", "class_code", "isin", "lot", "currency", "klong", "kshort", "dlong", "dshort",
            # "dlong_min", "dshort_min", "short_enabled_flag", "name", "exchange", "coupon_quantity_per_year",
            # "maturity_date", "nominal", "initial_nominal", "state_reg_date", "placement_date", "placement_price",
            # "aci_value", "country_of_risk", "country_of_risk_name", "sector", "issue_kind", "issue_size", "issue_size_plan",
            # "trading_status", "otc_flag", "buy_available_flag", "sell_available_flag", "floating_coupon_flag",
            # "perpetual_flag", "amortization_flag", "min_price_increment", "api_trade_available_flag", "Bonds"."uid",
            # "real_exchange", "position_uid", "for_iis_flag", "for_qual_investor_flag", "weekend_flag", "blocked_tca_flag",
            # "subordinated_flag", "liquidity_flag", "first_1min_candle_date", "first_1day_candle_date", "risk_level"
            # FROM "BondsStatus", "Bonds"
            # WHERE "BondsStatus"."token" = :token AND "BondsStatus"."status" = :status AND
            # "BondsStatus"."uid" = "Bonds"."uid";'''

            sql_command: str = '''
            SELECT "figi", "ticker", "class_code", "isin", "lot", "currency", "klong", "kshort", "dlong", "dshort",
            "dlong_min", "dshort_min", "short_enabled_flag", "name", "exchange", "coupon_quantity_per_year",
            "maturity_date", "nominal", "initial_nominal", "state_reg_date", "placement_date", "placement_price",
            "aci_value", "country_of_risk", "country_of_risk_name", "sector", "issue_kind", "issue_size", "issue_size_plan", 
            "trading_status", "otc_flag", "buy_available_flag", "sell_available_flag", "floating_coupon_flag", 
            "perpetual_flag", "amortization_flag", "min_price_increment", "api_trade_available_flag", {0}."uid", 
            "real_exchange", "position_uid", "for_iis_flag", "for_qual_investor_flag", "weekend_flag", "blocked_tca_flag", 
            "subordinated_flag", "liquidity_flag", "first_1min_candle_date", "first_1day_candle_date", "risk_level"
            FROM "BondsStatus", {0}
            WHERE "BondsStatus"."token" = :token AND "BondsStatus"."status" = :status AND
            "BondsStatus"."uid" = {0}."uid"{1};'''.format(
                '\"{0}\"'.format(MyConnection.BONDS_TABLE),
                '' if sql_condition is None else ' AND {0}'.format(sql_condition)
            )

            db: QSqlDatabase = MainConnection.getDatabase()
            query = QSqlQuery(db)
            prepare_flag: bool = query.prepare(sql_command)
            assert prepare_flag, query.lastError().text()

            query.bindValue(':token', token.token)
            query.bindValue(':status', instrument_status.name)

            exec_flag: bool = query.exec()
            assert exec_flag, query.lastError().text()
            '''---------------------------------------------------------------------------'''

            '''------------------------Извлекаем список облигаций------------------------'''
            self._bonds = []
            while query.next():
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
                    short_enabled_flag: bool = bool(query.value('short_enabled_flag'))
                    name: str = query.value('name')
                    exchange: str = query.value('exchange')
                    coupon_quantity_per_year: int = query.value('coupon_quantity_per_year')
                    maturity_date: datetime = MyConnection.convertTextToDateTime(query.value('maturity_date'))
                    nominal: MyMoneyValue = MyConnection.convertTextToMyMoneyValue(query.value('nominal'))
                    initial_nominal: MyMoneyValue = MyConnection.convertTextToMyMoneyValue(query.value('initial_nominal'))
                    state_reg_date: datetime = MyConnection.convertTextToDateTime(query.value('state_reg_date'))
                    placement_date: datetime = MyConnection.convertTextToDateTime(query.value('placement_date'))
                    placement_price: MyMoneyValue = MyConnection.convertTextToMyMoneyValue(query.value('placement_price'))
                    aci_value: MyMoneyValue = MyConnection.convertTextToMyMoneyValue(query.value('aci_value'))
                    country_of_risk: str = query.value('country_of_risk')
                    country_of_risk_name: str = query.value('country_of_risk_name')
                    sector: str = query.value('sector')
                    issue_kind: str = query.value('issue_kind')
                    issue_size: int = query.value('issue_size')
                    issue_size_plan: int = query.value('issue_size_plan')
                    trading_status: SecurityTradingStatus = SecurityTradingStatus(query.value('trading_status'))
                    otc_flag: bool = bool(query.value('otc_flag'))
                    buy_available_flag: bool = bool(query.value('buy_available_flag'))
                    sell_available_flag: bool = bool(query.value('sell_available_flag'))
                    floating_coupon_flag: bool = bool(query.value('floating_coupon_flag'))
                    perpetual_flag: bool = bool(query.value('perpetual_flag'))
                    amortization_flag: bool = bool(query.value('amortization_flag'))
                    min_price_increment: Quotation = MyConnection.convertTextToQuotation(query.value('min_price_increment'))
                    api_trade_available_flag: bool = bool(query.value('api_trade_available_flag'))
                    uid: str = query.value('uid')
                    real_exchange: RealExchange = RealExchange(query.value('real_exchange'))
                    position_uid: str = query.value('position_uid')
                    for_iis_flag: bool = bool(query.value('for_iis_flag'))
                    for_qual_investor_flag: bool = bool(query.value('for_qual_investor_flag'))
                    weekend_flag: bool = bool(query.value('weekend_flag'))
                    blocked_tca_flag: bool = bool(query.value('blocked_tca_flag'))
                    subordinated_flag: bool = bool(query.value('subordinated_flag'))
                    liquidity_flag: bool = bool(query.value('liquidity_flag'))
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

                bond: Bond = getBond()
                bond_class: MyBondClass = MyBondClass(bond)
                self._bonds.append(bond_class)
            '''--------------------------------------------------------------------------'''

        self.endResetModel()  # Завершает операцию сброса модели.

    def rowCount(self, parent: QModelIndex = ...) -> int:
        """Возвращает количество облигаций в модели."""
        return len(self._bonds)

    def columnCount(self, parent: QModelIndex = ...) -> int:
        """Возвращает количество столбцов в модели."""
        return len(self.columns)

    def data(self, index: QModelIndex, role: int = ...) -> typing.Any:
        column: Column = self.columns[index.column()]
        bond_class: MyBondClass = self._bonds[index.row()]
        return column(role, bond_class)


class BondsProxyModel(QSortFilterProxyModel):
    """Прокси-модель облигаций."""
    def __init__(self, source_model: QAbstractTableModel | None, parent: QObject | None = None):
        super().__init__(parent)  # __init__() QSortFilterProxyModel.
        self.setSourceModel(source_model)  # Подключаем исходную модель к прокси-модели.

    def sourceModel(self) -> BondsModel:
        """Возвращает исходную модель."""
        source_model = super().sourceModel()
        assert type(source_model) == BondsModel
        return typing.cast(BondsModel, source_model)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = ...) -> typing.Any:
        """Функция headerData объявлена в прокси-модели, чтобы названия строк не сортировались вместе с данными."""
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Vertical: return section + 1  # Проставляем номера строк.
            if orientation == Qt.Orientation.Horizontal: return self.sourceModel().columns[section].header
        elif role == Qt.ItemDataRole.ToolTipRole:  # Подсказки.
            if orientation == Qt.Orientation.Horizontal: return self.sourceModel().columns[section].header_tooltip
