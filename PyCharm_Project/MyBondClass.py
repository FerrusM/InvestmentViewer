from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from PyQt6.QtCore import QObject, pyqtSignal
from tinkoff.invest import Bond, Coupon, LastPrice, CouponType, Quotation, HistoricCandle
from tinkoff.invest.utils import decimal_to_quotation
from MyDateTime import getUtcDateTime
from MyLastPrice import MyLastPrice
from MyMoneyValue import MyMoneyValue, ifCurrenciesAreEqual
from MyQuotation import MyQuotation

TINKOFF_COMMISSION: float = 0.003
NDFL: float = 0.13
DAYS_IN_YEAR: int = 365


class MyCoupon:
    """Класс, объединяющий функции для работы с купонами."""
    @staticmethod  # Преобразует метод класса в статический метод этого класса.
    def ifCouponHasBeenPaid(coupon: Coupon, entered_datetime: datetime = getUtcDateTime()) -> bool:
        """Возвращает True, если купон уже выплачен на момент указанной даты, иначе возвращает False."""
        return entered_datetime >= coupon.coupon_end_date  # Сравниваем дату окончания купонного периода с указанной датой.

    @staticmethod  # Преобразует метод класса в статический метод этого класса.
    def ifCouponIsCurrent(coupon: Coupon, entered_datetime: datetime = getUtcDateTime()) -> bool:
        """Возвращает True, если указанная дата находится в границах купонного периода."""
        return coupon.coupon_start_date <= entered_datetime <= coupon.coupon_end_date

    @staticmethod  # Преобразует метод класса в статический метод этого класса.
    def ifRegistryWasFixed(coupon: Coupon, entered_datetime: datetime = getUtcDateTime()) -> bool:
        """Возвращает True, если фиксация реестра на момент указанной даты была произведена."""
        """
        После фиксации реестра для выплаты купона получатель текущего купона будет определён.
        Если продажа облигации будет совершена после фиксации реестра текущего купона,
        то продавец всё равно получит выплату по текущему купону в день его выплаты.
        Если покупка облигации будет совершена не раньше даты фиксации реестра текущего купона,
        то покупатель не получит выплату по текущему купону по этой облигации.
        Если фиксация реестра была произведена, то НКД не должно входить в итоговую цену облигации.
        Я не знаю, можно ли определить временной интервал, в который осуществляется фиксация реестра для выплаты купона
        в день фиксации реестра.
        Эта функция определяет, наступил ли день фиксации реестра.
        """
        """
        В расчётах, связанных с продажей имеющейся облигации, стоит пересмотреть критерии определения того, 
        что фиксация реестра для выплаты купона была произведена.
        Например, можно определять фиксацию реестра по значению параметра aci_value облигации,
        но для этого необходимо знать, есть ли у облигации купоны, и учитывать тип купона и его величину.
        """
        return coupon.fix_date <= entered_datetime

    @staticmethod  # Преобразует метод класса в статический метод этого класса.
    def getCountOfDaysOfAci(coupon: Coupon, entered_datetime: datetime = getUtcDateTime()) -> int:
        """Возвращает количество дней купонного накопления к указанной дате."""
        '''
        Начисление НКД производится между 3:00 и 13:45 по МСК по моим наблюдениям.
        Эта функция не всегда даёт точный результат, так как учитывает в расчёте только даты без времени.
        '''
        # return (entered_datetime.date() - coupon.coupon_start_date.date()).days  # Дней с начала купонного периода.
        return (entered_datetime.date() - coupon.coupon_start_date.date()).days + 1  # Дней с начала купонного периода.

    @staticmethod  # Преобразует метод класса в статический метод этого класса.
    def getCouponACI(coupon: Coupon, entered_datetime: datetime = getUtcDateTime(), with_fix: bool = False) -> MyMoneyValue | None:
        """Возвращает НКД купона к указанным дате и времени."""
        if not MyCoupon.ifCouponIsCurrent(coupon, entered_datetime): return None  # Если указанная дата не находится в границах купонного периода.
        if with_fix:  # Если требуется учесть фиксацию реестра для выплаты купона.
            if MyCoupon.ifRegistryWasFixed(coupon, entered_datetime):  # Если фиксация реестра для выплаты купона была произведена.
                return MyMoneyValue(coupon.pay_one_bond.currency, Quotation(units=0, nano=0))  # Возвращаем ноль.
        if coupon.coupon_period == 0: return None  # Избегаем деления на ноль.
        count_of_days: int = MyCoupon.getCountOfDaysOfAci(coupon, entered_datetime)  # Дней с начала купонного периода.
        aci: Decimal = MyMoneyValue.getDecimal(coupon.pay_one_bond) * count_of_days / coupon.coupon_period
        return MyMoneyValue(coupon.pay_one_bond.currency, decimal_to_quotation(aci))


