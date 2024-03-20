from __future__ import annotations
from datetime import datetime
from tinkoff.invest import RequestError, Account, Client, UnaryLimit, StreamLimit, GetUserTariffResponse, \
    InstrumentStatus, Share, LastPrice, Dividend, Bond, InstrumentType, Asset, AssetFull, HistoricCandle, \
    CandleInterval, Coupon
from tinkoff.invest.schemas import GetForecastRequest, GetForecastResponse, GetConsensusForecastsRequest, \
    GetConsensusForecastsResponse, Page
from tinkoff.invest.services import InstrumentsService


class RequestTryClass:
    """Класс для контроля количества попыток получения ответа на запрос."""
    def __init__(self, max_request_try_count: int = -1):
        self.__request_try_count: int = 0  # Количество произведённых попыток запроса.
        self.__max_request_try_count: int = max_request_try_count  # Максимальное количество попыток запроса.

    def __iadd__(self, other: int) -> RequestTryClass:
        """self += other"""
        self.__request_try_count += other
        return self

    def __bool__(self) -> bool:
        """Возвращает True, если количество произведённых попыток запроса меньше максимального, иначе возвращает False.
        Если максимальное количество попыток запроса меньше нуля, то всегда возвращает True."""
        return True if self.__max_request_try_count < 0 else self.__request_try_count < self.__max_request_try_count


class MyResponse:
    """
    Мой класс для возврата результатов запроса.
    request_occurred - если True, то запрос был произведён, иначе False.
    response_data - данные, полученные в ответ на запрос. По умолчанию None.
    exception_flag - флаг наличия исключения. Если False, то запрос был произведён без исключения.
    """
    def __init__(self, method_name: str | None = None, request_occurred: bool | None = None, response_data=None,
                 exception_flag: bool | None = None, exception: Exception | None = None,
                 request_error_flag: bool | None = None, request_error: RequestError | None = None):
        self.method: str | None = method_name

        self.request_occurred: bool | None = request_occurred
        self.response_data = response_data

        self.exception_flag: bool | None = exception_flag
        self.exception: Exception | None = exception

        self.request_error_flag: bool | None = request_error_flag
        self.request_error: RequestError | None = request_error

    def ifDataSuccessfullyReceived(self) -> bool:
        """Возвращает True, если данные были успешно получены. Иначе возвращает False."""
        if not self.exception_flag and not self.request_error_flag and self.request_occurred:
            return True
        else:
            return False


def getAccounts(token: str, show_unauthenticated_error: bool = True) -> MyResponse:
    """Получает и возвращает список счетов."""
    accounts: list[Account] = []
    request_occurred: bool = False  # Флаг произведённого запроса.
    exception_flag: bool | None = None  # Флаг наличия исключения.
    exception: Exception | None = None  # Исключение.
    request_error_flag: bool | None = None  # Флаг наличия RequestError.
    request_error: RequestError | None = None  # RequestError.
    with Client(token) as client:
        try:
            accounts = client.users.get_accounts().accounts
        except RequestError as error:
            request_error_flag = True  # Флаг наличия RequestError.
            request_error = error  # RequestError.
            # if show_unauthenticated_error:
            #     self.showRequestError('get_accounts()', error)  # Отображает исключение RequestError.
            # elif not ifTokenIsUnauthenticated(error):  # Если токен прошёл проверку подлинности.
            #     self.showRequestError('get_accounts()', error)  # Отображает исключение RequestError.
        except Exception as error:
            exception_flag = True  # Флаг наличия исключения.
            exception = error  # Исключение.
            # self.showException('get_accounts()', error)  # Отображает исключение.
        else:  # Если исключения не было.
            exception_flag = False  # Флаг наличия исключения.
            request_error_flag = False  # Флаг наличия RequestError.
        request_occurred = True  # Флаг произведённого запроса.
    return MyResponse('get_accounts()', request_occurred, accounts, exception_flag, exception, request_error_flag, request_error)


