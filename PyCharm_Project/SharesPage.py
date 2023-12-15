import enum
import typing
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import pyqtSlot
from tinkoff.invest import Share, InstrumentStatus, ShareType, Dividend
from Classes import TokenClass
from DividendsModel import DividendsModel, DividendsProxyModel
from DividendsThread import DividendsThread
from MyDatabase import MainConnection
from MyDateTime import getMoscowDateTime
from MyRequests import MyResponse, getShares, RequestTryClass
from MyShareClass import MyShareClass
from PagesClasses import GroupBox_InstrumentsFilters, GroupBox_InstrumentsRequest, GroupBox_CalculationDate, appFilter_Flag, zipWithLastPrices, ProgressBar_DataReceiving
from SharesModel import SharesProxyModel, SharesModel
from TokenModel import TokenListModel


class GroupBox_OnlySharesFilters(QtWidgets.QGroupBox):
    """GroupBox с фильтрами акций."""
    @enum.unique  # Декоратор, требующий, чтобы все элементы имели разные значения.
    class Filters(enum.IntEnum):
        """Перечисление фильтров акций."""
        SHARE_TYPE = 0  # Тип акции.
        DIV_YIELD_FLAG = 1  # Признак наличия дивидендной доходности.

    def __init__(self, object_name: str, parent: QtWidgets.QWidget | None = ...):
        super().__init__(parent)  # QGroupBox __init__().
        self.setObjectName(object_name)

        self.gridLayout_main = QtWidgets.QGridLayout(self)
        self.gridLayout_main.setContentsMargins(2, 2, 2, 2)
        self.gridLayout_main.setHorizontalSpacing(7)
        self.gridLayout_main.setVerticalSpacing(2)
        self.gridLayout_main.setObjectName('gridLayout_main')

        """-----------------------------Тип акции-----------------------------"""
        self.label_share_type = QtWidgets.QLabel(self)
        self.label_share_type.setObjectName('label_share_type')
        self.gridLayout_main.addWidget(self.label_share_type, 0, 0, 1, 1)

        self.comboBox_share_type = QtWidgets.QComboBox(self)
        self.comboBox_share_type.setObjectName('comboBox_share_type')
        self.comboBox_share_type.addItem('')
        self.comboBox_share_type.addItem('')
        self.comboBox_share_type.addItem('')
        self.comboBox_share_type.addItem('')
        self.comboBox_share_type.addItem('')
        self.comboBox_share_type.addItem('')
        self.comboBox_share_type.addItem('')
        self.comboBox_share_type.addItem('')
        self.comboBox_share_type.addItem('')
        self.comboBox_share_type.addItem('')
        self.gridLayout_main.addWidget(self.comboBox_share_type, 0, 1, 1, 1)
        """-------------------------------------------------------------------"""

        """---------------Признак наличия дивидендной доходности---------------"""
        self.label_div_yield_flag = QtWidgets.QLabel(self)
        self.label_div_yield_flag.setObjectName('label_div_yield_flag')
        self.gridLayout_main.addWidget(self.label_div_yield_flag, 0, 2, 1, 1)

        self.comboBox_div_yield_flag = QtWidgets.QComboBox(self)
        self.comboBox_div_yield_flag.setObjectName('comboBox_div_yield_flag')
        self.comboBox_div_yield_flag.addItem('')
        self.comboBox_div_yield_flag.addItem('')
        self.comboBox_div_yield_flag.addItem('')
        self.gridLayout_main.addWidget(self.comboBox_div_yield_flag, 0, 3, 1, 1)
        """--------------------------------------------------------------------"""

        '''------------------------------------retranslateUi------------------------------------'''
        _translate = QtCore.QCoreApplication.translate
        self.setTitle(_translate('MainWindow', 'Фильтры акций'))
        self.label_share_type.setToolTip(_translate('MainWindow', 'Тип акции.'))
        self.label_share_type.setText(_translate('MainWindow', 'Тип:'))
        self.comboBox_share_type.setItemText(0, _translate('MainWindow', 'Все'))
        self.comboBox_share_type.setItemText(1, _translate('MainWindow', 'Не определён'))
        self.comboBox_share_type.setItemText(2, _translate('MainWindow', 'Обыкновенные'))
        self.comboBox_share_type.setItemText(3, _translate('MainWindow', 'Привилегированные'))
        self.comboBox_share_type.setItemText(4, _translate('MainWindow', 'АДР'))
        self.comboBox_share_type.setItemText(5, _translate('MainWindow', 'ГДР'))
        self.comboBox_share_type.setItemText(6, _translate('MainWindow', 'ТОО'))
        self.comboBox_share_type.setItemText(7, _translate('MainWindow', 'Акции из Нью-Йорка'))
        self.comboBox_share_type.setItemText(8, _translate('MainWindow', 'Закрытый ИФ'))
        self.comboBox_share_type.setItemText(9, _translate('MainWindow', 'Траст недвижимости'))
        self.label_div_yield_flag.setToolTip(_translate('MainWindow', 'Признак наличия дивидендной доходности.'))
        self.label_div_yield_flag.setText(_translate('MainWindow', 'Дивиденды:'))
        self.comboBox_div_yield_flag.setItemText(0, _translate('MainWindow', 'Все'))
        self.comboBox_div_yield_flag.setItemText(1, _translate('MainWindow', 'True'))
        self.comboBox_div_yield_flag.setItemText(2, _translate('MainWindow', 'False'))
        '''-------------------------------------------------------------------------------------'''

        '''------------------------------------Фильтры акций------------------------------------'''
        def appFilter_ShareType(share_type: ShareType, filter: str) -> bool:
            """Проверяет, удовлетворяет ли тип акции фильтру."""
            match filter:
                case 'Все': return True
                case 'Не определён': return True if share_type == ShareType.SHARE_TYPE_UNSPECIFIED else False
                case 'Обыкновенные': return True if share_type == ShareType.SHARE_TYPE_COMMON else False
                case 'Привилегированные': return True if share_type == ShareType.SHARE_TYPE_PREFERRED else False
                case 'АДР': return True if share_type == ShareType.SHARE_TYPE_ADR else False
                case 'ГДР': return True if share_type == ShareType.SHARE_TYPE_GDR else False
                case 'ТОО': return True if share_type == ShareType.SHARE_TYPE_MLP else False
                case 'Акции из Нью-Йорка': return True if share_type == ShareType.SHARE_TYPE_NY_REG_SHRS else False
                case 'Закрытый ИФ': return True if share_type == ShareType.SHARE_TYPE_CLOSED_END_FUND else False
                case 'Траст недвижимости': return True if share_type == ShareType.SHARE_TYPE_REIT else False
                case _: raise ValueError('Некорректное значение фильтра по типу акции ({0})!'.format(filter))

        self.filters: dict = {
            self.Filters.SHARE_TYPE:
                lambda share: appFilter_ShareType(share.share_type, self.comboBox_share_type.currentText()),
            self.Filters.DIV_YIELD_FLAG:
                lambda share: appFilter_Flag(share.div_yield_flag, self.comboBox_div_yield_flag.currentText()),
        }
        '''-------------------------------------------------------------------------------------'''

    def checkFilters(self, share: Share) -> bool:
        """Проверяет акцию на соответствие фильтрам."""
        for filter in self.filters.values():
            if not filter(share): return False
        return True


