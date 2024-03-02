import typing
from datetime import datetime
from PyQt6 import QtWidgets, QtCore
from PyQt6.QtCore import QAbstractListModel, QModelIndex, Qt, QVariant, QObject, pyqtSignal
from tinkoff.invest.schemas import RiskLevel, InstrumentStatus
from Classes import TokenClass, MyConnection
from CouponsModel import CouponsModel, CouponsProxyModel
from MyBondClass import MyBondClass
from MyDateTime import getUtcDateTime
from PagesClasses import GroupBox_InstrumentsRequest, GroupBox_CalculationDate, ProgressBar_DataReceiving, TitleLabel, TitleWithCount
from TokenModel import TokenListModel
from new_BondsModel import BondsModel, BondsProxyModel


class GroupBox_CouponsReceiving(QtWidgets.QGroupBox):
    """Панель прогресса получения купонов."""
    def __init__(self, object_name: str, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)
        self.setObjectName(object_name)

        verticalLayout_main = QtWidgets.QVBoxLayout(self)
        verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        verticalLayout_main.setSpacing(2)

        verticalLayout_main.addWidget(TitleLabel(text='ПОЛУЧЕНИЕ КУПОНОВ', parent=self), 0)

        '''-------------------------ProgressBar-------------------------'''
        self.progressBar_coupons = ProgressBar_DataReceiving(parent=self)
        verticalLayout_main.addWidget(self.progressBar_coupons, 0)
        '''-------------------------------------------------------------'''

        '''---------------------------Строка с выбором типа купонов---------------------------'''
        horizontalLayout_coupons_type = QtWidgets.QHBoxLayout()
        horizontalLayout_coupons_type.setSpacing(0)

        self.label_coupons_type = QtWidgets.QLabel(text='Тип купонов:', parent=self)
        self.label_coupons_type.setToolTip('Тип купона.')
        horizontalLayout_coupons_type.addWidget(self.label_coupons_type, 0)

        horizontalLayout_coupons_type.addSpacing(4)

        self.comboBox_coupons_type = QtWidgets.QComboBox(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.comboBox_coupons_type.sizePolicy().hasHeightForWidth())
        self.comboBox_coupons_type.setSizePolicy(sizePolicy)
        self.comboBox_coupons_type.addItem('Любой')
        self.comboBox_coupons_type.addItem('Постоянный')
        self.comboBox_coupons_type.addItem('Фиксированный')
        self.comboBox_coupons_type.addItem('Переменный')
        self.comboBox_coupons_type.addItem('Плавающий')
        self.comboBox_coupons_type.addItem('Дисконт')
        self.comboBox_coupons_type.addItem('Ипотечный')
        self.comboBox_coupons_type.addItem('Прочее')
        self.comboBox_coupons_type.addItem('Неопределённый')
        self.comboBox_coupons_type.addItem('Нет купонов')
        self.comboBox_coupons_type.addItem('Разные купоны')
        horizontalLayout_coupons_type.addWidget(self.comboBox_coupons_type, 0)

        horizontalLayout_coupons_type.addStretch(1)
        '''-----------------------------------------------------------------------------------'''

        verticalLayout_main.addLayout(horizontalLayout_coupons_type, 0)
        verticalLayout_main.addStretch(1)

    def setRange(self, minimum: int, maximum: int):
        """Устанавливает минимум и максимум для progressBar'а."""
        self.progressBar_coupons.setRange(minimum, maximum)

    def setValue(self, value: int):
        """Изменяет прогресс в progressBar'е"""
        self.progressBar_coupons.setValue(value)

    def reset(self):
        """Сбрасывает progressBar."""
        self.progressBar_coupons.reset()


class FilterComboBox(QtWidgets.QComboBox):
    def __init__(self, parameter_name: str, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(sizePolicy)
        self.setObjectName('comboBox_{0}'.format(parameter_name))


class FilterModel(QAbstractListModel):
    class Item:
        def __init__(self, name: str, sql_condition: str | None):
            self.name: str = name
            self.sql_condition: str | None = sql_condition

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent=parent)

        Item = self.Item  # Даём псевдоним классу.
        self._items: tuple[Item, ...] = ()

    def rowCount(self, parent: QModelIndex = ...) -> int:
        return len(self._items)

    def data(self, index: QModelIndex, role: int = ...) -> typing.Any:
        if role == Qt.ItemDataRole.DisplayRole:
            return QVariant(self._items[index.row()].name)
        elif role == Qt.ItemDataRole.UserRole:
            return QVariant(self._items[index.row()].sql_condition)
        else:
            return QVariant()


class BoolFilterComboBox(FilterComboBox):
    class BoolFilterModel(FilterModel):
        def __init__(self, parameter_name: str, parent: QObject | None = None):
            super().__init__(parent=parent)

            Item = self.Item  # Даём псевдоним классу.
            self._items: tuple[Item, Item, Item] = (
                Item('Все', None),
                Item('True', '\"{0}\".\"{1}\" = {2}'.format(MyConnection.BONDS_TABLE, parameter_name, MyConnection.convertBoolToBlob(True))),
                Item('False', '\"{0}\".\"{1}\" = {2}'.format(MyConnection.BONDS_TABLE, parameter_name, MyConnection.convertBoolToBlob(False)))
            )

    def __init__(self, parameter_name: str, parent: QtWidgets.QWidget | None = None):
        super().__init__(parameter_name, parent)  # FilterComboBox __init__().
        model = self.BoolFilterModel(parameter_name, self)
        self.setModel(model)

    def currentCondition(self) -> str | None:
        """Возвращает SQL-условие, соответствующее выбранному в ComboBox значению."""
        # variant: QVariant = self.currentData(Qt.ItemDataRole.UserRole)
        # condition: str | None = variant.value()
        # return condition

        return self.currentData(Qt.ItemDataRole.UserRole)