def getUserTariff(token: str, show_unauthenticated_error: bool = True) -> MyResponse:
    """Получает и возвращает текущие лимиты пользователя."""
    unary_limits: list[UnaryLimit] = []  # Список лимитов пользователя по unary-запросам.
    stream_limits: list[StreamLimit] = []  # Список лимитов пользователей для stream-соединений.
    request_occurred: bool = False  # Флаг произведённого запроса.
    exception_flag: bool | None = None  # Флаг наличия исключения.
    exception: Exception | None = None  # Исключение.
    request_error_flag: bool | None = None  # Флаг наличия RequestError.
    request_error: RequestError | None = None  # RequestError.
    with Client(token) as client:
        try:
            user_tariff_response: GetUserTariffResponse = client.users.get_user_tariff()
        except RequestError as error:
            request_error_flag = True  # Флаг наличия RequestError.
            request_error = error  # RequestError.
            # if show_unauthenticated_error:
            #     self.showRequestError('get_user_tariff()', error)  # Отображает исключение RequestError.
            # elif not ifTokenIsUnauthenticated(error):  # Если токен прошёл проверку подлинности.
            #     self.showRequestError('get_user_tariff()', error)  # Отображает исключение RequestError.
        except Exception as error:
            exception_flag = True  # Флаг наличия исключения.
            exception = error  # Исключение.
            # self.showException('get_user_tariff()', error)  # Отображает исключение.
        else:  # Если исключения не было.
            unary_limits = user_tariff_response.unary_limits
            stream_limits = user_tariff_response.stream_limits
            exception_flag = False  # Флаг наличия исключения.
            request_error_flag = False  # Флаг наличия RequestError.
        request_occurred = True  # Флаг произведённого запроса.
    return MyResponse('get_user_tariff()', request_occurred, (unary_limits, stream_limits), exception_flag, exception, request_error_flag, request_error)


def getShares(token: str, instrument_status: InstrumentStatus) -> MyResponse:
    """Получает и возвращает список акций."""
    shares_list: list[Share] = []
    request_occurred: bool = False  # Флаг произведённого запроса.
    exception_flag: bool | None = None  # Флаг наличия исключения.
    exception: Exception | None = None  # Исключение.
    request_error_flag: bool | None = None  # Флаг наличия RequestError.
    request_error: RequestError | None = None  # RequestError.
    with Client(token) as client:
        try:
            shares_list = client.instruments.shares(instrument_status=instrument_status).instruments
        except RequestError as error:
            request_error_flag = True  # Флаг наличия RequestError.
            request_error = error  # RequestError.
        except Exception as error:
            exception_flag = True  # Флаг наличия исключения.
            exception = error  # Исключение.
        else:  # Если исключения не было.
            exception_flag = False  # Флаг наличия исключения.
            request_error_flag = False  # Флаг наличия RequestError.
        request_occurred = True  # Флаг произведённого запроса.
    return MyResponse('shares()', request_occurred, shares_list, exception_flag, exception, request_error_flag, request_error)


def getBonds(token: str, instrument_status: InstrumentStatus) -> MyResponse:
    """Получает и возвращает список облигаций."""
    bonds_list: list[Bond] = []
    request_occurred: bool = False  # Флаг произведённого запроса.
    exception_flag: bool | None = None  # Флаг наличия исключения.
    exception: Exception | None = None  # Исключение.
    request_error_flag: bool | None = None  # Флаг наличия RequestError.
    request_error: RequestError | None = None  # RequestError.
    with Client(token) as client:
        try:
            bonds_list = client.instruments.bonds(instrument_status=instrument_status).instruments
        except RequestError as error:
            request_error_flag = True  # Флаг наличия RequestError.
            request_error = error  # RequestError.
        except Exception as error:
            exception_flag = True  # Флаг наличия исключения.
            exception = error  # Исключение.
        else:  # Если исключения не было.
            exception_flag = False  # Флаг наличия исключения.
            request_error_flag = False  # Флаг наличия RequestError.
        request_occurred = True  # Флаг произведённого запроса.
    return MyResponse('bonds()', request_occurred, bonds_list, exception_flag, exception, request_error_flag, request_error)


def getLastPrices(token: str, instrument_uid: list[str] | None = None) -> MyResponse:
    """Получает и возвращает список цен последних сделок."""
    last_prices: list[LastPrice] = []
    request_occurred: bool = False  # Флаг произведённого запроса.
    exception_flag: bool | None = None  # Флаг наличия исключения.
    exception: Exception | None = None  # Исключение.
    request_error_flag: bool | None = None  # Флаг наличия RequestError.
    request_error: RequestError | None = None  # RequestError.
    with Client(token) as client:
        try:
            last_prices = client.market_data.get_last_prices(instrument_id=instrument_uid).last_prices
        except RequestError as error:
            request_error_flag = True  # Флаг наличия RequestError.
            request_error = error  # RequestError.
        except Exception as error:
            exception_flag = True  # Флаг наличия исключения.
            exception = error  # Исключение.
        else:  # Если исключения не было.
            exception_flag = False  # Флаг наличия исключения.
            request_error_flag = False  # Флаг наличия RequestError.
        request_occurred = True  # Флаг произведённого запроса.
    return MyResponse('get_last_prices()', request_occurred, last_prices, exception_flag, exception, request_error_flag, request_error)


