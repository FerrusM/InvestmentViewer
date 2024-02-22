from tinkoff.invest import Share, Dividend, LastPrice, HistoricCandle
from MyLastPrice import MyLastPrice
from MyMoneyValue import MyMoneyValue


class MyShareClass:
    """Мой класс акций."""
    def __init__(self, share: Share, last_price: LastPrice | None = None, dividends: list[Dividend] | None = None, candles: list[HistoricCandle] | None = None):
        self.share: Share = share
        self.last_price: LastPrice | None = last_price
        self.__dividends: list[Dividend] | None = dividends  # Дивиденды.
        self.candles: list[HistoricCandle] | None = candles

    @property
    def uid(self) -> str:
        return self.share.uid

    @property
    def dividends(self) -> list[Dividend] | None:
        return self.__dividends

    def setDividends(self, dividends: list[Dividend]):
        """Записывает список дивидендов."""
        self.__dividends = dividends

    def instrument(self) -> Share:
        """Возвращает инструмент (акцию), хранящийся в классе."""
        return self.share

    def getLastPrice(self) -> MyMoneyValue | None:
        """Рассчитывает последнюю цену одной акции."""
        # Валюта акции содержится как в currency, так и в nominal.currency. Откуда брать валюту?
        return None if self.last_price is None else MyMoneyValue(self.share.currency, self.last_price.price)

    def reportLastPrice(self, ndigits: int = 2, delete_decimal_zeros: bool = False) -> str:
        """Отображает структуру MoneyValue, соответствующую последней цене одной акции."""
        last_price: MyMoneyValue | None = self.getLastPrice()
        if last_price is None: return 'Нет данных'
        if MyLastPrice.isEmpty(self.last_price): return 'Нет данных'
        return MyMoneyValue.__str__(last_price, ndigits, delete_decimal_zeros)

    def getLotLastPrice(self) -> MyMoneyValue | None:
        """Рассчитывает последнюю цену лота."""
        last_price: MyMoneyValue | None = self.getLastPrice()
        if last_price is None: return None
        return last_price * self.share.lot

    def reportLotLastPrice(self, ndigits: int = 2, delete_decimal_zeros: bool = False) -> str:
        """Отображает структуру MoneyValue, соответствующую последней цене лота."""
        last_price: MyMoneyValue | None = self.getLastPrice()
        if last_price is None: return 'Нет данных'
        if MyLastPrice.isEmpty(self.last_price): return 'Нет данных'
        return MyMoneyValue.__str__(last_price * self.share.lot, ndigits, delete_decimal_zeros)
