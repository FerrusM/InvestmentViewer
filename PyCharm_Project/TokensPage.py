import typing
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import QModelIndex, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import QMessageBox
from tinkoff.invest import Account, UnaryLimit, StreamLimit
from Classes import TokenClass, MyTreeView, reportAccountType, reportAccountStatus, reportAccountAccessLevel
from LimitClasses import MyUnaryLimit, MyStreamLimit
from MyDateTime import reportSignificantInfoFromDateTime
from MyRequests import MyResponse, getUserTariff, getAccounts, RequestTryClass
from TokenModel import TokenModel
from TreeTokenModel import TreeProxyModel, TreeItem


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

    def setModel(self, token_model: TokenModel):
        """Подключает модель сохранённых токенов."""
        tree_token_model: TreeProxyModel = TreeProxyModel(token_model)
        self.treeView_saved_tokens.setModel(tree_token_model)

        '''------------------Создаём делегат кнопки удаления токенов------------------'''
        delete_button_delegate: TreeProxyModel.DeleteButtonDelegate = tree_token_model.DeleteButtonDelegate(self.treeView_saved_tokens)
        # delete_button_delegate.clicked.connect(lambda index: print('Номер строки: {0}'.format(str(index.row()))))

        @pyqtSlot(str)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
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
                    deleted_flag: bool = tree_token_model.deleteToken(index)
                    # assert not deleted_flag, 'Проблема с удалением токена!'
                    if not deleted_flag:
                        raise ValueError('Проблема с удалением токена!')
                    """---------------------------------------------------------------------------"""
                    return
                case _:
                    assert False, 'Неверное значение нажатой кнопки в окне удаления токена ({0})!'.format(clicked_button)

        delete_button_delegate.clicked.connect(lambda index: deleteButtonFunction(index))
        '''---------------------------------------------------------------------------'''

        self.treeView_saved_tokens.setItemDelegateForColumn(tree_token_model.Columns.TOKEN_DELETE_BUTTON, delete_button_delegate)

        self.onUpdateView()  # Обновление отображения модели.
        tree_token_model.modelReset.connect(self.onUpdateView)

    def model(self):
        """Возвращает модель."""
        model = self.treeView_saved_tokens.model()
        assert type(model) == TreeProxyModel
        return typing.cast(TreeProxyModel, model)

    def onUpdateView(self):
        """Выполняется после обновления модели."""
        model: TreeProxyModel = self.model()
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

    @pyqtSlot(str)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
    def addedTokenChanged_slot(self, text: str):
        """Событие при изменении добавляемого токена."""
        self._clearAccountsTabWidget()  # Очищаем tabWidget счетов добавляемого токена.

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

        # accounts_response: MyResponse = getAccounts(text, False)
        # assert accounts_response.request_occurred, 'Запрос счетов не был произведён.'
        # accounts_list: list[Account] = accounts_response.response_data  # Получаем список счетов.

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

            '''------------------------Компоновка------------------------'''
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
            '''----------------------------------------------------------'''

            self.tabWidget_accounts.addTab(account_tab, '')  # Добавляем страницу.
            self.tabWidget_accounts.setTabText(i, 'Счёт ' + str(i + 1))

    @pyqtSlot()  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
    def _addToken(self):
        """Добавляет токен в модель."""
        new_token: str = self.lineEdit_new_token.text()  # Извлекаем текст из lineEdit.
        assert new_token == self.current_token_class.token

        '''---------------------------Получение лимитов---------------------------'''
        limits_try_count: RequestTryClass = RequestTryClass(1)
        limits_response: MyResponse = MyResponse()
        while limits_try_count and not limits_response.ifDataSuccessfullyReceived():
            limits_response = getUserTariff(self.current_token_class.token)
            assert limits_response.request_occurred, 'Запрос лимитов не был произведён.'
            limits_try_count += 1

        if limits_response.ifDataSuccessfullyReceived():
            unary_limits: list[UnaryLimit]
            stream_limits: list[StreamLimit]
            unary_limits, stream_limits = limits_response.response_data
            my_unary_limits: list[MyUnaryLimit] = [MyUnaryLimit(unary_limit) for unary_limit in unary_limits]  # Массив лимитов пользователя по unary-запросам.
            my_stream_limits: list[MyStreamLimit] = [MyStreamLimit(stream_limit) for stream_limit in stream_limits]  # Массив лимитов пользователя по stream-соединениям.
        else:
            my_unary_limits: list[MyUnaryLimit] = []  # Массив лимитов пользователя по unary-запросам.
            my_stream_limits: list[MyStreamLimit] = []  # Массив лимитов пользователя по stream-соединениям.
        '''-----------------------------------------------------------------------'''

        # unary_limits, stream_limits = getUserTariff(self.current_token_class.token).response_data
        # my_unary_limits: list[MyUnaryLimit] = [MyUnaryLimit(unary_limit) for unary_limit in unary_limits]  # Массив лимитов пользователя по unary-запросам.
        # my_stream_limits: list[MyStreamLimit] = [MyStreamLimit(stream_limit) for stream_limit in stream_limits]  # Массив лимитов пользователя по stream-соединениям.

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


class TokensPage(QtWidgets.QWidget):
    """Страница токенов."""
    def __init__(self, object_name: str, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)  # QWidget __init__().
        self.setObjectName(object_name)

        self.verticalLayout_main = QtWidgets.QVBoxLayout(self)
        self.verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        self.verticalLayout_main.setSpacing(2)
        self.verticalLayout_main.setObjectName('verticalLayout_main')

        """------------Панель отображения сохранённых токенов------------"""
        self.groupBox_saved_tokens: GroupBox_SavedTokens = GroupBox_SavedTokens('groupBox_saved_tokens', self)
        self.verticalLayout_main.addWidget(self.groupBox_saved_tokens)
        """--------------------------------------------------------------"""

        """----------------Панель добавления нового токена----------------"""
        self.groupBox_new_token: GroupBox_NewToken = GroupBox_NewToken('groupBox_new_token', self)
        self.verticalLayout_main.addWidget(self.groupBox_new_token)
        """---------------------------------------------------------------"""

    def setModel(self, token_model: TokenModel):
        """Устанавливает модель токенов для TreeView."""
        self.groupBox_saved_tokens.setModel(token_model)
        self.groupBox_new_token.add_token_signal.connect(token_model.addToken)
