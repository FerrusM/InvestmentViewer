from datetime import datetime
from PyQt6.QtCore import Qt
from tinkoff.invest import Account, AccessLevel, AccountType, AccountStatus
from LimitClasses import MyUnaryLimit, MyStreamLimit, UnaryLimitsManager


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

    def __call__(self, data, role: int = Qt.ItemDataRole.UserRole):
        match role:
            case Qt.ItemDataRole.UserRole:
                if self.getData is None: return None
                return self.getData(data)
            case Qt.ItemDataRole.DisplayRole:
                if self.getDisplay is None: return None
                return self.getDisplay(data)
            case Qt.ItemDataRole.BackgroundRole:
                if self.getBackground is None: return None
                return self.getBackground(data)
            case Qt.ItemDataRole.ForegroundRole:
                if self.getForeground is None: return None
                return self.getForeground(data)


class TokenClass:
    """Мой класс для хранения всей информации, связанной с токеном."""
    def __init__(self, token: str, accounts: list[Account], unary_limits: list[MyUnaryLimit], stream_limits: list[MyStreamLimit], response_datetime: datetime = datetime.now()):
        self.token: str = token
        self.accounts: list[Account] = accounts  # Список аккаунтов.
        self.unary_limits: list[MyUnaryLimit] = unary_limits  # Unary-лимиты.

        self.unary_limits_manager: UnaryLimitsManager = UnaryLimitsManager(self.unary_limits)  # Менеджер unary-лимитов.

        self.stream_limits: list[MyStreamLimit] = stream_limits  # Stream-лимиты.
        self.response_datetime: datetime = response_datetime


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
