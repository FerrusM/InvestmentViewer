from PyQt6 import QtWidgets, QtCore
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot
from tinkoff.invest import InstrumentType, Asset
from AssetsModel import AssetsTreeModel, AssetClass
from Classes import TokenClass, MyTreeView
from DatabaseWidgets import ComboBox_Token
from MyDatabase import MainConnection
from MyRequests import MyResponse, getAssets, RequestTryClass
from PagesClasses import ProgressBar_DataReceiving, TitleWithCount, TitleLabel
from TokenModel import TokenListModel


class GroupBox_AssetsRequest(QtWidgets.QGroupBox):
    """GroupBox с параметрами запроса активов."""
    currentTokenChanged: pyqtSignal = pyqtSignal(TokenClass, InstrumentType)  # Сигнал испускается при изменении текущего токена.
    currentTokenReset: pyqtSignal = pyqtSignal()  # Сигнал испускается при выборе пустого значения.
    currentStatusChanged: pyqtSignal = pyqtSignal(InstrumentType)  # Сигнал испускается при изменении текущего типа инструмента.

    def __init__(self, tokens_model: TokenListModel, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)

        verticalLayout_main = QtWidgets.QVBoxLayout(self)
        verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        verticalLayout_main.setSpacing(2)

        self.titlebar = TitleWithCount(title='ЗАПРОС', count_text='0', parent=self)
        verticalLayout_main.addLayout(self.titlebar, 0)

        '''---------------------------Токен---------------------------'''
        horizontalLayout_token = QtWidgets.QHBoxLayout()
        horizontalLayout_token.setSpacing(0)

        label_token = QtWidgets.QLabel(text='Токен:', parent=self)
        label_token.setToolTip('Токен доступа.')
        horizontalLayout_token.addWidget(label_token, 0)

        horizontalLayout_token.addSpacing(4)

        self.comboBox_token = ComboBox_Token(token_model=tokens_model, parent=self)
        horizontalLayout_token.addWidget(self.comboBox_token)

        horizontalLayout_token.addStretch(1)

        verticalLayout_main.addLayout(horizontalLayout_token)
        '''-----------------------------------------------------------'''

        '''-----------------------Тип инструмента-----------------------'''
        horizontalLayout_instrument_type = QtWidgets.QHBoxLayout()
        horizontalLayout_instrument_type.setSpacing(0)

        label_instrument_type = QtWidgets.QLabel(text='Тип инструментов:', parent=self)
        label_instrument_type.setToolTip('Тип запрашиваемых инструментов.')
        horizontalLayout_instrument_type.addWidget(label_instrument_type, 0)

        horizontalLayout_instrument_type.addSpacing(4)

        self.comboBox_instrument_type = QtWidgets.QComboBox(parent=self)
        self.comboBox_instrument_type.addItem('Тип инструмента не определён')
        self.comboBox_instrument_type.addItem('Облигация')
        self.comboBox_instrument_type.addItem('Акция')
        self.comboBox_instrument_type.addItem('Валюта')
        self.comboBox_instrument_type.addItem('Exchange-traded fund')
        self.comboBox_instrument_type.addItem('Фьючерс')
        self.comboBox_instrument_type.addItem('Структурная нота')
        self.comboBox_instrument_type.addItem('Опцион')
        self.comboBox_instrument_type.addItem('Clearing certificate')
        horizontalLayout_instrument_type.addWidget(self.comboBox_instrument_type)

        horizontalLayout_instrument_type.addStretch(1)

        verticalLayout_main.addLayout(horizontalLayout_instrument_type)
        '''----------------------------------------------------------'''

        self.comboBox_instrument_type.currentIndexChanged.connect(lambda index: self.currentStatusChanged.emit(self.instrument_type))

        @QtCore.pyqtSlot(TokenClass)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
        def __onTokenSelected(token: TokenClass):
            self.currentTokenChanged.emit(token, self.instrument_type)

        self.comboBox_token.tokenSelected.connect(__onTokenSelected)
        self.comboBox_token.tokenReset.connect(self.currentTokenReset.emit)

    @property
    def token(self) -> TokenClass | None:
        return self.comboBox_token.token

    @property
    def instrument_type(self) -> InstrumentType:
        def getInstrumentType(instrument_type: str) -> InstrumentType:
            """Конвертирует строку выбранного типа инструментов в InstrumentType."""
            match instrument_type:
                case 'Тип инструмента не определён': return InstrumentType.INSTRUMENT_TYPE_UNSPECIFIED
                case 'Облигация': return InstrumentType.INSTRUMENT_TYPE_BOND
                case 'Акция': return InstrumentType.INSTRUMENT_TYPE_SHARE
                case 'Валюта': return InstrumentType.INSTRUMENT_TYPE_CURRENCY
                case 'Exchange-traded fund': return InstrumentType.INSTRUMENT_TYPE_ETF
                case 'Фьючерс': return InstrumentType.INSTRUMENT_TYPE_FUTURES
                case 'Структурная нота': return InstrumentType.INSTRUMENT_TYPE_SP
                case 'Опцион': return InstrumentType.INSTRUMENT_TYPE_OPTION
                case 'Clearing certificate': return InstrumentType.INSTRUMENT_TYPE_CLEARING_CERTIFICATE
                case _:
                    assert False, 'Некорректное значение типа инструментов запрашиваемых активов: {0}!'.format(instrument_type)
                    return InstrumentType.INSTRUMENT_TYPE_UNSPECIFIED
        return getInstrumentType(self.comboBox_instrument_type.currentText())

    def setCount(self, count: int):
        """Устанавливает полученное количество активов."""
        self.titlebar.setCount(str(count))


