from PyQt6 import QtCore, QtWidgets, QtSql
from AssetsPage import AssetsPage
from BondsPage import BondsPage
from CandlesPage import CandlesPage
from Classes import MyConnection
from ForecastsPage import ForecastsPage
from LimitsPage import LimitsPage
from MyDatabase import MainConnection
from SharesPage import SharesPage
from TokenModel import TokenModel, TokenListModel
from TokensPage import TokensPage
from new_BondsPage import new_BondsPage
from new_CandlesPage import CandlesPage_new


class InvestmentForm(QtWidgets.QMainWindow):
    """Главная форма."""
    candlesChanged: QtCore.pyqtSignal = QtCore.pyqtSignal(int)

    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)
        self.setObjectName('InvestmentWindow')
        self.resize(1200, 800)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(sizePolicy)
        self.setWindowTitle('Тинькофф Инвестиции')

        MainConnection()  # Открываем соединение с базой данных.

        token_model: TokenModel = TokenModel(self)  # Модель токенов.

        token_list_model: TokenListModel = TokenListModel()
        token_list_model.setSourceModel(token_model)

        '''====================================Ui_MainWindow===================================='''
        '''------------------------------Создаём CentralWidget------------------------------'''
        central_widget = QtWidgets.QWidget(self)

        main_verticalLayout = QtWidgets.QVBoxLayout(central_widget)
        main_verticalLayout.setContentsMargins(1, 1, 0, 0)
        main_verticalLayout.setSpacing(0)

        '''------------------------------Создаём tabWidget------------------------------'''
        self.tabWidget = QtWidgets.QTabWidget(parent=central_widget)  # Панель вкладок.

        self.tab_tokens = TokensPage(token_model)  # Страница "Токены".
        self.tabWidget.addTab(self.tab_tokens, 'Токены')

        self.tab_limits = LimitsPage('tab_limits')  # Страница "Лимиты".
        self.tab_limits.setTokensModel(token_list_model)
        self.tabWidget.addTab(self.tab_limits, 'Лимиты')

        self.tab_shares = SharesPage('tab_shares')  # Страница "Акции".
        self.tab_shares.setTokensModel(token_list_model)
        self.tabWidget.addTab(self.tab_shares, 'Акции')

        self.tab_bonds = BondsPage('tab_bonds')  # Страница "Облигации".
        self.tab_bonds.setTokensModel(token_list_model)
        self.tabWidget.addTab(self.tab_bonds, 'Облигации')

        self.new_tab_bonds = new_BondsPage('new_tab_bonds')  # Страница "Облигации".
        self.new_tab_bonds.setTokensModel(token_list_model)
        self.tabWidget.addTab(self.new_tab_bonds, 'new_Облигации')

        self.tab_forecasts = ForecastsPage(tokens_model=token_list_model)  # Страница "Прогнозы".
        self.tabWidget.addTab(self.tab_forecasts, 'Прогнозы')

        self.tab_candles = CandlesPage(parent=self)  # Страница "Свечи".
        self.tab_candles.setTokensModel(token_list_model)
        self.tabWidget.addTab(self.tab_candles, 'Свечи')

        self.tab_candles_new = CandlesPage_new(token_model=token_list_model, parent=self)
        self.tabWidget.addTab(self.tab_candles_new, 'Свечи_new')

        self.tab_assets = AssetsPage('tab_assets')  # Страница "Активы".
        self.tab_assets.setTokensModel(token_list_model)
        self.tabWidget.addTab(self.tab_assets, 'Активы')

        self.tabWidget.setCurrentIndex(2)
        '''-----------------------------------------------------------------------------'''

        main_verticalLayout.addWidget(self.tabWidget)
        '''---------------------------------------------------------------------------------'''

        self.setCentralWidget(central_widget)
        '''====================================================================================='''

        '''------------------Подключаем уведомления от бд------------------'''
        @QtCore.pyqtSlot(str, QtSql.QSqlDriver.NotificationSource, int)
        def __notificationSlot(name: str, source: QtSql.QSqlDriver.NotificationSource, rowid: int):
            assert source == QtSql.QSqlDriver.NotificationSource.UnknownSource
            print('notificationSlot: name = {0}, payload = {1}.'.format(name, rowid))

            if name == MyConnection.CANDLES_TABLE:
                # self.candlesChanged.emit(payload)
                self.tab_candles_new.groupBox_candles_view.onCandlesChanges(rowid)
            elif name == MyConnection.LAST_PRICES_TABLE:
                self.new_tab_bonds.groupBox_view.sourceModel().onLastPricesChanged(rowid)
            elif name == MyConnection.COUPONS_TABLE:
                self.new_tab_bonds.groupBox_view.sourceModel().onCouponsChanged(rowid)
            elif name == MyConnection.BONDS_TABLE:
                self.new_tab_bonds.groupBox_view.sourceModel().onBondsChanged(rowid)
            elif name == MyConnection.TOKENS_TABLE:
                token_model.onTokensChanged(rowid)
            else:
                raise ValueError('Неверный параметр name ({0})!'.format(name))

        db: QtSql.QSqlDatabase = MainConnection.getDatabase()
        driver = db.driver()
        driver.notification.connect(__notificationSlot)

        # subscribe_tokens_flag: bool = driver.subscribeToNotification(MyConnection.TOKENS_TABLE)
        # assert subscribe_tokens_flag, 'Не удалось подписаться на уведомления об изменении таблицы {0}! driver.lastError().text(): \'{1}\'.'.format(MyConnection.TOKENS_TABLE, driver.lastError().text())
        #
        # subscribe_candles_flag: bool = driver.subscribeToNotification(MyConnection.CANDLES_TABLE)
        # assert subscribe_candles_flag, 'Не удалось подписаться на уведомления об изменении таблицы {0}! driver.lastError().text(): \'{1}\'.'.format(MyConnection.CANDLES_TABLE, driver.lastError().text())
        #
        # subscribe_bonds_flag: bool = driver.subscribeToNotification(MyConnection.BONDS_TABLE)
        # assert subscribe_bonds_flag, 'Не удалось подписаться на уведомления об изменении таблицы {0}! driver.lastError().text(): \'{1}\'.'.format(MyConnection.BONDS_TABLE, driver.lastError().text())
        #
        # subscribe_coupons_flag: bool = driver.subscribeToNotification(MyConnection.COUPONS_TABLE)
        # assert subscribe_coupons_flag, 'Не удалось подписаться на уведомления об изменении таблицы {0}! driver.lastError().text(): \'{1}\'.'.format(MyConnection.COUPONS_TABLE, driver.lastError().text())
        #
        # subscribe_lp_flag: bool = driver.subscribeToNotification(MyConnection.LAST_PRICES_TABLE)
        # assert subscribe_lp_flag, 'Не удалось подписаться на уведомления об изменении таблицы {0}! driver.lastError().text(): \'{1}\'.'.format(MyConnection.LAST_PRICES_TABLE, driver.lastError().text())
        '''----------------------------------------------------------------'''

        # self.candlesChanged.connect(self.tab_candles_new.groupBox_candles_view.onCandlesChanges)
