from PyQt6 import QtWidgets
from Form import InvestmentForm


if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName('InvestmentViewer')
    app.setOrganizationName('Ferrus Company')
    window = InvestmentForm()
    window.show()
    sys.exit(app.exec())
