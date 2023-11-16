from datetime import datetime
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtSql import QSqlDatabase, QSqlQuery
from tinkoff.invest import Client, Coupon, RequestError
from Classes import TokenClass, MyDatabase
from LimitClasses import LimitPerMinuteSemaphore
from MyDatabase import MainConnection
from MyDateTime import ifDateTimeIsEmpty, getUtcDateTime
from MyBondClass import MyBondClass
from MyMoneyValue import MyMoneyValue


class CouponsThread(QThread):
    """Поток получения купонов."""
    class DatabaseConnection(MyDatabase):
        CONNECTION_NAME: str = 'InvestmentViewer_CouponsThread'

        def __init__(self):
            super().__init__()  # __init__() MyDatabase.

            """---------Открываем соединение с базой данных---------"""
            db: QSqlDatabase = QSqlDatabase.addDatabase(self.SQLITE_DRIVER, self.CONNECTION_NAME)
            db.setDatabaseName(self.DATABASE_NAME)
            open_flag: bool = db.open()
            assert open_flag and db.isOpen()
            """-----------------------------------------------------"""

            '''---------Включаем использование внешних ключей---------'''
            query = QSqlQuery(db)
            prepare_flag: bool = query.prepare('PRAGMA foreign_keys = ON;')
            assert prepare_flag, query.lastError().text()
            exec_flag: bool = query.exec()
            assert exec_flag, query.lastError().text()
            '''-------------------------------------------------------'''

        @classmethod
        def getDatabase(cls) -> QSqlDatabase:
            return QSqlDatabase.database(cls.CONNECTION_NAME)

        @classmethod
        def removeConnection(cls):
            """Удаляет соединение с базой данных."""
            db: QSqlDatabase = cls.getDatabase()
            db.close()  # Для удаления соединения с базой данных, надо сначала закрыть базу данных.
            db.removeDatabase(cls.CONNECTION_NAME)

        @classmethod
        def setCoupons(cls, figi: str, coupons: list[Coupon]):
            """Обновляет купоны с переданным figi в таблице купонов."""
            db: QSqlDatabase = cls.getDatabase()
            if coupons:  # Если список купонов не пуст.
                coupons_count: int = len(coupons)  # Количество купонов.
                assert [coupon.figi for coupon in coupons].count(figi) == coupons_count, 'Список купонов должен содержать один и тот же figi ({0})!'.format(figi)

                transaction_flag: bool = db.transaction()  # Начинает транзакцию в базе данных.
                assert transaction_flag, db.lastError().text()

                if transaction_flag:
                    '''---Удаляет из таблицы купонов все купоны, имеющие переданный figi---'''
                    delete_coupons_query = QSqlQuery(db)
                    delete_coupons_query.prepare('DELETE FROM Coupons WHERE figi = :figi;')
                    delete_coupons_query.bindValue(':figi', figi)
                    delete_coupons_exec_flag: bool = delete_coupons_query.exec()
                    assert delete_coupons_exec_flag, delete_coupons_query.lastError().text()
                    '''--------------------------------------------------------------------'''

                    '''---------------------------Добавляет купоны в таблицу купонов---------------------------'''
                    add_coupons_query = QSqlQuery(db)
                    sql_command: str = 'INSERT INTO Coupons (' \
                                       'figi, coupon_date, coupon_number, fix_date, pay_one_bond, coupon_type, ' \
                                       'coupon_start_date, coupon_end_date, coupon_period' \
                                       ') VALUES '
                    for i in range(coupons_count):
                        if i > 0: sql_command += ', '  # Если добавляемый купон не первый.
                        sql_command += '(' \
                                       ':figi{0}, :coupon_date{0}, :coupon_number{0}, :fix_date{0}, ' \
                                       ':pay_one_bond{0}, :coupon_type{0}, :coupon_start_date{0}, ' \
                                       ':coupon_end_date{0}, :coupon_period{0}' \
                                       ')'.format(i)

                    prepare_flag: bool = add_coupons_query.prepare(sql_command)
                    assert prepare_flag, add_coupons_query.lastError().text()

                    for i, coupon in enumerate(coupons):
                        add_coupons_query.bindValue(':figi{0}'.format(i), coupon.figi)
                        add_coupons_query.bindValue(':coupon_date{0}'.format(i), MainConnection.convertDateTimeToText(coupon.coupon_date))
                        add_coupons_query.bindValue(':coupon_number{0}'.format(i), coupon.coupon_number)
                        add_coupons_query.bindValue(':fix_date{0}'.format(i), MainConnection.convertDateTimeToText(coupon.fix_date))
                        add_coupons_query.bindValue(':pay_one_bond{0}'.format(i), MyMoneyValue.__repr__(coupon.pay_one_bond))
                        add_coupons_query.bindValue(':coupon_type{0}'.format(i), int(coupon.coupon_type))
                        add_coupons_query.bindValue(':coupon_start_date{0}'.format(i), MainConnection.convertDateTimeToText(coupon.coupon_start_date))
                        add_coupons_query.bindValue(':coupon_end_date{0}'.format(i), MainConnection.convertDateTimeToText(coupon.coupon_end_date))
                        add_coupons_query.bindValue(':coupon_period{0}'.format(i), coupon.coupon_period)

                    add_coupons_exec_flag: bool = add_coupons_query.exec()
                    assert add_coupons_exec_flag, add_coupons_query.lastError().text()
                    '''----------------------------------------------------------------------------------------'''

                    '''---------------Добавляем информацию к облигации---------------'''
                    query = QSqlQuery(db)
                    query.prepare('UPDATE Bonds SET coupons = :coupons WHERE figi = :coupon_figi;')
                    query.bindValue(':coupons', 'Yes')
                    query.bindValue(':coupon_figi', figi)
                    exec_flag: bool = query.exec()
                    assert exec_flag, query.lastError().text()
                    '''--------------------------------------------------------------'''

                    commit_flag: bool = db.commit()  # Фиксирует транзакцию в базу данных.
                    assert commit_flag
            else:
                '''---------------Добавляем информацию к облигации---------------'''
                query = QSqlQuery(db)
                query.prepare('UPDATE Bonds SET coupons = :coupons WHERE figi = :coupon_figi;')
                query.bindValue(':coupons', 'No')
                query.bindValue(':coupon_figi', figi)
                exec_flag: bool = query.exec()
                assert exec_flag, query.lastError().text()
                '''--------------------------------------------------------------'''

    receive_coupons_method_name: str = 'GetBondCoupons'

    """------------------------Сигналы------------------------"""
    printText_signal: pyqtSignal = pyqtSignal(str)  # Сигнал для отображения сообщений в консоли.
    """-------------------------------------------------------"""

    """-----------------Сигналы progressBar'а-----------------"""
    # Сигнал для установления минимума и максимума progressBar'а заполнения купонов.
    setProgressBarRange_signal: pyqtSignal = pyqtSignal(int, int)
    setProgressBarValue_signal: pyqtSignal = pyqtSignal(int)  # Сигнал для изменения прогресса в progressBar'е.
    """-------------------------------------------------------"""

    """---------------------Сигналы ошибок---------------------"""
    showRequestError_signal: pyqtSignal = pyqtSignal(str, RequestError)  # Сигнал для отображения исключения RequestError.
    showException_signal: pyqtSignal = pyqtSignal(str, Exception)  # Сигнал для отображения исключения.
    clearStatusBar_signal: pyqtSignal = pyqtSignal()  # Сигнал выключения отображения ошибки.
    """--------------------------------------------------------"""

    releaseSemaphore_signal: pyqtSignal = pyqtSignal(LimitPerMinuteSemaphore, int)  # Сигнал для освобождения ресурсов семафора из основного потока.

    def __init__(self, token_class: TokenClass, bond_class_list: list[MyBondClass]):
        super().__init__()  # __init__() QThread.
        self.token: TokenClass = token_class
        self.semaphore: LimitPerMinuteSemaphore | None = self.token.unary_limits_manager.getSemaphore(self.receive_coupons_method_name)
        self.bonds: list[MyBondClass] = bond_class_list

        """------------Статистические переменные------------"""
        self.request_count: int = 0  # Общее количество запросов.
        self.exception_count: int = 0  # Количество исключений.
        self.request_error_count: int = 0  # Количество RequestError.
        self.control_point: datetime | None = None  # Начальная точка отсчёта времени.
        """-------------------------------------------------"""

    def run(self) -> None:
        def printInConsole(text: str):
            self.printText_signal.emit('{0}: {1}'.format(CouponsThread.__name__, text))

        def ifFirstIteration() -> bool:
            """Возвращает True, если поток не сделал ни одного запроса. Иначе возвращает False."""
            return self.request_count > 0

        bonds_count: int = len(self.bonds)  # Количество облигаций.
        self.setProgressBarRange_signal.emit(0, bonds_count)  # Задаёт минимум и максимум progressBar'а заполнения купонов.

        if self.semaphore is None:
            printInConsole('Лимит для метода {0} не найден.'.format(self.receive_coupons_method_name))
        else:
            self.DatabaseConnection()  # Открываем соединение с БД.

            # bonds_count: int = len(self.bonds)  # Количество облигаций.
            # self.setProgressBarRange_signal.emit(0, bonds_count)  # Задаёт минимум и максимум progressBar'а заполнения купонов.
            for i, bond_class in enumerate(self.bonds):
                if self.isInterruptionRequested():
                    printInConsole('Поток прерван.')
                    break

                bond_number: int = i + 1  # Номер текущей облигации.
                self.setProgressBarValue_signal.emit(bond_number)  # Отображаем прогресс в progressBar.

                '------------Выбор временного интервала------------'
                qdt_from: datetime = bond_class.bond.state_reg_date
                qdt_to: datetime = getUtcDateTime() if ifDateTimeIsEmpty(bond_class.bond.maturity_date) else bond_class.bond.maturity_date
                '--------------------------------------------------'

                exception_flag = True  # Индикатор наличия исключения.
                while exception_flag:
                    if self.isInterruptionRequested():
                        printInConsole('Поток прерван.')
                        break

                    """---------------------------Выполнение запроса---------------------------"""
                    self.semaphore.acquire(1)  # Блокирует вызов до тех пор, пока не будет доступно достаточно ресурсов.

                    """----------------Подсчёт статистических параметров----------------"""
                    if ifFirstIteration():  # Не выполняется до второго запроса.
                        delta: float = (getUtcDateTime() - self.control_point).total_seconds()  # Секунд прошло с последнего запроса.
                        printInConsole('{0} из {1} ({2:.2f}с)'.format(bond_number, bonds_count, delta))
                    else:
                        printInConsole('{0} из {1}'.format(bond_number, bonds_count))
                    self.control_point = getUtcDateTime()  # Промежуточная точка отсчёта времени.
                    """-----------------------------------------------------------------"""

                    with Client(self.token.token) as client:
                        try:
                            coupons: list[Coupon] = client.instruments.get_bond_coupons(figi=bond_class.bond.figi, from_=qdt_from, to=qdt_to).events
                        except RequestError as error:
                            self.request_error_count += 1  # Количество RequestError.
                            self.showRequestError_signal.emit('{0} ({1})'.format('get_bond_coupons()', CouponsThread.__name__), error)
                        except Exception as error:
                            self.exception_count += 1  # Количество исключений.
                            self.showException_signal.emit('{0} ({1})'.format('get_bond_coupons()', CouponsThread.__name__), error)
                        else:  # Если исключения не было.
                            exception_flag = False
                            self.clearStatusBar_signal.emit()
                        finally:  # Выполняется в любом случае.
                            self.request_count += 1  # Подсчитываем запрос.

                    self.releaseSemaphore_signal.emit(self.semaphore, 1)  # Освобождаем ресурсы семафора из основного потока.
                    """------------------------------------------------------------------------"""
                if exception_flag: break  # Если поток был прерван.
                bond_class.setCoupons(coupons)  # Записываем список купонов в облигацию.
                self.DatabaseConnection.setCoupons(bond_class.bond.figi, coupons)  # Добавляем купоны в таблицу купонов.

            self.DatabaseConnection.removeConnection()  # Удаляет соединение с БД.
