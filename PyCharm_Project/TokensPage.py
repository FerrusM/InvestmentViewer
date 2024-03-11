import typing
from PyQt6 import QtCore, QtWidgets
from tinkoff.invest import Account
from Classes import TokenClass, MyTreeView, reportAccountType, reportAccountStatus, reportAccountAccessLevel
from LimitClasses import MyUnaryLimit, MyStreamLimit
from MyDatabase import MainConnection
from MyDateTime import reportSignificantInfoFromDateTime
from MyRequests import MyResponse, getUserTariff, getAccounts, RequestTryClass
from PagesClasses import TitleLabel, TitleWithCount
from TokenModel import TokenModel
from TreeTokenModel import TreeProxyModel, TreeItem


class GroupBox_SavedTokens(QtWidgets.QGroupBox):
    """Панель отображения сохранённых токенов."""
    def __init__(self, token_model: TokenModel, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)

        verticalLayout_main = QtWidgets.QVBoxLayout(self)
        verticalLayout_main.setContentsMargins(2, 2, 2, 3)
        verticalLayout_main.setSpacing(2)

        """------------Заголовок над отображением токенов------------"""
        self.titlebar = TitleWithCount(title='СОХРАНЁННЫЕ ТОКЕНЫ', count_text='0', parent=self)
        verticalLayout_main.addLayout(self.titlebar, 0)
        """----------------------------------------------------------"""

        self.treeView_saved_tokens = MyTreeView(self)  # Отображение токенов.
        tree_model: TreeProxyModel = TreeProxyModel(token_model)

        """=================================Подключаем модель сохранённых токенов================================="""
        '''------------------Создаём делегат кнопки удаления токенов------------------'''
        delete_button_delegate: TreeProxyModel.DeleteButtonDelegate = tree_model.DeleteButtonDelegate(self.treeView_saved_tokens)

        def deleteButtonFunction(index: QtCore.QModelIndex):
            def getTokenFromIndex(model_index: QtCore.QModelIndex) -> str:
                """Получает и возвращает токен, соответствующий индексу."""
                tree_item: TreeItem = model_index.internalPointer()  # Указатель на внутреннюю структуру данных.
                assert type(tree_item) is TreeItem
                token_class: TokenClass = tree_item.data
                assert type(token_class) is TokenClass
                return token_class.token

            @QtCore.pyqtSlot(str)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
            def deleteTokenDialog(deleting_token: str) -> QtWidgets.QMessageBox.StandardButton:
                """Диалоговое окно удаления токена."""
                msgBox = QtWidgets.QMessageBox(icon=QtWidgets.QMessageBox.Icon.Warning,
                                               text='Вы уверены, что хотите удалить токен {0}?'.format(deleting_token))
                msgBox.setWindowTitle('Удаление токена')
                msgBox.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
                msgBox.setDefaultButton(QtWidgets.QMessageBox.StandardButton.No)
                return QtWidgets.QMessageBox.StandardButton(msgBox.exec())

            token: str = getTokenFromIndex(index)
            clicked_button: QtWidgets.QMessageBox.StandardButton = deleteTokenDialog(token)
            match clicked_button:
                case QtWidgets.QMessageBox.StandardButton.No:
                    return
                case QtWidgets.QMessageBox.StandardButton.Yes:
                    """------------------------------Удаление токена------------------------------"""
                    deleted_flag: bool = tree_model.deleteToken(index)
                    if not deleted_flag:
                        raise ValueError('Проблема с удалением токена!')
                    """---------------------------------------------------------------------------"""
                    return
                case _:
                    assert False, 'Неверное значение нажатой кнопки в окне удаления токена ({0})!'.format(clicked_button)

        delete_button_delegate.clicked.connect(lambda index: deleteButtonFunction(index))
        '''---------------------------------------------------------------------------'''

        self.treeView_saved_tokens.setItemDelegateForColumn(tree_model.Columns.TOKEN_DELETE_BUTTON, delete_button_delegate)
        """======================================================================================================="""

        self.treeView_saved_tokens.setModel(tree_model)
        verticalLayout_main.addWidget(self.treeView_saved_tokens)
        self.onUpdateView()  # Обновление отображения модели.
        tree_model.modelReset.connect(self.onUpdateView)

    def model(self):
        """Возвращает модель."""
        model = self.treeView_saved_tokens.model()
        assert type(model) is TreeProxyModel
        return typing.cast(TreeProxyModel, model)

    def onUpdateView(self):
        """Выполняется после обновления модели."""
        self.treeView_saved_tokens.expandAll()  # Разворачивает все элементы.
        self.treeView_saved_tokens.resizeColumnsToContents()  # Авторазмер всех столбцов под содержимое.
        self.titlebar.setCount(str(self.model().getTokensCount()))  # Отображаем количество сохранённых токенов.