class CurrencyFilterComboBox(FilterComboBox):
    class CurrencyFilterModel(FilterModel):
        def __init__(self, parameter_name: str, parent: QObject | None = None):
            super().__init__(parent=parent)  # __init__() FilterModel.

            def getAnotherCurrencyCondition(currencies: tuple[str, ...] = ('rub', 'usd', 'eur')) -> str | None:
                """Возвращает SQL-условие, исключающее валюты, переданные в функцию."""
                if currencies:
                    condition: str = ''
                    for currency in currencies:
                        if condition:
                            condition += ' AND '
                        condition += '\"{0}\".\"{1}\" != \'{2}\''.format(MyConnection.BONDS_TABLE, parameter_name, currency)
                    return '({0})'.format(condition)
                else:
                    return None

            Item = self.Item  # Даём псевдоним классу.
            self._items: tuple[Item, ...] = (
                Item('Любая', None),
                Item('rub', '\"{0}\".\"{1}\" = \'{2}\''.format(MyConnection.BONDS_TABLE, parameter_name, 'rub')),
                Item('Иностранная', '\"{0}\".\"{1}\" != \'{2}\''.format(MyConnection.BONDS_TABLE, parameter_name, 'rub')),
                Item('usd', '\"{0}\".\"{1}\" = \'{2}\''.format(MyConnection.BONDS_TABLE, parameter_name, 'usd')),
                Item('eur', '\"{0}\".\"{1}\" = \'{2}\''.format(MyConnection.BONDS_TABLE, parameter_name, 'eur')),
                Item('Другая', getAnotherCurrencyCondition()),
                Item('Мультивалютная', None)
            )

    def __init__(self, parameter_name: str, parent: QtWidgets.QWidget | None = None):
        super().__init__(parameter_name, parent)  # FilterComboBox __init__().
        # self.setEditable(True)

        CurrencyFilterModel = self.CurrencyFilterModel  # Даём псевдоним классу.
        model: CurrencyFilterModel = CurrencyFilterModel(parameter_name, self)
        self.setModel(model)
        self.setCurrentIndex(1)
        self.setMinimumContentsLength(max((len(item.name) for item in model._items)))

    def currentCondition(self) -> str | None:
        """Возвращает SQL-условие, соответствующее выбранному в ComboBox значению."""
        return self.currentData(Qt.ItemDataRole.UserRole)


class RiskFilterComboBox(FilterComboBox):
    class RiskFilterModel(FilterModel):
        def __init__(self, parameter_name: str, parent: QObject | None = None):
            super().__init__(parent=parent)

            Item = self.Item  # Даём псевдоним классу.
            self._items: tuple[Item, ...] = (
                Item('Любой', None),
                Item('Низкий', '\"{0}\".\"{1}\" = \'{2}\''.format(MyConnection.BONDS_TABLE, parameter_name, RiskLevel.RISK_LEVEL_LOW.name)),
                Item('Средний', '\"{0}\".\"{1}\" = \'{2}\''.format(MyConnection.BONDS_TABLE, parameter_name, RiskLevel.RISK_LEVEL_MODERATE.name)),
                Item('Высокий', '\"{0}\".\"{1}\" = \'{2}\''.format(MyConnection.BONDS_TABLE, parameter_name, RiskLevel.RISK_LEVEL_HIGH.name)),
                Item('Неизвестен', '\"{0}\".\"{1}\" = \'{2}\''.format(MyConnection.BONDS_TABLE, parameter_name, RiskLevel.RISK_LEVEL_UNSPECIFIED.name))
            )

    def __init__(self, parameter_name: str, parent: QtWidgets.QWidget | None = None):
        super().__init__(parameter_name, parent)  # FilterComboBox __init__().
        model = self.RiskFilterModel(parameter_name, self)
        self.setModel(model)

    def currentCondition(self) -> str | None:
        """Возвращает SQL-условие, соответствующее выбранному в ComboBox значению."""
        return self.currentData(Qt.ItemDataRole.UserRole)


class MaturityFilterComboBox(FilterComboBox):
    class MaturityFilterModel(FilterModel):
        def __init__(self, parameter_name: str, parent: QObject | None = None):
            super().__init__(parent)  # __init__() FilterModel.

            Item = self.Item  # Даём псевдоним классу.
            self._items: tuple[Item, ...] = (
                Item('Все', None),
                Item('Непогашенные', 'DATETIME(\"{0}\".\"{1}\") >= DATETIME(\'now\')'.format(MyConnection.BONDS_TABLE, parameter_name)),
                Item('Погашенные', 'DATETIME(\"{0}\".\"{1}\") < DATETIME(\'now\')'.format(MyConnection.BONDS_TABLE, parameter_name))
                # Item('Непогашенные', 'DATETIME(\"{0}\".\"{1}\") >= DATETIME(\'{2}\')'.format(MyConnection.BONDS_TABLE, parameter_name, '{0}')),
                # Item('Погашенные', 'DATETIME(\"{0}\".\"{1}\") < DATETIME(\'{2}\')'.format(MyConnection.BONDS_TABLE, parameter_name, '{0}'))
            )

    def __init__(self, parameter_name: str, parent: QtWidgets.QWidget | None = None):
        super().__init__(parameter_name, parent)
        model = self.MaturityFilterModel(parameter_name, self)
        self.setModel(model)
        self.setCurrentIndex(1)

    def currentCondition(self, compared_datetime: datetime = getUtcDateTime()) -> str | None:
        """Возвращает SQL-условие, соответствующее выбранному в ComboBox значению."""
        sql_condition: str | None = self.currentData(Qt.ItemDataRole.UserRole)
        return None if sql_condition is None else sql_condition.format(compared_datetime)


