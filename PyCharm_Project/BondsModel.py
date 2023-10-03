from __future__ import annotations
from datetime import datetime
import enum
import typing
from decimal import Decimal
from PyQt6.QtCore import QAbstractTableModel, Qt, QModelIndex, QSortFilterProxyModel
from tinkoff.invest.schemas import RiskLevel, Quotation, Coupon, Bond
from Classes import reportTradingStatus, Column
from CouponsThread import CouponsThread
from MyDateTime import reportSignificantInfoFromDateTime, getCurrentDateTime, reportDateIfOnlyDate
from MyQuotation import MyQuotation, MyDecimal
from MyMoneyValue import MyMoneyValue, MoneyValueToMyMoneyValue
from MyBondClass import MyBondClass, ifBondIsMulticurrency, MyLastPrice, TINKOFF_COMMISSION, NDFL, MyCoupon


def reportRiskLevel(risk_level: RiskLevel) -> str:
    """Расшифровывает уровень риска облигации."""
    match risk_level:
        case RiskLevel.RISK_LEVEL_UNSPECIFIED: return "-"
        case RiskLevel.RISK_LEVEL_LOW: return 'Низкий'
        case RiskLevel.RISK_LEVEL_MODERATE: return 'Средний'
        case RiskLevel.RISK_LEVEL_HIGH: return 'Высокий'
        case _: raise ValueError('Неизвестное значение переменной класса RiskLevel ({0})!'.format(risk_level))


class BondColumn(Column):
    """Класс столбца таблицы облигаций."""
    def __init__(self, header: str | None = None, header_tooltip: str | None = None, data_function=None, display_function=None, tooltip_function=None,
                 background_function=None, foreground_function=None,
                 date_dependence: bool = False, entered_datetime: datetime | None = None, coupon_dependence: bool = False):
        super().__init__(header, header_tooltip, data_function, display_function, tooltip_function, background_function, foreground_function)
        self._date_dependence: bool = date_dependence  # Флаг зависимости от даты.
        self._entered_datetime: datetime | None = entered_datetime  # Дата расчёта.
        self._coupon_dependence: bool = coupon_dependence  # Флаг зависимости от купонов.

    def dependsOnEnteredDate(self) -> bool:
        """Возвращает True, если значение столбца зависит от выбранной даты. Иначе возвращает False."""
        return self._date_dependence

    def dependsOnCoupons(self) -> bool:
        """Зависит ли значение столбца от купонов."""
        return self._coupon_dependence


class update_source_class:
    def __init__(self, source_model: BondsModel, source_top_left_index: QModelIndex, source_bottom_right_index: QModelIndex):
        self._source_model: BondsModel = source_model
        self._source_top_left_index: QModelIndex = source_top_left_index
        self._source_bottom_right_index: QModelIndex = source_bottom_right_index

    def __call__(self):
        return self._source_model.dataChanged.emit(self._source_top_left_index, self._source_bottom_right_index)


def showCalculatedACI(bond_class: MyBondClass, entered_datetime: datetime) -> str | None:
    """Функция для отображения рассчитанного НКД."""
    if bond_class.coupons is None:  # Если купоны ещё не были получены.
        return None

    def getLastCoupon(coupons: list[bond_class.coupons]):
        """Находит и возвращает последний купон."""
        maxim: int = -1
        for i, coupon in enumerate(coupons):
            if maxim < 0:
                maxim = i
            elif coupon.coupon_end_date > coupons[maxim].coupon_end_date:
                maxim = i
        return maxim

    def ifBondIsMaturity(bond: Bond, compared_datetime: datetime = getCurrentDateTime()) -> bool:
        """Проверяет, погашена ли облигация."""
        return bond.maturity_date < compared_datetime

    last_coupon_id: int = getLastCoupon(bond_class.coupons)
    if last_coupon_id < 0:
        return 'Нет купонов'
    last_coupon: Coupon = bond_class.coupons[last_coupon_id]
    if bond_class.bond.maturity_date < last_coupon.coupon_end_date:
        raise ValueError('Дата окончания купонного периода купона {0} больше даты погашения облигации {1}!'.
                         format(last_coupon_id, bond_class.bond.figi))
    else:
        if ifBondIsMaturity(bond_class.bond, entered_datetime):
            return 'Погашено'
        elif bond_class.bond.maturity_date > entered_datetime:
            if entered_datetime >= last_coupon.coupon_end_date:
                return 'Все купоны выплачены'
            else:
                calculated_aci: MyMoneyValue | None = bond_class.calculateACI(entered_datetime, True)
                return 'None' if calculated_aci is None else calculated_aci.report()
        else:
            return 'Все купоны выплачены'


