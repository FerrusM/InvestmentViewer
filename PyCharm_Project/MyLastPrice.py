from tinkoff.invest import LastPrice
from MyDateTime import ifDateTimeIsEmpty
from MyQuotation import MyQuotation


class MyLastPrice:
    """Класс, объединяющий функции для работы с классом LastPrice."""
    @staticmethod  # Преобразует метод класса в статический метод этого класса.
    def isEmpty(last_price: LastPrice):
        """Проверка цены.
        В некоторых случаях метод get_last_prices() возвращает цену облигации равную нулю.
        На самом деле скорее всего о цене просто нет данных. Эта функция определяет критерий наличия данных о цене."""
        '''------------Проверки------------'''
        if ifDateTimeIsEmpty(last_price.time) and not MyQuotation.IsEmpty(last_price.price):
            raise ValueError('Нет данных о времени последней цены, хотя цена ненулевая, figi={0}!'.format(last_price.figi))
        if not ifDateTimeIsEmpty(last_price.time) and MyQuotation.IsEmpty(last_price.price):
            raise ValueError('Бесплатная облигация? Время цены указано, а цена ноль, figi={0}!'.format(last_price.figi))
        '''--------------------------------'''
        return ifDateTimeIsEmpty(last_price.time)

    def __lt__(self: LastPrice, other: LastPrice):
        """self < other"""
        # Проверяем тип.
        if not isinstance(other, LastPrice):
            raise TypeError('Правый операнд должен быть типом LastPrice, а не {}!'.format(type(other)))
        return self.price < other.price