class FilterLabel(QtWidgets.QLabel):
    """Класс для шаблонного создания QLabel на панелях фильтров."""
    def __init__(self, object_name: str, text: str | None, tooltip: str | None, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)
        self.setObjectName(object_name)
        self.setText(text)
        self.setToolTip(tooltip)


class GroupBox_InstrumentsFilters(QtWidgets.QGroupBox):
    """GroupBox с фильтрами инструментов."""
    filtersChanged: pyqtSignal = pyqtSignal()  # Сигнал испускается при изменении фильтров.

    def __init__(self, object_name: str, parent: QtWidgets.QWidget | None = ...):
        super().__init__(parent)
        self.setTitle('Общие фильтры')
        self.setObjectName(object_name)

        self.verticalLayout_main = QtWidgets.QVBoxLayout(self)
        self.verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        self.verticalLayout_main.setSpacing(2)

        self.gridLayout_main = QtWidgets.QGridLayout()
        self.gridLayout_main.setHorizontalSpacing(7)
        self.gridLayout_main.setVerticalSpacing(2)

        """---------------Возможность торговать инструментом через API---------------"""
        self.label_api_trade_available_flag = FilterLabel(object_name='label_api_trade_available_flag',
                                                          text='Доступ API:',
                                                          tooltip='Параметр указывает на возможность торговать инструментом через API.',
                                                          parent=self)
        self.gridLayout_main.addWidget(self.label_api_trade_available_flag, 0, 0, 1, 1)

        self.comboBox_api_trade_available_flag = BoolFilterComboBox('api_trade_available_flag', self)
        self.gridLayout_main.addWidget(self.comboBox_api_trade_available_flag, 0, 1, 1, 1)
        """--------------------------------------------------------------------------"""

        """---------------------Признак доступности для ИИС---------------------"""
        self.label_for_iis_flag = FilterLabel(object_name='label_for_iis_flag',
                                              text='Доступ ИИС:',
                                              tooltip='Признак доступности для ИИС.',
                                              parent=self)
        self.gridLayout_main.addWidget(self.label_for_iis_flag, 1, 0, 1, 1)

        self.comboBox_for_iis_flag = BoolFilterComboBox('for_iis_flag', self)
        self.gridLayout_main.addWidget(self.comboBox_for_iis_flag, 1, 1, 1, 1)
        """---------------------------------------------------------------------"""

        """------Доступность торговли инструментом только для квалифицированных инвесторов------"""
        self.label_for_qual_investor_flag = FilterLabel(object_name='label_for_qual_investor_flag',
                                                        text='Только \"квалы\":',
                                                        tooltip='Флаг отображающий доступность торговли инструментом только для квалифицированных инвесторов.',
                                                        parent=self)
        self.gridLayout_main.addWidget(self.label_for_qual_investor_flag, 2, 0, 1, 1)

        self.comboBox_for_qual_investor_flag = BoolFilterComboBox('for_qual_investor_flag', self)
        self.gridLayout_main.addWidget(self.comboBox_for_qual_investor_flag, 2, 1, 1, 1)
        """-------------------------------------------------------------------------------------"""

        """---------------------Флаг достаточной ликвидности---------------------"""
        self.label_liquidity_flag = FilterLabel(object_name='label_liquidity_flag',
                                                text='Ликвидность:',
                                                tooltip='Флаг достаточной ликвидности.',
                                                parent=self)
        self.gridLayout_main.addWidget(self.label_liquidity_flag, 3, 0, 1, 1)

        self.comboBox_liquidity_flag = BoolFilterComboBox('liquidity_flag', self)
        self.gridLayout_main.addWidget(self.comboBox_liquidity_flag, 3, 1, 1, 1)
        """----------------------------------------------------------------------"""

        """---------------Признак доступности для операций в шорт---------------"""
        self.label_short_enabled_flag = FilterLabel(object_name='label_short_enabled_flag',
                                                    text='Операции в шорт:',
                                                    tooltip='Признак доступности для операций в шорт.',
                                                    parent=self)
        self.gridLayout_main.addWidget(self.label_short_enabled_flag, 4, 0, 1, 1)

        self.comboBox_short_enabled_flag = BoolFilterComboBox('short_enabled_flag', self)
        self.gridLayout_main.addWidget(self.comboBox_short_enabled_flag, 4, 1, 1, 1)
        """---------------------------------------------------------------------"""

        """------------------------Признак доступности для покупки------------------------"""
        self.label_buy_available_flag = FilterLabel(object_name='label_buy_available_flag',
                                                    text='Доступность покупки:',
                                                    tooltip='Признак доступности для покупки.',
                                                    parent=self)
        self.gridLayout_main.addWidget(self.label_buy_available_flag, 0, 2, 1, 1)

        self.comboBox_buy_available_flag = BoolFilterComboBox('buy_available_flag', self)
        self.gridLayout_main.addWidget(self.comboBox_buy_available_flag, 0, 3, 1, 1)
        """-------------------------------------------------------------------------------"""

        """------------------------Признак доступности для продажи------------------------"""
        self.label_sell_available_flag = FilterLabel(object_name='label_sell_available_flag',
                                                     text='Доступность продажи:',
                                                     tooltip='Признак доступности для продажи.',
                                                     parent=self)
        self.gridLayout_main.addWidget(self.label_sell_available_flag, 1, 2, 1, 1)

        self.comboBox_sell_available_flag = BoolFilterComboBox('sell_available_flag', self)
        self.gridLayout_main.addWidget(self.comboBox_sell_available_flag, 1, 3, 1, 1)
        """-------------------------------------------------------------------------------"""

        """------------Доступность торговли инструментом по выходным------------"""
        self.label_weekend_flag = FilterLabel(object_name='label_weekend_flag',
                                              text='Торговля по выходным:',
                                              tooltip='Флаг отображающий доступность торговли инструментом по выходным.',
                                              parent=self)
        self.gridLayout_main.addWidget(self.label_weekend_flag, 2, 2, 1, 1)

        self.comboBox_weekend_flag = BoolFilterComboBox('weekend_flag', self)
        self.gridLayout_main.addWidget(self.comboBox_weekend_flag, 2, 3, 1, 1)
        """---------------------------------------------------------------------"""

        """------------------Признак внебиржевой ценной бумаги------------------"""
        self.label_otc_flag = FilterLabel(object_name='label_otc_flag',
                                          text='Внебиржевая бумага:',
                                          tooltip='Признак внебиржевой ценной бумаги.',
                                          parent=self)
        self.gridLayout_main.addWidget(self.label_otc_flag, 3, 2, 1, 1)

        self.comboBox_otc_flag = BoolFilterComboBox('otc_flag', self)
        self.gridLayout_main.addWidget(self.comboBox_otc_flag, 3, 3, 1, 1)
        """---------------------------------------------------------------------"""

        """---------------------Флаг заблокированного ТКС---------------------"""
        self.label_blocked_tca_flag = FilterLabel(object_name='label_blocked_tca_flag',
                                                  text='Заблокированный ТКС:',
                                                  tooltip='Флаг заблокированного ТКС.',
                                                  parent=self)
        self.gridLayout_main.addWidget(self.label_blocked_tca_flag, 4, 2, 1, 1)

        self.comboBox_blocked_tca_flag = BoolFilterComboBox('blocked_tca_flag', self)
        self.gridLayout_main.addWidget(self.comboBox_blocked_tca_flag, 4, 3, 1, 1)
        """-------------------------------------------------------------------"""

        """----------------------------Валюта----------------------------"""
        self.label_currency = FilterLabel(object_name='label_currency',
                                          text='Валюта:',
                                          tooltip='Валюта расчётов.',
                                          parent=self)
        self.gridLayout_main.addWidget(self.label_currency, 5, 0, 1, 1)

        self.comboBox_currency = CurrencyFilterComboBox('currency', self)
        self.gridLayout_main.addWidget(self.comboBox_currency, 5, 1, 1, 3)
        """--------------------------------------------------------------"""

        self.verticalLayout_main.addLayout(self.gridLayout_main)

        self.filters: dict[str, BoolFilterComboBox | CurrencyFilterComboBox] = {
            'api_trade_available_flag': self.comboBox_api_trade_available_flag,
            'for_iis_flag': self.comboBox_for_iis_flag,
            'for_qual_investor_flag': self.comboBox_for_qual_investor_flag,
            'liquidity_flag': self.comboBox_liquidity_flag,
            'short_enabled_flag': self.comboBox_short_enabled_flag,
            'buy_available_flag': self.comboBox_buy_available_flag,
            'sell_available_flag': self.comboBox_sell_available_flag,
            'weekend_flag': self.comboBox_weekend_flag,
            'otc_flag': self.comboBox_otc_flag,
            'blocked_tca_flag': self.comboBox_blocked_tca_flag,
            'currency': self.comboBox_currency
        }

        for filter in self.filters.values():
            filter.currentIndexChanged.connect(lambda index: self.filtersChanged.emit())

    def getSqlCondition(self) -> str | None:
        condition: str = ''
        for comboBox in self.filters.values():
            current_condition: str | None = comboBox.currentCondition()
            if current_condition is not None:
                if condition:
                    condition += ' AND '
                else:
                    condition += '('
                condition += '{0}'.format(current_condition)
        return '{0})'.format(condition) if condition else None


