import enum
import typing
from PyQt6 import QtCore, QtWidgets
from PyQt6.QtCore import pyqtSlot
from tinkoff.invest import Share, InstrumentStatus, ShareType, Dividend
from Classes import TokenClass, TITLE_FONT
from DividendsModel import DividendsModel, DividendsProxyModel
from DividendsThread import DividendsThread
from MyDatabase import MainConnection
from MyDateTime import getMoscowDateTime
from MyRequests import MyResponse, getShares, RequestTryClass
from MyShareClass import MyShareClass
from PagesClasses import GroupBox_InstrumentsFilters, GroupBox_InstrumentsRequest, GroupBox_CalculationDate, \
    appFilter_Flag, zipWithLastPrices3000, ProgressBar_DataReceiving, TitleWithCount, TitleLabel
from SharesModel import SharesProxyModel, SharesModel
from TokenModel import TokenListModel


class GroupBox_OnlySharesFilters(QtWidgets.QGroupBox):
    """GroupBox с фильтрами акций."""
    @enum.unique  # Декоратор, требующий, чтобы все элементы имели разные значения.
    class Filters(enum.IntEnum):
        """Перечисление фильтров акций."""
        SHARE_TYPE = 0  # Тип акции.
        DIV_YIELD_FLAG = 1  # Признак наличия дивидендной доходности.

    def __init__(self, object_name: str, parent: QtWidgets.QWidget | None = None):
        super().__init__(title='Фильтры акций', parent=parent)
        self.setObjectName(object_name)

        self.gridLayout_main = QtWidgets.QGridLayout(self)
        self.gridLayout_main.setContentsMargins(2, 2, 2, 2)
        self.gridLayout_main.setHorizontalSpacing(7)
        self.gridLayout_main.setVerticalSpacing(2)

        """-----------------------------Тип акции-----------------------------"""
        self.label_share_type = QtWidgets.QLabel(text='Тип:', parent=self)
        self.label_share_type.setToolTip('Тип акции.')
        self.gridLayout_main.addWidget(self.label_share_type, 0, 0, 1, 1)

        self.comboBox_share_type = QtWidgets.QComboBox(self)
        self.comboBox_share_type.addItems(
            ('Все', 'Не определён', 'Обыкновенные', 'Привилегированные', 'АДР', 'ГДР', 'ТОО', 'Акции из Нью-Йорка',
             'Закрытый ИФ', 'Траст недвижимости')
        )

        self.gridLayout_main.addWidget(self.comboBox_share_type, 0, 1, 1, 1)
        """-------------------------------------------------------------------"""

        """---------------Признак наличия дивидендной доходности---------------"""
        self.label_div_yield_flag = QtWidgets.QLabel(text='Дивиденды:', parent=self)
        self.label_div_yield_flag.setToolTip('Признак наличия дивидендной доходности.')
        self.gridLayout_main.addWidget(self.label_div_yield_flag, 0, 2, 1, 1)

        self.comboBox_div_yield_flag = QtWidgets.QComboBox(parent=self)
        self.comboBox_div_yield_flag.addItems(('Все', 'True', 'False'))

        self.gridLayout_main.addWidget(self.comboBox_div_yield_flag, 0, 3, 1, 1)
        """--------------------------------------------------------------------"""

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
    def __init__(self, object_name: str, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)
        self.setObjectName(object_name)

        verticalLayout_main = QtWidgets.QVBoxLayout(self)
        verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        verticalLayout_main.setSpacing(0)

        """--------------------------Заголовок--------------------------"""
        self.titlebar = TitleWithCount(title='ФИЛЬТРЫ', count_text='0', parent=parent)
        verticalLayout_main.addLayout(self.titlebar, 0)
        """-------------------------------------------------------------"""

        """---------------------Фильтры инструментов---------------------"""
        horizontalLayout_instruments_filters = QtWidgets.QHBoxLayout(self)
        horizontalLayout_instruments_filters.setSpacing(0)

        self.groupBox_instruments_filters = GroupBox_InstrumentsFilters('groupBox_instruments_filters', self)
        horizontalLayout_instruments_filters.addWidget(self.groupBox_instruments_filters, 0)

        horizontalLayout_instruments_filters.addStretch(1)

        verticalLayout_main.addLayout(horizontalLayout_instruments_filters, 0)
        """--------------------------------------------------------------"""

        """------------------------Фильтры акций------------------------"""
        horizontalLayout_share_filters = QtWidgets.QHBoxLayout(self)
        horizontalLayout_share_filters.setSpacing(0)

        self.groupBox_shares_filters = GroupBox_OnlySharesFilters('groupBox_shares_filters', self)
        horizontalLayout_share_filters.addWidget(self.groupBox_shares_filters, 0)

        horizontalLayout_share_filters.addStretch(1)

        verticalLayout_main.addLayout(horizontalLayout_share_filters, 0)
        """-------------------------------------------------------------"""

        verticalLayout_main.addStretch(1)

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
        self.titlebar.setCount(str(count))


