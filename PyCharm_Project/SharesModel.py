import enum
import typing
from PyQt6.QtCore import QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt
from tinkoff.invest import ShareType, MoneyValue
from Classes import Column, reportTradingStatus
from common.datetime_functions import reportSignificantInfoFromDateTime
from MyMoneyValue import MyMoneyValue
from MyQuotation import MyQuotation
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
        case _: raise ValueError('Некорректное значение типа акции ({0})!'.format(share_type))


class SharesModel(QAbstractTableModel):
    """Модель акций."""
    @enum.unique  # Декоратор, требующий, чтобы все элементы имели разные значения.
    class Columns(enum.IntEnum):
        """Перечисление столбцов таблицы акций."""
        SHARE_FIGI = 0
        SHARE_TICKER = 1
        SHARE_ISIN = 2
        SHARE_CURRENCY = 3
        SHARE_NAME = 4
        LOT_LAST_PRICE = 5
        SHARE_LOT = 6
        SHARE_EXCHANGE = 7
        SHARE_IPO_DATE = 8
        SHARE_COUNTRY_OF_RISK_NAME = 9
        SHARE_SECTOR = 10
        SHARE_NOMINAL = 11
        SHARE_DIV_YIELD_FLAG = 12
        SHARE_TYPE = 13
        SHARE_TRADING_STATUS = 14

    def __init__(self):
        super().__init__()  # __init__() QAbstractTableModel.
        self.share_class_list: list[MyShareClass] = []
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
            self.Columns.SHARE_CURRENCY:
                Column(header='Валюта',
                       header_tooltip='Валюта расчётов.',
                       data_function=lambda share_class: share_class.share.currency),
            self.Columns.SHARE_NAME:
                Column(header='Название',
                       header_tooltip='Название инструмента.',
                       data_function=lambda share_class: share_class.share.name),
            self.Columns.LOT_LAST_PRICE:
                Column(header='Цена лота',
                       header_tooltip='Цена последней сделки по лоту акции.',
                       data_function=lambda share_class: share_class.getLotLastPrice(),
                       display_function=lambda share_class: share_class.reportLotLastPrice(),
                       tooltip_function=lambda share_class: 'Нет данных.' if share_class.last_price is None else 'last_price:\nfigi = {0},\nprice = {1},\ntime = {2},\ninstrument_uid = {3}.\n\nlot = {4}'.format(share_class.last_price.figi, MyQuotation.__str__(share_class.last_price.price, 2), share_class.last_price.time, share_class.last_price.instrument_uid, share_class.share.lot)),
            self.Columns.SHARE_LOT:
                Column(header='Лотность',
                       header_tooltip='Лотность инструмента. Возможно совершение операций только на количества ценной бумаги, кратные этому параметру.',
                       data_function=lambda share_class: share_class.share.lot),
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
                       display_function=lambda share_class: MyMoneyValue.__str__(share_class.share.nominal, 2)),
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

    def rowCount(self, parent: QModelIndex = ...) -> int:
        """Возвращает количество акций в модели."""
        return len(self.share_class_list)

    def columnCount(self, parent: QModelIndex = ...) -> int:
        """Возвращает количество столбцов в модели."""
        return len(self.columns)

    def data(self, index: QModelIndex, role: int = ...) -> typing.Any:
        column: Column = self.columns[index.column()]
        share_class: MyShareClass = self.share_class_list[index.row()]
        return column(role, share_class)

    def setShares(self, shares_class_list: list[MyShareClass]):
        """Устанавливает данные модели."""
        self.beginResetModel()  # Начинает операцию сброса модели.
        self.share_class_list = shares_class_list
        self.endResetModel()  # Завершает операцию сброса модели.

    def getShare(self, row: int) -> MyShareClass | None:
        """Возвращает элемент списка данных по его номеру."""
        if 0 <= row < len(self.share_class_list):
            return self.share_class_list[row]
        else:
            return None


class SharesProxyModel(QSortFilterProxyModel):
    """Моя прокси-модель акций."""

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = ...):
        """Функция headerData объявлена в прокси-модели, чтобы названия строк не сортировались вместе с данными."""
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Vertical: return section + 1  # Проставляем номера строк.
            if orientation == Qt.Orientation.Horizontal: return self.sourceModel().columns[section].header
        elif role == Qt.ItemDataRole.ToolTipRole:  # Подсказки.
            if orientation == Qt.Orientation.Horizontal: return self.sourceModel().columns[section].header_tooltip

    def sourceModel(self) -> SharesModel:
        """Возвращает исходную модель."""
        source_model = super().sourceModel()
        assert type(source_model) is SharesModel
        return typing.cast(SharesModel, source_model)

    def getShare(self, proxy_index: QModelIndex) -> MyShareClass | None:
        """Возвращает акцию по индексу элемента."""
        source_index: QModelIndex = self.mapToSource(proxy_index)
        return self.sourceModel().getShare(source_index.row())

    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:
        """Определяет критерий сравнения данных для сортировки."""
        left_data = left.data(role=Qt.ItemDataRole.UserRole)
        right_data = right.data(role=Qt.ItemDataRole.UserRole)
        if isinstance(left_data, MoneyValue) and isinstance(right_data, MoneyValue):
            return MyMoneyValue.__lt__(left_data, right_data)
        elif isinstance(left_data, MoneyValue) and right_data is None:
            return False
        elif left_data is None and isinstance(right_data, MoneyValue):
            return True
        else:
            return super().lessThan(left, right)  # Для всех остальных типов.
