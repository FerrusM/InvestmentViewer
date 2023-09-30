from PyQt6 import QtCore, QtGui, QtWidgets
from tinkoff.invest import InstrumentStatus
from Classes import TokenClass
from PagesClasses import GroupBox_InstrumentsRequest, GroupBox_InstrumentsFilters, GroupBox_CalculationDate
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
        self.verticalLayout_main.addWidget(self.label_title)

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
        self.comboBox_coupons_type.addItem('')
        self.comboBox_coupons_type.addItem('')
        self.comboBox_coupons_type.addItem('')
        self.comboBox_coupons_type.addItem('')
        self.comboBox_coupons_type.addItem('')
        self.comboBox_coupons_type.addItem('')
        self.comboBox_coupons_type.addItem('')
        self.comboBox_coupons_type.addItem('')
        self.comboBox_coupons_type.addItem('')
        self.horizontalLayout_coupons_type.addWidget(self.comboBox_coupons_type)

        spacerItem_2 = QtWidgets.QSpacerItem(0, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_coupons_type.addItem(spacerItem_2)
        '''-----------------------------------------------------------------------------------'''

        self.verticalLayout_main.addLayout(self.horizontalLayout_coupons_type)
        self.verticalLayout_main.setStretch(1, 1)

        """------------------------------------retranslateUi------------------------------------"""
        _translate = QtCore.QCoreApplication.translate
        self.label_title.setText(_translate('MainWindow', 'ПОЛУЧЕНИЕ КУПОНОВ'))
        self.progressBar_coupons.setFormat(_translate('MainWindow', '%v из %m (%p%)'))
        self.label_coupons_type.setToolTip(_translate('MainWindow', 'Тип купона.'))
        self.label_coupons_type.setText(_translate('MainWindow', 'Тип купонов:'))
        self.comboBox_coupons_type.setItemText(0, _translate('MainWindow', 'Любой'))
        self.comboBox_coupons_type.setItemText(1, _translate('MainWindow', 'Постоянный'))
        self.comboBox_coupons_type.setItemText(2, _translate('MainWindow', 'Фиксированный'))
        self.comboBox_coupons_type.setItemText(3, _translate('MainWindow', 'Переменный'))
        self.comboBox_coupons_type.setItemText(4, _translate('MainWindow', 'Плавающий'))
        self.comboBox_coupons_type.setItemText(5, _translate('MainWindow', 'Дисконт'))
        self.comboBox_coupons_type.setItemText(6, _translate('MainWindow', 'Ипотечный'))
        self.comboBox_coupons_type.setItemText(7, _translate('MainWindow', 'Прочее'))
        self.comboBox_coupons_type.setItemText(8, _translate('MainWindow', 'Неопределённый'))
        """-------------------------------------------------------------------------------------"""


class GroupBox_OnlyBondsFilters(QtWidgets.QGroupBox):
    """GroupBox с фильтрами облигаций."""
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

        """----------------------------Погашенность----------------------------"""
        self.label_maturity = QtWidgets.QLabel(self)
        self.label_maturity.setObjectName('label_maturity')
        self.gridLayout_main.addWidget(self.label_maturity, 0, 0, 1, 1)

        self.comboBox_maturity = QtWidgets.QComboBox(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.comboBox_maturity.sizePolicy().hasHeightForWidth())
        self.comboBox_maturity.setSizePolicy(sizePolicy)
        self.comboBox_maturity.setObjectName('comboBox_maturity')
        self.comboBox_maturity.addItem('')
        self.comboBox_maturity.addItem('')
        self.comboBox_maturity.addItem('')
        self.gridLayout_main.addWidget(self.comboBox_maturity, 0, 1, 1, 1)
        """--------------------------------------------------------------------"""

        """---------------------------Плавающий купон---------------------------"""
        self.label_floating_coupon_flag = QtWidgets.QLabel(self)
        self.label_floating_coupon_flag.setObjectName('label_floating_coupon_flag')
        self.gridLayout_main.addWidget(self.label_floating_coupon_flag, 0, 2, 1, 1)

        self.comboBox_floating_coupon_flag = QtWidgets.QComboBox(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.comboBox_floating_coupon_flag.sizePolicy().hasHeightForWidth())
        self.comboBox_floating_coupon_flag.setSizePolicy(sizePolicy)
        self.comboBox_floating_coupon_flag.setObjectName('comboBox_floating_coupon_flag')
        self.comboBox_floating_coupon_flag.addItem('')
        self.comboBox_floating_coupon_flag.addItem('')
        self.comboBox_floating_coupon_flag.addItem('')
        self.gridLayout_main.addWidget(self.comboBox_floating_coupon_flag, 0, 3, 1, 1)
        """---------------------------------------------------------------------"""

        """----------------------------Уровень риска----------------------------"""
        self.label_risk_level = QtWidgets.QLabel(self)
        self.label_risk_level.setObjectName('label_risk_level')
        self.gridLayout_main.addWidget(self.label_risk_level, 1, 0, 1, 1)

        self.comboBox_risk_level = QtWidgets.QComboBox(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.comboBox_risk_level.sizePolicy().hasHeightForWidth())
        self.comboBox_risk_level.setSizePolicy(sizePolicy)
        self.comboBox_risk_level.setObjectName('comboBox_risk_level')
        self.comboBox_risk_level.addItem('')
        self.comboBox_risk_level.addItem('')
        self.comboBox_risk_level.addItem('')
        self.comboBox_risk_level.addItem('')
        self.comboBox_risk_level.addItem('')
        self.gridLayout_main.addWidget(self.comboBox_risk_level, 1, 1, 1, 1)
        """---------------------------------------------------------------------"""

        """----------------------------Бессрочность----------------------------"""
        self.label_perpetual_flag = QtWidgets.QLabel(self)
        self.label_perpetual_flag.setObjectName('label_perpetual_flag')
        self.gridLayout_main.addWidget(self.label_perpetual_flag, 1, 2, 1, 1)

        self.comboBox_perpetual_flag = QtWidgets.QComboBox(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.comboBox_perpetual_flag.sizePolicy().hasHeightForWidth())
        self.comboBox_perpetual_flag.setSizePolicy(sizePolicy)
        self.comboBox_perpetual_flag.setObjectName('comboBox_perpetual_flag')
        self.comboBox_perpetual_flag.addItem('')
        self.comboBox_perpetual_flag.addItem('')
        self.comboBox_perpetual_flag.addItem('')
        self.gridLayout_main.addWidget(self.comboBox_perpetual_flag, 1, 3, 1, 1)
        """--------------------------------------------------------------------"""

        """-----------------------------Амортизация-----------------------------"""
        self.label_amortization_flag = QtWidgets.QLabel(self)
        self.label_amortization_flag.setObjectName('label_amortization_flag')
        self.gridLayout_main.addWidget(self.label_amortization_flag, 2, 0, 1, 1)

        self.comboBox_amortization_flag = QtWidgets.QComboBox(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.comboBox_amortization_flag.sizePolicy().hasHeightForWidth())
        self.comboBox_amortization_flag.setSizePolicy(sizePolicy)
        self.comboBox_amortization_flag.setObjectName('comboBox_amortization_flag')
        self.comboBox_amortization_flag.addItem('')
        self.comboBox_amortization_flag.addItem('')
        self.comboBox_amortization_flag.addItem('')
        self.gridLayout_main.addWidget(self.comboBox_amortization_flag, 2, 1, 1, 1)
        """---------------------------------------------------------------------"""

        """-------------------------------Суборд-------------------------------"""
        self.label_subordinated_flag = QtWidgets.QLabel(self)
        self.label_subordinated_flag.setObjectName('label_subordinated_flag')
        self.gridLayout_main.addWidget(self.label_subordinated_flag, 2, 2, 1, 1)

        self.comboBox_subordinated_flag = QtWidgets.QComboBox(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.comboBox_subordinated_flag.sizePolicy().hasHeightForWidth())
        self.comboBox_subordinated_flag.setSizePolicy(sizePolicy)
        self.comboBox_subordinated_flag.setObjectName('comboBox_subordinated_flag')
        self.comboBox_subordinated_flag.addItem('')
        self.comboBox_subordinated_flag.addItem('')
        self.comboBox_subordinated_flag.addItem('')
        self.gridLayout_main.addWidget(self.comboBox_subordinated_flag, 2, 3, 1, 1)
        """--------------------------------------------------------------------"""

        self.verticalLayout_main.addLayout(self.gridLayout_main)

        """------------------------------------retranslateUi------------------------------------"""
        _translate = QtCore.QCoreApplication.translate
        self.setTitle(_translate('MainWindow', 'Фильтры облигаций'))
        self.label_maturity.setToolTip(_translate("MainWindow", "Флаг, отображающий погашенность облигации к текущей дате."))
        self.label_maturity.setText(_translate("MainWindow", "Погашенность:"))
        self.comboBox_maturity.setItemText(0, _translate("MainWindow", "Все"))
        self.comboBox_maturity.setItemText(1, _translate("MainWindow", "Непогашенные"))
        self.comboBox_maturity.setItemText(2, _translate("MainWindow", "Погашенные"))
        self.label_floating_coupon_flag.setToolTip(_translate("MainWindow", "Признак облигации с плавающим купоном."))
        self.label_floating_coupon_flag.setText(_translate("MainWindow", "Плавающий купон:"))
        self.comboBox_floating_coupon_flag.setItemText(0, _translate("MainWindow", "Все"))
        self.comboBox_floating_coupon_flag.setItemText(1, _translate("MainWindow", "True"))
        self.comboBox_floating_coupon_flag.setItemText(2, _translate("MainWindow", "False"))
        self.label_risk_level.setToolTip(_translate("MainWindow", "Уровень риска."))
        self.label_risk_level.setText(_translate("MainWindow", "Уровень риска:"))
        self.comboBox_risk_level.setItemText(0, _translate("MainWindow", "Любой"))
        self.comboBox_risk_level.setItemText(1, _translate("MainWindow", "Низкий"))
        self.comboBox_risk_level.setItemText(2, _translate("MainWindow", "Средний"))
        self.comboBox_risk_level.setItemText(3, _translate("MainWindow", "Высокий"))
        self.comboBox_risk_level.setItemText(4, _translate("MainWindow", "Неизвестен"))
        self.label_perpetual_flag.setToolTip(_translate("MainWindow", "Признак бессрочной облигации."))
        self.label_perpetual_flag.setText(_translate("MainWindow", "Бессрочность:"))
        self.comboBox_perpetual_flag.setItemText(0, _translate("MainWindow", "Все"))
        self.comboBox_perpetual_flag.setItemText(1, _translate("MainWindow", "True"))
        self.comboBox_perpetual_flag.setItemText(2, _translate("MainWindow", "False"))
        self.label_amortization_flag.setToolTip(_translate("MainWindow", "Признак облигации с амортизацией долга."))
        self.label_amortization_flag.setText(_translate("MainWindow", "Амортизация:"))
        self.comboBox_amortization_flag.setItemText(0, _translate("MainWindow", "Все"))
        self.comboBox_amortization_flag.setItemText(1, _translate("MainWindow", "True"))
        self.comboBox_amortization_flag.setItemText(2, _translate("MainWindow", "False"))
        self.label_subordinated_flag.setToolTip(_translate("MainWindow", "Признак субординированной облигации."))
        self.label_subordinated_flag.setText(_translate("MainWindow", "Суборд:"))
        self.comboBox_subordinated_flag.setItemText(0, _translate("MainWindow", "Все"))
        self.comboBox_subordinated_flag.setItemText(1, _translate("MainWindow", "True"))
        self.comboBox_subordinated_flag.setItemText(2, _translate("MainWindow", "False"))
        """-------------------------------------------------------------------------------------"""

        self.comboBox_maturity.setCurrentIndex(1)
        self.comboBox_floating_coupon_flag.setCurrentIndex(0)
        self.comboBox_perpetual_flag.setCurrentIndex(0)
        self.comboBox_amortization_flag.setCurrentIndex(0)
        self.comboBox_subordinated_flag.setCurrentIndex(0)


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

        _translate = QtCore.QCoreApplication.translate
        self.label_title.setText(_translate('MainWindow', 'КУПОНЫ'))
        self.label_count.setText(_translate('MainWindow', '0'))


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

        """------------------------Заголовок------------------------"""
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

        spacerItem49 = QtWidgets.QSpacerItem(10, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_title.addItem(spacerItem49)

        self.horizontalLayout_title.setStretch(1, 1)
        self.horizontalLayout_title.setStretch(2, 1)
        self.horizontalLayout_title.setStretch(4, 2)
        self.verticalLayout_main.addLayout(self.horizontalLayout_title)
        """---------------------------------------------------------"""

        self.tableView = QtWidgets.QTableView(self)
        self.tableView.setEnabled(True)
        self.tableView.setBaseSize(QtCore.QSize(0, 557))
        self.tableView.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tableView.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.tableView.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.tableView.setSortingEnabled(True)
        self.tableView.setObjectName('tableView')
        self.verticalLayout_main.addWidget(self.tableView)

        _translate = QtCore.QCoreApplication.translate
        self.lineEdit_search.setPlaceholderText(_translate('MainWindow', 'Поиск...'))
        self.label_title.setText(_translate('MainWindow', 'ОБЛИГАЦИИ'))
        self.label_count.setText(_translate('MainWindow', '0 / 0'))


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
        self.bonds_groupBox_filters: GroupBox_BondsFilters = GroupBox_BondsFilters('bonds_groupBox_filters', self.layoutWidget)
        self.verticalLayout_filters.addWidget(self.bonds_groupBox_filters)
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

    def setTokensModel(self, token_list_model: TokenListModel):
        """Устанавливает модель токенов для ComboBox'а."""
        self.groupBox_request.comboBox_token.setModel(token_list_model)

    def getCurrentToken(self) -> TokenClass | None:
        """Возвращает выбранный в ComboBox'е токен."""
        return self.groupBox_request.getCurrentToken()

    def getCurrentStatus(self) -> InstrumentStatus:
        """Возвращает выбранный в ComboBox'е статус."""
        return self.groupBox_request.getCurrentStatus()
