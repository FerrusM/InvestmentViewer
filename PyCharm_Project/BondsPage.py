import enum
import typing
from datetime import datetime
from PyQt6 import QtCore, QtWidgets
from PyQt6.QtCore import pyqtSlot
from tinkoff.invest import InstrumentStatus, Bond
from tinkoff.invest.schemas import RiskLevel
from old_BondsModel import BondsModel, BondsProxyModel
from Classes import TokenClass, print_slot
from CouponsModel import CouponsModel, CouponsProxyModel
from CouponsThread import CouponsThread
from MyBondClass import MyBondClass, MyBond
from MyDatabase import MainConnection
from MyDateTime import getMoscowDateTime
from MyRequests import MyResponse, getBonds, RequestTryClass
from PagesClasses import GroupBox_InstrumentsRequest, GroupBox_InstrumentsFilters, GroupBox_CalculationDate, \
    appFilter_Flag, zipWithLastPrices3000, ProgressBar_DataReceiving, TitleWithCount, TitleLabel
from TokenModel import TokenListModel


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

        label_coupons_type = QtWidgets.QLabel(text='Тип купонов:', parent=self)
        label_coupons_type.setToolTip('Тип купона.')
        horizontalLayout_coupons_type.addWidget(label_coupons_type, 0)

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
        horizontalLayout_coupons_type.addWidget(self.comboBox_coupons_type)

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
    def __init__(self, object_name: str, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)
        self.setObjectName(object_name)

        verticalLayout_main = QtWidgets.QVBoxLayout(self)
        verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        verticalLayout_main.setSpacing(0)

        """--------------------------Заголовок--------------------------"""
        self.titlebar = TitleWithCount(title='ФИЛЬТРЫ', count_text='0', parent=self)
        verticalLayout_main.addLayout(self.titlebar, 0)
        """-------------------------------------------------------------"""

        """---------------------Фильтры инструментов---------------------"""
        horizontalLayout_instruments_filters = QtWidgets.QHBoxLayout()
        horizontalLayout_instruments_filters.setSpacing(0)

        """---------------------Панель фильтров инструментов---------------------"""
        self.groupBox_instruments_filters = GroupBox_InstrumentsFilters('groupBox_instruments_filters', self)
        horizontalLayout_instruments_filters.addWidget(self.groupBox_instruments_filters)
        """----------------------------------------------------------------------"""

        horizontalLayout_instruments_filters.addStretch(1)

        verticalLayout_main.addLayout(horizontalLayout_instruments_filters, 0)
        """--------------------------------------------------------------"""

        """----------------------Фильтры облигаций----------------------"""
        horizontalLayout_bond_filters = QtWidgets.QHBoxLayout()
        horizontalLayout_bond_filters.setSpacing(0)

        self.groupBox_bonds_filters: GroupBox_OnlyBondsFilters = GroupBox_OnlyBondsFilters('groupBox_bonds_filters', self)
        horizontalLayout_bond_filters.addWidget(self.groupBox_bonds_filters)

        horizontalLayout_bond_filters.addStretch(1)

        verticalLayout_main.addLayout(horizontalLayout_bond_filters, 0)
        """-------------------------------------------------------------"""

        verticalLayout_main.addStretch(1)

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
        self.titlebar.setCount(str(count))


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

        verticalLayout_main = QtWidgets.QVBoxLayout(self)
        verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        verticalLayout_main.setSpacing(2)

        """------------------------Заголовок------------------------"""
        self.titlebar = TitleWithCount(title='КУПОНЫ', count_text='0', parent=self)
        verticalLayout_main.addLayout(self.titlebar, 0)
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
        verticalLayout_main.addWidget(self.tableView, 1)
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
        """Обновляет данные модели купонов в соответствии с выбранной облигацией."""
        self.sourceModel().updateData(bond_class)
        self.titlebar.setCount(str(self.tableView.model().rowCount()))  # Отображаем количество купонов.
        self.tableView.resizeColumnsToContents()  # Авторазмер столбцов под содержимое.


