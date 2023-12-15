import typing
from datetime import datetime
from PyQt6.QtCore import QAbstractTableModel, QObject, QModelIndex, QSortFilterProxyModel, Qt, QVariant
from PyQt6.QtGui import QBrush
from PyQt6.QtSql import QSqlDatabase, QSqlQuery
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
    MATURITY_COLOR: QBrush = QBrush(Qt.GlobalColor.lightGray)  # Цвет фона строк погашенных облигаций.
    PERPETUAL_COLOR: QBrush = QBrush(Qt.GlobalColor.magenta)  # Цвет фона строк бессрочных облигаций.

    def __init__(self, header: str | None = None, header_tooltip: str | None = None, data_function=None, display_function=None, tooltip_function=None,
                 background_function=lambda bond_class, *args: BondColumn.PERPETUAL_COLOR if bond_class.bond.perpetual_flag and ifDateTimeIsEmpty(bond_class.bond.maturity_date) else BondColumn.MATURITY_COLOR if MyBond.ifBondIsMaturity(bond_class.bond) else QVariant(),
                 foreground_function=None, lessThan=None, sort_role: Qt.ItemDataRole = Qt.ItemDataRole.UserRole,
                 date_dependence: bool = False, entered_datetime: datetime | None = None, coupon_dependence: bool = False):
        super().__init__(header, header_tooltip, data_function, display_function, tooltip_function,
                         background_function, foreground_function, lessThan, sort_role)
        self._date_dependence: bool = date_dependence  # Флаг зависимости от даты.
        self._entered_datetime: datetime | None = entered_datetime  # Дата расчёта.
        self._coupon_dependence: bool = coupon_dependence  # Флаг зависимости от купонов.

    def dependsOnDateTime(self) -> bool:
        """Возвращает True, если значение столбца зависит от выбранной даты. Иначе возвращает False."""
        return self._date_dependence

    def dependsOnCoupons(self) -> bool:
        """Возвращает True, если значение столбца зависит от купонов. Иначе возвращает False."""
        return self._coupon_dependence