def tooltipCalculatedACI(bond_class: MyBondClass, entered_datetime: datetime, with_fix: bool = True) -> str | None:
    """Функция для отображения подсказки рассчитанного НКД."""
    if bond_class.coupons is None:  # Если купоны ещё не были получены.
        return 'Купоны ещё не получены.'
    if len(bond_class.coupons) == 0:  # Если у облигации нет купонов.
        return 'Облигация не содержит купонов.'

    current_coupon: Coupon | None = bond_class.getCurrentCoupon(entered_datetime)  # Купон облигации, соответствующий выбранной дате.
    if current_coupon is None:
        return 'Не удалось определить текущий купон.'
    report: str = 'Текущий купон: {0}. {1}'.format(current_coupon.coupon_number, MyMoneyValue.report(current_coupon.pay_one_bond, -1))

    """---------MyCoupon.getCouponACI(current_coupon, entered_datetime, True)---------"""
    if not MyCoupon.ifCouponIsCurrent(current_coupon, entered_datetime):  # Если указанная дата не находится в границах купонного периода.
        report += '\nДата расчёта не находится в границах купонного периода текущего купона.'
        return report
    if with_fix:  # Если требуется учесть фиксацию реестра для выплаты купона.
        if MyCoupon.ifRegistryWasFixed(current_coupon, entered_datetime):  # Если фиксация реестра для выплаты купона была произведена.
            report += '\nФиксация реестра для выплаты текущего купона была произведена.'
            return report
    if current_coupon.coupon_period == 0:
        report += '\nКупонный период текущего купона равен нулю.'
        return report
    count_of_days: int = MyCoupon.getCountOfDaysOfAci(current_coupon, entered_datetime)  # Дней с начала купонного периода.
    report += '\nДней с начала купонного периода: {0}.'.format(count_of_days)
    """-------------------------------------------------------------------------------"""
    return report


def showAbsoluteProfit(bond_class: MyBondClass, entered_datetime: datetime) -> str | None:
    """Функция для отображения абсолютной доходности облигации к дате расчёта."""
    if bond_class.coupons is None:  # Если купоны ещё не были получены.
        return None
    absolute_profit: MyMoneyValue | None = bond_class.getAbsoluteProfit(entered_datetime)
    return 'None' if absolute_profit is None else absolute_profit.report()


def showRelativeProfit(bond_class: MyBondClass, entered_datetime: datetime) -> str | None:
    """Функция для отображения относительной доходности облигации к дате расчёта."""
    if bond_class.coupons is None:  # Если купоны ещё не были получены.
        return None
    relative_profit: Decimal | None = bond_class.getRelativeProfit(entered_datetime)
    return 'None' if relative_profit is None else '{0}%'.format(MyDecimal.report((relative_profit * 100), 2))


