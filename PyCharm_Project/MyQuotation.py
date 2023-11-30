from __future__ import annotations
from decimal import Decimal, ROUND_HALF_UP
from tinkoff.invest import Quotation
from tinkoff.invest.utils import quotation_to_decimal, decimal_to_quotation


class MyDecimal:
    """Класс, объединяющий мои функции для класса Decimal."""
    @staticmethod  # Преобразует метод класса в статический метод этого класса.
    def report(decimal_value: Decimal, ndigits: int = -1) -> str:
        """
        ndigits задаёт количество знаков после запятой.
        Если ndigits < 0, то отображает Decimal "как есть".
        Если ndigits == 0, то округляет до целых.
        Если ndigits > 0, то округляет до ndigits знаков после запятой.
        """
        # return '{0:.{1}f}'.format(decimal_value, ndigits)
        if ndigits < 0:
            return str(decimal_value)
        else:
            decimal_str: str = '1'
            if ndigits > 0: decimal_str += '.' + ('0' * ndigits)
            return str(decimal_value.quantize(Decimal(decimal_str), ROUND_HALF_UP))


class MyQuotation(Quotation):
    """Класс Quotation, дополненный функциями."""
    def __init__(self, quotation: Quotation):
        super().__init__(units=quotation.units, nano=quotation.nano)

    def getDecimal(self: Quotation) -> Decimal:
        """Конвертирует Quotation в Decimal."""
        return quotation_to_decimal(self)

    def IsEmpty(self: Quotation) -> bool:
        """Проверяет значение Quotation на равенство нулю."""
        return self.units == 0 and self.nano == 0

    def __mul__(self, other: int | float | Decimal) -> MyQuotation:
        """self * other"""
        # Проверяем тип.
        if not isinstance(other, int | float | Decimal):
            raise ValueError('Quotation можно умножать только на int, float, Decimal и их наследников, а передано {0}!'.format(type(other)))
        value: Decimal = self.getDecimal() * Decimal(other)
        return MyQuotation(decimal_to_quotation(value))

    def __str__(self: Quotation, ndigits: int = -1, delete_decimal_zeros: bool = False) -> str:
        """
        ndigits задаёт максимальное количество знаков после запятой.
        Если ndigits < 0, то отображает Decimal "как есть".
        Если ndigits == 0, то округляет до целых.
        Если ndigits > 0, то округляет до ndigits знаков после запятой.
        Если delete_decimal_zeros == True, то Decimal округляется до первой справа значащей цифры,
        но не до большего количества цифр, чем до ndigits.
        """

        if delete_decimal_zeros:
            """---Определяем количество ненулевых цифр---"""
            fractional_part: int = abs(self.nano)
            number_of_digits: int = 0
            max_count: int = 9 + 1
            for i in range(1, max_count):
                if fractional_part % (10 ** i) > 0:
                    number_of_digits = max_count - i
                    break
            """------------------------------------------"""
            if number_of_digits < ndigits: ndigits = number_of_digits
        return MyDecimal.report(MyQuotation.getDecimal(self), ndigits)

    def __repr__(self: Quotation) -> str:
        return '{0}.{1}'.format(self.units, str(self.nano).zfill(9))
