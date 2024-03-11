import enum
from datetime import datetime, date, timezone
from PyQt6 import QtCore, QtWidgets, QtGui
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot
from tinkoff.invest import InstrumentStatus, Share, Bond, LastPrice
from Classes import TokenClass, partition, TITLE_FONT
from MyBondClass import MyBondClass
from MyDatabase import MainConnection
from MyDateTime import getMoscowDateTime, getCountOfDaysBetweenTwoDates
from MyMoneyValue import MyMoneyValue
from MyRequests import MyResponse, getLastPrices, RequestTryClass
from MyShareClass import MyShareClass
from TokenModel import TokenListModel


class TitleLabel(QtWidgets.QLabel):
    """Класс QLabel'а-заголовка."""
    def __init__(self, text: str, parent: QtWidgets.QWidget | None = None):
        super().__init__(text=text, parent=parent)
        self.setFont(TITLE_FONT)
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)


class TitleWithCount(QtWidgets.QHBoxLayout):
    """Виджет, представляющий собой отцентрированный заголовок с QLabel'ом количества чего-либо в правом углу."""
    def __init__(self, title: str, count_text: str = '0', parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self.setSpacing(0)

        self.addSpacing(10)
        self.addStretch(1)
        self.addWidget(TitleLabel(text=title, parent=parent), 0)

        self.__label_count = QtWidgets.QLabel(text=count_text, parent=parent)
        self.__label_count.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.addWidget(self.__label_count, 1)

        self.addSpacing(10)

    def setCount(self, count_text: str | None):
        self.__label_count.setText(count_text)


class GroupBox_InstrumentInfo(QtWidgets.QGroupBox):
    """Панель отображения информации об инструменте."""
    class InstrumentInfoText(QtWidgets.QPlainTextEdit):
        def __init__(self, parent: QtWidgets.QWidget | None = None):
            super().__init__(parent=parent)
            self.setReadOnly(True)
            self.setWordWrapMode(QtGui.QTextOption.WrapMode.NoWrap)

        def __reportShare(self, share: MyShareClass):
            text: str = 'Тип: {0}\nНазвание: {1}\nuid: {2}\nfigi: {3}\nisin: {4}\nПервая минутная свеча: {5}\n' \
                        'Первая дневная свеча: {6}'.format(
                            'Акция',
                            share.share.name,
                            share.share.uid,
                            share.share.figi,
                            share.share.isin,
                            share.share.first_1min_candle_date,
                            share.share.first_1day_candle_date
                        )
            self.setPlainText(text)

        def __reportBond(self, bond: MyBondClass):
            text: str = 'Тип: {0}\nНазвание: {1}\nuid: {2}\nfigi: {3}\nisin: {4}\nПервая минутная свеча: {5}\n' \
                        'Первая дневная свеча: {6}\nАмортизация: {7}\nНоминал: {8}\nПервоначальный номинал: {9}'.format(
                            'Облигация',
                            bond.bond.name,
                            bond.bond.uid,
                            bond.bond.figi,
                            bond.bond.isin,
                            bond.bond.first_1min_candle_date,
                            bond.bond.first_1day_candle_date,
                            bond.bond.amortization_flag,
                            MyMoneyValue.__str__(bond.bond.nominal, delete_decimal_zeros=True),
                            MyMoneyValue.__str__(bond.bond.initial_nominal, delete_decimal_zeros=True)
                        )
            self.setPlainText(text)

        def reset(self):
            self.setPlainText(None)

        def setInstrument(self, instrument: MyBondClass | MyShareClass):
            if isinstance(instrument, MyBondClass):
                self.__reportBond(instrument)
            elif isinstance(instrument, MyShareClass):
                self.__reportShare(instrument)
            else:
                raise TypeError('Некорректный тип параметра!')

    # class Label_InstrumentInfo(QtWidgets.QLabel):
    #     def __init__(self, parent: QtWidgets.QWidget | None = None):
    #         super().__init__(parent=parent)
    #         sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Expanding)
    #         sizePolicy.setHorizontalStretch(0)
    #         sizePolicy.setVerticalStretch(0)
    #         sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
    #         self.setSizePolicy(sizePolicy)
    #         self.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
    #
    #     def setInstrument(self, instrument: MyBondClass | MyShareClass):
    #         if isinstance(instrument, MyBondClass):
    #             self.__reportBond(instrument)
    #         elif isinstance(instrument, MyShareClass):
    #             self.__reportShare(instrument)
    #         else:
    #             raise TypeError('Некорректный тип параметра!')
    #
    #     def reset(self):
    #         self.setText(None)
    #
    #     def __reportBond(self, bond: MyBondClass):
    #         text: str = \
    #             'Тип: {0}\nНазвание: {1}\nuid: {2}\nfigi: {3}\nisin: {4}\nПервая минутная свеча: {5}\n' \
    #             'Первая дневная свеча: {6}\nАмортизация: {7}\nНоминал: {8}\nПервоначальный номинал: {9}'.format(
    #                 'Облигация',
    #                 bond.bond.name,
    #                 bond.bond.uid,
    #                 bond.bond.figi,
    #                 bond.bond.isin,
    #                 bond.bond.first_1min_candle_date,
    #                 bond.bond.first_1day_candle_date,
    #                 bond.bond.amortization_flag,
    #                 MyMoneyValue.__str__(bond.bond.nominal, delete_decimal_zeros=True),
    #                 MyMoneyValue.__str__(bond.bond.initial_nominal, delete_decimal_zeros=True)
    #             )
    #         self.setText(text)
    #
    #     def __reportShare(self, share: MyShareClass):
    #         text: str = 'Тип: {0}\nНазвание: {1}\nuid: {2}\nfigi: {3}\nisin: {4}\nПервая минутная свеча: {5}\nПервая дневная свеча: {6}'.format(
    #             'Акция',
    #             share.share.name,
    #             share.share.uid,
    #             share.share.figi,
    #             share.share.isin,
    #             share.share.first_1min_candle_date,
    #             share.share.first_1day_candle_date
    #         )
    #         self.setText(text)

    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)

        verticalLayout_main = QtWidgets.QVBoxLayout(self)
        verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        verticalLayout_main.setSpacing(2)

        verticalLayout_main.addWidget(TitleLabel(text='ИНФОРМАЦИЯ ОБ ИНСТРУМЕНТЕ', parent=self))

        # self.label_info = self.Label_InstrumentInfo(self)
        self.label_info = self.InstrumentInfoText(parent=self)
        verticalLayout_main.addWidget(self.label_info)

    def setInstrument(self, instrument: MyShareClass | MyBondClass | None = None):
        if instrument is None:
            self.label_info.reset()
        else:
            instrument_type = type(instrument)
            if instrument_type is MyShareClass or instrument_type is MyBondClass:
                self.label_info.setInstrument(instrument)
            else:
                raise TypeError('Некорректный тип инструмента ({0})!'.format(instrument_type))

    def reset(self):
        self.label_info.reset()


