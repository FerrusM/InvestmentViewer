import typing
from datetime import datetime
from PyQt6 import QtSql, QtCore, QtGui
from PyQt6.QtCore import QAbstractTableModel, QObject, QModelIndex, QSortFilterProxyModel, Qt, QVariant
from decimal import Decimal
from tinkoff.invest import InstrumentStatus, Bond, Quotation, SecurityTradingStatus, RealExchange
from tinkoff.invest.schemas import RiskLevel, LastPrice, Coupon, CouponType, MoneyValue
from Classes import MyConnection, Column, TokenClass, reportTradingStatus
from MyBondClass import MyBondClass, MyBond, TINKOFF_COMMISSION, MyCoupon, NDFL, DAYS_IN_YEAR
from MyDatabase import MainConnection
from MyDateTime import reportSignificantInfoFromDateTime, ifDateTimeIsEmpty, reportDateIfOnlyDate, getUtcDateTime, getCountOfDaysBetweenTwoDateTimes
from MyLastPrice import MyLastPrice
from MyMoneyValue import MyMoneyValue, MoneyValueToMyMoneyValue
from MyQuotation import MyQuotation, MyDecimal


class BondColumn(Column):
    """Класс столбца таблицы облигаций."""
    MATURITY_COLOR: QtGui.QBrush = QtGui.QBrush(Qt.GlobalColor.lightGray)  # Цвет фона строк погашенных облигаций.
    PERPETUAL_COLOR: QtGui.QBrush = QtGui.QBrush(Qt.GlobalColor.magenta)  # Цвет фона строк бессрочных облигаций.

    def __init__(self, header: str | None = None, header_tooltip: str | None = None, data_function=None, display_function=None, tooltip_function=None,
                 background_function=lambda bond_class, *args: BondColumn.PERPETUAL_COLOR if bond_class.bond.perpetual_flag and ifDateTimeIsEmpty(bond_class.bond.maturity_date) else BondColumn.MATURITY_COLOR if MyBond.ifBondIsMaturity(bond_class.bond) else QVariant(),
                 foreground_function=None, lessThan=None, sort_role: Qt.ItemDataRole = Qt.ItemDataRole.UserRole,
                 date_dependence: bool = False, entered_datetime: datetime | None = None,
                 coupon_dependence: bool = False, lp_dependence: bool = False, bond_dependence: bool = True):
        super().__init__(header, header_tooltip, data_function, display_function, tooltip_function,
                         background_function, foreground_function, lessThan, sort_role)
        self._date_dependence: bool = date_dependence  # Флаг зависимости от даты.
        self._entered_datetime: datetime | None = entered_datetime  # Дата расчёта.
        self._coupon_dependence: bool = coupon_dependence  # Флаг зависимости от купонов.
        self._lp_dependence: bool = lp_dependence  # Флаг зависимости от последней цены.
        self._bond_dependence: bool = bond_dependence  # Флаг зависимости от облигации.

    def dependsOnDateTime(self) -> bool:
        """Возвращает True, если значение столбца зависит от выбранной даты. Иначе возвращает False."""
        return self._date_dependence

    def dependsOnCoupons(self) -> bool:
        """Возвращает True, если значение столбца зависит от купонов. Иначе возвращает False."""
        return self._coupon_dependence

    def dependsOnLastPrice(self) -> bool:
        """Возвращает True, если значение столбца зависит от последней цены. Иначе возвращает False."""
        return self._lp_dependence

    def dependsOnBond(self) -> bool:
        """Возвращает True, если значение столбца зависит от облигации. Иначе возвращает False."""
        return self._bond_dependence


