from PyQt6 import QtCore, QtWidgets
from AssetsPage import AssetsPage
from BondsPage import BondsPage
from CandlesPage import CandlesPage
from ForecastsPage import ForecastsPage
from LimitsPage import LimitsPage
from MyDatabase import MainConnection
from SharesPage import SharesPage
from TokenModel import TokenModel, TokenListModel
from TokensPage import TokensPage
from new_BondsPage import new_BondsPage


class InvestmentForm(QtWidgets.QMainWindow):
    """Главная форма."""
    def __init__(self):
        super().__init__()

        self.__database: MainConnection = MainConnection()  # Открываем соединение с базой данных.

        token_model: TokenModel = TokenModel(self)  # Модель токенов.

        token_list_model: TokenListModel = TokenListModel()
        token_list_model.setSourceModel(token_model)

        '''====================================Ui_MainWindow===================================='''
        _translate = QtCore.QCoreApplication.translate

        self.setObjectName('InvestmentWindow')
        self.resize(1200, 800)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(sizePolicy)
        self.setWindowTitle(_translate('MainWindow', 'Тинькофф Инвестиции'))

        '''------------------------------Создаём CentralWidget------------------------------'''
        central_widget = QtWidgets.QWidget(self)

        self.main_verticalLayout = QtWidgets.QVBoxLayout(central_widget)
        self.main_verticalLayout.setContentsMargins(1, 1, 0, 0)
        self.main_verticalLayout.setSpacing(0)

        '''------------------------------Создаём tabWidget------------------------------'''
        self.tabWidget = QtWidgets.QTabWidget(parent=central_widget)  # Панель вкладок.

        self.tab_tokens = TokensPage('tab_tokens')  # Страница "Токены".
        self.tab_tokens.setModel(token_model)  # Модель доступа.
        self.tabWidget.addTab(self.tab_tokens, _translate('MainWindow', 'Токены'))

        self.tab_limits = LimitsPage('tab_limits')  # Страница "Лимиты".
        self.tab_limits.setTokensModel(token_list_model)
        self.tabWidget.addTab(self.tab_limits, _translate('MainWindow', 'Лимиты'))

        self.tab_shares = SharesPage('tab_shares')  # Страница "Акции".
        self.tab_shares.setTokensModel(token_list_model)
        self.tabWidget.addTab(self.tab_shares, _translate('MainWindow', 'Акции'))

        self.tab_bonds = BondsPage('tab_bonds')  # Страница "Облигации".
        self.tab_bonds.setTokensModel(token_list_model)
        self.tabWidget.addTab(self.tab_bonds, _translate('MainWindow', 'Облигации'))

        self.new_tab_bonds = new_BondsPage('new_tab_bonds')  # Страница "Облигации".
        self.new_tab_bonds.setTokensModel(token_list_model)
        self.tabWidget.addTab(self.new_tab_bonds, _translate('MainWindow', 'new_Облигации'))

        self.tab_forecasts = ForecastsPage(tokens_model=token_list_model)  # Страница "Прогнозы".
        self.tabWidget.addTab(self.tab_forecasts, 'Прогнозы')

        self.tab_candles = CandlesPage(parent=self)  # Страница "Свечи".
        self.tab_candles.setTokensModel(token_list_model)
        self.tabWidget.addTab(self.tab_candles, _translate('MainWindow', 'Свечи'))

        self.tab_assets = AssetsPage('tab_assets')  # Страница "Активы".
        self.tab_assets.setTokensModel(token_list_model)
        self.tabWidget.addTab(self.tab_assets, _translate('MainWindow', 'Активы'))

        self.tabWidget.setCurrentIndex(2)
        '''-----------------------------------------------------------------------------'''

        self.main_verticalLayout.addWidget(self.tabWidget)
        '''---------------------------------------------------------------------------------'''

        self.setCentralWidget(central_widget)

        statusbar = QtWidgets.QStatusBar(parent=self)
        self.setStatusBar(statusbar)
        '''====================================================================================='''
