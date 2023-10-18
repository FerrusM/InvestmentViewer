import typing
from datetime import datetime
from decimal import Decimal
from PyQt6.QtCore import QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt
from PyQt6.QtGui import QBrush
from tinkoff.invest import Coupon, CouponType
from Classes import Column
from MyBondClass import MyBondClass, MyCoupon
from MyDateTime import reportSignificantInfoFromDateTime
from MyMoneyValue import MyMoneyValue
from MyQuotation import MyDecimal


def reportCouponType(coupon_type: CouponType) -> str:
    """Расшифровывает тип купона."""
    match coupon_type:
        case CouponType.COUPON_TYPE_UNSPECIFIED: return 'Неопределенное значение'
        case CouponType.COUPON_TYPE_CONSTANT: return 'Постоянный'
        case CouponType.COUPON_TYPE_FLOATING: return 'Плавающий'
        case CouponType.COUPON_TYPE_DISCOUNT: return 'Дисконт'
        case CouponType.COUPON_TYPE_MORTGAGE: return 'Ипотечный'
        case CouponType.COUPON_TYPE_FIX: return 'Фиксированный'
        case CouponType.COUPON_TYPE_VARIABLE: return 'Переменный'
        case CouponType.COUPON_TYPE_OTHER: return 'Прочее'
        case _: raise ValueError('Некорректное значение типа купона ({0})!'.format(coupon_type))


def reportCouponRate(bond_class: MyBondClass, coupon: Coupon | None) -> str:
    """Рассчитывает и отображает ставку купона."""
    coupon_rate: Decimal | None = bond_class.getCouponRate(coupon)
    # return 'None' if coupon_rate is None else '{:.2f}%'.format(coupon_rate*100)
    return 'None' if coupon_rate is None else '{0}%'.format(MyDecimal.report(coupon_rate*100, 2))


class CouponColumn(Column):
    """Класс столбца таблицы купонов."""
    def __init__(self, header: str | None = None, header_tooltip: str | None = None, data_function=None, display_function=None, tooltip_function=None,
                 background_function=lambda bond_class, coupon: QBrush(Qt.GlobalColor.lightGray) if MyCoupon.ifCouponHasBeenPaid(coupon) else None,
                 foreground_function=None, date_dependence: bool = False, calculation_datetime: datetime | None = None):
        super().__init__(header, header_tooltip, data_function, display_function, tooltip_function, background_function, foreground_function)
        self._date_dependence: bool = date_dependence  # Флаг зависимости от даты.
        self._calculation_datetime: datetime | None = calculation_datetime  # Дата расчёта.

    def dependsOnEnteredDate(self) -> bool:
        """Возвращает True, если значение столбца зависит от выбранной даты. Иначе возвращает False."""
        return self._date_dependence

    def setDateTime(self, calculation_datetime: datetime):
        """Устанавливает новые дату и время."""
        self._calculation_datetime = calculation_datetime