def reportCouponAbsoluteProfitCalculation(bond_class: MyBondClass, entered_datetime: datetime) -> str:
    """Рассчитывает купонную доходность к указанной дате."""
    if bond_class.coupons is None: return "Купоны ещё не заполнены."  # Если купоны ещё не были заполнены.
    current_datetime: datetime = getCurrentDateTime()  # Текущая дата.
    # Если выбранная дата меньше текущей даты.
    if entered_datetime < current_datetime: return "Выбранная дата ({0}) меньше текущей даты ({1}).".format(reportDateIfOnlyDate(entered_datetime), reportDateIfOnlyDate(current_datetime))
    # Если список купонов пуст, то используем bond.currency в качестве валюты и возвращаем 0.
    if len(bond_class.coupons) == 0: return "Список купонов пуст."

    profit: MyMoneyValue = MyMoneyValue(bond_class.coupons[0].pay_one_bond.currency)  # Доходность к выбранной дате.
    report: str = "Купонные начисления в выбранный период ({0} - {1}):".format(reportDateIfOnlyDate(current_datetime), reportDateIfOnlyDate(entered_datetime))
    for coupon in reversed(bond_class.coupons):
        """
        Расчёт купонной доходности не учитывает НКД, который выплачивается при покупке облигации,
        но учитывает НКД, который будет получен до даты конца расчёта.
        НКД, который выплачивается при покупке облигации, учитывается в расчётах доходностей облигации.
        Расчёт купонной доходности учитывает НДФЛ (в том числе НДФЛ на НКД).
        """
        # Если купонный период текущего купона целиком находится в границах заданного интервала.
        if current_datetime < coupon.coupon_start_date and entered_datetime > coupon.coupon_end_date:
            pay_one_bond: MyMoneyValue = MoneyValueToMyMoneyValue(coupon.pay_one_bond) * (1 - NDFL)
            profit += pay_one_bond  # Прибавляем величину купонной выплаты с учётом НДФЛ.
            report += "\n\t{0} Купон {1}: +{3} ({2} - 0,13%)".format(reportDateIfOnlyDate(coupon.coupon_date), str(coupon.coupon_number), MyMoneyValue.report(coupon.pay_one_bond), MyMoneyValue.report(pay_one_bond))
        # Если текущий (в цикле) купон является текущим на дату начала расчёта.
        elif MyCoupon.ifCouponIsCurrent(coupon, current_datetime):
            # Если фиксация реестра не была произведена.
            if not MyCoupon.ifRegistryWasFixed(coupon, current_datetime):
                # Если купон будет выплачен до даты конца расчёта.
                if entered_datetime >= coupon.coupon_date:
                    pay_one_bond: MyMoneyValue = MoneyValueToMyMoneyValue(coupon.pay_one_bond) * (1 - NDFL)
                    profit += pay_one_bond  # Прибавляем величину купонной выплаты с учётом НДФЛ.
                    report += "\n\t{0} Купон {1}: +{3} ({2} - 0,13%)".format(reportDateIfOnlyDate(coupon.coupon_date), str(coupon.coupon_number), MyMoneyValue.report(coupon.pay_one_bond), MyMoneyValue.report(pay_one_bond))
                # Если фиксация текущего на дату начала расчёта купона будет произведена до даты конца расчёта.
                elif MyCoupon.ifRegistryWasFixed(coupon, entered_datetime):
                    # Всё равно прибавляем величину купонной выплаты с учётом НДФЛ, хоть она и придёт только в день выплаты.
                    pay_one_bond: MyMoneyValue = MoneyValueToMyMoneyValue(coupon.pay_one_bond) * (1 - NDFL)
                    profit += pay_one_bond  # Прибавляем величину купонной выплаты с учётом НДФЛ.
                    report += "\n\t{0} Купон {1}: +{3} ({2} - 0,13%) (Купон будет выплачен после выбранной даты)".format(reportDateIfOnlyDate(coupon.coupon_date), str(coupon.coupon_number), MyMoneyValue.report(coupon.pay_one_bond), MyMoneyValue.report(pay_one_bond))
                # Если фиксация реестра и выплата купона произойдут после даты конца расчёта.
                else:
                    aci: MyMoneyValue | None = MyCoupon.getCouponACI(coupon, entered_datetime, False)  # НКД купона к дате конца расчёта.
                    if aci is None:  # Купонный период равен нулю.
                        return "Купон {0}: Купонный период равен нулю.".format(str(coupon.coupon_number))
                    aci_with_ndfl = aci * (1 - NDFL)  # Учитываем НДФЛ.
                    profit += aci_with_ndfl  # Прибавляем НКД с учётом НДФЛ.
                    report += "\n\t{0} Начисленный НКД: +{2} ({1} - 0,13%)".format(reportDateIfOnlyDate(entered_datetime), MyMoneyValue.report(aci), MyMoneyValue.report(aci_with_ndfl))
        # Если текущий (в цикле) купон является текущим на дату конца расчёта.
        elif MyCoupon.ifCouponIsCurrent(coupon, entered_datetime):
            # Если фиксация реестра будет произведена на дату конца расчёта.
            if MyCoupon.ifRegistryWasFixed(coupon, current_datetime):
                # Прибавляем величину купонной выплаты с учётом НДФЛ, хоть она и придёт только в день выплаты.
                pay_one_bond: MyMoneyValue = MoneyValueToMyMoneyValue(coupon.pay_one_bond) * (1 - NDFL)
                profit += pay_one_bond  # Прибавляем величину купонной выплаты с учётом НДФЛ.
                report += "\n\t{0} Купон {1}: +{3} ({2} - 0,13%) (Купон будет выплачен после выбранной даты)".format(reportDateIfOnlyDate(coupon.coupon_date), str(coupon.coupon_number), MyMoneyValue.report(coupon.pay_one_bond), MyMoneyValue.report(pay_one_bond))
            # Если фиксация реестра не была произведена.
            else:
                aci: MyMoneyValue | None = MyCoupon.getCouponACI(coupon, entered_datetime, False)  # НКД купона к указанной дате.
                if aci is None:  # Купонный период равен нулю.
                    return "Купон {0}: Купонный период равен нулю.".format(str(coupon.coupon_number))
                aci_with_ndfl = aci * (1 - NDFL)  # Учитываем НДФЛ.
                profit += aci_with_ndfl  # Прибавляем НКД с учётом НДФЛ.
                report += "\n\t{0} Начисленный НКД: +{2} ({1} - 0,13%)".format(reportDateIfOnlyDate(entered_datetime), MyMoneyValue.report(aci), MyMoneyValue.report(aci_with_ndfl))
    return report


