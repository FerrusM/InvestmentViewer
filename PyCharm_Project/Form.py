from PyQt6.QtCore import pyqtSignal, pyqtSlot, QModelIndex, Qt
from PyQt6.QtWidgets import QMessageBox
from grpc import StatusCode
from PyQt6 import QtCore, QtGui, QtWidgets
from tinkoff.invest import Account, RequestError
from Classes import TokenClass, reportAccountType, reportAccountStatus, reportAccountAccessLevel, Filter
from LimitClasses import MyUnaryLimit, MyStreamLimit
from LimitsModel import LimitsTreeModel
from MyDateTime import reportSignificantInfoFromDateTime
from MyRequests import getAccounts, MyResponse, getUserTariff
from PagesClasses import GroupBox_Request, GroupBox_InstrumentsRequest, GroupBox_CalculationDate, GroupBox_InstrumentsFilters
from SharesModel import SharesModel, SharesProxyModel
from SharesPage import Tab_Shares
from TokenModel import TokenModel, TokenListModel
from TreeTokenModel import TreeProxyModel, TreeItem


class MyTreeView(QtWidgets.QTreeView):
    def resizeColumnsToContents(self: QtWidgets.QTreeView):
        """Авторазмер всех столбцов TreeView под содержимое."""
        for i in range(self.model().columnCount()):
            self.resizeColumnToContents(i)  # Авторазмер i-го столбца под содержимое.


'''====================Классы для страницы токенов===================='''