class BondsModel(QAbstractTableModel):
    """Модель облигаций."""

    class BondRow:
        """Класс строки таблицы облигаций."""
        def __init__(self, rowid: int, bond_class: MyBondClass):
            self.__rowid: int = rowid  # rowid облигации в таблице облигаций.
            self.__bond_class: MyBondClass = bond_class

            self.__bond_changed_connections: list[QtCore.QMetaObject.Connection] = []
            self.__coupons_changed_connections: list[QtCore.QMetaObject.Connection] = []
            self.__last_price_changed_connections: list[QtCore.QMetaObject.Connection] = []

        @property
        def rowid(self):
            return self.__rowid

        @property
        def bond_class(self) -> MyBondClass:
            return self.__bond_class

        @property
        def bond(self) -> Bond:
            return self.__bond_class.bond

        @property
        def coupons(self) -> list[Coupon]:
            return self.__bond_class.coupons

        @property
        def last_price(self) -> LastPrice:
            return self.__bond_class.last_price

        def appendBondChangedConnection(self, bond_changed_connection: QtCore.QMetaObject.Connection):
            self.__bond_changed_connections.append(bond_changed_connection)

        def appendCouponsChangedConnection(self, coupons_changed_connection: QtCore.QMetaObject.Connection):
            self.__coupons_changed_connections.append(coupons_changed_connection)

        def appendLastPriceChangedConnection(self, last_price_changed_connection: QtCore.QMetaObject.Connection):
            self.__last_price_changed_connections.append(last_price_changed_connection)

        def disconnectAllConnections(self):
            """Отключает и удаляет все соединения."""
            for bond_connection in self.__bond_changed_connections:
                self.__bond_class.bondChanged_signal.disconnect(bond_connection)
            for coupon_connection in self.__coupons_changed_connections:
                self.__bond_class.couponsChanged_signal.disconnect(coupon_connection)
            for last_price_connection in self.__last_price_changed_connections:
                self.__bond_class.lastPriceChanged_signal.disconnect(last_price_connection)
            self.__bond_changed_connections.clear()
            self.__coupons_changed_connections.clear()
            self.__last_price_changed_connections.clear()

        def __del__(self):
            self.disconnectAllConnections()  # Отключаем и удаляем все соединения.


    def __init__(self, token: TokenClass | None, instrument_status: InstrumentStatus, sql_condition: str | None, calculation_dt: datetime, parent: QObject | None = None):
        super().__init__(parent=parent)

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

        def lessThan_MyMoneyValue_or_None(left: QModelIndex, right: QModelIndex, role: int) -> bool:
            """Функция сортировки для значений MyMoneyValue | None."""
            left_data: MyMoneyValue | None = left.data(role=role)
            right_data: MyMoneyValue | None = right.data(role=role)
            if type(left_data) == MyMoneyValue:
                if type(right_data) == MyMoneyValue:
                    return left_data < right_data
                elif right_data is None:
                    return False
                else:
                    assert False, 'Некорректный тип переменной \"right_data\" ({0}) в функции {1}!'.format(type(right_data), lessThan_MyMoneyValue_or_None.__name__)
                    return False
            elif left_data is None:
                if type(right_data) == MyMoneyValue:
                    return True
                elif right_data is None:
                    return False
                else:
                    assert False, 'Некорректный тип переменной \"right_data\" ({0}) в функции {1}!'.format(type(right_data), lessThan_MyMoneyValue_or_None.__name__)
                    return False
            else:
                assert False, 'Некорректный тип переменной \"left_data\" ({0}) в функции {1}!'.format(type(left_data), lessThan_MyMoneyValue_or_None.__name__)
                return True

        def lessThan_Decimal_or_None(left: QModelIndex, right: QModelIndex, role: Qt.ItemDataRole):
            """Функция сортировки для значений Decimal | None."""
            left_data: Decimal | None = left.data(role=role)
            right_data: Decimal | None = right.data(role=role)
            if type(left_data) == Decimal:
                if type(right_data) == Decimal:
                    return left_data < right_data
                elif right_data is None:
                    return False
                else:
                    assert False, 'Некорректный тип переменной \"right_data\" ({0}) в функции {1}!'.format(type(right_data), lessThan_Decimal_or_None.__name__)
                    return False
            elif left_data is None:
                if type(right_data) == Decimal:
                    return True
                elif right_data is None:
                    return False
                else:
                    assert False, 'Некорректный тип переменной \"right_data\" ({0}) в функции {1}!'.format(type(right_data), lessThan_Decimal_or_None.__name__)
                    return False
            else:
                assert False, 'Некорректный тип переменной \"left_data\" ({0}) в функции {1}!'.format(type(left_data), lessThan_Decimal_or_None.__name__)
                return True

        def lessThan_RiskLevel(left: QModelIndex, right: QModelIndex, role: Qt.ItemDataRole) -> bool:
            """Функция сортировки для столбца BOND_RISK_LEVEL."""
            left_data: RiskLevel = left.data(role=role)
            right_data: RiskLevel = right.data(role=role)
            if type(left_data) == RiskLevel and type(right_data) == RiskLevel:
                if left_data == RiskLevel.RISK_LEVEL_UNSPECIFIED:
                    if right_data in (RiskLevel.RISK_LEVEL_LOW, RiskLevel.RISK_LEVEL_MODERATE, RiskLevel.RISK_LEVEL_HIGH):
                        return False
                    elif right_data == RiskLevel.RISK_LEVEL_UNSPECIFIED:
                        return False
                    else:
                        raise ValueError('Некорректное значение переменной \"Уровень риска\" ({0})!'.format(right_data))
                elif left_data in (RiskLevel.RISK_LEVEL_LOW, RiskLevel.RISK_LEVEL_MODERATE, RiskLevel.RISK_LEVEL_HIGH):
                    if right_data in (RiskLevel.RISK_LEVEL_LOW, RiskLevel.RISK_LEVEL_MODERATE, RiskLevel.RISK_LEVEL_HIGH):
                        return left_data < right_data
                    elif right_data == RiskLevel.RISK_LEVEL_UNSPECIFIED:
                        return True
                    else:
                        raise ValueError('Некорректное значение переменной \"Уровень риска\" ({0})!'.format(right_data))
                else:
                    raise ValueError('Некорректное значение переменной \"Уровень риска\" ({0})!'.format(left_data))
            else:
                raise TypeError('Некорректный тип переменной в функции lessThan_RiskLevel!')

        def reportCouponAbsoluteProfitCalculation(bond_class: MyBondClass, calculation_datetime: datetime, current_dt: datetime = getUtcDateTime()) -> str:
            """Рассчитывает купонную доходность к указанной дате."""
            if bond_class.coupons is None: return "Купоны ещё не заполнены."  # Если купоны ещё не были заполнены.
            # Если выбранная дата меньше текущей даты.
            if calculation_datetime < current_dt: return "Выбранная дата ({0}) меньше текущей даты ({1}).".format(reportDateIfOnlyDate(calculation_datetime), reportDateIfOnlyDate(current_dt))
            # Если список купонов пуст, то используем bond.currency в качестве валюты и возвращаем 0.
            if len(bond_class.coupons) == 0: return "Список купонов пуст."

            profit: MyMoneyValue = MyMoneyValue(bond_class.coupons[0].pay_one_bond.currency)  # Доходность к выбранной дате.
            report: str = "Купонные начисления в выбранный период ({0} - {1}):".format(reportDateIfOnlyDate(current_dt), reportDateIfOnlyDate(calculation_datetime))
            for coupon in reversed(bond_class.coupons):
                """
                Расчёт купонной доходности не учитывает НКД, который выплачивается при покупке облигации,
                но учитывает НКД, который будет получен до даты конца расчёта.
                НКД, который выплачивается при покупке облигации, учитывается в расчётах доходностей облигации.
                Расчёт купонной доходности учитывает НДФЛ (в том числе НДФЛ на НКД).
                """
                # Если купонный период текущего купона целиком находится в границах заданного интервала.
                if current_dt < coupon.coupon_start_date and calculation_datetime > coupon.coupon_end_date:
                    pay_one_bond: MyMoneyValue = MoneyValueToMyMoneyValue(coupon.pay_one_bond) * (1 - NDFL)
                    profit += pay_one_bond  # Прибавляем величину купонной выплаты с учётом НДФЛ.
                    report += "\n\t{0} Купон {1}: +{3} ({2} - 13%)".format(reportDateIfOnlyDate(coupon.coupon_date),
                                                                           str(coupon.coupon_number),
                                                                           MyMoneyValue.__str__(coupon.pay_one_bond),
                                                                           MyMoneyValue.__str__(pay_one_bond))
                # Если текущий (в цикле) купон является текущим на дату начала расчёта.
                elif MyCoupon.ifCouponIsCurrent(coupon, current_dt):
                    # Если фиксация реестра не была произведена.
                    if not MyCoupon.ifRegistryWasFixed(coupon, current_dt):
                        # Если купон будет выплачен до даты конца расчёта.
                        if calculation_datetime >= coupon.coupon_date:
                            pay_one_bond: MyMoneyValue = MoneyValueToMyMoneyValue(coupon.pay_one_bond) * (1 - NDFL)
                            profit += pay_one_bond  # Прибавляем величину купонной выплаты с учётом НДФЛ.
                            report += "\n\t{0} Купон {1}: +{3} ({2} - 13%)".format(
                                reportDateIfOnlyDate(coupon.coupon_date), str(coupon.coupon_number),
                                MyMoneyValue.__str__(coupon.pay_one_bond), MyMoneyValue.__str__(pay_one_bond))
                        # Если фиксация текущего на дату начала расчёта купона будет произведена до даты конца расчёта.
                        elif MyCoupon.ifRegistryWasFixed(coupon, calculation_datetime):
                            # Всё равно прибавляем величину купонной выплаты с учётом НДФЛ, хоть она и придёт только в день выплаты.
                            pay_one_bond: MyMoneyValue = MoneyValueToMyMoneyValue(coupon.pay_one_bond) * (1 - NDFL)
                            profit += pay_one_bond  # Прибавляем величину купонной выплаты с учётом НДФЛ.
                            report += "\n\t{0} Купон {1}: +{3} ({2} - 13%) (Купон будет выплачен после выбранной даты)".format(
                                reportDateIfOnlyDate(coupon.coupon_date), str(coupon.coupon_number),
                                MyMoneyValue.__str__(coupon.pay_one_bond), MyMoneyValue.__str__(pay_one_bond))
                        # Если фиксация реестра и выплата купона произойдут после даты конца расчёта.
                        else:
                            aci: MyMoneyValue | None = MyCoupon.getCouponACI(coupon, calculation_datetime, False)  # НКД купона к дате конца расчёта.
                            if aci is None:  # Купонный период равен нулю.
                                return "Купон {0}: Купонный период равен нулю.".format(str(coupon.coupon_number))
                            aci_with_ndfl = aci * (1 - NDFL)  # Учитываем НДФЛ.
                            profit += aci_with_ndfl  # Прибавляем НКД с учётом НДФЛ.
                            report += "\n\t{0} Начисленный НКД: +{2} ({1} - 13%)".format(
                                reportDateIfOnlyDate(calculation_datetime), MyMoneyValue.__str__(aci),
                                MyMoneyValue.__str__(aci_with_ndfl))
                # Если текущий (в цикле) купон является текущим на дату конца расчёта.
                elif MyCoupon.ifCouponIsCurrent(coupon, calculation_datetime):
                    # Если фиксация реестра будет произведена на дату конца расчёта.
                    if MyCoupon.ifRegistryWasFixed(coupon, current_dt):
                        # Прибавляем величину купонной выплаты с учётом НДФЛ, хоть она и придёт только в день выплаты.
                        pay_one_bond: MyMoneyValue = MoneyValueToMyMoneyValue(coupon.pay_one_bond) * (1 - NDFL)
                        profit += pay_one_bond  # Прибавляем величину купонной выплаты с учётом НДФЛ.
                        report += "\n\t{0} Купон {1}: +{3} ({2} - 13%) (Купон будет выплачен после выбранной даты)".format(
                            reportDateIfOnlyDate(coupon.coupon_date), coupon.coupon_number,
                            MyMoneyValue.__str__(coupon.pay_one_bond), MyMoneyValue.__str__(pay_one_bond))
                    # Если фиксация реестра не была произведена.
                    else:
                        aci: MyMoneyValue | None = MyCoupon.getCouponACI(coupon, calculation_datetime, False)  # НКД купона к указанной дате.
                        if aci is None:  # Купонный период равен нулю.
                            return "Купон {0}: Купонный период равен нулю.".format(coupon.coupon_number)
                        aci_with_ndfl = aci * (1 - NDFL)  # Учитываем НДФЛ.
                        profit += aci_with_ndfl  # Прибавляем НКД с учётом НДФЛ.
                        report += "\n\t{0} Начисленный НКД: +{2} ({1} - 13%)".format(
                            reportDateIfOnlyDate(calculation_datetime), MyMoneyValue.__str__(aci),
                            MyMoneyValue.__str__(aci_with_ndfl))
            return report

        def reportAbsoluteProfitCalculation(bond_class: MyBondClass, calculation_datetime: datetime) -> str:
            """Отображает подробности расчёта абсолютной доходности."""
            if MyBond.ifBondIsMulticurrency(bond_class.bond): return "Расчёт доходности мультивалютных облигаций ещё не реализован."
            # Доходность к выбранной дате (откуда брать валюту?).
            absolute_profit: MyMoneyValue = MyMoneyValue(bond_class.bond.currency, Quotation(units=0, nano=0))

            """---------Считаем купонную доходность---------"""
            coupon_profit: MyMoneyValue | None = bond_class.getCouponAbsoluteProfit(calculation_datetime)  # Купонный доход к выбранной дате.
            if coupon_profit is None: return "Не удалось рассчитать купонную доходность."
            absolute_profit += coupon_profit
            report: str = "Расчёт купонного дохода к выбранной дате:\n\t{0}\n\tКупонная доходность: {1}".format(reportCouponAbsoluteProfitCalculation(bond_class, calculation_datetime), MyMoneyValue.__str__(coupon_profit))
            """---------------------------------------------"""

            """---------------Учитываем НКД в цене---------------"""
            # НКД, указанная в облигации, учитывает дату фиксации реестра.
            absolute_profit -= bond_class.bond.aci_value  # Вычитаем НКД.
            report += "\nНКД, указанный в облигации: - {0}".format(MyMoneyValue.__str__(bond_class.bond.aci_value))
            """--------------------------------------------------"""

            """--Учитываем возможное погашение облигации к выбранной дате--"""
            if bond_class.last_price is None:
                raise ValueError('Последняя цена облигации должна была быть получена!')
            if not MyLastPrice.isEmpty(bond_class.last_price):  # Проверка цены.
                # Если облигация будет погашена до выбранной даты включительно.
                if calculation_datetime >= bond_class.bond.maturity_date:
                    # Добавляем в доходность разницу между номиналом и ценой облигации.
                    absolute_profit += bond_class.bond.nominal
                    last_price_value: MyMoneyValue = bond_class.getLastPrice()
                    absolute_profit -= (last_price_value * (1.0 + TINKOFF_COMMISSION))
                    report += "\nОблигация будет погашена до выбранной даты.\nРазница между номиналом и ценой с учётом комиссии: {0}".format(
                        MyMoneyValue.__str__(MoneyValueToMyMoneyValue(bond_class.bond.nominal) - (last_price_value * (1.0 + TINKOFF_COMMISSION))))
            else:
                # Если цена облигации неизвестна, то рассчитывается так, будто цена облигации равняется номиналу.
                absolute_profit -= (MoneyValueToMyMoneyValue(bond_class.bond.nominal) * TINKOFF_COMMISSION)
                report += "\nЦена облигации неизвестна, используем в расчёте номинал.\nНоминал облигации с учётом комиссии: {0}".format(bond_class.bond.nominal)
            """------------------------------------------------------------"""
            report += "\nИтого: {0}".format(MyMoneyValue.__str__(absolute_profit))
            return report

        def showRelativeProfit(bond_class: MyBondClass, calculation_datetime: datetime) -> str | QVariant:
            """Функция для отображения относительной доходности облигации к дате расчёта."""
            if bond_class.coupons is None: return QVariant()  # Если купоны ещё не были получены, то не отображаем ничего.
            relative_profit: Decimal | None = bond_class.getRelativeProfit(calculation_datetime)
            return 'None' if relative_profit is None else '{0}%'.format(MyDecimal.report((relative_profit * 100), 2))

        def getAnnualProfit(bond_class: MyBondClass, calculation_datetime: datetime, start_datetime: datetime = getUtcDateTime()) -> Decimal | None:
            """Возвращает доходность облигации за выбранный период в пересчёте на год."""
            relative_profit: Decimal | None = bond_class.getRelativeProfit(calculation_datetime)  # Рассчитывает относительную доходность к выбранной дате.
            if relative_profit is None: return None
            days_count: int = getCountOfDaysBetweenTwoDateTimes(start_datetime, calculation_datetime)
            if days_count < 1:
                return None
            else:
                return (relative_profit / days_count) * DAYS_IN_YEAR

        def showAnnualProfit(bond_class: MyBondClass, calculation_datetime: datetime) -> str | QVariant:
            if bond_class.coupons is None: return QVariant()  # Если купоны ещё не были получены, то не отображаем ничего.
            annual_profit: Decimal | None = getAnnualProfit(bond_class, calculation_datetime)
            return 'None' if annual_profit is None else '{0}%'.format(MyDecimal.report((annual_profit * 100), 2))
        '''---------------------------------------------------------------------------------'''

        self.columns: tuple[BondColumn, ...] = (
            BondColumn(header='uid',
                       header_tooltip='Уникальный идентификатор инструмента.',
                       data_function=lambda bond_class: bond_class.bond.uid),
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
                       display_function=lambda bond_class: str(bond_class.bond.lot),
                       sort_role=Qt.ItemDataRole.UserRole,
                       lessThan=lambda left, right, role: left.data(role=role) < right.data(role=role)),
            BondColumn(header='Цена лота',
                       header_tooltip='Цена последней сделки по лоту облигации.',
                       data_function=lambda bond_class: bond_class.getLotLastPrice(),
                       display_function=lambda bond_class: bond_class.reportLotLastPrice(),
                       tooltip_function=lambda bond_class: 'Нет данных.' if bond_class.last_price is None else 'last_price:\nfigi = {0},\nprice = {1},\ntime = {2},\ninstrument_uid = {3}.\n\nlot = {4}'.format(bond_class.last_price.figi, MyQuotation.__str__(bond_class.last_price.price, 2), bond_class.last_price.time, bond_class.last_price.instrument_uid, bond_class.bond.lot),
                       sort_role=Qt.ItemDataRole.UserRole,
                       lessThan=lessThan_MyMoneyValue_or_None,
                       lp_dependence=True),
            BondColumn(header='НКД',
                       header_tooltip='Значение НКД (накопленного купонного дохода) на дату.',
                       data_function=lambda bond_class: bond_class.bond.aci_value,
                       display_function=lambda bond_class: MyMoneyValue.__str__(bond_class.bond.aci_value),
                       sort_role=Qt.ItemDataRole.UserRole,
                       lessThan=lambda left, right, role: MyMoneyValue.__lt__(left.data(role=role), right.data(role=role))),
            BondColumn(header='Номинал',
                       header_tooltip='Номинал облигации.',
                       data_function=lambda bond_class: bond_class.bond.nominal,
                       display_function=lambda bond_class: MyMoneyValue.__str__(bond_class.bond.nominal, 2),
                       sort_role=Qt.ItemDataRole.UserRole,
                       lessThan=lambda left, right, role: MyMoneyValue.__lt__(left.data(role=role), right.data(role=role))),
            BondColumn(header='Шаг цены',
                       header_tooltip='Минимальное изменение цены определённого инструмента.',
                       data_function=lambda bond_class: bond_class.bond.min_price_increment,
                       display_function=lambda bond_class: MyQuotation.__str__(bond_class.bond.min_price_increment, ndigits=9, delete_decimal_zeros=True),
                       sort_role=Qt.ItemDataRole.UserRole,
                       lessThan=lambda left, right, role: left.data(role=role) < right.data(role=role)),
            BondColumn(header='Амортизация',
                       header_tooltip='Признак облигации с амортизацией долга.',
                       data_function=lambda bond_class: bond_class.bond.amortization_flag,
                       display_function=lambda bond_class: "Да" if bond_class.bond.amortization_flag else "Нет"),
            BondColumn(header='До погашения',
                       header_tooltip='Количество дней до погашения облигации.',
                       data_function=lambda bond_class: MyBond.getDaysToMaturityCount(bond_class.bond),
                       display_function=lambda bond_class: 'Нет данных' if ifDateTimeIsEmpty(bond_class.bond.maturity_date) else '{0} дней'.format(MyBond.getDaysToMaturityCount(bond_class.bond)),
                       sort_role=Qt.ItemDataRole.UserRole,
                       lessThan=lambda left, right, role: left.data(role=role) < right.data(role=role)),
            BondColumn(header='Дата погашения',
                       header_tooltip='Дата погашения облигации в часовом поясе UTC.',
                       data_function=lambda bond_class: bond_class.bond.maturity_date,
                       display_function=lambda bond_class: reportSignificantInfoFromDateTime(bond_class.bond.maturity_date),
                       tooltip_function=lambda bond_class: str(bond_class.bond.maturity_date),
                       sort_role=Qt.ItemDataRole.UserRole,
                       lessThan=lambda left, right, role: left.data(role=role) < right.data(role=role)),
            BondColumn(header='Валюта',
                       header_tooltip='Валюта расчётов.',
                       data_function=lambda bond_class: bond_class.bond.currency),
            BondColumn(header='Страна риска',
                       header_tooltip='Наименование страны риска, т.е. страны, в которой компания ведёт основной бизнес.',
                       data_function=lambda bond_class: bond_class.bond.country_of_risk_name),
            BondColumn(header='Риск',
                       header_tooltip='Уровень риска.',
                       data_function=lambda bond_class: bond_class.bond.risk_level,
                       display_function=lambda bond_class: reportRiskLevel(bond_class.bond.risk_level),
                       sort_role=Qt.ItemDataRole.UserRole,
                       lessThan=lessThan_RiskLevel),
            BondColumn(header='Купонная дох-ть',
                       header_tooltip='Купонная доходность к выбранной дате.',
                       data_function=lambda bond_class, entered_dt: bond_class.getCouponAbsoluteProfit(entered_dt),
                       display_function=lambda bond_class, entered_dt: None if bond_class.coupons is None else str(bond_class.getCouponAbsoluteProfit(entered_dt)),
                       tooltip_function=reportCouponAbsoluteProfitCalculation,
                       date_dependence=True,
                       coupon_dependence=True,
                       sort_role=Qt.ItemDataRole.UserRole,
                       lessThan=lessThan_MyMoneyValue_or_None),
            BondColumn(header='Абсолют. дох-ть',
                       header_tooltip='Абсолютная доходность к выбранной дате.',
                       data_function=lambda bond_class, entered_dt: bond_class.getAbsoluteProfit(entered_dt),
                       display_function=lambda bond_class, entered_dt: QVariant() if bond_class.coupons is None else QVariant(str(bond_class.getAbsoluteProfit(entered_dt))),
                       tooltip_function=reportAbsoluteProfitCalculation,
                       date_dependence=True,
                       coupon_dependence=True,
                       lp_dependence=True,
                       sort_role=Qt.ItemDataRole.UserRole,
                       lessThan=lessThan_MyMoneyValue_or_None),
            BondColumn(header='Отн-ая дох-ть',
                       header_tooltip='Относительная доходность к выбранной дате.',
                       data_function=lambda bond_class, entered_dt: bond_class.getRelativeProfit(entered_dt),
                       display_function=showRelativeProfit,
                       date_dependence=True,
                       coupon_dependence=True,
                       lp_dependence=True,
                       sort_role=Qt.ItemDataRole.UserRole,
                       lessThan=lessThan_Decimal_or_None),
            BondColumn(header='Годовая дох-ть',
                       header_tooltip='Относительная доходность к выбранной дате в пересчёте на год.',
                       data_function=lambda bond_class, entered_dt: getAnnualProfit(bond_class, entered_dt),
                       display_function=showAnnualProfit,
                       date_dependence=True,
                       coupon_dependence=True,
                       lp_dependence=True,
                       sort_role=Qt.ItemDataRole.UserRole,
                       lessThan=lessThan_Decimal_or_None),
            BondColumn(header='Режим торгов',
                       header_tooltip='Текущий режим торгов инструмента.',
                       data_function=lambda bond_class: bond_class.bond.trading_status,
                       display_function=lambda bond_class: reportTradingStatus(bond_class.bond.trading_status))
        )
        self.__rows: list[BondsModel.BondRow] = []

        '''------------------Параметры запроса к БД------------------'''
        self.__token: TokenClass | None = None
        self.__instrument_status: InstrumentStatus = instrument_status
        self.__sql_condition: str | None = sql_condition
        self.__calculation_dt: datetime = calculation_dt  # Дата расчёта.
        '''----------------------------------------------------------'''

        '''-------Статистические параметры-------'''
        self.bond_notifications_count: int = 0
        self.lp_notifications_count: int = 0
        self.coupons_notifications_count: int = 0

        self.bond_notifications_seconds: float = 0.0
        self.lp_notifications_seconds: float = 0.0
        self.coupons_notifications_seconds: float = 0.0
        '''--------------------------------------'''

        self.update(token, instrument_status, sql_condition)  # Обновляем данные модели.

        '''------------------------Подписываемся на уведомления от бд------------------------'''
        def notificationSlot(name: str, source: QtSql.QSqlDriver.NotificationSource, payload: int):
            assert source == QtSql.QSqlDriver.NotificationSource.UnknownSource
            # print('notificationSlot: name = {0}, payload = {1}.'.format(name, payload))
            if self.__token is None:
                if name == MyConnection.BONDS_TABLE:
                    self.bond_notifications_count += 1
                elif name == MyConnection.COUPONS_TABLE:
                    self.coupons_notifications_count += 1
                elif name == MyConnection.LAST_PRICES_TABLE:
                    self.lp_notifications_count += 1
                else:
                    pass
                    # raise ValueError('Неверный параметр name ({0})!'.format(name))
            else:
                if name == MyConnection.BONDS_TABLE:
                    self.bond_notifications_count += 1
                    begin_datetime: datetime = getUtcDateTime()
                    print('notificationSlot: name = {0} ({2}), payload = {1}.'.format(name, payload, self.bond_notifications_count))
                    self.updateBondRow(payload)
                    self.bond_notifications_seconds += (getUtcDateTime() - begin_datetime).total_seconds()
                elif name == MyConnection.COUPONS_TABLE:
                    self.coupons_notifications_count += 1
                    begin_datetime: datetime = getUtcDateTime()
                    print('notificationSlot: name = {0} ({2}), payload = {1}.'.format(name, payload, self.coupons_notifications_count))
                    self.updateCouponsRow(payload)
                    self.coupons_notifications_seconds += (getUtcDateTime() - begin_datetime).total_seconds()
                elif name == MyConnection.LAST_PRICES_TABLE:
                    self.lp_notifications_count += 1
                    begin_datetime: datetime = getUtcDateTime()
                    print('notificationSlot: name = {0} ({2}), payload = {1}.'.format(name, payload, self.lp_notifications_count))
                    self.updateLastPricesRow_new(payload)
                    self.lp_notifications_seconds += (getUtcDateTime() - begin_datetime).total_seconds()
                else:
                    pass
                    # raise ValueError('Неверный параметр name ({0})!'.format(name))

        db: QtSql.QSqlDatabase = MainConnection.getDatabase()
        driver = db.driver()
        driver.notification.connect(notificationSlot)

        subscribe_flag: bool = driver.subscribeToNotification(MyConnection.BONDS_TABLE)
        assert subscribe_flag, 'Не удалось подписаться на уведомления об изменении таблицы {0}!'.format(MyConnection.BONDS_TABLE)
        subscribe_coupons_flag: bool = driver.subscribeToNotification(MyConnection.COUPONS_TABLE)
        assert subscribe_coupons_flag, 'Не удалось подписаться на уведомления об изменении таблицы {0}!'.format(MyConnection.COUPONS_TABLE)
        subscribe_lp_flag: bool = driver.subscribeToNotification(MyConnection.LAST_PRICES_TABLE)
        assert subscribe_lp_flag, 'Не удалось подписаться на уведомления об изменении таблицы {0}!'.format(MyConnection.LAST_PRICES_TABLE)
        '''----------------------------------------------------------------------------------'''

    def getBondNotificationAverageTime(self) -> float:
        return self.bond_notifications_seconds / self.bond_notifications_count

    def getCouponsNotificationAverageTime(self) -> float:
        return self.coupons_notifications_seconds / self.coupons_notifications_count

    def getLpNotificationAverageTime(self) -> float:
        return self.lp_notifications_seconds / self.lp_notifications_count

    def update(self, token: TokenClass | None, instrument_status: InstrumentStatus, sql_condition: str | None):
        """Обновляет данные модели в соответствии с переданными параметрами запроса к БД."""
        self.beginResetModel()  # Начинаем операцию сброса модели.

        '''------------Параметры запроса к БД------------'''
        self.__token = token
        self.__instrument_status = instrument_status
        self.__sql_condition = sql_condition
        '''----------------------------------------------'''

        '''-------Статистические параметры-------'''
        self.bond_notifications_count = 0
        self.lp_notifications_count = 0
        self.coupons_notifications_count = 0

        self.bond_notifications_seconds = 0.0
        self.lp_notifications_seconds = 0.0
        self.coupons_notifications_seconds = 0.0
        '''--------------------------------------'''

        if token is None:
            self.__rows.clear()  # Очищаем список с удалением всех строк.
        else:
            self.__rows.clear()  # Очищаем список с удалением всех строк.

            '''---------------------------------------Создание запроса к БД---------------------------------------'''
            bonds_select: str = '''
            SELECT {0}.\"rowid\", {0}.\"figi\", {0}.\"ticker\", {0}.\"class_code\", {0}.\"isin\", {0}.\"lot\", 
            {0}.\"currency\", {0}.\"klong\", {0}.\"kshort\", {0}.\"dlong\", {0}.\"dshort\", {0}.\"dlong_min\", 
            {0}.\"dshort_min\", {0}.\"short_enabled_flag\", {0}.\"name\", {0}.\"exchange\", 
            {0}.\"coupon_quantity_per_year\", {0}.\"maturity_date\", {0}.\"nominal\", {0}.\"initial_nominal\", 
            {0}.\"state_reg_date\", {0}.\"placement_date\", {0}.\"placement_price\", {0}.\"aci_value\", 
            {0}.\"country_of_risk\", {0}.\"country_of_risk_name\", {0}.\"sector\", {0}.\"issue_kind\", 
            {0}.\"issue_size\", {0}.\"issue_size_plan\", {0}.\"trading_status\", {0}.\"otc_flag\", 
            {0}.\"buy_available_flag\", {0}.\"sell_available_flag\", {0}.\"floating_coupon_flag\", 
            {0}.\"perpetual_flag\", {0}.\"amortization_flag\", {0}.\"min_price_increment\", 
            {0}.\"api_trade_available_flag\", {0}.\"uid\", {0}.\"real_exchange\", {0}.\"position_uid\", 
            {0}.\"for_iis_flag\", {0}.\"for_qual_investor_flag\", {0}.\"weekend_flag\", {0}.\"blocked_tca_flag\", 
            {0}.\"subordinated_flag\", {0}.\"liquidity_flag\", {0}.\"first_1min_candle_date\", 
            {0}.\"first_1day_candle_date\", {0}.\"risk_level\", {0}.\"coupons\"
            FROM {1}, {0}
            WHERE {1}.\"token\" = :token AND {1}.\"status\" = :status AND {1}.\"uid\" = {0}.\"uid\"{2}'''.format(
                '\"{0}\"'.format(MyConnection.BONDS_TABLE),
                '\"{0}\"'.format(MyConnection.INSTRUMENT_STATUS_TABLE),
                '' if sql_condition is None else ' AND {0}'.format(sql_condition)
            )

            sql_command: str = '''
            SELECT {1}.\"rowid\", {1}.\"figi\", {1}.\"ticker\", {1}.\"class_code\", {1}.\"isin\", {1}.\"lot\", {1}.\"currency\", 
            {1}.\"klong\", {1}.\"kshort\", {1}.\"dlong\", {1}.\"dshort\", {1}.\"dlong_min\", {1}.\"dshort_min\", 
            {1}.\"short_enabled_flag\", {1}.\"name\", {1}.\"exchange\", {1}.\"coupon_quantity_per_year\", 
            {1}.\"maturity_date\", {1}.\"nominal\", {1}.\"initial_nominal\", {1}.\"state_reg_date\", 
            {1}.\"placement_date\", {1}.\"placement_price\", {1}.\"aci_value\", {1}.\"country_of_risk\", 
            {1}.\"country_of_risk_name\", {1}.\"sector\", {1}.\"issue_kind\", {1}.\"issue_size\", 
            {1}.\"issue_size_plan\", {1}.\"trading_status\", {1}.\"otc_flag\", {1}.\"buy_available_flag\", 
            {1}.\"sell_available_flag\", {1}.\"floating_coupon_flag\", {1}.\"perpetual_flag\", 
            {1}.\"amortization_flag\", {1}.\"min_price_increment\", {1}.\"api_trade_available_flag\", {1}.\"uid\", 
            {1}.\"real_exchange\", {1}.\"position_uid\", {1}.\"for_iis_flag\", {1}.\"for_qual_investor_flag\", 
            {1}.\"weekend_flag\", {1}.\"blocked_tca_flag\", {1}.\"subordinated_flag\", {1}.\"liquidity_flag\", 
            {1}.\"first_1min_candle_date\", {1}.\"first_1day_candle_date\", {1}.\"risk_level\", {1}.\"coupons\",
            {2}.\"figi\" AS \"lp_figi\", {2}.\"price\" AS \"lp_price\", {2}.\"time\" AS \"lp_time\", 
            {2}.\"instrument_uid\" AS \"lp_instrument_uid\"
            FROM ({0}) AS {1} INNER JOIN {2} ON {1}.\"uid\" = {2}.\"instrument_uid\" 
            ;'''.format(
                bonds_select,
                '\"B\"',
                '\"{0}\"'.format(MyConnection.LAST_PRICES_VIEW)
            )
            '''---------------------------------------------------------------------------------------------------'''

            db: QtSql.QSqlDatabase = MainConnection.getDatabase()
            transaction_flag: bool = db.transaction()  # Начинает транзакцию в базе данных.
            if transaction_flag:
                query = QtSql.QSqlQuery(db)
                prepare_flag: bool = query.prepare(sql_command)
                assert prepare_flag, query.lastError().text()
                query.bindValue(':token', token.token)
                query.bindValue(':status', instrument_status.name)
                exec_flag: bool = query.exec()
                assert exec_flag, query.lastError().text()

                '''------------------------Извлекаем список облигаций------------------------'''
                while query.next():
                    def getLastPrice() -> LastPrice:
                        """Создаёт и возвращает экземпляр класса LastPrice."""
                        figi: str = query.value('lp_figi')
                        price_str: str = query.value('lp_price')
                        time_str: str = query.value('lp_time')
                        instrument_uid: str = query.value('lp_instrument_uid')

                        try:
                            price: Quotation = MyConnection.convertTextToQuotation(price_str)
                        except AttributeError:
                            raise AttributeError('getLastPrice: figi = \'{0}\', price = \'{1}\', time = \'{2}\', instrument_uid = \'{3}\'.'.format(figi, price_str, time_str, instrument_uid))
                        try:
                            time: datetime = MyConnection.convertTextToDateTime(time_str)
                        except ValueError:
                            raise ValueError('getLastPrice: figi = \'{0}\', price = \'{1}\', time = \'{2}\', instrument_uid = \'{3}\'.'.format(figi, price_str, time_str, instrument_uid))
                        return LastPrice(figi=figi, price=price, time=time, instrument_uid=instrument_uid)

                    def getCoupons(bond_uid: str) -> list[Coupon] | None:
                        """Извлекает купоны из таблицы купонов."""
                        coupons_value: str = query.value('coupons')
                        if coupons_value:
                            if coupons_value == 'Yes':
                                '''------------------Извлекаем купоны из таблицы купонов------------------'''
                                coupons_sql_command: str = '''SELECT \"figi\", \"coupon_date\", \"coupon_number\", 
                                \"fix_date\", \"pay_one_bond\", \"coupon_type\", \"coupon_start_date\", 
                                \"coupon_end_date\", \"coupon_period\" FROM {0} WHERE {0}.\"instrument_uid\" = :bond_uid
                                ;'''.format('\"{0}\"'.format(MyConnection.COUPONS_TABLE))
                                coupons_query = QtSql.QSqlQuery(db)
                                coupons_prepare_flag: bool = coupons_query.prepare(coupons_sql_command)
                                assert coupons_prepare_flag, coupons_query.lastError().text()
                                coupons_query.bindValue(':bond_uid', bond_uid)
                                coupons_exec_flag: bool = coupons_query.exec()
                                assert coupons_exec_flag, coupons_query.lastError().text()

                                '''-----------Извлекаем купоны из SQL-запроса-----------'''
                                coupons_list: list[Coupon] = []
                                while coupons_query.next():
                                    coupon: Coupon = self._getCurrentCoupon(coupons_query)
                                    coupons_list.append(coupon)

                                assert len(coupons_list) > 0, 'Столбец \"coupons\" в таблице {0} имеет значение \'Yes\' для uid = \'{2}\', но таблица {1} не содержит купонов с этим uid!'.format(
                                    '\"{0}\"'.format(MyConnection.BONDS_TABLE),
                                    '\"{0}\"'.format(MyConnection.COUPONS_TABLE),
                                    bond_uid
                                )
                                '''-----------------------------------------------------'''
                                '''-----------------------------------------------------------------------'''
                                return coupons_list
                            elif coupons_value == 'No':
                                return []
                            else:
                                raise ValueError('Некорректное значение столбца \"coupons\" в таблице \"{0}\"!'.format(MyConnection.BONDS_TABLE))
                        else:
                            return None

                    bond: Bond = MyConnection.getCurrentBond(query)
                    last_price: LastPrice = getLastPrice()
                    bond_class: MyBondClass = MyBondClass(bond, last_price, getCoupons(bond_uid=bond.uid))
                    rowid: int = query.value('rowid')
                    self.__rows.append(BondsModel.BondRow(rowid=rowid, bond_class=bond_class))
                '''--------------------------------------------------------------------------'''

                commit_flag: bool = db.commit()  # Фиксирует транзакцию в базу данных.
                assert commit_flag, db.lastError().text()
            else:
                assert transaction_flag, db.lastError().text()

        '''---------------------Подключение слотов обновления к сигналам облигаций---------------------'''
        columns_count: int = len(self.columns)
        if columns_count > 0:
            for row, bond_row in enumerate(self.__rows):
                first_row_index: QModelIndex = self.index(row, 0)
                last_row_index: QModelIndex = self.index(row, (columns_count - 1))
                bond_changed_connection: QtCore.QMetaObject.Connection = \
                    bond_row.bond_class.bondChanged_signal.connect(lambda: self.dataChanged.emit(first_row_index, last_row_index))  # Подключаем слот обновления.
                bond_row.appendBondChangedConnection(bond_changed_connection)

                for column, bond_column in enumerate(self.columns):
                    if bond_column.dependsOnCoupons():
                        source_index: QModelIndex = self.index(row, column)
                        coupons_changed_connection: QtCore.QMetaObject.Connection = \
                            bond_row.bond_class.couponsChanged_signal.connect(lambda: self.dataChanged.emit(source_index, source_index))  # Подключаем слот обновления.
                        bond_row.appendCouponsChangedConnection(coupons_changed_connection)
                    if bond_column.dependsOnLastPrice():
                        source_index: QModelIndex = self.index(row, column)
                        last_price_changed_connection: QtCore.QMetaObject.Connection = \
                            bond_row.bond_class.lastPriceChanged_signal.connect(lambda: self.dataChanged.emit(source_index, source_index))  # Подключаем слот обновления.
                        bond_row.appendLastPriceChangedConnection(last_price_changed_connection)
        '''--------------------------------------------------------------------------------------------'''
        self.endResetModel()  # Завершаем операцию сброса модели.

    def __findRowIndexWithBondRowid(self, rowid: int) -> int | None:
        """Находит и возвращает индекс строки с переданным rowid.
        Если строки с таким rowid нет в списке строк модели, то возвращает None."""
        found_rowid_indexes: list[int] = [i for i, row in enumerate(self.__rows) if row.rowid == rowid]
        found_rowid_indexes_count: int = len(found_rowid_indexes)  # Количество найденных строк.
        if found_rowid_indexes_count == 0:
            return None
        elif found_rowid_indexes_count == 1:
            return found_rowid_indexes[0]
        else:
            raise SystemError('Модель облигаций содержит несколько одинаковых rowid ({0})!'.format(rowid))

    def __findRowIndexWithBondUid(self, uid: str) -> int | None:
        """Находит и возвращает индекс строки с переданным uid облигации.
        Если строки с таким uid облигации нет в списке строк модели, то возвращает None."""
        found_bonds_indexes: list[int] = [i for i, row in enumerate(self.__rows) if row.bond.uid == uid]
        found_bonds_indexes_count: int = len(found_bonds_indexes)  # Количество найденных облигаций.
        if found_bonds_indexes_count == 0:
            return None
        elif found_bonds_indexes_count == 1:
            return found_bonds_indexes[0]
        else:
            raise SystemError('Модель облигаций содержит несколько облигаций с одинаковым uid (\'{0}\')!'.format(uid))

    def updateBondRow(self, rowid: int):
        """Обновляет все необходимые данные при изменении строки таблицы облигаций."""
        rowid_select: str = '''SELECT {0}.\"uid\" FROM {0} WHERE {0}.\"rowid\" = :rowid;'''.format(
            '\"{0}\"'.format(MyConnection.BONDS_TABLE)
        )

        db: QtSql.QSqlDatabase = MainConnection.getDatabase()
        transaction_flag: bool = db.transaction()  # Начинает транзакцию в базе данных.
        if transaction_flag:
            '''-----------Пробуем получить облигацию по rowid-----------'''
            rowid_query = QtSql.QSqlQuery(db)
            rowid_prepare_flag: bool = rowid_query.prepare(rowid_select)
            assert rowid_prepare_flag, rowid_query.lastError().text()
            rowid_query.bindValue(':rowid', rowid)
            rowid_exec_flag: bool = rowid_query.exec()
            assert rowid_exec_flag, rowid_query.lastError().text()
            '''---------------------------------------------------------'''

            '''-----------Извлекаем облигацию из query-----------'''
            rows_count: int = 0
            changed_rowid_uid: str
            while rowid_query.next():
                rows_count += 1
                assert rows_count < 2, 'Не должно быть нескольких строк с одним и тем же rowid ({0})!'.format(rowid)
                changed_rowid_uid = rowid_query.value('uid')
            '''--------------------------------------------------'''

            if rows_count == 0:
                """Если строки rowid не было найдено в бд, то она была удалена."""
                row_index: int | None = self.__findRowIndexWithBondRowid(rowid)
                if row_index is not None:
                    self.beginRemoveRows(QModelIndex(), row_index, row_index)
                    deleted_row: BondsModel.BondRow = self.__rows.pop(row_index)
                    deleted_row.disconnectAllConnections()  # Отключаем и удаляем все соединения.
                    self.endRemoveRows()
                    print('Облигация \'{0}\' удалена из модели облигаций. Время: {1:.2f}c.'.format(deleted_row.bond.uid, self.getBondNotificationAverageTime()))
            else:
                """Если облигация была получена."""
                '''----------------Проверяем облигацию на статус и фильтры----------------'''
                status_uid_select: str = '''SELECT \"uid\" FROM \"{0}\" WHERE \"{0}\".\"token\" = :token AND 
                \"{0}\".\"status\" = :status'''.format(MyConnection.INSTRUMENT_STATUS_TABLE)

                filter_bond_uid_select: str = '''SELECT {0}.\"rowid\", {0}.\"figi\", {0}.\"ticker\", {0}.\"class_code\", 
                {0}.\"isin\", {0}.\"lot\", {0}.\"currency\", {0}.\"klong\", {0}.\"kshort\", {0}.\"dlong\", 
                {0}.\"dshort\", {0}.\"dlong_min\", {0}.\"dshort_min\", {0}.\"short_enabled_flag\", {0}.\"name\", 
                {0}.\"exchange\", {0}.\"coupon_quantity_per_year\", {0}.\"maturity_date\", {0}.\"nominal\", 
                {0}.\"initial_nominal\", {0}.\"state_reg_date\", {0}.\"placement_date\", {0}.\"placement_price\", 
                {0}.\"aci_value\", {0}.\"country_of_risk\", {0}.\"country_of_risk_name\", {0}.\"sector\", 
                {0}.\"issue_kind\", {0}.\"issue_size\", {0}.\"issue_size_plan\", {0}.\"trading_status\", 
                {0}.\"otc_flag\", {0}.\"buy_available_flag\", {0}.\"sell_available_flag\", {0}.\"floating_coupon_flag\", 
                {0}.\"perpetual_flag\", {0}.\"amortization_flag\", {0}.\"min_price_increment\", 
                {0}.\"api_trade_available_flag\", {0}.\"uid\", {0}.\"real_exchange\", {0}.\"position_uid\", 
                {0}.\"for_iis_flag\", {0}.\"for_qual_investor_flag\", {0}.\"weekend_flag\", {0}.\"blocked_tca_flag\", 
                {0}.\"subordinated_flag\", {0}.\"liquidity_flag\", {0}.\"first_1min_candle_date\", 
                {0}.\"first_1day_candle_date\", {0}.\"risk_level\", {0}.\"coupons\" 
                FROM {0} WHERE {0}.\"uid\" = :bond_uid{1}'''.format(
                    '\"{0}\"'.format(MyConnection.BONDS_TABLE),
                    '' if self.__sql_condition is None else ' AND {0}'.format(self.__sql_condition)
                )

                filter_query_sql_command: str = '''SELECT {0}.\"rowid\", {0}.\"figi\", {0}.\"ticker\", 
                {0}.\"class_code\", {0}.\"isin\", {0}.\"lot\", {0}.\"currency\", {0}.\"klong\", {0}.\"kshort\", 
                {0}.\"dlong\", {0}.\"dshort\", {0}.\"dlong_min\", {0}.\"dshort_min\", {0}.\"short_enabled_flag\", 
                {0}.\"name\", {0}.\"exchange\", {0}.\"coupon_quantity_per_year\", {0}.\"maturity_date\", 
                {0}.\"nominal\", {0}.\"initial_nominal\", {0}.\"state_reg_date\", {0}.\"placement_date\", 
                {0}.\"placement_price\", {0}.\"aci_value\", {0}.\"country_of_risk\", {0}.\"country_of_risk_name\", 
                {0}.\"sector\", {0}.\"issue_kind\", {0}.\"issue_size\", {0}.\"issue_size_plan\", {0}.\"trading_status\", 
                {0}.\"otc_flag\", {0}.\"buy_available_flag\", {0}.\"sell_available_flag\", {0}.\"floating_coupon_flag\", 
                {0}.\"perpetual_flag\", {0}.\"amortization_flag\", {0}.\"min_price_increment\", 
                {0}.\"api_trade_available_flag\", {0}.\"uid\", {0}.\"real_exchange\", {0}.\"position_uid\", 
                {0}.\"for_iis_flag\", {0}.\"for_qual_investor_flag\", {0}.\"weekend_flag\", {0}.\"blocked_tca_flag\", 
                {0}.\"subordinated_flag\", {0}.\"liquidity_flag\", {0}.\"first_1min_candle_date\", 
                {0}.\"first_1day_candle_date\", {0}.\"risk_level\", {0}.\"coupons\" 
                FROM ({1}) AS {0} WHERE {0}.\"uid\" IN ({2});'''.format(
                    '\"B\"',
                    filter_bond_uid_select,
                    status_uid_select
                )

                filter_query = QtSql.QSqlQuery(db)
                filter_prepare_flag: bool = filter_query.prepare(filter_query_sql_command)
                assert filter_prepare_flag, filter_query.lastError().text()
                filter_query.bindValue(':bond_uid', changed_rowid_uid)
                filter_query.bindValue(':token', self.__token.token)
                filter_query.bindValue(':status', self.__instrument_status.name)
                filter_exec_flag: bool = filter_query.exec()
                assert filter_exec_flag, filter_query.lastError().text()
                '''-----------------------------------------------------------------------'''

                '''-----------Извлекаем облигацию из query-----------'''
                coupons_flag: bool
                rows_count: int = 0
                while filter_query.next():
                    rows_count += 1
                    assert rows_count < 2, 'Не должно быть нескольких строк с одним и тем же uid ({0})!'.format(changed_rowid_uid)
                    new_filtered_bond: Bond = MyConnection.getCurrentBond(query=filter_query)
                    coupons_flag = MyConnection.convertCouponsFlagToBool(filter_query.value('coupons'))
                    new_filtered_bond_rowid: int = filter_query.value('rowid')
                '''--------------------------------------------------'''

                row_index: int | None = self.__findRowIndexWithBondUid(changed_rowid_uid)
                if rows_count == 0:
                    """Если ни одной облигации не получено, то облигация не соответствует параметрам запроса."""
                    if row_index is not None:
                        self.beginRemoveRows(QModelIndex(), row_index, row_index)
                        deleted_row: BondsModel.BondRow = self.__rows.pop(row_index)
                        deleted_row.disconnectAllConnections()  # Отключаем и удаляем все соединения.
                        self.endRemoveRows()

                        if deleted_row is not None:
                            print('Облигация \'{0}\' обновилась и больше не соответствует фильтрам. Облигация удалена из модели облигаций. Время: {1:.2f}c.'.format(deleted_row.bond.uid, self.getBondNotificationAverageTime()))
                else:
                    """Если облигация была получена, то она должна присутствовать в модели."""
                    if row_index is None:
                        """Если облигации с таким uid нет в модели, то добавляем её."""
                        '''---------------------------Получаем последнюю цену---------------------------'''
                        last_price_sql_command: str = '''SELECT {0}.\"figi\", {0}.\"price\", {0}.\"time\", 
                        {0}.\"instrument_uid\" FROM {0} WHERE {0}.\"instrument_uid\" = :bond_uid;
                        '''.format('\"{0}\"'.format(MyConnection.LAST_PRICES_VIEW))

                        last_price_query = QtSql.QSqlQuery(db)
                        last_price_prepare_flag: bool = last_price_query.prepare(last_price_sql_command)
                        assert last_price_prepare_flag, last_price_query.lastError().text()
                        last_price_query.bindValue(':bond_uid', changed_rowid_uid)
                        last_price_exec_flag: bool = last_price_query.exec()
                        assert last_price_exec_flag, last_price_query.lastError().text()

                        last_price_rows_count: int = 0
                        last_price: LastPrice | None = None
                        while last_price_query.next():
                            last_price_rows_count += 1
                            assert last_price_rows_count < 2, 'Не должно быть нескольких строк с одним и тем же instrument_uid (\'{0}\')!'.format(changed_rowid_uid)
                            last_price = MyConnection.getCurrentLastPrice(last_price_query)
                        '''-----------------------------------------------------------------------------'''

                        '''--------------------------Получаем купоны облигации--------------------------'''
                        if coupons_flag:
                            coupons_sql_command: str = '''SELECT {0}.\"figi\", {0}.\"coupon_date\", 
                            {0}.\"coupon_number\", {0}.\"fix_date\", {0}.\"pay_one_bond\", {0}.\"coupon_type\", 
                            {0}.\"coupon_start_date\", {0}.\"coupon_end_date\", {0}.\"coupon_period\" 
                            FROM {0} WHERE {0}.\"instrument_uid\" = :bond_uid;
                            '''.format('\"{0}\"'.format(MyConnection.COUPONS_TABLE))

                            coupons_query = QtSql.QSqlQuery(db)
                            coupons_prepare_flag: bool = coupons_query.prepare(coupons_sql_command)
                            assert coupons_prepare_flag, coupons_query.lastError().text()
                            coupons_query.bindValue(':bond_uid', changed_rowid_uid)
                            coupons_exec_flag: bool = coupons_query.exec()
                            assert coupons_exec_flag, coupons_query.lastError().text()

                            coupons: list[Coupon] = []
                            while coupons_query.next():
                                coupons.append(MyConnection.getCurrentCoupon(coupons_query))
                            assert len(coupons) > 0
                        else:
                            coupons: None = None
                        '''-----------------------------------------------------------------------------'''

                        inserting_bond_class: MyBondClass = MyBondClass(bond=new_filtered_bond,
                                                                        last_price=last_price,
                                                                        coupons=coupons)
                        inserting_row: BondsModel.BondRow = BondsModel.BondRow(rowid=new_filtered_bond_rowid,
                                                                               bond_class=inserting_bond_class)
                        first: int = len(self.__rows)
                        self.beginInsertRows(QModelIndex(), first, first)
                        self.__rows.append(inserting_row)
                        '''---------------------Подключение слотов обновления к сигналам облигации---------------------'''
                        columns_count: int = len(self.columns)
                        if columns_count > 0:
                            first_row_index: QModelIndex = self.index(first, 0)
                            last_row_index: QModelIndex = self.index(first, (columns_count - 1))
                            bond_changed_connection: QtCore.QMetaObject.Connection = \
                                self.__rows[first].bond_class.bondChanged_signal.connect(lambda: self.dataChanged.emit(first_row_index, last_row_index))  # Подключаем слот обновления.
                            self.__rows[first].appendBondChangedConnection(bond_changed_connection)
                            for column, bond_column in enumerate(self.columns):
                                if bond_column.dependsOnCoupons():
                                    source_index: QModelIndex = self.index(first, column)
                                    coupons_changed_connection: QtCore.QMetaObject.Connection = \
                                        self.__rows[first].bond_class.couponsChanged_signal.connect(lambda: self.dataChanged.emit(source_index, source_index))  # Подключаем слот обновления.
                                    self.__rows[first].appendCouponsChangedConnection(coupons_changed_connection)
                                if bond_column.dependsOnLastPrice():
                                    source_index: QModelIndex = self.index(first, column)
                                    last_price_changed_connection: QtCore.QMetaObject.Connection = \
                                        self.__rows[first].bond_class.lastPriceChanged_signal.connect(lambda: self.dataChanged.emit(source_index, source_index))  # Подключаем слот обновления.
                                    self.__rows[first].appendLastPriceChangedConnection(last_price_changed_connection)
                        '''--------------------------------------------------------------------------------------------'''
                        self.endInsertRows()
                        print('Добавлена облигация \'{0}\' в модель облигаций. Время: {1:.2f}c.'.format(new_filtered_bond.uid, self.getBondNotificationAverageTime()))
                    else:
                        """Если облигация с таким uid есть в модели, то её следует обновить."""
                        self.__rows[row_index].bond_class.updateBond(new_filtered_bond)
                        print('Облигация \'{0}\' в модели облигаций обновлена. Время: {1:.2f}c.'.format(changed_rowid_uid, self.getBondNotificationAverageTime()))

            commit_flag: bool = db.commit()  # Фиксирует транзакцию в базу данных.
            assert commit_flag, db.lastError().text()
        else:
            assert transaction_flag, db.lastError().text()

    def updateCouponsRow(self, rowid: int):
        """Обновляет все необходимые данные при изменении строки таблицы купонов."""
        rowid_select_str: str = '''SELECT {0}.\"instrument_uid\", {0}.\"figi\", {0}.\"coupon_date\", 
        {0}.\"coupon_number\", {0}.\"fix_date\", {0}.\"pay_one_bond\", {0}.\"coupon_type\", {0}.\"coupon_start_date\", 
        {0}.\"coupon_end_date\", {0}.\"coupon_period\" 
        FROM {0} WHERE {0}.\"rowid\" = :rowid;'''.format('\"{0}\"'.format(MyConnection.COUPONS_TABLE))

        db: QtSql.QSqlDatabase = MainConnection.getDatabase()
        transaction_flag: bool = db.transaction()  # Начинает транзакцию в базе данных.
        if transaction_flag:
            '''-----------Пробуем получить купон по rowid-----------'''
            rowid_query = QtSql.QSqlQuery(db)
            rowid_prepare_flag: bool = rowid_query.prepare(rowid_select_str)
            assert rowid_prepare_flag, rowid_query.lastError().text()
            rowid_query.bindValue(':rowid', rowid)
            rowid_exec_flag: bool = rowid_query.exec()
            assert rowid_exec_flag, rowid_query.lastError().text()
            '''-----------------------------------------------------'''

            '''-----------------Извлекаем купон из query-----------------'''
            rows_count: int = 0
            while rowid_query.next():
                rows_count += 1
                if rows_count > 1:
                    raise SystemError('Не должно быть нескольких строк с одним и тем же rowid ({0})!'.format(rowid))
                coupon: Coupon = self._getCurrentCoupon(rowid_query)
                coupon_instrument_uid: str = rowid_query.value('instrument_uid')
            '''----------------------------------------------------------'''

            commit_flag: bool = db.commit()  # Фиксирует транзакцию в базу данных.
            assert commit_flag, db.lastError().text()

            bond_index: int | None = self.__findRowIndexWithBondUid(coupon_instrument_uid)
            if bond_index is None:
                """Купон не имеет отношения к облигациям в модели облигаций."""
                pass  # Ничего не делаем.
            else:
                if rows_count == 0:
                    """Если купон не был получен, то он был удалён."""
                    self.__rows[bond_index].bond_class.removeCoupons(coupon.coupon_number)
                else:
                    """Если купон был получен."""
                    self.__rows[bond_index].bond_class.upsertCoupon(coupon)  # Обновляем список купонов облигации.
        else:
            assert transaction_flag, db.lastError().text()

    def updateLastPricesRow_old(self, rowid: int):
        """Обновляет все необходимые данные при изменении строки таблицы последних цен."""
        view_select_str: str = '''SELECT {0}.\"figi\", {0}.\"price\", {0}.\"time\", {0}.\"instrument_uid\" 
        FROM {0} WHERE {0}.\"lp_rowid\" = :rowid;'''.format('\"{0}\"'.format(MyConnection.LAST_PRICES_VIEW))

        db: QtSql.QSqlDatabase = MainConnection.getDatabase()
        transaction_flag: bool = db.transaction()  # Начинает транзакцию в базе данных.
        if transaction_flag:
            """==================Пробуем получить последнюю цену из представления последних цен=================="""
            view_query = QtSql.QSqlQuery(db)
            view_prepare_flag: bool = view_query.prepare(view_select_str)
            assert view_prepare_flag, view_query.lastError().text()
            view_query.bindValue(':rowid', rowid)
            view_exec_flag: bool = view_query.exec()
            assert view_exec_flag, view_query.lastError().text()

            '''----------Извлекаем последнюю цену из query----------'''
            view_rows_count: int = 0
            while view_query.next():
                view_rows_count += 1
                if view_rows_count > 1:
                    raise SystemError('Не должно быть нескольких строк с одним и тем же rowid ({0})!'.format(rowid))
                last_price: LastPrice = MyConnection.getCurrentLastPrice(view_query)
            '''-----------------------------------------------------'''
            """=================================================================================================="""

            if view_rows_count == 0:
                """Если представление не содержит последнюю цену, то:
                    если произошёл INSERT, то ничего делать не надо;
                    если произошёл UPDATE, то последняя цена не могла стать неактуальной, так как поле time является 
                частью составного первичного ключа и не могло измениться в меньшую сторону, - значит, что если 
                действительно произошёл UPDATE и последней цены нет в представлении, то её там и не было, следовательно, 
                ничего делать не надо;
                    если произошёл DELETE, то, по хорошему, надо проверить таблицу последних цен, чтобы узнать, надо ли 
                удалить из модели удалённую цену. Но, так как в моём коде не предусмотрено удаление последних цен иначе 
                как вместе с инструментом, то пока можно пропустить эту операцию."""

                # rowid_select_str: str = '''SELECT {0}.\"figi\", {0}.\"price\", {0}.\"time\", {0}.\"instrument_uid\"
                # FROM {0} WHERE {0}.\"rowid\" = :rowid;'''.format('\"{0}\"'.format(MyConnection.LAST_PRICES_TABLE))
                #
                # '''-------Пробуем получить последнюю цену по rowid-------'''
                # rowid_query = QtSql.QSqlQuery(db)
                # rowid_prepare_flag: bool = rowid_query.prepare(rowid_select_str)
                # assert rowid_prepare_flag, rowid_query.lastError().text()
                # rowid_query.bindValue(':rowid', rowid)
                # rowid_exec_flag: bool = rowid_query.exec()
                # assert rowid_exec_flag, rowid_query.lastError().text()
                # '''------------------------------------------------------'''
                #
                # '''----------Извлекаем последнюю цену из query----------'''
                # rows_count: int = 0
                # while rowid_query.next():
                #     rows_count += 1
                #     if rows_count > 1:
                #         raise SystemError('Не должно быть нескольких строк с одним и тем же rowid ({0})!'.format(rowid))
                #     last_price: LastPrice = MyConnection.getCurrentLastPrice(rowid_query)
                # '''-----------------------------------------------------'''

                pass
                print('LastPrices notification: view_rows_count == 0 для rowid = {0}. Время: {1:.2f}c.'.format(rowid, self.getLpNotificationAverageTime()))
            else:
                """Если представление содержит последнюю цену, то последняя цена актуальна."""
                bond_index: int | None = self.__findRowIndexWithBondUid(last_price.instrument_uid)
                if bond_index is None:
                    """Последняя цена не имеет отношения к облигациям в модели облигаций."""
                    pass  # Ничего не делаем.
                    print('LastPrices notification: Последняя цена не имеет отношения к облигациям в модели облигаций. Время: {0:.2f}c.'.format(self.getLpNotificationAverageTime()))
                else:
                    self.__rows[bond_index].bond_class.setLastPrice(last_price)
                    print('LastPrices notification: добавлена новая последняя цена (instrument_uid = \'{0}\'). Время: {1:.2f}c.'.format(last_price.instrument_uid, self.getLpNotificationAverageTime()))

            commit_flag: bool = db.commit()  # Фиксирует транзакцию в базу данных.
            assert commit_flag, db.lastError().text()
        else:
            assert transaction_flag, db.lastError().text()

    def updateLastPricesRow_new(self, rowid: int):
        """Обновляет все необходимые данные при изменении строки таблицы последних цен."""
        lp_select_str: str = '''SELECT {0}.\"figi\", {0}.\"price\", {0}.\"time\", {0}.\"instrument_uid\" 
        FROM {0} WHERE {0}.\"rowid\" = :rowid;'''.format('\"{0}\"'.format(MyConnection.LAST_PRICES_TABLE))

        db: QtSql.QSqlDatabase = MainConnection.getDatabase()
        transaction_flag: bool = db.transaction()  # Начинает транзакцию в базе данных.
        if transaction_flag:
            lp_select_query = QtSql.QSqlQuery(db)
            lp_select_prepare_flag: bool = lp_select_query.prepare(lp_select_str)
            assert lp_select_prepare_flag, lp_select_query.lastError().text()
            lp_select_query.bindValue(':rowid', rowid)
            lp_select_exec_flag: bool = lp_select_query.exec()
            assert lp_select_exec_flag, lp_select_query.lastError().text()

            '''----------Извлекаем последнюю цену из query----------'''
            lp_count: int = 0
            while lp_select_query.next():
                lp_count += 1
                if lp_count > 1:
                    raise SystemError('Не должно быть нескольких строк с одним и тем же rowid ({0})!'.format(rowid))
                last_price: LastPrice = MyConnection.getCurrentLastPrice(lp_select_query)
            '''-----------------------------------------------------'''

            if lp_count == 0:
                """Если последняя цена была удалена."""
                raise SystemError('Пока не реализовано!')
                ...
            else:
                """Если последняя цена найдена."""
                bond_index: int | None = self.__findRowIndexWithBondUid(last_price.instrument_uid)
                if bond_index is None:
                    """Последняя цена не имеет отношения к облигациям в модели облигаций."""
                    pass  # Ничего не делаем.
                    print('LastPrices notification: Последняя цена не имеет отношения к облигациям в модели облигаций. Время: {0:.2f}c.'.format(self.getLpNotificationAverageTime()))
                else:
                    """===========Получаем актуальную цену для инструмента по полученному instrument_uid==========="""
                    view_select_str: str = '''SELECT {0}.\"figi\", {0}.\"price\", {0}.\"time\", {0}.\"instrument_uid\"
                    FROM {0} WHERE {0}.\"instrument_uid\" = :instrument_uid;'''.format('\"{0}\"'.format(MyConnection.LAST_PRICES_VIEW))

                    # view_select_str: str = '''SELECT {0}.\"figi\", {0}.\"price\", MAX({0}.\"time\") AS \"time\",
                    # {0}.\"instrument_uid\" FROM {0} WHERE {0}.\"instrument_uid\" = :instrument_uid
                    # GROUP BY {0}.\"instrument_uid\";'''.format('\"{0}\"'.format(MyConnection.LAST_PRICES_TABLE))

                    view_select_query = QtSql.QSqlQuery(db)
                    view_select_prepare_flag: bool = view_select_query.prepare(view_select_str)
                    assert view_select_prepare_flag, view_select_query.lastError().text()
                    view_select_query.bindValue(':instrument_uid', last_price.instrument_uid)
                    view_select_exec_flag: bool = view_select_query.exec()
                    assert view_select_exec_flag, view_select_query.lastError().text()

                    '''----------Извлекаем последнюю цену из query----------'''
                    view_count: int = 0
                    view_last_price: LastPrice
                    while view_select_query.next():
                        view_count += 1
                        if view_count > 1:
                            raise SystemError('Не должно быть нескольких строк с одним и тем же instrument_uid ({0})!'.format(last_price.instrument_uid))
                        view_last_price: LastPrice = MyConnection.getCurrentLastPrice(view_select_query)
                    '''-----------------------------------------------------'''
                    """============================================================================================"""

                    if view_count == 0:
                        raise SystemError('Если у инструмента есть хотя бы одна цена, то её не может не быть в представлении!.')
                    else:
                        self.__rows[bond_index].bond_class.setLastPrice(view_last_price)
                        print('LastPricesNotification: Актуальная цена обновлена. Время: {0:.2f}c.'.format(self.getLpNotificationAverageTime()))

            commit_flag: bool = db.commit()  # Фиксирует транзакцию в базу данных.
            assert commit_flag, db.lastError().text()
        else:
            assert transaction_flag, db.lastError().text()

    def setCalculationDateTime(self, calculation_dt: datetime):
        """Устанавливает новую дату расчёта."""
        def updateDependsOnCalculationDateTimeColumns():
            """Сообщает о необходимости обновить столбцы, значение которых зависит от даты расчёта."""
            last_row_number: int = self.rowCount() - 1
            if last_row_number >= 0:
                for i, column in enumerate(self.columns):
                    if column.dependsOnDateTime():
                        top_index: QModelIndex = self.index(0, i)
                        bottom_index: QModelIndex = self.index(last_row_number, i)
                        self.dataChanged.emit(top_index, bottom_index)

        self.__calculation_dt = calculation_dt
        updateDependsOnCalculationDateTimeColumns()  # Сообщаем о необходимости обновить столбцы.

    def rowCount(self, parent: QModelIndex = ...) -> int:
        """Возвращает количество облигаций в модели."""
        return len(self.__rows)

    def columnCount(self, parent: QModelIndex = ...) -> int:
        """Возвращает количество столбцов в модели."""
        return len(self.columns)

    def data(self, index: QModelIndex, role: int = ...) -> typing.Any:
        column: BondColumn = self.columns[index.column()]
        bond_class: MyBondClass = self.__rows[index.row()].bond_class
        return column(role, bond_class, self.__calculation_dt) if column.dependsOnDateTime() else column(role, bond_class)

    def getBond(self, row: int) -> MyBondClass | None:
        """Возвращает облигацию, соответствующую переданному номеру."""
        return self.__rows[row].bond_class if 0 <= row < len(self.__rows) else None


