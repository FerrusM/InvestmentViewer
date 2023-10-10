from tinkoff.invest import Share, Dividend, LastPrice, AssetFull

from MyLastPrice import MyLastPrice
from MyMoneyValue import MyMoneyValue


class MyShareClass:
    """Мой класс акций."""
    def __init__(self, share: Share, last_price: LastPrice | None = None):
        self.share: Share = share
        self.last_price: LastPrice | None = last_price
        self.dividends: list[Dividend] = []  # Дивиденды.
        self.asset: AssetFull | None = None

    def setDividends(self, dividends: list[Dividend]):
        """Записывает список дивидендов."""
        self.dividends = dividends

    def getLastPrice(self) -> MyMoneyValue | None:
        """Рассчитывает последнюю цену одной акции."""
        if self.last_price is None: return None
        # Валюта акции содержится как в currency, так и в nominal.currency. Откуда брать валюту?
        return MyMoneyValue(self.share.currency, self.last_price.price)

    def getLotLastPrice(self) -> MyMoneyValue | None:
        """Рассчитывает последнюю цену лота."""
        last_price: MyMoneyValue | None = self.getLastPrice()
        if last_price is None: return None
        return last_price * self.share.lot

    def reportLastPrice(self, ndigits: int = 2, delete_decimal_zeros: bool = False) -> str:
        """Отображает структуру MoneyValue, соответствующую последней цене акции."""
        last_price: MyMoneyValue | None = self.getLastPrice()
        if last_price is None: return 'Нет данных'
        if MyLastPrice.isEmpty(self.last_price): return 'Нет данных'
        return MyMoneyValue.report(last_price, ndigits, delete_decimal_zeros)

    def reportLotLastPrice(self, ndigits: int = 2, delete_decimal_zeros: bool = False) -> str:
        """Отображает структуру MoneyValue, соответствующую последней цене лота акции."""
        last_price: MyMoneyValue | None = self.getLastPrice()
        if last_price is None: return 'Нет данных'
        if MyLastPrice.isEmpty(self.last_price): return 'Нет данных'
        return MyMoneyValue.report(last_price * self.share.lot, ndigits, delete_decimal_zeros)
