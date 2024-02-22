from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from PyQt6 import QtCore
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
    def __eq__(self: Coupon, other: Coupon) -> bool:
        """self == other"""
        if not type(other) == Coupon:
            raise TypeError('Правый операнд должен иметь тип Coupon, а передан тип {0}!'.format(type(other)))
        if self.figi == other.figi and self.coupon_date == other.coupon_date and \
                self.coupon_number == other.coupon_number and self.fix_date == other.fix_date and \
                MyMoneyValue.__eq__(self.pay_one_bond, other.pay_one_bond) and \
                self.coupon_type == other.coupon_type and self.coupon_start_date == other.coupon_start_date and \
                self.coupon_end_date == other.coupon_end_date and self.coupon_period == other.coupon_period:
            return True
        else:
            return False

    @staticmethod
    def ifCouponHasBeenPaid(coupon: Coupon, entered_datetime: datetime = getUtcDateTime()) -> bool:
        """Возвращает True, если купон уже выплачен на момент указанной даты, иначе возвращает False."""
        return entered_datetime >= coupon.coupon_end_date  # Сравниваем дату окончания купонного периода с указанной датой.

    @staticmethod
    def ifCouponIsCurrent(coupon: Coupon, entered_datetime: datetime = getUtcDateTime()) -> bool:
        """Возвращает True, если указанная дата находится в границах купонного периода."""
        return coupon.coupon_start_date <= entered_datetime <= coupon.coupon_end_date

    @staticmethod
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

    @staticmethod
    def getCountOfDaysOfAci(coupon: Coupon, entered_datetime: datetime = getUtcDateTime()) -> int:
        """Возвращает количество дней купонного накопления к указанной дате."""
        '''
        Начисление НКД производится между 3:00 и 13:45 по МСК по моим наблюдениям.
        Эта функция не всегда даёт точный результат, так как учитывает в расчёте только даты без времени.
        '''
        # return (entered_datetime.date() - coupon.coupon_start_date.date()).days  # Дней с начала купонного периода.
        return (entered_datetime.date() - coupon.coupon_start_date.date()).days + 1  # Дней с начала купонного периода.

    @staticmethod
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
    def __eq__(self: Bond, other: Bond):
        if self.figi == other.figi and self.ticker == other.ticker and self.class_code == other.class_code and \
                self.isin == other.isin and self.lot == other.lot and self.currency == other.currency and \
                self.klong == other.klong and self.kshort == other.kshort and self.dlong == other.dlong and \
                self.dshort == other.dshort and self.dlong_min == other.dlong_min and \
                self.dshort_min == other.dshort_min and self.short_enabled_flag == other.short_enabled_flag and \
                self.name == other.name and self.exchange == other.exchange and \
                self.coupon_quantity_per_year == other.coupon_quantity_per_year and \
                self.maturity_date == other.maturity_date and MyMoneyValue.__eq__(self.nominal, other.nominal) and \
                MyMoneyValue.__eq__(self.initial_nominal, other.initial_nominal) and \
                self.state_reg_date == other.state_reg_date and self.placement_date == other.placement_date and \
                MyMoneyValue.__eq__(self.placement_price, other.placement_price) and \
                MyMoneyValue.__eq__(self.aci_value, other.aci_value) and self.country_of_risk == other.country_of_risk \
                and self.country_of_risk_name == other.country_of_risk_name and self.sector == other.sector and \
                self.issue_kind == other.issue_kind and self.issue_size == other.issue_size and \
                self.issue_size_plan == other.issue_size_plan and self.trading_status == other.trading_status and \
                self.otc_flag == other.otc_flag and self.buy_available_flag == other.buy_available_flag and \
                self.sell_available_flag == other.sell_available_flag and \
                self.floating_coupon_flag == other.floating_coupon_flag and \
                self.perpetual_flag == other.perpetual_flag and self.amortization_flag == other.amortization_flag and \
                self.min_price_increment == other.min_price_increment and \
                self.api_trade_available_flag == other.api_trade_available_flag and self.uid == other.uid and \
                self.real_exchange == other.real_exchange and self.position_uid == other.position_uid and \
                self.asset_uid == other.asset_uid and self.for_iis_flag == other.for_iis_flag and \
                self.for_qual_investor_flag == other.for_qual_investor_flag and \
                self.weekend_flag == other.weekend_flag and self.blocked_tca_flag == other.blocked_tca_flag and \
                self.subordinated_flag == other.subordinated_flag and self.liquidity_flag == other.liquidity_flag and \
                self.first_1min_candle_date == other.first_1min_candle_date and \
                self.first_1day_candle_date == other.first_1day_candle_date and self.risk_level == other.risk_level:
            return True
        else:
            return False

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


