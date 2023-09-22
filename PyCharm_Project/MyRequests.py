from tinkoff.invest import RequestError, Account, Client, UnaryLimit, StreamLimit, GetUserTariffResponse


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

        self.request_occurred: bool = request_occurred
        self.response_data = response_data

        self.exception_flag: bool = exception_flag
        self.exception: Exception | None = exception

        self.request_error_flag: bool = request_error_flag
        self.request_error: RequestError | None = request_error

    def ifDataSuccessfullyReceived(self):
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
            # self.statusbar.clearMessage()  # Очищает statusbar.
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
            # self.statusbar.clearMessage()  # Очищает statusbar.
        request_occurred = True  # Флаг произведённого запроса.
    return MyResponse('get_user_tariff()', request_occurred, (unary_limits, stream_limits), exception_flag, exception, request_error_flag, request_error)
