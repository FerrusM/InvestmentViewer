from PyQt6.QtCore import QObject
from PyQt6.QtSql import QSqlQueryModel, QSqlQuery, QSqlDatabase
from tinkoff.invest import InstrumentStatus
from MyDatabase import MainConnection


class BondsModel(QSqlQueryModel):
    """Модель облигаций."""
    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)  # __init__() QSqlQueryModel.
        self._uid_list: list[str] = []

    # def setModelData(self, uid_list: list[str]):
    #     """Задаёт новые данные модели."""
    #     if uid_list:  # Если список последних цен не пуст.
    #         self.beginResetModel()  # Начинает операцию сброса модели.
    #         self._uid_list = uid_list
    #
    #         '''------------------------Создание запроса к БД------------------------'''
    #         sql_command: str = '''SELECT "figi", "name", "uid" FROM "Bonds" WHERE'''
    #         for i, uid in enumerate(self._uid_list):
    #             if i > 0:
    #                 sql_command += ' OR'
    #             sql_command += ' \"uid\" = \'{0}\''.format(uid)
    #         sql_command += ';'
    #         '''---------------------------------------------------------------------'''
    #
    #         self.setQuery(sql_command)
    #         self.endResetModel()  # Завершает операцию сброса модели.
    #     else:
    #         pass

    def setQueryParameters(self, token: str, instrument_status: InstrumentStatus):
        """Устанавливает параметры запроса к БД."""
        self.beginResetModel()  # Начинает операцию сброса модели.

        '''------------------------Создание запроса к БД------------------------'''
        sql_command: str = '''
        SELECT * FROM "BondsStatus", "Bonds" 
        WHERE "BondsStatus"."token" = :token AND "BondsStatus"."status" = :status AND 
        "BondsStatus"."uid" = "Bonds"."uid";'''

        db: QSqlDatabase = MainConnection.getDatabase()
        query = QSqlQuery(db)
        prepare_flag: bool = query.prepare(sql_command)
        assert prepare_flag, query.lastError().text()

        query.bindValue(':token', token)
        query.bindValue(':status', instrument_status.name)

        exec_flag: bool = query.exec()
        assert exec_flag, query.lastError().text()
        '''---------------------------------------------------------------------'''

        self.setQuery(query)
        self.endResetModel()  # Завершает операцию сброса модели.

    def getUid(self, row: int) -> str | None:
        """Возвращает uid-идентификатор облигации, соответствующей переданному номеру."""
        return self._uid_list[row] if 0 <= row < len(self._uid_list) else None