class CouponsModel(QAbstractTableModel):
    """Модель для отображения купонов облигаций."""
    def __init__(self):
        super().__init__()  # __init__() QAbstractTableModel.
        self._bond_class: MyBondClass | None = None
        self.columns: tuple[CouponColumn, ...] = (
            CouponColumn(header='Дата выплаты',
                         header_tooltip='Дата выплаты купона.',
                         data_function=lambda bond_class, coupon: None if coupon is None else coupon.coupon_date,
                         display_function=lambda bond_class, coupon: None if coupon is None else reportSignificantInfoFromDateTime(coupon.coupon_date)),
            CouponColumn(header='Дата фиксации реестра',
                         header_tooltip='(Опционально) Дата фиксации реестра для выплаты купона.',
                         data_function=lambda bond_class, coupon: None if coupon is None else coupon.fix_date,
                         display_function=lambda bond_class, coupon: None if coupon is None else reportSignificantInfoFromDateTime(coupon.fix_date)),
            CouponColumn(header='Номер',
                         header_tooltip='Номер купона.',
                         data_function=lambda bond_class, coupon: None if coupon is None else coupon.coupon_number),
            CouponColumn(header='Тип купона',
                         header_tooltip='Тип купона.',
                         data_function=lambda bond_class, coupon: None if coupon is None else coupon.coupon_type,
                         display_function=lambda bond_class, coupon: None if coupon is None else reportCouponType(coupon.coupon_type)),
            CouponColumn(header='Выплата на одну облигацию',
                         header_tooltip='Выплата на одну облигацию.',
                         data_function=lambda bond_class, coupon: None if coupon is None else coupon.pay_one_bond,
                         display_function=lambda bond_class, coupon: None if coupon is None else MyMoneyValue.report(coupon.pay_one_bond, 2)),
            CouponColumn(header='Ставка',
                         header_tooltip='Ставка купона.',
                         data_function=lambda bond_class, coupon: bond_class.getCouponRate(coupon),
                         display_function=lambda bond_class, coupon: reportCouponRate(bond_class, coupon)),
            CouponColumn(header='Купонный период в днях',
                         header_tooltip='Купонный период в днях.',
                         data_function=lambda bond_class, coupon: None if coupon is None else coupon.coupon_period),
            CouponColumn(header='Начало купонного периода',
                         header_tooltip='Начало купонного периода.',
                         data_function=lambda bond_class, coupon: None if coupon is None else coupon.coupon_start_date,
                         display_function=lambda bond_class, coupon: None if coupon is None else reportSignificantInfoFromDateTime(coupon.coupon_start_date)),
            CouponColumn(header='Окончание купонного периода',
                         header_tooltip='Окончание купонного периода.',
                         data_function=lambda bond_class, coupon: None if coupon is None else coupon.coupon_end_date,
                         display_function=lambda bond_class, coupon: None if coupon is None else reportSignificantInfoFromDateTime(coupon.coupon_end_date))
        )

    def updateData(self, bond_class: MyBondClass | None):
        """Задаёт новые данные модели."""
        self.beginResetModel()  # Начинает операцию сброса модели.
        self._bond_class = bond_class
        self.endResetModel()  # Завершает операцию сброса модели.

    def rowCount(self, parent: QModelIndex = ...) -> int:
        """Возвращает количество купонов."""
        if self._bond_class is None: return 0  # Если данные не были заданы.
        if self._bond_class.coupons is None: return 0  # Если купоны облигации ещё не были запрошены.
        return len(self._bond_class.coupons)

    def columnCount(self, parent: QModelIndex = ...) -> int:
        """Возвращает количество столбцов в модели."""
        return len(self.columns)

    def data(self, index: QModelIndex, role: int = ...) -> typing.Any:
        if self._bond_class is not None:
            coupon: Coupon | None = self._bond_class.getCoupon(index.row())
            if coupon is not None:
                column: CouponColumn = self.columns[index.column()]
                return column(role, self._bond_class, coupon)


class CouponsProxyModel(QSortFilterProxyModel):
    """Прокси-модель купонов."""
    def headerData(self, section: int, orientation: Qt.Orientation, role: int = ...) -> typing.Any:
        # Функция headerData объявлена в прокси-модели, чтобы
        # названия строк не сортировались вместе с данными.
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Vertical:
                return section + 1  # Номер строки.
            elif orientation == Qt.Orientation.Horizontal:
                return self.sourceModel().columns[section].header  # Заголовок столбца
        elif role == Qt.ItemDataRole.ToolTipRole:  # Подсказки.
            if orientation == Qt.Orientation.Horizontal:
                return self.sourceModel().columns[section].header_tooltip

    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:
        """Определяет критерий сравнения данных для сортировки."""
        left_data = left.data(role=Qt.ItemDataRole.UserRole)
        right_data = right.data(role=Qt.ItemDataRole.UserRole)
        if isinstance(left_data, datetime) and isinstance(right_data, datetime):
            return left_data < right_data
        else:
            return super().lessThan(left, right)  # Для всех остальных типов.