class MyBond:
    """Класс, объединяющий функции для работы с облигациями."""
    @staticmethod  # Преобразует метод класса в статический метод этого класса.
    def ifBondIsMaturity(bond: Bond, compared_datetime: datetime = getUtcDateTime()) -> bool:
        """Проверяет, погашена ли облигация."""
        return bond.maturity_date < compared_datetime

    @staticmethod  # Преобразует метод класса в статический метод этого класса.
    def ifBondIsMulticurrency(bond: Bond) -> bool:
        """Возвращает True, если не все поля MoneyValue-типа облигации имеют одинаковую валюту, иначе возвращает False."""
        return not ifCurrenciesAreEqual(bond.currency, bond.nominal, bond.initial_nominal, bond.aci_value)

    @staticmethod  # Преобразует метод класса в статический метод этого класса.
    def getDaysToMaturityCount(bond: Bond, calculation_datetime: datetime = getUtcDateTime()) -> int:
        """Возвращает количество дней до погашения облигации."""
        return (bond.maturity_date.date() - calculation_datetime.date()).days


class MyBondClass(QObject):
    """Класс облигации, дополненный параметрами (последняя цена, купоны) и функциями."""
    setCoupons_signal: pyqtSignal = pyqtSignal()  # Сигнал, испускаемый при изменении списка купонов.

    def __init__(self, bond: Bond, last_price: LastPrice | None = None, coupons: list[Coupon] | None = None, candles: list[HistoricCandle] | None = None, parent: QObject | None = None):
        super().__init__(parent)
        self.bond: Bond = bond
        self.last_price: LastPrice | None = last_price
        self.coupons: list[Coupon] | None = coupons  # Список купонов.
        self.candles: list[HistoricCandle] | None = candles

    def instrument(self) -> Bond:
        """Возвращает инструмент (облигацию), хранящийся в классе."""
        return self.bond

    def getLastPrice(self) -> MyMoneyValue | None:
        """Рассчитывает последнюю цену одной облигации."""
        if self.last_price is None: return None
        # Пункты цены для котировок облигаций представляют собой проценты номинала облигации.
        value: Decimal = MyQuotation.getDecimal(self.last_price.price) * MyMoneyValue.getDecimal(self.bond.nominal) / 100
        return MyMoneyValue(self.bond.nominal.currency, decimal_to_quotation(value))

    def reportLastPrice(self, ndigits: int = 2, delete_decimal_zeros: bool = False) -> str:
        """Отображает структуру MoneyValue, соответствующую последней цене одной облигации."""
        last_price: MyMoneyValue | None = self.getLastPrice()
        if last_price is None: return 'Нет данных'
        if MyLastPrice.isEmpty(self.last_price): return 'Нет данных'
        return MyMoneyValue.__str__(last_price, ndigits, delete_decimal_zeros)

    def getLotLastPrice(self) -> MyMoneyValue | None:
        """Рассчитывает последнюю цену лота."""
        last_price: MyMoneyValue | None = self.getLastPrice()
        if last_price is None: return None
        return last_price * self.bond.lot

    def reportLotLastPrice(self, ndigits: int = 2, delete_decimal_zeros: bool = False) -> str:
        """Отображает структуру MoneyValue, соответствующую последней цене лота."""
        last_price: MyMoneyValue | None = self.getLastPrice()
        if last_price is None: return 'Нет данных'
        if MyLastPrice.isEmpty(self.last_price): return 'Нет данных'
        return MyMoneyValue.__str__(last_price * self.bond.lot, ndigits, delete_decimal_zeros)

    def getCoupon(self, coupon_number: int) -> Coupon | None:
        """Возвращает купон, соответствующий переданному порядковому номеру.
        Если купон не найден, то возвращает None."""
        if self.coupons is None:
            return None
        elif 0 <= coupon_number < len(self.coupons):
            return self.coupons[coupon_number]
        else:
            return None

    def setCoupons(self, coupons_list: list[Coupon]):
        """Заполняет список купонов."""
        self.coupons = coupons_list
        self.setCoupons_signal.emit()  # Испускаем сигнал о том, что купоны были изменены.

    def getCouponsCurrency(self) -> str | None:
        """Если все купоны облигации имеют одинаковую валюту, то возвращает её, иначе возвращает None."""
        if self.coupons is None: return None  # Если купоны ещё не были заполнены.
        if len(self.coupons) == 0: return None  # Если список купонов пуст.
        currency: str = self.coupons[0].pay_one_bond.currency
        for coupon in self.coupons:
            if coupon.pay_one_bond.currency != currency:
                return None
        return currency

    """---------------------Купонная доходность облигаций---------------------"""
    def getCouponAbsoluteProfit(self, calculation_datetime: datetime, current_datetime: datetime = getUtcDateTime()) -> MyMoneyValue | None:
        """Рассчитывает купонную доходность к указанной дате."""
        if self.coupons is None: return None  # Если купоны ещё не были заполнены.
        if calculation_datetime < current_datetime: return None  # Если дата расчёта меньше текущей даты.
        # Если список купонов пуст, то используем bond.currency в качестве валюты и возвращаем 0.
        if len(self.coupons) == 0: return MyMoneyValue(self.bond.currency, Quotation(units=0, nano=0))

        profit: MyMoneyValue = MyMoneyValue(self.coupons[0].pay_one_bond.currency)  # Доходность к выбранной дате.
        for coupon in self.coupons:
            '''
            Расчёт купонной доходности не учитывает НКД, который выплачивается при покупке облигации,
            но учитывает НКД, который будет получен до даты конца расчёта.
            НКД, который выплачивается при покупке облигации, учитывается в расчётах доходностей облигации.
            Расчёт купонной доходности учитывает НДФЛ (в том числе НДФЛ на НКД).
            '''
            # Если купонный период текущего купона целиком находится в границах заданного интервала.
            if current_datetime < coupon.coupon_start_date and calculation_datetime > coupon.coupon_end_date:
                profit += coupon.pay_one_bond  # Прибавляем всю величину купонной выплаты.
            # Если текущий (в цикле) купон является текущим на дату начала расчёта.
            elif MyCoupon.ifCouponIsCurrent(coupon, current_datetime):
                # Если фиксация реестра не была произведена.
                if not MyCoupon.ifRegistryWasFixed(coupon, current_datetime):
                    # Если купон будет выплачен до даты конца расчёта.
                    if calculation_datetime >= coupon.coupon_date:
                        profit += coupon.pay_one_bond  # Прибавляем всю величину купонной выплаты.
                    # Если фиксация текущего на дату начала расчёта купона будет произведена до даты конца расчёта.
                    elif MyCoupon.ifRegistryWasFixed(coupon, calculation_datetime):
                        # Всё равно прибавляем всю величину купонной выплаты, хоть она и придёт только в день выплаты.
                        profit += coupon.pay_one_bond
                    # Если фиксация реестра и выплата купона произойдут после даты конца расчёта.
                    else:
                        aci: MyMoneyValue | None = MyCoupon.getCouponACI(coupon, calculation_datetime, False)  # НКД купона к дате конца расчёта.
                        if aci is None: return None  # Купонный период равен нулю.
                        profit += aci  # Прибавляем НКД.
            # Если текущий (в цикле) купон является текущим на дату конца расчёта.
            elif MyCoupon.ifCouponIsCurrent(coupon, calculation_datetime):
                # Если фиксация реестра будет произведена на дату конца расчёта.
                if MyCoupon.ifRegistryWasFixed(coupon, current_datetime):
                    # Прибавляем всю величину купонной выплаты, хоть она и придёт только в день выплаты.
                    profit += coupon.pay_one_bond
                # Если фиксация реестра не была произведена.
                else:
                    aci: MyMoneyValue | None = MyCoupon.getCouponACI(coupon, calculation_datetime, False)  # НКД купона к указанной дате.
                    if aci is None: return None  # Купонный период равен нулю.
                    profit += aci  # Прибавляем НКД.
        return profit * (1 - NDFL)  # Учитываем НДФЛ.
    """-----------------------------------------------------------------------"""

    """========================Доходности========================"""
    def getAbsoluteProfit(self, calculation_datetime: datetime) -> MyMoneyValue | None:
        """Рассчитывает абсолютную доходность облигации к выбранной дате."""
        if MyBond.ifBondIsMulticurrency(self.bond): return None  # Ещё нет расчёта мультивалютных облигаций.
        # Доходность к выбранной дате (откуда брать валюту?).
        absolute_profit: MyMoneyValue = MyMoneyValue(self.bond.currency, Quotation(units=0, nano=0))

        '''---------Считаем купонную доходность---------'''
        coupon_profit: MyMoneyValue | None = self.getCouponAbsoluteProfit(calculation_datetime)  # Купонный доход к выбранной дате.
        if coupon_profit is None: return None
        absolute_profit += coupon_profit
        '''---------------------------------------------'''

        '''---------------Учитываем НКД в цене---------------'''
        # НКД, указанная в облигации, учитывает дату фиксации реестра.
        absolute_profit -= self.bond.aci_value  # Вычитаем НКД.
        '''--------------------------------------------------'''

        '''--Учитываем возможное погашение облигации к выбранной дате--'''
        if self.last_price is None or MyLastPrice.isEmpty(self.last_price):  # Проверка цены.
            return None

            # # Если цена облигации неизвестна, то рассчитывается так, будто цена облигации равняется номиналу.
            # absolute_profit -= (MoneyValueToMyMoneyValue(self.bond.nominal) * TINKOFF_COMMISSION)
        else:
            # Если облигация будет погашена до выбранной даты включительно.
            if calculation_datetime >= self.bond.maturity_date:
                # Добавляем в доходность разницу между номиналом и ценой облигации.
                absolute_profit += self.bond.nominal
                absolute_profit -= (self.getLastPrice() * (1.0 + TINKOFF_COMMISSION))
        '''------------------------------------------------------------'''
        return absolute_profit

    def getRelativeProfit(self, calculation_datetime: datetime) -> Decimal | None:
        """Рассчитывает относительную доходность облигации к выбранной дате."""
        absolute_profit: MyMoneyValue | None = self.getAbsoluteProfit(calculation_datetime)  # Рассчитывает абсолютную доходность к выбранной дате.
        if absolute_profit is None: return None
        ''''''
        # if self.last_price is None: return None
        ''''''
        if MyLastPrice.isEmpty(self.last_price): return None  # Проверка цены.
        if MyQuotation.IsEmpty(MyMoneyValue.getQuotation(self.bond.nominal)) or MyQuotation.IsEmpty(self.last_price.price): return None  # Избегаем деления на ноль.
        return absolute_profit / self.getLastPrice()

    def getCouponRelativeProfit(self, calculation_datetime: datetime) -> Decimal | None:
        """Рассчитывает относительную купонную доходность к дате."""
        # Рассчитываем абсолютную купонную доходность к выбранной дате
        coupon_absolute_profit: MyMoneyValue | None = self.getCouponAbsoluteProfit(calculation_datetime)
        if coupon_absolute_profit is None: return None
        if MyQuotation.IsEmpty(MyMoneyValue.getQuotation(self.bond.nominal)) is None: return None  # Избегаем деления на ноль.
        return coupon_absolute_profit / self.bond.nominal

    def getCouponAnnualRelativeProfit(self) -> Decimal | None:
        """Рассчитывает годовую относительную купонную доходность."""
        if self.coupons is None: return None  # Если купоны ещё не были заполнены.
        if len(self.coupons) == 0: return Decimal('0')  # Если купонов нет, то доходность равна нулю.

        currency: str | None = self.getCouponsCurrency()  # Возвращает валюту купонов.
        if currency is None: return None

        # Валюта номинала облигации и всех её купонов должна быть одна и та же.
        if currency != self.bond.nominal.currency: return None

        # Расчёт годовой относительной купонной доходности реализован только для постоянных купонов.
        if any(coupon.coupon_type != CouponType.COUPON_TYPE_CONSTANT for coupon in self.coupons): return None

        # Для облигаций с амортизацией необходимо использовать первый (последний в списке купонов) купон.
        first_coupon: Coupon = self.coupons[-1]
        if MyQuotation.IsEmpty(MyMoneyValue.getQuotation(self.bond.nominal)) or first_coupon.coupon_period == 0: return None  # Избегаем деления на ноль.

        pay_one_bond: Decimal = MyMoneyValue.getDecimal(first_coupon.pay_one_bond)
        coupon_annual_relative_profit: Decimal = (pay_one_bond * DAYS_IN_YEAR) / (MyMoneyValue.getDecimal(self.bond.nominal) * first_coupon.coupon_period)
        return coupon_annual_relative_profit

    """=========================================================="""

    def getCurrentCoupon(self, entered_datetime: datetime = getUtcDateTime()) -> Coupon | None:
        """Возвращает купон облигации, который соответствует выбранной дате."""
        if self.coupons is None: return None  # Если список купонов ещё не был заполнен.
        current_coupon: Coupon | None = None
        for coupon in self.coupons:
            if coupon.coupon_start_date <= entered_datetime < coupon.coupon_end_date:
                if current_coupon is not None:
                    raise ValueError("Купонные периоды нескольких купонов облигации \'{0}\' пересекаются!".format(self.bond.figi))
                current_coupon = coupon
        return current_coupon

    def getCouponRate(self, coupon: Coupon | None) -> Decimal | None:
        """Рассчитывает ставку купона."""
        if coupon is None: return None
        if not ifCurrenciesAreEqual(coupon.pay_one_bond, self.bond.nominal): return None
        if MyQuotation.IsEmpty(MyMoneyValue.getQuotation(self.bond.nominal)) or coupon.coupon_period == 0: return None  # Избегаем деления на ноль.
        n: Decimal = MyMoneyValue.getDecimal(self.bond.nominal)
        return (MyMoneyValue.getDecimal(coupon.pay_one_bond) * DAYS_IN_YEAR) / (n * coupon.coupon_period)

    def getPaidCouponsCount(self) -> int | None:
        """Возвращает количество выплаченных купонов."""
        if self.coupons is None: return None  # Если список купонов ещё не был заполнен.
        paid_coupons_count: int = 0  # Количество выплаченных купонов.
        for coupon in self.coupons:
            if MyCoupon.ifCouponHasBeenPaid(coupon): paid_coupons_count += 1
        return paid_coupons_count

    def calculateACI(self, calculation_datetime: datetime = getUtcDateTime(), with_fix: bool = True) -> MyMoneyValue | None:
        """Рассчитывает НКД (накопленный купонный доход) облигации к выбранной дате."""
        # Купон облигации, соответствующий выбранной дате.
        current_coupon: Coupon | None = self.getCurrentCoupon(calculation_datetime)
        if current_coupon is None: return None
        return MyCoupon.getCouponACI(current_coupon, calculation_datetime, with_fix)
