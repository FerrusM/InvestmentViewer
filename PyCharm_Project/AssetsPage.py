from PyQt6 import QtWidgets, QtGui
from PyQt6.QtCore import Qt, pyqtSignal, QCoreApplication, pyqtSlot
from tinkoff.invest import InstrumentType, Asset
from AssetsModel import AssetsTreeModel
from AssetsThread import AssetsThread, AssetClass
from Classes import TokenClass, MyTreeView
from MyDatabase import MainConnection
from MyDateTime import getMoscowDateTime
from MyRequests import MyResponse, getAssets, RequestTryClass
from PagesClasses import ProgressBar_DataReceiving
from TokenModel import TokenListModel


class GroupBox_AssetsRequest(QtWidgets.QGroupBox):
    """GroupBox с параметрами запроса активов."""
    currentTokenChanged: pyqtSignal = pyqtSignal(TokenClass, InstrumentType)  # Сигнал испускается при изменении текущего токена.
    currentTokenReset: pyqtSignal = pyqtSignal()  # Сигнал испускается при выборе пустого значения.
    currentStatusChanged: pyqtSignal = pyqtSignal(InstrumentType)  # Сигнал испускается при изменении текущего типа инструмента.

    def __init__(self, object_name: str, parent: QtWidgets.QWidget | None = ...):
        super().__init__(parent)
        self.setObjectName(object_name)

        self.verticalLayout_main = QtWidgets.QVBoxLayout(self)
        self.verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        self.verticalLayout_main.setSpacing(2)
        self.verticalLayout_main.setObjectName('verticalLayout_main')

        _translate = QCoreApplication.translate

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
        self.label_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_title.setObjectName('label_title')
        self.label_title.setText(_translate('MainWindow', 'ЗАПРОС'))
        self.horizontalLayout_title.addWidget(self.label_title)

        self.label_count = QtWidgets.QLabel(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_count.sizePolicy().hasHeightForWidth())
        self.label_count.setSizePolicy(sizePolicy)
        self.label_count.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTrailing | Qt.AlignmentFlag.AlignVCenter)
        self.label_count.setObjectName('label_count')
        self.label_count.setText(_translate('MainWindow', '0'))
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
        self.label_token.setToolTip(_translate('MainWindow', 'Токен доступа.'))
        self.label_token.setText(_translate('MainWindow', 'Токен:'))
        self.horizontalLayout_token.addWidget(self.label_token)

        self.horizontalLayout_token.addItem(QtWidgets.QSpacerItem(4, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum))

        self.comboBox_token = QtWidgets.QComboBox(self)
        self.comboBox_token.setObjectName('comboBox_token')
        self.horizontalLayout_token.addWidget(self.comboBox_token)

        self.horizontalLayout_token.addItem(QtWidgets.QSpacerItem(0, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum))

        self.verticalLayout_main.addLayout(self.horizontalLayout_token)
        '''-----------------------------------------------------------'''

        '''-----------------------Тип инструмента-----------------------'''
        self.horizontalLayout_instrument_type = QtWidgets.QHBoxLayout()
        self.horizontalLayout_instrument_type.setSpacing(0)
        self.horizontalLayout_instrument_type.setObjectName('horizontalLayout_instrument_type')

        self.label_instrument_type = QtWidgets.QLabel(self)
        self.label_instrument_type.setObjectName('label_instrument_type')
        self.label_instrument_type.setToolTip(_translate('MainWindow', 'Тип запрашиваемых инструментов.'))
        self.label_instrument_type.setText(_translate('MainWindow', 'Тип инструментов:'))
        self.horizontalLayout_instrument_type.addWidget(self.label_instrument_type)

        self.horizontalLayout_instrument_type.addItem(QtWidgets.QSpacerItem(4, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum))

        self.comboBox_instrument_type = QtWidgets.QComboBox(self)
        self.comboBox_instrument_type.setObjectName('comboBox_instrument_type')
        self.comboBox_instrument_type.addItem(_translate('MainWindow', 'Тип инструмента не определён'))
        self.comboBox_instrument_type.addItem(_translate('MainWindow', 'Облигация'))
        self.comboBox_instrument_type.addItem(_translate('MainWindow', 'Акция'))
        self.comboBox_instrument_type.addItem(_translate('MainWindow', 'Валюта'))
        self.comboBox_instrument_type.addItem(_translate('MainWindow', 'Exchange-traded fund'))
        self.comboBox_instrument_type.addItem(_translate('MainWindow', 'Фьючерс'))
        self.comboBox_instrument_type.addItem(_translate('MainWindow', 'Структурная нота'))
        self.comboBox_instrument_type.addItem(_translate('MainWindow', 'Опцион'))
        self.comboBox_instrument_type.addItem(_translate('MainWindow', 'Clearing certificate'))
        self.horizontalLayout_instrument_type.addWidget(self.comboBox_instrument_type)

        self.horizontalLayout_instrument_type.addItem(QtWidgets.QSpacerItem(0, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum))

        self.verticalLayout_main.addLayout(self.horizontalLayout_instrument_type)
        '''----------------------------------------------------------'''

        @pyqtSlot()  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
        def onTokenChangedSlot():
            current_token: TokenClass | None = self.getCurrentToken()
            self.currentTokenReset.emit() if current_token is None else self.currentTokenChanged.emit(current_token, self.getCurrentInstrumentType())

        self.comboBox_token.currentIndexChanged.connect(lambda index: onTokenChangedSlot())
        self.comboBox_instrument_type.currentIndexChanged.connect(lambda index: self.currentStatusChanged.emit(self.getCurrentInstrumentType()))

    def setTokensModel(self, token_list_model: TokenListModel):
        """Устанавливает модель токенов для ComboBox'а."""
        self.comboBox_token.setModel(token_list_model)

    def getCurrentToken(self) -> TokenClass | None:
        """Возвращает выбранный в ComboBox'е токен."""
        return self.comboBox_token.currentData(role=Qt.ItemDataRole.UserRole)

    def getCurrentInstrumentType(self) -> InstrumentType:
        """Возвращает выбранный в ComboBox'е тип инструментов."""
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
        self.label_count.setText(str(count))


