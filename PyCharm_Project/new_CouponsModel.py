from PyQt6.QtCore import QObject
from PyQt6.QtSql import QSqlQueryModel


class CouponsModel(QSqlQueryModel):
    """Модель для отображения купонов облигаций."""
    def __init__(self, parent: QObject | None = ...):
        super().__init__(parent)  # QSqlQueryModel __init__().
        self._figi: str | None = None
        self.setQuery('''
        SELECT "coupon_date", "fix_date", "coupon_number", "coupon_type", "pay_one_bond", "coupon_period", "coupon_start_date", "coupon_end_date" 
        FROM "Coupons" WHERE "figi" = 'BBG0149P1T91';
        ''')

    def setModelData(self, figi: str | None):
        """Задаёт новые данные модели."""
        self.beginResetModel()  # Начинает операцию сброса модели.
        self._figi = figi
        self.endResetModel()  # Завершает операцию сброса модели.
