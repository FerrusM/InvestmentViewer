from tinkoff.invest import Share, Dividend, LastPrice, AssetFull


class MyShareClass:
    """Мой класс акций."""
    def __init__(self, share: Share, last_price: LastPrice | None = None):
        self.share: Share = share
        self.last_price: LastPrice | None = last_price
        self.dividends: list[Dividend] = []
        self.asset: AssetFull | None = None

    def setDividends(self, dividends: list[Dividend]):
        """Записывает список дивидендов."""
        self.dividends = dividends