class GroupBox_CalculationDate(QtWidgets.QGroupBox):
    """GroupBox с датой расчёта."""
    def __init__(self, object_name: str, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(sizePolicy)
        self.setMinimumSize(QtCore.QSize(0, 234))
        self.setObjectName(object_name)

        verticalLayout_main = QtWidgets.QVBoxLayout(self)
        verticalLayout_main.setContentsMargins(0, 2, 0, 1)
        verticalLayout_main.setSpacing(2)

        '''--------------------------Заголовок "Дата расчёта"--------------------------'''
        self.title_widget = TitleWithCount(title='ДАТА РАСЧЁТА', count_text='0', parent=self)
        verticalLayout_main.addLayout(self.title_widget, 0)
        '''----------------------------------------------------------------------------'''

        """------------------Календарь с выбором даты------------------"""
        self.calendarWidget = QtWidgets.QCalendarWidget(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.calendarWidget.sizePolicy().hasHeightForWidth())
        self.calendarWidget.setSizePolicy(sizePolicy)
        self.calendarWidget.setMinimumSize(QtCore.QSize(320, 190))
        verticalLayout_main.addWidget(self.calendarWidget)
        """------------------------------------------------------------"""

        @pyqtSlot()  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
        def __updateDaysBeforeCount():
            """Обновляет количество дней до даты расчёта."""
            start_date: date = getMoscowDateTime().date()
            end_date: date = self.getDate()
            days_count: int = getCountOfDaysBetweenTwoDates(start_date, end_date)
            self.title_widget.setCount(str(days_count))

        self.calendarWidget.selectionChanged.connect(__updateDaysBeforeCount)

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

    def __init__(self, object_name: str, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)
        self.setObjectName(object_name)

        self.verticalLayout_main = QtWidgets.QVBoxLayout(self)
        self.verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        self.verticalLayout_main.setSpacing(2)

        """------------------------Заголовок------------------------"""
        self.title_widget = TitleWithCount(title='ЗАПРОС', count_text='0', parent=self)
        self.verticalLayout_main.addLayout(self.title_widget, 0)
        """---------------------------------------------------------"""

        """---------------------------Токен---------------------------"""
        horizontalLayout_token = QtWidgets.QHBoxLayout()
        horizontalLayout_token.setSpacing(0)

        self.label_token = QtWidgets.QLabel(self)
        self.label_token.setToolTip('Токен доступа.')
        self.label_token.setText('Токен:')
        horizontalLayout_token.addWidget(self.label_token)

        horizontalLayout_token.addSpacing(4)

        self.comboBox_token = QtWidgets.QComboBox(self)
        self.comboBox_token.addItem('Не выбран')
        horizontalLayout_token.addWidget(self.comboBox_token)

        horizontalLayout_token.addStretch(1)

        self.verticalLayout_main.addLayout(horizontalLayout_token)
        """-----------------------------------------------------------"""

        @pyqtSlot()  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
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
        self.title_widget.setCount(str(count))


class GroupBox_InstrumentsRequest(QtWidgets.QGroupBox):
    """GroupBox с параметрами запроса инструментов."""
    currentTokenChanged: pyqtSignal = pyqtSignal(TokenClass, InstrumentStatus)  # Сигнал испускается при изменении текущего токена.
    currentTokenReset: pyqtSignal = pyqtSignal()  # Сигнал испускается при выборе пустого значения.
    currentStatusChanged: pyqtSignal = pyqtSignal(InstrumentStatus)  # Сигнал испускается при изменении текущего статуса инструмента.

    def __init__(self, object_name: str, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)
        self.setObjectName(object_name)

        verticalLayout_main = QtWidgets.QVBoxLayout(self)
        verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        verticalLayout_main.setSpacing(2)

        '''------------------------Заголовок------------------------'''
        self.title_widget = TitleWithCount(title='ЗАПРОС', count_text='0', parent=self)
        verticalLayout_main.addLayout(self.title_widget, 0)
        '''---------------------------------------------------------'''

        '''---------------------------Токен---------------------------'''
        horizontalLayout_token = QtWidgets.QHBoxLayout()
        horizontalLayout_token.setSpacing(0)

        label_token = QtWidgets.QLabel(text='Токен:', parent=self)
        label_token.setToolTip('Токен доступа.')
        horizontalLayout_token.addWidget(label_token, 0)

        horizontalLayout_token.addSpacing(4)

        self.comboBox_token = QtWidgets.QComboBox(self)
        self.comboBox_token.addItem('Не выбран')
        self.comboBox_token.setCurrentIndex(0)
        horizontalLayout_token.addWidget(self.comboBox_token)

        horizontalLayout_token.addStretch(1)

        verticalLayout_main.addLayout(horizontalLayout_token, 0)
        '''-----------------------------------------------------------'''

        '''--------------------------Статус--------------------------'''
        horizontalLayout_status = QtWidgets.QHBoxLayout()
        horizontalLayout_status.setSpacing(0)

        label_status = QtWidgets.QLabel(text='Статус:', parent=self)
        label_status.setToolTip('Статус запрашиваемых инструментов.')
        horizontalLayout_status.addWidget(label_status)

        horizontalLayout_status.addSpacing(4)

        self.comboBox_status = QtWidgets.QComboBox(self)
        self.comboBox_status.addItem('Все')
        self.comboBox_status.addItem('Доступные для торговли')
        self.comboBox_status.addItem('Не определён')
        self.comboBox_status.setCurrentIndex(0)
        horizontalLayout_status.addWidget(self.comboBox_status)

        horizontalLayout_status.addStretch(1)

        verticalLayout_main.addLayout(horizontalLayout_status, 0)
        '''----------------------------------------------------------'''

        verticalLayout_main.addStretch(1)

        @pyqtSlot()  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
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
        self.title_widget.setCount(str(count))


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

    def __init__(self, object_name: str, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)
        self.setTitle('Общие фильтры')
        self.setObjectName(object_name)

        self.verticalLayout_main = QtWidgets.QVBoxLayout(self)
        self.verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        self.verticalLayout_main.setSpacing(2)

        self.gridLayout_main = QtWidgets.QGridLayout()
        self.gridLayout_main.setHorizontalSpacing(7)
        self.gridLayout_main.setVerticalSpacing(2)

        """---------------Возможность торговать инструментом через API---------------"""
        label_api_trade_available_flag = QtWidgets.QLabel(text='Доступ API:', parent=self)
        label_api_trade_available_flag.setToolTip('Параметр указывает на возможность торговать инструментом через API.')
        self.gridLayout_main.addWidget(label_api_trade_available_flag, 0, 0, 1, 1)

        self.comboBox_api_trade_available_flag = QtWidgets.QComboBox(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.comboBox_api_trade_available_flag.sizePolicy().hasHeightForWidth())
        self.comboBox_api_trade_available_flag.setSizePolicy(sizePolicy)
        self.comboBox_api_trade_available_flag.addItems(('Все', 'True', 'False'))
        self.comboBox_api_trade_available_flag.setCurrentIndex(1)
        self.gridLayout_main.addWidget(self.comboBox_api_trade_available_flag, 0, 1, 1, 1)
        """--------------------------------------------------------------------------"""

        """---------------------Признак доступности для ИИС---------------------"""
        label_for_iis_flag = QtWidgets.QLabel(text='Доступ ИИС:', parent=self)
        label_for_iis_flag.setToolTip('Признак доступности для ИИС.')
        self.gridLayout_main.addWidget(label_for_iis_flag, 1, 0, 1, 1)

        self.comboBox_for_iis_flag = QtWidgets.QComboBox(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.comboBox_for_iis_flag.sizePolicy().hasHeightForWidth())
        self.comboBox_for_iis_flag.setSizePolicy(sizePolicy)
        self.comboBox_for_iis_flag.addItems(('Все', 'True', 'False'))
        self.comboBox_for_iis_flag.setCurrentIndex(0)
        self.gridLayout_main.addWidget(self.comboBox_for_iis_flag, 1, 1, 1, 1)
        """---------------------------------------------------------------------"""

        """------Доступность торговли инструментом только для квалифицированных инвесторов------"""
        label_for_qual_investor_flag = QtWidgets.QLabel(text='Только \"квалы\":', parent=self)
        label_for_qual_investor_flag.setToolTip('Флаг отображающий доступность торговли инструментом только для квалифицированных инвесторов.')
        self.gridLayout_main.addWidget(label_for_qual_investor_flag, 2, 0, 1, 1)

        self.comboBox_for_qual_investor_flag = QtWidgets.QComboBox(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.comboBox_for_qual_investor_flag.sizePolicy().hasHeightForWidth())
        self.comboBox_for_qual_investor_flag.setSizePolicy(sizePolicy)
        self.comboBox_for_qual_investor_flag.addItems(('Все', 'True', 'False'))
        self.comboBox_for_qual_investor_flag.setCurrentIndex(0)
        self.gridLayout_main.addWidget(self.comboBox_for_qual_investor_flag, 2, 1, 1, 1)
        """-------------------------------------------------------------------------------------"""

        """---------------------Флаг достаточной ликвидности---------------------"""
        label_liquidity_flag = QtWidgets.QLabel(text='Ликвидность:', parent=self)
        label_liquidity_flag.setToolTip('Флаг достаточной ликвидности.')
        self.gridLayout_main.addWidget(label_liquidity_flag, 3, 0, 1, 1)

        self.comboBox_liquidity_flag = QtWidgets.QComboBox(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.comboBox_liquidity_flag.sizePolicy().hasHeightForWidth())
        self.comboBox_liquidity_flag.setSizePolicy(sizePolicy)
        self.comboBox_liquidity_flag.addItems(('Все', 'True', 'False'))
        self.comboBox_liquidity_flag.setCurrentIndex(0)
        self.gridLayout_main.addWidget(self.comboBox_liquidity_flag, 3, 1, 1, 1)
        """----------------------------------------------------------------------"""

        """---------------Признак доступности для операций в шорт---------------"""
        label_short_enabled_flag = QtWidgets.QLabel(text='Операции в шорт:', parent=self)
        label_short_enabled_flag.setToolTip('Признак доступности для операций в шорт.')
        self.gridLayout_main.addWidget(label_short_enabled_flag, 4, 0, 1, 1)

        self.comboBox_short_enabled_flag = QtWidgets.QComboBox(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.comboBox_short_enabled_flag.sizePolicy().hasHeightForWidth())
        self.comboBox_short_enabled_flag.setSizePolicy(sizePolicy)
        self.comboBox_short_enabled_flag.addItems(('Все', 'True', 'False'))
        self.comboBox_short_enabled_flag.setCurrentIndex(0)
        self.gridLayout_main.addWidget(self.comboBox_short_enabled_flag, 4, 1, 1, 1)
        """---------------------------------------------------------------------"""

        """------------------------Признак доступности для покупки------------------------"""
        label_buy_available_flag = QtWidgets.QLabel(text='Доступность покупки:', parent=self)
        label_buy_available_flag.setToolTip('Признак доступности для покупки.')
        self.gridLayout_main.addWidget(label_buy_available_flag, 0, 2, 1, 1)

        self.comboBox_buy_available_flag = QtWidgets.QComboBox(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.comboBox_buy_available_flag.sizePolicy().hasHeightForWidth())
        self.comboBox_buy_available_flag.setSizePolicy(sizePolicy)
        self.comboBox_buy_available_flag.addItems(('Все', 'True', 'False'))
        self.comboBox_buy_available_flag.setCurrentIndex(0)
        self.gridLayout_main.addWidget(self.comboBox_buy_available_flag, 0, 3, 1, 1)
        """-------------------------------------------------------------------------------"""

        """------------------------Признак доступности для продажи------------------------"""
        label_sell_available_flag = QtWidgets.QLabel(text='Доступность продажи:', parent=self)
        label_sell_available_flag.setToolTip('Признак доступности для продажи.')
        self.gridLayout_main.addWidget(label_sell_available_flag, 1, 2, 1, 1)

        self.comboBox_sell_available_flag = QtWidgets.QComboBox(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.comboBox_sell_available_flag.sizePolicy().hasHeightForWidth())
        self.comboBox_sell_available_flag.setSizePolicy(sizePolicy)
        self.comboBox_sell_available_flag.addItems(('Все', 'True', 'False'))
        self.comboBox_sell_available_flag.setCurrentIndex(0)
        self.gridLayout_main.addWidget(self.comboBox_sell_available_flag, 1, 3, 1, 1)
        """-------------------------------------------------------------------------------"""

        """------------Доступность торговли инструментом по выходным------------"""
        label_weekend_flag = QtWidgets.QLabel(text='Торговля по выходным:', parent=self)
        label_weekend_flag.setToolTip('Флаг отображающий доступность торговли инструментом по выходным.')
        self.gridLayout_main.addWidget(label_weekend_flag, 2, 2, 1, 1)

        self.comboBox_weekend_flag = QtWidgets.QComboBox(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.comboBox_weekend_flag.sizePolicy().hasHeightForWidth())
        self.comboBox_weekend_flag.setSizePolicy(sizePolicy)
        self.comboBox_weekend_flag.addItems(('Все', 'True', 'False'))
        self.comboBox_weekend_flag.setCurrentIndex(0)
        self.gridLayout_main.addWidget(self.comboBox_weekend_flag, 2, 3, 1, 1)
        """---------------------------------------------------------------------"""

        """------------------Признак внебиржевой ценной бумаги------------------"""
        label_otc_flag = QtWidgets.QLabel(text='Внебиржевая бумага:', parent=self)
        label_otc_flag.setToolTip('Признак внебиржевой ценной бумаги.')
        self.gridLayout_main.addWidget(label_otc_flag, 3, 2, 1, 1)

        self.comboBox_otc_flag = QtWidgets.QComboBox(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.comboBox_otc_flag.sizePolicy().hasHeightForWidth())
        self.comboBox_otc_flag.setSizePolicy(sizePolicy)
        self.comboBox_otc_flag.addItems(('Все', 'True', 'False'))
        self.comboBox_otc_flag.setCurrentIndex(0)
        self.gridLayout_main.addWidget(self.comboBox_otc_flag, 3, 3, 1, 1)
        """---------------------------------------------------------------------"""

        """---------------------Флаг заблокированного ТКС---------------------"""
        label_blocked_tca_flag = QtWidgets.QLabel(text='Заблокированный ТКС:', parent=self)
        label_blocked_tca_flag.setToolTip('Флаг заблокированного ТКС.')
        self.gridLayout_main.addWidget(label_blocked_tca_flag, 4, 2, 1, 1)

        self.comboBox_blocked_tca_flag = QtWidgets.QComboBox(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.comboBox_blocked_tca_flag.sizePolicy().hasHeightForWidth())
        self.comboBox_blocked_tca_flag.setSizePolicy(sizePolicy)
        self.comboBox_blocked_tca_flag.addItems(('Все', 'True', 'False'))
        self.comboBox_blocked_tca_flag.setCurrentIndex(0)
        self.gridLayout_main.addWidget(self.comboBox_blocked_tca_flag, 4, 3, 1, 1)
        """-------------------------------------------------------------------"""

        """----------------------------Валюта----------------------------"""
        label_currency = QtWidgets.QLabel(text='Валюта:', parent=self)
        label_currency.setToolTip('Валюта расчётов.')
        self.gridLayout_main.addWidget(label_currency, 5, 0, 1, 1)

        self.comboBox_currency = QtWidgets.QComboBox(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.comboBox_currency.sizePolicy().hasHeightForWidth())
        self.comboBox_currency.setSizePolicy(sizePolicy)
        self.comboBox_currency.setEditable(True)
        self.comboBox_currency.addItems(('Любая', 'rub', 'Иностранная', 'usd', 'eur', 'Другая', 'Мультивалютная'))
        self.comboBox_currency.setCurrentIndex(1)
        self.gridLayout_main.addWidget(self.comboBox_currency, 5, 1, 1, 3)
        """--------------------------------------------------------------"""

        self.verticalLayout_main.addLayout(self.gridLayout_main)

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


class ProgressBar_DataReceiving(QtWidgets.QProgressBar):
    """ProgressBar для получения данных."""
    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)
        self.setMinimumSize(QtCore.QSize(0, 0))
        self.setStyleSheet('text-align: center;')
        self.setMaximum(0)
        self.setProperty('value', 0)
        self.setTextVisible(True)
        self.setFormat('%p% (%v из %m)')
        self.reset()  # Сбрасывает progressBar.

    def setRange(self, minimum: int, maximum: int):
        """Устанавливает минимум и максимум для progressBar'а. Если максимум равен нулю, то скрывает бегающую полоску."""
        if maximum == 0:
            '''setRange(0, 0) устанавливает неопределённое состояние progressBar'а, чего хотелось бы избежать.'''
            super().setRange(minimum, 100)  # Устанавливает минимум и максимум для progressBar'а.
        else:
            super().setRange(minimum, maximum)  # Устанавливает минимум и максимум для progressBar'а.
        self.setValue(0)
        super().reset()  # Сбрасывает progressBar.

    def reset(self):
        """Сбрасывает progressBar."""
        super().setRange(0, 100)  # Убирает неопределённое состояние progressBar'а.
        super().reset()  # Сбрасывает progressBar.


