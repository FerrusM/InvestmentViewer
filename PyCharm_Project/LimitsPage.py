from PyQt6 import QtCore, QtWidgets
from Classes import MyTreeView, TokenClass
from LimitClasses import MyUnaryLimit, MyStreamLimit
from LimitsModel import LimitsTreeModel
from MyDatabase import MainConnection
from MyRequests import RequestTryClass, MyResponse, getUserTariff
from common.pyqt6_widgets import TitleLabel
from TokenModel import TokenListModel


class GroupBox_Request(QtWidgets.QGroupBox):
    """GroupBox с параметрами запроса."""
    currentTokenChanged: QtCore.pyqtSignal = QtCore.pyqtSignal(TokenClass)  # Сигнал испускается при изменении текущего токена.
    currentTokenReset: QtCore.pyqtSignal = QtCore.pyqtSignal()  # Сигнал испускается при выборе пустого значения.

    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)

        verticalLayout_main = QtWidgets.QVBoxLayout(self)
        verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        verticalLayout_main.setSpacing(2)

        """------------------------Заголовок------------------------"""
        _title = TitleLabel(text='ЗАПРОС', parent=self)
        verticalLayout_main.addWidget(_title, 0)
        """---------------------------------------------------------"""

        """---------------------------Токен---------------------------"""
        horizontalLayout_token = QtWidgets.QHBoxLayout()
        horizontalLayout_token.setSpacing(0)

        self.label_token = QtWidgets.QLabel(text='Токен:', parent=self)
        self.label_token.setToolTip('Токен доступа.')
        horizontalLayout_token.addWidget(self.label_token, 0)

        horizontalLayout_token.addSpacing(4)

        self.comboBox_token = QtWidgets.QComboBox(self)
        self.comboBox_token.addItem('Не выбран')
        horizontalLayout_token.addWidget(self.comboBox_token)

        horizontalLayout_token.addStretch(1)

        self.update_button = QtWidgets.QPushButton(text='Обновить лимиты', parent=self)
        self.update_button.clicked.connect(self.updateLimits)
        horizontalLayout_token.addWidget(self.update_button, 0)

        verticalLayout_main.addLayout(horizontalLayout_token)
        """-----------------------------------------------------------"""

        def onTokenChangedSlot():
            current_token: TokenClass | None = self.getCurrentToken()
            self.currentTokenReset.emit() if current_token is None else self.currentTokenChanged.emit(current_token)

        self.comboBox_token.currentIndexChanged.connect(lambda index: onTokenChangedSlot())

    def setTokensModel(self, token_list_model: TokenListModel):
        """Устанавливает модель токенов для ComboBox'а."""
        self.comboBox_token.setModel(token_list_model)

    def getCurrentToken(self) -> TokenClass | None:
        """Возвращает выбранный в ComboBox'е токен."""
        return self.comboBox_token.currentData(role=QtCore.Qt.ItemDataRole.UserRole)

    @QtCore.pyqtSlot()  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
    def updateLimits(self):
        """Обновляет лимиты выбранного токена."""
        current_token: TokenClass | None = self.getCurrentToken()
        if current_token is not None:
            '''------------------------------Получение лимитов------------------------------'''
            limits_try_count: RequestTryClass = RequestTryClass(1)
            limits_response: MyResponse = MyResponse()
            while limits_try_count and not limits_response.ifDataSuccessfullyReceived():
                limits_response = getUserTariff(current_token.token)
                assert limits_response.request_occurred, 'Запрос лимитов не был произведён.'
                limits_try_count += 1

            if limits_response.ifDataSuccessfullyReceived():
                unary_limits, stream_limits = limits_response.response_data
                MainConnection.updateTokenLimits(token=current_token.token,
                                                 unary_limits=[MyUnaryLimit(unary_limit) for unary_limit in unary_limits],
                                                 stream_limits=[MyStreamLimit(stream_limit) for stream_limit in stream_limits])
            '''-----------------------------------------------------------------------------'''


class GroupBox_LimitsTreeView(QtWidgets.QGroupBox):
    """Панель отображения лимитов выбранного токена."""
    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)
        self.setAutoFillBackground(False)
        self.setFlat(False)
        self.setCheckable(False)

        verticalLayout_main = QtWidgets.QVBoxLayout(self)
        verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        verticalLayout_main.setSpacing(2)

        """------------------------Заголовок------------------------"""
        horizontalLayout_title = QtWidgets.QHBoxLayout()
        horizontalLayout_title.setSpacing(0)

        horizontalLayout_title.addSpacing(10)

        self.lineEdit_search = QtWidgets.QLineEdit(self)
        self.lineEdit_search.setPlaceholderText('Поиск...')
        horizontalLayout_title.addWidget(self.lineEdit_search, 1)

        horizontalLayout_title.addSpacerItem(QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum))
        horizontalLayout_title.setStretch(2, 1)

        horizontalLayout_title.addWidget(TitleLabel(text='ЛИМИТЫ', parent=self), 0)

        self.label_count = QtWidgets.QLabel(text='0', parent=self)
        self.label_count.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignTrailing | QtCore.Qt.AlignmentFlag.AlignVCenter)
        horizontalLayout_title.addWidget(self.label_count, 2)

        horizontalLayout_title.addSpacing(10)

        verticalLayout_main.addLayout(horizontalLayout_title)
        """---------------------------------------------------------"""

        """-------------------Отображение лимитов-------------------"""
        self.treeView_limits = MyTreeView(self)
        verticalLayout_main.addWidget(self.treeView_limits)
        """---------------------------------------------------------"""

        limits_model: LimitsTreeModel = LimitsTreeModel()
        self.treeView_limits.setModel(limits_model)  # Подключаем модель к TreeView.
        self.treeView_limits.resizeColumnsToContents()  # Авторазмер всех столбцов под содержимое.

    def setToken(self, token: TokenClass | None):
        """Устанавливает токен для отображения лимитов."""
        self.treeView_limits.model().setToken(token)
        self.treeView_limits.expandAll()  # Разворачивает все элементы.
        self.treeView_limits.resizeColumnsToContents()  # Авторазмер всех столбцов под содержимое.


class LimitsPage(QtWidgets.QWidget):
    """Страница лимитов."""
    def __init__(self, tokens_model: TokenListModel, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)

        verticalLayout_main = QtWidgets.QVBoxLayout(self)
        verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        verticalLayout_main.setSpacing(2)

        """------------------Панель выполнения запроса------------------"""
        self.groupBox_request = GroupBox_Request(parent=self)
        verticalLayout_main.addWidget(self.groupBox_request, 0)
        """-------------------------------------------------------------"""

        """------------------Панель отображения лимитов------------------"""
        self.groupBox_view = GroupBox_LimitsTreeView(parent=self)
        verticalLayout_main.addWidget(self.groupBox_view, 1)
        """--------------------------------------------------------------"""

        # self.groupBox_request.comboBox_token.currentIndexChanged.connect(lambda index: self.groupBox_view.setToken(self.groupBox_request.getCurrentToken()))

        self.groupBox_request.currentTokenChanged.connect(self.groupBox_view.setToken)
        self.groupBox_request.currentTokenReset.connect(lambda: self.groupBox_view.setToken(None))

        self.groupBox_request.comboBox_token.setModel(tokens_model)  # Устанавливает модель токенов для ComboBox'а.
