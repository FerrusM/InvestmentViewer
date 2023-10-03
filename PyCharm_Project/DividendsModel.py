import typing
from PyQt6.QtCore import QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt
from tinkoff.invest import Dividend
from Classes import Column
from MyDateTime import reportSignificantInfoFromDateTime
from MyQuotation import MyQuotation
from MyMoneyValue import MyMoneyValue


class DividendsModel(QAbstractTableModel):
    """Модель для отображения дивидендов акций."""
    def __init__(self):
        super().__init__()  # __init__() QAbstractTableModel.
        self.dividends: list[Dividend] = []
        self.columns: tuple[Column, ...] = (
            Column(header='Величина',
                   header_tooltip='Величина дивиденда на 1 ценную бумагу (включая валюту).',
                   data_function=lambda dividend: dividend.dividend_net,
                   display_function=lambda dividend: MyMoneyValue.report(dividend.dividend_net, 2)),
            Column(header='Фактические выплаты',
                   header_tooltip='Дата фактических выплат в часовом поясе UTC.',
                   data_function=lambda dividend: dividend.payment_date,
                   display_function=lambda dividend: reportSignificantInfoFromDateTime(dividend.payment_date)),
            Column(header='Дата объявления',
                   header_tooltip='Дата объявления дивидендов в часовом поясе UTC.',
                   data_function=lambda dividend: dividend.declared_date,
                   display_function=lambda dividend: reportSignificantInfoFromDateTime(dividend.declared_date)),
            Column(header='Последний день',
                   header_tooltip='Последний день (включительно) покупки для получения выплаты в часовом поясе UTC.',
                   data_function=lambda dividend: dividend.last_buy_date,
                   display_function=lambda dividend: reportSignificantInfoFromDateTime(dividend.last_buy_date)),
            Column(header='Тип выплаты',
                   header_tooltip='Тип выплаты.',
                   data_function=lambda dividend: dividend.dividend_type,
                   display_function=lambda dividend: dividend.dividend_type),
            Column(header='Фиксация реестра',
                   header_tooltip='Дата фиксации реестра в часовом поясе UTC.',
                   data_function=lambda dividend: dividend.record_date,
                   display_function=lambda dividend: reportSignificantInfoFromDateTime(dividend.record_date)),
            Column(header='Регулярность',
                   header_tooltip='Регулярность выплаты.',
                   data_function=lambda dividend: dividend.regularity,
                   display_function=lambda dividend: dividend.regularity),
            Column(header='Цена закрытия',
                   header_tooltip='Цена закрытия инструмента на момент ex_dividend_date.',
                   data_function=lambda dividend: dividend.close_price,
                   display_function=lambda dividend: MyMoneyValue.report(dividend.close_price, 2)),
            Column(header='Доходность',
                   header_tooltip='Величина доходности.',
                   data_function=lambda dividend: dividend.yield_value,
                   display_function=lambda dividend: MyQuotation.report(dividend.yield_value, 2)),
            Column(header='Создание записи',
                   header_tooltip='Дата и время создания записи в часовом поясе UTC.',
                   data_function=lambda dividend: dividend.created_at,
                   display_function=lambda dividend: dividend.created_at.strftime('%d.%m.%Y %H:%M:%S'))
        )

    def updateData(self, dividends: list[Dividend]):
        self.beginResetModel()  # Начинает операцию сброса модели.
        self.dividends = dividends
        self.endResetModel()  # Завершает операцию сброса модели.

    def data(self, index: QModelIndex, role: int = ...) -> typing.Any:
        column: Column = self.columns[index.column()]
        dividend: Dividend = self.dividends[index.row()]
        return column(role, dividend)

    def rowCount(self, parent: QModelIndex = ...) -> int:
        """Возвращает количество строк."""
        return len(self.dividends)

    def columnCount(self, parent: QModelIndex = ...) -> int:
        """Возвращает количество столбцов."""
        return len(self.columns)


class DividendsProxyModel(QSortFilterProxyModel):
    """Моя прокси-модель дивидендов."""
    def headerData(self, section: int, orientation: Qt.Orientation, role: int = ...):
        """Функция headerData объявлена в прокси-модели, чтобы названия строк не сортировались вместе с данными."""
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Vertical: return section + 1  # Проставляем номера строк.
            if orientation == Qt.Orientation.Horizontal: return self.sourceModel().columns[section].header
        elif role == Qt.ItemDataRole.ToolTipRole:  # Подсказки.
            if orientation == Qt.Orientation.Horizontal: return self.sourceModel().columns[section].header_tooltip
