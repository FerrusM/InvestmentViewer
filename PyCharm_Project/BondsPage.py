import enum
import typing
from datetime import datetime
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import pyqtSlot
from tinkoff.invest import InstrumentStatus, Bond
from tinkoff.invest.schemas import RiskLevel
from BondsModel import BondsModel, BondsProxyModel
from Classes import TokenClass
from CouponsModel import CouponsModel, CouponsProxyModel
from CouponsThread import CouponsThread
from MyBondClass import MyBondClass, MyBond
from MyDateTime import getMoscowDateTime
from MyRequests import MyResponse, getBonds
from PagesClasses import GroupBox_InstrumentsRequest, GroupBox_InstrumentsFilters, GroupBox_CalculationDate, appFilter_Flag, zipWithLastPrices
from TokenModel import TokenListModel


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

        self.progressBar_coupons = QtWidgets.QProgressBar(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.progressBar_coupons.sizePolicy().hasHeightForWidth())
        self.progressBar_coupons.setSizePolicy(sizePolicy)
        self.progressBar_coupons.setMinimumSize(QtCore.QSize(0, 0))
        self.progressBar_coupons.setStyleSheet('text-align: center;')
        self.progressBar_coupons.setMaximum(0)
        self.progressBar_coupons.setProperty('value', 0)
        self.progressBar_coupons.setTextVisible(True)
        self.progressBar_coupons.setObjectName('progressBar_coupons')
        self.progressBar_coupons.setFormat(_translate('MainWindow', '%p% (%v из %m)'))
        self.verticalLayout_main.addWidget(self.progressBar_coupons)

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
        """Устанавливает минимум и максимум для progressBar'а. Если максимум равен нулю, то скрывает бегающую полоску."""
        if maximum == 0:
            '''setRange(0, 0) устанавливает неопределённое состояние progressBar'а, чего хотелось бы избежать.'''
            self.progressBar_coupons.setRange(minimum, 100)  # Устанавливает минимум и максимум для progressBar'а.
        else:
            self.progressBar_coupons.setRange(minimum, maximum)  # Устанавливает минимум и максимум для progressBar'а.
        self.progressBar_coupons.setValue(0)
        self.progressBar_coupons.reset()  # Сбрасывает progressBar.

    def setValue(self, value: int):
        """Изменяет прогресс в progressBar'е"""
        self.progressBar_coupons.setValue(value)

    def reset(self):
        """Сбрасывает progressBar."""
        self.progressBar_coupons.setRange(0, 100)  # Убирает неопределённое состояние progressBar'а.
        self.progressBar_coupons.reset()


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
        self.label_maturity.setToolTip(_translate("MainWindow", "Флаг, отображающий погашенность облигации к текущей дате."))
        self.label_maturity.setText(_translate("MainWindow", "Погашенность:"))
        self.gridLayout_main.addWidget(self.label_maturity, 0, 0, 1, 1)

        self.comboBox_maturity = QtWidgets.QComboBox(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.comboBox_maturity.sizePolicy().hasHeightForWidth())
        self.comboBox_maturity.setSizePolicy(sizePolicy)
        self.comboBox_maturity.setObjectName('comboBox_maturity')
        self.comboBox_maturity.addItem(_translate("MainWindow", "Все"))
        self.comboBox_maturity.addItem(_translate("MainWindow", "Непогашенные"))
        self.comboBox_maturity.addItem(_translate("MainWindow", "Погашенные"))
        self.gridLayout_main.addWidget(self.comboBox_maturity, 0, 1, 1, 1)
        """--------------------------------------------------------------------"""

        """---------------------------Плавающий купон---------------------------"""
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
        """---------------------------------------------------------------------"""

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

        '''-----------------------Модель купонов-----------------------'''
        coupons_source_model: CouponsModel = CouponsModel()  # Создаём модель.
        coupons_proxy_model: CouponsProxyModel = CouponsProxyModel()  # Создаём прокси-модель.
        coupons_proxy_model.setSourceModel(coupons_source_model)  # Подключаем исходную модель к прокси-модели.
        self.tableView.setModel(coupons_proxy_model)  # Подключаем модель к таблице.
        self.tableView.resizeColumnsToContents()  # Авторазмер столбцов под содержимое.
        '''------------------------------------------------------------'''

    def sourceModel(self) -> CouponsModel:
        """Возвращает исходную модель купонов."""
        return self.tableView.model().sourceModel()

    def setData(self, bond_class: MyBondClass | None):
        """Обновляет данные модели купонов в соответствии с выбранной облигацией."""
        self.sourceModel().updateData(bond_class)
        self.label_count.setText(str(self.tableView.model().rowCount()))  # Отображаем количество купонов.
        self.tableView.resizeColumnsToContents()  # Авторазмер столбцов под содержимое.


