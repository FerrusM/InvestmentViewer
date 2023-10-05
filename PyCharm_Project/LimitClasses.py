from PyQt6.QtCore import QSemaphore, QTimer, pyqtSignal, pyqtSlot, QObject
from tinkoff.invest import UnaryLimit, StreamLimit


class LimitPerMinuteSemaphore(QObject):
    """Семафор для ограничения количества запросов в минуту."""
    availableChanged_signal: pyqtSignal = pyqtSignal()

    def __init__(self, limit_per_minute: int):
        super().__init__()  # __init__() QObject.
        self._semaphore: QSemaphore = QSemaphore(limit_per_minute)
        self.limit_per_minute: int = limit_per_minute  # Максимальное количество запросов в минуту.
        # self.release_timers: list[QTimer] = []

    # def _getPeriod(self) -> int:
    #     """Определяет минимальный промежуток времени [мс] между запросами."""
    #     return round(60000 / self.limit_per_minute)

    def available(self) -> int:
        """Возвращает количество ресурсов, доступных в данный момент семафору."""
        return self._semaphore.available()

    def acquire(self, n: int = ...) -> None:
        self._semaphore.acquire(n)
        self.availableChanged_signal.emit()

    def release(self, n: int = ...) -> None:
        @pyqtSlot()  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
        def onRelease():
            self._semaphore.release(n)
            # self.release_timers.remove(timer)  # Удаляем отработавший таймер.
            self.availableChanged_signal.emit()

        timer: QTimer = QTimer(self)
        timer.setSingleShot(True)  # Без повторений.
        # self.release_timers.append(timer)  # Запоминаем ссылку на таймер, чтобы он не уничтожился после выполнения функции.
        timer.timeout.connect(onRelease)
        timer.start(60000)  # Запускаем таймер на одну минуту.


class MyMethod:
    """Класс метода."""
    def __init__(self, full_method: str):
        self.full_method: str = full_method

        split_method: dict[str: str, str: str, str: str] | None = self.splitFullMethod()
        if split_method is None:
            self.correctness: bool = False
            self.prefix: str = ''
            self.service: str = ''
            self.method_name: str = ''
        else:
            self.correctness: bool = True
            self.prefix: str = split_method['prefix']
            self.service: str = split_method['service']
            self.method_name: str = split_method['method_name']

    def splitFullMethod(self) -> dict[str: str, str: str, str: str] | None:
        """Разделяет строку на префикс, сервис и имя метода. Шаблон метода выглядит следующим образом:
        prefix + service + '/' + method_name. Префикс должен оканчиваться точкой. Если метод не удаётся разделить, то
        возвращает None. Иначе возвращает словарь {'prefix': prefix, 'service': service, 'method_name': method_name}."""
        last_slash_index: int = self.full_method.rfind('/')  # Порядковый номер последнего символа '/' в полном названии метода.
        if last_slash_index == -1: return None  # Если символ '/' не найден.
        method_name: str = self.full_method[(last_slash_index + 1):]
        method_without_name: str = self.full_method[:last_slash_index]
        last_dot_index: int = method_without_name.rfind('.')  # Порядковый номер последнего символа '.'.
        if last_dot_index == -1: return None  # Если символ '.' не найден.
        service: str = method_without_name[(last_dot_index + 1):]  # Сервис.
        prefix: str = method_without_name[:(last_dot_index + 1)]  # Префикс.
        return {'prefix': prefix, 'service': service, 'method_name': method_name}


class MyUnaryLimit:
    """Класс unary-лимита, дополненный семафором."""
    def __init__(self, unary_limit: UnaryLimit):
        # self.unary_limit: UnaryLimit = unary_limit
        self.limit_per_minute: int = unary_limit.limit_per_minute  # Количество unary-запросов в минуту.
        '''---------Получение списка сервисов и имён методов---------'''
        self.methods: list[MyMethod] = []
        for full_method in unary_limit.methods:
            my_method: MyMethod = MyMethod(full_method)
            if not my_method.correctness:
                raise ValueError('Название метода {0} имеет некорректную структуру!'.format(full_method))
            self.methods.append(my_method)
        '''----------------------------------------------------------'''
        self.semaphore: LimitPerMinuteSemaphore = LimitPerMinuteSemaphore(self.limit_per_minute)

    def getFullMethodsNames(self) -> list[str]:
        """Возвращает список полных имён методов."""
        return [my_method.full_method for my_method in self.methods]

    def getShortMethodsNames(self) -> list[str]:
        """Возвращает список кратких имён методов."""
        return [my_method.method_name for my_method in self.methods]

    def getMethodsServices(self) -> list[str]:
        """Возвращает список сервисов методов."""
        return [my_method.service for my_method in self.methods]

    def getMethodsNamesAndServices(self) -> list[tuple[str, str]]:
        """Возвращает список пар (сервис, краткое имя) методов."""
        return [(my_method.method_name, my_method.service) for my_method in self.methods]


