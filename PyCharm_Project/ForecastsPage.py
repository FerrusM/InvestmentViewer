from PyQt6 import QtWidgets, QtCore
from DatabaseWidgets import GroupBox_InstrumentSelection, TITLE_FONT
from TokenModel import TokenListModel


class MyTableViewGroupBoxWidget(QtWidgets.QGroupBox):
    def __init__(self, model, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        self.setSizePolicy(sizePolicy)

        self.verticalLayout_main = QtWidgets.QVBoxLayout(self)
        self.verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        self.verticalLayout_main.setSpacing(2)

        '''------------------------------Заголовок------------------------------'''
        vPolicy: QtWidgets.QSizePolicy.Policy = QtWidgets.QSizePolicy.Policy.Minimum

        self.horizontalLayout_title = QtWidgets.QHBoxLayout()
        self.horizontalLayout_title.setSpacing(0)

        spacerItem_title_first = QtWidgets.QSpacerItem(10, 20, QtWidgets.QSizePolicy.Policy.Fixed, vPolicy)
        self.horizontalLayout_title.addItem(spacerItem_title_first)

        spacerItem_title_expanding = QtWidgets.QSpacerItem(0, 20, QtWidgets.QSizePolicy.Policy.Expanding, vPolicy)
        self.horizontalLayout_title.addItem(spacerItem_title_expanding)

        self.label_title = QtWidgets.QLabel(self)
        self.label_title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.label_title.setFont(TITLE_FONT)
        self.label_title.setText('ПРОГНОЗЫ')
        self.horizontalLayout_title.addWidget(self.label_title)

        self.label_count = QtWidgets.QLabel(self)
        self.label_count.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, vPolicy))
        self.label_count.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignTrailing | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.label_count.setText('0')
        self.horizontalLayout_title.addWidget(self.label_count)

        spacerItem_title_last = QtWidgets.QSpacerItem(10, 20, QtWidgets.QSizePolicy.Policy.Fixed, vPolicy)
        self.horizontalLayout_title.addItem(spacerItem_title_last)

        self.verticalLayout_main.addLayout(self.horizontalLayout_title)
        '''---------------------------------------------------------------------'''

        '''------------------------------Отображение------------------------------'''
        self.tableView = QtWidgets.QTableView(parent=self)
        self.tableView.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tableView.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.tableView.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.tableView.setSortingEnabled(True)

        self.tableView.setModel(model)  # Подключаем модель к таблице.
        self.tableView.resizeColumnsToContents()  # Авторазмер столбцов под содержимое.

        self.verticalLayout_main.addWidget(self.tableView)
        '''-----------------------------------------------------------------------'''


class ForecastsPage(QtWidgets.QWidget):
    """Страница прогнозов."""
    class ConsensusItemsModel(QtCore.QAbstractTableModel):
        def __init__(self, parent: QtCore.QObject | None = None):
            super().__init__(parent=parent)
            pass
            self.__items: list = []

        def rowCount(self, parent: QtCore.QModelIndex = ...) -> int:
            return len(self.__items)

        def columnCount(self, parent: QtCore.QModelIndex = ...) -> int:
            pass
            return 0

    def __init__(self, tokens_model: TokenListModel, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)

        verticalLayout_main = QtWidgets.QVBoxLayout(self)
        verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        verticalLayout_main.setSpacing(2)

        self.groupBox_instrument_selection = GroupBox_InstrumentSelection(tokens_model=tokens_model, parent=parent)
        verticalLayout_main.addWidget(self.groupBox_instrument_selection, 0)

        self.view_panel = MyTableViewGroupBoxWidget(model=ForecastsPage.ConsensusItemsModel(self), parent=self)
        verticalLayout_main.addWidget(self.view_panel, 1)

        self.setLayout(verticalLayout_main)