class GroupBox_BondsView(QtWidgets.QGroupBox):
    """Панель отображения облигаций."""
    def __init__(self, object_name: str, parent: QtWidgets.QWidget | None = ...):
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

        '''------------------------Заголовок------------------------'''
        self.horizontalLayout_title = QtWidgets.QHBoxLayout()
        self.horizontalLayout_title.setSpacing(0)
        self.horizontalLayout_title.setObjectName('horizontalLayout_title')

        spacerItem47 = QtWidgets.QSpacerItem(10, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_title.addItem(spacerItem47)

        _translate = QtCore.QCoreApplication.translate

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

    def proxyModel(self) -> BondsProxyModel:
        """Возвращает прокси-модель облигаций."""
        proxy_model = self.tableView.model()
        assert type(proxy_model) == BondsProxyModel
        return typing.cast(BondsProxyModel, proxy_model)

    def sourceModel(self) -> BondsModel:
        """Возвращает исходную модель облигаций."""
        return self.proxyModel().sourceModel()

    def setBonds(self, bond_class_list: list[MyBondClass]):
        """Устанавливает данные модели облигаций."""
        self.sourceModel().setBonds(bond_class_list)  # Передаём данные в исходную модель.
        self.tableView.resizeColumnsToContents()  # Авторазмер столбцов под содержимое.
        self.label_count.setText('{0} / {1}'.format(self.sourceModel().rowCount(), self.proxyModel().rowCount()))  # Отображаем количество облигаций.

    def setCalculationDateTime(self, calculation_datetime: datetime):
        """Устанавливает дату расчёта."""
        self.sourceModel().setDateTime(calculation_datetime)  # Передаём дату расчёта в исходную модель.
        self.tableView.resizeColumnsToContents()  # Авторазмер столбцов под содержимое.


class BondsPage(QtWidgets.QWidget):
    """Страница облигаций."""
    def __init__(self, object_name: str, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)  # QWidget __init__().
        self.setObjectName(object_name)

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
        self.groupBox_view: GroupBox_BondsView = GroupBox_BondsView('groupBox_view', self.splitter)
        '''--------------------------------------------------------------'''

        self.verticalLayout_main.addWidget(self.splitter)

        '''--------------------Модель облигаций--------------------'''
        source_model: BondsModel = BondsModel(self.groupBox_calendar.getDateTime())  # Создаём модель.
        proxy_model: BondsProxyModel = BondsProxyModel()  # Создаём прокси-модель.
        proxy_model.setSourceModel(source_model)  # Подключаем исходную модель к прокси-модели.
        self.groupBox_view.tableView.setModel(proxy_model)  # Подключаем модель к TableView.
        self.groupBox_view.tableView.resizeColumnsToContents()  # Авторазмер столбцов под содержимое.
        '''--------------------------------------------------------'''

        """-----------------------------------------------------------------------"""
        self.__token: TokenClass | None = None
        self.bonds: list[Bond] = []
        # self.coupons_thread: DividendsThread | None = None  # Поток получения дивидендов.
        """-----------------------------------------------------------------------"""

        self.groupBox_request.currentTokenChanged.connect(self.onTokenChanged)
        self.groupBox_request.currentTokenReset.connect(self.onTokenReset)
        self.groupBox_request.currentStatusChanged.connect(self.onStatusChanged)

        '''---------------------------------Фильтры---------------------------------'''
        def onFilterChanged():
            """Функция, выполняемая при изменении фильтра."""
            self._stopCouponsThread()  # Останавливаем поток получения купонов.
            token: TokenClass | None = self.token
            if token is None:
                self.bonds = []
                self.groupBox_view.setBonds([])  # Передаём в исходную модель данные.
                '''---------------Обновляет отображение количеств облигаций в моделях---------------'''
                self.groupBox_request.setCount(0)  # Количество полученных облигаций.
                self.groupBox_filters.setCount(0)  # Количество отобранных облигаций.
                '''---------------------------------------------------------------------------------'''
                self.groupBox_coupons_receiving.reset()  # Сбрасывает progressBar.
            else:
                bonds: list[Bond] = self.bonds
                filtered_bonds: list[Bond] = self.groupBox_filters.getFilteredBondsList(bonds)  # Отфильтрованный список облигаций.
                '''---------------Обновляет отображение количеств облигаций в моделях---------------'''
                self.groupBox_request.setCount(len(bonds))  # Количество полученных облигаций.
                self.groupBox_filters.setCount(len(filtered_bonds))  # Количество отобранных облигаций.
                '''---------------------------------------------------------------------------------'''
                bond_class_list: list[MyBondClass] = [MyBondClass(bond, lp) for (bond, lp) in zipWithLastPrices(token, filtered_bonds)]
                self.groupBox_view.setBonds(bond_class_list)  # Передаём в исходную модель данные.
                if bond_class_list:  # Если список не пуст.
                    self._startCouponsThread(bond_class_list)  # Запускает поток получения купонов.

        # Фильтры инструментов.
        self.groupBox_filters.groupBox_instruments_filters.comboBox_api_trade_available_flag.currentIndexChanged.connect(lambda index: onFilterChanged())
        self.groupBox_filters.groupBox_instruments_filters.comboBox_for_iis_flag.currentIndexChanged.connect(lambda index: onFilterChanged())
        self.groupBox_filters.groupBox_instruments_filters.comboBox_for_qual_investor_flag.currentIndexChanged.connect(lambda index: onFilterChanged())
        self.groupBox_filters.groupBox_instruments_filters.comboBox_liquidity_flag.currentIndexChanged.connect(lambda index: onFilterChanged())
        self.groupBox_filters.groupBox_instruments_filters.comboBox_short_enabled_flag.currentIndexChanged.connect(lambda index: onFilterChanged())
        self.groupBox_filters.groupBox_instruments_filters.comboBox_buy_available_flag.currentIndexChanged.connect(lambda index: onFilterChanged())
        self.groupBox_filters.groupBox_instruments_filters.comboBox_sell_available_flag.currentIndexChanged.connect(lambda index: onFilterChanged())
        self.groupBox_filters.groupBox_instruments_filters.comboBox_weekend_flag.currentIndexChanged.connect(lambda index: onFilterChanged())
        self.groupBox_filters.groupBox_instruments_filters.comboBox_otc_flag.currentIndexChanged.connect(lambda index: onFilterChanged())
        self.groupBox_filters.groupBox_instruments_filters.comboBox_blocked_tca_flag.currentIndexChanged.connect(lambda index: onFilterChanged())
        self.groupBox_filters.groupBox_instruments_filters.comboBox_currency.currentTextChanged.connect(lambda text: onFilterChanged())

        # Фильтры акций.
        self.groupBox_filters.groupBox_bonds_filters.comboBox_maturity.currentIndexChanged.connect(lambda index: onFilterChanged())
        self.groupBox_filters.groupBox_bonds_filters.comboBox_risk_level.currentIndexChanged.connect(lambda index: onFilterChanged())
        self.groupBox_filters.groupBox_bonds_filters.comboBox_amortization_flag.currentIndexChanged.connect(lambda index: onFilterChanged())
        self.groupBox_filters.groupBox_bonds_filters.comboBox_floating_coupon_flag.currentIndexChanged.connect(lambda index: onFilterChanged())
        self.groupBox_filters.groupBox_bonds_filters.comboBox_perpetual_flag.currentIndexChanged.connect(lambda index: onFilterChanged())
        self.groupBox_filters.groupBox_bonds_filters.comboBox_subordinated_flag.currentIndexChanged.connect(lambda index: onFilterChanged())
        '''-------------------------------------------------------------------------'''

        self.groupBox_calendar.calendarWidget.selectionChanged.connect(lambda: self.groupBox_view.setCalculationDateTime(self.groupBox_calendar.getDateTime()))

        self.groupBox_view.tableView.selectionModel().currentRowChanged.connect(lambda current, previous: self.groupBox_coupons.setData(self.groupBox_view.proxyModel().getBond(current)))  # Событие смены выбранной облигации.

    @property
    def token(self) -> TokenClass | None:
        return self.__token

    @token.setter
    def token(self, token: TokenClass | None):
        self.__token = token

    def setTokensModel(self, token_list_model: TokenListModel):
        """Устанавливает модель токенов для ComboBox'а."""
        self.groupBox_request.comboBox_token.setModel(token_list_model)

    @pyqtSlot(InstrumentStatus)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
    def onStatusChanged(self, instrument_status: InstrumentStatus):
        """Функция, выполняемая при изменении выбранного статуса инструмента."""
        self._stopCouponsThread()  # Останавливаем поток получения купонов.
        token: TokenClass | None = self.token
        if token is None:
            '''
            Если token is None, то все параметры и так уже должны иметь пустые значения,
            поэтому, возможно, этот код лишний.
            '''
            self.bonds = []
            self.groupBox_view.setBonds([])  # Передаём в исходную модель данные.
            '''---------------Обновляет отображение количеств облигаций в моделях---------------'''
            self.groupBox_request.setCount(0)  # Количество полученных облигаций.
            self.groupBox_filters.setCount(0)  # Количество отобранных облигаций.
            '''---------------------------------------------------------------------------------'''
            self.groupBox_coupons_receiving.reset()  # Сбрасывает progressBar.
        else:
            bonds_response: MyResponse = getBonds(token.token, instrument_status)  # Получение облигаций.
            assert bonds_response.request_occurred, 'Запрос облигаций не был произведён.'
            if bonds_response.ifDataSuccessfullyReceived():  # Если список облигаций был получен.
                bonds: list[Bond] = bonds_response.response_data  # Получаем список облигаций.
                self.bonds = bonds
                filtered_bonds: list[Bond] = self.groupBox_filters.getFilteredBondsList(bonds)  # Отфильтрованный список облигаций.
                '''---------------Обновляет отображение количеств облигаций в моделях---------------'''
                self.groupBox_request.setCount(len(bonds))  # Количество полученных облигаций.
                self.groupBox_filters.setCount(len(filtered_bonds))  # Количество отобранных облигаций.
                '''---------------------------------------------------------------------------------'''
                bond_class_list: list[MyBondClass] = [MyBondClass(bond, lp) for (bond, lp) in zipWithLastPrices(token, filtered_bonds)]
                self.groupBox_view.setBonds(bond_class_list)  # Передаём в исходную модель данные.
                if bond_class_list:  # Если список не пуст.
                    self._startCouponsThread(bond_class_list)  # Запускает поток получения купонов.
            else:
                self.bonds = []
                self.groupBox_view.setBonds([])  # Передаём в исходную модель данные.
                '''---------------Обновляет отображение количеств облигаций в моделях---------------'''
                self.groupBox_request.setCount(0)  # Количество полученных облигаций.
                self.groupBox_filters.setCount(0)  # Количество отобранных облигаций.
                '''---------------------------------------------------------------------------------'''
                self.groupBox_coupons_receiving.reset()  # Сбрасывает progressBar.

    @pyqtSlot()  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
    def onTokenReset(self):
        """Функция, выполняемая при выборе пустого значения вместо токена."""
        self._stopCouponsThread()  # Останавливаем поток получения купонов.
        self.token = None
        self.bonds = []
        self.groupBox_view.setBonds([])  # Передаём в исходную модель данные.
        '''---------------Обновляет отображение количеств облигаций в моделях---------------'''
        self.groupBox_request.setCount(0)  # Количество полученных облигаций.
        self.groupBox_filters.setCount(0)  # Количество отобранных облигаций.
        '''---------------------------------------------------------------------------------'''
        self.groupBox_coupons_receiving.reset()  # Сбрасывает progressBar.

    @pyqtSlot(TokenClass, InstrumentStatus)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
    def onTokenChanged(self, token: TokenClass, instrument_status: InstrumentStatus):
        """Функция, выполняемая при изменении выбранного токена."""
        self._stopCouponsThread()  # Останавливаем поток получения купонов.
        self.token = token
        bonds_response: MyResponse = getBonds(token.token, instrument_status)  # Получение облигаций.
        assert bonds_response.request_occurred, 'Запрос облигаций не был произведён.'
        if bonds_response.ifDataSuccessfullyReceived():  # Если список облигаций был получен.
            bonds: list[Bond] = bonds_response.response_data  # Извлекаем список облигаций.
            self.bonds = bonds
            filtered_bonds: list[Bond] = self.groupBox_filters.getFilteredBondsList(bonds)  # Отфильтрованный список облигаций.
            '''---------------Обновляет отображение количеств облигаций в моделях---------------'''
            self.groupBox_request.setCount(len(bonds))  # Количество полученных облигаций.
            self.groupBox_filters.setCount(len(filtered_bonds))  # Количество отобранных облигаций.
            '''---------------------------------------------------------------------------------'''
            bond_class_list: list[MyBondClass] = [MyBondClass(bond, lp) for (bond, lp) in zipWithLastPrices(token, filtered_bonds)]
            self.groupBox_view.setBonds(bond_class_list)  # Передаём в исходную модель данные.
            if bond_class_list:  # Если список не пуст.
                self._startCouponsThread(bond_class_list)  # Запускает поток получения купонов.
        else:
            self.bonds = []
            self.groupBox_view.setBonds([])  # Передаём в исходную модель данные.
            '''---------------Обновляет отображение количеств облигаций в моделях---------------'''
            self.groupBox_request.setCount(0)  # Количество полученных облигаций.
            self.groupBox_filters.setCount(0)  # Количество отобранных облигаций.
            '''---------------------------------------------------------------------------------'''
            self.groupBox_coupons_receiving.reset()  # Сбрасывает progressBar.

    def _startCouponsThread(self, bonds: list[MyBondClass]):
        """Запускает поток получения купонов."""
        assert self.groupBox_view.sourceModel().coupons_receiving_thread is None, 'Поток получения купонов должен быть завершён!'

        self.groupBox_view.sourceModel().coupons_receiving_thread = CouponsThread(token_class=self.token, bond_class_list=bonds)
        """---------------------Подключаем сигналы потока к слотам---------------------"""
        # self.groupBox_view.sourceModel().coupons_receiving_thread.printText_signal.connect(print, type=Qt.ConnectionType.BlockingQueuedConnection)  # Сигнал для отображения сообщений в консоли.
        self.groupBox_view.sourceModel().coupons_receiving_thread.printText_signal.connect(print)  # Сигнал для отображения сообщений в консоли.

        self.groupBox_view.sourceModel().coupons_receiving_thread.setProgressBarRange_signal.connect(self.groupBox_coupons_receiving.setRange)
        self.groupBox_view.sourceModel().coupons_receiving_thread.setProgressBarValue_signal.connect(self.groupBox_coupons_receiving.setValue)

        # self.groupBox_view.sourceModel().coupons_receiving_thread.showRequestError_signal.connect(self.showRequestError)
        # self.groupBox_view.sourceModel().coupons_receiving_thread.showException_signal.connect(self.showException)
        # self.groupBox_view.sourceModel().coupons_receiving_thread.clearStatusBar_signal.connect(self.statusbar.clearMessage)

        self.groupBox_view.sourceModel().coupons_receiving_thread.releaseSemaphore_signal.connect(lambda semaphore, n: semaphore.release(n))  # Освобождаем ресурсы семафора из основного потока.

        self.groupBox_view.sourceModel().coupons_receiving_thread.started.connect(lambda: print('{0}: Поток запущен. ({1})'.format(CouponsThread.__name__, getMoscowDateTime())))
        self.groupBox_view.sourceModel().coupons_receiving_thread.finished.connect(lambda: print('{0}: Поток завершён. ({1})'.format(CouponsThread.__name__, getMoscowDateTime())))
        """----------------------------------------------------------------------------"""
        self.groupBox_view.sourceModel().coupons_receiving_thread.start()  # Запускаем поток.

    def _stopCouponsThread(self):
        """Останавливаем поток получения купонов."""
        self.groupBox_view.sourceModel().stopCouponsThread()