class MyBondClass(QtCore.QObject):
    """Класс облигации, дополненный параметрами (последняя цена, купоны) и функциями."""
    bondChanged_signal: QtCore.pyqtSignal = QtCore.pyqtSignal()  # Сигнал, испускаемый при изменении облигации.
    couponsChanged_signal: QtCore.pyqtSignal = QtCore.pyqtSignal()  # Сигнал, испускаемый при изменении списка купонов.
    lastPriceChanged_signal: QtCore.pyqtSignal = QtCore.pyqtSignal()  # Сигнал, испускаемый при изменении последней цены.

    def __init__(self, bond: Bond, last_price: LastPrice | None = None, coupons: list[Coupon] | None = None, candles: list[HistoricCandle] | None = None, parent: QtCore.QObject | None = None):
        super().__init__(parent)
        self.bond: Bond = bond
        self.last_price: LastPrice | None = last_price
        self.coupons: list[Coupon] | None = coupons  # Список купонов.
        self.candles: list[HistoricCandle] | None = candles

    @property
    def uid(self) -> str:
        return self.bond.uid

    def instrument(self) -> Bond:
        """Возвращает инструмент (облигацию), хранящийся в классе."""
        return self.bond

    def updateBond(self, bond: Bond):
        """Обновляет облигацию."""
        if not MyBond.__eq__(self.bond, bond):
            self.bond = bond
            self.bondChanged_signal.emit()  # Испускаем сигнал о том, что облигация была изменена.

    def setLastPrice(self, last_price: LastPrice | None):
        """Назначает последнюю цену облигации."""
        if last_price is None:
            if self.last_price is not None:
                self.last_price = last_price
                self.lastPriceChanged_signal.emit()  # Испускаем сигнал о том, что последняя цена была изменена.
        else:
            assert self.bond.uid == last_price.instrument_uid, 'Uid-идентификаторы облигации и последней цены должны совпадать (\'{0}\' и \'{1}\')!'.format(self.bond.uid, last_price.instrument_uid)
            if self.last_price is None:
                self.last_price = last_price
                self.lastPriceChanged_signal.emit()  # Испускаем сигнал о том, что последняя цена была изменена.
            else:
                if not MyLastPrice.__eq__(last_price, self.last_price):
                    self.last_price = last_price
                    self.lastPriceChanged_signal.emit()  # Испускаем сигнал о том, что последняя цена была изменена.

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

    def getCouponIndex(self, coupon_number: int) -> int | None:
        """Находит по coupon_number купон в списке купонов облигации и возвращает его индекс.
        Если купон не найден, то возвращает None."""
        found_coupons_indexes: list[int] = [i for i, cpn in enumerate(self.coupons) if cpn.coupon_number == coupon_number]
        found_coupons_indexes_count: int = len(found_coupons_indexes)  # Количество найденных купонов.
        if found_coupons_indexes_count == 0:
            return None
        elif found_coupons_indexes_count == 1:
            return found_coupons_indexes[0]
        else:
            raise SystemError('Облигация содержит несколько купонов с одинаковым coupon_number ({0})!'.format(self.bond.uid))

    def setCoupons(self, coupons_list: list[Coupon]):
        """Заполняет список купонов."""
        if len(coupons_list) == len(set(cpn.coupon_number for cpn in coupons_list)):
            self.coupons = coupons_list
            self.couponsChanged_signal.emit()  # Испускаем сигнал о том, что купоны были изменены.
        else:
            raise SystemError('Каждый купон облигации должен иметь уникальный номер! Uid = \'{0}\''.format(self.bond.uid))

    def addCoupon(self, coupon: Coupon):
        """Добавляет купон в список купонов."""
        if self.coupons is None:
            self.coupons = [coupon]
            self.couponsChanged_signal.emit()  # Испускаем сигнал о том, что купоны были изменены.
        else:
            found_coupons: list[Coupon] = [cpn for cpn in self.coupons if cpn.coupon_number == coupon.coupon_number]
            found_coupons_count: int = len(found_coupons)  # Количество купонов с таким же номером.
            if found_coupons_count == 0:
                self.coupons.append(coupon)
                self.couponsChanged_signal.emit()  # Испускаем сигнал о том, что купоны были изменены.
            elif found_coupons_count == 1:
                raise SystemError('Облигация \'{0}\' уже содержит купон с таким номером ({1})!'.format(self.bond.uid, coupon.coupon_number))
            else:
                raise SystemError('Облигация \'{0}\' содержит несколько купонов с одним и тем же номером ({1})!'.format(self.bond.uid, coupon.coupon_number))

    def upsertCoupon(self, coupon: Coupon):
        """Обновляет купон из списка купонов облигации, имеющий такой же coupon_number.
        Если такого купона нет, то добавляет купон в список."""
        if self.coupons is None:
            self.coupons = [coupon]
            self.couponsChanged_signal.emit()  # Испускаем сигнал о том, что купоны были изменены.
        else:
            found_coupons_indexes: list[int] = [i for i, cpn in enumerate(self.coupons) if cpn.coupon_number == coupon.coupon_number]
            found_coupons_indexes_count: int = len(found_coupons_indexes)  # Количество купонов с таким же номером.
            if found_coupons_indexes_count == 0:
                self.coupons.append(coupon)
                self.couponsChanged_signal.emit()  # Испускаем сигнал о том, что купоны были изменены.
            elif found_coupons_indexes_count == 1:
                old_coupon_index: int = found_coupons_indexes[0]
                if MyCoupon.__eq__(coupon, self.coupons[old_coupon_index]):
                    return  # Если купоны одинаковы, то нет смысла что-то перезаписывать.
                else:
                    self.coupons[old_coupon_index] = coupon
                    self.couponsChanged_signal.emit()  # Испускаем сигнал о том, что купоны были изменены.
            else:
                raise SystemError('Облигация \'{0}\' содержит несколько купонов с одним и тем же номером ({1})!'.format(self.bond.uid, coupon.coupon_number))

    def removeCoupons(self, coupon_number: int):
        """Удаляет из списка купонов облигации купоны, чей coupon_number равен переданному."""
        begin_coupons_count: int = len(self.coupons)
        i: int = 0
        while i < len(self.coupons):
            if self.coupons[i].coupon_number == coupon_number:
                self.coupons.pop(i)
            else:
                i += 1
        if begin_coupons_count != len(self.coupons):
            self.couponsChanged_signal.emit()  # Испускаем сигнал о том, что купоны были изменены.

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
