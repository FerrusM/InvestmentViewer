from grpc import StatusCode
from PyQt6 import QtCore, QtGui, QtWidgets
from tinkoff.invest import RequestError
from BondsPage import BondsPage
from LimitsModel import LimitsTreeModel
from LimitsPage import GroupBox_LimitsTreeView, LimitsPage
from PagesClasses import GroupBox_Request
from SharesPage import SharesPage
from TokenModel import TokenModel, TokenListModel
from TokensPage import TokensPage


class Ui_MainWindow(object):
    def setupUi(self, main_window: QtWidgets.QMainWindow):
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

        """------------------------------Страница "Токены"------------------------------"""
        self.tab_tokens: TokensPage = TokensPage('tab_tokens')
        self.tabWidget.addTab(self.tab_tokens, '')
        """-----------------------------------------------------------------------------"""

        """------------------------------Страница "Лимиты"------------------------------"""
        # self.tab_limits = QtWidgets.QWidget()
        # self.tab_limits.setObjectName('tab_limits')
        #
        # self.limits_verticalLayout = QtWidgets.QVBoxLayout(self.tab_limits)
        # self.limits_verticalLayout.setContentsMargins(2, 2, 2, 2)
        # self.limits_verticalLayout.setSpacing(2)
        # self.limits_verticalLayout.setObjectName('limits_verticalLayout')
        #
        # """------------------Панель выполнения запроса------------------"""
        # self.limits_groupBox_request = GroupBox_Request('limits_groupBox_request', self.tab_limits)
        # self.limits_verticalLayout.addWidget(self.limits_groupBox_request)
        # """-------------------------------------------------------------"""
        #
        # """------------------Панель отображения лимитов------------------"""
        # self.limits_groupBox_view: GroupBox_LimitsTreeView = GroupBox_LimitsTreeView('limits_groupBox_view', self.tab_limits)
        # self.limits_verticalLayout.addWidget(self.limits_groupBox_view)
        # """--------------------------------------------------------------"""
        #
        # self.tabWidget.addTab(self.tab_limits, '')
        """-----------------------------------------------------------------------------"""

        """------------------------------Страница "Лимиты"------------------------------"""
        self.tab_limits: LimitsPage = LimitsPage('tab_limits')
        self.tabWidget.addTab(self.tab_limits, '')
        """-----------------------------------------------------------------------------"""

        """------------------------------Страница "Акции"------------------------------"""
        self.tab_shares: SharesPage = SharesPage('tab_shares')
        self.tabWidget.addTab(self.tab_shares, '')
        """----------------------------------------------------------------------------"""

        """-----------------------------Страница "Облигации"-----------------------------"""
        self.tab_bonds: BondsPage = BondsPage('tab_bonds')
        self.tabWidget.addTab(self.tab_bonds, '')
        """------------------------------------------------------------------------------"""

        self.main_verticalLayout.addWidget(self.tabWidget)
        main_window.setCentralWidget(self.centralwidget)
        self.statusbar = QtWidgets.QStatusBar(main_window)
        self.statusbar.setObjectName('statusbar')
        main_window.setStatusBar(self.statusbar)

        self.retranslateUi(main_window)
        self.tabWidget.setCurrentIndex(2)
        QtCore.QMetaObject.connectSlotsByName(main_window)

    def retranslateUi(self, main_window: QtWidgets.QMainWindow):
        _translate = QtCore.QCoreApplication.translate
        main_window.setWindowTitle(_translate('MainWindow', 'Тинькофф Инвестиции'))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_tokens), _translate('MainWindow', 'Токены'))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_limits), _translate('MainWindow', 'Лимиты'))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_shares), _translate('MainWindow', 'Акции'))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_bonds), _translate('MainWindow', 'Облигации'))


def ifTokenIsUnauthenticated(error: RequestError):
    """Возвращает True, если токен не прошёл проверку подлинности, иначе возвращает False."""
    return True if error.code == StatusCode.UNAUTHENTICATED and error.details == '40003' else False


class InvestmentForm(QtWidgets.QMainWindow, Ui_MainWindow):
    """Главная форма."""
    def __init__(self):
        super().__init__()  # __init__() QMainWindow и Ui_MainWindow.
        self.setupUi(self)  # Инициализация нашего дизайна.

        """---------------------Модель токенов---------------------"""
        token_model: TokenModel = TokenModel()
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
        """------------------------------------------------------------"""
