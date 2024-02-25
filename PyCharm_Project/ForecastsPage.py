from PyQt6 import QtWidgets, QtCore
from DatabaseWidgets import GroupBox_InstrumentSelection
from PagesClasses import TitleLabel, ProgressBar_DataReceiving, TitleWithCount
from TokenModel import TokenListModel


class MyTableViewGroupBox(QtWidgets.QGroupBox):
    def __init__(self, title: str, model, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)

        verticalLayout_main = QtWidgets.QVBoxLayout(self)
        verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        verticalLayout_main.setSpacing(2)

        '''------------------------------Заголовок------------------------------'''
        self.title_widget = TitleWithCount(title=title, count_text='0', parent=self)
        verticalLayout_main.addLayout(self.title_widget, 0)
        '''---------------------------------------------------------------------'''

        '''------------------------------Отображение------------------------------'''
        self.tableView = QtWidgets.QTableView(parent=self)
        self.tableView.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tableView.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.tableView.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.tableView.setSortingEnabled(True)

        self.tableView.setModel(model)  # Подключаем модель к таблице.
        self.tableView.resizeColumnsToContents()  # Авторазмер столбцов под содержимое.

        verticalLayout_main.addWidget(self.tableView, 1)
        '''-----------------------------------------------------------------------'''


class MyProgressBarGroupBox(QtWidgets.QGroupBox):
    def __init__(self, title: str, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)

        verticalLayout_main = QtWidgets.QVBoxLayout(self)
        verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        verticalLayout_main.setSpacing(2)

        verticalLayout_main.addWidget(TitleLabel(text=title, parent=self), 0)

        self.progressBar = ProgressBar_DataReceiving(parent=self)
        verticalLayout_main.addWidget(self.progressBar, 0)

        verticalLayout_main.addStretch(1)


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

        horizontalLayout_top = QtWidgets.QHBoxLayout()
        horizontalLayout_top.setSpacing(2)

        self.groupBox_instrument_selection = GroupBox_InstrumentSelection(tokens_model=tokens_model, parent=self)
        horizontalLayout_top.addWidget(self.groupBox_instrument_selection, 1)

        verticalLayout_progressBar = QtWidgets.QVBoxLayout(self)
        verticalLayout_progressBar.setSpacing(0)
        self.progressBar = MyProgressBarGroupBox(title='ПОЛУЧЕНИЕ ПРОГНОЗОВ', parent=self)
        verticalLayout_progressBar.addWidget(self.progressBar, 0)
        verticalLayout_progressBar.addStretch(1)
        horizontalLayout_top.addLayout(verticalLayout_progressBar, 1)

        verticalLayout_main.addLayout(horizontalLayout_top, 0)

        horizontalLayout_bottom = QtWidgets.QHBoxLayout()
        horizontalLayout_bottom.setSpacing(2)

        self.consensuses_view = MyTableViewGroupBox(title='КОНСЕНСУС-ПРОГНОЗЫ', model=ForecastsPage.ConsensusItemsModel(self), parent=self)
        horizontalLayout_bottom.addWidget(self.consensuses_view, 1)

        self.targets_view = MyTableViewGroupBox(title='ПРОГНОЗЫ', model=ForecastsPage.ConsensusItemsModel(self), parent=self)
        horizontalLayout_bottom.addWidget(self.targets_view, 1)

        verticalLayout_main.addLayout(horizontalLayout_bottom, 1)