class GroupBox_AssetFullsReceiving(QtWidgets.QGroupBox):
    """Панель прогресса получения AssetFull'ов."""
    def __init__(self, object_name: str, parent: QtWidgets.QWidget | None = ...):
        super().__init__(parent)  # QGroupBox __init__().
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(sizePolicy)
        self.setTitle('')
        self.setObjectName(object_name)

        self.verticalLayout_main = QtWidgets.QVBoxLayout(self)
        self.verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        self.verticalLayout_main.setSpacing(2)
        self.verticalLayout_main.setObjectName('verticalLayout_main')

        _translate = QCoreApplication.translate

        self.label_title = QtWidgets.QLabel(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_title.sizePolicy().hasHeightForWidth())
        self.label_title.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setBold(True)
        self.label_title.setFont(font)
        self.label_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_title.setObjectName('label_title')
        self.label_title.setText(_translate('MainWindow', 'ПОЛУЧЕНИЕ ИНФОРМАЦИИ ОБ АКТИВАХ'))
        self.verticalLayout_main.addWidget(self.label_title)

        '''-------------------------ProgressBar-------------------------'''
        self.progressBar_assets = ProgressBar_DataReceiving('progressBar_assets', self)
        self.verticalLayout_main.addWidget(self.progressBar_assets)
        '''-------------------------------------------------------------'''

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

        _translate = QCoreApplication.translate

        '''------------------------Заголовок------------------------'''
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
        self.lineEdit_search.setPlaceholderText(_translate('MainWindow', 'Поиск...'))
        self.horizontalLayout_title.addWidget(self.lineEdit_search)

        spacerItem6 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_title.addItem(spacerItem6)

        self.label_title = QtWidgets.QLabel(self)
        font = QtGui.QFont()
        font.setBold(True)
        self.label_title.setFont(font)
        self.label_title.setObjectName('label_title')
        self.label_title.setText(_translate('MainWindow', 'АКТИВЫ'))
        self.horizontalLayout_title.addWidget(self.label_title)

        self.label_count = QtWidgets.QLabel(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_count.sizePolicy().hasHeightForWidth())
        self.label_count.setSizePolicy(sizePolicy)
        self.label_count.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTrailing | Qt.AlignmentFlag.AlignVCenter)
        self.label_count.setObjectName('label_count')
        self.label_count.setText(_translate('MainWindow', '0'))
        self.horizontalLayout_title.addWidget(self.label_count)

        spacerItem7 = QtWidgets.QSpacerItem(10, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_title.addItem(spacerItem7)

        self.horizontalLayout_title.setStretch(1, 1)
        self.horizontalLayout_title.setStretch(2, 1)
        self.horizontalLayout_title.setStretch(4, 2)
        self.verticalLayout_main.addLayout(self.horizontalLayout_title)
        '''---------------------------------------------------------'''

        '''-------------------Отображение активов-------------------'''
        self.treeView_assets = MyTreeView(self)
        self.treeView_assets.setObjectName('treeView_assets')
        self.verticalLayout_main.addWidget(self.treeView_assets)
        '''---------------------------------------------------------'''

        assets_model: AssetsTreeModel = AssetsTreeModel()
        self.treeView_assets.setModel(assets_model)  # Подключаем модель к TreeView.
        self.treeView_assets.resizeColumnsToContents()  # Авторазмер всех столбцов под содержимое.

    def setAssets(self, assets: list[AssetClass]):
        """Устанавливает активы для отображения."""
        self.treeView_assets.model().setAssets(assets)
        self.treeView_assets.expandAll()  # Разворачивает все элементы.
        self.treeView_assets.resizeColumnsToContents()  # Авторазмер всех столбцов под содержимое.


class AssetsPage(QtWidgets.QWidget):
    """Страница активов."""
    def __init__(self, object_name: str, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)  # QWidget __init__().
        self.setObjectName(object_name)

        self.verticalLayout_main = QtWidgets.QVBoxLayout(self)
        self.verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        self.verticalLayout_main.setSpacing(2)
        self.verticalLayout_main.setObjectName('verticalLayout_main')

        self.horizontalLayout_top = QtWidgets.QHBoxLayout()
        self.horizontalLayout_top.setSpacing(2)
        self.horizontalLayout_top.setObjectName('horizontalLayout_top')

        '''------------------Панель выполнения запроса------------------'''
        self.groupBox_request: GroupBox_AssetsRequest = GroupBox_AssetsRequest('groupBox_request', self)
        self.horizontalLayout_top.addWidget(self.groupBox_request)
        '''-------------------------------------------------------------'''

        self.verticalLayout_fulls_receiving = QtWidgets.QVBoxLayout()
        self.verticalLayout_fulls_receiving.setSpacing(0)
        self.verticalLayout_fulls_receiving.setObjectName('verticalLayout_fulls_receiving')

        '''------------Панель прогресса получения AssetFull'ов------------'''
        self.groupBox_fulls_receiving: GroupBox_AssetFullsReceiving = GroupBox_AssetFullsReceiving('groupBox_fulls_receiving', self)
        self.verticalLayout_fulls_receiving.addWidget(self.groupBox_fulls_receiving)
        '''---------------------------------------------------------------'''

        spacerItem = QtWidgets.QSpacerItem(20, 0, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        self.verticalLayout_fulls_receiving.addItem(spacerItem)

        self.horizontalLayout_top.addLayout(self.verticalLayout_fulls_receiving)
        self.horizontalLayout_top.setStretch(1, 1)
        self.verticalLayout_main.addLayout(self.horizontalLayout_top)

        ''''------------------Панель отображения активов------------------'''
        self.groupBox_view: GroupBox_AssetsTreeView = GroupBox_AssetsTreeView('groupBox_view', self)
        self.verticalLayout_main.addWidget(self.groupBox_view)
        self.verticalLayout_main.setStretch(1, 1)
        '''--------------------------------------------------------------'''

        '''-----------------------------------------------------------'''
        self.__token: TokenClass | None = None
        self.full_assets_thread: AssetsThread | None = None  # Поток получения информации об активах.
        '''-----------------------------------------------------------'''

        self.groupBox_request.currentTokenChanged.connect(self.onTokenChanged)
        self.groupBox_request.currentTokenReset.connect(self.onTokenReset)

    @property
    def token(self) -> TokenClass | None:
        return self.__token

    @token.setter
    def token(self, token: TokenClass | None):
        self.__token = token

    def setTokensModel(self, token_list_model: TokenListModel):
        """Устанавливает модель токенов для ComboBox'а."""
        self.groupBox_request.comboBox_token.setModel(token_list_model)

    @pyqtSlot()  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
    def onTokenReset(self):
        """Функция, выполняемая при выборе пустого значения вместо токена."""
        self._stopAssetsThread()  # Останавливает поток получения информации об активах.
        self.token = None
        self.groupBox_view.setAssets([])  # Передаём в исходную модель данные.
        self.groupBox_request.setCount(0)  # Количество полученных активов.
        self.groupBox_fulls_receiving.reset()  # Сбрасывает progressBar.

    @pyqtSlot(TokenClass, InstrumentType)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
    def onTokenChanged(self, token: TokenClass, instruments_type: InstrumentType):
        """Функция, выполняемая при изменении выбранного токена."""
        self._stopAssetsThread()  # Останавливает поток получения информации об активах.
        self.token = token

        assets_try_count: RequestTryClass = RequestTryClass(2)
        assets_response: MyResponse = MyResponse()
        while assets_try_count and not assets_response.ifDataSuccessfullyReceived():
            assets_response: MyResponse = getAssets(token.token, instruments_type)  # Получение активов.
            assert assets_response.request_occurred, 'Запрос активов не был произведён.'
            assets_try_count += 1

        if assets_response.ifDataSuccessfullyReceived():  # Если список активов был получен.
            assets: list[Asset] = assets_response.response_data  # Извлекаем список активов.
            MainConnection.addAssets(assets)  # Добавляем активы в таблицу активов.

            assetclass_list: list[AssetClass] = [AssetClass(asset) for asset in assets]
            self.groupBox_view.setAssets(assetclass_list)  # Передаём в исходную модель данные.
            self.groupBox_request.setCount(len(assetclass_list))  # Количество полученных активов.
            if assetclass_list:  # Если список не пуст.
                self._startAssetsThread(token, assetclass_list)  # Запускает поток получения информации об активах.
        else:
            self.groupBox_view.setAssets([])  # Передаём в исходную модель данные.
            self.groupBox_request.setCount(0)  # Количество полученных активов.
            self.groupBox_fulls_receiving.reset()  # Сбрасывает progressBar.

    def _startAssetsThread(self, token: TokenClass, asset_class_list: list[AssetClass]):
        """Запускает поток получения информации об активах."""
        assert self.full_assets_thread is None, 'Поток получения информации об активах должен быть завершён!'

        self.full_assets_thread = AssetsThread(token_class=token, assets=asset_class_list)
        '''---------------------Подключаем сигналы потока к слотам---------------------'''
        self.full_assets_thread.printText_signal.connect(print)  # Сигнал для отображения сообщений в консоли.

        self.full_assets_thread.setProgressBarRange_signal.connect(self.groupBox_fulls_receiving.setRange)
        self.full_assets_thread.setProgressBarValue_signal.connect(self.groupBox_fulls_receiving.setValue)

        self.full_assets_thread.assetFullReceived.connect(MainConnection.insertAssetFull)

        self.full_assets_thread.releaseSemaphore_signal.connect(lambda semaphore, n: semaphore.release(n))  # Освобождаем ресурсы семафора из основного потока.

        self.full_assets_thread.started.connect(lambda: print('{0}: Поток запущен. ({1})'.format(AssetsThread.__name__, getMoscowDateTime())))
        self.full_assets_thread.finished.connect(lambda: print('{0}: Поток завершён. ({1})'.format(AssetsThread.__name__, getMoscowDateTime())))
        '''----------------------------------------------------------------------------'''
        self.full_assets_thread.start()  # Запускаем поток.

    def _stopAssetsThread(self):
        """Останавливает поток получения информации об активах."""
        if self.full_assets_thread is not None:  # Если поток был создан.
            self.full_assets_thread.requestInterruption()  # Сообщаем потоку о том, что надо завершиться.
            self.full_assets_thread.wait()  # Ждём завершения потока.
            self.full_assets_thread = None
