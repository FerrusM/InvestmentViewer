import enum
from datetime import datetime, date, timezone
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot
from tinkoff.invest import InstrumentStatus, Share, Bond, LastPrice
from Classes import TokenClass
from MyBondClass import MyBondClass
from MyRequests import MyResponse, getLastPrices, RequestTryClass
from TokenModel import TokenListModel


class GroupBox_CalculationDate(QtWidgets.QGroupBox):
    """GroupBox с датой расчёта."""
    def __init__(self, object_name: str, parent: QtWidgets.QWidget | None = ...):
        super().__init__(parent)  # QGroupBox __init__().

        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(sizePolicy)
        self.setMinimumSize(QtCore.QSize(0, 234))
        self.setTitle('')
        self.setObjectName(object_name)

        self.verticalLayout_main = QtWidgets.QVBoxLayout(self)
        self.verticalLayout_main.setContentsMargins(0, 2, 0, 1)
        self.verticalLayout_main.setSpacing(2)
        self.verticalLayout_main.setObjectName('verticalLayout_main')

        """-----------------Заголовок "Дата расчёта"-----------------"""
        self.label_title = QtWidgets.QLabel(self)
        font = QtGui.QFont()
        font.setBold(True)
        self.label_title.setFont(font)
        self.label_title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.label_title.setObjectName('label_title')
        self.label_title.setText(QtCore.QCoreApplication.translate('MainWindow', 'ДАТА РАСЧЁТА'))
        self.verticalLayout_main.addWidget(self.label_title)
        """----------------------------------------------------------"""

        """------------------Календарь с выбором даты------------------"""
        self.calendarWidget = QtWidgets.QCalendarWidget(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.calendarWidget.sizePolicy().hasHeightForWidth())
        self.calendarWidget.setSizePolicy(sizePolicy)
        self.calendarWidget.setMinimumSize(QtCore.QSize(320, 190))
        self.calendarWidget.setObjectName('calendarWidget')
        self.verticalLayout_main.addWidget(self.calendarWidget)
        """------------------------------------------------------------"""

    def getDate(self) -> date:
        """Возвращает выбранную в календаре дату в формате datetime.date."""
        return self.calendarWidget.selectedDate().toPyDate()

    def getDateTime(self) -> datetime:
        """Возвращает выбранную в календаре дату в формате datetime.datetime."""
        def convertDateToDateTime(entered_date: date) -> datetime:
            """Конвертирует дату в дату и время в UTC."""
            # return datetime(entered_date.year, entered_date.month, entered_date.day).replace(tzinfo=timezone.utc)
            return datetime(entered_date.year, entered_date.month, entered_date.day, tzinfo=timezone.utc)

        return convertDateToDateTime(self.getDate())