class GroupBox_BondsView(QtWidgets.QGroupBox):
    """Панель отображения облигаций."""
    def __init__(self, object_name: str, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(sizePolicy)
        self.setBaseSize(QtCore.QSize(0, 0))
        self.setObjectName(object_name)

        verticalLayout_main = QtWidgets.QVBoxLayout(self)
        verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        verticalLayout_main.setSpacing(2)

        '''------------------------Заголовок------------------------'''
        self.horizontalLayout_title = QtWidgets.QHBoxLayout()
        self.horizontalLayout_title.setSpacing(0)

        self.horizontalLayout_title.addSpacing(10)

        self.lineEdit_search = QtWidgets.QLineEdit(self)
        self.lineEdit_search.setSizePolicy(sizePolicy)
        self.lineEdit_search.setPlaceholderText('Поиск...')
        self.horizontalLayout_title.addWidget(self.lineEdit_search, 1)

        self.horizontalLayout_title.addStretch(1)
        self.horizontalLayout_title.addWidget(TitleLabel(text='ОБЛИГАЦИИ', parent=self), 0)

        self.label_count = QtWidgets.QLabel(text='0 / 0', parent=self)
        self.label_count.setSizePolicy(sizePolicy)
        self.label_count.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignTrailing | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.horizontalLayout_title.addWidget(self.label_count, 2)

        self.horizontalLayout_title.addSpacing(10)

        verticalLayout_main.addLayout(self.horizontalLayout_title, 0)
        '''---------------------------------------------------------'''

        '''------------------Отображение облигаций------------------'''
        self.tableView = QtWidgets.QTableView(self)
        self.tableView.setEnabled(True)
        self.tableView.setBaseSize(QtCore.QSize(0, 557))
        self.tableView.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tableView.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.tableView.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.tableView.setSortingEnabled(True)
        verticalLayout_main.addWidget(self.tableView, 1)
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

        def resizeDependsOnCalculationDateTimeColumns():
            """Подгоняет ширину столбцов под содержимое для столбцов, зависящих от даты расчёта."""
            for i, column in self.sourceModel().columns.items():
                if column.dependsOnEnteredDate():
                    self.tableView.resizeColumnToContents(i)

        resizeDependsOnCalculationDateTimeColumns()  # Авторазмер столбцов зависящих от даты расчёта под содержимое.


class BondsPage(QtWidgets.QWidget):
    """Страница облигаций."""
    def __init__(self, object_name: str, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)
        self.setObjectName(object_name)

        verticalLayout_main = QtWidgets.QVBoxLayout(self)
        verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        verticalLayout_main.setSpacing(2)

        splitter = QtWidgets.QSplitter(orientation=QtCore.Qt.Orientation.Vertical, parent=self)

        layoutWidget = QtWidgets.QWidget(splitter)

        verticalLayout_top = QtWidgets.QVBoxLayout(layoutWidget)
        verticalLayout_top.setContentsMargins(0, 0, 0, 0)
        verticalLayout_top.setSpacing(2)

        horizontalLayout_top_top = QtWidgets.QHBoxLayout()
        horizontalLayout_top_top.setSpacing(2)
        """------------------Панель выполнения запроса------------------"""
        self.groupBox_request = GroupBox_InstrumentsRequest('groupBox_request', layoutWidget)
        horizontalLayout_top_top.addWidget(self.groupBox_request, 0)
        """-------------------------------------------------------------"""
        """--------------Панель прогресса получения купонов--------------"""
        self.groupBox_coupons_receiving = GroupBox_CouponsReceiving('groupBox_coupons_receiving', layoutWidget)
        horizontalLayout_top_top.addWidget(self.groupBox_coupons_receiving, 1)
        """--------------------------------------------------------------"""
        verticalLayout_top.addLayout(horizontalLayout_top_top, 0)

        horizontalLayout_top_bottom = QtWidgets.QHBoxLayout()
        horizontalLayout_top_bottom.setSpacing(2)

        verticalLayout_calendar = QtWidgets.QVBoxLayout()
        verticalLayout_calendar.setSpacing(0)
        """---------------------Панель даты расчёта---------------------"""
        self.groupBox_calendar = GroupBox_CalculationDate('groupBox_calendar', layoutWidget)
        verticalLayout_calendar.addWidget(self.groupBox_calendar, 0)
        """-------------------------------------------------------------"""
        verticalLayout_calendar.addStretch(1)
        horizontalLayout_top_bottom.addLayout(verticalLayout_calendar, 0)

        verticalLayout_filters = QtWidgets.QVBoxLayout()
        verticalLayout_filters.setSpacing(0)
        """-----------------------Панель фильтров-----------------------"""
        self.groupBox_filters = GroupBox_BondsFilters('groupBox_filters', layoutWidget)
        verticalLayout_filters.addWidget(self.groupBox_filters, 0)
        """-------------------------------------------------------------"""
        verticalLayout_filters.addStretch(1)
        horizontalLayout_top_bottom.addLayout(verticalLayout_filters, 0)

        """------------------Панель отображения купонов------------------"""
        self.groupBox_coupons = GroupBox_CouponsView('groupBox_coupons', layoutWidget)
        horizontalLayout_top_bottom.addWidget(self.groupBox_coupons, 1)
        """--------------------------------------------------------------"""

        verticalLayout_top.addLayout(horizontalLayout_top_bottom, 1)

        '''-----------------Панель отображения облигаций-----------------'''
        self.groupBox_view = GroupBox_BondsView('groupBox_view', splitter)
        '''--------------------------------------------------------------'''

        verticalLayout_main.addWidget(splitter)

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
                self.groupBox_coupons.setData(None)  # Сбрасываем модель купонов.
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
                bond_class_list: list[MyBondClass] = [MyBondClass(bond, lp) for (bond, lp) in zipWithLastPrices3000(token, filtered_bonds)]
                self.groupBox_view.setBonds(bond_class_list)  # Передаём в исходную модель данные.
                self.groupBox_coupons.setData(None)  # Сбрасываем модель купонов.
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

    def __reset(self):
        """Сбрасывает облигации."""
        self.bonds = []
        self.groupBox_view.setBonds([])  # Передаём в исходную модель данные.
        self.groupBox_coupons.setData(None)  # Сбрасываем модель купонов.
        '''---------------Обновляет отображение количеств облигаций в моделях---------------'''
        self.groupBox_request.setCount(0)  # Количество полученных облигаций.
        self.groupBox_filters.setCount(0)  # Количество отобранных облигаций.
        '''---------------------------------------------------------------------------------'''
        self.groupBox_coupons_receiving.reset()  # Сбрасывает progressBar.

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
            self.__reset()  # Сбрасывает облигации.
        else:
            bonds_response: MyResponse = getBonds(token.token, instrument_status)  # Получение облигаций.
            assert bonds_response.request_occurred, 'Запрос облигаций не был произведён.'
            if bonds_response.ifDataSuccessfullyReceived():  # Если список облигаций был получен.
                bonds: list[Bond] = bonds_response.response_data  # Получаем список облигаций.
                MainConnection.addBonds(token.token, instrument_status, bonds)  # Добавляем облигации в таблицу облигаций.
                self.bonds = bonds
                filtered_bonds: list[Bond] = self.groupBox_filters.getFilteredBondsList(bonds)  # Отфильтрованный список облигаций.
                '''---------------Обновляет отображение количеств облигаций в моделях---------------'''
                self.groupBox_request.setCount(len(bonds))  # Количество полученных облигаций.
                self.groupBox_filters.setCount(len(filtered_bonds))  # Количество отобранных облигаций.
                '''---------------------------------------------------------------------------------'''
                bond_class_list: list[MyBondClass] = [MyBondClass(bond, lp) for (bond, lp) in zipWithLastPrices3000(token, filtered_bonds)]
                self.groupBox_view.setBonds(bond_class_list)  # Передаём в исходную модель данные.
                self.groupBox_coupons.setData(None)  # Сбрасываем модель купонов.
                if bond_class_list:  # Если список не пуст.
                    self._startCouponsThread(bond_class_list)  # Запускает поток получения купонов.
            else:
                self.__reset()  # Сбрасывает облигации.

    @pyqtSlot()  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
    def onTokenReset(self):
        """Функция, выполняемая при выборе пустого значения вместо токена."""
        self._stopCouponsThread()  # Останавливаем поток получения купонов.
        self.token = None
        self.__reset()  # Сбрасывает облигации.

    @pyqtSlot(TokenClass, InstrumentStatus)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
    def onTokenChanged(self, token: TokenClass, instrument_status: InstrumentStatus):
        """Функция, выполняемая при изменении выбранного токена."""
        self._stopCouponsThread()  # Останавливаем поток получения купонов.
        self.token = token

        bonds_try_count: RequestTryClass = RequestTryClass(2)
        bonds_response: MyResponse = MyResponse()
        while bonds_try_count and not bonds_response.ifDataSuccessfullyReceived():
            bonds_response: MyResponse = getBonds(token.token, instrument_status)  # Получение облигаций.
            assert bonds_response.request_occurred, 'Запрос облигаций не был произведён.'
            bonds_try_count += 1

        if bonds_response.ifDataSuccessfullyReceived():  # Если список облигаций был получен.
            bonds: list[Bond] = bonds_response.response_data  # Извлекаем список облигаций.
            MainConnection.addBonds(token.token, instrument_status, bonds)  # Добавляем облигации в таблицу облигаций.
            self.bonds = bonds
            filtered_bonds: list[Bond] = self.groupBox_filters.getFilteredBondsList(bonds)  # Отфильтрованный список облигаций.
            '''---------------Обновляет отображение количеств облигаций в моделях---------------'''
            self.groupBox_request.setCount(len(bonds))  # Количество полученных облигаций.
            self.groupBox_filters.setCount(len(filtered_bonds))  # Количество отобранных облигаций.
            '''---------------------------------------------------------------------------------'''
            bond_class_list: list[MyBondClass] = [MyBondClass(bond, lp) for (bond, lp) in zipWithLastPrices3000(token, filtered_bonds)]
            self.groupBox_view.setBonds(bond_class_list)  # Передаём в исходную модель данные.
            self.groupBox_coupons.setData(None)  # Сбрасываем модель купонов.
            if bond_class_list:  # Если список не пуст.
                self._startCouponsThread(bond_class_list)  # Запускает поток получения купонов.
        else:
            self.__reset()  # Сбрасывает облигации.

    def _startCouponsThread(self, bonds: list[MyBondClass]):
        """Запускает поток получения купонов."""
        assert self.groupBox_view.sourceModel().coupons_receiving_thread is None, 'Поток получения купонов должен быть завершён!'

        self.groupBox_view.sourceModel().coupons_receiving_thread = CouponsThread(token_class=self.token, bond_class_list=bonds)
        """---------------------Подключаем сигналы потока к слотам---------------------"""
        # self.groupBox_view.sourceModel().coupons_receiving_thread.printText_signal.connect(print)  # Сигнал для отображения сообщений в консоли.
        self.groupBox_view.sourceModel().coupons_receiving_thread.printText_signal.connect(print_slot)  # Сигнал для отображения сообщений в консоли.

        self.groupBox_view.sourceModel().coupons_receiving_thread.setProgressBarRange_signal.connect(self.groupBox_coupons_receiving.setRange)
        self.groupBox_view.sourceModel().coupons_receiving_thread.setProgressBarValue_signal.connect(self.groupBox_coupons_receiving.setValue)

        # self.groupBox_view.sourceModel().coupons_receiving_thread.showRequestError_signal.connect(self.showRequestError)
        # self.groupBox_view.sourceModel().coupons_receiving_thread.showException_signal.connect(self.showException)

        self.groupBox_view.sourceModel().coupons_receiving_thread.couponsReceived.connect(MainConnection.setCoupons)

        self.groupBox_view.sourceModel().coupons_receiving_thread.releaseSemaphore_signal.connect(lambda semaphore, n: semaphore.release(n))  # Освобождаем ресурсы семафора из основного потока.

        self.groupBox_view.sourceModel().coupons_receiving_thread.started.connect(lambda: print('{0}: Поток запущен. ({1})'.format(CouponsThread.__name__, getMoscowDateTime())))
        self.groupBox_view.sourceModel().coupons_receiving_thread.finished.connect(lambda: print('{0}: Поток завершён. ({1})'.format(CouponsThread.__name__, getMoscowDateTime())))
        """----------------------------------------------------------------------------"""
        self.groupBox_view.sourceModel().coupons_receiving_thread.start()  # Запускаем поток.

    def _stopCouponsThread(self):
        """Останавливаем поток получения купонов."""
        self.groupBox_view.sourceModel().stopCouponsThread()