class GroupBox_SharesFilters(QtWidgets.QGroupBox):
    """GroupBox со всеми фильтрами акций."""
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

        spacerItem16 = QtWidgets.QSpacerItem(10, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_title.addItem(spacerItem16)

        spacerItem17 = QtWidgets.QSpacerItem(0, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_title.addItem(spacerItem17)

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

        spacerItem18 = QtWidgets.QSpacerItem(10, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_title.addItem(spacerItem18)

        self.verticalLayout_main.addLayout(self.horizontalLayout_title)
        """-------------------------------------------------------------"""

        """---------------------Фильтры инструментов---------------------"""
        self.horizontalLayout_instruments_filters = QtWidgets.QHBoxLayout()
        self.horizontalLayout_instruments_filters.setSpacing(0)
        self.horizontalLayout_instruments_filters.setObjectName('horizontalLayout_instruments_filters')

        self.groupBox_instruments_filters = GroupBox_InstrumentsFilters('groupBox_instruments_filters', self)
        self.horizontalLayout_instruments_filters.addWidget(self.groupBox_instruments_filters)

        spacerItem19 = QtWidgets.QSpacerItem(0, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_instruments_filters.addItem(spacerItem19)

        self.verticalLayout_main.addLayout(self.horizontalLayout_instruments_filters)
        """--------------------------------------------------------------"""

        """------------------------Фильтры акций------------------------"""
        self.horizontalLayout_share_filters = QtWidgets.QHBoxLayout()
        self.horizontalLayout_share_filters.setSpacing(0)
        self.horizontalLayout_share_filters.setObjectName('horizontalLayout_share_filters')

        self.groupBox_shares_filters: GroupBox_OnlySharesFilters = GroupBox_OnlySharesFilters('groupBox_shares_filters', self)
        self.horizontalLayout_share_filters.addWidget(self.groupBox_shares_filters)

        spacerItem20 = QtWidgets.QSpacerItem(0, 17, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_share_filters.addItem(spacerItem20)

        self.verticalLayout_main.addLayout(self.horizontalLayout_share_filters)
        """-------------------------------------------------------------"""

        _translate = QtCore.QCoreApplication.translate
        self.label_title.setText(_translate('MainWindow', 'ФИЛЬТРЫ'))
        self.label_count.setText(_translate('MainWindow', '0'))

    def _checkFilters(self, share: Share) -> bool:
        """Проверяет акцию на соответствие фильтрам."""
        return self.groupBox_instruments_filters.checkFilters(share) & self.groupBox_shares_filters.checkFilters(share)

    def getFilteredSharesList(self, shares: list[Share]) -> list[Share]:
        """Фильтрует список акций и возвращает отфильтрованный список."""
        filtered_list: list[Share] = list(filter(self._checkFilters, shares))
        # self.setCount(len(filtered_list))  # Обновляет количество отобранных акций.
        return filtered_list

    def setCount(self, count: int):
        """Устанавливает количество отобранных акций."""
        self.label_count.setText(str(count))


class GroupBox_DividendsView(QtWidgets.QGroupBox):
    """Панель отображения дивидендов акций."""
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

        _translate = QtCore.QCoreApplication.translate

        """------------------------Заголовок------------------------"""
        self.horizontalLayout_title = QtWidgets.QHBoxLayout()
        self.horizontalLayout_title.setSpacing(0)
        self.horizontalLayout_title.setObjectName('horizontalLayout_title')
        spacerItem22 = QtWidgets.QSpacerItem(10, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_title.addItem(spacerItem22)
        spacerItem23 = QtWidgets.QSpacerItem(0, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_title.addItem(spacerItem23)

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
        self.label_title.setText(_translate('MainWindow', 'ДИВИДЕНДЫ'))

        self.label_count = QtWidgets.QLabel(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_count.sizePolicy().hasHeightForWidth())
        self.label_count.setSizePolicy(sizePolicy)
        self.label_count.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignTrailing | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.label_count.setObjectName('label_count')
        self.horizontalLayout_title.addWidget(self.label_count)
        self.label_count.setText(_translate('MainWindow', '0'))

        spacerItem24 = QtWidgets.QSpacerItem(10, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_title.addItem(spacerItem24)

        self.verticalLayout_main.addLayout(self.horizontalLayout_title)
        """---------------------------------------------------------"""

        """------------------Отображение дивидендов------------------"""
        self.tableView = QtWidgets.QTableView(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.tableView.sizePolicy().hasHeightForWidth())
        self.tableView.setSizePolicy(sizePolicy)
        self.tableView.setStyleSheet("background-color: rgb(255, 255, 255);")
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

        """--------------------Модель дивидендов--------------------"""
        dividends_source_model: DividendsModel = DividendsModel()  # Создаём модель.
        dividends_proxy_model: DividendsProxyModel = DividendsProxyModel()  # Создаём прокси-модель.
        dividends_proxy_model.setSourceModel(dividends_source_model)  # Подключаем исходную модель к прокси-модели.
        self.tableView.setModel(dividends_proxy_model)  # Подключаем модель к таблице.
        self.tableView.resizeColumnsToContents()  # Авторазмер столбцов под содержимое.
        """---------------------------------------------------------"""

    def sourceModel(self) -> DividendsModel:
        """Возвращает исходную модель дивидендов."""
        return self.tableView.model().sourceModel()

    def setData(self, share_class: MyShareClass | None):
        """Обновляет данные модели дивидендов в соответствии с выбранной акцией."""
        if share_class is None:
            self.sourceModel().updateData([])
        else:
            dividends: list[Dividend] | None = share_class.dividends
            self.sourceModel().updateData([] if dividends is None else dividends)
        self.tableView.resizeColumnsToContents()  # Авторазмер столбцов под содержимое.
        self.label_count.setText(str(self.tableView.model().rowCount()))  # Отображаем количество дивидендов.


class GroupBox_SharesView(QtWidgets.QGroupBox):
    """Панель отображения акций."""
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

        spacerItem25 = QtWidgets.QSpacerItem(10, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_title.addItem(spacerItem25)

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

        spacerItem26 = QtWidgets.QSpacerItem(0, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_title.addItem(spacerItem26)

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
        self.label_title.setText(_translate('MainWindow', 'АКЦИИ'))
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

        spacerItem27 = QtWidgets.QSpacerItem(10, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_title.addItem(spacerItem27)

        self.horizontalLayout_title.setStretch(1, 1)
        self.horizontalLayout_title.setStretch(2, 1)
        self.horizontalLayout_title.setStretch(4, 2)
        self.verticalLayout_main.addLayout(self.horizontalLayout_title)
        """---------------------------------------------------------"""

        """--------------------Отображение акций--------------------"""
        self.tableView = QtWidgets.QTableView(self)
        self.tableView.setEnabled(True)
        self.tableView.setBaseSize(QtCore.QSize(0, 557))
        self.tableView.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tableView.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.tableView.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.tableView.setSortingEnabled(True)
        self.tableView.setObjectName('tableView')
        self.tableView.horizontalHeader().setSortIndicatorShown(True)
        self.tableView.verticalHeader().setSortIndicatorShown(False)
        self.verticalLayout_main.addWidget(self.tableView)
        """---------------------------------------------------------"""

        """----------------------Модель акций----------------------"""
        source_model: SharesModel = SharesModel()  # Создаём модель.
        proxy_model: SharesProxyModel = SharesProxyModel()  # Создаём прокси-модель.
        proxy_model.setSourceModel(source_model)  # Подключаем исходную модель к прокси-модели.
        self.tableView.setModel(proxy_model)  # Подключаем модель к TableView.
        self.tableView.resizeColumnsToContents()  # Авторазмер столбцов под содержимое.
        """--------------------------------------------------------"""

    def proxyModel(self) -> SharesProxyModel:
        """Возвращает прокси-модель акций."""
        proxy_model = self.tableView.model()
        assert type(proxy_model) == SharesProxyModel
        return typing.cast(SharesProxyModel, proxy_model)

    def sourceModel(self) -> SharesModel:
        """Возвращает исходную модель акций."""
        return self.proxyModel().sourceModel()

    def setShares(self, share_class_list: list[MyShareClass]):
        """Устанавливает данные модели акций."""
        self.sourceModel().setShares(share_class_list)  # Передаём данные в исходную модель.
        self.tableView.resizeColumnsToContents()  # Авторазмер столбцов под содержимое.
        self.label_count.setText('{0} / {1}'.format(self.sourceModel().rowCount(), self.proxyModel().rowCount()))  # Отображаем количество акций.


class GroupBox_DividendsReceiving(QtWidgets.QGroupBox):
    """Панель прогресса получения дивидендов."""
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

        self.label_title = QtWidgets.QLabel(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_title.sizePolicy().hasHeightForWidth())
        self.label_title.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setBold(True)
        self.label_title.setFont(font)
        self.label_title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.label_title.setObjectName('label_title')
        self.verticalLayout_main.addWidget(self.label_title)

        _translate = QtCore.QCoreApplication.translate

        '''-------------------------ProgressBar-------------------------'''
        self.progressBar_dividends = ProgressBar_DataReceiving('progressBar_dividends', self)
        self.verticalLayout_main.addWidget(self.progressBar_dividends)
        '''-------------------------------------------------------------'''

        self.label_title.setText(_translate('MainWindow', 'ПОЛУЧЕНИЕ ДИВИДЕНДОВ'))

    def setRange(self, minimum: int, maximum: int):
        """Устанавливает минимум и максимум для progressBar'а."""
        self.progressBar_dividends.setRange(minimum, maximum)

    def setValue(self, value: int):
        """Изменяет прогресс в progressBar'е"""
        self.progressBar_dividends.setValue(value)

    def reset(self):
        """Сбрасывает progressBar."""
        self.progressBar_dividends.reset()


class SharesPage(QtWidgets.QWidget):
    """Страница акций."""
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

        self.verticalLayout_dividends_receiving = QtWidgets.QVBoxLayout()
        self.verticalLayout_dividends_receiving.setSpacing(0)
        self.verticalLayout_dividends_receiving.setObjectName('verticalLayout_dividends_receiving')

        """------------Панель прогресса получения дивидендов------------"""
        self.groupBox_dividends_receiving: GroupBox_DividendsReceiving = GroupBox_DividendsReceiving('groupBox_dividends_receiving', self.layoutWidget)
        self.verticalLayout_dividends_receiving.addWidget(self.groupBox_dividends_receiving)
        """-------------------------------------------------------------"""

        spacerItem15 = QtWidgets.QSpacerItem(20, 0, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        self.verticalLayout_dividends_receiving.addItem(spacerItem15)

        self.horizontalLayout_top_top.addLayout(self.verticalLayout_dividends_receiving)
        self.horizontalLayout_top_top.setStretch(1, 1)
        self.verticalLayout_top.addLayout(self.horizontalLayout_top_top)

        self.horizontalLayout_top_bottom = QtWidgets.QHBoxLayout()
        self.horizontalLayout_top_bottom.setSpacing(2)
        self.horizontalLayout_top_bottom.setObjectName('horizontalLayout_top_bottom')

        self.verticalLayout_top_bottom_left = QtWidgets.QVBoxLayout()
        self.verticalLayout_top_bottom_left.setSpacing(0)
        self.verticalLayout_top_bottom_left.setObjectName('verticalLayout_top_bottom_left')

        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setSpacing(2)
        self.horizontalLayout_2.setObjectName('horizontalLayout_2')

        """---------------------Панель даты расчёта---------------------"""
        self.groupBox_calendar = GroupBox_CalculationDate('groupBox_calendar', self.layoutWidget)
        self.horizontalLayout_2.addWidget(self.groupBox_calendar)
        """-------------------------------------------------------------"""

        """-----------------------Панель фильтров-----------------------"""
        self.groupBox_filters: GroupBox_SharesFilters = GroupBox_SharesFilters('groupBox_filters', self.layoutWidget)
        self.horizontalLayout_2.addWidget(self.groupBox_filters)
        """-------------------------------------------------------------"""

        self.verticalLayout_top_bottom_left.addLayout(self.horizontalLayout_2)

        spacerItem21 = QtWidgets.QSpacerItem(20, 0, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        self.verticalLayout_top_bottom_left.addItem(spacerItem21)

        self.verticalLayout_top_bottom_left.setStretch(1, 1)
        self.horizontalLayout_top_bottom.addLayout(self.verticalLayout_top_bottom_left)

        """----------------Панель отображения дивидендов----------------"""
        self.groupBox_dividends = GroupBox_DividendsView('groupBox_dividends', self.layoutWidget)
        self.horizontalLayout_top_bottom.addWidget(self.groupBox_dividends)
        """-------------------------------------------------------------"""

        self.horizontalLayout_top_bottom.setStretch(1, 1)

        self.verticalLayout_top.addLayout(self.horizontalLayout_top_bottom)
        self.verticalLayout_top.setStretch(1, 1)

        """-------------------Панель отображения акций-------------------"""
        self.groupBox_view: GroupBox_SharesView = GroupBox_SharesView('groupBox_view', self.splitter)
        """--------------------------------------------------------------"""

        self.verticalLayout_main.addWidget(self.splitter)

        """---------------------------------Токен---------------------------------"""
        self.token: TokenClass | None = None
        self.shares: list[Share] = []
        self.dividends_thread: DividendsThread | None = None  # Поток получения дивидендов.
        """-----------------------------------------------------------------------"""

        self.groupBox_request.currentTokenChanged.connect(self.onTokenChanged)
        self.groupBox_request.currentTokenReset.connect(self.onTokenReset)
        self.groupBox_request.currentStatusChanged.connect(self.onStatusChanged)

        '''---------------------------------Фильтры---------------------------------'''
        def onFilterChanged():
            """Функция, выполняемая при изменении фильтра."""
            self._stopDividendsThread()  # Останавливаем поток получения дивидендов.
            token: TokenClass | None = self.token
            if token is None:
                self.shares = []
                self.groupBox_view.setShares([])  # Передаём в исходную модель данные.
                self.groupBox_dividends.setData(None)  # Сбрасываем модель дивидендов.
                '''-----------------Обновляет отображение количеств акций в моделях-----------------'''
                self.groupBox_request.setCount(0)  # Количество полученных акций.
                self.groupBox_filters.setCount(0)  # Количество отобранных акций.
                '''---------------------------------------------------------------------------------'''
                self.groupBox_dividends_receiving.reset()  # Сбрасывает progressBar.
            else:
                shares: list[Share] = self.shares
                filtered_shares: list[Share] = self.groupBox_filters.getFilteredSharesList(shares)  # Отфильтрованный список акций.
                '''-----------------Обновляет отображение количеств акций в моделях-----------------'''
                self.groupBox_request.setCount(len(shares))  # Количество полученных акций.
                self.groupBox_filters.setCount(len(filtered_shares))  # Количество отобранных акций.
                '''---------------------------------------------------------------------------------'''

                share_class_list: list[MyShareClass] = [MyShareClass(share, lp) for (share, lp) in zipWithLastPrices(token, filtered_shares)]
                self.groupBox_view.setShares(share_class_list)  # Передаём в исходную модель данные.
                self.groupBox_dividends.setData(None)  # Сбрасываем модель дивидендов.
                if share_class_list:  # Если список не пуст.
                    self._startDividendsThread(token, share_class_list)  # Запускает поток получения дивидендов.

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
        self.groupBox_filters.groupBox_shares_filters.comboBox_share_type.currentIndexChanged.connect(lambda index: onFilterChanged())
        self.groupBox_filters.groupBox_shares_filters.comboBox_div_yield_flag.currentIndexChanged.connect(lambda index: onFilterChanged())
        '''-------------------------------------------------------------------------'''

        # @pyqtSlot(QModelIndex, QModelIndex)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
        # def onCurrentRowChanged(current: QModelIndex, previous: QModelIndex):
        #     """Событие при изменении выбранной акции."""
        #     share_class: MyShareClass | None = self.groupBox_view.proxyModel().getShare(current)
        #     self.groupBox_dividends.setData(share_class)
        #     print('Выбрана акция: {0}'.format(share_class.share.name))

        # self.groupBox_view.tableView.selectionModel().currentRowChanged.connect(onCurrentRowChanged)  # Событие смены выбранной акции.
        self.groupBox_view.tableView.selectionModel().currentRowChanged.connect(lambda current, previous: self.groupBox_dividends.setData(self.groupBox_view.proxyModel().getShare(current)))  # Событие смены выбранной акции.

    def setTokensModel(self, token_list_model: TokenListModel):
        """Устанавливает модель токенов для ComboBox'а."""
        self.groupBox_request.setTokensModel(token_list_model)

    def __reset(self):
        """Сбрасывает акции."""
        self.shares = []
        self.groupBox_view.setShares([])  # Передаём в исходную модель данные.
        self.groupBox_dividends.setData(None)  # Сбрасываем модель дивидендов.
        '''-----------------Обновляет отображение количеств акций в моделях-----------------'''
        self.groupBox_request.setCount(0)  # Количество полученных акций.
        self.groupBox_filters.setCount(0)  # Количество отобранных акций.
        '''---------------------------------------------------------------------------------'''
        self.groupBox_dividends_receiving.reset()  # Сбрасывает progressBar.

    @pyqtSlot(InstrumentStatus)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
    def onStatusChanged(self, instrument_status: InstrumentStatus):
        """Функция, выполняемая при изменении выбранного статуса инструмента."""
        self._stopDividendsThread()  # Останавливаем поток получения дивидендов.
        token: TokenClass | None = self.token
        if token is None:
            '''
            Если token is None, то все параметры и так уже должны иметь пустые значения,
            поэтому, возможно, этот код лишний.
            '''
            self.__reset()  # Сбрасывает акции.
        else:
            shares_response: MyResponse = getShares(token.token, instrument_status)  # Получение акций.
            assert shares_response.request_occurred, 'Запрос акций не был произведён.'
            if shares_response.ifDataSuccessfullyReceived():  # Если список акций был получен.
                shares: list[Share] = shares_response.response_data  # Извлекаем список акций.
                MainConnection.addShares(shares)  # Добавляем акции в таблицу акций.
                self.shares = shares
                filtered_shares: list[Share] = self.groupBox_filters.getFilteredSharesList(shares)  # Отфильтрованный список акций.

                '''-----------------Обновляет отображение количеств акций в моделях-----------------'''
                self.groupBox_request.setCount(len(shares))  # Количество полученных акций.
                self.groupBox_filters.setCount(len(filtered_shares))  # Количество отобранных акций.
                '''---------------------------------------------------------------------------------'''

                share_class_list: list[MyShareClass] = [MyShareClass(share, lp) for (share, lp) in zipWithLastPrices(token, filtered_shares)]
                self.groupBox_view.setShares(share_class_list)  # Передаём в исходную модель данные.
                self.groupBox_dividends.setData(None)  # Сбрасываем модель дивидендов.
                if share_class_list:  # Если список не пуст.
                    self._startDividendsThread(token, share_class_list)  # Запускает поток получения дивидендов.
            else:
                self.__reset()  # Сбрасывает акции.

    @pyqtSlot()  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
    def onTokenReset(self):
        """Функция, выполняемая при выборе пустого значения вместо токена."""
        self._stopDividendsThread()  # Останавливаем поток получения дивидендов.
        self.token = None
        self.__reset()  # Сбрасывает акции.

    @pyqtSlot(TokenClass, InstrumentStatus)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
    def onTokenChanged(self, token: TokenClass, instrument_status: InstrumentStatus):
        """Функция, выполняемая при изменении выбранного токена."""
        self._stopDividendsThread()  # Останавливаем поток получения дивидендов.
        self.token = token

        shares_try_count: RequestTryClass = RequestTryClass(2)
        shares_response: MyResponse = MyResponse()
        while shares_try_count and not shares_response.ifDataSuccessfullyReceived():
            shares_response: MyResponse = getShares(token.token, instrument_status)  # Получение акций.
            assert shares_response.request_occurred, 'Запрос акций не был произведён.'
            shares_try_count += 1

        if shares_response.ifDataSuccessfullyReceived():  # Если список акций был получен.
            shares: list[Share] = shares_response.response_data  # Получаем список акций.
            MainConnection.addShares(shares)  # Добавляем акции в таблицу акций.
            self.shares = shares
            filtered_shares: list[Share] = self.groupBox_filters.getFilteredSharesList(shares)  # Отфильтрованный список акций.
            '''-----------------Обновляет отображение количеств акций в моделях-----------------'''
            self.groupBox_request.setCount(len(shares))  # Количество полученных акций.
            self.groupBox_filters.setCount(len(filtered_shares))  # Количество отобранных акций.
            '''---------------------------------------------------------------------------------'''
            share_class_list: list[MyShareClass] = [MyShareClass(share, lp) for (share, lp) in zipWithLastPrices(token, filtered_shares)]
            self.groupBox_view.setShares(share_class_list)  # Передаём в исходную модель данные.
            self.groupBox_dividends.setData(None)  # Сбрасываем модель дивидендов.
            if share_class_list:  # Если список не пуст.
                self._startDividendsThread(token, share_class_list)  # Запускает поток получения дивидендов.
        else:
            self.__reset()  # Сбрасывает акции.

    def _startDividendsThread(self, token: TokenClass, share_class_list: list[MyShareClass]):
        """Запускает поток получения дивидендов."""
        assert self.dividends_thread is None, 'Поток заполнения дивидендов должен быть завершён!'

        self.dividends_thread = DividendsThread(parent=self, token_class=token, share_class_list=share_class_list)
        """---------------------Подключаем сигналы потока к слотам---------------------"""
        self.dividends_thread.printText_signal.connect(print)  # Сигнал для отображения сообщений в консоли.

        self.dividends_thread.setProgressBarRange_signal.connect(self.groupBox_dividends_receiving.setRange)
        self.dividends_thread.setProgressBarValue_signal.connect(self.groupBox_dividends_receiving.setValue)

        # self.dividends_thread.showRequestError_signal.connect(self.showRequestError)
        # self.dividends_thread.showException_signal.connect(self.showException)
        # self.dividends_thread.clearStatusBar_signal.connect(self.statusbar.clearMessage)

        self.dividends_thread.releaseSemaphore_signal.connect(lambda semaphore, n: semaphore.release(n))  # Освобождаем ресурсы семафора из основного потока.

        self.dividends_thread.started.connect(lambda: print('{0}: Поток запущен. ({1})'.format(DividendsThread.__name__, getMoscowDateTime())))
        self.dividends_thread.finished.connect(lambda: print('{0}: Поток завершён. ({1})'.format(DividendsThread.__name__, getMoscowDateTime())))
        """----------------------------------------------------------------------------"""
        self.dividends_thread.start()  # Запускаем поток.

    def _stopDividendsThread(self):
        """Останавливает поток получения дивидендов."""
        if self.dividends_thread is not None:  # Если поток был создан.
            self.dividends_thread.requestInterruption()  # Сообщаем потоку о том, что надо завершиться.
            self.dividends_thread.wait()  # Ждём завершения потока.
            self.dividends_thread = None