class MyStreamLimit:
    """Класс stream-лимита, дополненный семафором."""
    def __init__(self, stream_limit: StreamLimit):
        # self.stream_limit: StreamLimit = stream_limit
        self.limit: int = stream_limit.limit  # Максимальное количество stream-соединений.
        '''---------Получение списка сервисов и имён методов---------'''
        self.methods: list[MyMethod] = []
        for full_method in stream_limit.streams:
            my_method: MyMethod = MyMethod(full_method)
            if not my_method.correctness:
                raise ValueError('Название метода {0} имеет некорректную структуру!'.format(full_method))
            self.methods.append(my_method)
        '''----------------------------------------------------------'''
        self.semaphore: QSemaphore = QSemaphore(self.limit)


class UnaryLimitsManager:
    """Класс для управления лимитами unary-методов."""
    def __init__(self, unary_limits: list[MyUnaryLimit]):
        self.unary_limits: list[MyUnaryLimit] = []  # Массив лимитов пользователя по unary-запросам.
        self.method_repeat_flag: bool = False  # Флаг повтора полных названий методов.
        self.service_and_name_repeat_flag: bool = False  # Флаг повтора сочетаний сервисов и кратких названий методов.
        self.name_repeat_flag: bool = False  # Флаг повтора кратких названий методов.
        self.setData(unary_limits)

    def setData(self, unary_limits: list[MyUnaryLimit]):
        """Задаёт данные."""
        self.unary_limits = unary_limits  # Массив лимитов пользователя по unary-запросам.

        '''
        Наличие повторений внутри списков не проверяется, потому что повторение
        методов внутри одного лимита ни на что не влияет.
        '''
        N: int = len(self.unary_limits)  # Количество ограничений.

        """---------Проверка на отсутствие повторений полных названий методов---------"""
        self.method_repeat_flag = False  # Флаг повтора полных названий методов.
        for i in range(N - 1):
            current_methods_set: set[str] = set(self.unary_limits[i].getFullMethodsNames())
            for j in range(i + 1, N):
                if list(current_methods_set & set(self.unary_limits[j].getFullMethodsNames())):
                    self.method_repeat_flag = True
                    break
            if self.method_repeat_flag:  # Если обнаружено хотя бы одно совпадение.
                break
        """---------------------------------------------------------------------------"""

        """-----Проверка на отсутствие повторений одинаковых сочетаний сервисов и кратких названий методов-----"""
        if self.method_repeat_flag:  # Если было обнаружено совпадение полного названия метода.
            self.service_and_name_repeat_flag = True
        else:
            self.service_and_name_repeat_flag = False  # Флаг повтора сочетаний сервисов и кратких названий методов.
            for i in range(N - 1):
                current_services_and_names_set: set[tuple[str, str]] = set(self.unary_limits[i].getMethodsNamesAndServices())
                for j in range(i + 1, N):
                    if list(current_services_and_names_set & set(self.unary_limits[j].getMethodsNamesAndServices())):
                        self.service_and_name_repeat_flag = True
                        break
                if self.service_and_name_repeat_flag:  # Если обнаружено хотя бы одно совпадение.
                    break
        """----------------------------------------------------------------------------------------------------"""

        """------------Проверка на отсутствие повторений кратких названий методов------------"""
        if self.method_repeat_flag or self.service_and_name_repeat_flag:
            self.name_repeat_flag = True
        else:
            self.name_repeat_flag = False  # Флаг повтора кратких названий методов.
            for i in range(N - 1):
                current_names_set: set[str] = set(self.unary_limits[i].getShortMethodsNames())  # Перечисление.
                for j in range(i + 1, N):
                    if list(current_names_set & set(self.unary_limits[j].getShortMethodsNames())):
                        self.name_repeat_flag = True
                        break
                if self.name_repeat_flag:  # Если обнаружено хотя бы одно совпадение.
                    break
        """----------------------------------------------------------------------------------"""

        if self.method_repeat_flag or self.service_and_name_repeat_flag:
            raise ValueError('Разные ограничения включают один и тот же метод (одинаковое полное название или одинаковое сочетание сервиса и краткого названия метода)!')

    def getMyUnaryLimit(self,  method_name: str, service: str | None = None) -> MyUnaryLimit | None:
        """Находит и возвращает лимит, соответствующий переданным параметрам."""
        if self.method_repeat_flag:
            return None
        elif self.service_and_name_repeat_flag:
            return None
        elif self.name_repeat_flag:
            if service is None:
                return None
            else:
                for my_unary_limit in self.unary_limits:
                    for my_method in my_unary_limit.methods:
                        if my_method.method_name == method_name:
                            if my_method.service == service:
                                return my_unary_limit
        else:
            if service is None:
                for my_unary_limit in self.unary_limits:
                    for my_method in my_unary_limit.methods:
                        if my_method.method_name == method_name:
                            return my_unary_limit
            else:
                for my_unary_limit in self.unary_limits:
                    for my_method in my_unary_limit.methods:
                        if my_method.method_name == method_name:
                            if my_method.service == service:
                                return my_unary_limit
        return None

    def getSemaphore(self, method_name: str, service: str | None = None) -> LimitPerMinuteSemaphore | None:
        """Находит и возвращает семафор, соответствующий переданным параметрам."""
        my_unary_limit: MyUnaryLimit | None = self.getMyUnaryLimit(method_name, service)
        return None if my_unary_limit is None else my_unary_limit.semaphore
