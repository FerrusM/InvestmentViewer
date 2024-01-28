from PyQt6 import QtWidgets
from DatabaseWidgets import GroupBox_InstrumentSelection
from TokenModel import TokenListModel


class ForecastsPage(QtWidgets.QWidget):
    """Страница прогнозов."""
    def __init__(self, tokens_model: TokenListModel, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)

        self.verticalLayout_main = QtWidgets.QVBoxLayout(self)
        self.verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        self.verticalLayout_main.setSpacing(2)

        self.groupBox_instrument_selection = GroupBox_InstrumentSelection(tokens_model=tokens_model, parent=parent)

        self.verticalLayout_main.addWidget(self.groupBox_instrument_selection)