def reportAbsoluteProfitCalculation(bond_class: MyBondClass, entered_datetime: datetime) -> str:
    """Отображает подробности расчёта абсолютной доходности."""
    if ifBondIsMulticurrency(bond_class.bond): return "Расчёт доходности мультивалютных облигаций ещё не реализован."
    # Доходность к выбранной дате (откуда брать валюту?).
    absolute_profit: MyMoneyValue = MyMoneyValue(bond_class.bond.currency, Quotation(units=0, nano=0))

    """---------Считаем купонную доходность---------"""
    coupon_profit: MyMoneyValue | None = bond_class.getCouponAbsoluteProfit(entered_datetime)  # Купонный доход к выбранной дате.
    if coupon_profit is None: return "Не удалось рассчитать купонную доходность."
    absolute_profit += coupon_profit
    report: str = "Расчёт купонного дохода к выбранной дате:\n\t{0}\n\tКупонная доходность: {1}".format(reportCouponAbsoluteProfitCalculation(bond_class, entered_datetime), MyMoneyValue.report(coupon_profit))
    """---------------------------------------------"""

    """---------------Учитываем НКД в цене---------------"""
    # НКД, указанная в облигации, учитывает дату фиксации реестра.
    absolute_profit -= bond_class.bond.aci_value  # Вычитаем НКД.
    report += "\nНКД, указанный в облигации: - {0}".format(MyMoneyValue.report(bond_class.bond.aci_value))
    """--------------------------------------------------"""

    """--Учитываем возможное погашение облигации к выбранной дате--"""
    if bond_class.last_price is None:
        raise ValueError('Последняя цена облигации должна была быть получена!')
    if not MyLastPrice.isNone(bond_class.last_price):  # Проверка цены.
        # Если облигация будет погашена до выбранной даты включительно.
        if entered_datetime >= bond_class.bond.maturity_date:
            # Добавляем в доходность разницу между номиналом и ценой облигации.
            absolute_profit += bond_class.bond.nominal
            last_price_value: MyMoneyValue = bond_class.getLastPrice()
            absolute_profit -= (last_price_value * (1.0 + TINKOFF_COMMISSION))
            report += "\nОблигация будет погашена до выбранной даты.\nРазница между номиналом и ценой с учётом комиссии: {0}".format(MyMoneyValue.report(MoneyValueToMyMoneyValue(bond_class.bond.nominal) - (last_price_value * (1.0 + TINKOFF_COMMISSION))))
    else:
        # Если цена облигации неизвестна, то рассчитывается так, будто цена облигации равняется номиналу.
        absolute_profit -= (MoneyValueToMyMoneyValue(bond_class.bond.nominal) * TINKOFF_COMMISSION)
        report += "\nЦена облигации неизвестна, используем в расчёте номинал.\nНоминал облигации с учётом комиссии: {0}".format(bond_class.bond.nominal)
    """------------------------------------------------------------"""
    report += "\nИтого: {0}".format(MyMoneyValue.report(absolute_profit))
    return report