class GroupBox_OnlyBondsFilters(QtWidgets.QGroupBox):
    """GroupBox с фильтрами облигаций."""
    filtersChanged: pyqtSignal = pyqtSignal()  # Сигнал испускается при изменении фильтров.

    def __init__(self, object_name: str, parent: QtWidgets.QWidget | None = None):
        super().__init__(title='Фильтры облигаций', parent=parent)
        self.setObjectName(object_name)

        verticalLayout_main = QtWidgets.QVBoxLayout(self)
        verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        verticalLayout_main.setSpacing(2)

        self.gridLayout_main = QtWidgets.QGridLayout()
        self.gridLayout_main.setHorizontalSpacing(7)
        self.gridLayout_main.setVerticalSpacing(2)

        """----------------------------Погашенность----------------------------"""
        self.label_maturity = FilterLabel(object_name='label_maturity',
                                          text='Погашенность:',
                                          tooltip='Флаг, отображающий погашенность облигации к текущей дате.',
                                          parent=self)
        self.gridLayout_main.addWidget(self.label_maturity, 0, 0, 1, 1)

        self.comboBox_maturity = MaturityFilterComboBox('maturity_date', self)
        self.gridLayout_main.addWidget(self.comboBox_maturity, 0, 1, 1, 1)
        """--------------------------------------------------------------------"""

        """----------------------------Плавающий купон---------------------------"""
        self.label_floating_coupon_flag = FilterLabel(object_name='label_floating_coupon_flag',
                                                      text='Плавающий купон:',
                                                      tooltip='Признак облигации с плавающим купоном.',
                                                      parent=self)
        self.gridLayout_main.addWidget(self.label_floating_coupon_flag, 0, 2, 1, 1)

        self.comboBox_floating_coupon_flag = BoolFilterComboBox('floating_coupon_flag', self)
        self.gridLayout_main.addWidget(self.comboBox_floating_coupon_flag, 0, 3, 1, 1)
        """----------------------------------------------------------------------"""

        """----------------------------Уровень риска----------------------------"""
        self.label_risk_level = FilterLabel(object_name='label_risk_level',
                                            text='Уровень риска:',
                                            tooltip='Уровень риска.',
                                            parent=self)
        self.gridLayout_main.addWidget(self.label_risk_level, 1, 0, 1, 1)

        self.comboBox_risk_level = RiskFilterComboBox('risk_level', self)
        self.gridLayout_main.addWidget(self.comboBox_risk_level, 1, 1, 1, 1)
        """---------------------------------------------------------------------"""

        """----------------------------Бессрочность----------------------------"""
        self.label_perpetual_flag = FilterLabel(object_name='label_perpetual_flag',
                                                text='Бессрочность:',
                                                tooltip='Признак бессрочной облигации.',
                                                parent=self)
        self.gridLayout_main.addWidget(self.label_perpetual_flag, 1, 2, 1, 1)

        self.comboBox_perpetual_flag = BoolFilterComboBox('perpetual_flag', self)
        self.gridLayout_main.addWidget(self.comboBox_perpetual_flag, 1, 3, 1, 1)
        """--------------------------------------------------------------------"""

        """-----------------------------Амортизация-----------------------------"""
        self.label_amortization_flag = FilterLabel(object_name='label_amortization_flag',
                                                   text='Амортизация:',
                                                   tooltip='Признак облигации с амортизацией долга.',
                                                   parent=self)
        self.gridLayout_main.addWidget(self.label_amortization_flag, 2, 0, 1, 1)

        self.comboBox_amortization_flag = BoolFilterComboBox('amortization_flag', self)
        self.gridLayout_main.addWidget(self.comboBox_amortization_flag, 2, 1, 1, 1)
        """---------------------------------------------------------------------"""

        """-------------------------------Суборд-------------------------------"""
        self.label_subordinated_flag = FilterLabel(object_name='label_subordinated_flag',
                                                   text='Суборд:',
                                                   tooltip='Признак субординированной облигации.',
                                                   parent=self)
        self.gridLayout_main.addWidget(self.label_subordinated_flag, 2, 2, 1, 1)

        self.comboBox_subordinated_flag = BoolFilterComboBox('subordinated_flag', self)
        self.gridLayout_main.addWidget(self.comboBox_subordinated_flag, 2, 3, 1, 1)
        """--------------------------------------------------------------------"""

        verticalLayout_main.addLayout(self.gridLayout_main)

        self.filters: dict[str, BoolFilterComboBox] = {
            'amortization_flag': self.comboBox_amortization_flag,
            'floating_coupon_flag': self.comboBox_floating_coupon_flag,
            'perpetual_flag': self.comboBox_perpetual_flag,
            'subordinated_flag': self.comboBox_subordinated_flag,
            'risk_level': self.comboBox_risk_level,
            'maturity': self.comboBox_maturity
        }

        for filter in self.filters.values():
            filter.currentIndexChanged.connect(lambda index: self.filtersChanged.emit())

    def getSqlCondition(self) -> str | None:
        condition: str = ''
        for comboBox in self.filters.values():
            current_condition: str | None = comboBox.currentCondition()
            if current_condition is not None:
                if condition:
                    condition += ' AND '
                else:
                    condition += '('
                condition += '{0}'.format(current_condition)
        return '{0})'.format(condition) if condition else None


