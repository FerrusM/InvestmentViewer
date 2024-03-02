from PyQt6 import QtCore, QtWidgets
from Classes import MyTreeView, TokenClass
from LimitsModel import LimitsTreeModel
from PagesClasses import GroupBox_Request, TitleLabel
from TokenModel import TokenListModel


class GroupBox_LimitsTreeView(QtWidgets.QGroupBox):
    """Панель отображения лимитов выбранного токена."""
    def __init__(self, object_name: str, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)
        self.setAutoFillBackground(False)
        self.setFlat(False)
        self.setCheckable(False)
        self.setObjectName(object_name)

        self.verticalLayout_main = QtWidgets.QVBoxLayout(self)
        self.verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        self.verticalLayout_main.setSpacing(2)

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

        self.verticalLayout_main.addLayout(horizontalLayout_title)
        """---------------------------------------------------------"""

        """-------------------Отображение лимитов-------------------"""
        self.treeView_limits = MyTreeView(self)
        self.verticalLayout_main.addWidget(self.treeView_limits)
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
        self.groupBox_request = GroupBox_Request('groupBox_request', self)
        verticalLayout_main.addWidget(self.groupBox_request, 0)
        """-------------------------------------------------------------"""

        """------------------Панель отображения лимитов------------------"""
        self.groupBox_view = GroupBox_LimitsTreeView('groupBox_view', self)
        verticalLayout_main.addWidget(self.groupBox_view, 1)
        """--------------------------------------------------------------"""

        # self.groupBox_request.comboBox_token.currentIndexChanged.connect(lambda index: self.groupBox_view.setToken(self.groupBox_request.getCurrentToken()))

        self.groupBox_request.currentTokenChanged.connect(self.groupBox_view.setToken)
        self.groupBox_request.currentTokenReset.connect(lambda: self.groupBox_view.setToken(None))

        self.groupBox_request.comboBox_token.setModel(tokens_model)  # Устанавливает модель токенов для ComboBox'а.