class BondsModel(QAbstractTableModel):
    """Моя модель облигаций."""
    @enum.unique  # Декоратор, требующий, чтобы все элементы имели разные значения.
    class Columns(enum.IntEnum):
        """Перечисление столбцов таблицы облигаций."""
        BOND_ISIN = 0
        BOND_NAME = 1
        LAST_PRICE = 2
        BOND_NKD = 3
        CALCULATED_NKD = 4
        BOND_NOMINAL = 5
        BOND_INITIAL_NOMINAL = 6
        BOND_MIN_PRICE_INCREMENT = 7
        BOND_LOT = 8
        BOND_TRADING_STATUS = 9
        BOND_AMORTIZATION_FLAG = 10
        BOND_MATURITY_DATE = 11
        BOND_CURRENCY = 12
        BOND_COUNTRY_OF_RISK_NAME = 13
        DATE_ABSOLUTE_PROFIT = 14
        DATE_RELATIVE_PROFIT = 15
        BOND_RISK_LEVEL = 16

    def __init__(self, entered_datetime: datetime):
        super().__init__()  # __init__() QAbstractTableModel.
        self.current_time: datetime | None = None  # Текущие время и дата.
        self._calculation_datetime: datetime = entered_datetime  # Дата расчёта.
        self._bond_class_list: list[MyBondClass] = []
        self.coupons_receiving_thread: CouponsThread | None = None  # Поток, заполняющий купоны облигаций.
        self.columns: dict[int, BondColumn] = {
            self.Columns.BOND_ISIN:
                BondColumn(header='isin',
                           header_tooltip='Isin-идентификатор инструмента.',
                           data_function=lambda bond_class: bond_class.bond.isin),
            self.Columns.BOND_NAME:
                BondColumn(header='Название',
                           header_tooltip='Название инструмента.',
                           data_function=lambda bond_class: bond_class.bond.name),
            self.Columns.LAST_PRICE:
                BondColumn(header='Цена',
                           header_tooltip='Цена последней сделки по облигации.',
                           data_function=lambda bond_class: bond_class.getLastPrice(),
                           display_function=lambda bond_class: bond_class.reportLastPrice(),
                           tooltip_function=lambda bond_class: 'Нет данных.' if bond_class.last_price is None else 'last_price:\nfigi = {0},\nprice = {1},\ntime = {2},\ninstrument_uid = {3}.'.format(bond_class.last_price.figi, MyQuotation.report(bond_class.last_price.price), bond_class.last_price.time, bond_class.last_price.instrument_uid)),
            self.Columns.BOND_NKD:
                BondColumn(header='НКД',
                           header_tooltip='Значение НКД (накопленного купонного дохода) на дату.',
                           data_function=lambda bond_class: bond_class.bond.aci_value,
                           display_function=lambda bond_class: MyMoneyValue.report(bond_class.bond.aci_value)),
            self.Columns.CALCULATED_NKD:
                BondColumn(header='НКД к дате',
                           header_tooltip='Рассчитанное значение НКД (накопленного купонного дохода) на дату.',
                           data_function=lambda bond_class, entered_dt: bond_class.calculateACI(entered_dt, True),
                           display_function=lambda bond_class, entered_dt: showCalculatedACI(bond_class, entered_dt),
                           tooltip_function=lambda bond_class, entered_dt: tooltipCalculatedACI(bond_class, entered_dt, True),
                           date_dependence=True,
                           coupon_dependence=True),
            self.Columns.BOND_NOMINAL:
                BondColumn(header='Номинал',
                           header_tooltip='Номинал облигации.',
                           data_function=lambda bond_class: bond_class.bond.nominal,
                           display_function=lambda bond_class: MyMoneyValue.report(bond_class.bond.nominal, 2)),
            self.Columns.BOND_INITIAL_NOMINAL:
                BondColumn(header='Начальный номинал',
                           header_tooltip='Первоначальный номинал облигации.',
                           data_function=lambda bond_class: bond_class.bond.initial_nominal,
                           display_function=lambda bond_class: MyMoneyValue.report(bond_class.bond.initial_nominal)),
            self.Columns.BOND_MIN_PRICE_INCREMENT:
                BondColumn(header='Шаг цены',
                           header_tooltip='Минимальное изменение цены определённого инструмента.',
                           data_function=lambda bond_class: bond_class.bond.min_price_increment,
                           display_function=lambda bond_class: MyQuotation.report(bond_class.bond.min_price_increment, ndigits=9, delete_decimal_zeros=True)),
            self.Columns.BOND_LOT:
                BondColumn(header='Лотность',
                           header_tooltip='Лотность инструмента.',
                           data_function=lambda bond_class: bond_class.bond.lot,
                           display_function=lambda bond_class: str(bond_class.bond.lot)),
            self.Columns.BOND_TRADING_STATUS:
                BondColumn(header='Режим торгов',
                           header_tooltip='Текущий режим торгов инструмента.',
                           data_function=lambda bond_class: bond_class.bond.trading_status,
                           display_function=lambda bond_class: reportTradingStatus(bond_class.bond.trading_status)),
            self.Columns.BOND_AMORTIZATION_FLAG:
                BondColumn(header='Амортизация',
                           header_tooltip='Признак облигации с амортизацией долга.',
                           data_function=lambda bond_class: bond_class.bond.amortization_flag,
                           display_function=lambda bond_class: "Да" if bond_class.bond.amortization_flag else "Нет"),
            self.Columns.BOND_MATURITY_DATE:
                BondColumn(header='Дата погашения',
                           header_tooltip='Дата погашения облигации в часовом поясе UTC.',
                           data_function=lambda bond_class: bond_class.bond.maturity_date,
                           display_function=lambda bond_class: reportSignificantInfoFromDateTime(bond_class.bond.maturity_date)),
            self.Columns.BOND_CURRENCY:
                BondColumn(header='Валюта',
                           header_tooltip='Валюта расчётов.',
                           data_function=lambda bond_class: bond_class.bond.currency),
            self.Columns.BOND_COUNTRY_OF_RISK_NAME:
                BondColumn(header='Страна риска',
                           header_tooltip='Наименование страны риска, т.е. страны, в которой компания ведёт основной бизнес.',
                           data_function=lambda bond_class: bond_class.bond.country_of_risk_name),
            self.Columns.DATE_ABSOLUTE_PROFIT:
                BondColumn(header='Дох-ть к дате',
                           header_tooltip='Абсолютная доходность к выбранной дате.',
                           data_function=lambda bond_class, entered_dt: bond_class.getAbsoluteProfit(entered_dt),
                           display_function=lambda bond_class, entered_dt: showAbsoluteProfit(bond_class, entered_dt),
                           tooltip_function=lambda bond_class, entered_dt: reportAbsoluteProfitCalculation(bond_class, entered_dt),
                           date_dependence=True,
                           coupon_dependence=True),
            self.Columns.DATE_RELATIVE_PROFIT:
                BondColumn(header='Отн-ая дох-ть к дате',
                           header_tooltip='Относительная доходность к выбранной дате.',
                           data_function=lambda bond_class, entered_dt: bond_class.getRelativeProfit(entered_dt),
                           display_function=lambda bond_class, entered_dt: showRelativeProfit(bond_class, entered_dt),
                           date_dependence=True,
                           coupon_dependence=True),
            self.Columns.BOND_RISK_LEVEL:
                BondColumn(header='Риск',
                           header_tooltip='Уровень риска.',
                           data_function=lambda bond_class: bond_class.bond.risk_level,
                           display_function=lambda bond_class: reportRiskLevel(bond_class.bond.risk_level))
        }

    def rowCount(self, parent: QModelIndex = ...) -> int:
        """Возвращает количество облигаций в модели."""
        return len(self._bond_class_list)

    def columnCount(self, parent: QModelIndex = ...) -> int:
        """Возвращает количество столбцов в модели."""
        return len(self.columns)

    def data(self, index: QModelIndex, role: int = ...) -> typing.Any:
        column: BondColumn = self.columns[index.column()]
        bond_class: MyBondClass = self._bond_class_list[index.row()]
        return column(role, bond_class, self._calculation_datetime) if column.dependsOnEnteredDate() else column(role, bond_class)

    def setBonds(self, bond_class_list: list[MyBondClass]):
        """Устанавливает данные модели."""
        self.beginResetModel()  # Начинает операцию сброса модели.
        self.current_time: datetime = getCurrentDateTime()  # Получаем текущую datetime, чтобы закрасить уже выплаченные облигации.
        self._bond_class_list: list[MyBondClass] = bond_class_list
        for row, bond_class in enumerate(self._bond_class_list):
            for column, bond_column in self.columns.items():
                if bond_column.dependsOnCoupons():
                    source_index: QModelIndex = self.index(row, column)
                    # bond_class.setCoupons_signal.connect(lambda: self.dataChanged.emit(source_index, source_index))  # Подключаем слот обновления.
                    # bond_class.setCoupons_signal.connect(lambda: self.sourceDataChanged(row, column))
                    bond_class.setCoupons_signal.connect(update_source_class(self, source_index, source_index))  # Подключаем слот обновления.
        self.endResetModel()  # Завершает операцию сброса модели.

    def setDateTime(self, entered_datetime: datetime):
        """Устанавливает новую дату расчёта."""
        self._calculation_datetime = entered_datetime

        """---------Сообщаем о необходимости обновить столбцы---------"""
        bonds_count: int = len(self._bond_class_list)
        if bonds_count > 0:
            for column, bond_column in self.columns.items():
                if bond_column.dependsOnEnteredDate():
                    top_index: QModelIndex = self.index(0, column)
                    bottom_index: QModelIndex = self.index((bonds_count - 1), column)
                    self.dataChanged.emit(top_index, bottom_index)
        """-----------------------------------------------------------"""

    def getData(self, row: int) -> MyBondClass | None:
        """Возвращает облигацию, соответствующую переданному номеру."""
        return self._bond_class_list[row] if 0 <= row < len(self._bond_class_list) else None

    def getBonds(self) -> list[MyBondClass]:
        """Возвращает облигации, хранящиеся в модели."""
        return self._bond_class_list

    def stopCouponsThread(self):
        """Останавливает поток получения купонов и дожидается завершения."""
        if self.coupons_receiving_thread is not None:  # Если поток был создан.
            self.coupons_receiving_thread.requestInterruption()  # Сообщаем потоку о том, что надо завершиться.
            self.coupons_receiving_thread.wait()  # Ждём завершения потока.
            self.coupons_receiving_thread = None


class BondsProxyModel(QSortFilterProxyModel):
    """Моя прокси-модель облигаций."""

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = ...) -> typing.Any:
        """Функция headerData объявлена в прокси-модели, чтобы названия строк не сортировались вместе с данными."""
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Vertical: return section + 1  # Проставляем номера строк.
            if orientation == Qt.Orientation.Horizontal: return self.sourceModel().columns[section].header
        elif role == Qt.ItemDataRole.ToolTipRole:  # Подсказки.
            if orientation == Qt.Orientation.Horizontal: return self.sourceModel().columns[section].header_tooltip

    def sourceModel(self) -> BondsModel:
        """Возвращает исходную модель."""
        source_model = super().sourceModel()
        assert type(source_model) == BondsModel
        return typing.cast(BondsModel, source_model)