class BondsModel(QAbstractTableModel):
    """Модель облигаций."""
    def __init__(self, token: TokenClass | None, instrument_status: InstrumentStatus, sql_condition: str | None, calculation_dt: datetime, parent: QObject | None = None):
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
                       lessThan=lessThan_MyMoneyValue_or_None),
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
            BondColumn(header='Дней до погашения',
                       header_tooltip='Количество дней до погашения облигации.',
                       data_function=lambda bond_class: MyBond.getDaysToMaturityCount(bond_class.bond),
                       display_function=lambda bond_class: 'Нет данных' if ifDateTimeIsEmpty(bond_class.bond.maturity_date) else MyBond.getDaysToMaturityCount(bond_class.bond),
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
                       sort_role=Qt.ItemDataRole.UserRole,
                       lessThan=lessThan_MyMoneyValue_or_None),
            BondColumn(header='Отн-ая дох-ть',
                       header_tooltip='Относительная доходность к выбранной дате.',
                       data_function=lambda bond_class, entered_dt: bond_class.getRelativeProfit(entered_dt),
                       display_function=showRelativeProfit,
                       date_dependence=True,
                       coupon_dependence=True,
                       sort_role=Qt.ItemDataRole.UserRole,
                       lessThan=lessThan_Decimal_or_None),
            BondColumn(header='Годовая доходность',
                       header_tooltip='Относительная доходность к выбранной дате в пересчёте на год.',
                       data_function=lambda bond_class, entered_dt: getAnnualProfit(bond_class, entered_dt),
                       display_function=showAnnualProfit,
                       date_dependence=True,
                       coupon_dependence=True,
                       sort_role=Qt.ItemDataRole.UserRole,
                       lessThan=lessThan_Decimal_or_None),
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
        self.__calculation_dt: datetime = calculation_dt  # Дата расчёта.
        '''----------------------------------------------------------'''

        self.update(token, instrument_status, sql_condition)  # Обновляем данные модели.

    def update(self, token: TokenClass | None, instrument_status: InstrumentStatus, sql_condition: str | None):
        """Обновляет данные модели в соответствии с переданными параметрами запроса к БД."""
        self.beginResetModel()  # Начинаем операцию сброса модели.

        '''------------------Параметры запроса к БД------------------'''
        self.__token = token
        self.__instrument_status = instrument_status
        self.__sql_condition = sql_condition
        '''----------------------------------------------------------'''

        if token is None:
            self._bonds = []
        else:
            '''---------------------------Создание запроса к БД---------------------------'''
            bonds_select: str = '''
            SELECT {0}."figi", {0}."ticker", {0}."class_code", {0}."isin", {0}."lot", {0}."currency", {0}."klong", 
            {0}."kshort", {0}."dlong", {0}."dshort", {0}."dlong_min", {0}."dshort_min", {0}."short_enabled_flag", 
            {0}."name", {0}."exchange", {0}."coupon_quantity_per_year", {0}."maturity_date", {0}."nominal", 
            {0}."initial_nominal", {0}."state_reg_date", {0}."placement_date", {0}."placement_price", {0}."aci_value", 
            {0}."country_of_risk", {0}."country_of_risk_name", {0}."sector", {0}."issue_kind", {0}."issue_size", 
            {0}."issue_size_plan", {0}."trading_status", {0}."otc_flag", {0}."buy_available_flag", 
            {0}."sell_available_flag", {0}."floating_coupon_flag", {0}."perpetual_flag", {0}."amortization_flag", 
            {0}."min_price_increment", {0}."api_trade_available_flag", {0}."uid", {0}."real_exchange", 
            {0}."position_uid", {0}."for_iis_flag", {0}."for_qual_investor_flag", {0}."weekend_flag", 
            {0}."blocked_tca_flag", {0}."subordinated_flag", {0}."liquidity_flag", {0}."first_1min_candle_date", 
            {0}."first_1day_candle_date", {0}."risk_level"
            FROM "BondsStatus", {0}
            WHERE "BondsStatus"."token" = :token AND "BondsStatus"."status" = :status AND
            "BondsStatus"."uid" = {0}."uid"{1}'''.format(
                '\"{0}\"'.format(MyConnection.BONDS_TABLE),
                '' if sql_condition is None else ' AND {0}'.format(sql_condition)
            )

            sql_command: str = '''
            SELECT {1}."figi", {1}."ticker", {1}."class_code", {1}."isin", {1}."lot", {1}."currency", {1}."klong", 
            {1}."kshort", {1}."dlong", {1}."dshort", {1}."dlong_min", {1}."dshort_min", {1}."short_enabled_flag", 
            {1}."name", {1}."exchange", {1}."coupon_quantity_per_year", {1}."maturity_date", {1}."nominal", 
            {1}."initial_nominal", {1}."state_reg_date", {1}."placement_date", {1}."placement_price", {1}."aci_value", 
            {1}."country_of_risk", {1}."country_of_risk_name", {1}."sector", {1}."issue_kind", {1}."issue_size", 
            {1}."issue_size_plan", {1}."trading_status", {1}."otc_flag", {1}."buy_available_flag", 
            {1}."sell_available_flag", {1}."floating_coupon_flag", {1}."perpetual_flag", {1}."amortization_flag", 
            {1}."min_price_increment", {1}."api_trade_available_flag", {1}."uid", {1}."real_exchange", 
            {1}."position_uid", {1}."for_iis_flag", {1}."for_qual_investor_flag", {1}."weekend_flag", 
            {1}."blocked_tca_flag", {1}."subordinated_flag", {1}."liquidity_flag", {1}."first_1min_candle_date", 
            {1}."first_1day_candle_date", {1}."risk_level", 
            {2}."figi" AS "lp_figi", {2}."price" AS "lp_price", {2}."time" AS "lp_time", 
            {2}."instrument_uid" AS "lp_instrument_uid"
            FROM ({0}) AS {1} INNER JOIN {2} ON {1}."uid" = {2}."instrument_uid" 
            ;'''.format(
                bonds_select,
                '\"B\"',
                '\"{0}\"'.format(MyConnection.LAST_PRICES_VIEW)
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

                def getLastPrice() -> LastPrice | None:
                    """Создаёт и возвращает экземпляр класса LastPrice."""
                    figi: str = query.value('lp_figi')
                    price_str: str = query.value('lp_price')
                    time_str: str = query.value('lp_time')
                    instrument_uid: str = query.value('lp_instrument_uid')

                    if figi or price_str or time_str or instrument_uid:
                        assert figi == bond.figi, 'Figi-идентификатор LastPrice (\'{0}\') не совпадает с figi облигации (\'{1}\')!'.format(figi, bond.figi)
                        price: Quotation = MyConnection.convertTextToQuotation(price_str)
                        time: datetime = MyConnection.convertTextToDateTime(time_str)
                        return LastPrice(figi=figi, price=price, time=time, instrument_uid=instrument_uid)
                    else:  # Если last_price отсутствует.
                        return None

                def getCoupons(bond_figi: str) -> list[Coupon] | None:
                    def checkCoupons(figi: str) -> bool | None:
                        """Выполняет запрос к таблице BondsFinancialInstrumentGlobalIdentifiers и возвращает результат."""
                        check_coupons_sql_command: str = '''
                        SELECT {0}."coupons"
                        FROM {0}
                        WHERE {0}."figi" = :figi
                        ;'''.format(
                            '\"{0}\"'.format(MyConnection.BONDS_FIGI_TABLE),
                        )
                        check_coupons_query = QSqlQuery(db)
                        check_coupons_prepare_flag: bool = check_coupons_query.prepare(check_coupons_sql_command)
                        assert check_coupons_prepare_flag, check_coupons_query.lastError().text()

                        check_coupons_query.bindValue(':figi', figi)

                        check_coupons_exec_flag: bool = check_coupons_query.exec()
                        assert check_coupons_exec_flag, check_coupons_query.lastError().text()

                        '''------Здесь нужна проверка, что получено только одно значение------'''
                        # coupons_count: int = check_coupons_query.size()
                        # assert coupons_count == 1, 'Запрос к БД должен был вернуть одно значение, а вернул {0} для figi=\'{1}\'!'.format(coupons_count, bond_figi)
                        # u: int = 0
                        # while check_coupons_query.next():
                        #     u += 1
                        '''-------------------------------------------------------------------'''

                        next_flag: bool = check_coupons_query.next()
                        assert next_flag
                        coupons_value: str = check_coupons_query.value('coupons')

                        if coupons_value:
                            if coupons_value == 'Yes':
                                return True
                            elif coupons_value == 'No':
                                return False
                            else:
                                raise ValueError('Некорректное значение столбца \"currency\" в таблице {0}!'.format('\"{0}\"'.format(MyConnection.BONDS_FIGI_TABLE)))
                        else:
                            return None

                    value: bool | None = checkCoupons(bond_figi)
                    if value is None:
                        return None
                    elif value:
                        coupons_sql_command: str = '''
                        SELECT "figi", "coupon_date", "coupon_number", "fix_date", "pay_one_bond", "coupon_type", 
                        "coupon_start_date", "coupon_end_date", "coupon_period"
                        FROM {0}
                        WHERE {0}."figi" = :bond_figi
                        ;'''.format(
                            '\"{0}\"'.format(MyConnection.COUPONS_TABLE),
                        )
                        coupons_query = QSqlQuery(db)
                        coupons_prepare_flag: bool = coupons_query.prepare(coupons_sql_command)
                        assert coupons_prepare_flag, coupons_query.lastError().text()

                        coupons_query.bindValue(':bond_figi', bond_figi)

                        coupons_exec_flag: bool = coupons_query.exec()
                        assert coupons_exec_flag, coupons_query.lastError().text()

                        '''---------------------Извлекаем купоны из SQL-запроса---------------------'''
                        coupons_list: list[Coupon] = []
                        while coupons_query.next():
                            def getCoupon() -> Coupon:
                                figi: str = coupons_query.value('figi')
                                coupon_date: datetime = MyConnection.convertTextToDateTime(coupons_query.value('coupon_date'))
                                coupon_number: int = coupons_query.value('coupon_number')
                                fix_date: datetime = MyConnection.convertTextToDateTime(coupons_query.value('fix_date'))
                                pay_one_bond: MoneyValue = MyConnection.convertTextToMoneyValue(coupons_query.value('pay_one_bond'))
                                coupon_type: CouponType = CouponType(coupons_query.value('coupon_type'))
                                coupon_start_date: datetime = MyConnection.convertTextToDateTime(coupons_query.value('coupon_start_date'))
                                coupon_end_date: datetime = MyConnection.convertTextToDateTime(coupons_query.value('coupon_end_date'))
                                coupon_period: int = coupons_query.value('coupon_period')
                                return Coupon(figi=figi, coupon_date=coupon_date, coupon_number=coupon_number,
                                              fix_date=fix_date, pay_one_bond=pay_one_bond, coupon_type=coupon_type,
                                              coupon_start_date=coupon_start_date, coupon_end_date=coupon_end_date,
                                              coupon_period=coupon_period)

                            coupon: Coupon = getCoupon()
                            coupons_list.append(coupon)
                        '''-------------------------------------------------------------------------'''
                        assert len(coupons_list) > 0, 'Столбец \"currency\" в таблице {0} имеет значение \'Yes\' для figi = \'{2}\', но таблица {1} не содержит купонов с этим figi!'.format(
                            '\"{0}\"'.format(MyConnection.BONDS_FIGI_TABLE),
                            '\"{0}\"'.format(MyConnection.COUPONS_TABLE),
                            bond_figi
                        )
                        return coupons_list
                    else:
                        return []

                last_price: LastPrice | None = getLastPrice()
                coupons: list[Coupon] | None = getCoupons(bond.figi)
                bond_class: MyBondClass = MyBondClass(bond, last_price, coupons)
                self._bonds.append(bond_class)
            '''--------------------------------------------------------------------------'''

        self.endResetModel()  # Завершаем операцию сброса модели.

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
        return len(self._bonds)

    def columnCount(self, parent: QModelIndex = ...) -> int:
        """Возвращает количество столбцов в модели."""
        return len(self.columns)

    def data(self, index: QModelIndex, role: int = ...) -> typing.Any:
        column: BondColumn = self.columns[index.column()]
        bond_class: MyBondClass = self._bonds[index.row()]
        return column(role, bond_class, self.__calculation_dt) if column.dependsOnDateTime() else column(role, bond_class)

    def getBond(self, row: int) -> MyBondClass | None:
        """Возвращает облигацию, соответствующую переданному номеру."""
        return self._bonds[row] if 0 <= row < len(self._bonds) else None


class BondsProxyModel(QSortFilterProxyModel):
    """Прокси-модель облигаций."""
    DEPENDS_ON_DATE_COLOR: QBrush = QBrush(Qt.GlobalColor.darkRed)  # Цвет фона заголовков, зависящих от даты расчёта.

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