class BondsProxyModel(QSortFilterProxyModel):
    """Прокси-модель облигаций."""
    DEPENDS_ON_DATE_COLOR: QtGui.QBrush = QtGui.QBrush(Qt.GlobalColor.darkRed)  # Цвет фона заголовков, зависящих от даты расчёта.

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
        if orientation == Qt.Orientation.Vertical:
            if role == Qt.ItemDataRole.DisplayRole:
                return section + 1  # Проставляем номера строк.
        elif orientation == Qt.Orientation.Horizontal:
            if role == Qt.ItemDataRole.DisplayRole:
                return self.sourceModel().columns[section].header
            elif role == Qt.ItemDataRole.ToolTipRole:  # Подсказки.
                return self.sourceModel().columns[section].header_tooltip
            elif role == Qt.ItemDataRole.ForegroundRole:
                if self.sourceModel().columns[section].dependsOnDateTime():
                    return self.DEPENDS_ON_DATE_COLOR

    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:
        """Определяет критерий сравнения данных для сортировки."""
        left_column_number: int = left.column()  # Номер строки "левого" элемента.
        if left_column_number == right.column():
            column: BondColumn = self.sourceModel().columns[left_column_number]
            if column.lessThan is None: return super().lessThan(left, right)  # Сортировка по умолчанию.
            return column.lessThan(left, right, column.getSortRole)

    def getBond(self, proxy_index: QModelIndex) -> MyBondClass | None:
        """Возвращает облигацию по индексу элемента."""
        source_index: QModelIndex = self.mapToSource(proxy_index)
        return self.sourceModel().getBond(source_index.row())