class GroupBox_AssetFullsReceiving(QtWidgets.QGroupBox):
    """Панель прогресса получения AssetFull'ов."""
    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)

        verticalLayout_main = QtWidgets.QVBoxLayout(self)
        verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        verticalLayout_main.setSpacing(0)

        verticalLayout_main.addWidget(TitleLabel(text='ПОЛУЧЕНИЕ ИНФОРМАЦИИ ОБ АКТИВАХ', parent=self), 0)

        verticalLayout_main.addSpacing(2)

        '''-------------------------ProgressBar-------------------------'''
        self.progressBar_assets = ProgressBar_DataReceiving(parent=self)
        verticalLayout_main.addWidget(self.progressBar_assets, 0)
        '''-------------------------------------------------------------'''

        verticalLayout_main.addStretch(1)

    def setRange(self, minimum: int, maximum: int):
        """Устанавливает минимум и максимум для progressBar'а."""
        self.progressBar_assets.setRange(minimum, maximum)

    def setValue(self, value: int):
        """Изменяет прогресс в progressBar'е"""
        self.progressBar_assets.setValue(value)

    def reset(self):
        """Сбрасывает progressBar."""
        self.progressBar_assets.reset()


class GroupBox_AssetsTreeView(QtWidgets.QGroupBox):
    """Панель отображения активов."""
    def __init__(self, model: AssetsTreeModel, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)
        self.setAutoFillBackground(False)
        self.setFlat(False)
        self.setCheckable(False)

        verticalLayout_main = QtWidgets.QVBoxLayout(self)
        verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        verticalLayout_main.setSpacing(2)

        '''------------------------Заголовок------------------------'''
        horizontalLayout_title = QtWidgets.QHBoxLayout()
        horizontalLayout_title.setSpacing(0)

        horizontalLayout_title.addSpacing(10)

        self.lineEdit_search = QtWidgets.QLineEdit(parent=self)
        self.lineEdit_search.setPlaceholderText('Поиск...')
        horizontalLayout_title.addWidget(self.lineEdit_search, 1)

        horizontalLayout_title.addSpacerItem(QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum))

        horizontalLayout_title.addWidget(TitleLabel(text='АКТИВЫ', parent=self), 0)

        self.label_count = QtWidgets.QLabel(text='0', parent=self)
        self.label_count.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTrailing | Qt.AlignmentFlag.AlignVCenter)
        horizontalLayout_title.addWidget(self.label_count, 2)

        horizontalLayout_title.addSpacing(10)

        horizontalLayout_title.setStretch(2, 1)
        verticalLayout_main.addLayout(horizontalLayout_title, 0)
        '''---------------------------------------------------------'''

        '''-------------------Отображение активов-------------------'''
        self.treeView_assets = MyTreeView(self)
        self.treeView_assets.setModel(model)
        verticalLayout_main.addWidget(self.treeView_assets, 1)
        self.treeView_assets.resizeColumnsToContents()  # Авторазмер всех столбцов под содержимое.
        '''---------------------------------------------------------'''

    def setAssets(self, token: TokenClass, assets: list[AssetClass]):
        """Устанавливает активы для отображения."""
        self.treeView_assets.model().setAssets(token, assets)
        self.treeView_assets.expandAll()  # Разворачивает все элементы.
        self.treeView_assets.resizeColumnsToContents()  # Авторазмер всех столбцов под содержимое.

    def reset(self):
        self.treeView_assets.model().reset()
        self.treeView_assets.resizeColumnsToContents()  # Авторазмер всех столбцов под содержимое.