def getCoupons(token: str, figi: str = "", from_: datetime | None = None, to: datetime | None = None, instrument_id: str = "") -> MyResponse:
    """Получает и возвращает список купонов облигации."""
    coupons: list[Coupon] = []
    request_occurred: bool = False  # Флаг произведённого запроса.
    exception_flag: bool | None = None  # Флаг наличия исключения.
    exception: Exception | None = None  # Исключение.
    request_error_flag: bool | None = None  # Флаг наличия RequestError.
    request_error: RequestError | None = None  # RequestError.
    with Client(token) as client:
        try:
            coupons = client.instruments.get_bond_coupons(figi=figi, from_=from_, to=to, instrument_id=instrument_id).events
        except RequestError as error:
            request_error_flag = True  # Флаг наличия RequestError.
            request_error = error  # RequestError.
        except Exception as error:
            exception_flag = True  # Флаг наличия исключения.
            exception = error  # Исключение.
        else:  # Если исключения не было.
            exception_flag = False  # Флаг наличия исключения.
            request_error_flag = False  # Флаг наличия RequestError.
        request_occurred = True  # Флаг произведённого запроса.
    return MyResponse('get_bond_coupons()', request_occurred, coupons, exception_flag, exception, request_error_flag, request_error)


def getDividends(token: str, figi: str = "", from_: datetime | None = None, to: datetime | None = None, instrument_id: str = "") -> MyResponse:
    """Получает и возвращает список дивидендов."""
    dividends: list[Dividend] = []
    request_occurred: bool = False  # Флаг произведённого запроса.
    exception_flag: bool | None = None  # Флаг наличия исключения.
    exception: Exception | None = None  # Исключение.
    request_error_flag: bool | None = None  # Флаг наличия RequestError.
    request_error: RequestError | None = None  # RequestError.
    with Client(token) as client:
        try:
            dividends = client.instruments.get_dividends(figi=figi, from_=from_, to=to, instrument_id=instrument_id).dividends
        except RequestError as error:
            request_error_flag = True  # Флаг наличия RequestError.
            request_error = error  # RequestError.
        except Exception as error:
            exception_flag = True  # Флаг наличия исключения.
            exception = error  # Исключение.
        else:  # Если исключения не было.
            exception_flag = False  # Флаг наличия исключения.
            request_error_flag = False  # Флаг наличия RequestError.
        request_occurred = True  # Флаг произведённого запроса.
    return MyResponse('get_dividends()', request_occurred, dividends, exception_flag, exception, request_error_flag, request_error)


def getAssets(token: str, instruments_type: InstrumentType) -> MyResponse:
    """Получает и возвращает список активов."""
    assets: list[Asset] = []
    request_occurred: bool = False  # Флаг произведённого запроса.
    exception_flag: bool | None = None  # Флаг наличия исключения.
    exception: Exception | None = None  # Исключение.
    request_error_flag: bool | None = None  # Флаг наличия RequestError.
    request_error: RequestError | None = None  # RequestError.
    with Client(token) as client:
        try:
            assets = client.instruments.get_assets().assets
        except RequestError as error:
            request_error_flag = True  # Флаг наличия RequestError.
            request_error = error  # RequestError.
        except Exception as error:
            exception_flag = True  # Флаг наличия исключения.
            exception = error  # Исключение.
        else:  # Если исключения не было.
            exception_flag = False  # Флаг наличия исключения.
            request_error_flag = False  # Флаг наличия RequestError.
        request_occurred = True  # Флаг произведённого запроса.
    return MyResponse('get_assets()', request_occurred, assets, exception_flag, exception, request_error_flag, request_error)


def getAssetBy(token: str, asset_uid: str) -> MyResponse:
    """Получает и возвращает данные об активе."""
    asset_full: AssetFull | None = None
    request_occurred: bool = False  # Флаг произведённого запроса.
    exception_flag: bool | None = None  # Флаг наличия исключения.
    exception: Exception | None = None  # Исключение.
    request_error_flag: bool | None = None  # Флаг наличия RequestError.
    request_error: RequestError | None = None  # RequestError.
    with Client(token) as client:
        try:
            asset_full = client.instruments.get_asset_by(id=asset_uid)
        except RequestError as error:
            request_error_flag = True  # Флаг наличия RequestError.
            request_error = error  # RequestError.
        except Exception as error:
            exception_flag = True  # Флаг наличия исключения.
            exception = error  # Исключение.
        else:  # Если исключения не было.
            exception_flag = False  # Флаг наличия исключения.
            request_error_flag = False  # Флаг наличия RequestError.
        request_occurred = True  # Флаг произведённого запроса.
    return MyResponse('get_asset_by()', request_occurred, asset_full, exception_flag, exception, request_error_flag, request_error)