class MyTableViewGroupBox(QtWidgets.QGroupBox):
    def __init__(self, title: str, model: QtCore.QAbstractItemModel | None = None, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)

        verticalLayout_main = QtWidgets.QVBoxLayout(self)
        verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        verticalLayout_main.setSpacing(2)

        '''------------------------------Заголовок------------------------------'''
        self.__titlebar = TitleWithCount(title=title, count_text='0', parent=self)
        verticalLayout_main.addLayout(self.__titlebar, 0)
        '''---------------------------------------------------------------------'''

        '''------------------------------Отображение------------------------------'''
        self.__tableView = QtWidgets.QTableView(parent=self)
        self.__tableView.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.__tableView.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.__tableView.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.__tableView.setSortingEnabled(True)

        self.__model_reset_connection: QtCore.QMetaObject.Connection = QtCore.QMetaObject.Connection()

        self.setModel(model)  # Подключаем модель к таблице.

        verticalLayout_main.addWidget(self.__tableView, 1)
        '''-----------------------------------------------------------------------'''

    def setModel(self, model: QtCore.QAbstractItemModel | None):
        old_model: QtCore.QAbstractItemModel | None = self.__tableView.model()
        if old_model is not None:
            disconnect_flag: bool = old_model.disconnect(self.__model_reset_connection)
            assert disconnect_flag, 'Не удалось отключить слот!'

        self.__tableView.setModel(model)  # Подключаем модель к таблице.

        if model is not None:
            def __onModelUpdated():
                """Выполняется при изменении модели."""
                self.__titlebar.setCount(str(model.rowCount()))
                self.__tableView.resizeColumnsToContents()  # Авторазмер столбцов под содержимое.

            __onModelUpdated()
            self.__model_reset_connection = model.modelReset.connect(__onModelUpdated)