class GroupBox_SavedTokens(QtWidgets.QGroupBox):
    """Панель отображения сохранённых токенов."""
    def __init__(self, object_name: str, parent: QtWidgets.QWidget | None = ...):
        super().__init__(parent)  # QGroupBox __init__().
        self.setTitle('')
        self.setObjectName(object_name)

        self.verticalLayout_main = QtWidgets.QVBoxLayout(self)
        self.verticalLayout_main.setContentsMargins(2, 2, 2, 3)
        self.verticalLayout_main.setSpacing(2)
        self.verticalLayout_main.setObjectName('verticalLayout_main')

        """------------Заголовок над отображением токенов------------"""
        self.horizontalLayout_title = QtWidgets.QHBoxLayout()
        self.horizontalLayout_title.setSpacing(0)
        self.horizontalLayout_title.setObjectName('horizontalLayout_title')

        spacerItem8 = QtWidgets.QSpacerItem(10, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_title.addItem(spacerItem8)

        spacerItem9 = QtWidgets.QSpacerItem(0, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_title.addItem(spacerItem9)

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

        spacerItem10 = QtWidgets.QSpacerItem(10, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_title.addItem(spacerItem10)

        self.verticalLayout_main.addLayout(self.horizontalLayout_title)
        """----------------------------------------------------------"""

        """------------------Отображение токенов------------------"""
        self.treeView_saved_tokens = MyTreeView(self)
        self.treeView_saved_tokens.setObjectName('treeView_saved_tokens')
        self.verticalLayout_main.addWidget(self.treeView_saved_tokens)
        """-------------------------------------------------------"""

        _translate = QtCore.QCoreApplication.translate
        self.label_title.setText(_translate('MainWindow', 'СОХРАНЁННЫЕ ТОКЕНЫ'))
        self.label_count.setText(_translate('MainWindow', '0'))

    def setModel(self, model: TreeProxyModel):
        """Подключает модель сохранённых токенов."""
        self.treeView_saved_tokens.setModel(model)

        '''------------------Создаём делегат кнопки удаления токенов------------------'''
        delete_button_delegate: TreeProxyModel.DeleteButtonDelegate = model.DeleteButtonDelegate(self.treeView_saved_tokens)
        # delete_button_delegate.clicked.connect(lambda index: print('Номер строки: {0}'.format(str(index.row()))))

        @pyqtSlot(str)  # Декоратор, который помечает функцию как qt-слот и ускоряет его выполнение.
        def deleteTokenDialog(token: str) -> QMessageBox.StandardButton:
            """Диалоговое окно удаления токена."""
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Icon.Warning)  # Задаёт значок окна сообщения.
            msgBox.setWindowTitle('Удаление токена')  # Заголовок окна сообщения.
            msgBox.setText('Вы уверены, что хотите удалить токен {0}?'.format(token))  # Текст окна сообщения.
            msgBox.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            msgBox.setDefaultButton(QMessageBox.StandardButton.No)
            return msgBox.exec()

        def getTokenFromIndex(index: QModelIndex) -> str:
            """Получает и возвращает токен, соответствующий индексу."""
            tree_item: TreeItem = index.internalPointer()  # Указатель на внутреннюю структуру данных.
            assert type(tree_item) == TreeItem
            token_class: TokenClass = tree_item.data
            assert type(token_class) == TokenClass
            return token_class.token

        def deleteButtonFunction(index: QModelIndex):
            token: str = getTokenFromIndex(index)
            clicked_button: QMessageBox.StandardButton = deleteTokenDialog(token)
            match clicked_button:
                case QMessageBox.StandardButton.No:
                    return
                case QMessageBox.StandardButton.Yes:
                    """------------------------------Удаление токена------------------------------"""
                    deleted_flag: bool = model.deleteToken(index)
                    # assert not deleted_flag, 'Проблема с удалением токена!'
                    if not deleted_flag:
                        raise ValueError('Проблема с удалением токена!')
                    """---------------------------------------------------------------------------"""
                    return
                case _:
                    assert False, 'Неверное значение нажатой кнопки в окне удаления токена ({0})!'.format(clicked_button)

        delete_button_delegate.clicked.connect(lambda index: deleteButtonFunction(index))
        '''---------------------------------------------------------------------------'''

        self.treeView_saved_tokens.setItemDelegateForColumn(model.Columns.TOKEN_DELETE_BUTTON, delete_button_delegate)

        self.treeView_saved_tokens.expandAll()  # Разворачивает все элементы.
        self.treeView_saved_tokens.resizeColumnsToContents()  # Авторазмер всех столбцов под содержимое.
        self.label_count.setText(str(model.getTokensCount()))  # Отображаем количество сохранённых токенов.


class GroupBox_NewToken(QtWidgets.QGroupBox):
    """Панель добавления нового токена."""

    """------------------------Сигналы------------------------"""
    add_token_signal: pyqtSignal = pyqtSignal(TokenClass)  # Сигнал, испускаемый при необходимости добавить токен в модель.
    """-------------------------------------------------------"""

    def __init__(self, object_name: str, parent: QtWidgets.QWidget | None = ...):
        super().__init__(parent)  # QGroupBox __init__().

        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(sizePolicy)
        self.setTitle('')
        self.setObjectName(object_name)

        self.verticalLayout_main = QtWidgets.QVBoxLayout(self)
        self.verticalLayout_main.setContentsMargins(2, 2, 2, 3)
        self.verticalLayout_main.setSpacing(2)
        self.verticalLayout_main.setObjectName('verticalLayout_main')

        """------------------Заголовок "Новый токен"------------------"""
        self.label_title = QtWidgets.QLabel(self)
        font = QtGui.QFont()
        font.setBold(True)
        self.label_title.setFont(font)
        self.label_title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.label_title.setObjectName('label_title')
        self.verticalLayout_main.addWidget(self.label_title)
        """-----------------------------------------------------------"""

        """-------------Строка добавления нового токена-------------"""
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setSpacing(2)
        self.horizontalLayout.setObjectName('horizontalLayout')

        self.lineEdit_new_token = QtWidgets.QLineEdit(self)
        self.lineEdit_new_token.setObjectName('lineEdit_new_token')
        self.horizontalLayout.addWidget(self.lineEdit_new_token)

        self.pushButton_save_token = QtWidgets.QPushButton(self)
        self.pushButton_save_token.setEnabled(False)  # Кнопка "Сохранить" для нового токена д.б. неактивна по умолчанию.
        self.pushButton_save_token.setObjectName('pushButton_save_token')
        self.horizontalLayout.addWidget(self.pushButton_save_token)

        self.verticalLayout_main.addLayout(self.horizontalLayout)
        """---------------------------------------------------------"""

        """---------Отображение аккаунтов добавляемого токена---------"""
        self.tabWidget_accounts = QtWidgets.QTabWidget(self)
        self.tabWidget_accounts.setMinimumSize(QtCore.QSize(0, 100))
        self.tabWidget_accounts.setBaseSize(QtCore.QSize(0, 0))
        self.tabWidget_accounts.setObjectName('tabWidget_accounts')
        self.verticalLayout_main.addWidget(self.tabWidget_accounts)
        """-----------------------------------------------------------"""

        _translate = QtCore.QCoreApplication.translate
        self.label_title.setText(_translate('MainWindow', 'НОВЫЙ ТОКЕН'))
        self.lineEdit_new_token.setPlaceholderText(_translate('MainWindow', 'Введите токен'))
        self.pushButton_save_token.setText(_translate('MainWindow', 'Сохранить'))

        self.current_token_class: TokenClass = TokenClass(token='',
                                                          accounts=[],
                                                          unary_limits=[],
                                                          stream_limits=[])
        """---------------------Подключение слотов токенов---------------------"""
        self.lineEdit_new_token.textChanged.connect(self.addedTokenChanged_slot)  # При изменении токена.
        self.pushButton_save_token.clicked.connect(self._addToken)  # При сохранении нового токена.
        """--------------------------------------------------------------------"""

    def _clearAccountsTabWidget(self):
        """Очищает tabWidget счетов добавляемого токена."""
        tabs_count: int = self.tabWidget_accounts.count()
        for i in range(tabs_count):
            self.tabWidget_accounts.removeTab(i)

    @pyqtSlot(str)  # Декоратор, который помечает функцию как qt-слот и ускоряет его выполнение.
    def addedTokenChanged_slot(self, text: str):
        """Событие при изменении добавляемого токена."""
        self._clearAccountsTabWidget()  # Очищаем tabWidget счетов добавляемого токена.

        if not text:  # Если строка токена пустая.
            self.pushButton_save_token.setEnabled(False)
        else:
            self.pushButton_save_token.setEnabled(True)

        accounts_response: MyResponse = getAccounts(text, False)
        accounts_list: list[Account] = accounts_response.response_data  # Получаем список счетов.
        self.current_token_class = TokenClass(token=text,
                                              accounts=accounts_list,
                                              unary_limits=[],
                                              stream_limits=[])
        for i, account in enumerate(accounts_list):
            account_tab = QtWidgets.QWidget()
            tab_name: str = 'tab_account_' + str(i)
            account_tab.setObjectName(tab_name)

            # Идентификатор счёта.
            label_account_id_text = QtWidgets.QLabel(account_tab)
            label_account_id_text.setObjectName(tab_name + '_label_account_id_text')
            label_account_id_text.setText('Идентификатор:')
            label_account_id = QtWidgets.QLabel(account_tab)
            label_account_id.setObjectName(tab_name + '_label_account_id')
            label_account_id.setText(account.id)

            # Тип счёта.
            label_account_type_text = QtWidgets.QLabel(account_tab)
            label_account_type_text.setObjectName(tab_name + '_label_account_type_text')
            label_account_type_text.setText('Тип счёта:')
            label_account_type = QtWidgets.QLabel(account_tab)
            label_account_type.setObjectName(tab_name + '_label_account_type')
            label_account_type.setText(reportAccountType(account.type))

            # Название счёта.
            label_account_name_text = QtWidgets.QLabel(account_tab)
            label_account_name_text.setObjectName(tab_name + '_label_account_name_text')
            label_account_name_text.setText('Название счёта:')
            label_account_name = QtWidgets.QLabel(account_tab)
            label_account_name.setObjectName(tab_name + '_label_account_name')
            label_account_name.setText(account.name)

            # Статус счёта.
            label_account_status_text = QtWidgets.QLabel(account_tab)
            label_account_status_text.setObjectName(tab_name + '_label_account_status_text')
            label_account_status_text.setText('Статус счёта:')
            label_account_status = QtWidgets.QLabel(account_tab)
            label_account_status.setObjectName(tab_name + '_label_account_status')
            label_account_status.setText(reportAccountStatus(account.status))

            # Дата открытия счёта.
            label_account_opened_date_text = QtWidgets.QLabel(account_tab)
            label_account_opened_date_text.setObjectName(tab_name + '_label_account_opened_date_text')
            label_account_opened_date_text.setText('Дата открытия:')
            label_account_opened_date = QtWidgets.QLabel(account_tab)
            label_account_opened_date.setObjectName(tab_name + '_label_account_opened_date')
            label_account_opened_date.setText(reportSignificantInfoFromDateTime(account.opened_date))

            # Дата закрытия счёта.
            label_account_closed_date_text = QtWidgets.QLabel(account_tab)
            label_account_closed_date_text.setObjectName(tab_name + '_label_account_closed_date_text')
            label_account_closed_date_text.setText('Дата закрытия:')
            label_account_closed_date = QtWidgets.QLabel(account_tab)
            label_account_closed_date.setObjectName(tab_name + '_label_account_closed_date')
            label_account_closed_date.setText(reportSignificantInfoFromDateTime(account.closed_date))

            # Уровень доступа к счёту.
            label_account_access_level_text = QtWidgets.QLabel(account_tab)
            label_account_access_level_text.setObjectName(tab_name + '_label_account_access_level_text')
            label_account_access_level_text.setText('Уровень доступа:')
            label_account_access_level = QtWidgets.QLabel(account_tab)
            label_account_access_level.setObjectName(tab_name + '_label_account_access_level')
            label_account_access_level.setText(reportAccountAccessLevel(account.access_level))

            """------------------------Компоновка------------------------"""
            gridLayout = QtWidgets.QGridLayout(account_tab)
            gridLayout.setHorizontalSpacing(10)
            gridLayout.setVerticalSpacing(1)
            gridLayout.setObjectName(tab_name + "_gridLayout")

            gridLayout.addWidget(label_account_id_text, 0, 0)
            gridLayout.addWidget(label_account_id, 0, 1)
            gridLayout.addWidget(label_account_name_text, 1, 0)
            gridLayout.addWidget(label_account_name, 1, 1)
            gridLayout.addWidget(label_account_type_text, 2, 0)
            gridLayout.addWidget(label_account_type, 2, 1)
            gridLayout.addWidget(label_account_access_level_text, 3, 0)
            gridLayout.addWidget(label_account_access_level, 3, 1)

            gridLayout.addWidget(label_account_status_text, 0, 2)
            gridLayout.addWidget(label_account_status, 0, 3)
            gridLayout.addWidget(label_account_opened_date_text, 1, 2)
            gridLayout.addWidget(label_account_opened_date, 1, 3)
            gridLayout.addWidget(label_account_closed_date_text, 2, 2)
            gridLayout.addWidget(label_account_closed_date, 2, 3)
            """----------------------------------------------------------"""

            self.tabWidget_accounts.addTab(account_tab, '')  # Добавляем страницу.
            self.tabWidget_accounts.setTabText(i, 'Счёт ' + str(i + 1))

    @pyqtSlot()  # Декоратор, который помечает функцию как qt-слот и ускоряет его выполнение.
    def _addToken(self):
        """Добавляет токен в модель."""
        new_token: str = self.lineEdit_new_token.text()  # Извлекаем текст из lineEdit.
        assert new_token == self.current_token_class.token

        unary_limits, stream_limits = getUserTariff(self.current_token_class.token).response_data
        my_unary_limits: list[MyUnaryLimit] = [MyUnaryLimit(unary_limit) for unary_limit in unary_limits]  # Массив лимитов пользователя по unary-запросам.
        my_stream_limits: list[MyStreamLimit] = [MyStreamLimit(stream_limit) for stream_limit in stream_limits]  # Массив лимитов пользователя по stream-соединениям.

        added_token: TokenClass = TokenClass(token=self.current_token_class.token,
                                             accounts=self.current_token_class.accounts,
                                             unary_limits=my_unary_limits,
                                             stream_limits=my_stream_limits)
        self.add_token_signal.emit(added_token)
        self.current_token_class: TokenClass = TokenClass(token='',
                                                          accounts=[],
                                                          unary_limits=[],
                                                          stream_limits=[])
        self.lineEdit_new_token.clear()  # Очищает содержимое lineEdit.


'''==================================================================='''


class GroupBox_LimitsTreeView(QtWidgets.QGroupBox):
    """Панель отображения лимитов выбранного токена."""
    def __init__(self, object_name: str, parent: QtWidgets.QWidget | None = ...):
        super().__init__(parent)  # QGroupBox __init__().
        self.setAutoFillBackground(False)
        self.setStyleSheet('')
        self.setTitle('')
        self.setFlat(False)
        self.setCheckable(False)
        self.setObjectName(object_name)

        self.verticalLayout_main = QtWidgets.QVBoxLayout(self)
        self.verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        self.verticalLayout_main.setSpacing(2)
        self.verticalLayout_main.setObjectName('verticalLayout_main')

        """------------------------Заголовок------------------------"""
        self.horizontalLayout_title = QtWidgets.QHBoxLayout()
        self.horizontalLayout_title.setSpacing(0)
        self.horizontalLayout_title.setObjectName('horizontalLayout_title')

        spacerItem5 = QtWidgets.QSpacerItem(10, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_title.addItem(spacerItem5)

        self.lineEdit_search = QtWidgets.QLineEdit(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.lineEdit_search.sizePolicy().hasHeightForWidth())
        self.lineEdit_search.setSizePolicy(sizePolicy)
        self.lineEdit_search.setObjectName('lineEdit_search')
        self.horizontalLayout_title.addWidget(self.lineEdit_search)

        spacerItem6 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_title.addItem(spacerItem6)

        self.label_title = QtWidgets.QLabel(self)
        font = QtGui.QFont()
        font.setBold(True)
        self.label_title.setFont(font)
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

        spacerItem7 = QtWidgets.QSpacerItem(10, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_title.addItem(spacerItem7)

        self.horizontalLayout_title.setStretch(1, 1)
        self.horizontalLayout_title.setStretch(2, 1)
        self.horizontalLayout_title.setStretch(4, 2)
        self.verticalLayout_main.addLayout(self.horizontalLayout_title)
        """---------------------------------------------------------"""

        """-------------------Отображение лимитов-------------------"""
        self.treeView_limits = MyTreeView(self)
        self.treeView_limits.setObjectName('treeView_limits')
        self.verticalLayout_main.addWidget(self.treeView_limits)
        """---------------------------------------------------------"""

        _translate = QtCore.QCoreApplication.translate
        self.lineEdit_search.setPlaceholderText(_translate("MainWindow", "Поиск..."))
        self.label_title.setText(_translate("MainWindow", "ЛИМИТЫ"))
        self.label_count.setText(_translate("MainWindow", "0"))

    def setModel(self, model: LimitsTreeModel):
        """Подключает модель лимитов."""
        self.treeView_limits.setModel(model)
        self.treeView_limits.expandAll()  # Разворачивает все элементы.
        self.treeView_limits.resizeColumnsToContents()  # Авторазмер всех столбцов под содержимое.
        # self.label_count.setText(str(model.getTokensCount()))  # Отображаем количество лимитов.

    def setToken(self, token: TokenClass | None):
        """Устанавливает токен для отображения лимитов."""
        self.treeView_limits.model().setToken(token)
        self.treeView_limits.expandAll()  # Разворачивает все элементы.
        self.treeView_limits.resizeColumnsToContents()  # Авторазмер всех столбцов под содержимое.


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
        self.tab_tokens = QtWidgets.QWidget()
        self.tab_tokens.setObjectName('tab_tokens')

        self.tokens_verticalLayout = QtWidgets.QVBoxLayout(self.tab_tokens)
        self.tokens_verticalLayout.setContentsMargins(2, 2, 2, 2)
        self.tokens_verticalLayout.setSpacing(2)
        self.tokens_verticalLayout.setObjectName('tokens_verticalLayout')

        """------------Панель отображения сохранённых токенов------------"""
        self.tokens_groupBox_tokens: GroupBox_SavedTokens = GroupBox_SavedTokens('tokens_groupBox_tokens', self.tab_tokens)
        self.tokens_verticalLayout.addWidget(self.tokens_groupBox_tokens)
        """--------------------------------------------------------------"""

        """----------------Панель добавления нового токена----------------"""
        self.tokens_groupBox_new_token: GroupBox_NewToken = GroupBox_NewToken('tokens_groupBox_new_token', self.tab_tokens)
        self.tokens_verticalLayout.addWidget(self.tokens_groupBox_new_token)
        """---------------------------------------------------------------"""

        self.tabWidget.addTab(self.tab_tokens, '')
        """-----------------------------------------------------------------------------"""

        """------------------------------Страница "Лимиты"------------------------------"""
        self.tab_limits = QtWidgets.QWidget()
        self.tab_limits.setObjectName('tab_limits')

        self.limits_verticalLayout = QtWidgets.QVBoxLayout(self.tab_limits)
        self.limits_verticalLayout.setContentsMargins(2, 2, 2, 2)
        self.limits_verticalLayout.setSpacing(2)
        self.limits_verticalLayout.setObjectName('limits_verticalLayout')

        """------------------Панель выполнения запроса------------------"""
        self.limits_groupBox_request = GroupBox_Request('limits_groupBox_request', self.tab_limits)
        self.limits_verticalLayout.addWidget(self.limits_groupBox_request)
        """-------------------------------------------------------------"""

        """------------------Панель отображения лимитов------------------"""
        self.limits_groupBox_view: GroupBox_LimitsTreeView = GroupBox_LimitsTreeView('limits_groupBox_view', self.tab_limits)
        self.limits_verticalLayout.addWidget(self.limits_groupBox_view)
        """--------------------------------------------------------------"""

        self.tabWidget.addTab(self.tab_limits, '')
        """-----------------------------------------------------------------------------"""

        """------------------------------Страница "Акции"------------------------------"""
        # self.tab_shares = QtWidgets.QWidget()
        # self.tab_shares.setStyleSheet('')
        # self.tab_shares.setObjectName('tab_shares')
        #
        # self.shares_verticalLayout_main = QtWidgets.QVBoxLayout(self.tab_shares)
        # self.shares_verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        # self.shares_verticalLayout_main.setSpacing(2)
        # self.shares_verticalLayout_main.setObjectName('shares_verticalLayout_main')
        #
        # self.shares_splitter = QtWidgets.QSplitter(self.tab_shares)
        # self.shares_splitter.setOrientation(QtCore.Qt.Orientation.Vertical)
        # self.shares_splitter.setObjectName('shares_splitter')
        #
        # self.shares_layoutWidget = QtWidgets.QWidget(self.shares_splitter)
        # self.shares_layoutWidget.setObjectName('shares_layoutWidget')
        #
        # self.verticalLayout_6 = QtWidgets.QVBoxLayout(self.shares_layoutWidget)
        # self.verticalLayout_6.setContentsMargins(0, 0, 0, 0)
        # self.verticalLayout_6.setSpacing(2)
        # self.verticalLayout_6.setObjectName('verticalLayout_6')
        #
        # self.shares_horizontalLayout_requests = QtWidgets.QHBoxLayout()
        # self.shares_horizontalLayout_requests.setSpacing(2)
        # self.shares_horizontalLayout_requests.setObjectName('shares_horizontalLayout_requests')
        #
        # """------------------Панель выполнения запроса------------------"""
        # self.shares_groupBox_request = GroupBox_InstrumentsRequest('shares_groupBox_request', self.shares_layoutWidget)
        # self.shares_horizontalLayout_requests.addWidget(self.shares_groupBox_request)
        # """-------------------------------------------------------------"""
        #
        # self.shares_verticalLayout_dividends_receiving = QtWidgets.QVBoxLayout()
        # self.shares_verticalLayout_dividends_receiving.setSpacing(0)
        # self.shares_verticalLayout_dividends_receiving.setObjectName('shares_verticalLayout_dividends_receiving')
        #
        # """------------Панель прогресса получения дивидендов------------"""
        # self.shares_groupBox_dividends_receiving: GroupBox_DividendsReceiving = GroupBox_DividendsReceiving('shares_groupBox_dividends_receiving', self.shares_layoutWidget)
        # self.shares_verticalLayout_dividends_receiving.addWidget(self.shares_groupBox_dividends_receiving)
        # """-------------------------------------------------------------"""
        #
        # spacerItem15 = QtWidgets.QSpacerItem(20, 0, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        # self.shares_verticalLayout_dividends_receiving.addItem(spacerItem15)
        #
        # self.shares_horizontalLayout_requests.addLayout(self.shares_verticalLayout_dividends_receiving)
        # self.shares_horizontalLayout_requests.setStretch(1, 1)
        # self.verticalLayout_6.addLayout(self.shares_horizontalLayout_requests)
        #
        # self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        # self.horizontalLayout_3.setSpacing(2)
        # self.horizontalLayout_3.setObjectName('horizontalLayout_3')
        #
        # self.verticalLayout_5 = QtWidgets.QVBoxLayout()
        # self.verticalLayout_5.setSpacing(0)
        # self.verticalLayout_5.setObjectName('verticalLayout_5')
        #
        # self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        # self.horizontalLayout_2.setSpacing(2)
        # self.horizontalLayout_2.setObjectName('horizontalLayout_2')
        #
        # """---------------------Панель даты расчёта---------------------"""
        # self.shares_groupBox_calendar = GroupBox_CalculationDate('shares_groupBox_calendar', self.shares_layoutWidget)
        # self.horizontalLayout_2.addWidget(self.shares_groupBox_calendar)
        # """-------------------------------------------------------------"""
        #
        # """-----------------------Панель фильтров-----------------------"""
        # self.shares_groupBox_filters: GroupBox_SharesFilters = GroupBox_SharesFilters('shares_groupBox_filters', self.shares_layoutWidget)
        # self.horizontalLayout_2.addWidget(self.shares_groupBox_filters)
        # """-------------------------------------------------------------"""
        #
        # self.verticalLayout_5.addLayout(self.horizontalLayout_2)
        #
        # spacerItem21 = QtWidgets.QSpacerItem(20, 0, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        # self.verticalLayout_5.addItem(spacerItem21)
        #
        # self.verticalLayout_5.setStretch(1, 1)
        # self.horizontalLayout_3.addLayout(self.verticalLayout_5)
        #
        # """----------------Панель отображения дивидендов----------------"""
        # self.shares_groupBox_dividends = GroupBox_DividendsView('shares_groupBox_dividends', self.shares_layoutWidget)
        # self.horizontalLayout_3.addWidget(self.shares_groupBox_dividends)
        # """-------------------------------------------------------------"""
        #
        # self.horizontalLayout_3.setStretch(1, 1)
        #
        # self.verticalLayout_6.addLayout(self.horizontalLayout_3)
        # self.verticalLayout_6.setStretch(1, 1)
        #
        # """------------------Панель отображения лимитов------------------"""
        # self.shares_groupBox_view: GroupBox_SharesView = GroupBox_SharesView('shares_groupBox_view', self.shares_splitter)
        # """--------------------------------------------------------------"""
        #
        # self.shares_verticalLayout_main.addWidget(self.shares_splitter)
        # self.tabWidget.addTab(self.tab_shares, '')
        """----------------------------------------------------------------------------"""

        """------------------------------Страница "Акции"------------------------------"""
        self.tab_shares: Tab_Shares = Tab_Shares('tab_shares')
        self.tabWidget.addTab(self.tab_shares, '')
        """----------------------------------------------------------------------------"""

        """-----------------------------Страница "Облигации"-----------------------------"""
        self.tab_bonds = QtWidgets.QWidget()
        self.tab_bonds.setObjectName("tab_bonds")
        self.verticalLayout_43 = QtWidgets.QVBoxLayout(self.tab_bonds)
        self.verticalLayout_43.setContentsMargins(2, 2, 2, 2)
        self.verticalLayout_43.setSpacing(2)
        self.verticalLayout_43.setObjectName("verticalLayout_43")
        self.splitter_5 = QtWidgets.QSplitter(self.tab_bonds)
        self.splitter_5.setOrientation(QtCore.Qt.Orientation.Vertical)
        self.splitter_5.setObjectName("splitter_5")
        self.layoutWidget1 = QtWidgets.QWidget(self.splitter_5)
        self.layoutWidget1.setObjectName("layoutWidget1")
        self.verticalLayout_42 = QtWidgets.QVBoxLayout(self.layoutWidget1)
        self.verticalLayout_42.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_42.setSpacing(2)
        self.verticalLayout_42.setObjectName("verticalLayout_42")
        self.horizontalLayout_36 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_36.setSpacing(2)
        self.horizontalLayout_36.setObjectName("horizontalLayout_36")

        """------------------Панель выполнения запроса------------------"""
        self.bonds_groupBox_request = GroupBox_InstrumentsRequest('bonds_groupBox_request', self.layoutWidget1)
        self.horizontalLayout_36.addWidget(self.bonds_groupBox_request)
        """-------------------------------------------------------------"""

        self.groupBox_11 = QtWidgets.QGroupBox(self.layoutWidget1)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.groupBox_11.sizePolicy().hasHeightForWidth())
        self.groupBox_11.setSizePolicy(sizePolicy)
        self.groupBox_11.setTitle("")
        self.groupBox_11.setObjectName("groupBox_11")
        self.verticalLayout_8 = QtWidgets.QVBoxLayout(self.groupBox_11)
        self.verticalLayout_8.setContentsMargins(2, 2, 2, 2)
        self.verticalLayout_8.setSpacing(2)
        self.verticalLayout_8.setObjectName("verticalLayout_8")
        self.label_64 = QtWidgets.QLabel(self.groupBox_11)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_64.sizePolicy().hasHeightForWidth())
        self.label_64.setSizePolicy(sizePolicy)
        self.label_64.setMaximumSize(QtCore.QSize(16777215, 16777215))
        font = QtGui.QFont()
        font.setBold(True)
        self.label_64.setFont(font)
        self.label_64.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.label_64.setObjectName("label_64")
        self.verticalLayout_8.addWidget(self.label_64)
        self.bonds_progressBar_coupons = QtWidgets.QProgressBar(self.groupBox_11)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.bonds_progressBar_coupons.sizePolicy().hasHeightForWidth())
        self.bonds_progressBar_coupons.setSizePolicy(sizePolicy)
        self.bonds_progressBar_coupons.setMinimumSize(QtCore.QSize(0, 0))
        self.bonds_progressBar_coupons.setStyleSheet("text-align: center;")
        self.bonds_progressBar_coupons.setMaximum(0)
        self.bonds_progressBar_coupons.setProperty("value", 0)
        self.bonds_progressBar_coupons.setTextVisible(True)
        self.bonds_progressBar_coupons.setObjectName("bonds_progressBar_coupons")
        self.verticalLayout_8.addWidget(self.bonds_progressBar_coupons)
        self.horizontalLayout_33 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_33.setSpacing(0)
        self.horizontalLayout_33.setObjectName("horizontalLayout_33")
        self.label_66 = QtWidgets.QLabel(self.groupBox_11)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_66.sizePolicy().hasHeightForWidth())
        self.label_66.setSizePolicy(sizePolicy)
        self.label_66.setObjectName("label_66")
        self.horizontalLayout_33.addWidget(self.label_66)
        spacerItem35 = QtWidgets.QSpacerItem(4, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_33.addItem(spacerItem35)
        self.bonds_comboBox_coupon_type = QtWidgets.QComboBox(self.groupBox_11)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.bonds_comboBox_coupon_type.sizePolicy().hasHeightForWidth())
        self.bonds_comboBox_coupon_type.setSizePolicy(sizePolicy)
        self.bonds_comboBox_coupon_type.setStyleSheet("")
        self.bonds_comboBox_coupon_type.setObjectName("bonds_comboBox_coupon_type")
        self.bonds_comboBox_coupon_type.addItem("")
        self.bonds_comboBox_coupon_type.addItem("")
        self.bonds_comboBox_coupon_type.addItem("")
        self.bonds_comboBox_coupon_type.addItem("")
        self.bonds_comboBox_coupon_type.addItem("")
        self.bonds_comboBox_coupon_type.addItem("")
        self.bonds_comboBox_coupon_type.addItem("")
        self.bonds_comboBox_coupon_type.addItem("")
        self.bonds_comboBox_coupon_type.addItem("")
        self.horizontalLayout_33.addWidget(self.bonds_comboBox_coupon_type)
        spacerItem36 = QtWidgets.QSpacerItem(0, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_33.addItem(spacerItem36)
        self.verticalLayout_8.addLayout(self.horizontalLayout_33)
        self.verticalLayout_8.setStretch(1, 1)
        self.horizontalLayout_36.addWidget(self.groupBox_11)
        self.horizontalLayout_36.setStretch(1, 1)
        self.verticalLayout_42.addLayout(self.horizontalLayout_36)
        self.horizontalLayout_37 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_37.setSpacing(2)
        self.horizontalLayout_37.setObjectName("horizontalLayout_37")
        self.verticalLayout_40 = QtWidgets.QVBoxLayout()
        self.verticalLayout_40.setSpacing(0)
        self.verticalLayout_40.setObjectName("verticalLayout_40")

        """---------------------Панель даты расчёта---------------------"""
        self.bonds_groupBox_calendar = GroupBox_CalculationDate('bonds_groupBox_calendar', self.layoutWidget1)
        self.verticalLayout_40.addWidget(self.bonds_groupBox_calendar)
        """-------------------------------------------------------------"""

        spacerItem37 = QtWidgets.QSpacerItem(20, 2, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        self.verticalLayout_40.addItem(spacerItem37)
        self.verticalLayout_40.setStretch(1, 1)
        self.horizontalLayout_37.addLayout(self.verticalLayout_40)
        self.verticalLayout_41 = QtWidgets.QVBoxLayout()
        self.verticalLayout_41.setSpacing(0)
        self.verticalLayout_41.setObjectName("verticalLayout_41")
        self.bonds_groupBox_filters = QtWidgets.QGroupBox(self.layoutWidget1)
        self.bonds_groupBox_filters.setTitle("")
        self.bonds_groupBox_filters.setObjectName("bonds_groupBox_filters")
        self.verticalLayout_36 = QtWidgets.QVBoxLayout(self.bonds_groupBox_filters)
        self.verticalLayout_36.setContentsMargins(2, 2, 2, 2)
        self.verticalLayout_36.setSpacing(0)
        self.verticalLayout_36.setObjectName("verticalLayout_36")
        self.horizontalLayout_25 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_25.setSpacing(0)
        self.horizontalLayout_25.setObjectName("horizontalLayout_25")
        spacerItem38 = QtWidgets.QSpacerItem(10, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_25.addItem(spacerItem38)
        spacerItem39 = QtWidgets.QSpacerItem(0, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_25.addItem(spacerItem39)
        self.label_58 = QtWidgets.QLabel(self.bonds_groupBox_filters)
        font = QtGui.QFont()
        font.setBold(True)
        self.label_58.setFont(font)
        self.label_58.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.label_58.setObjectName("label_58")
        self.horizontalLayout_25.addWidget(self.label_58)
        self.bonds_label_filtered_count = QtWidgets.QLabel(self.bonds_groupBox_filters)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.bonds_label_filtered_count.sizePolicy().hasHeightForWidth())
        self.bonds_label_filtered_count.setSizePolicy(sizePolicy)
        self.bonds_label_filtered_count.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignTrailing | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.bonds_label_filtered_count.setObjectName('bonds_label_filtered_count')
        self.horizontalLayout_25.addWidget(self.bonds_label_filtered_count)
        spacerItem40 = QtWidgets.QSpacerItem(10, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_25.addItem(spacerItem40)
        self.verticalLayout_36.addLayout(self.horizontalLayout_25)

        self.horizontalLayout_35 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_35.setSpacing(0)
        self.horizontalLayout_35.setObjectName('horizontalLayout_35')

        """---------------------Панель фильтров инструментов---------------------"""
        self.bonds_groupBox_instruments_filters = GroupBox_InstrumentsFilters('bonds_groupBox_instruments_filters', self.bonds_groupBox_filters)
        self.horizontalLayout_35.addWidget(self.bonds_groupBox_instruments_filters)
        """----------------------------------------------------------------------"""

        spacerItem41 = QtWidgets.QSpacerItem(0, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_35.addItem(spacerItem41)
        self.verticalLayout_36.addLayout(self.horizontalLayout_35)
        self.horizontalLayout_34 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_34.setSpacing(0)
        self.horizontalLayout_34.setObjectName("horizontalLayout_34")
        self.groupBox_9 = QtWidgets.QGroupBox(self.bonds_groupBox_filters)
        self.groupBox_9.setObjectName("groupBox_9")
        self.verticalLayout_34 = QtWidgets.QVBoxLayout(self.groupBox_9)
        self.verticalLayout_34.setContentsMargins(2, 2, 2, 2)
        self.verticalLayout_34.setSpacing(2)
        self.verticalLayout_34.setObjectName("verticalLayout_34")
        self.gridLayout_3 = QtWidgets.QGridLayout()
        self.gridLayout_3.setHorizontalSpacing(7)
        self.gridLayout_3.setVerticalSpacing(2)
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.label_72 = QtWidgets.QLabel(self.groupBox_9)
        self.label_72.setObjectName("label_72")
        self.gridLayout_3.addWidget(self.label_72, 0, 0, 1, 1)
        self.bonds_comboBox_maturity = QtWidgets.QComboBox(self.groupBox_9)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.bonds_comboBox_maturity.sizePolicy().hasHeightForWidth())
        self.bonds_comboBox_maturity.setSizePolicy(sizePolicy)
        self.bonds_comboBox_maturity.setObjectName("bonds_comboBox_maturity")
        self.bonds_comboBox_maturity.addItem("")
        self.bonds_comboBox_maturity.addItem("")
        self.bonds_comboBox_maturity.addItem("")
        self.gridLayout_3.addWidget(self.bonds_comboBox_maturity, 0, 1, 1, 1)
        self.label_76 = QtWidgets.QLabel(self.groupBox_9)
        self.label_76.setObjectName("label_76")
        self.gridLayout_3.addWidget(self.label_76, 0, 2, 1, 1)
        self.bonds_comboBox_floating_coupon = QtWidgets.QComboBox(self.groupBox_9)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.bonds_comboBox_floating_coupon.sizePolicy().hasHeightForWidth())
        self.bonds_comboBox_floating_coupon.setSizePolicy(sizePolicy)
        self.bonds_comboBox_floating_coupon.setObjectName("bonds_comboBox_floating_coupon")
        self.bonds_comboBox_floating_coupon.addItem("")
        self.bonds_comboBox_floating_coupon.addItem("")
        self.bonds_comboBox_floating_coupon.addItem("")
        self.gridLayout_3.addWidget(self.bonds_comboBox_floating_coupon, 0, 3, 1, 1)
        self.label_79 = QtWidgets.QLabel(self.groupBox_9)
        self.label_79.setObjectName("label_79")
        self.gridLayout_3.addWidget(self.label_79, 1, 0, 1, 1)
        self.bonds_comboBox_risk = QtWidgets.QComboBox(self.groupBox_9)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.bonds_comboBox_risk.sizePolicy().hasHeightForWidth())
        self.bonds_comboBox_risk.setSizePolicy(sizePolicy)
        self.bonds_comboBox_risk.setObjectName("bonds_comboBox_risk")
        self.bonds_comboBox_risk.addItem("")
        self.bonds_comboBox_risk.addItem("")
        self.bonds_comboBox_risk.addItem("")
        self.bonds_comboBox_risk.addItem("")
        self.bonds_comboBox_risk.addItem("")
        self.gridLayout_3.addWidget(self.bonds_comboBox_risk, 1, 1, 1, 1)
        self.label_73 = QtWidgets.QLabel(self.groupBox_9)
        self.label_73.setObjectName("label_73")
        self.gridLayout_3.addWidget(self.label_73, 1, 2, 1, 1)
        self.bonds_comboBox_perpetual = QtWidgets.QComboBox(self.groupBox_9)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.bonds_comboBox_perpetual.sizePolicy().hasHeightForWidth())
        self.bonds_comboBox_perpetual.setSizePolicy(sizePolicy)
        self.bonds_comboBox_perpetual.setObjectName("bonds_comboBox_perpetual")
        self.bonds_comboBox_perpetual.addItem("")
        self.bonds_comboBox_perpetual.addItem("")
        self.bonds_comboBox_perpetual.addItem("")
        self.gridLayout_3.addWidget(self.bonds_comboBox_perpetual, 1, 3, 1, 1)
        self.label_77 = QtWidgets.QLabel(self.groupBox_9)
        self.label_77.setObjectName("label_77")
        self.gridLayout_3.addWidget(self.label_77, 2, 0, 1, 1)
        self.bonds_comboBox_amortization = QtWidgets.QComboBox(self.groupBox_9)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.bonds_comboBox_amortization.sizePolicy().hasHeightForWidth())
        self.bonds_comboBox_amortization.setSizePolicy(sizePolicy)
        self.bonds_comboBox_amortization.setObjectName("bonds_comboBox_amortization")
        self.bonds_comboBox_amortization.addItem("")
        self.bonds_comboBox_amortization.addItem("")
        self.bonds_comboBox_amortization.addItem("")
        self.gridLayout_3.addWidget(self.bonds_comboBox_amortization, 2, 1, 1, 1)
        self.label_78 = QtWidgets.QLabel(self.groupBox_9)
        self.label_78.setObjectName("label_78")
        self.gridLayout_3.addWidget(self.label_78, 2, 2, 1, 1)
        self.bonds_comboBox_subord = QtWidgets.QComboBox(self.groupBox_9)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.bonds_comboBox_subord.sizePolicy().hasHeightForWidth())
        self.bonds_comboBox_subord.setSizePolicy(sizePolicy)
        self.bonds_comboBox_subord.setObjectName("bonds_comboBox_subord")
        self.bonds_comboBox_subord.addItem("")
        self.bonds_comboBox_subord.addItem("")
        self.bonds_comboBox_subord.addItem("")
        self.gridLayout_3.addWidget(self.bonds_comboBox_subord, 2, 3, 1, 1)
        self.verticalLayout_34.addLayout(self.gridLayout_3)
        self.horizontalLayout_34.addWidget(self.groupBox_9)
        spacerItem42 = QtWidgets.QSpacerItem(0, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_34.addItem(spacerItem42)
        self.verticalLayout_36.addLayout(self.horizontalLayout_34)
        self.verticalLayout_41.addWidget(self.bonds_groupBox_filters)
        spacerItem43 = QtWidgets.QSpacerItem(20, 0, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        self.verticalLayout_41.addItem(spacerItem43)
        self.horizontalLayout_37.addLayout(self.verticalLayout_41)
        self.groupBox_7 = QtWidgets.QGroupBox(self.layoutWidget1)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.groupBox_7.sizePolicy().hasHeightForWidth())
        self.groupBox_7.setSizePolicy(sizePolicy)
        self.groupBox_7.setTitle("")
        self.groupBox_7.setObjectName("groupBox_7")
        self.verticalLayout_33 = QtWidgets.QVBoxLayout(self.groupBox_7)
        self.verticalLayout_33.setContentsMargins(2, 2, 2, 2)
        self.verticalLayout_33.setSpacing(2)
        self.verticalLayout_33.setObjectName("verticalLayout_33")
        self.horizontalLayout_28 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_28.setSpacing(0)
        self.horizontalLayout_28.setObjectName("horizontalLayout_28")
        spacerItem44 = QtWidgets.QSpacerItem(10, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_28.addItem(spacerItem44)
        spacerItem45 = QtWidgets.QSpacerItem(0, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_28.addItem(spacerItem45)
        self.label_57 = QtWidgets.QLabel(self.groupBox_7)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_57.sizePolicy().hasHeightForWidth())
        self.label_57.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setPointSize(9)
        font.setBold(True)
        self.label_57.setFont(font)
        self.label_57.setStyleSheet("border: none;")
        self.label_57.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.label_57.setObjectName("label_57")
        self.horizontalLayout_28.addWidget(self.label_57)
        self.bonds_label_coupons_count = QtWidgets.QLabel(self.groupBox_7)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.bonds_label_coupons_count.sizePolicy().hasHeightForWidth())
        self.bonds_label_coupons_count.setSizePolicy(sizePolicy)
        self.bonds_label_coupons_count.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignTrailing | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.bonds_label_coupons_count.setObjectName("bonds_label_coupons_count")
        self.horizontalLayout_28.addWidget(self.bonds_label_coupons_count)
        spacerItem46 = QtWidgets.QSpacerItem(10, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_28.addItem(spacerItem46)
        self.verticalLayout_33.addLayout(self.horizontalLayout_28)
        self.bonds_tableView_coupons = QtWidgets.QTableView(self.groupBox_7)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.bonds_tableView_coupons.sizePolicy().hasHeightForWidth())
        self.bonds_tableView_coupons.setSizePolicy(sizePolicy)
        self.bonds_tableView_coupons.setStyleSheet("background-color: rgb(255, 255, 255);")
        self.bonds_tableView_coupons.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.bonds_tableView_coupons.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.bonds_tableView_coupons.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.bonds_tableView_coupons.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.bonds_tableView_coupons.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.bonds_tableView_coupons.setGridStyle(QtCore.Qt.PenStyle.SolidLine)
        self.bonds_tableView_coupons.setSortingEnabled(True)
        self.bonds_tableView_coupons.setObjectName("bonds_tableView_coupons")
        self.verticalLayout_33.addWidget(self.bonds_tableView_coupons)
        self.horizontalLayout_37.addWidget(self.groupBox_7)
        self.horizontalLayout_37.setStretch(2, 1)
        self.verticalLayout_42.addLayout(self.horizontalLayout_37)
        self.verticalLayout_42.setStretch(1, 1)
        self.groupBox_8 = QtWidgets.QGroupBox(self.splitter_5)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.groupBox_8.sizePolicy().hasHeightForWidth())
        self.groupBox_8.setSizePolicy(sizePolicy)
        self.groupBox_8.setBaseSize(QtCore.QSize(0, 0))
        self.groupBox_8.setTitle("")
        self.groupBox_8.setObjectName("groupBox_8")
        self.verticalLayout_32 = QtWidgets.QVBoxLayout(self.groupBox_8)
        self.verticalLayout_32.setContentsMargins(2, 2, 2, 2)
        self.verticalLayout_32.setSpacing(2)
        self.verticalLayout_32.setObjectName("verticalLayout_32")
        self.horizontalLayout_27 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_27.setSpacing(0)
        self.horizontalLayout_27.setObjectName("horizontalLayout_27")
        spacerItem47 = QtWidgets.QSpacerItem(10, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_27.addItem(spacerItem47)
        self.bonds_lineEdit_search = QtWidgets.QLineEdit(self.groupBox_8)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.bonds_lineEdit_search.sizePolicy().hasHeightForWidth())
        self.bonds_lineEdit_search.setSizePolicy(sizePolicy)
        self.bonds_lineEdit_search.setObjectName("bonds_lineEdit_search")
        self.horizontalLayout_27.addWidget(self.bonds_lineEdit_search)
        spacerItem48 = QtWidgets.QSpacerItem(0, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_27.addItem(spacerItem48)
        self.label_56 = QtWidgets.QLabel(self.groupBox_8)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_56.sizePolicy().hasHeightForWidth())
        self.label_56.setSizePolicy(sizePolicy)
        self.label_56.setMaximumSize(QtCore.QSize(16777215, 13))
        font = QtGui.QFont()
        font.setPointSize(9)
        font.setBold(True)
        self.label_56.setFont(font)
        self.label_56.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.label_56.setObjectName("label_56")
        self.horizontalLayout_27.addWidget(self.label_56)
        self.bonds_label_view_count = QtWidgets.QLabel(self.groupBox_8)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.bonds_label_view_count.sizePolicy().hasHeightForWidth())
        self.bonds_label_view_count.setSizePolicy(sizePolicy)
        self.bonds_label_view_count.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignTrailing | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.bonds_label_view_count.setObjectName("bonds_label_view_count")
        self.horizontalLayout_27.addWidget(self.bonds_label_view_count)
        spacerItem49 = QtWidgets.QSpacerItem(10, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_27.addItem(spacerItem49)
        self.horizontalLayout_27.setStretch(1, 1)
        self.horizontalLayout_27.setStretch(2, 1)
        self.horizontalLayout_27.setStretch(4, 2)
        self.verticalLayout_32.addLayout(self.horizontalLayout_27)
        self.bonds_tableView_bonds = QtWidgets.QTableView(self.groupBox_8)
        self.bonds_tableView_bonds.setEnabled(True)
        self.bonds_tableView_bonds.setBaseSize(QtCore.QSize(0, 557))
        self.bonds_tableView_bonds.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.bonds_tableView_bonds.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.bonds_tableView_bonds.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.bonds_tableView_bonds.setSortingEnabled(True)
        self.bonds_tableView_bonds.setObjectName("bonds_tableView_bonds")
        self.verticalLayout_32.addWidget(self.bonds_tableView_bonds)
        self.verticalLayout_43.addWidget(self.splitter_5)
        self.tabWidget.addTab(self.tab_bonds, "")
        """------------------------------------------------------------------------------"""

        self.main_verticalLayout.addWidget(self.tabWidget)
        main_window.setCentralWidget(self.centralwidget)
        self.statusbar = QtWidgets.QStatusBar(main_window)
        self.statusbar.setObjectName("statusbar")
        main_window.setStatusBar(self.statusbar)

        self.retranslateUi(main_window)
        self.tabWidget.setCurrentIndex(2)
        self.bonds_comboBox_maturity.setCurrentIndex(1)
        self.bonds_comboBox_floating_coupon.setCurrentIndex(0)
        self.bonds_comboBox_perpetual.setCurrentIndex(0)
        self.bonds_comboBox_amortization.setCurrentIndex(0)
        self.bonds_comboBox_subord.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(main_window)

    def retranslateUi(self, main_window: QtWidgets.QMainWindow):
        _translate = QtCore.QCoreApplication.translate
        main_window.setWindowTitle(_translate("MainWindow", "Тинькофф Инвестиции"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_tokens), _translate("MainWindow", "Токены"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_limits), _translate("MainWindow", "Лимиты"))

        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_shares), _translate("MainWindow", "Акции"))
        self.label_64.setText(_translate("MainWindow", "ПОЛУЧЕНИЕ КУПОНОВ"))
        self.bonds_progressBar_coupons.setFormat(_translate("MainWindow", "%v из %m (%p%)"))
        self.label_66.setToolTip(_translate("MainWindow", "Тип купона."))
        self.label_66.setText(_translate("MainWindow", "Тип купонов:"))
        self.bonds_comboBox_coupon_type.setItemText(0, _translate("MainWindow", "Любой"))
        self.bonds_comboBox_coupon_type.setItemText(1, _translate("MainWindow", "Постоянный"))
        self.bonds_comboBox_coupon_type.setItemText(2, _translate("MainWindow", "Фиксированный"))
        self.bonds_comboBox_coupon_type.setItemText(3, _translate("MainWindow", "Переменный"))
        self.bonds_comboBox_coupon_type.setItemText(4, _translate("MainWindow", "Плавающий"))
        self.bonds_comboBox_coupon_type.setItemText(5, _translate("MainWindow", "Дисконт"))
        self.bonds_comboBox_coupon_type.setItemText(6, _translate("MainWindow", "Ипотечный"))
        self.bonds_comboBox_coupon_type.setItemText(7, _translate("MainWindow", "Прочее"))
        self.bonds_comboBox_coupon_type.setItemText(8, _translate("MainWindow", "Неопределённый"))
        self.label_58.setText(_translate("MainWindow", "ФИЛЬТРЫ"))
        self.bonds_label_filtered_count.setText(_translate("MainWindow", "0"))

        self.groupBox_9.setTitle(_translate("MainWindow", "Фильтры облигаций"))
        self.label_72.setToolTip(_translate("MainWindow", "Флаг, отображающий погашенность облигации к текущей дате."))
        self.label_72.setText(_translate("MainWindow", "Погашенность:"))
        self.bonds_comboBox_maturity.setItemText(0, _translate("MainWindow", "Все"))
        self.bonds_comboBox_maturity.setItemText(1, _translate("MainWindow", "Непогашенные"))
        self.bonds_comboBox_maturity.setItemText(2, _translate("MainWindow", "Погашенные"))
        self.label_76.setToolTip(_translate("MainWindow", "Признак облигации с плавающим купоном."))
        self.label_76.setText(_translate("MainWindow", "Плавающий купон:"))
        self.bonds_comboBox_floating_coupon.setItemText(0, _translate("MainWindow", "Все"))
        self.bonds_comboBox_floating_coupon.setItemText(1, _translate("MainWindow", "True"))
        self.bonds_comboBox_floating_coupon.setItemText(2, _translate("MainWindow", "False"))
        self.label_79.setToolTip(_translate("MainWindow", "Уровень риска."))
        self.label_79.setText(_translate("MainWindow", "Уровень риска:"))
        self.bonds_comboBox_risk.setItemText(0, _translate("MainWindow", "Любой"))
        self.bonds_comboBox_risk.setItemText(1, _translate("MainWindow", "Низкий"))
        self.bonds_comboBox_risk.setItemText(2, _translate("MainWindow", "Средний"))
        self.bonds_comboBox_risk.setItemText(3, _translate("MainWindow", "Высокий"))
        self.bonds_comboBox_risk.setItemText(4, _translate("MainWindow", "Неизвестен"))
        self.label_73.setToolTip(_translate("MainWindow", "Признак бессрочной облигации."))
        self.label_73.setText(_translate("MainWindow", "Бессрочность:"))
        self.bonds_comboBox_perpetual.setItemText(0, _translate("MainWindow", "Все"))
        self.bonds_comboBox_perpetual.setItemText(1, _translate("MainWindow", "True"))
        self.bonds_comboBox_perpetual.setItemText(2, _translate("MainWindow", "False"))
        self.label_77.setToolTip(_translate("MainWindow", "Признак облигации с амортизацией долга."))
        self.label_77.setText(_translate("MainWindow", "Амортизация:"))
        self.bonds_comboBox_amortization.setItemText(0, _translate("MainWindow", "Все"))
        self.bonds_comboBox_amortization.setItemText(1, _translate("MainWindow", "True"))
        self.bonds_comboBox_amortization.setItemText(2, _translate("MainWindow", "False"))
        self.label_78.setToolTip(_translate("MainWindow", "Признак субординированной облигации."))
        self.label_78.setText(_translate("MainWindow", "Суборд:"))
        self.bonds_comboBox_subord.setItemText(0, _translate("MainWindow", "Все"))
        self.bonds_comboBox_subord.setItemText(1, _translate("MainWindow", "True"))
        self.bonds_comboBox_subord.setItemText(2, _translate("MainWindow", "False"))
        self.label_57.setText(_translate("MainWindow", "КУПОНЫ"))
        self.bonds_label_coupons_count.setText(_translate("MainWindow", "0"))
        self.bonds_lineEdit_search.setPlaceholderText(_translate("MainWindow", "Поиск..."))
        self.label_56.setText(_translate("MainWindow", "ОБЛИГАЦИИ"))
        self.bonds_label_view_count.setText(_translate("MainWindow", "0 / 0"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_bonds), _translate("MainWindow", "Облигации"))


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

        """---Подключаем ComboBox'ы для отображения токенов к модели---"""
        token_list_model: TokenListModel = TokenListModel()
        token_list_model.setSourceModel(token_model)
        self.limits_groupBox_request.comboBox_token.setModel(token_list_model)
        # self.shares_groupBox_request.comboBox_token.setModel(token_list_model)
        self.tab_shares.setTokensModel(token_list_model)
        self.bonds_groupBox_request.comboBox_token.setModel(token_list_model)
        """------------------------------------------------------------"""

        """---------------------Модель доступа---------------------"""
        tree_token_model: TreeProxyModel = TreeProxyModel(token_model)
        self.tokens_groupBox_tokens.setModel(tree_token_model)  # Подключаем модель к TreeView.
        """--------------------------------------------------------"""

        """---------------------------Подключение слотов---------------------------"""
        self.tokens_groupBox_new_token.add_token_signal.connect(token_model.addToken)
        """------------------------------------------------------------------------"""

        """---------------------Модель лимитов---------------------"""
        limits_model: LimitsTreeModel = LimitsTreeModel()
        self.limits_groupBox_view.setModel(limits_model)  # Подключаем модель к TreeView.
        self.limits_groupBox_request.comboBox_token.currentIndexChanged.connect(lambda index: self.limits_groupBox_view.setToken(self.limits_groupBox_request.getCurrentToken()))
        """--------------------------------------------------------"""
