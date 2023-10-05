from datetime import datetime
from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt
from tinkoff.invest import Account, AccessLevel, AccountType, AccountStatus, SecurityTradingStatus
from LimitClasses import MyUnaryLimit, MyStreamLimit, UnaryLimitsManager


class MyTreeView(QtWidgets.QTreeView):
    def resizeColumnsToContents(self: QtWidgets.QTreeView):
        """Авторазмер всех столбцов TreeView под содержимое."""
        for i in range(self.model().columnCount()):
            self.resizeColumnToContents(i)  # Авторазмер i-го столбца под содержимое.


class Column:
    """Класс столбца."""
    def __init__(self, header: str | None = None, header_tooltip: str | None = None, data_function=None, display_function=None, tooltip_function=None,
                 background_function=None, foreground_function=None):
        self.header: str | None = header  # Название столбца.
        self.header_tooltip: str | None = header_tooltip  # Подсказка в заголовке.
        self.getData = data_function  # Функция для получения данных.
        self.getDisplay = data_function if display_function is None else display_function  # Функция для отображения данных.
        self.getToolTip = tooltip_function  # Функция для получения подсказки к отображаемым данным.
        self.getBackground = background_function
        self.getForeground = foreground_function

    def __call__(self, role: int = Qt.ItemDataRole.UserRole, *data):
        match role:
            case Qt.ItemDataRole.UserRole:
                if self.getData is None: return None
                return self.getData(*data)
            case Qt.ItemDataRole.DisplayRole:
                if self.getDisplay is None: return None
                return self.getDisplay(*data)
            case Qt.ItemDataRole.BackgroundRole:
                if self.getBackground is None: return None
                return self.getBackground(*data)
            case Qt.ItemDataRole.ForegroundRole:
                if self.getForeground is None: return None
                return self.getForeground(*data)


class TokenClass:
    """Мой класс для хранения всей информации, связанной с токеном."""
    def __init__(self, token: str, accounts: list[Account], unary_limits: list[MyUnaryLimit], stream_limits: list[MyStreamLimit], response_datetime: datetime = datetime.now()):
        self.token: str = token
        self.accounts: list[Account] = accounts  # Список аккаунтов.
        self.unary_limits: list[MyUnaryLimit] = unary_limits  # Unary-лимиты.

        self.unary_limits_manager: UnaryLimitsManager = UnaryLimitsManager(self.unary_limits)  # Менеджер unary-лимитов.

        self.stream_limits: list[MyStreamLimit] = stream_limits  # Stream-лимиты.
        self.response_datetime: datetime = response_datetime


class Filter:
    """Класс фильтра."""
    def __init__(self, comparison_function, filter_value, extraction_function=None):
        self._comparison_function = comparison_function  # Функция сравнения filter_value и извлекаемого значения.
        self._value: str = filter_value  # Значение фильтра на форме.
        self._extraction_function = extraction_function  # Функция извлечения необходимых данных.

    def setValue(self, value: str):
        """Устанавливает значение фильтра."""
        self._value = value  # Устанавливает значение фильтра на форме.

    def __call__(self, data) -> bool:
        extracted_data = data if self._extraction_function is None else self._extraction_function(data)
        return self._comparison_function(extracted_data, self._value)


def reportAccountAccessLevel(access_level: AccessLevel) -> str:
    """Расшифровывает уровень доступа к текущему счёту."""
    match access_level:
        case AccessLevel.ACCOUNT_ACCESS_LEVEL_UNSPECIFIED: return 'Уровень доступа не определён.'
        case AccessLevel.ACCOUNT_ACCESS_LEVEL_FULL_ACCESS: return 'Полный доступ к счёту.'
        case AccessLevel.ACCOUNT_ACCESS_LEVEL_READ_ONLY: return 'Доступ с уровнем прав "только чтение".'
        case AccessLevel.ACCOUNT_ACCESS_LEVEL_NO_ACCESS: return 'Доступ отсутствует.'
        case _: raise ValueError('Неизвестное значение переменной класса AccessLevel ({0})!'.format(access_level))


