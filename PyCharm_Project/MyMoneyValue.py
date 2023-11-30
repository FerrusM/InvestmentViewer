from __future__ import annotations
from decimal import Decimal
from tinkoff.invest import MoneyValue, Quotation
from tinkoff.invest.utils import quotation_to_decimal
from MyQuotation import MyQuotation


class MyMoneyValue(MoneyValue):
    """Класс MoneyValue, дополненный функциями."""
    def __init__(self, currency: str, value: Quotation = Quotation(units=0, nano=0)):
        self.currency: str = currency  # Валюта.
        self._setQuotation(value)  # Задаёт котировку.

    def _setQuotation(self, value: Quotation):
        """Задаёт котировку."""
        self.units: int = value.units
        self.nano: int = value.nano

    def getQuotation(self: MoneyValue) -> Quotation:
        """Возвращает котировку Quotation."""
        return Quotation(units=self.units, nano=self.nano)

    def getMyQuotation(self: MoneyValue) -> MyQuotation:
        """Возвращает котировку MyQuotation."""
        return MyQuotation(MyMoneyValue.getQuotation(self))

    def getDecimal(self: MoneyValue) -> Decimal:
        """Конвертирует MyMoneyValue в Decimal."""
        return quotation_to_decimal(MyMoneyValue.getQuotation(self))

    @staticmethod  # Преобразует метод класса в статический метод этого класса.
    def __checkOtherType(other):
        # Проверяем тип.
        if not isinstance(other, MoneyValue):
            raise TypeError("Правый операнд должен быть типом MoneyValue, а не {}!".format(type(other)))

    def __checkOther(self, other):
        """Проверка other."""
        self.__checkOtherType(other)  # Проверяем тип.
        # Проверяем валюту.
        if other.currency != self.currency:
            raise ValueError("MoneyValue должны иметь одну и ту же валюту: ({0} и {1})!".format(self.currency, other.currency))

    def __sub__(self, other: MoneyValue):
        """self - other"""
        self.__checkOther(other)  # Проверка other.
        return MyMoneyValue(self.currency, (self.getQuotation() - MyMoneyValue.getQuotation(other)))

    def __iadd__(self, other: MoneyValue) -> MyMoneyValue:
        """self += other"""
        self.__checkOther(other)  # Проверка other.
        self._setQuotation(self.getQuotation() + MyMoneyValue.getQuotation(other))  # Задаёт котировку.
        return self

    def __isub__(self, other: MoneyValue) -> MyMoneyValue:
        """self -= other"""
        self.__checkOther(other)  # Проверка other.
        self._setQuotation(self.getQuotation() - MyMoneyValue.getQuotation(other))  # Задаёт котировку.
        return self

    def __mul__(self, other) -> MyMoneyValue:
        """self * other"""
        # Проверяем тип.
        if not isinstance(other, int | float | Decimal):
            raise ValueError('MoneyValue можно умножать только на int, float, Decimal и их наследников, а передано {0}!'.format(type(other)))
        return MyMoneyValue(self.currency, (self.getMyQuotation() * other))

    def __truediv__(self, other: MoneyValue) -> Decimal:
        """self / other"""
        self.__checkOther(other)  # Проверка other.
        return self.getDecimal() / MyMoneyValue.getDecimal(other)

    def __lt__(self: MoneyValue, other: MoneyValue):
        """self < other"""
        MyMoneyValue.__checkOtherType(other)  # Проверяем тип.
        if self.currency == other.currency:
            return MyMoneyValue.getQuotation(self) < MyMoneyValue.getQuotation(other)
        else:
            return self.currency < other.currency

    def __str__(self: MoneyValue, ndigits: int = 2, delete_decimal_zeros: bool = False) -> str:
        return '{0} {1}'.format(MyQuotation.__str__(MyMoneyValue.getQuotation(self), ndigits, delete_decimal_zeros), self.currency)

    def __repr__(self: MoneyValue) -> str:
        return '{0} {1}'.format(MyMoneyValue.getMyQuotation(self).__repr__(), self.currency)


def ifCurrenciesAreEqual(*currency_tuple) -> bool:
    """Функция возвращает True, если валюты переданных переменных равны, иначе возвращает False."""
    # Функция может сравнивать только классы str и MoneyValue
    for element in currency_tuple:
        if not isinstance(element, (str, MoneyValue)): return False
    return len(set((element.currency if isinstance(element, MoneyValue) else element) for element in currency_tuple)) == 1


def MoneyValueToMyMoneyValue(money_value: MoneyValue) -> MyMoneyValue:
    """Конвертирует MoneyValue в MyMoneyValue."""
    return MyMoneyValue(money_value.currency, Quotation(units=money_value.units, nano=money_value.nano))