class GroupBox_Request(QtWidgets.QGroupBox):
    """GroupBox с параметрами запроса."""
    currentTokenChanged: pyqtSignal = pyqtSignal(TokenClass)  # Сигнал испускается при изменении текущего токена.
    currentTokenReset: pyqtSignal = pyqtSignal()  # Сигнал испускается при выборе пустого значения.

    def __init__(self, object_name: str, parent: QtWidgets.QWidget | None = ...):
        super().__init__(parent)  # QGroupBox __init__().
        self.setTitle('')
        self.setObjectName(object_name)

        self.verticalLayout_main = QtWidgets.QVBoxLayout(self)
        self.verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        self.verticalLayout_main.setSpacing(2)
        self.verticalLayout_main.setObjectName('verticalLayout_main')

        """------------------------Заголовок------------------------"""
        self.horizontalLayout_title = QtWidgets.QHBoxLayout()
        self.horizontalLayout_title.setSpacing(0)
        self.horizontalLayout_title.setObjectName('horizontalLayout_title')

        spacerItem = QtWidgets.QSpacerItem(10, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_title.addItem(spacerItem)

        spacerItem1 = QtWidgets.QSpacerItem(0, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_title.addItem(spacerItem1)

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

        spacerItem2 = QtWidgets.QSpacerItem(10, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_title.addItem(spacerItem2)

        self.verticalLayout_main.addLayout(self.horizontalLayout_title)
        """---------------------------------------------------------"""

        """---------------------------Токен---------------------------"""
        self.horizontalLayout_token = QtWidgets.QHBoxLayout()
        self.horizontalLayout_token.setSpacing(0)
        self.horizontalLayout_token.setObjectName('horizontalLayout_token')

        self.label_token = QtWidgets.QLabel(self)
        self.label_token.setObjectName('label_token')
        self.horizontalLayout_token.addWidget(self.label_token)

        spacerItem3 = QtWidgets.QSpacerItem(4, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_token.addItem(spacerItem3)

        self.comboBox_token = QtWidgets.QComboBox(self)
        self.comboBox_token.setObjectName('comboBox_token')
        self.comboBox_token.addItem('')
        self.horizontalLayout_token.addWidget(self.comboBox_token)

        spacerItem4 = QtWidgets.QSpacerItem(0, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_token.addItem(spacerItem4)

        self.verticalLayout_main.addLayout(self.horizontalLayout_token)
        """-----------------------------------------------------------"""

        _translate = QtCore.QCoreApplication.translate
        self.label_title.setText(_translate('MainWindow', 'ЗАПРОС'))
        self.label_count.setText(_translate('MainWindow', '0'))
        self.label_token.setToolTip(_translate('MainWindow', 'Токен доступа.'))
        self.label_token.setText(_translate('MainWindow', 'Токен:'))
        self.comboBox_token.setItemText(0, _translate('MainWindow', 'Не выбран'))

        self.comboBox_token.setCurrentIndex(0)

        @pyqtSlot()  # Декоратор, который помечает функцию как qt-слот и ускоряет его выполнение.
        def onTokenChangedSlot():
            current_token: TokenClass | None = self.getCurrentToken()
            self.currentTokenReset.emit() if current_token is None else self.currentTokenChanged.emit(current_token)

        self.comboBox_token.currentIndexChanged.connect(lambda index: onTokenChangedSlot())

    def setTokensModel(self, token_list_model: TokenListModel):
        """Устанавливает модель токенов для ComboBox'а."""
        self.comboBox_token.setModel(token_list_model)

    def getCurrentToken(self) -> TokenClass | None:
        """Возвращает выбранный в ComboBox'е токен."""
        return self.comboBox_token.currentData(role=Qt.ItemDataRole.UserRole)

    def setCount(self, count: int):
        """Устанавливает полученное количество."""
        self.label_count.setText(str(count))


class GroupBox_InstrumentsRequest(QtWidgets.QGroupBox):
    """GroupBox с параметрами запроса инструментов."""
    currentTokenChanged: pyqtSignal = pyqtSignal(TokenClass, InstrumentStatus)  # Сигнал испускается при изменении текущего токена.
    currentTokenReset: pyqtSignal = pyqtSignal()  # Сигнал испускается при выборе пустого значения.
    currentStatusChanged: pyqtSignal = pyqtSignal(InstrumentStatus)  # Сигнал испускается при изменении текущего статуса инструмента.

    def __init__(self, object_name: str, parent: QtWidgets.QWidget | None = ...):
        super().__init__(parent)  # QGroupBox __init__().
        self.setTitle('')
        self.setObjectName(object_name)

        self.verticalLayout_main = QtWidgets.QVBoxLayout(self)
        self.verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        self.verticalLayout_main.setSpacing(2)
        self.verticalLayout_main.setObjectName('verticalLayout_main')

        '''------------------------Заголовок------------------------'''
        self.horizontalLayout_title = QtWidgets.QHBoxLayout()
        self.horizontalLayout_title.setSpacing(0)
        self.horizontalLayout_title.setObjectName('horizontalLayout_title')

        spacerItem = QtWidgets.QSpacerItem(10, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_title.addItem(spacerItem)

        spacerItem1 = QtWidgets.QSpacerItem(0, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_title.addItem(spacerItem1)

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

        spacerItem2 = QtWidgets.QSpacerItem(10, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_title.addItem(spacerItem2)

        self.verticalLayout_main.addLayout(self.horizontalLayout_title)
        '''---------------------------------------------------------'''

        '''---------------------------Токен---------------------------'''
        self.horizontalLayout_token = QtWidgets.QHBoxLayout()
        self.horizontalLayout_token.setSpacing(0)
        self.horizontalLayout_token.setObjectName('horizontalLayout_token')

        self.label_token = QtWidgets.QLabel(self)
        self.label_token.setObjectName('label_token')
        self.horizontalLayout_token.addWidget(self.label_token)

        spacerItem3 = QtWidgets.QSpacerItem(4, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_token.addItem(spacerItem3)

        self.comboBox_token = QtWidgets.QComboBox(self)
        self.comboBox_token.setObjectName('comboBox_token')
        self.comboBox_token.addItem('')
        self.horizontalLayout_token.addWidget(self.comboBox_token)

        spacerItem4 = QtWidgets.QSpacerItem(0, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_token.addItem(spacerItem4)

        self.verticalLayout_main.addLayout(self.horizontalLayout_token)
        '''-----------------------------------------------------------'''

        '''--------------------------Статус--------------------------'''
        self.horizontalLayout_status = QtWidgets.QHBoxLayout()
        self.horizontalLayout_status.setSpacing(0)
        self.horizontalLayout_status.setObjectName('horizontalLayout_status')

        self.label_status = QtWidgets.QLabel(self)
        self.label_status.setObjectName('label_status')
        self.horizontalLayout_status.addWidget(self.label_status)

        spacerItem13 = QtWidgets.QSpacerItem(4, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_status.addItem(spacerItem13)

        self.comboBox_status = QtWidgets.QComboBox(self)
        self.comboBox_status.setObjectName('shares_comboBox_status')
        self.comboBox_status.addItem('')
        self.comboBox_status.addItem('')
        self.comboBox_status.addItem('')
        self.horizontalLayout_status.addWidget(self.comboBox_status)

        spacerItem14 = QtWidgets.QSpacerItem(0, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_status.addItem(spacerItem14)

        self.verticalLayout_main.addLayout(self.horizontalLayout_status)
        '''----------------------------------------------------------'''

        _translate = QtCore.QCoreApplication.translate
        self.label_title.setText(_translate('MainWindow', 'ЗАПРОС'))
        self.label_count.setText(_translate('MainWindow', '0'))
        self.label_token.setToolTip(_translate('MainWindow', 'Токен доступа.'))
        self.label_token.setText(_translate('MainWindow', 'Токен:'))
        self.comboBox_token.setItemText(0, _translate('MainWindow', 'Не выбран'))

        self.label_status.setToolTip(_translate('MainWindow', 'Статус запрашиваемых инструментов.'))
        self.label_status.setText(_translate('MainWindow', 'Статус:'))
        self.comboBox_status.setItemText(0, _translate('MainWindow', 'Все'))
        self.comboBox_status.setItemText(1, _translate('MainWindow', 'Доступные для торговли'))
        self.comboBox_status.setItemText(2, _translate('MainWindow', 'Не определён'))

        self.comboBox_token.setCurrentIndex(0)

        @pyqtSlot()  # Декоратор, который помечает функцию как qt-слот и ускоряет его выполнение.
        def onTokenChangedSlot():
            current_token: TokenClass | None = self.getCurrentToken()
            self.currentTokenReset.emit() if current_token is None else self.currentTokenChanged.emit(current_token, self.getCurrentStatus())

        self.comboBox_token.currentIndexChanged.connect(lambda index: onTokenChangedSlot())
        self.comboBox_status.currentIndexChanged.connect(lambda index: self.currentStatusChanged.emit(self.getCurrentStatus()))

    def setTokensModel(self, token_list_model: TokenListModel):
        """Устанавливает модель токенов для ComboBox'а."""
        self.comboBox_token.setModel(token_list_model)

    def getCurrentToken(self) -> TokenClass | None:
        """Возвращает выбранный в ComboBox'е токен."""
        return self.comboBox_token.currentData(role=Qt.ItemDataRole.UserRole)

    def getCurrentStatus(self) -> InstrumentStatus:
        """Возвращает выбранный в ComboBox'е статус."""
        def getInstrumentStatus(status: str) -> InstrumentStatus:
            """Конвертирует строку выбранного статуса в InstrumentStatus."""
            match status:
                case 'Не определён': return InstrumentStatus.INSTRUMENT_STATUS_UNSPECIFIED
                case 'Доступные для торговли': return InstrumentStatus.INSTRUMENT_STATUS_BASE
                case 'Все': return InstrumentStatus.INSTRUMENT_STATUS_ALL
                case _: raise ValueError('Некорректное значение статуса запрашиваемых инструментов (акций): {0}!'.format(status))

        combobox_status: str = self.comboBox_status.currentText()  # Текущий статус в ComboBox'е.
        return getInstrumentStatus(combobox_status)

    def setCount(self, count: int):
        """Устанавливает полученное количество."""
        self.label_count.setText(str(count))


# class GroupBox_InstrumentsRequest(GroupBox_Request):
#     """GroupBox с параметрами запроса инструментов."""
#     currentTokenChanged: pyqtSignal = pyqtSignal(TokenClass, InstrumentStatus)  # Сигнал испускается при изменении текущего токена.
#     currentStatusChanged: pyqtSignal = pyqtSignal(InstrumentStatus)  # Сигнал испускается при изменении текущего статуса инструмента.
#
#     def __init__(self, object_name: str, parent: QtWidgets.QWidget | None = ...):
#         super().__init__(object_name, parent)  # GroupBox_Request __init__().
#
#         '''------------------------Статус------------------------'''
#         self.horizontalLayout_status = QtWidgets.QHBoxLayout()
#         self.horizontalLayout_status.setSpacing(0)
#         self.horizontalLayout_status.setObjectName('horizontalLayout_status')
#
#         self.label_status = QtWidgets.QLabel(self)
#         self.label_status.setObjectName('label_status')
#         self.horizontalLayout_status.addWidget(self.label_status)
#
#         spacerItem13 = QtWidgets.QSpacerItem(4, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum)
#         self.horizontalLayout_status.addItem(spacerItem13)
#
#         self.comboBox_status = QtWidgets.QComboBox(self)
#         self.comboBox_status.setObjectName('shares_comboBox_status')
#         self.comboBox_status.addItem('')
#         self.comboBox_status.addItem('')
#         self.comboBox_status.addItem('')
#         self.horizontalLayout_status.addWidget(self.comboBox_status)
#
#         spacerItem14 = QtWidgets.QSpacerItem(0, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
#         self.horizontalLayout_status.addItem(spacerItem14)
#
#         self.verticalLayout_main.addLayout(self.horizontalLayout_status)
#         '''------------------------------------------------------'''
#
#         _translate = QtCore.QCoreApplication.translate
#         self.label_status.setToolTip(_translate('MainWindow', 'Статус запрашиваемых инструментов.'))
#         self.label_status.setText(_translate('MainWindow', 'Статус:'))
#         self.comboBox_status.setItemText(0, _translate('MainWindow', 'Все'))
#         self.comboBox_status.setItemText(1, _translate('MainWindow', 'Доступные для торговли'))
#         self.comboBox_status.setItemText(2, _translate('MainWindow', 'Не определён'))
#
#     def getCurrentStatus(self) -> InstrumentStatus:
#         """Возвращает выбранный в ComboBox'е статус."""
#         def getInstrumentStatus(status: str) -> InstrumentStatus:
#             """Конвертирует строку выбранного статуса в InstrumentStatus."""
#             match status:
#                 case 'Не определён': return InstrumentStatus.INSTRUMENT_STATUS_UNSPECIFIED
#                 case 'Доступные для торговли': return InstrumentStatus.INSTRUMENT_STATUS_BASE
#                 case 'Все': return InstrumentStatus.INSTRUMENT_STATUS_ALL
#                 case _: raise ValueError('Некорректное значение статуса запрашиваемых инструментов (акций): {0}!'.format(status))
#
#         combobox_status: str = self.comboBox_status.currentText()  # Текущий статус в ComboBox'е.
#         return getInstrumentStatus(combobox_status)


def appFilter_Flag(flag: bool, filter: str) -> bool:
    """Проверяет, удовлетворяет ли акция фильтру с возможными значениями "Все", "True" и "False"."""
    match filter:
        case 'True': return flag
        case 'False': return not flag
        case 'Все': return True
        case _: raise ValueError('Некорректное значение фильтра ({0})!'.format(filter))


class GroupBox_InstrumentsFilters(QtWidgets.QGroupBox):
    """GroupBox с фильтрами инструментов."""
    @enum.unique  # Декоратор, требующий, чтобы все элементы имели разные значения.
    class Filters(enum.IntEnum):
        """Перечисление фильтров инструментов."""
        # TRADING_STATUS = 1  # Текущий режим торгов инструмента.
        API_ACCESS = 0  # Доступ API.
        IIS_ACCESS = 1  # Доступ ИИС.
        QUAL_INVESTOR = 2  # Торговля инструментом только для квалифицированных инвесторов.
        LIQUIDITY_FLAG = 3  # Флаг достаточной ликвидности.
        SHORT_ENABLE = 4  # Признак доступности для операций в шорт.
        BUY_AVAILABLE = 5  # Признак доступности для покупки.
        SELL_AVAILABLE = 6  # Признак доступности для продажи.
        WEEKEND_FLAG = 7  # Доступность торговли инструментом по выходным.
        OTC_FLAG = 8  # Признак внебиржевой ценной бумаги.
        BLOCKED_TCA = 9  # Флаг заблокированного ТКС.
        CURRENCY = 10  # Валюта расчётов.

    def __init__(self, object_name: str, parent: QtWidgets.QWidget | None = ...):
        super().__init__(parent)  # QGroupBox __init__().
        self.setObjectName(object_name)

        self.verticalLayout_main = QtWidgets.QVBoxLayout(self)
        self.verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        self.verticalLayout_main.setSpacing(2)
        self.verticalLayout_main.setObjectName('verticalLayout_main')

        self.gridLayout_main = QtWidgets.QGridLayout()
        self.gridLayout_main.setHorizontalSpacing(7)
        self.gridLayout_main.setVerticalSpacing(2)
        self.gridLayout_main.setObjectName('gridLayout_main')

        """---------------Возможность торговать инструментом через API---------------"""
        self.label_api_trade_available_flag = QtWidgets.QLabel(self)
        self.label_api_trade_available_flag.setObjectName('label_api_trade_available_flag')
        self.gridLayout_main.addWidget(self.label_api_trade_available_flag, 0, 0, 1, 1)

        self.comboBox_api_trade_available_flag = QtWidgets.QComboBox(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.comboBox_api_trade_available_flag.sizePolicy().hasHeightForWidth())
        self.comboBox_api_trade_available_flag.setSizePolicy(sizePolicy)
        self.comboBox_api_trade_available_flag.setToolTip('')
        self.comboBox_api_trade_available_flag.setObjectName('shares_comboBox_api')
        self.comboBox_api_trade_available_flag.addItem('')
        self.comboBox_api_trade_available_flag.addItem('')
        self.comboBox_api_trade_available_flag.addItem('')
        self.gridLayout_main.addWidget(self.comboBox_api_trade_available_flag, 0, 1, 1, 1)
        """--------------------------------------------------------------------------"""

        """---------------------Признак доступности для ИИС---------------------"""
        self.label_for_iis_flag = QtWidgets.QLabel(self)
        self.label_for_iis_flag.setObjectName('label_for_iis_flag')
        self.gridLayout_main.addWidget(self.label_for_iis_flag, 1, 0, 1, 1)

        self.comboBox_for_iis_flag = QtWidgets.QComboBox(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.comboBox_for_iis_flag.sizePolicy().hasHeightForWidth())
        self.comboBox_for_iis_flag.setSizePolicy(sizePolicy)
        self.comboBox_for_iis_flag.setObjectName('comboBox_for_iis_flag')
        self.comboBox_for_iis_flag.addItem('')
        self.comboBox_for_iis_flag.addItem('')
        self.comboBox_for_iis_flag.addItem('')
        self.gridLayout_main.addWidget(self.comboBox_for_iis_flag, 1, 1, 1, 1)
        """---------------------------------------------------------------------"""

        """------Доступность торговли инструментом только для квалифицированных инвесторов------"""
        self.label_for_qual_investor_flag = QtWidgets.QLabel(self)
        self.label_for_qual_investor_flag.setObjectName('label_for_qual_investor_flag')
        self.gridLayout_main.addWidget(self.label_for_qual_investor_flag, 2, 0, 1, 1)

        self.comboBox_for_qual_investor_flag = QtWidgets.QComboBox(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.comboBox_for_qual_investor_flag.sizePolicy().hasHeightForWidth())
        self.comboBox_for_qual_investor_flag.setSizePolicy(sizePolicy)
        self.comboBox_for_qual_investor_flag.setObjectName('comboBox_for_qual_investor_flag')
        self.comboBox_for_qual_investor_flag.addItem('')
        self.comboBox_for_qual_investor_flag.addItem('')
        self.comboBox_for_qual_investor_flag.addItem('')
        self.gridLayout_main.addWidget(self.comboBox_for_qual_investor_flag, 2, 1, 1, 1)
        """-------------------------------------------------------------------------------------"""

        """---------------------Флаг достаточной ликвидности---------------------"""
        self.label_liquidity_flag = QtWidgets.QLabel(self)
        self.label_liquidity_flag.setObjectName('label_liquidity_flag')
        self.gridLayout_main.addWidget(self.label_liquidity_flag, 3, 0, 1, 1)

        self.comboBox_liquidity_flag = QtWidgets.QComboBox(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.comboBox_liquidity_flag.sizePolicy().hasHeightForWidth())
        self.comboBox_liquidity_flag.setSizePolicy(sizePolicy)
        self.comboBox_liquidity_flag.setObjectName('comboBox_liquidity_flag')
        self.comboBox_liquidity_flag.addItem('')
        self.comboBox_liquidity_flag.addItem('')
        self.comboBox_liquidity_flag.addItem('')
        self.gridLayout_main.addWidget(self.comboBox_liquidity_flag, 3, 1, 1, 1)
        """----------------------------------------------------------------------"""

        """---------------Признак доступности для операций в шорт---------------"""
        self.label_short_enabled_flag = QtWidgets.QLabel(self)
        self.label_short_enabled_flag.setObjectName('label_short_enabled_flag')
        self.gridLayout_main.addWidget(self.label_short_enabled_flag, 4, 0, 1, 1)

        self.comboBox_short_enabled_flag = QtWidgets.QComboBox(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.comboBox_short_enabled_flag.sizePolicy().hasHeightForWidth())
        self.comboBox_short_enabled_flag.setSizePolicy(sizePolicy)
        self.comboBox_short_enabled_flag.setObjectName('comboBox_short_enabled_flag')
        self.comboBox_short_enabled_flag.addItem('')
        self.comboBox_short_enabled_flag.addItem('')
        self.comboBox_short_enabled_flag.addItem('')
        self.gridLayout_main.addWidget(self.comboBox_short_enabled_flag, 4, 1, 1, 1)
        """---------------------------------------------------------------------"""

        """------------------------Признак доступности для покупки------------------------"""
        self.label_buy_available_flag = QtWidgets.QLabel(self)
        self.label_buy_available_flag.setObjectName('label_buy_available_flag')
        self.gridLayout_main.addWidget(self.label_buy_available_flag, 0, 2, 1, 1)

        self.comboBox_buy_available_flag = QtWidgets.QComboBox(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.comboBox_buy_available_flag.sizePolicy().hasHeightForWidth())
        self.comboBox_buy_available_flag.setSizePolicy(sizePolicy)
        self.comboBox_buy_available_flag.setObjectName('comboBox_buy_available_flag')
        self.comboBox_buy_available_flag.addItem('')
        self.comboBox_buy_available_flag.addItem('')
        self.comboBox_buy_available_flag.addItem('')
        self.gridLayout_main.addWidget(self.comboBox_buy_available_flag, 0, 3, 1, 1)
        """-------------------------------------------------------------------------------"""

        """------------------------Признак доступности для продажи------------------------"""
        self.label_sell_available_flag = QtWidgets.QLabel(self)
        self.label_sell_available_flag.setObjectName('label_sell_available_flag')
        self.gridLayout_main.addWidget(self.label_sell_available_flag, 1, 2, 1, 1)

        self.comboBox_sell_available_flag = QtWidgets.QComboBox(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.comboBox_sell_available_flag.sizePolicy().hasHeightForWidth())
        self.comboBox_sell_available_flag.setSizePolicy(sizePolicy)
        self.comboBox_sell_available_flag.setObjectName('comboBox_sell_available_flag')
        self.comboBox_sell_available_flag.addItem('')
        self.comboBox_sell_available_flag.addItem('')
        self.comboBox_sell_available_flag.addItem('')
        self.gridLayout_main.addWidget(self.comboBox_sell_available_flag, 1, 3, 1, 1)
        """-------------------------------------------------------------------------------"""

        """------------Доступность торговли инструментом по выходным------------"""
        self.label_weekend_flag = QtWidgets.QLabel(self)
        self.label_weekend_flag.setObjectName('label_weekend_flag')
        self.gridLayout_main.addWidget(self.label_weekend_flag, 2, 2, 1, 1)

        self.comboBox_weekend_flag = QtWidgets.QComboBox(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.comboBox_weekend_flag.sizePolicy().hasHeightForWidth())
        self.comboBox_weekend_flag.setSizePolicy(sizePolicy)
        self.comboBox_weekend_flag.setObjectName('comboBox_weekend_flag')
        self.comboBox_weekend_flag.addItem('')
        self.comboBox_weekend_flag.addItem('')
        self.comboBox_weekend_flag.addItem('')
        self.gridLayout_main.addWidget(self.comboBox_weekend_flag, 2, 3, 1, 1)
        """---------------------------------------------------------------------"""

        """------------------Признак внебиржевой ценной бумаги------------------"""
        self.label_otc_flag = QtWidgets.QLabel(self)
        self.label_otc_flag.setObjectName("label_otc_flag")
        self.gridLayout_main.addWidget(self.label_otc_flag, 3, 2, 1, 1)

        self.comboBox_otc_flag = QtWidgets.QComboBox(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.comboBox_otc_flag.sizePolicy().hasHeightForWidth())
        self.comboBox_otc_flag.setSizePolicy(sizePolicy)
        self.comboBox_otc_flag.setObjectName('comboBox_otc_flag')
        self.comboBox_otc_flag.addItem('')
        self.comboBox_otc_flag.addItem('')
        self.comboBox_otc_flag.addItem('')
        self.gridLayout_main.addWidget(self.comboBox_otc_flag, 3, 3, 1, 1)
        """---------------------------------------------------------------------"""

        """---------------------Флаг заблокированного ТКС---------------------"""
        self.label_blocked_tca_flag = QtWidgets.QLabel(self)
        self.label_blocked_tca_flag.setObjectName('label_blocked_tca_flag')
        self.gridLayout_main.addWidget(self.label_blocked_tca_flag, 4, 2, 1, 1)

        self.comboBox_blocked_tca_flag = QtWidgets.QComboBox(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.comboBox_blocked_tca_flag.sizePolicy().hasHeightForWidth())
        self.comboBox_blocked_tca_flag.setSizePolicy(sizePolicy)
        self.comboBox_blocked_tca_flag.setObjectName('comboBox_blocked_tca_flag')
        self.comboBox_blocked_tca_flag.addItem('')
        self.comboBox_blocked_tca_flag.addItem('')
        self.comboBox_blocked_tca_flag.addItem('')
        self.gridLayout_main.addWidget(self.comboBox_blocked_tca_flag, 4, 3, 1, 1)
        """-------------------------------------------------------------------"""

        """----------------------------Валюта----------------------------"""
        self.label_currency = QtWidgets.QLabel(self)
        self.label_currency.setObjectName('label_currency')
        self.gridLayout_main.addWidget(self.label_currency, 5, 0, 1, 1)

        self.comboBox_currency = QtWidgets.QComboBox(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.comboBox_currency.sizePolicy().hasHeightForWidth())
        self.comboBox_currency.setSizePolicy(sizePolicy)
        self.comboBox_currency.setEditable(True)
        self.comboBox_currency.setObjectName('comboBox_currency')
        self.comboBox_currency.addItem('')
        self.comboBox_currency.addItem('')
        self.comboBox_currency.addItem('')
        self.comboBox_currency.addItem('')
        self.comboBox_currency.addItem('')
        self.comboBox_currency.addItem('')
        self.comboBox_currency.addItem('')
        self.gridLayout_main.addWidget(self.comboBox_currency, 5, 1, 1, 3)
        """--------------------------------------------------------------"""

        self.verticalLayout_main.addLayout(self.gridLayout_main)

        """------------------------------------retranslateUi------------------------------------"""
        _translate = QtCore.QCoreApplication.translate
        self.setTitle(_translate('MainWindow', 'Общие фильтры'))
        self.label_sell_available_flag.setToolTip(_translate('MainWindow', 'Признак доступности для продажи.'))
        self.label_sell_available_flag.setText(_translate('MainWindow', 'Доступность продажи:'))
        self.label_otc_flag.setToolTip(_translate('MainWindow', 'Признак внебиржевой ценной бумаги.'))
        self.label_otc_flag.setText(_translate('MainWindow', 'Внебиржевая бумага:'))
        self.comboBox_api_trade_available_flag.setItemText(0, _translate('MainWindow', 'Все'))
        self.comboBox_api_trade_available_flag.setItemText(1, _translate('MainWindow', 'True'))
        self.comboBox_api_trade_available_flag.setItemText(2, _translate('MainWindow', 'False'))
        self.label_weekend_flag.setToolTip(_translate('MainWindow', 'Флаг отображающий доступность торговли инструментом по выходным.'))
        self.label_weekend_flag.setText(_translate('MainWindow', 'Торговля по выходным:'))
        self.label_for_iis_flag.setToolTip(_translate('MainWindow', 'Признак доступности для ИИС.'))
        self.label_for_iis_flag.setText(_translate('MainWindow', 'Доступ ИИС:'))
        self.label_for_qual_investor_flag.setToolTip(_translate('MainWindow', 'Флаг отображающий доступность торговли инструментом только для квалифицированных инвесторов.'))
        self.label_for_qual_investor_flag.setText(_translate('MainWindow', 'Только \"квалы\":'))
        self.comboBox_for_iis_flag.setItemText(0, _translate('MainWindow', 'Все'))
        self.comboBox_for_iis_flag.setItemText(1, _translate('MainWindow', 'True'))
        self.comboBox_for_iis_flag.setItemText(2, _translate('MainWindow', 'False'))
        self.label_blocked_tca_flag.setToolTip(_translate('MainWindow', 'Флаг заблокированного ТКС.'))
        self.label_blocked_tca_flag.setText(_translate('MainWindow', 'Заблокированный ТКС:'))
        self.comboBox_for_qual_investor_flag.setItemText(0, _translate('MainWindow', 'Все'))
        self.comboBox_for_qual_investor_flag.setItemText(1, _translate('MainWindow', 'True'))
        self.comboBox_for_qual_investor_flag.setItemText(2, _translate('MainWindow', 'False'))
        self.comboBox_sell_available_flag.setItemText(0, _translate('MainWindow', 'Все'))
        self.comboBox_sell_available_flag.setItemText(1, _translate('MainWindow', 'True'))
        self.comboBox_sell_available_flag.setItemText(2, _translate('MainWindow', 'False'))
        self.comboBox_liquidity_flag.setItemText(0, _translate('MainWindow', 'Все'))
        self.comboBox_liquidity_flag.setItemText(1, _translate('MainWindow', 'True'))
        self.comboBox_liquidity_flag.setItemText(2, _translate('MainWindow', 'False'))
        self.comboBox_weekend_flag.setItemText(0, _translate('MainWindow', 'Все'))
        self.comboBox_weekend_flag.setItemText(1, _translate('MainWindow', 'True'))
        self.comboBox_weekend_flag.setItemText(2, _translate('MainWindow', 'False'))
        self.comboBox_blocked_tca_flag.setItemText(0, _translate('MainWindow', 'Все'))
        self.comboBox_blocked_tca_flag.setItemText(1, _translate('MainWindow', 'True'))
        self.comboBox_blocked_tca_flag.setItemText(2, _translate('MainWindow', 'False'))
        self.label_buy_available_flag.setToolTip(_translate('MainWindow', 'Признак доступности для покупки.'))
        self.label_buy_available_flag.setText(_translate('MainWindow', 'Доступность покупки:'))
        self.label_short_enabled_flag.setToolTip(_translate('MainWindow', 'Признак доступности для операций в шорт.'))
        self.label_short_enabled_flag.setText(_translate('MainWindow', 'Операции в шорт:'))
        self.label_liquidity_flag.setToolTip(_translate('MainWindow', 'Флаг достаточной ликвидности.'))
        self.label_liquidity_flag.setText(_translate('MainWindow', 'Ликвидность:'))
        self.comboBox_otc_flag.setItemText(0, _translate('MainWindow', 'Все'))
        self.comboBox_otc_flag.setItemText(1, _translate('MainWindow', 'True'))
        self.comboBox_otc_flag.setItemText(2, _translate('MainWindow', 'False'))
        self.comboBox_short_enabled_flag.setItemText(0, _translate('MainWindow', 'Все'))
        self.comboBox_short_enabled_flag.setItemText(1, _translate('MainWindow', 'True'))
        self.comboBox_short_enabled_flag.setItemText(2, _translate('MainWindow', 'False'))
        self.label_api_trade_available_flag.setToolTip(_translate('MainWindow', 'Параметр указывает на возможность торговать инструментом через API.'))
        self.label_api_trade_available_flag.setText(_translate('MainWindow', 'Доступ API:'))
        self.comboBox_buy_available_flag.setItemText(0, _translate('MainWindow', 'Все'))
        self.comboBox_buy_available_flag.setItemText(1, _translate('MainWindow', 'True'))
        self.comboBox_buy_available_flag.setItemText(2, _translate('MainWindow', 'False'))
        self.label_currency.setToolTip(_translate('MainWindow', 'Валюта расчётов.'))
        self.label_currency.setText(_translate('MainWindow', 'Валюта:'))
        self.comboBox_currency.setItemText(0, _translate('MainWindow', 'Любая'))
        self.comboBox_currency.setItemText(1, _translate('MainWindow', 'rub'))
        self.comboBox_currency.setItemText(2, _translate('MainWindow', 'Иностранная'))
        self.comboBox_currency.setItemText(3, _translate('MainWindow', 'usd'))
        self.comboBox_currency.setItemText(4, _translate('MainWindow', 'eur'))
        self.comboBox_currency.setItemText(5, _translate('MainWindow', 'Другая'))
        self.comboBox_currency.setItemText(6, _translate('MainWindow', 'Мультивалютная'))
        """-------------------------------------------------------------------------------------"""

        self.comboBox_api_trade_available_flag.setCurrentIndex(1)
        self.comboBox_for_iis_flag.setCurrentIndex(0)
        self.comboBox_for_qual_investor_flag.setCurrentIndex(0)
        self.comboBox_sell_available_flag.setCurrentIndex(0)
        self.comboBox_liquidity_flag.setCurrentIndex(0)
        self.comboBox_weekend_flag.setCurrentIndex(0)
        self.comboBox_blocked_tca_flag.setCurrentIndex(0)
        self.comboBox_otc_flag.setCurrentIndex(0)
        self.comboBox_short_enabled_flag.setCurrentIndex(0)
        self.comboBox_buy_available_flag.setCurrentIndex(0)
        self.comboBox_currency.setCurrentIndex(1)

        '''---------------------------------Фильтры инструментов---------------------------------'''
        def appFilter_Currency(currency: str, filter: str) -> bool:
            """Проверяет, удовлетворяет ли акция фильтру на валюту."""
            match filter:
                case 'Любая': return True
                case 'Иностранная': return False if currency == 'rub' else True
                case 'Другая': return False if any(currency == current_currency for current_currency in ('rub', 'usd', 'eur')) else True
                case _: return True if currency == filter else False

        self.filters: dict = {
            self.Filters.API_ACCESS:
                lambda instrument: appFilter_Flag(instrument.api_trade_available_flag, self.comboBox_api_trade_available_flag.currentText()),
            self.Filters.IIS_ACCESS:
                lambda instrument: appFilter_Flag(instrument.for_iis_flag, self.comboBox_for_iis_flag.currentText()),
            self.Filters.QUAL_INVESTOR:
                lambda instrument: appFilter_Flag(instrument.for_qual_investor_flag, self.comboBox_for_qual_investor_flag.currentText()),
            self.Filters.LIQUIDITY_FLAG:
                lambda instrument: appFilter_Flag(instrument.liquidity_flag, self.comboBox_liquidity_flag.currentText()),
            self.Filters.SHORT_ENABLE:
                lambda instrument: appFilter_Flag(instrument.short_enabled_flag, self.comboBox_short_enabled_flag.currentText()),
            self.Filters.BUY_AVAILABLE:
                lambda instrument: appFilter_Flag(instrument.buy_available_flag, self.comboBox_buy_available_flag.currentText()),
            self.Filters.SELL_AVAILABLE:
                lambda instrument: appFilter_Flag(instrument.sell_available_flag, self.comboBox_sell_available_flag.currentText()),
            self.Filters.WEEKEND_FLAG:
                lambda instrument: appFilter_Flag(instrument.weekend_flag, self.comboBox_weekend_flag.currentText()),
            self.Filters.OTC_FLAG:
                lambda instrument: appFilter_Flag(instrument.otc_flag, self.comboBox_otc_flag.currentText()),
            self.Filters.BLOCKED_TCA:
                lambda instrument: appFilter_Flag(instrument.blocked_tca_flag, self.comboBox_blocked_tca_flag.currentText()),
            self.Filters.CURRENCY:
                lambda instrument: appFilter_Currency(instrument.currency, self.comboBox_currency.currentText())
        }
        '''--------------------------------------------------------------------------------------'''

    def checkFilters(self, instrument: Share | Bond) -> bool:
        """Проверяет инструмент на соответствие фильтрам."""
        for filter in self.filters.values():
            if not filter(instrument): return False
        return True


def zipWithLastPrices(token: TokenClass, class_list: list[Share] | list[Bond]) -> list[tuple[Share, LastPrice | None]] | list[tuple[Bond, LastPrice | None]]:
    """Возвращает список пар акций и последних цен или облигаций и последних цен."""
    '''
    Если передать в запрос get_last_prices() пустой массив, то метод вернёт цены последних сделок
    всех доступных для торговли инструментов. Поэтому, если список облигаций пуст,
    то следует пропустить запрос цен последних сделок.
    '''
    if class_list:  # Если список отфильтрованных облигаций не пуст.


        current_try_count: RequestTryClass = RequestTryClass()
        last_prices_response: MyResponse = MyResponse()
        while current_try_count and not last_prices_response.ifDataSuccessfullyReceived():
            last_prices_response = getLastPrices(token.token, [cls.figi for cls in class_list])
            assert last_prices_response.request_occurred, 'Запрос последних цен облигаций не был произведён.'
            current_try_count += 1


        # last_prices_response: MyResponse = getLastPrices(token.token, [cls.figi for cls in class_list])
        # assert last_prices_response.request_occurred, 'Запрос последних цен облигаций не был произведён.'


        if last_prices_response.ifDataSuccessfullyReceived():  # Если список последних цен был получен.
            last_prices: list[LastPrice] = last_prices_response.response_data
            zip_list: list[tuple[Share, LastPrice | None]] | list[tuple[Bond, LastPrice | None]] = []
            '''------------------Проверка полученного списка последних цен------------------'''
            last_prices_figi_list: list[str] = [last_price.figi for last_price in last_prices]
            for cls in class_list:
                figi_count: int = last_prices_figi_list.count(cls.figi)
                if figi_count == 1:
                    last_price_number: int = last_prices_figi_list.index(cls.figi)
                    last_price: LastPrice = last_prices[last_price_number]
                    zip_list.append((cls, last_price))
                elif figi_count > 1:
                    assert False, 'Список последних цен содержит несколько элементов с одним и тем же figi ().'.format(cls.figi)
                    pass
                else:
                    '''
                    Если список последних цен не содержит ни одного подходящего элемента,
                    то заполняем поле last_price значением None.
                    '''
                    zip_list.append((cls, None))
            '''-----------------------------------------------------------------------------'''
            return zip_list
        else:
            return [(cls, None) for cls in class_list]
    else:
        return []
