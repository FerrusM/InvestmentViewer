from PyQt6 import QtCore, QtWidgets
from AssetsPage import AssetsPage
from BondsPage import BondsPage
from LimitsPage import LimitsPage
from MyDatabase import MyDatabase
from SharesPage import SharesPage
# from old_TokenModel import TokenModel, TokenListModel
from new_TokenModel import TokenModel, TokenListModel
from TokensPage import TokensPage


class Ui_MainWindow(object):
    def setupUi(self, main_window: QtWidgets.QMainWindow, db: MyDatabase):
        main_window.setObjectName('InvestmentWindow')
        main_window.resize(1200, 800)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(main_window.sizePolicy().hasHeightForWidth())
        main_window.setSizePolicy(sizePolicy)

        self.centralwidget = QtWidgets.QWidget(main_window)
        self.centralwidget.setObjectName('centralwidget')

        self.main_verticalLayout = QtWidgets.QVBoxLayout(self.centralwidget)
        self.main_verticalLayout.setContentsMargins(1, 1, 0, 0)
        self.main_verticalLayout.setSpacing(0)
        self.main_verticalLayout.setObjectName('main_verticalLayout')

        self.tabWidget = QtWidgets.QTabWidget(self.centralwidget)  # Панель вкладок.
        self.tabWidget.setObjectName('tabWidget')

        _translate = QtCore.QCoreApplication.translate

        """------------------------------Страница "Токены"------------------------------"""
        self.tab_tokens: TokensPage = TokensPage('tab_tokens')
        self.tabWidget.addTab(self.tab_tokens, _translate('MainWindow', 'Токены'))
        """-----------------------------------------------------------------------------"""

        """------------------------------Страница "Лимиты"------------------------------"""
        self.tab_limits: LimitsPage = LimitsPage('tab_limits')
        self.tabWidget.addTab(self.tab_limits, _translate('MainWindow', 'Лимиты'))
        """-----------------------------------------------------------------------------"""

        """------------------------------Страница "Акции"------------------------------"""
        self.tab_shares: SharesPage = SharesPage('tab_shares')
        self.tabWidget.addTab(self.tab_shares, _translate('MainWindow', 'Акции'))
        """----------------------------------------------------------------------------"""

        """-----------------------------Страница "Облигации"-----------------------------"""
        self.tab_bonds: BondsPage = BondsPage(db, 'tab_bonds')
        self.tabWidget.addTab(self.tab_bonds, _translate('MainWindow', 'Облигации'))
        """------------------------------------------------------------------------------"""

        """------------------------------Страница "Активы"------------------------------"""
        self.tab_assets: AssetsPage = AssetsPage('tab_assets')
        self.tabWidget.addTab(self.tab_assets, _translate('MainWindow', 'Активы'))
        """-----------------------------------------------------------------------------"""

        self.main_verticalLayout.addWidget(self.tabWidget)
        main_window.setCentralWidget(self.centralwidget)

        self.statusbar = QtWidgets.QStatusBar(main_window)
        self.statusbar.setObjectName('statusbar')
        main_window.setStatusBar(self.statusbar)

        main_window.setWindowTitle(_translate('MainWindow', 'Тинькофф Инвестиции'))

        self.tabWidget.setCurrentIndex(2)
        QtCore.QMetaObject.connectSlotsByName(main_window)


class InvestmentForm(QtWidgets.QMainWindow, Ui_MainWindow):
    """Главная форма."""
    def __init__(self):
        super().__init__()  # __init__() QMainWindow и Ui_MainWindow.
        self._database: MyDatabase = MyDatabase()
        self.setupUi(self, self._database)  # Инициализация нашего дизайна.

        """---------------------Модель токенов---------------------"""
        token_model: TokenModel = TokenModel(self._database, self)
        """--------------------------------------------------------"""

        """---------------------Модель доступа---------------------"""
        self.tab_tokens.setModel(token_model)
        """--------------------------------------------------------"""

        """---Подключаем ComboBox'ы для отображения токенов к модели---"""
        token_list_model: TokenListModel = TokenListModel()
        token_list_model.setSourceModel(token_model)
        self.tab_limits.setTokensModel(token_list_model)
        self.tab_shares.setTokensModel(token_list_model)
        self.tab_bonds.setTokensModel(token_list_model)
        self.tab_assets.setTokensModel(token_list_model)
        """------------------------------------------------------------"""
