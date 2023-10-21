from datetime import datetime
from PyQt6.QtCore import QThread, pyqtSignal, QObject
from tinkoff.invest import Asset, AssetFull
from Classes import TokenClass
from LimitClasses import LimitPerMinuteSemaphore
from MyDateTime import getUtcDateTime
from MyRequests import MyResponse, getAssetBy, RequestTryClass


class AssetClass(QObject):
    """Класс, содержащий всю доступную информацию об активе."""
    setAssetFull_signal: pyqtSignal = pyqtSignal()  # Сигнал, испускаемый при изменении информации об активе.

    def __init__(self, asset: Asset):
        super().__init__()  # __init__() QObject.
        self.asset: Asset = asset
        self.full_asset: AssetFull | None = None

    def setAssetFull(self, assetfull: AssetFull):
        """Заполняет информацию об активе."""
        self.full_asset = assetfull
        self.setAssetFull_signal.emit()  # Испускаем сигнал о том, что информация об активе была изменена.


class AssetsThread(QThread):
    """Поток получения полной информации об активах."""
    receive_assetfulls_method_name: str = 'GetAssetBy'

    '''------------------------Сигналы------------------------'''
    printText_signal: pyqtSignal = pyqtSignal(str)  # Сигнал для отображения сообщений в консоли.
    releaseSemaphore_signal: pyqtSignal = pyqtSignal(LimitPerMinuteSemaphore, int)  # Сигнал для освобождения ресурсов семафора из основного потока.
    '''-------------------------------------------------------'''

    '''-----------------Сигналы progressBar'а-----------------'''
    # Сигнал для установления минимума и максимума progressBar'а заполнения купонов.
    setProgressBarRange_signal: pyqtSignal = pyqtSignal(int, int)
    setProgressBarValue_signal: pyqtSignal = pyqtSignal(int)  # Сигнал для изменения прогресса в progressBar'е.
    '''-------------------------------------------------------'''

    def __init__(self, token_class: TokenClass, assets: list[AssetClass]):
        super().__init__()  # __init__() QThread.
        self.token: TokenClass = token_class
        self.semaphore: LimitPerMinuteSemaphore | None = self.token.unary_limits_manager.getSemaphore(self.receive_assetfulls_method_name)
        self.assets: list[AssetClass] = assets

        '''------------Статистические переменные------------'''
        self.request_count: int = 0  # Общее количество запросов.
        self.control_point: datetime | None = None  # Начальная точка отсчёта времени.
        '''-------------------------------------------------'''

    def run(self) -> None:
        def printInConsole(text: str):
            self.printText_signal.emit('{0}: {1}'.format(AssetsThread.__name__, text))

        def ifFirstIteration() -> bool:
            """Возвращает True, если поток не сделал ни одного запроса. Иначе возвращает False."""
            return self.request_count > 0

        if self.semaphore is None:
            printInConsole('Лимит для метода {0} не найден.'.format(self.receive_assetfulls_method_name))
        else:
            assets_count: int = len(self.assets)  # Количество активов.
            self.setProgressBarRange_signal.emit(0, assets_count)  # Задаёт минимум и максимум progressBar'а.

            for i, asset_class in enumerate(self.assets):
                if self.isInterruptionRequested():
                    printInConsole('Поток прерван.')
                    break

                asset_number: int = i + 1  # Номер текущего актива.
                self.setProgressBarValue_signal.emit(asset_number)  # Отображаем прогресс в progressBar.

                assetfull_try_count: RequestTryClass = RequestTryClass()
                assetfull_response: MyResponse = MyResponse()
                while assetfull_try_count and not assetfull_response.ifDataSuccessfullyReceived():
                    if self.isInterruptionRequested():
                        printInConsole('Поток прерван.')
                        break

                    """------------------------------Выполнение запроса------------------------------"""
                    self.semaphore.acquire(1)  # Блокирует вызов до тех пор, пока не будет доступно достаточно ресурсов.

                    '''----------------Подсчёт статистических параметров----------------'''
                    if ifFirstIteration():  # Не выполняется до второго запроса.
                        delta: float = (getUtcDateTime() - self.control_point).total_seconds()  # Секунд прошло с последнего запроса.
                        printInConsole('{0} из {1} ({2:.2f}с)'.format(asset_number, assets_count, delta))
                    else:
                        printInConsole('{0} из {1}'.format(asset_number, assets_count))
                    self.control_point = getUtcDateTime()  # Промежуточная точка отсчёта времени.
                    '''-----------------------------------------------------------------'''

                    assetfull_response = getAssetBy(self.token.token, asset_class.asset.uid)
                    assert assetfull_response.request_occurred, 'Запрос информации об активе не был произведён.'
                    self.request_count += 1  # Подсчитываем запрос.
                    self.releaseSemaphore_signal.emit(self.semaphore, 1)  # Освобождаем ресурсы семафора из основного потока.
                    """------------------------------------------------------------------------------"""
                    assetfull_try_count += 1

                assetfull: AssetFull | None = assetfull_response.response_data.asset if assetfull_response.ifDataSuccessfullyReceived() else None
                if assetfull is None: continue  # Если поток был прерван или если информация не была получена.
                asset_class.setAssetFull(assetfull)  # Записываем информацию об активе в AssetClass.
