from PyQt6 import QtWidgets, QtCore
from DatabaseWidgets import GroupBox_InstrumentSelection
from PagesClasses import TitleWithCount
from TokenModel import TokenListModel


class MyTableViewGroupBox(QtWidgets.QGroupBox):
    def __init__(self, model, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)

        verticalLayout_main = QtWidgets.QVBoxLayout(self)
        verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        verticalLayout_main.setSpacing(2)

        '''------------------------------Заголовок------------------------------'''
        self.title_widget = TitleWithCount(title='ПРОГНОЗЫ', count_text='0', parent=self)
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

        self.view_panel = MyTableViewGroupBox(model=ForecastsPage.ConsensusItemsModel(self), parent=self)
        verticalLayout_main.addWidget(self.view_panel, 1)