class GroupBox_BondsFilters(QtWidgets.QGroupBox):
    """GroupBox со всеми фильтрами облигаций."""
    filtersChanged: pyqtSignal = pyqtSignal()  # Сигнал испускается при изменении фильтров.

    def __init__(self, object_name: str, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)
        self.setObjectName(object_name)

        self.verticalLayout_main = QtWidgets.QVBoxLayout(self)
        self.verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        self.verticalLayout_main.setSpacing(0)

        """--------------------------Заголовок--------------------------"""
        self.title_widget = TitleWithCount(title='ФИЛЬТРЫ', count_text='0', parent=self)
        self.verticalLayout_main.addLayout(self.title_widget, 0)
        """-------------------------------------------------------------"""

        """---------------------Фильтры инструментов---------------------"""
        self.horizontalLayout_instruments_filters = QtWidgets.QHBoxLayout()
        self.horizontalLayout_instruments_filters.setSpacing(0)

        """---------------------Панель фильтров инструментов---------------------"""
        self.groupBox_instruments_filters = GroupBox_InstrumentsFilters('groupBox_instruments_filters', self)
        self.groupBox_instruments_filters.filtersChanged.connect(self.filtersChanged.emit)
        self.horizontalLayout_instruments_filters.addWidget(self.groupBox_instruments_filters)
        """----------------------------------------------------------------------"""

        self.horizontalLayout_instruments_filters.addStretch(1)

        self.verticalLayout_main.addLayout(self.horizontalLayout_instruments_filters)
        """--------------------------------------------------------------"""

        """----------------------Фильтры облигаций----------------------"""
        horizontalLayout_bond_filters = QtWidgets.QHBoxLayout()
        horizontalLayout_bond_filters.setSpacing(0)

        self.groupBox_bonds_filters = GroupBox_OnlyBondsFilters('groupBox_bonds_filters', self)
        self.groupBox_bonds_filters.filtersChanged.connect(self.filtersChanged.emit)
        horizontalLayout_bond_filters.addWidget(self.groupBox_bonds_filters)

        horizontalLayout_bond_filters.addStretch(1)

        self.verticalLayout_main.addLayout(horizontalLayout_bond_filters)
        """-------------------------------------------------------------"""

    def setCount(self, count: int):
        """Устанавливает количество отобранных облигаций."""
        self.title_widget.setCount(str(count))

    def getSqlCondition(self) -> str | None:
        instruments_condition: str | None = self.groupBox_instruments_filters.getSqlCondition()
        bonds_condition: str | None = self.groupBox_bonds_filters.getSqlCondition()
        if instruments_condition is None:
            return bonds_condition
        else:
            if bonds_condition is None:
                return instruments_condition
            else:
                return '{0} AND {1}'.format(instruments_condition, bonds_condition)