class GroupBox_NewToken(QtWidgets.QGroupBox):
    """Панель добавления нового токена."""
    add_token_signal: QtCore.pyqtSignal = QtCore.pyqtSignal(TokenClass)  # Сигнал, испускаемый при необходимости добавить токен в модель.

    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(sizePolicy)

        verticalLayout_main = QtWidgets.QVBoxLayout(self)
        verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        verticalLayout_main.setSpacing(2)

        verticalLayout_main.addWidget(TitleLabel(text='НОВЫЙ ТОКЕН', parent=self))  # Заголовок "Новый токен".

        """-------------Строка добавления нового токена-------------"""
        horizontalLayout = QtWidgets.QHBoxLayout(self)
        horizontalLayout.setSpacing(2)

        self.lineEdit_new_token = QtWidgets.QLineEdit(parent=self)
        self.lineEdit_new_token.setPlaceholderText('Введите токен')
        horizontalLayout.addWidget(self.lineEdit_new_token)

        self.lineEdit_token_name = QtWidgets.QLineEdit(parent=self)
        self.lineEdit_token_name.setPlaceholderText('Введите имя токена')
        horizontalLayout.addWidget(self.lineEdit_token_name)

        self.pushButton_save_token = QtWidgets.QPushButton(text='Сохранить', parent=self)
        self.pushButton_save_token.setEnabled(False)  # Кнопка "Сохранить" для нового токена д.б. неактивна по умолчанию.
        horizontalLayout.addWidget(self.pushButton_save_token)

        verticalLayout_main.addLayout(horizontalLayout)
        """---------------------------------------------------------"""

        """---------Отображение аккаунтов добавляемого токена---------"""
        self.tabWidget_accounts = QtWidgets.QTabWidget(self)
        self.tabWidget_accounts.setMinimumSize(QtCore.QSize(0, 100))
        self.tabWidget_accounts.setBaseSize(QtCore.QSize(0, 0))
        verticalLayout_main.addWidget(self.tabWidget_accounts)
        """-----------------------------------------------------------"""

        self.__current_token: TokenClass | None = None

        """---------------------Подключение слотов токенов---------------------"""
        self.lineEdit_new_token.textChanged.connect(self.__addedTokenChanged_slot)  # При изменении токена.
        self.pushButton_save_token.clicked.connect(self.__addToken)  # При сохранении нового токена.
        """--------------------------------------------------------------------"""

    def __clearAccountsTabWidget(self):
        """Очищает tabWidget счетов добавляемого токена."""
        tabs_count: int = self.tabWidget_accounts.count()
        for i in range(tabs_count):
            self.tabWidget_accounts.removeTab(i)

    @QtCore.pyqtSlot(str)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
    def __addedTokenChanged_slot(self, text: str):
        """Событие при изменении добавляемого токена."""
        self.__clearAccountsTabWidget()  # Очищаем tabWidget счетов добавляемого токена.

        if not text:  # Если строка токена пустая.
            self.pushButton_save_token.setEnabled(False)
        else:
            self.pushButton_save_token.setEnabled(True)

        '''------------------------Получение счетов------------------------'''
        accounts_try_count: RequestTryClass = RequestTryClass(1)
        accounts_response: MyResponse = MyResponse()
        while accounts_try_count and not accounts_response.ifDataSuccessfullyReceived():
            accounts_response = getAccounts(text, False)  # Получаем список счетов.
            assert accounts_response.request_occurred, 'Запрос счетов не был произведён.'
            accounts_try_count += 1
        accounts_list: list[Account] = accounts_response.response_data if accounts_response.ifDataSuccessfullyReceived() else []
        '''----------------------------------------------------------------'''

        self.__current_token = TokenClass(token=text, accounts=accounts_list, name='')
        for i, account in enumerate(accounts_list):
            account_tab = QtWidgets.QWidget()

            '''------------------------Компоновка------------------------'''
            gridLayout = QtWidgets.QGridLayout(account_tab)
            gridLayout.setHorizontalSpacing(10)
            gridLayout.setVerticalSpacing(1)

            gridLayout.addWidget(QtWidgets.QLabel(text='Идентификатор:', parent=account_tab), 0, 0)
            gridLayout.addWidget(QtWidgets.QLabel(text=account.id, parent=account_tab), 0, 1)
            gridLayout.addWidget(QtWidgets.QLabel(text='Название счёта:', parent=account_tab), 1, 0)
            gridLayout.addWidget(QtWidgets.QLabel(text=account.name, parent=account_tab), 1, 1)
            gridLayout.addWidget(QtWidgets.QLabel(text='Тип счёта:', parent=account_tab), 2, 0)
            gridLayout.addWidget(QtWidgets.QLabel(text=reportAccountType(account.type), parent=account_tab), 2, 1)
            gridLayout.addWidget(QtWidgets.QLabel(text='Уровень доступа:', parent=account_tab), 3, 0)
            gridLayout.addWidget(QtWidgets.QLabel(text=reportAccountAccessLevel(account.access_level), parent=account_tab), 3, 1)

            gridLayout.addWidget(QtWidgets.QLabel(text='Статус счёта:', parent=account_tab), 0, 2)
            gridLayout.addWidget(QtWidgets.QLabel(text=reportAccountStatus(account.status), parent=account_tab), 0, 3)
            gridLayout.addWidget(QtWidgets.QLabel(text='Дата открытия:', parent=account_tab), 1, 2)
            gridLayout.addWidget(QtWidgets.QLabel(text=reportSignificantInfoFromDateTime(account.opened_date), parent=account_tab), 1, 3)
            gridLayout.addWidget(QtWidgets.QLabel(text='Дата закрытия:', parent=account_tab), 2, 2)
            gridLayout.addWidget(QtWidgets.QLabel(text=reportSignificantInfoFromDateTime(account.closed_date), parent=account_tab), 2, 3)
            '''----------------------------------------------------------'''

            self.tabWidget_accounts.addTab(account_tab, 'Счёт {0}'.format(str(i + 1)))  # Добавляем страницу.

    @QtCore.pyqtSlot()  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
    def __addToken(self):
        """Добавляет токен в модель."""
        self.lineEdit_new_token.setEnabled(False)
        assert self.__current_token is not None and self.lineEdit_new_token.text() == self.__current_token.token

        '''---------------------------Получение лимитов---------------------------'''
        limits_try_count: RequestTryClass = RequestTryClass(1)
        limits_response: MyResponse = MyResponse()
        while limits_try_count and not limits_response.ifDataSuccessfullyReceived():
            limits_response = getUserTariff(self.__current_token.token)
            assert limits_response.request_occurred, 'Запрос лимитов не был произведён.'
            limits_try_count += 1

        if limits_response.ifDataSuccessfullyReceived():
            unary_limits, stream_limits = limits_response.response_data
            self.__current_token.unary_limits = [MyUnaryLimit(unary_limit) for unary_limit in unary_limits]  # Массив лимитов пользователя по unary-запросам.
            self.__current_token.stream_limits = [MyStreamLimit(stream_limit) for stream_limit in stream_limits]  # Массив лимитов пользователя по stream-соединениям.
        else:
            self.__current_token.unary_limits = []  # Массив лимитов пользователя по unary-запросам.
            self.__current_token.stream_limits = []  # Массив лимитов пользователя по stream-соединениям.
        '''-----------------------------------------------------------------------'''

        self.add_token_signal.emit(self.__current_token)
        self.__current_token = None
        self.lineEdit_new_token.clear()  # Очищает содержимое lineEdit.
        self.lineEdit_new_token.setEnabled(True)


class TokensPage(QtWidgets.QWidget):
    """Страница токенов."""
    def __init__(self, token_model: TokenModel, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)

        verticalLayout_main = QtWidgets.QVBoxLayout(self)
        verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        verticalLayout_main.setSpacing(2)

        """------------Панель отображения сохранённых токенов------------"""
        self.groupBox_saved_tokens: GroupBox_SavedTokens = GroupBox_SavedTokens(token_model, self)
        verticalLayout_main.addWidget(self.groupBox_saved_tokens)
        """--------------------------------------------------------------"""

        """----------------Панель добавления нового токена----------------"""
        self.groupBox_new_token: GroupBox_NewToken = GroupBox_NewToken(self)
        # self.groupBox_new_token.add_token_signal.connect(token_model.addToken)
        self.groupBox_new_token.add_token_signal.connect(MainConnection.addNewToken)
        verticalLayout_main.addWidget(self.groupBox_new_token)
        """---------------------------------------------------------------"""