def getCandles(token: str, uid: str, interval: CandleInterval, from_: datetime | None = None, to: datetime | None = None) -> MyResponse:
    """Получает и возвращает список исторических свечей инструмента."""
    candles: list[HistoricCandle] = []
    request_occurred: bool = False  # Флаг произведённого запроса.
    exception_flag: bool | None = None  # Флаг наличия исключения.
    exception: Exception | None = None  # Исключение.
    request_error_flag: bool | None = None  # Флаг наличия RequestError.
    request_error: RequestError | None = None  # RequestError.
    with Client(token) as client:
        try:
            candles = client.market_data.get_candles(from_=from_, to=to, interval=interval, instrument_id=uid).candles
        except RequestError as error:
            request_error_flag = True  # Флаг наличия RequestError.
            request_error = error  # RequestError.
        except Exception as error:
            exception_flag = True  # Флаг наличия исключения.
            exception = error  # Исключение.
        else:  # Если исключения не было.
            exception_flag = False  # Флаг наличия исключения.
            request_error_flag = False  # Флаг наличия RequestError.
        request_occurred = True  # Флаг произведённого запроса.
    return MyResponse(method_name='get_candles()',
                      request_occurred=request_occurred,
                      response_data=candles,
                      exception_flag=exception_flag,
                      exception=exception,
                      request_error_flag=request_error_flag,
                      request_error=request_error)


def getForecast(token: str, uid: str) -> MyResponse:
    """Получает и возвращает прогнозы инвестдомов по инструменту."""
    forecasts: GetForecastResponse | None = None
    request_occurred: bool = False  # Флаг произведённого запроса.
    exception_flag: bool | None = None  # Флаг наличия исключения.
    exception: Exception | None = None  # Исключение.
    request_error_flag: bool | None = None  # Флаг наличия RequestError.
    request_error: RequestError | None = None  # RequestError.
    with Client(token) as client:
        try:
            forecasts = client.instruments.get_forecast_by(request=GetForecastRequest(instrument_id=uid))
        except RequestError as error:
            request_error_flag = True  # Флаг наличия RequestError.
            request_error = error  # RequestError.
        except Exception as error:
            exception_flag = True  # Флаг наличия исключения.
            exception = error  # Исключение.
        else:  # Если исключения не было.
            exception_flag = False  # Флаг наличия исключения.
            request_error_flag = False  # Флаг наличия RequestError.
        request_occurred = True  # Флаг произведённого запроса.
    return MyResponse(method_name=InstrumentsService.get_forecast_by.__name__,
                      request_occurred=request_occurred,
                      response_data=forecasts,
                      exception_flag=exception_flag,
                      exception=exception,
                      request_error_flag=request_error_flag,
                      request_error=request_error)


def getConsensusForecasts(token: str, page: Page | None) -> MyResponse:
    """Получает и возвращает консенсус-прогнозы."""
    forecasts: GetConsensusForecastsResponse | None = None
    request_occurred: bool = False  # Флаг произведённого запроса.
    exception_flag: bool | None = None  # Флаг наличия исключения.
    exception: Exception | None = None  # Исключение.
    request_error_flag: bool | None = None  # Флаг наличия RequestError.
    request_error: RequestError | None = None  # RequestError.
    with Client(token) as client:
        try:
            forecasts = client.instruments.get_consensus_forecasts(request=GetConsensusForecastsRequest(paging=page))
        except RequestError as error:
            request_error_flag = True  # Флаг наличия RequestError.
            request_error = error  # RequestError.
        except Exception as error:
            exception_flag = True  # Флаг наличия исключения.
            exception = error  # Исключение.
        else:  # Если исключения не было.
            exception_flag = False  # Флаг наличия исключения.
            request_error_flag = False  # Флаг наличия RequestError.
        request_occurred = True  # Флаг произведённого запроса.
    return MyResponse(method_name=InstrumentsService.get_consensus_forecasts.__name__,
                      request_occurred=request_occurred,
                      response_data=forecasts,
                      exception_flag=exception_flag,
                      exception=exception,
                      request_error_flag=request_error_flag,
                      request_error=request_error)
