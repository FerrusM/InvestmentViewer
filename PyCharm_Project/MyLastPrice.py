from datetime import datetime
from tinkoff.invest import LastPrice, Quotation
from MyDateTime import ifDateTimeIsEmpty
from MyQuotation import MyQuotation


class MyLastPrice(LastPrice):
    """Класс LastPrice, дополненный функциями."""
    def __init__(self, figi: str, price: Quotation, time: datetime, instrument_uid: str):
        super().__init__(figi=figi, price=price, time=time, instrument_uid=instrument_uid)  # __init__() LastPrice.

    def isEmpty(self: LastPrice):
        """Проверка цены.
        В некоторых случаях метод get_last_prices() возвращает цену облигации равную нулю.
        На самом деле скорее всего о цене просто нет данных. Эта функция определяет критерий наличия данных о цене."""
        empty_time_flag: bool = ifDateTimeIsEmpty(self.time)
        '''------------Проверки------------'''
        empty_price_flag: bool = MyQuotation.IsEmpty(self.price)
        if empty_time_flag:
            assert empty_price_flag, 'Нет данных о времени последней цены, хотя цена ненулевая, instrument_uid={0}!'.format(self.instrument_uid)
        else:
            assert not empty_price_flag, 'Бесплатная облигация? Время цены указано, а цена ноль, instrument_uid={0}!'.format(self.instrument_uid)
        '''--------------------------------'''
        return empty_time_flag

    def __lt__(self: LastPrice, other: LastPrice):
        """self < other"""
        # Проверяем тип.
        if not isinstance(other, LastPrice):
            raise TypeError('Правый операнд должен быть типом LastPrice, а не {0}!'.format(type(other)))
        return self.price < other.price
