import enum
from PyQt6 import QtCore, QtGui, QtWidgets
from tinkoff.invest import Share, LastPrice, InstrumentStatus, ShareType
from Classes import TokenClass
from DividendsModel import DividendsModel, DividendsProxyModel
from DividendsThread import DividendsThread
from MyRequests import MyResponse, getLastPrices, getShares
from MyShareClass import MyShareClass
from PagesClasses import GroupBox_InstrumentsFilters, GroupBox_InstrumentsRequest, GroupBox_CalculationDate
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

        """------------------------------------retranslateUi------------------------------------"""
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
        """-------------------------------------------------------------------------------------"""

        '''------------------------------------Фильтры акций------------------------------------'''
        def appFilter_Flag(flag: bool, filter: str) -> bool:
            """Проверяет, удовлетворяет ли акция фильтру с возможными значениями "Все", "True" и "False"."""
            match filter:
                case 'True': return flag
                case 'False': return not flag
                case 'Все': return True
                case _: raise ValueError('Некорректное значение фильтра ({0})!'.format(filter))

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
        return list(filter(self._checkFilters, shares))

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

        """------------------------Заголовок------------------------"""
        self.horizontalLayout_title = QtWidgets.QHBoxLayout()
        self.horizontalLayout_title.setSpacing(0)
        self.horizontalLayout_title.setObjectName('horizontalLayout_title')
        spacerItem22 = QtWidgets.QSpacerItem(10, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_title.addItem(spacerItem22)
        spacerItem23 = QtWidgets.QSpacerItem(0, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_title.addItem(spacerItem23)

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

    def setData(self, share_class: MyShareClass | None):
        """Обновляет данные модели дивидендов в соответствии с выбранной акцией."""
        if share_class is None:
            self.tableView.model().sourceModel().updateData([])
        else:
            self.tableView.model().sourceModel().updateData(share_class.dividends)
        self.label_count.setText(str(self.tableView.model().rowCount()))  # Отображаем количество дивидендов.
        self.tableView.resizeColumnsToContents()  # Авторазмер столбцов под содержимое.


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
        return self.tableView.model()

    def sourceModel(self) -> SharesModel:
        """Возвращает исходную модель акций."""
        return self.proxyModel().sourceModel()

    def setShares(self, share_class_list: list[MyShareClass]):
        """Устанавливает данные модели акций."""
        self.sourceModel().setShares(share_class_list)  # Передаём данные в исходную модель.
        self.tableView.resizeColumnsToContents()  # Авторазмер столбцов под содержимое.

    def updateShares(self, token_class: TokenClass, shares: list[Share]):
        """Обновляет данные модели акций в соответствии с указанными на форме параметрами."""
        share_class_list: list[MyShareClass] = []
        '''
        Если передать в запрос get_last_prices() пустой массив, то метод вернёт цены последних сделок
        всех доступных для торговли инструментов. Поэтому, если отфильтрованный список акций пуст,
        то следует пропустить запрос цен последних сделок. 
        '''
        if shares:
            shares_figi_list: list[str] = [share.figi for share in shares]
            last_prices_response: MyResponse = getLastPrices(token_class.token, shares_figi_list)
            last_prices: list[LastPrice] = last_prices_response.response_data

            '''------------------Проверка полученного списка последних цен------------------'''
            last_prices_figi_list: list[str] = [last_price.figi for last_price in last_prices]
            for share in shares:
                figi_count: int = last_prices_figi_list.count(share.figi)
                if figi_count == 1:
                    last_price_number: int = last_prices_figi_list.index(share.figi)
                    last_price: LastPrice = last_prices[last_price_number]
                    share_class_list.append(MyShareClass(share, last_price))
                elif figi_count > 1:
                    assert False, 'Список последних цен акций содержит несколько элементов с одним и тем же figi ().'.format(share.figi)
                else:
                    '''
                    Если список последних цен не содержит ни одного подходящего элемента,
                    то заполняем поле last_price значением None.
                    '''
                    share_class_list.append(MyShareClass(share, None))
            '''-----------------------------------------------------------------------------'''

            # share_class_list: list[MyShareClass] = [MyShareClass(share, last_price) for share, last_price in zip(shares, last_prices)]
        else:  # Если список отфильтрованных акций пуст.
            pass

        self.setShares(share_class_list)  # Передаём в исходную модель акций данные.


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

        self.progressBar_dividends = QtWidgets.QProgressBar(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.progressBar_dividends.sizePolicy().hasHeightForWidth())
        self.progressBar_dividends.setSizePolicy(sizePolicy)
        self.progressBar_dividends.setMinimumSize(QtCore.QSize(0, 26))
        self.progressBar_dividends.setStyleSheet('text-align: center;')
        self.progressBar_dividends.setMaximum(0)
        self.progressBar_dividends.setProperty('value', 0)
        self.progressBar_dividends.setObjectName('progressBar_dividends')
        self.verticalLayout_main.addWidget(self.progressBar_dividends)

        _translate = QtCore.QCoreApplication.translate
        self.label_title.setText(_translate('MainWindow', 'ПОЛУЧЕНИЕ ДИВИДЕНДОВ'))
        self.progressBar_dividends.setFormat(_translate('MainWindow', '%v из %m (%p%)'))

    def setRange(self, minimum: int, maximum: int):
        """Устанавливает минимум и максимум для progressBar'а. Если максимум равен нулю, то скрывает бегающую полоску."""
        if maximum == 0:
            '''setRange(0, 0) устанавливает неопределённое состояние progressBar'а, чего хотелось бы избежать.'''
            self.progressBar_dividends.setRange(minimum, 100)  # Устанавливает минимум и максимум для progressBar'а.
        else:
            self.progressBar_dividends.setRange(minimum, maximum)  # Устанавливает минимум и максимум для progressBar'а.
        self.progressBar_dividends.setValue(0)
        self.progressBar_dividends.reset()  # Сбрасывает progressBar.

    def setValue(self, value: int):
        """Изменяет прогресс в progressBar'е"""
        self.progressBar_dividends.setValue(value)


class SharesPage(QtWidgets.QWidget):
    """Страница акций."""
    def __init__(self, object_name: str, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)  # QWidget __init__().
        self.setStyleSheet('')
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

        self.groupBox_request.comboBox_token.currentIndexChanged.connect(lambda index: self.onTokenChanged(self.getCurrentToken()))
        """-----------------------------------------------------------------------"""

        '''---------------------------------Фильтры---------------------------------'''
        def onFilterChanged():
            """Функция, выполняемая при изменении фильтра."""
            filtered_shares: list[Share] = self.groupBox_filters.getFilteredSharesList(self.shares)  # Отфильтрованный список акций.
            filtered_shares_class_list: list[MyShareClass] = [MyShareClass(share) for share in filtered_shares]
            self.groupBox_view.setShares(filtered_shares_class_list)  # Передаём в исходную модель акций данные.
            self._startDividendsThread(filtered_shares_class_list)  # Запускает поток получения дивидендов.

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

        # @pyqtSlot(QModelIndex, QModelIndex)  # Декоратор, который помечает функцию как qt-слот и ускоряет его выполнение.
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

    def getCurrentToken(self) -> TokenClass | None:
        """Возвращает выбранный в ComboBox'е токен."""
        return self.groupBox_request.getCurrentToken()

    def getCurrentStatus(self) -> InstrumentStatus:
        """Возвращает выбранный в ComboBox'е статус."""
        return self.groupBox_request.getCurrentStatus()

    def onTokenChanged(self, token: TokenClass | None):
        """Функция, выполняемая при изменении выбранного токена."""
        self._stopDividendsThread()  # Останавливаем поток получения дивидендов.
        self.token = token
        if self.token is None:
            self.shares = []
            self.groupBox_view.setShares([])  # Передаём в исходную модель акций данные.
        else:
            '''------------------------------Получение акций------------------------------'''
            shares_response: MyResponse = getShares(self.token.token, self.getCurrentStatus())
            self.shares = shares_response.response_data  # Получаем список акций.
            '''---------------------------------------------------------------------------'''

            filtered_shares: list[Share] = self.groupBox_filters.getFilteredSharesList(self.shares)  # Отфильтрованный список акций.
            filtered_shares_class_list: list[MyShareClass] = [MyShareClass(share) for share in filtered_shares]
            self.groupBox_view.setShares(filtered_shares_class_list)  # Передаём в исходную модель акций данные.
            # self.groupBox_view.updateShares(token, filtered_shares)

            # """------------------Отображение количеств акций на форме------------------"""
            # shares_count: int = len(self.shares)  # Количество полученных акций.
            # filtered_count: int = len(filtered_shares)  # Количество отобранных акций.
            # self.groupBox_request.setCount(shares_count)  # Отображаем количество полученных акций.
            # self.groupBox_filters.setCount(filtered_count)  # Кол-во отобранных акций.
            # self.groupBox_view.label_count.setText('{0} / {1}'.format(filtered_count, shares_count))  # Отображаем количество акций.
            # """------------------------------------------------------------------------"""

            self._startDividendsThread(filtered_shares_class_list)  # Запускает поток получения дивидендов.

    def _startDividendsThread(self, share_class_list: list[MyShareClass]):
        """Запускает поток получения дивидендов."""
        self.dividends_thread = DividendsThread(parent=self, token_class=self.token, share_class_list=share_class_list)
        """---------------------Подключаем сигналы потока к слотам---------------------"""
        self.dividends_thread.printText_signal.connect(print)  # Сигнал для отображения сообщений в консоли.

        self.dividends_thread.setProgressBarRange_signal.connect(self.groupBox_dividends_receiving.setRange)
        self.dividends_thread.setProgressBarValue_signal.connect(self.groupBox_dividends_receiving.setValue)

        # self.dividends_thread.showRequestError_signal.connect(self.showRequestError)
        # self.dividends_thread.showException_signal.connect(self.showException)
        # self.dividends_thread.clearStatusBar_signal.connect(self.statusbar.clearMessage)

        self.dividends_thread.releaseSemaphore_signal.connect(lambda semaphore, n: semaphore.release(n))  # Освобождаем ресурсы семафора из основного потока.
        """----------------------------------------------------------------------------"""
        self.dividends_thread.start()  # Запускаем поток.

    def _stopDividendsThread(self):
        """Останавливает поток получения дивидендов."""
        if self.dividends_thread is not None:  # Если поток был создан.
            self.dividends_thread.requestInterruption()  # Сообщаем потоку о том, что надо завершиться.
            self.dividends_thread.wait()  # Ждём завершения потока.
            self.dividends_thread = None