class GroupBox_CouponsView(QtWidgets.QGroupBox):
    """Панель отображения купонов облигаций."""
    def __init__(self, object_name: str, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(sizePolicy)
        self.setObjectName(object_name)

        self.verticalLayout_main = QtWidgets.QVBoxLayout(self)
        self.verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        self.verticalLayout_main.setSpacing(2)

        """------------------------Заголовок------------------------"""
        self.horizontalLayout_title = QtWidgets.QHBoxLayout(self)
        self.horizontalLayout_title.setSpacing(0)

        self.horizontalLayout_title.addSpacing(10)
        self.horizontalLayout_title.addStretch(1)

        label_title = TitleLabel(text='КУПОНЫ', parent=self)
        label_title.setStyleSheet('border: none;')
        self.horizontalLayout_title.addWidget(label_title, 0)

        self.label_count = QtWidgets.QLabel(text='0', parent=self)
        self.label_count.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignTrailing | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.horizontalLayout_title.addWidget(self.label_count, 1)

        self.horizontalLayout_title.addSpacing(10)

        self.verticalLayout_main.addLayout(self.horizontalLayout_title, 0)
        """---------------------------------------------------------"""

        """------------------Отображение дивидендов------------------"""
        self.tableView = QtWidgets.QTableView(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.tableView.sizePolicy().hasHeightForWidth())
        self.tableView.setSizePolicy(sizePolicy)
        self.tableView.setStyleSheet('background-color: rgb(255, 255, 255);')
        self.tableView.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.tableView.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.tableView.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tableView.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.tableView.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.tableView.setGridStyle(QtCore.Qt.PenStyle.SolidLine)
        self.tableView.setSortingEnabled(True)
        self.verticalLayout_main.addWidget(self.tableView)
        """----------------------------------------------------------"""

        '''-----------------------Модель купонов-----------------------'''
        coupons_proxy_model: CouponsProxyModel = CouponsProxyModel(self)  # Создаём прокси-модель.
        self.tableView.setModel(coupons_proxy_model)  # Подключаем модель к таблице.
        self.tableView.resizeColumnsToContents()  # Авторазмер столбцов под содержимое.
        '''------------------------------------------------------------'''

    def sourceModel(self) -> CouponsModel:
        """Возвращает исходную модель купонов."""
        return self.tableView.model().sourceModel()

    def setData(self, bond_class: MyBondClass | None):
        """Обновляет данные модели купонов в соответствии с выбранным figi."""
        self.sourceModel().updateData(bond_class)
        self.tableView.resizeColumnsToContents()  # Авторазмер столбцов под содержимое.
        self.label_count.setText(str(self.tableView.model().rowCount()))  # Отображаем количество купонов.


class GroupBox_BondsView(QtWidgets.QGroupBox):
    """Панель отображения облигаций."""
    def __init__(self, object_name: str, token: TokenClass | None, instrument_status: InstrumentStatus,
                 sql_condition: str | None, calculation_dt: datetime, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(sizePolicy)
        self.setBaseSize(QtCore.QSize(0, 0))
        self.setObjectName(object_name)

        self.verticalLayout_main = QtWidgets.QVBoxLayout(self)
        self.verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        self.verticalLayout_main.setSpacing(2)

        '''------------------------Заголовок------------------------'''
        self.horizontalLayout_title = QtWidgets.QHBoxLayout()
        self.horizontalLayout_title.setSpacing(0)

        self.horizontalLayout_title.addSpacing(10)

        self.lineEdit_search = QtWidgets.QLineEdit(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.lineEdit_search.sizePolicy().hasHeightForWidth())
        self.lineEdit_search.setSizePolicy(sizePolicy)
        self.lineEdit_search.setPlaceholderText('Поиск...')
        self.horizontalLayout_title.addWidget(self.lineEdit_search)

        self.horizontalLayout_title.addStretch(1)

        self.horizontalLayout_title.addWidget(TitleLabel(text='ОБЛИГАЦИИ', parent=self), 0)

        self.label_count = QtWidgets.QLabel(text='0 / 0', parent=self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_count.sizePolicy().hasHeightForWidth())
        self.label_count.setSizePolicy(sizePolicy)
        self.label_count.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignTrailing | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.horizontalLayout_title.addWidget(self.label_count)

        self.horizontalLayout_title.addSpacing(10)

        self.horizontalLayout_title.setStretch(1, 1)
        self.horizontalLayout_title.setStretch(2, 1)
        self.horizontalLayout_title.setStretch(4, 2)
        self.verticalLayout_main.addLayout(self.horizontalLayout_title)
        '''---------------------------------------------------------'''

        '''------------------Отображение облигаций------------------'''
        self.tableView = QtWidgets.QTableView(self)
        self.tableView.setEnabled(True)
        self.tableView.setBaseSize(QtCore.QSize(0, 557))
        self.tableView.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tableView.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.tableView.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.tableView.setSortingEnabled(True)
        self.verticalLayout_main.addWidget(self.tableView)
        '''---------------------------------------------------------'''

        '''--------------------------Модель облигаций--------------------------'''
        source_model: BondsModel = BondsModel(token, instrument_status, sql_condition, calculation_dt)
        proxy_model: BondsProxyModel = BondsProxyModel(source_model)  # Создаём прокси-модель.
        self.tableView.setModel(proxy_model)  # Подключаем модель к TableView.
        self.tableView.resizeColumnsToContents()  # Авторазмер столбцов под содержимое.
        '''--------------------------------------------------------------------'''

    def proxyModel(self) -> BondsProxyModel:
        """Возвращает прокси-модель облигаций."""
        proxy_model = self.tableView.model()
        assert type(proxy_model) == BondsProxyModel
        return typing.cast(BondsProxyModel, proxy_model)

    def sourceModel(self) -> BondsModel:
        """Возвращает исходную модель облигаций."""
        return self.proxyModel().sourceModel()

    def updateModel(self, token: TokenClass | None, instrument_status: InstrumentStatus, sql_condition: str | None):
        """Обновляет модель облигаций в соответствии с переданными параметрами."""
        self.sourceModel().update(token, instrument_status, sql_condition)  # Передаём параметры в исходную модель.
        self.tableView.resizeColumnsToContents()  # Авторазмер столбцов под содержимое.
        self.label_count.setText('{0} / {1}'.format(self.sourceModel().rowCount(), self.proxyModel().rowCount()))  # Отображаем количество облигаций.

    def setCalculationDateTime(self, calculation_datetime: datetime):
        """Устанавливает дату расчёта."""
        self.sourceModel().setCalculationDateTime(calculation_datetime)  # Передаём дату расчёта в исходную модель.

        def resizeDependsOnCalculationDateTimeColumns():
            """Подгоняет ширину столбцов под содержимое для столбцов, зависящих от даты расчёта."""
            for i, column in enumerate(self.sourceModel().columns):
                if column.dependsOnDateTime():
                    self.tableView.resizeColumnToContents(i)

        resizeDependsOnCalculationDateTimeColumns()  # Авторазмер столбцов зависящих от даты расчёта под содержимое.


class new_BondsPage(QtWidgets.QWidget):
    """Страница облигаций."""
    def __init__(self, tokens_model: TokenListModel, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)

        '''------------------------Аттрибуты экземпляра класса------------------------'''
        self.__token: TokenClass | None = None
        self.__instrument_status: InstrumentStatus = InstrumentStatus.INSTRUMENT_STATUS_ALL
        '''---------------------------------------------------------------------------'''

        """=======================================Создание UI======================================="""
        self.verticalLayout_main = QtWidgets.QVBoxLayout(self)
        self.verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        self.verticalLayout_main.setSpacing(2)

        self.splitter = QtWidgets.QSplitter(self)
        self.splitter.setOrientation(QtCore.Qt.Orientation.Vertical)

        self.layoutWidget = QtWidgets.QWidget(self.splitter)

        self.verticalLayout_top = QtWidgets.QVBoxLayout(self.layoutWidget)
        self.verticalLayout_top.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_top.setSpacing(2)

        self.horizontalLayout_top_top = QtWidgets.QHBoxLayout()
        self.horizontalLayout_top_top.setSpacing(2)

        """------------------Панель выполнения запроса------------------"""
        self.groupBox_request = GroupBox_InstrumentsRequest('groupBox_request', self.layoutWidget)
        self.horizontalLayout_top_top.addWidget(self.groupBox_request)
        """-------------------------------------------------------------"""

        """--------------Панель прогресса получения купонов--------------"""
        self.groupBox_coupons_receiving = GroupBox_CouponsReceiving('groupBox_coupons_receiving', self.layoutWidget)
        self.horizontalLayout_top_top.addWidget(self.groupBox_coupons_receiving)
        self.horizontalLayout_top_top.setStretch(1, 1)
        """--------------------------------------------------------------"""

        self.verticalLayout_top.addLayout(self.horizontalLayout_top_top)

        self.horizontalLayout_top_bottom = QtWidgets.QHBoxLayout()
        self.horizontalLayout_top_bottom.setSpacing(2)

        self.verticalLayout_calendar = QtWidgets.QVBoxLayout()
        self.verticalLayout_calendar.setSpacing(0)

        """---------------------Панель даты расчёта---------------------"""
        self.groupBox_calendar = GroupBox_CalculationDate('groupBox_calendar', self.layoutWidget)
        self.verticalLayout_calendar.addWidget(self.groupBox_calendar)
        """-------------------------------------------------------------"""

        self.verticalLayout_calendar.addSpacerItem(QtWidgets.QSpacerItem(20, 2, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding))

        self.verticalLayout_calendar.setStretch(1, 1)
        self.horizontalLayout_top_bottom.addLayout(self.verticalLayout_calendar)

        self.verticalLayout_filters = QtWidgets.QVBoxLayout()
        self.verticalLayout_filters.setSpacing(0)

        """-----------------------Панель фильтров-----------------------"""
        self.groupBox_filters: GroupBox_BondsFilters = GroupBox_BondsFilters('groupBox_filters', self.layoutWidget)
        self.verticalLayout_filters.addWidget(self.groupBox_filters)
        """-------------------------------------------------------------"""

        """Аттрибут self.__sql_condition не относится к UI, но он должен быть инициализирован после
        панели фильтров и перед панелью отображения облигаций."""
        self.__sql_condition: str | None = self.groupBox_filters.getSqlCondition()

        self.verticalLayout_filters.addSpacerItem(QtWidgets.QSpacerItem(20, 0, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding))

        self.horizontalLayout_top_bottom.addLayout(self.verticalLayout_filters)

        """------------------Панель отображения купонов------------------"""
        self.groupBox_coupons: GroupBox_CouponsView = GroupBox_CouponsView('groupBox_coupons', self.layoutWidget)
        self.horizontalLayout_top_bottom.addWidget(self.groupBox_coupons)
        self.horizontalLayout_top_bottom.setStretch(2, 1)
        """--------------------------------------------------------------"""

        self.verticalLayout_top.addLayout(self.horizontalLayout_top_bottom)
        self.verticalLayout_top.setStretch(1, 1)

        '''-----------------Панель отображения облигаций-----------------'''
        self.groupBox_view: GroupBox_BondsView = GroupBox_BondsView('groupBox_view', self.token, self.instrument_status,
                                                                    self.sql_condition,
                                                                    self.groupBox_calendar.getDateTime(), self.splitter)
        '''--------------------------------------------------------------'''

        self.verticalLayout_main.addWidget(self.splitter)
        """========================================================================================="""

        self.groupBox_request.currentTokenChanged.connect(lambda token, instrument_status: self.__setToken(token))
        self.groupBox_request.currentTokenReset.connect(lambda: self.__setToken(None))
        self.groupBox_request.currentStatusChanged.connect(self.__setInstrumentStatus)

        self.groupBox_filters.filtersChanged.connect(lambda: self.__setSqlCondition(self.groupBox_filters.getSqlCondition()))
        self.groupBox_calendar.calendarWidget.selectionChanged.connect(lambda: self.groupBox_view.setCalculationDateTime(self.groupBox_calendar.getDateTime()))
        self.groupBox_view.tableView.selectionModel().currentRowChanged.connect(lambda current, previous: self.groupBox_coupons.setData(self.groupBox_view.proxyModel().getBond(current)))  # Событие смены строки таблицы.

        self.groupBox_request.comboBox_token.setModel(tokens_model)  # Устанавливает модель токенов для ComboBox'а.

    '''-------------------------------------Токен-------------------------------------'''
    def __getToken(self) -> TokenClass | None:
        return self.__token

    def __setToken(self, token: TokenClass | None):
        self.__token = token
        self.groupBox_view.updateModel(self.token, self.instrument_status, self.sql_condition)  # Задаём параметры запроса к БД.

    token = property(__getToken, __setToken)
    '''-------------------------------------------------------------------------------'''

    '''------------------------------Статус инструментов------------------------------'''
    def __getInstrumentStatus(self) -> InstrumentStatus:
        return self.__instrument_status

    def __setInstrumentStatus(self, instrument_status: InstrumentStatus):
        self.__instrument_status = instrument_status
        self.groupBox_view.updateModel(self.token, self.instrument_status, self.sql_condition)  # Задаём параметры запроса к БД.

    instrument_status = property(__getInstrumentStatus, __setInstrumentStatus)
    '''-------------------------------------------------------------------------------'''

    '''---------------------------Свойство условий фильтров---------------------------'''
    def __getSqlCondition(self) -> str | None:
        return self.__sql_condition

    def __setSqlCondition(self, sql_condition: str | None):
        self.__sql_condition = sql_condition
        self.groupBox_view.updateModel(self.token, self.instrument_status, self.sql_condition)  # Задаём параметры запроса к БД.

    sql_condition = property(__getSqlCondition, __setSqlCondition)
    '''-------------------------------------------------------------------------------'''
