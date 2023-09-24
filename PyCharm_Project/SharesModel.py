import enum
import typing
from PyQt6.QtCore import QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt
from tinkoff.invest import ShareType
from Classes import Column, reportTradingStatus
from MyDateTime import reportSignificantInfoFromDateTime
from MyMoneyValue import MyMoneyValue
from MyShareClass import MyShareClass


def reportShareType(share_type: int):
    """Расшифровывает тип акции."""
    match share_type:
        case ShareType.SHARE_TYPE_UNSPECIFIED: return 'Не определён'
        case ShareType.SHARE_TYPE_COMMON: return 'Обыкновенная'
        case ShareType.SHARE_TYPE_PREFERRED: return 'Привилегированная'
        case ShareType.SHARE_TYPE_ADR: return 'АДР'
        case ShareType.SHARE_TYPE_GDR: return 'ГДР'
        case ShareType.SHARE_TYPE_MLP: return 'ТОО'
        case ShareType.SHARE_TYPE_NY_REG_SHRS: return 'Акции из Нью-Йорка'
        case ShareType.SHARE_TYPE_CLOSED_END_FUND: return 'Закрытый ИФ'
        case ShareType.SHARE_TYPE_REIT: return 'Траст недвижимости'
        case _: raise ValueError("Некорректное значение типа акции ({0})!".format(share_type))


class SharesModel(QAbstractTableModel):
    """Модель акций."""
    @enum.unique  # Декоратор, требующий, чтобы все элементы имели разные значения.
    class Columns(enum.IntEnum):
        """Перечисление столбцов таблицы акций."""
        SHARE_FIGI = 0
        SHARE_TICKER = 1
        SHARE_ISIN = 2
        SHARE_LOT = 3
        SHARE_CURRENCY = 4
        SHARE_NAME = 5
        SHARE_EXCHANGE = 6
        SHARE_IPO_DATE = 7
        SHARE_COUNTRY_OF_RISK_NAME = 8
        SHARE_SECTOR = 9
        SHARE_NOMINAL = 10
        SHARE_DIV_YIELD_FLAG = 11
        SHARE_TYPE = 12
        SHARE_TRADING_STATUS = 13

    def __init__(self):
        super().__init__()  # __init__() QAbstractTableModel.
        self.columns: dict[int, Column] = {
            self.Columns.SHARE_FIGI:
                Column(header='figi',
                       header_tooltip='Figi-идентификатор инструмента.',
                       data_function=lambda share_class: share_class.share.figi),
            self.Columns.SHARE_TICKER:
                Column(header='ticker',
                       header_tooltip='Тикер инструмента.',
                       data_function=lambda share_class: share_class.share.ticker),
            self.Columns.SHARE_ISIN:
                Column(header='isin',
                       header_tooltip='Isin-идентификатор инструмента.',
                       data_function=lambda share_class: share_class.share.isin),
            self.Columns.SHARE_LOT:
                Column(header='Лотность',
                       header_tooltip='Лотность инструмента. Возможно совершение операций только на количества ценной бумаги, кратные этому параметру.',
                       data_function=lambda share_class: share_class.share.lot),
            self.Columns.SHARE_CURRENCY:
                Column(header='Валюта',
                       header_tooltip='Валюта расчётов.',
                       data_function=lambda share_class: share_class.share.currency),
            self.Columns.SHARE_NAME:
                Column(header='Название',
                       header_tooltip='Название инструмента.',
                       data_function=lambda share_class: share_class.share.name),
            self.Columns.SHARE_EXCHANGE:
                Column(header='Торговая площадка',
                       header_tooltip='Торговая площадка.',
                       data_function=lambda share_class: share_class.share.exchange),
            self.Columns.SHARE_IPO_DATE:
                Column(header='Дата IPO',
                       header_tooltip='Дата IPO акции в часовом поясе UTC.',
                       data_function=lambda share_class: share_class.share.ipo_date,
                       display_function=lambda share_class: reportSignificantInfoFromDateTime(share_class.share.ipo_date)),
            self.Columns.SHARE_COUNTRY_OF_RISK_NAME:
                Column(header='Страна риска',
                       header_tooltip='Наименование страны риска, т.е. страны, в которой компания ведёт основной бизнес.',
                       data_function=lambda share_class: share_class.share.country_of_risk_name),
            self.Columns.SHARE_SECTOR:
                Column(header='Сектор',
                       header_tooltip='Сектор экономики.',
                       data_function=lambda share_class: share_class.share.sector),
            self.Columns.SHARE_NOMINAL:
                Column(header='Номинал',
                       header_tooltip='Номинал.',
                       data_function=lambda share_class: share_class.share.nominal,
                       display_function=lambda share_class: MyMoneyValue.report(share_class.share.nominal, 2)),
            self.Columns.SHARE_DIV_YIELD_FLAG:
                Column(header='Дивиденды',
                       header_tooltip='Признак наличия дивидендной доходности.',
                       data_function=lambda share_class: share_class.share.div_yield_flag,
                       display_function=lambda share_class: 'Да' if share_class.share.div_yield_flag else 'Нет'),
            self.Columns.SHARE_TYPE:
                Column(header='Тип акции',
                       header_tooltip='Тип акции.',
                       data_function=lambda share_class: share_class.share.share_type,
                       display_function=lambda share_class: reportShareType(share_class.share.share_type)),
            self.Columns.SHARE_TRADING_STATUS:
                Column(header='Режим торгов',
                       header_tooltip='Текущий режим торгов инструмента.',
                       data_function=lambda share_class: share_class.share.trading_status,
                       display_function=lambda share_class: reportTradingStatus(share_class.share.trading_status)),
        }
        self.share_class_list: list[MyShareClass] = []

    def rowCount(self, parent: QModelIndex = ...) -> int:
        """Возвращает количество акций в модели."""
        return len(self.share_class_list)

    def columnCount(self, parent: QModelIndex = ...) -> int:
        """Возвращает количество столбцов в модели."""
        return len(self.columns)

    def data(self, index: QModelIndex, role: int = ...) -> typing.Any:
        column: Column = self.columns[index.column()]
        share_class: MyShareClass = self.share_class_list[index.row()]
        return column(share_class, role)

    def setShares(self, shares_class_list: list[MyShareClass]):
        """Устанавливает данные модели."""
        self.beginResetModel()
        self.share_class_list = shares_class_list
        self.endResetModel()


class SharesProxyModel(QSortFilterProxyModel):
    """Моя прокси-модель акций."""

    # def __init__(self):
    #     super().__init__()  # __init__() QSortFilterProxyModel.

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = ...):
        """Функция headerData объявлена в прокси-модели, чтобы названия строк не сортировались вместе с данными."""
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Vertical: return section + 1  # Проставляем номера строк.
            if orientation == Qt.Orientation.Horizontal: return self.sourceModel().columns[section].header
        elif role == Qt.ItemDataRole.ToolTipRole:  # Подсказки.
            if orientation == Qt.Orientation.Horizontal: return self.sourceModel().columns[section].header_tooltip
