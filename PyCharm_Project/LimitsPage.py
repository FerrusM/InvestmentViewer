from PyQt6 import QtCore, QtGui, QtWidgets
from Classes import MyTreeView, TokenClass
from LimitsModel import LimitsTreeModel
from PagesClasses import GroupBox_Request
from TokenModel import TokenListModel


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
        self.lineEdit_search.setPlaceholderText(_translate('MainWindow', 'Поиск...'))
        self.label_title.setText(_translate('MainWindow', 'ЛИМИТЫ'))
        self.label_count.setText(_translate('MainWindow', '0'))

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
    def __init__(self, object_name: str, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)  # QWidget __init__().
        self.setObjectName(object_name)

        self.verticalLayout_main = QtWidgets.QVBoxLayout(self)
        self.verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        self.verticalLayout_main.setSpacing(2)
        self.verticalLayout_main.setObjectName('verticalLayout_main')

        """------------------Панель выполнения запроса------------------"""
        self.groupBox_request: GroupBox_Request = GroupBox_Request('groupBox_request', self)
        self.verticalLayout_main.addWidget(self.groupBox_request)
        """-------------------------------------------------------------"""

        """------------------Панель отображения лимитов------------------"""
        self.groupBox_view: GroupBox_LimitsTreeView = GroupBox_LimitsTreeView('groupBox_view', self)
        self.verticalLayout_main.addWidget(self.groupBox_view)
        """--------------------------------------------------------------"""

        self.groupBox_request.comboBox_token.currentIndexChanged.connect(lambda index: self.groupBox_view.setToken(self.groupBox_request.getCurrentToken()))

    def setTokensModel(self, token_list_model: TokenListModel):
        """Устанавливает модель токенов для ComboBox'а."""
        self.groupBox_request.comboBox_token.setModel(token_list_model)

    def getCurrentToken(self) -> TokenClass | None:
        """Возвращает выбранный в ComboBox'е токен."""
        return self.groupBox_request.getCurrentToken()