class AssetsPage(QtWidgets.QWidget):
    """Страница активов."""
    def __init__(self, tokens_model: TokenListModel, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)

        verticalLayout_main = QtWidgets.QVBoxLayout(self)
        verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        verticalLayout_main.setSpacing(2)

        horizontalLayout_top = QtWidgets.QHBoxLayout()
        horizontalLayout_top.setSpacing(2)

        '''------------------Панель выполнения запроса------------------'''
        self.groupBox_request = GroupBox_AssetsRequest(tokens_model=tokens_model, parent=self)
        horizontalLayout_top.addWidget(self.groupBox_request, 0)
        '''-------------------------------------------------------------'''

        verticalLayout_fulls_receiving = QtWidgets.QVBoxLayout()
        verticalLayout_fulls_receiving.setSpacing(0)
        '''------------Панель прогресса получения AssetFull'ов------------'''
        self.groupBox_fulls_receiving = GroupBox_AssetFullsReceiving(self)
        verticalLayout_fulls_receiving.addWidget(self.groupBox_fulls_receiving, 0)
        '''---------------------------------------------------------------'''
        verticalLayout_fulls_receiving.addStretch(1)
        horizontalLayout_top.addLayout(verticalLayout_fulls_receiving, 1)

        verticalLayout_main.addLayout(horizontalLayout_top, 0)

        ''''------------------Панель отображения активов------------------'''
        assets_model = AssetsTreeModel(parent=self)
        assets_model.setProgressBarRange_signal.connect(self.groupBox_fulls_receiving.setRange)
        assets_model.setProgressBarValue_signal.connect(self.groupBox_fulls_receiving.setValue)
        self.groupBox_view = GroupBox_AssetsTreeView(model=assets_model, parent=self)
        verticalLayout_main.addWidget(self.groupBox_view, 1)
        '''--------------------------------------------------------------'''

        self.groupBox_request.currentTokenChanged.connect(self.onTokenChanged)
        self.groupBox_request.currentTokenReset.connect(self.onTokenReset)

    @property
    def token(self) -> TokenClass | None:
        return self.groupBox_request.token

    def __resetData(self):
        self.groupBox_view.reset()
        self.groupBox_request.setCount(0)  # Количество полученных активов.
        self.groupBox_fulls_receiving.reset()  # Сбрасывает progressBar.

    @pyqtSlot()  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
    def onTokenReset(self):
        """Функция, выполняемая при выборе пустого значения вместо токена."""
        self.__resetData()

    @pyqtSlot(TokenClass, InstrumentType)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
    def onTokenChanged(self, token: TokenClass, instruments_type: InstrumentType):
        """Функция, выполняемая при изменении выбранного токена."""
        assets_try_count: RequestTryClass = RequestTryClass(max_request_try_count=2)
        assets_response: MyResponse = MyResponse()
        while assets_try_count and not assets_response.ifDataSuccessfullyReceived():
            assets_response: MyResponse = getAssets(token.token, instruments_type)  # Получение активов.
            assert assets_response.request_occurred, 'Запрос активов не был произведён.'
            assets_try_count += 1

        if assets_response.ifDataSuccessfullyReceived():  # Если список активов был получен.
            assets: list[Asset] = assets_response.response_data  # Извлекаем список активов.
            if assets:
                MainConnection.addAssets(assets)  # Добавляем активы в таблицу активов.

                assets_list: list[AssetClass] = [AssetClass(asset=asset, parent=self) for asset in assets]

                self.groupBox_view.setAssets(token=token, assets=assets_list)  # Передаём в исходную модель данные.
                self.groupBox_request.setCount(len(assets_list))  # Количество полученных активов.
            else:
                self.__resetData()
        else:
            self.__resetData()