def zipWithLastPrices3000(token: TokenClass, class_list: list[Share] | list[Bond]) -> list[tuple[Share, LastPrice | None]] | list[tuple[Bond, LastPrice | None]]:
    """Возвращает список пар акций и последних цен или облигаций и последних цен.
    Функция предусматривает ограничение на количество единоразово запрашиваемых последних цен инструментов (до 3000)."""
    class_list_parts: list[list[Share]] | list[list[Bond]] = partition(class_list, 3000)  # quantity of instruments can't be more than 3000
    result_list_parts: list[tuple[Share, LastPrice | None]] | list[tuple[Bond, LastPrice | None]] = []
    for class_list_part in class_list_parts:
        result_list_parts.extend(zipWithLastPrices(token, class_list_part))
    return result_list_parts


def zipWithLastPrices(token: TokenClass, class_list: list[Share] | list[Bond]) -> list[tuple[Share, LastPrice | None]] | list[tuple[Bond, LastPrice | None]]:
    """Возвращает список пар акций и последних цен или облигаций и последних цен."""
    '''
    Если передать в запрос get_last_prices() пустой массив, то метод вернёт цены последних сделок
    всех доступных для торговли инструментов. Поэтому, если список облигаций пуст,
    то следует пропустить запрос цен последних сделок.
    '''
    if class_list:  # Если список не пуст.
        current_try_count: RequestTryClass = RequestTryClass()
        last_prices_response: MyResponse = MyResponse()
        while current_try_count and not last_prices_response.ifDataSuccessfullyReceived():
            last_prices_response = getLastPrices(token.token, [cls.uid for cls in class_list])
            assert last_prices_response.request_occurred, 'Запрос последних цен не был произведён!'
            current_try_count += 1

        if last_prices_response.ifDataSuccessfullyReceived():  # Если список последних цен был получен.
            last_prices: list[LastPrice] = last_prices_response.response_data
            MainConnection.addLastPrices(last_prices)  # Добавляем последние цены в таблицу последних цен.
            zip_list: list[tuple[Share, LastPrice | None]] | list[tuple[Bond, LastPrice | None]] = []
            '''------------------Проверка полученного списка последних цен------------------'''
            last_prices_uid_list: list[str] = [last_price.instrument_uid for last_price in last_prices]
            for cls in class_list:
                uid_count: int = last_prices_uid_list.count(cls.uid)
                if uid_count == 1:
                    last_price_number: int = last_prices_uid_list.index(cls.uid)
                    last_price: LastPrice = last_prices[last_price_number]
                    zip_list.append((cls, last_price))
                elif uid_count > 1:
                    assert False, 'Список последних цен содержит несколько элементов с одним и тем же uid ({0}).'.format(cls.uid)
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