class GroupBox_DividendsView(QtWidgets.QGroupBox):
    """Панель отображения дивидендов акций."""
    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)

        verticalLayout_main = QtWidgets.QVBoxLayout(self)
        verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        verticalLayout_main.setSpacing(2)

        """------------------------Заголовок------------------------"""
        self.titlebar = TitleWithCount(title='ДИВИДЕНДЫ', count_text='0', parent=self)
        verticalLayout_main.addLayout(self.titlebar, 0)
        """---------------------------------------------------------"""

        """------------------Отображение дивидендов------------------"""
        self.tableView = QtWidgets.QTableView(self)
        self.tableView.setStyleSheet("background-color: rgb(255, 255, 255);")
        self.tableView.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.tableView.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.tableView.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tableView.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.tableView.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.tableView.setGridStyle(QtCore.Qt.PenStyle.SolidLine)
        self.tableView.setSortingEnabled(True)
        verticalLayout_main.addWidget(self.tableView, 1)
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
        self.titlebar.setCount(str(self.tableView.model().rowCount()))  # Отображаем количество дивидендов.


class GroupBox_SharesView(QtWidgets.QGroupBox):
    """Панель отображения акций."""
    def __init__(self, object_name: str, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)
        self.setObjectName(object_name)

        verticalLayout_main = QtWidgets.QVBoxLayout(self)
        verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        verticalLayout_main.setSpacing(2)

        """------------------------Заголовок------------------------"""
        horizontalLayout_title = QtWidgets.QHBoxLayout(self)
        horizontalLayout_title.setSpacing(0)

        horizontalLayout_title.addSpacing(10)

        self.lineEdit_search = QtWidgets.QLineEdit(self)
        self.lineEdit_search.setPlaceholderText('Поиск...')
        horizontalLayout_title.addWidget(self.lineEdit_search, 1)

        horizontalLayout_title.addStretch(1)

        horizontalLayout_title.addWidget(TitleLabel(text='АКЦИИ', parent=self), 0)

        self.label_count = QtWidgets.QLabel(text='0 / 0', parent=self)
        self.label_count.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignTrailing | QtCore.Qt.AlignmentFlag.AlignVCenter)
        horizontalLayout_title.addWidget(self.label_count, 2)

        horizontalLayout_title.addSpacing(10)

        verticalLayout_main.addLayout(horizontalLayout_title)
        """---------------------------------------------------------"""

        """--------------------Отображение акций--------------------"""
        self.tableView = QtWidgets.QTableView(self)
        self.tableView.setEnabled(True)
        self.tableView.setBaseSize(QtCore.QSize(0, 557))
        self.tableView.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tableView.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.tableView.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.tableView.setSortingEnabled(True)
        self.tableView.horizontalHeader().setSortIndicatorShown(True)
        self.tableView.verticalHeader().setSortIndicatorShown(False)
        verticalLayout_main.addWidget(self.tableView, 1)
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

        self.label_title = QtWidgets.QLabel(text='ПОЛУЧЕНИЕ ДИВИДЕНДОВ', parent=self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_title.sizePolicy().hasHeightForWidth())
        self.label_title.setSizePolicy(sizePolicy)
        self.label_title.setFont(TITLE_FONT)
        self.label_title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.verticalLayout_main.addWidget(self.label_title)

        '''-------------------------ProgressBar-------------------------'''
        self.progressBar_dividends = ProgressBar_DataReceiving(parent=self)
        self.verticalLayout_main.addWidget(self.progressBar_dividends)
        '''-------------------------------------------------------------'''

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
    def __init__(self, tokens_model: TokenListModel, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)

        verticalLayout_main = QtWidgets.QVBoxLayout(self)
        verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        verticalLayout_main.setSpacing(2)

        splitter = QtWidgets.QSplitter(orientation=QtCore.Qt.Orientation.Vertical, parent=self)
        layoutWidget = QtWidgets.QWidget()
        splitter.addWidget(layoutWidget)
        splitter.setStretchFactor(0, 0)

        verticalLayout_top = QtWidgets.QVBoxLayout(layoutWidget)
        verticalLayout_top.setContentsMargins(0, 0, 0, 0)
        verticalLayout_top.setSpacing(2)

        horizontalLayout_top_top = QtWidgets.QHBoxLayout()
        horizontalLayout_top_top.setSpacing(2)

        """------------------Панель выполнения запроса------------------"""
        self.groupBox_request = GroupBox_InstrumentsRequest('groupBox_request', layoutWidget)
        horizontalLayout_top_top.addWidget(self.groupBox_request, 0)
        """-------------------------------------------------------------"""

        verticalLayout_dividends_receiving = QtWidgets.QVBoxLayout()
        verticalLayout_dividends_receiving.setSpacing(0)
        """------------Панель прогресса получения дивидендов------------"""
        self.groupBox_dividends_receiving = GroupBox_DividendsReceiving('groupBox_dividends_receiving', layoutWidget)
        verticalLayout_dividends_receiving.addWidget(self.groupBox_dividends_receiving, 0)
        """-------------------------------------------------------------"""
        verticalLayout_dividends_receiving.addStretch(1)
        horizontalLayout_top_top.addLayout(verticalLayout_dividends_receiving, 1)

        verticalLayout_top.addLayout(horizontalLayout_top_top, 0)

        horizontalLayout_top_bottom = QtWidgets.QHBoxLayout()
        horizontalLayout_top_bottom.setSpacing(2)

        verticalLayout_top_bottom_left = QtWidgets.QVBoxLayout()
        verticalLayout_top_bottom_left.setSpacing(0)
        horizontalLayout_2 = QtWidgets.QHBoxLayout()
        horizontalLayout_2.setSpacing(2)
        """---------------------Панель даты расчёта---------------------"""
        self.groupBox_calendar = GroupBox_CalculationDate('groupBox_calendar', layoutWidget)
        horizontalLayout_2.addWidget(self.groupBox_calendar, 0)
        """-------------------------------------------------------------"""
        """-----------------------Панель фильтров-----------------------"""
        self.groupBox_filters = GroupBox_SharesFilters('groupBox_filters', layoutWidget)
        horizontalLayout_2.addWidget(self.groupBox_filters, 0)
        """-------------------------------------------------------------"""
        verticalLayout_top_bottom_left.addLayout(horizontalLayout_2, 0)
        verticalLayout_top_bottom_left.addStretch(1)
        horizontalLayout_top_bottom.addLayout(verticalLayout_top_bottom_left, 0)

        """----------------Панель отображения дивидендов----------------"""
        self.groupBox_dividends = GroupBox_DividendsView(layoutWidget)
        horizontalLayout_top_bottom.addWidget(self.groupBox_dividends, 1)
        """-------------------------------------------------------------"""

        verticalLayout_top.addLayout(horizontalLayout_top_bottom, 1)

        """-------------------Панель отображения акций-------------------"""
        self.groupBox_view = GroupBox_SharesView('groupBox_view')
        splitter.addWidget(self.groupBox_view)
        splitter.setStretchFactor(1, 1)
        """--------------------------------------------------------------"""

        verticalLayout_main.addWidget(splitter)

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

                share_class_list: list[MyShareClass] = [MyShareClass(share, lp) for (share, lp) in zipWithLastPrices3000(token, filtered_shares)]
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

        self.groupBox_request.setTokensModel(tokens_model)  # Устанавливает модель токенов для ComboBox'а.

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
                MainConnection.addShares(token.token, instrument_status, shares)  # Добавляем акции в таблицу акций.
                self.shares = shares
                filtered_shares: list[Share] = self.groupBox_filters.getFilteredSharesList(shares)  # Отфильтрованный список акций.

                '''-----------------Обновляет отображение количеств акций в моделях-----------------'''
                self.groupBox_request.setCount(len(shares))  # Количество полученных акций.
                self.groupBox_filters.setCount(len(filtered_shares))  # Количество отобранных акций.
                '''---------------------------------------------------------------------------------'''

                share_class_list: list[MyShareClass] = [MyShareClass(share, lp) for (share, lp) in zipWithLastPrices3000(token, filtered_shares)]
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
            MainConnection.addShares(token.token, instrument_status, shares)  # Добавляем акции в таблицу акций.
            self.shares = shares
            filtered_shares: list[Share] = self.groupBox_filters.getFilteredSharesList(shares)  # Отфильтрованный список акций.
            '''-----------------Обновляет отображение количеств акций в моделях-----------------'''
            self.groupBox_request.setCount(len(shares))  # Количество полученных акций.
            self.groupBox_filters.setCount(len(filtered_shares))  # Количество отобранных акций.
            '''---------------------------------------------------------------------------------'''
            share_class_list: list[MyShareClass] = [MyShareClass(share, lp) for (share, lp) in zipWithLastPrices3000(token, filtered_shares)]
            self.groupBox_view.setShares(share_class_list)  # Передаём в исходную модель данные.
            self.groupBox_dividends.setData(None)  # Сбрасываем модель дивидендов.
            if share_class_list:  # Если список не пуст.
                self._startDividendsThread(token, share_class_list)  # Запускает поток получения дивидендов.
        else:
            self.__reset()  # Сбрасывает акции.

    def _startDividendsThread(self, token: TokenClass, share_class_list: list[MyShareClass]):
        """Запускает поток получения дивидендов."""
        assert self.dividends_thread is None, 'Поток заполнения дивидендов должен быть завершён!'

        self.dividends_thread = DividendsThread(token_class=token, share_class_list=share_class_list, parent=self)
        """---------------------Подключаем сигналы потока к слотам---------------------"""
        self.dividends_thread.printText_signal.connect(print)  # Сигнал для отображения сообщений в консоли.

        self.dividends_thread.setProgressBarRange_signal.connect(self.groupBox_dividends_receiving.setRange)
        self.dividends_thread.setProgressBarValue_signal.connect(self.groupBox_dividends_receiving.setValue)

        # self.dividends_thread.showRequestError_signal.connect(self.showRequestError)
        # self.dividends_thread.showException_signal.connect(self.showException)

        self.dividends_thread.dividendsReceived.connect(MainConnection.setDividends)

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