def reportAccountType(account_type: AccountType) -> str:
    """Расшифровывает тип счёта."""
    match account_type:
        case AccountType.ACCOUNT_TYPE_UNSPECIFIED: return 'Тип аккаунта не определён.'
        case AccountType.ACCOUNT_TYPE_TINKOFF: return 'Брокерский счёт Тинькофф.'
        case AccountType.ACCOUNT_TYPE_TINKOFF_IIS: return 'ИИС счёт.'
        case AccountType.ACCOUNT_TYPE_INVEST_BOX: return 'Инвесткопилка.'
        case _: raise ValueError('Неизвестное значение переменной класса AccountType ({0})!'.format(account_type))


def reportAccountStatus(account_status: AccountStatus) -> str:
    """Расшифровывает статус счёта."""
    match account_status:
        case AccountStatus.ACCOUNT_STATUS_UNSPECIFIED: return 'Статус счёта не определён.'
        case AccountStatus.ACCOUNT_STATUS_NEW: return 'Новый, в процессе открытия.'
        case AccountStatus.ACCOUNT_STATUS_OPEN: return 'Открытый и активный счёт.'
        case AccountStatus.ACCOUNT_STATUS_CLOSED: return 'Закрытый счёт.'
        case _: raise ValueError('Неизвестное значение переменной класса AccountStatus ({0})!'.format(account_status))


def reportTradingStatus(trading_status: int) -> str:
    """Расшифровывает режим торгов инструмента."""
    match trading_status:
        case SecurityTradingStatus.SECURITY_TRADING_STATUS_UNSPECIFIED:
            return "Торговый статус не определён"
        case SecurityTradingStatus.SECURITY_TRADING_STATUS_NOT_AVAILABLE_FOR_TRADING:
            return "Недоступен для торгов"
        case SecurityTradingStatus.SECURITY_TRADING_STATUS_OPENING_PERIOD:
            return "Период открытия торгов"
        case SecurityTradingStatus.SECURITY_TRADING_STATUS_CLOSING_PERIOD:
            return "Период закрытия торгов"
        case SecurityTradingStatus.SECURITY_TRADING_STATUS_BREAK_IN_TRADING:
            return "Перерыв в торговле"
        case SecurityTradingStatus.SECURITY_TRADING_STATUS_NORMAL_TRADING:
            return "Нормальная торговля"
        case SecurityTradingStatus.SECURITY_TRADING_STATUS_CLOSING_AUCTION:
            return "Аукцион закрытия"
        case SecurityTradingStatus.SECURITY_TRADING_STATUS_DARK_POOL_AUCTION:
            return "Аукцион крупных пакетов"
        case SecurityTradingStatus.SECURITY_TRADING_STATUS_DISCRETE_AUCTION:
            return "Дискретный аукцион"
        case SecurityTradingStatus.SECURITY_TRADING_STATUS_OPENING_AUCTION_PERIOD:
            return "Аукцион открытия"
        case SecurityTradingStatus.SECURITY_TRADING_STATUS_TRADING_AT_CLOSING_AUCTION_PRICE:
            return "Период торгов по цене аукциона закрытия"
        case SecurityTradingStatus.SECURITY_TRADING_STATUS_SESSION_ASSIGNED:
            return "Сессия назначена"
        case SecurityTradingStatus.SECURITY_TRADING_STATUS_SESSION_CLOSE:
            return "Сессия закрыта"
        case SecurityTradingStatus.SECURITY_TRADING_STATUS_SESSION_OPEN:
            return "Сессия открыта"
        case SecurityTradingStatus.SECURITY_TRADING_STATUS_DEALER_NORMAL_TRADING:
            return "Доступна торговля в режиме внутренней ликвидности брокера"
        case SecurityTradingStatus.SECURITY_TRADING_STATUS_DEALER_BREAK_IN_TRADING:
            return "Перерыв торговли в режиме внутренней ликвидности брокера"
        case SecurityTradingStatus.SECURITY_TRADING_STATUS_DEALER_NOT_AVAILABLE_FOR_TRADING:
            return "Недоступна торговля в режиме внутренней ликвидности брокера"
        case _:
            raise ValueError("Некорректный режим торгов инструмента ({0})!".format(trading_status))
