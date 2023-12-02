import enum
import typing
from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtCore import pyqtSlot, QAbstractListModel, QModelIndex, Qt, QVariant, QObject, pyqtSignal
from tinkoff.invest import Bond
from tinkoff.invest.schemas import RiskLevel, InstrumentStatus
from Classes import TokenClass, MyConnection
from MyBondClass import MyBond
from PagesClasses import GroupBox_InstrumentsRequest, GroupBox_CalculationDate, appFilter_Flag, ProgressBar_DataReceiving
from TokenModel import TokenListModel
from new_BondsModel import BondsModel, BondsProxyModel
from new_CouponsModel import CouponsModel


class GroupBox_CouponsReceiving(QtWidgets.QGroupBox):
    """Панель прогресса получения купонов."""
    def __init__(self, object_name: str, parent: QtWidgets.QWidget | None = ...):
        super().__init__(parent)  # QGroupBox __init__().
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(sizePolicy)
        self.setTitle('')
        self.setObjectName(object_name)

        self.verticalLayout_main = QtWidgets.QVBoxLayout(self)
        self.verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        self.verticalLayout_main.setSpacing(2)
        self.verticalLayout_main.setObjectName('verticalLayout_main')

        _translate = QtCore.QCoreApplication.translate

        '''----------------------------------Заголовок----------------------------------'''
        self.label_title = QtWidgets.QLabel(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_title.sizePolicy().hasHeightForWidth())
        self.label_title.setSizePolicy(sizePolicy)
        self.label_title.setMaximumSize(QtCore.QSize(16777215, 16777215))
        font = QtGui.QFont()
        font.setBold(True)
        self.label_title.setFont(font)
        self.label_title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.label_title.setObjectName('label_title')
        self.label_title.setText(_translate('MainWindow', 'ПОЛУЧЕНИЕ КУПОНОВ'))
        self.verticalLayout_main.addWidget(self.label_title)
        '''-----------------------------------------------------------------------------'''

        '''-------------------------ProgressBar-------------------------'''
        self.progressBar_coupons = ProgressBar_DataReceiving('progressBar_coupons', self)
        self.verticalLayout_main.addWidget(self.progressBar_coupons)
        '''-------------------------------------------------------------'''

        '''---------------------------Строка с выбором типа купонов---------------------------'''
        self.horizontalLayout_coupons_type = QtWidgets.QHBoxLayout()
        self.horizontalLayout_coupons_type.setSpacing(0)
        self.horizontalLayout_coupons_type.setObjectName('horizontalLayout_coupons_type')

        self.label_coupons_type = QtWidgets.QLabel(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_coupons_type.sizePolicy().hasHeightForWidth())
        self.label_coupons_type.setSizePolicy(sizePolicy)
        self.label_coupons_type.setObjectName('label_coupons_type')
        self.label_coupons_type.setToolTip(_translate('MainWindow', 'Тип купона.'))
        self.label_coupons_type.setText(_translate('MainWindow', 'Тип купонов:'))
        self.horizontalLayout_coupons_type.addWidget(self.label_coupons_type)

        spacerItem_1 = QtWidgets.QSpacerItem(4, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_coupons_type.addItem(spacerItem_1)

        self.comboBox_coupons_type = QtWidgets.QComboBox(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.comboBox_coupons_type.sizePolicy().hasHeightForWidth())
        self.comboBox_coupons_type.setSizePolicy(sizePolicy)
        self.comboBox_coupons_type.setStyleSheet('')
        self.comboBox_coupons_type.setObjectName('comboBox_coupons_type')
        self.comboBox_coupons_type.addItem(_translate('MainWindow', 'Любой'))
        self.comboBox_coupons_type.addItem(_translate('MainWindow', 'Постоянный'))
        self.comboBox_coupons_type.addItem(_translate('MainWindow', 'Фиксированный'))
        self.comboBox_coupons_type.addItem(_translate('MainWindow', 'Переменный'))
        self.comboBox_coupons_type.addItem(_translate('MainWindow', 'Плавающий'))
        self.comboBox_coupons_type.addItem(_translate('MainWindow', 'Дисконт'))
        self.comboBox_coupons_type.addItem(_translate('MainWindow', 'Ипотечный'))
        self.comboBox_coupons_type.addItem(_translate('MainWindow', 'Прочее'))
        self.comboBox_coupons_type.addItem(_translate('MainWindow', 'Неопределённый'))
        self.comboBox_coupons_type.addItem(_translate('MainWindow', 'Нет купонов'))
        self.comboBox_coupons_type.addItem(_translate('MainWindow', 'Разные купоны'))
        self.horizontalLayout_coupons_type.addWidget(self.comboBox_coupons_type)

        spacerItem_2 = QtWidgets.QSpacerItem(0, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_coupons_type.addItem(spacerItem_2)
        '''-----------------------------------------------------------------------------------'''

        self.verticalLayout_main.addLayout(self.horizontalLayout_coupons_type)
        self.verticalLayout_main.setStretch(1, 1)

        self.reset()  # Сбрасывает progressBar.

    def setRange(self, minimum: int, maximum: int):
        """Устанавливает минимум и максимум для progressBar'а."""
        self.progressBar_coupons.setRange(minimum, maximum)

    def setValue(self, value: int):
        """Изменяет прогресс в progressBar'е"""
        self.progressBar_coupons.setValue(value)

    def reset(self):
        """Сбрасывает progressBar."""
        self.progressBar_coupons.reset()


class InstrumentFilters:
    class Filter:
        def __init__(self, name: str, value: typing.Any):
            self.name: str = name
            self.value: typing.Any = value

    def __init__(self, api_trade_available_flag: bool | None, for_iis_flag: bool | None,
                 for_qual_investor_flag: bool | None, liquidity_flag: bool | None, short_enabled_flag: bool | None,
                 buy_available_flag: bool | None, sell_available_flag: bool | None, weekend_flag: bool | None,
                 otc_flag: bool | None, blocked_tca_flag: bool | None, currency: str | None):
        Filter = self.Filter  # Даём псевдоним классу.
        # self.filters: list[Filter] = []
        # if api_trade_available_flag is not None:
        #     self.filters.append(Filter('api_trade_available_flag', api_trade_available_flag))
        # if for_iis_flag is not None:
        #     self.filters.append(Filter('for_iis_flag', for_iis_flag))
        # if for_qual_investor_flag is not None:
        #     self.filters.append(Filter('for_qual_investor_flag', for_qual_investor_flag))

        self.filters: tuple[Filter, ...] = (
            Filter('api_trade_available_flag', api_trade_available_flag),
            Filter('for_iis_flag', for_iis_flag),
            Filter('for_qual_investor_flag', for_qual_investor_flag),
            Filter('liquidity_flag', liquidity_flag),
            Filter('short_enabled_flag', short_enabled_flag),
            Filter('buy_available_flag', buy_available_flag),
            Filter('sell_available_flag', sell_available_flag),
            Filter('weekend_flag', weekend_flag),
            Filter('otc_flag', otc_flag),
            Filter('blocked_tca_flag', blocked_tca_flag),
            Filter('currency', currency)
        )

    def indexOf(self, name: str) -> int:
        """Находит и возвращает номер фильтра с переданным именем."""
        index: int = -1
        for i, filter in enumerate(self.filters):
            if name == filter.name:
                if index != -1:
                    raise Exception('Несколько фильтров содержат одно и то же название ({0})!'.format(name))
                index = i
        if index == -1:
            raise ValueError('Нет фильтра с таким названием ({0})!'.format(name))
        return index

    def value(self, name: str):
        """Возвращает значение фильтра с переданным именем."""
        index: int = self.indexOf(name)
        return self.filters[index].name


class BoolFilterComboBox(QtWidgets.QComboBox):
    class BoolFilterModel(QAbstractListModel):
        SQL_CONDITION_ROLE: int = (Qt.ItemDataRole.UserRole + 1)

        class Item:
            def __init__(self, name: str, value: bool | None):
                self.name: str = name
                self.value: bool | None = value

        def __init__(self, parameter_name: str, parent: QObject | None = ...):
            super().__init__(parent)  # __init__() QAbstractListModel.
            self.parameter_name: str = parameter_name

            Item = self.Item  # Даём псевдоним классу.
            self._items: tuple[Item, Item, Item] = (
                Item('Все', None),
                Item('True', True),
                Item('False', False)
            )

        def rowCount(self, parent: QModelIndex = ...) -> int:
            return len(self._items)

        def data(self, index: QModelIndex, role: int = ...) -> typing.Any:
            if role == Qt.ItemDataRole.DisplayRole:
                return QVariant(self._items[index.row()].name)
            elif role == Qt.ItemDataRole.UserRole:
                return QVariant(self._items[index.row()].value)
            elif role == self.SQL_CONDITION_ROLE:
                def sql_condition(row: int) -> str | None:
                    value: bool | None = self._items[row].value
                    if value is None:
                        return None
                    else:
                        return '\"{0}\".\"{1}\" = {2}'.format(
                            MyConnection.BONDS_TABLE, self.parameter_name, MyConnection.convertBoolToBlob(value)
                        )

                return QVariant(sql_condition(index.row()))
            else:
                return QVariant()

    def __init__(self, parameter_name: str, parent: QtWidgets.QWidget | None = ...):
        super().__init__(parent)  # QComboBox __init__().
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(sizePolicy)
        self.setToolTip('')
        self.setObjectName('comboBox_{0}'.format(parameter_name))

        self.parameter_name: str = parameter_name

        BoolFilterModel = self.BoolFilterModel  # Даём псевдоним классу.
        model: BoolFilterModel = BoolFilterModel(self.parameter_name, self)
        self.setModel(model)

    def currentCondition(self) -> str | None:
        # variant: QVariant = self.currentData(self.BoolFilterModel.SQL_CONDITION_ROLE)
        # condition: str | None = variant.value()
        # return condition

        return self.currentData(self.BoolFilterModel.SQL_CONDITION_ROLE)


class GroupBox_InstrumentsFilters(QtWidgets.QGroupBox):
    """GroupBox с фильтрами инструментов."""
    filtersChanged: pyqtSignal = pyqtSignal()  # Сигнал испускается при изменении фильтров.

    @enum.unique  # Декоратор, требующий, чтобы все элементы имели разные значения.
    class Filters(enum.IntEnum):
        """Перечисление фильтров инструментов."""
        # TRADING_STATUS = 1  # Текущий режим торгов инструмента.
        API_ACCESS = 0  # Доступ API.
        IIS_ACCESS = 1  # Доступ ИИС.
        QUAL_INVESTOR = 2  # Торговля инструментом только для квалифицированных инвесторов.
        LIQUIDITY_FLAG = 3  # Флаг достаточной ликвидности.
        SHORT_ENABLE = 4  # Признак доступности для операций в шорт.
        BUY_AVAILABLE = 5  # Признак доступности для покупки.
        SELL_AVAILABLE = 6  # Признак доступности для продажи.
        WEEKEND_FLAG = 7  # Доступность торговли инструментом по выходным.
        OTC_FLAG = 8  # Признак внебиржевой ценной бумаги.
        BLOCKED_TCA = 9  # Флаг заблокированного ТКС.
        CURRENCY = 10  # Валюта расчётов.

    def __init__(self, object_name: str, parent: QtWidgets.QWidget | None = ...):
        super().__init__(parent)  # QGroupBox __init__().
        self.setObjectName(object_name)

        self.verticalLayout_main = QtWidgets.QVBoxLayout(self)
        self.verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        self.verticalLayout_main.setSpacing(2)
        self.verticalLayout_main.setObjectName('verticalLayout_main')

        self.gridLayout_main = QtWidgets.QGridLayout()
        self.gridLayout_main.setHorizontalSpacing(7)
        self.gridLayout_main.setVerticalSpacing(2)
        self.gridLayout_main.setObjectName('gridLayout_main')

        """---------------Возможность торговать инструментом через API---------------"""
        self.label_api_trade_available_flag = QtWidgets.QLabel(self)
        self.label_api_trade_available_flag.setObjectName('label_api_trade_available_flag')
        self.gridLayout_main.addWidget(self.label_api_trade_available_flag, 0, 0, 1, 1)

        self.comboBox_api_trade_available_flag = BoolFilterComboBox('api_trade_available_flag', self)

        self.gridLayout_main.addWidget(self.comboBox_api_trade_available_flag, 0, 1, 1, 1)
        """--------------------------------------------------------------------------"""

        """---------------------Признак доступности для ИИС---------------------"""
        self.label_for_iis_flag = QtWidgets.QLabel(self)
        self.label_for_iis_flag.setObjectName('label_for_iis_flag')
        self.gridLayout_main.addWidget(self.label_for_iis_flag, 1, 0, 1, 1)

        # self.comboBox_for_iis_flag = QtWidgets.QComboBox(self)
        # sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum, QtWidgets.QSizePolicy.Policy.Fixed)
        # sizePolicy.setHorizontalStretch(0)
        # sizePolicy.setVerticalStretch(0)
        # sizePolicy.setHeightForWidth(self.comboBox_for_iis_flag.sizePolicy().hasHeightForWidth())
        # self.comboBox_for_iis_flag.setSizePolicy(sizePolicy)
        # self.comboBox_for_iis_flag.setObjectName('comboBox_for_iis_flag')
        # self.comboBox_for_iis_flag.addItem('')
        # self.comboBox_for_iis_flag.addItem('')
        # self.comboBox_for_iis_flag.addItem('')

        self.comboBox_for_iis_flag = BoolFilterComboBox('for_iis_flag', self)

        self.gridLayout_main.addWidget(self.comboBox_for_iis_flag, 1, 1, 1, 1)
        """---------------------------------------------------------------------"""

        """------Доступность торговли инструментом только для квалифицированных инвесторов------"""
        self.label_for_qual_investor_flag = QtWidgets.QLabel(self)
        self.label_for_qual_investor_flag.setObjectName('label_for_qual_investor_flag')
        self.gridLayout_main.addWidget(self.label_for_qual_investor_flag, 2, 0, 1, 1)

        self.comboBox_for_qual_investor_flag = BoolFilterComboBox('for_qual_investor_flag', self)

        self.gridLayout_main.addWidget(self.comboBox_for_qual_investor_flag, 2, 1, 1, 1)
        """-------------------------------------------------------------------------------------"""

        """---------------------Флаг достаточной ликвидности---------------------"""
        self.label_liquidity_flag = QtWidgets.QLabel(self)
        self.label_liquidity_flag.setObjectName('label_liquidity_flag')
        self.gridLayout_main.addWidget(self.label_liquidity_flag, 3, 0, 1, 1)

        self.comboBox_liquidity_flag = BoolFilterComboBox('liquidity_flag', self)

        self.gridLayout_main.addWidget(self.comboBox_liquidity_flag, 3, 1, 1, 1)
        """----------------------------------------------------------------------"""

        """---------------Признак доступности для операций в шорт---------------"""
        self.label_short_enabled_flag = QtWidgets.QLabel(self)
        self.label_short_enabled_flag.setObjectName('label_short_enabled_flag')
        self.gridLayout_main.addWidget(self.label_short_enabled_flag, 4, 0, 1, 1)

        self.comboBox_short_enabled_flag = BoolFilterComboBox('short_enabled_flag', self)

        self.gridLayout_main.addWidget(self.comboBox_short_enabled_flag, 4, 1, 1, 1)
        """---------------------------------------------------------------------"""

        """------------------------Признак доступности для покупки------------------------"""
        self.label_buy_available_flag = QtWidgets.QLabel(self)
        self.label_buy_available_flag.setObjectName('label_buy_available_flag')
        self.gridLayout_main.addWidget(self.label_buy_available_flag, 0, 2, 1, 1)

        self.comboBox_buy_available_flag = BoolFilterComboBox('buy_available_flag', self)

        self.gridLayout_main.addWidget(self.comboBox_buy_available_flag, 0, 3, 1, 1)
        """-------------------------------------------------------------------------------"""

        """------------------------Признак доступности для продажи------------------------"""
        self.label_sell_available_flag = QtWidgets.QLabel(self)
        self.label_sell_available_flag.setObjectName('label_sell_available_flag')
        self.gridLayout_main.addWidget(self.label_sell_available_flag, 1, 2, 1, 1)

        self.comboBox_sell_available_flag = BoolFilterComboBox('sell_available_flag', self)

        self.gridLayout_main.addWidget(self.comboBox_sell_available_flag, 1, 3, 1, 1)
        """-------------------------------------------------------------------------------"""

        """------------Доступность торговли инструментом по выходным------------"""
        self.label_weekend_flag = QtWidgets.QLabel(self)
        self.label_weekend_flag.setObjectName('label_weekend_flag')
        self.gridLayout_main.addWidget(self.label_weekend_flag, 2, 2, 1, 1)

        self.comboBox_weekend_flag = BoolFilterComboBox('weekend_flag', self)

        self.gridLayout_main.addWidget(self.comboBox_weekend_flag, 2, 3, 1, 1)
        """---------------------------------------------------------------------"""

        """------------------Признак внебиржевой ценной бумаги------------------"""
        self.label_otc_flag = QtWidgets.QLabel(self)
        self.label_otc_flag.setObjectName("label_otc_flag")
        self.gridLayout_main.addWidget(self.label_otc_flag, 3, 2, 1, 1)

        self.comboBox_otc_flag = BoolFilterComboBox('otc_flag', self)

        self.gridLayout_main.addWidget(self.comboBox_otc_flag, 3, 3, 1, 1)
        """---------------------------------------------------------------------"""

        """---------------------Флаг заблокированного ТКС---------------------"""
        self.label_blocked_tca_flag = QtWidgets.QLabel(self)
        self.label_blocked_tca_flag.setObjectName('label_blocked_tca_flag')
        self.gridLayout_main.addWidget(self.label_blocked_tca_flag, 4, 2, 1, 1)

        self.comboBox_blocked_tca_flag = BoolFilterComboBox('blocked_tca_flag', self)

        self.gridLayout_main.addWidget(self.comboBox_blocked_tca_flag, 4, 3, 1, 1)
        """-------------------------------------------------------------------"""

        """----------------------------Валюта----------------------------"""
        self.label_currency = QtWidgets.QLabel(self)
        self.label_currency.setObjectName('label_currency')
        self.gridLayout_main.addWidget(self.label_currency, 5, 0, 1, 1)

        self.comboBox_currency = QtWidgets.QComboBox(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.comboBox_currency.sizePolicy().hasHeightForWidth())
        self.comboBox_currency.setSizePolicy(sizePolicy)
        self.comboBox_currency.setEditable(True)
        self.comboBox_currency.setObjectName('comboBox_currency')
        self.comboBox_currency.addItem('')
        self.comboBox_currency.addItem('')
        self.comboBox_currency.addItem('')
        self.comboBox_currency.addItem('')
        self.comboBox_currency.addItem('')
        self.comboBox_currency.addItem('')
        self.comboBox_currency.addItem('')
        self.gridLayout_main.addWidget(self.comboBox_currency, 5, 1, 1, 3)
        """--------------------------------------------------------------"""

        self.verticalLayout_main.addLayout(self.gridLayout_main)

        """------------------------------------retranslateUi------------------------------------"""
        _translate = QtCore.QCoreApplication.translate
        self.setTitle(_translate('MainWindow', 'Общие фильтры'))
        self.label_sell_available_flag.setToolTip(_translate('MainWindow', 'Признак доступности для продажи.'))
        self.label_sell_available_flag.setText(_translate('MainWindow', 'Доступность продажи:'))
        self.label_otc_flag.setToolTip(_translate('MainWindow', 'Признак внебиржевой ценной бумаги.'))
        self.label_otc_flag.setText(_translate('MainWindow', 'Внебиржевая бумага:'))
        self.label_weekend_flag.setToolTip(_translate('MainWindow', 'Флаг отображающий доступность торговли инструментом по выходным.'))
        self.label_weekend_flag.setText(_translate('MainWindow', 'Торговля по выходным:'))
        self.label_for_iis_flag.setToolTip(_translate('MainWindow', 'Признак доступности для ИИС.'))
        self.label_for_iis_flag.setText(_translate('MainWindow', 'Доступ ИИС:'))
        self.label_for_qual_investor_flag.setToolTip(_translate('MainWindow', 'Флаг отображающий доступность торговли инструментом только для квалифицированных инвесторов.'))
        self.label_for_qual_investor_flag.setText(_translate('MainWindow', 'Только \"квалы\":'))
        self.label_blocked_tca_flag.setToolTip(_translate('MainWindow', 'Флаг заблокированного ТКС.'))
        self.label_blocked_tca_flag.setText(_translate('MainWindow', 'Заблокированный ТКС:'))
        self.label_buy_available_flag.setToolTip(_translate('MainWindow', 'Признак доступности для покупки.'))
        self.label_buy_available_flag.setText(_translate('MainWindow', 'Доступность покупки:'))
        self.label_short_enabled_flag.setToolTip(_translate('MainWindow', 'Признак доступности для операций в шорт.'))
        self.label_short_enabled_flag.setText(_translate('MainWindow', 'Операции в шорт:'))
        self.label_liquidity_flag.setToolTip(_translate('MainWindow', 'Флаг достаточной ликвидности.'))
        self.label_liquidity_flag.setText(_translate('MainWindow', 'Ликвидность:'))
        self.label_api_trade_available_flag.setToolTip(_translate('MainWindow', 'Параметр указывает на возможность торговать инструментом через API.'))
        self.label_api_trade_available_flag.setText(_translate('MainWindow', 'Доступ API:'))
        self.label_currency.setToolTip(_translate('MainWindow', 'Валюта расчётов.'))
        self.label_currency.setText(_translate('MainWindow', 'Валюта:'))
        self.comboBox_currency.setItemText(0, _translate('MainWindow', 'Любая'))
        self.comboBox_currency.setItemText(1, _translate('MainWindow', 'rub'))
        self.comboBox_currency.setItemText(2, _translate('MainWindow', 'Иностранная'))
        self.comboBox_currency.setItemText(3, _translate('MainWindow', 'usd'))
        self.comboBox_currency.setItemText(4, _translate('MainWindow', 'eur'))
        self.comboBox_currency.setItemText(5, _translate('MainWindow', 'Другая'))
        self.comboBox_currency.setItemText(6, _translate('MainWindow', 'Мультивалютная'))
        """-------------------------------------------------------------------------------------"""

        self.comboBox_currency.setCurrentIndex(1)

        '''---------------------------------Фильтры инструментов---------------------------------'''
        def appFilter_Currency(currency: str, filter: str) -> bool:
            """Проверяет, удовлетворяет ли акция фильтру на валюту."""
            match filter:
                case 'Любая': return True
                case 'Иностранная': return False if currency == 'rub' else True
                case 'Другая': return False if any(currency == current_currency for current_currency in ('rub', 'usd', 'eur')) else True
                case _: return True if currency == filter else False

        self.filters: dict = {
            self.Filters.API_ACCESS:
                lambda instrument: appFilter_Flag(instrument.api_trade_available_flag, self.comboBox_api_trade_available_flag.currentText()),
            self.Filters.IIS_ACCESS:
                lambda instrument: appFilter_Flag(instrument.for_iis_flag, self.comboBox_for_iis_flag.currentText()),
            self.Filters.QUAL_INVESTOR:
                lambda instrument: appFilter_Flag(instrument.for_qual_investor_flag, self.comboBox_for_qual_investor_flag.currentText()),
            self.Filters.LIQUIDITY_FLAG:
                lambda instrument: appFilter_Flag(instrument.liquidity_flag, self.comboBox_liquidity_flag.currentText()),
            self.Filters.SHORT_ENABLE:
                lambda instrument: appFilter_Flag(instrument.short_enabled_flag, self.comboBox_short_enabled_flag.currentText()),
            self.Filters.BUY_AVAILABLE:
                lambda instrument: appFilter_Flag(instrument.buy_available_flag, self.comboBox_buy_available_flag.currentText()),
            self.Filters.SELL_AVAILABLE:
                lambda instrument: appFilter_Flag(instrument.sell_available_flag, self.comboBox_sell_available_flag.currentText()),
            self.Filters.WEEKEND_FLAG:
                lambda instrument: appFilter_Flag(instrument.weekend_flag, self.comboBox_weekend_flag.currentText()),
            self.Filters.OTC_FLAG:
                lambda instrument: appFilter_Flag(instrument.otc_flag, self.comboBox_otc_flag.currentText()),
            self.Filters.BLOCKED_TCA:
                lambda instrument: appFilter_Flag(instrument.blocked_tca_flag, self.comboBox_blocked_tca_flag.currentText()),
            self.Filters.CURRENCY:
                lambda instrument: appFilter_Currency(instrument.currency, self.comboBox_currency.currentText())
        }
        '''--------------------------------------------------------------------------------------'''

        self.new_filters: dict[str, BoolFilterComboBox] = {
            'api_trade_available_flag': self.comboBox_api_trade_available_flag,
            'for_iis_flag': self.comboBox_for_iis_flag,
            'for_qual_investor_flag': self.comboBox_for_qual_investor_flag,
            'liquidity_flag': self.comboBox_liquidity_flag,
            'short_enabled_flag': self.comboBox_short_enabled_flag,
            'buy_available_flag': self.comboBox_buy_available_flag,
            'sell_available_flag': self.comboBox_sell_available_flag,
            'weekend_flag': self.comboBox_weekend_flag,
            'otc_flag': self.comboBox_otc_flag,
            'blocked_tca_flag': self.comboBox_blocked_tca_flag
        }

        for filter in self.new_filters.values():
            filter.currentIndexChanged.connect(lambda index: self.filtersChanged.emit())

    def checkFilters(self, instrument: Bond) -> bool:
        """Проверяет инструмент на соответствие фильтрам."""
        for filter in self.filters.values():
            if not filter(instrument): return False
        return True

    def getSqlCondition(self) -> str | None:
        condition: str = ''
        for comboBox in self.new_filters.values():
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
    @enum.unique  # Декоратор, требующий, чтобы все элементы имели разные значения.
    class Filters(enum.IntEnum):
        """Перечисление фильтров облигаций."""
        MATURITY_FLAG = 0  # Погашенность.
        RISK_LEVEL = 1  # Уровень риска.
        AMORTIZATION_FLAG = 2  # Признак облигации с амортизацией долга.
        FLOATING_COUPON_FLAG = 3  # Признак облигации с плавающим купоном.
        PERPETUAL_FLAG = 4  # Признак бессрочной облигации.
        SUBORDINATED_FLAG = 5  # Признак субординированной облигации.

    def __init__(self, object_name: str, parent: QtWidgets.QWidget | None = ...):
        super().__init__(parent)  # QGroupBox __init__().
        self.setObjectName(object_name)
        _translate = QtCore.QCoreApplication.translate
        self.setTitle(_translate('MainWindow', 'Фильтры облигаций'))

        self.verticalLayout_main = QtWidgets.QVBoxLayout(self)
        self.verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        self.verticalLayout_main.setSpacing(2)
        self.verticalLayout_main.setObjectName('verticalLayout_main')

        self.gridLayout_main = QtWidgets.QGridLayout()
        self.gridLayout_main.setHorizontalSpacing(7)
        self.gridLayout_main.setVerticalSpacing(2)
        self.gridLayout_main.setObjectName('gridLayout_main')

        """----------------------------Погашенность----------------------------"""
        self.label_maturity = QtWidgets.QLabel(self)
        self.label_maturity.setObjectName('label_maturity')
        self.label_maturity.setToolTip(_translate('MainWindow', 'Флаг, отображающий погашенность облигации к текущей дате.'))
        self.label_maturity.setText(_translate('MainWindow', 'Погашенность:'))
        self.gridLayout_main.addWidget(self.label_maturity, 0, 0, 1, 1)

        self.comboBox_maturity = QtWidgets.QComboBox(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.comboBox_maturity.sizePolicy().hasHeightForWidth())
        self.comboBox_maturity.setSizePolicy(sizePolicy)
        self.comboBox_maturity.setObjectName('comboBox_maturity')
        self.comboBox_maturity.addItem(_translate('MainWindow', 'Все'))
        self.comboBox_maturity.addItem(_translate('MainWindow', 'Непогашенные'))
        self.comboBox_maturity.addItem(_translate('MainWindow', 'Погашенные'))
        self.gridLayout_main.addWidget(self.comboBox_maturity, 0, 1, 1, 1)
        """--------------------------------------------------------------------"""

        """----------------------------Плавающий купон---------------------------"""
        self.label_floating_coupon_flag = QtWidgets.QLabel(self)
        self.label_floating_coupon_flag.setObjectName('label_floating_coupon_flag')
        self.label_floating_coupon_flag.setToolTip(_translate("MainWindow", "Признак облигации с плавающим купоном."))
        self.label_floating_coupon_flag.setText(_translate("MainWindow", "Плавающий купон:"))
        self.gridLayout_main.addWidget(self.label_floating_coupon_flag, 0, 2, 1, 1)

        self.comboBox_floating_coupon_flag = QtWidgets.QComboBox(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.comboBox_floating_coupon_flag.sizePolicy().hasHeightForWidth())
        self.comboBox_floating_coupon_flag.setSizePolicy(sizePolicy)
        self.comboBox_floating_coupon_flag.setObjectName('comboBox_floating_coupon_flag')
        self.comboBox_floating_coupon_flag.addItem(_translate("MainWindow", "Все"))
        self.comboBox_floating_coupon_flag.addItem(_translate("MainWindow", "True"))
        self.comboBox_floating_coupon_flag.addItem(_translate("MainWindow", "False"))
        self.gridLayout_main.addWidget(self.comboBox_floating_coupon_flag, 0, 3, 1, 1)
        """----------------------------------------------------------------------"""

        """----------------------------Уровень риска----------------------------"""
        self.label_risk_level = QtWidgets.QLabel(self)
        self.label_risk_level.setObjectName('label_risk_level')
        self.label_risk_level.setToolTip(_translate("MainWindow", "Уровень риска."))
        self.label_risk_level.setText(_translate("MainWindow", "Уровень риска:"))
        self.gridLayout_main.addWidget(self.label_risk_level, 1, 0, 1, 1)

        self.comboBox_risk_level = QtWidgets.QComboBox(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.comboBox_risk_level.sizePolicy().hasHeightForWidth())
        self.comboBox_risk_level.setSizePolicy(sizePolicy)
        self.comboBox_risk_level.setObjectName('comboBox_risk_level')
        self.comboBox_risk_level.addItem(_translate("MainWindow", "Любой"))
        self.comboBox_risk_level.addItem(_translate("MainWindow", "Низкий"))
        self.comboBox_risk_level.addItem(_translate("MainWindow", "Средний"))
        self.comboBox_risk_level.addItem(_translate("MainWindow", "Высокий"))
        self.comboBox_risk_level.addItem(_translate("MainWindow", "Неизвестен"))
        self.gridLayout_main.addWidget(self.comboBox_risk_level, 1, 1, 1, 1)
        """---------------------------------------------------------------------"""

        """----------------------------Бессрочность----------------------------"""
        self.label_perpetual_flag = QtWidgets.QLabel(self)
        self.label_perpetual_flag.setObjectName('label_perpetual_flag')
        self.label_perpetual_flag.setToolTip(_translate("MainWindow", "Признак бессрочной облигации."))
        self.label_perpetual_flag.setText(_translate("MainWindow", "Бессрочность:"))
        self.gridLayout_main.addWidget(self.label_perpetual_flag, 1, 2, 1, 1)

        self.comboBox_perpetual_flag = QtWidgets.QComboBox(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.comboBox_perpetual_flag.sizePolicy().hasHeightForWidth())
        self.comboBox_perpetual_flag.setSizePolicy(sizePolicy)
        self.comboBox_perpetual_flag.setObjectName('comboBox_perpetual_flag')
        self.comboBox_perpetual_flag.addItem(_translate("MainWindow", "Все"))
        self.comboBox_perpetual_flag.addItem(_translate("MainWindow", "True"))
        self.comboBox_perpetual_flag.addItem(_translate("MainWindow", "False"))
        self.gridLayout_main.addWidget(self.comboBox_perpetual_flag, 1, 3, 1, 1)
        """--------------------------------------------------------------------"""

        """-----------------------------Амортизация-----------------------------"""
        self.label_amortization_flag = QtWidgets.QLabel(self)
        self.label_amortization_flag.setObjectName('label_amortization_flag')
        self.label_amortization_flag.setToolTip(_translate("MainWindow", "Признак облигации с амортизацией долга."))
        self.label_amortization_flag.setText(_translate("MainWindow", "Амортизация:"))
        self.gridLayout_main.addWidget(self.label_amortization_flag, 2, 0, 1, 1)

        self.comboBox_amortization_flag = QtWidgets.QComboBox(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.comboBox_amortization_flag.sizePolicy().hasHeightForWidth())
        self.comboBox_amortization_flag.setSizePolicy(sizePolicy)
        self.comboBox_amortization_flag.setObjectName('comboBox_amortization_flag')
        self.comboBox_amortization_flag.addItem(_translate("MainWindow", "Все"))
        self.comboBox_amortization_flag.addItem(_translate("MainWindow", "True"))
        self.comboBox_amortization_flag.addItem(_translate("MainWindow", "False"))
        self.gridLayout_main.addWidget(self.comboBox_amortization_flag, 2, 1, 1, 1)
        """---------------------------------------------------------------------"""

        """-------------------------------Суборд-------------------------------"""
        self.label_subordinated_flag = QtWidgets.QLabel(self)
        self.label_subordinated_flag.setObjectName('label_subordinated_flag')
        self.label_subordinated_flag.setToolTip(_translate("MainWindow", "Признак субординированной облигации."))
        self.label_subordinated_flag.setText(_translate("MainWindow", "Суборд:"))
        self.gridLayout_main.addWidget(self.label_subordinated_flag, 2, 2, 1, 1)

        self.comboBox_subordinated_flag = QtWidgets.QComboBox(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.comboBox_subordinated_flag.sizePolicy().hasHeightForWidth())
        self.comboBox_subordinated_flag.setSizePolicy(sizePolicy)
        self.comboBox_subordinated_flag.setObjectName('comboBox_subordinated_flag')
        self.comboBox_subordinated_flag.addItem(_translate("MainWindow", "Все"))
        self.comboBox_subordinated_flag.addItem(_translate("MainWindow", "True"))
        self.comboBox_subordinated_flag.addItem(_translate("MainWindow", "False"))
        self.gridLayout_main.addWidget(self.comboBox_subordinated_flag, 2, 3, 1, 1)
        """--------------------------------------------------------------------"""

        self.verticalLayout_main.addLayout(self.gridLayout_main)

        self.comboBox_maturity.setCurrentIndex(1)
        self.comboBox_floating_coupon_flag.setCurrentIndex(0)
        self.comboBox_perpetual_flag.setCurrentIndex(0)
        self.comboBox_amortization_flag.setCurrentIndex(0)
        self.comboBox_subordinated_flag.setCurrentIndex(0)

        '''------------------------------------Фильтры облигаций------------------------------------'''
        def appFilter_Maturity(bond: Bond, cur_filter: str) -> bool:
            """Фильтр по погашенности."""
            match cur_filter:
                case 'Все': return True
                case 'Непогашенные': return not MyBond.ifBondIsMaturity(bond)
                case 'Погашенные': return MyBond.ifBondIsMaturity(bond)
                case _: raise ValueError('Некорректное значение фильтра \"Погашенность\" ({0})!'.format(cur_filter))

        def appFilter_RiskLevel(risk_level: RiskLevel, cur_filter: str) -> bool:
            """Фильтр по уровню риска."""
            match cur_filter:
                case 'Любой': return True
                case 'Низкий': return True if risk_level == RiskLevel.RISK_LEVEL_LOW else False
                case 'Средний': return True if risk_level == RiskLevel.RISK_LEVEL_MODERATE else False
                case 'Высокий': return True if risk_level == RiskLevel.RISK_LEVEL_HIGH else False
                case 'Неизвестен': return True if risk_level == RiskLevel.RISK_LEVEL_UNSPECIFIED else False
                case _: raise ValueError('Некорректное значение фильтра \"Уровень риска\" ({0})!'.format(cur_filter))

        self.filters: dict = {
            self.Filters.MATURITY_FLAG:
                lambda bond: appFilter_Maturity(bond, self.comboBox_maturity.currentText()),
            self.Filters.RISK_LEVEL:
                lambda bond: appFilter_RiskLevel(bond.risk_level, self.comboBox_risk_level.currentText()),
            self.Filters.AMORTIZATION_FLAG:
                lambda bond: appFilter_Flag(bond.amortization_flag, self.comboBox_amortization_flag.currentText()),
            self.Filters.FLOATING_COUPON_FLAG:
                lambda bond: appFilter_Flag(bond.floating_coupon_flag, self.comboBox_floating_coupon_flag.currentText()),
            self.Filters.PERPETUAL_FLAG:
                lambda bond: appFilter_Flag(bond.perpetual_flag, self.comboBox_perpetual_flag.currentText()),
            self.Filters.SUBORDINATED_FLAG:
                lambda bond: appFilter_Flag(bond.subordinated_flag, self.comboBox_subordinated_flag.currentText()),
        }
        '''-----------------------------------------------------------------------------------------'''

    def checkFilters(self, bond: Bond) -> bool:
        """Проверяет облигацию на соответствие фильтрам."""
        for filter in self.filters.values():
            if not filter(bond): return False
        return True


class GroupBox_BondsFilters(QtWidgets.QGroupBox):
    """GroupBox со всеми фильтрами облигаций."""
    filtersChanged: pyqtSignal = pyqtSignal()  # Сигнал испускается при изменении фильтров.

    def __init__(self, object_name: str, parent: QtWidgets.QWidget | None = ...):
        super().__init__(parent)  # QGroupBox __init__().
        self.setTitle('')
        self.setObjectName(object_name)

        self.verticalLayout_main = QtWidgets.QVBoxLayout(self)
        self.verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        self.verticalLayout_main.setSpacing(0)
        self.verticalLayout_main.setObjectName('verticalLayout_main')

        """--------------------------Заголовок--------------------------"""
        self.horizontalLayout_title = QtWidgets.QHBoxLayout()
        self.horizontalLayout_title.setSpacing(0)
        self.horizontalLayout_title.setObjectName('horizontalLayout_title')

        spacerItem38 = QtWidgets.QSpacerItem(10, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_title.addItem(spacerItem38)

        spacerItem39 = QtWidgets.QSpacerItem(0, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_title.addItem(spacerItem39)

        self.label_title = QtWidgets.QLabel(self)
        font = QtGui.QFont()
        font.setBold(True)
        self.label_title.setFont(font)
        self.label_title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.label_title.setObjectName('label_title')
        self.horizontalLayout_title.addWidget(self.label_title)

        self.label_count = QtWidgets.QLabel(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_count.sizePolicy().hasHeightForWidth())
        self.label_count.setSizePolicy(sizePolicy)
        self.label_count.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignTrailing | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.label_count.setObjectName('label_count')
        self.horizontalLayout_title.addWidget(self.label_count)

        spacerItem40 = QtWidgets.QSpacerItem(10, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_title.addItem(spacerItem40)

        self.verticalLayout_main.addLayout(self.horizontalLayout_title)
        """-------------------------------------------------------------"""

        """---------------------Фильтры инструментов---------------------"""
        self.horizontalLayout_instruments_filters = QtWidgets.QHBoxLayout()
        self.horizontalLayout_instruments_filters.setSpacing(0)
        self.horizontalLayout_instruments_filters.setObjectName('horizontalLayout_instruments_filters')

        """---------------------Панель фильтров инструментов---------------------"""
        self.groupBox_instruments_filters = GroupBox_InstrumentsFilters('groupBox_instruments_filters', self)
        self.groupBox_instruments_filters.filtersChanged.connect(self.filtersChanged.emit)
        self.horizontalLayout_instruments_filters.addWidget(self.groupBox_instruments_filters)
        """----------------------------------------------------------------------"""

        spacerItem41 = QtWidgets.QSpacerItem(0, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_instruments_filters.addItem(spacerItem41)

        self.verticalLayout_main.addLayout(self.horizontalLayout_instruments_filters)
        """--------------------------------------------------------------"""

        """----------------------Фильтры облигаций----------------------"""
        self.horizontalLayout_bond_filters = QtWidgets.QHBoxLayout()
        self.horizontalLayout_bond_filters.setSpacing(0)
        self.horizontalLayout_bond_filters.setObjectName('horizontalLayout_bond_filters')

        self.groupBox_bonds_filters: GroupBox_OnlyBondsFilters = GroupBox_OnlyBondsFilters('groupBox_bonds_filters', self)
        self.horizontalLayout_bond_filters.addWidget(self.groupBox_bonds_filters)

        spacerItem42 = QtWidgets.QSpacerItem(0, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_bond_filters.addItem(spacerItem42)

        self.verticalLayout_main.addLayout(self.horizontalLayout_bond_filters)
        """-------------------------------------------------------------"""

        """------------------------------------retranslateUi------------------------------------"""
        _translate = QtCore.QCoreApplication.translate
        self.label_title.setText(_translate('MainWindow', 'ФИЛЬТРЫ'))
        self.label_count.setText(_translate('MainWindow', '0'))
        """-------------------------------------------------------------------------------------"""

    def _checkFilters(self, bond: Bond) -> bool:
        """Проверяет облигацию на соответствие фильтрам."""
        return self.groupBox_instruments_filters.checkFilters(bond) & self.groupBox_bonds_filters.checkFilters(bond)

    def getFilteredBondsList(self, bonds: list[Bond]) -> list[Bond]:
        """Фильтрует список облигаций и возвращает отфильтрованный список."""
        filtered_list: list[Bond] = list(filter(self._checkFilters, bonds))
        # self.setCount(len(filtered_list))  # Обновляет количество отобранных облигаций.
        return filtered_list

    def setCount(self, count: int):
        """Устанавливает количество отобранных облигаций."""
        self.label_count.setText(str(count))

    def getSqlCondition(self) -> str | None:
        return self.groupBox_instruments_filters.getSqlCondition()


class GroupBox_CouponsView(QtWidgets.QGroupBox):
    """Панель отображения купонов облигаций."""
    def __init__(self, object_name: str, parent: QtWidgets.QWidget | None = ...):
        super().__init__(parent)  # QGroupBox __init__().
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(sizePolicy)
        self.setTitle('')
        self.setObjectName(object_name)

        self.verticalLayout_main = QtWidgets.QVBoxLayout(self)
        self.verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        self.verticalLayout_main.setSpacing(2)
        self.verticalLayout_main.setObjectName('verticalLayout_main')

        """------------------------Заголовок------------------------"""
        self.horizontalLayout_title = QtWidgets.QHBoxLayout()
        self.horizontalLayout_title.setSpacing(0)
        self.horizontalLayout_title.setObjectName('horizontalLayout_title')

        spacerItem44 = QtWidgets.QSpacerItem(10, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_title.addItem(spacerItem44)

        spacerItem45 = QtWidgets.QSpacerItem(0, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_title.addItem(spacerItem45)

        _translate = QtCore.QCoreApplication.translate

        self.label_title = QtWidgets.QLabel(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_title.sizePolicy().hasHeightForWidth())
        self.label_title.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setPointSize(9)
        font.setBold(True)
        self.label_title.setFont(font)
        self.label_title.setStyleSheet('border: none;')
        self.label_title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.label_title.setObjectName('label_title')
        self.label_title.setText(_translate('MainWindow', 'КУПОНЫ'))
        self.horizontalLayout_title.addWidget(self.label_title)

        self.label_count = QtWidgets.QLabel(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_count.sizePolicy().hasHeightForWidth())
        self.label_count.setSizePolicy(sizePolicy)
        self.label_count.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignTrailing | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.label_count.setObjectName('label_count')
        self.label_count.setText(_translate('MainWindow', '0'))
        self.horizontalLayout_title.addWidget(self.label_count)

        spacerItem46 = QtWidgets.QSpacerItem(10, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_title.addItem(spacerItem46)

        self.verticalLayout_main.addLayout(self.horizontalLayout_title)
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
        self.tableView.setObjectName('tableView')
        self.verticalLayout_main.addWidget(self.tableView)
        """----------------------------------------------------------"""

    def sourceModel(self) -> CouponsModel:
        """Возвращает исходную модель купонов."""
        # return self.tableView.model().sourceModel()
        return self.tableView.model()

    def setData(self, figi: str | None):
        """Обновляет данные модели купонов в соответствии с выбранным figi."""
        self.sourceModel().setModelData(figi)
        self.label_count.setText(str(self.tableView.model().rowCount()))  # Отображаем количество купонов.
        self.tableView.resizeColumnsToContents()  # Авторазмер столбцов под содержимое.


class GroupBox_BondsView(QtWidgets.QGroupBox):
    """Панель отображения облигаций."""
    def __init__(self, object_name: str, token: TokenClass | None, instrument_status: InstrumentStatus, sql_condition: str | None, parent: QtWidgets.QWidget | None = ...):
        super().__init__(parent)  # QGroupBox __init__().
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(sizePolicy)
        self.setBaseSize(QtCore.QSize(0, 0))
        self.setTitle('')
        self.setObjectName(object_name)

        self.verticalLayout_main = QtWidgets.QVBoxLayout(self)
        self.verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        self.verticalLayout_main.setSpacing(2)
        self.verticalLayout_main.setObjectName('verticalLayout_main')

        _translate = QtCore.QCoreApplication.translate

        '''------------------------Заголовок------------------------'''
        self.horizontalLayout_title = QtWidgets.QHBoxLayout()
        self.horizontalLayout_title.setSpacing(0)
        self.horizontalLayout_title.setObjectName('horizontalLayout_title')

        spacerItem47 = QtWidgets.QSpacerItem(10, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_title.addItem(spacerItem47)

        self.lineEdit_search = QtWidgets.QLineEdit(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.lineEdit_search.sizePolicy().hasHeightForWidth())
        self.lineEdit_search.setSizePolicy(sizePolicy)
        self.lineEdit_search.setObjectName('lineEdit_search')
        self.lineEdit_search.setPlaceholderText(_translate('MainWindow', 'Поиск...'))
        self.horizontalLayout_title.addWidget(self.lineEdit_search)

        spacerItem48 = QtWidgets.QSpacerItem(0, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_title.addItem(spacerItem48)

        self.label_title = QtWidgets.QLabel(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_title.sizePolicy().hasHeightForWidth())
        self.label_title.setSizePolicy(sizePolicy)
        self.label_title.setMaximumSize(QtCore.QSize(16777215, 13))
        font = QtGui.QFont()
        font.setPointSize(9)
        font.setBold(True)
        self.label_title.setFont(font)
        self.label_title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.label_title.setObjectName('label_title')
        self.label_title.setText(_translate('MainWindow', 'ОБЛИГАЦИИ'))
        self.horizontalLayout_title.addWidget(self.label_title)

        self.label_count = QtWidgets.QLabel(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_count.sizePolicy().hasHeightForWidth())
        self.label_count.setSizePolicy(sizePolicy)
        self.label_count.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignTrailing | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.label_count.setObjectName('label_count')
        self.label_count.setText(_translate('MainWindow', '0 / 0'))
        self.horizontalLayout_title.addWidget(self.label_count)

        spacerItem49 = QtWidgets.QSpacerItem(10, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_title.addItem(spacerItem49)

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
        self.tableView.setObjectName('tableView')
        self.verticalLayout_main.addWidget(self.tableView)
        '''---------------------------------------------------------'''

        '''--------------------------Модель облигаций--------------------------'''
        source_model: BondsModel = BondsModel(token, instrument_status, sql_condition)  # Создаём модель.
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


class new_BondsPage(QtWidgets.QWidget):
    """Страница облигаций."""
    def __init__(self, object_name: str, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)  # QWidget __init__().
        self.setObjectName(object_name)

        '''------------------------Аттрибуты экземпляра класса------------------------'''
        self.__token: TokenClass | None = None
        self.__instrument_status: InstrumentStatus = InstrumentStatus.INSTRUMENT_STATUS_ALL
        '''---------------------------------------------------------------------------'''

        """=======================================Создание UI======================================="""
        self.verticalLayout_main = QtWidgets.QVBoxLayout(self)
        self.verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        self.verticalLayout_main.setSpacing(2)
        self.verticalLayout_main.setObjectName('verticalLayout_main')

        self.splitter = QtWidgets.QSplitter(self)
        self.splitter.setOrientation(QtCore.Qt.Orientation.Vertical)
        self.splitter.setObjectName('splitter')

        self.layoutWidget = QtWidgets.QWidget(self.splitter)
        self.layoutWidget.setObjectName('layoutWidget')

        self.verticalLayout_top = QtWidgets.QVBoxLayout(self.layoutWidget)
        self.verticalLayout_top.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_top.setSpacing(2)
        self.verticalLayout_top.setObjectName('verticalLayout_top')

        self.horizontalLayout_top_top = QtWidgets.QHBoxLayout()
        self.horizontalLayout_top_top.setSpacing(2)
        self.horizontalLayout_top_top.setObjectName('horizontalLayout_top_top')

        """------------------Панель выполнения запроса------------------"""
        self.groupBox_request = GroupBox_InstrumentsRequest('groupBox_request', self.layoutWidget)
        self.horizontalLayout_top_top.addWidget(self.groupBox_request)
        """-------------------------------------------------------------"""

        """--------------Панель прогресса получения купонов--------------"""
        self.groupBox_coupons_receiving: GroupBox_CouponsReceiving = GroupBox_CouponsReceiving('groupBox_coupons_receiving', self.layoutWidget)
        self.horizontalLayout_top_top.addWidget(self.groupBox_coupons_receiving)
        self.horizontalLayout_top_top.setStretch(1, 1)
        """--------------------------------------------------------------"""

        self.verticalLayout_top.addLayout(self.horizontalLayout_top_top)

        self.horizontalLayout_top_bottom = QtWidgets.QHBoxLayout()
        self.horizontalLayout_top_bottom.setSpacing(2)
        self.horizontalLayout_top_bottom.setObjectName('horizontalLayout_top_bottom')

        self.verticalLayout_calendar = QtWidgets.QVBoxLayout()
        self.verticalLayout_calendar.setSpacing(0)
        self.verticalLayout_calendar.setObjectName('verticalLayout_calendar')

        """---------------------Панель даты расчёта---------------------"""
        self.groupBox_calendar = GroupBox_CalculationDate('groupBox_calendar', self.layoutWidget)
        self.verticalLayout_calendar.addWidget(self.groupBox_calendar)
        """-------------------------------------------------------------"""

        spacerItem37 = QtWidgets.QSpacerItem(20, 2, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        self.verticalLayout_calendar.addItem(spacerItem37)

        self.verticalLayout_calendar.setStretch(1, 1)
        self.horizontalLayout_top_bottom.addLayout(self.verticalLayout_calendar)

        self.verticalLayout_filters = QtWidgets.QVBoxLayout()
        self.verticalLayout_filters.setSpacing(0)
        self.verticalLayout_filters.setObjectName('verticalLayout_filters')

        """-----------------------Панель фильтров-----------------------"""
        self.groupBox_filters: GroupBox_BondsFilters = GroupBox_BondsFilters('groupBox_filters', self.layoutWidget)
        self.verticalLayout_filters.addWidget(self.groupBox_filters)
        """-------------------------------------------------------------"""

        """Аттрибут self.__sql_condition не относится к UI, но он должен быть инициализирован после
        панели фильтров и перед панелью отображения облигаций."""
        self.__sql_condition: str | None = self.groupBox_filters.getSqlCondition()

        spacerItem43 = QtWidgets.QSpacerItem(20, 0, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        self.verticalLayout_filters.addItem(spacerItem43)

        self.horizontalLayout_top_bottom.addLayout(self.verticalLayout_filters)

        """------------------Панель отображения купонов------------------"""
        self.groupBox_coupons: GroupBox_CouponsView = GroupBox_CouponsView('groupBox_coupons', self.layoutWidget)
        self.horizontalLayout_top_bottom.addWidget(self.groupBox_coupons)
        self.horizontalLayout_top_bottom.setStretch(2, 1)
        """--------------------------------------------------------------"""

        self.verticalLayout_top.addLayout(self.horizontalLayout_top_bottom)
        self.verticalLayout_top.setStretch(1, 1)

        '''-----------------Панель отображения облигаций-----------------'''
        self.groupBox_view: GroupBox_BondsView = GroupBox_BondsView('groupBox_view', self.token, self.instrument_status, self.sql_condition, self.splitter)
        '''--------------------------------------------------------------'''

        self.verticalLayout_main.addWidget(self.splitter)
        """========================================================================================="""

        # self.groupBox_request.currentTokenChanged.connect(self.onTokenChanged)
        self.groupBox_request.currentTokenChanged.connect(lambda token, instrument_status: self.__setToken(token))
        # self.groupBox_request.currentTokenReset.connect(self.onTokenReset)
        self.groupBox_request.currentTokenReset.connect(lambda: self.__setToken(None))
        self.groupBox_request.currentStatusChanged.connect(self.__setInstrumentStatus)

        self.groupBox_filters.filtersChanged.connect(lambda: self.__setSqlCondition(self.groupBox_filters.getSqlCondition()))

        '''---------------------------------Фильтры---------------------------------'''
        # def onFilterChanged():
        #     """Функция, выполняемая при изменении фильтра."""
        #     self._stopCouponsThread()  # Останавливаем поток получения купонов.
        #     token: TokenClass | None = self.token
        #     if token is None:
        #         self.bonds = []
        #         self.groupBox_view.setBonds([])  # Передаём в исходную модель данные.
        #         self.groupBox_coupons.setData(None)  # Сбрасываем модель купонов.
        #         '''---------------Обновляет отображение количеств облигаций в моделях---------------'''
        #         self.groupBox_request.setCount(0)  # Количество полученных облигаций.
        #         self.groupBox_filters.setCount(0)  # Количество отобранных облигаций.
        #         '''---------------------------------------------------------------------------------'''
        #         self.groupBox_coupons_receiving.reset()  # Сбрасывает progressBar.
        #     else:
        #         bonds: list[Bond] = self.bonds
        #         filtered_bonds: list[Bond] = self.groupBox_filters.getFilteredBondsList(bonds)  # Отфильтрованный список облигаций.
        #         '''---------------Обновляет отображение количеств облигаций в моделях---------------'''
        #         self.groupBox_request.setCount(len(bonds))  # Количество полученных облигаций.
        #         self.groupBox_filters.setCount(len(filtered_bonds))  # Количество отобранных облигаций.
        #         '''---------------------------------------------------------------------------------'''
        #         bond_class_list: list[MyBondClass] = [MyBondClass(bond, lp) for (bond, lp) in zipWithLastPrices(token, filtered_bonds)]
        #         self.groupBox_view.setBonds(bond_class_list)  # Передаём в исходную модель данные.
        #         self.groupBox_coupons.setData(None)  # Сбрасываем модель купонов.
        #         if bond_class_list:  # Если список не пуст.
        #             self._startCouponsThread(bond_class_list)  # Запускает поток получения купонов.
        #
        # # Фильтры инструментов.
        # self.groupBox_filters.groupBox_instruments_filters.comboBox_api_trade_available_flag.currentIndexChanged.connect(lambda index: onFilterChanged())
        # self.groupBox_filters.groupBox_instruments_filters.comboBox_for_iis_flag.currentIndexChanged.connect(lambda index: onFilterChanged())
        # self.groupBox_filters.groupBox_instruments_filters.comboBox_for_qual_investor_flag.currentIndexChanged.connect(lambda index: onFilterChanged())
        # self.groupBox_filters.groupBox_instruments_filters.comboBox_liquidity_flag.currentIndexChanged.connect(lambda index: onFilterChanged())
        # self.groupBox_filters.groupBox_instruments_filters.comboBox_short_enabled_flag.currentIndexChanged.connect(lambda index: onFilterChanged())
        # self.groupBox_filters.groupBox_instruments_filters.comboBox_buy_available_flag.currentIndexChanged.connect(lambda index: onFilterChanged())
        # self.groupBox_filters.groupBox_instruments_filters.comboBox_sell_available_flag.currentIndexChanged.connect(lambda index: onFilterChanged())
        # self.groupBox_filters.groupBox_instruments_filters.comboBox_weekend_flag.currentIndexChanged.connect(lambda index: onFilterChanged())
        # self.groupBox_filters.groupBox_instruments_filters.comboBox_otc_flag.currentIndexChanged.connect(lambda index: onFilterChanged())
        # self.groupBox_filters.groupBox_instruments_filters.comboBox_blocked_tca_flag.currentIndexChanged.connect(lambda index: onFilterChanged())
        # self.groupBox_filters.groupBox_instruments_filters.comboBox_currency.currentTextChanged.connect(lambda text: onFilterChanged())
        #
        # # Фильтры акций.
        # self.groupBox_filters.groupBox_bonds_filters.comboBox_maturity.currentIndexChanged.connect(lambda index: onFilterChanged())
        # self.groupBox_filters.groupBox_bonds_filters.comboBox_risk_level.currentIndexChanged.connect(lambda index: onFilterChanged())
        # self.groupBox_filters.groupBox_bonds_filters.comboBox_amortization_flag.currentIndexChanged.connect(lambda index: onFilterChanged())
        # self.groupBox_filters.groupBox_bonds_filters.comboBox_floating_coupon_flag.currentIndexChanged.connect(lambda index: onFilterChanged())
        # self.groupBox_filters.groupBox_bonds_filters.comboBox_perpetual_flag.currentIndexChanged.connect(lambda index: onFilterChanged())
        # self.groupBox_filters.groupBox_bonds_filters.comboBox_subordinated_flag.currentIndexChanged.connect(lambda index: onFilterChanged())
        '''-------------------------------------------------------------------------'''

        # self.groupBox_calendar.calendarWidget.selectionChanged.connect(lambda: self.groupBox_view.setCalculationDateTime(self.groupBox_calendar.getDateTime()))
        #
        # self.groupBox_view.tableView.selectionModel().currentRowChanged.connect(lambda current, previous: self.groupBox_coupons.setData(self.groupBox_view.proxyModel().getBond(current)))  # Событие смены выбранной облигации.

        # self.groupBox_view.tableView.selectionModel().currentRowChanged.connect(lambda current, previous: self.groupBox_coupons.setData(self.groupBox_view.sourceModel().getBond(current)))  # Событие смены выбранной облигации.

    def __getToken(self) -> TokenClass | None:
        return self.__token

    def __setToken(self, token: TokenClass | None):
        self.__token = token
        sql_condition: str | None = self.groupBox_filters.getSqlCondition()
        self.groupBox_view.updateModel(self.token, self.instrument_status, sql_condition)  # Задаём параметры запроса к БД.

    token = property(__getToken, __setToken)

    # @property
    # def token(self) -> TokenClass | None:
    #     return self.__token
    #
    # @token.setter
    # def token(self, token: TokenClass | None):
    #     self.__token = token
    #     self.groupBox_view.updateModel(self.token, self.instrument_status)  # Задаём параметры запроса к БД.

    def __getInstrumentStatus(self) -> InstrumentStatus:
        return self.__instrument_status

    def __setInstrumentStatus(self, instrument_status: InstrumentStatus):
        self.__instrument_status = instrument_status
        sql_condition: str | None = self.groupBox_filters.getSqlCondition()
        self.groupBox_view.updateModel(self.token, self.instrument_status, sql_condition)  # Задаём параметры запроса к БД.

    instrument_status = property(__getInstrumentStatus, __setInstrumentStatus)

    '''---------------------------Свойство условий фильтров---------------------------'''
    def __getSqlCondition(self) -> str | None:
        return self.__sql_condition

    def __setSqlCondition(self, sql_condition: str | None):
        self.__sql_condition = sql_condition
        self.groupBox_view.updateModel(self.token, self.instrument_status, self.sql_condition)  # Задаём параметры запроса к БД.

    sql_condition = property(__getSqlCondition, __setSqlCondition)
    '''-------------------------------------------------------------------------------'''

    def setTokensModel(self, token_list_model: TokenListModel):
        """Устанавливает модель токенов для ComboBox'а."""
        self.groupBox_request.comboBox_token.setModel(token_list_model)

    # @pyqtSlot(TokenClass, InstrumentStatus)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
    # def onTokenChanged(self, token: TokenClass, instrument_status: InstrumentStatus):
    #     """Функция, выполняемая при изменении выбранного токена."""
    #     self.token = token
    #
    # @pyqtSlot()  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
    # def onTokenReset(self):
    #     """Функция, выполняемая при выборе пустого значения вместо токена."""
    #     self.token = None
