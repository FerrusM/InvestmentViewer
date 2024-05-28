from datetime import datetime, timedelta
from PyQt6 import QtCore, QtWidgets, QtCharts, QtSql
from tinkoff.invest import CandleInterval, HistoricCandle
from Classes import MyConnection
from MyDatabase import MainConnection
from common.datetime_functions import getUtcDateTime, getMoscowDateTime, print_function_runtime
from MyQuotation import MyQuotation


class Candlestick(QtCharts.QCandlestickSet):
    def __init__(self, candle: HistoricCandle, parent: QtCore.QObject | None = None):
        self.__historic_candle: HistoricCandle = candle
        super().__init__(open=MyQuotation.getFloat(candle.open),
                         high=MyQuotation.getFloat(candle.high),
                         low=MyQuotation.getFloat(candle.low),
                         close=MyQuotation.getFloat(candle.close),
                         timestamp=(candle.time.timestamp() * 1000),
                         parent=parent)
        assert self.low() <= self.open() and self.low() <= self.close() and self.low() <= self.high() and self.high() >= self.open() and self.high() >= self.close()

        @QtCore.pyqtSlot(bool)  # Декоратор, который помечает функцию как qt-слот и ускоряет её выполнение.
        def __onHovered(status: bool):
            if status:
                # print('Свеча: {0}'.format(self.__historic_candle.time))
                pass

        self.hovered.connect(__onHovered)

    @property
    def historic_candle(self) -> HistoricCandle:
        return self.__historic_candle


class CandlesChart(QtCharts.QChart):
    __DEFAULT_VALUE_MIN: float = 0.0
    __DEFAULT_VALUE_MAX: float = 1000.0

    class CandlestickSeries(QtCharts.QCandlestickSeries):
        def __init__(self, parent: QtCore.QObject | None = None):
            super().__init__(parent=parent)
            self.setDecreasingColor(QtCore.Qt.GlobalColor.red)
            self.setIncreasingColor(QtCore.Qt.GlobalColor.green)
            self.setBodyOutlineVisible(False)

    def __init__(self, instrument_uid: str | None, interval: CandleInterval, parent: QtWidgets.QGraphicsItem | None = None):
        super().__init__(parent=parent)
        self.setAnimationDuration(0)  # Выключаем анимацию отрисовки свечей.

        '''---------------------------------Настройка---------------------------------'''
        self.setAnimationOptions(QtCharts.QChart.AnimationOption.SeriesAnimations)

        self.setContentsMargins(-10.0, -10.0, -10.0, -10.0)  # Скрываем поля содержимого виджета.
        self.layout().setContentsMargins(0, 0, 0, 0)  # Раздвигаем поля содержимого макета.
        self.legend().hide()  # Скрываем легенду диаграммы.
        '''---------------------------------------------------------------------------'''

        self.__instrument_uid: str | None = instrument_uid
        self.__interval: CandleInterval = interval

        '''---------------------Создание оси абсцисс---------------------'''
        def __createAxisX(min_: datetime, max_: datetime) -> QtCharts.QDateTimeAxis:
            axisX = QtCharts.QDateTimeAxis(parent=self)
            # axisX.setFormat()
            axisX.setRange(min_, max_)
            axisX.setTitleText('Дата и время')
            return axisX

        current_dt: datetime = getUtcDateTime()
        self.__horizontal_axis: QtCharts.QDateTimeAxis = __createAxisX(current_dt - self.__getDefaultInterval(self.__interval), current_dt)
        self.__range_changed_connection: QtCore.QMetaObject.Connection = self.__horizontal_axis.rangeChanged.connect(self.__onRangeChanged)
        '''--------------------------------------------------------------'''

        self.__candlestick_series: CandlesChart.CandlestickSeries = self.CandlestickSeries(self)
        if self.__instrument_uid is not None:
            self.__candlestick_series.append([Candlestick(candle=candle, parent=self) for candle in self.__getCandlesFromDb(self.min_datetime, self.max_datetime)])

        '''---------------------Создание оси ординат---------------------'''
        def __createAxisY(min_: float, max_: float) -> QtCharts.QValueAxis:
            axisY = QtCharts.QValueAxis(parent=self)
            axisY.setRange(min_, max_)
            # axisY.setTickCount(11)
            axisY.setTitleText('Цена')
            return axisY

        self.__vertical_axis: QtCharts.QValueAxis = __createAxisY(self.min_value, self.max_value)
        '''--------------------------------------------------------------'''

        self.addAxis(self.__horizontal_axis, QtCore.Qt.AlignmentFlag.AlignBottom)
        self.addAxis(self.__vertical_axis, QtCore.Qt.AlignmentFlag.AlignLeft)
        self.addSeries(self.__candlestick_series)

        self.__realtime: bool = True

    def addSeries(self, series) -> None:
        self.__candlestick_series = series
        super().addSeries(series)

        attachAxisX_flag: bool = self.__candlestick_series.attachAxis(self.__horizontal_axis)
        assert attachAxisX_flag, 'Не удалось прикрепить ось X к series.'
        attachAxisY_flag: bool = self.__candlestick_series.attachAxis(self.__vertical_axis)
        assert attachAxisY_flag, 'Не удалось прикрепить ось Y к series.'

    def __onRangeChanged(self, mn_dt: QtCore.QDateTime, mx_dt: QtCore.QDateTime):
        self.setDateTimeRange(mn_dt.toPyDateTime(), mx_dt.toPyDateTime())
        # print('range: [{0}, {1}]'.format(mn_dt.toString('dd.MM.yyyy hh:mm:ss.zzz'), mx_dt.toString('dd.MM.yyyy hh:mm:ss.zzz')))

    @print_function_runtime
    def setDateTimeRange(self, min_dt: datetime, max_dt: datetime):
        """Устанавливает новый диапазон дат."""
        self.__updateCandles(min_dt, max_dt)  # Обновляет список свечей в соответствии с текущим диапазоном дат.
        self.__horizontal_axis.rangeChanged.disconnect(self.__range_changed_connection)
        self.__horizontal_axis.setRange(min_dt, max_dt)
        self.__range_changed_connection: QtCore.QMetaObject.Connection = self.__horizontal_axis.rangeChanged.connect(self.__onRangeChanged)
        self.range_value = (self.min_value, self.max_value)

    def __updateCandles(self, min_dt: datetime, max_dt: datetime):
        """Обновляет список свечей в соответствии с текущим диапазоном дат."""
        self.__candlestick_series.clear()
        if self.__instrument_uid is not None:
            self.__candlestick_series.append([Candlestick(candle=candle, parent=self) for candle in self.__getCandlesFromDb(min_dt, max_dt)])

    @property
    def min_datetime(self) -> datetime:
        return self.__horizontal_axis.min().toPyDateTime()

    @property
    def max_datetime(self) -> datetime:
        return self.__horizontal_axis.max().toPyDateTime()

    @staticmethod
    def __getDefaultInterval(interval: CandleInterval) -> timedelta:
        """Возвращает временной интервал, отображаемый на графике."""
        minute_td: timedelta = timedelta(hours=1, minutes=45)
        day_td: timedelta = timedelta(days=45)

        match interval:
            case CandleInterval.CANDLE_INTERVAL_UNSPECIFIED:
                return day_td
            case CandleInterval.CANDLE_INTERVAL_1_MIN:
                return minute_td
            case CandleInterval.CANDLE_INTERVAL_5_MIN:
                return minute_td * 5
            case CandleInterval.CANDLE_INTERVAL_15_MIN:
                return minute_td * 15
            case CandleInterval.CANDLE_INTERVAL_HOUR:
                return minute_td * 60
            case CandleInterval.CANDLE_INTERVAL_DAY:
                return day_td
            case CandleInterval.CANDLE_INTERVAL_2_MIN:
                return minute_td * 2
            case CandleInterval.CANDLE_INTERVAL_3_MIN:
                return minute_td * 3
            case CandleInterval.CANDLE_INTERVAL_10_MIN:
                return minute_td * 10
            case CandleInterval.CANDLE_INTERVAL_30_MIN:
                return minute_td * 30
            case CandleInterval.CANDLE_INTERVAL_2_HOUR:
                return minute_td * 120
            case CandleInterval.CANDLE_INTERVAL_4_HOUR:
                return minute_td * 240
            case CandleInterval.CANDLE_INTERVAL_WEEK:
                return day_td * 7
            case CandleInterval.CANDLE_INTERVAL_MONTH:
                return day_td * 31
            case _:
                raise ValueError('Некорректный временной интервал свечей!')

    @property
    def min_value(self) -> float:
        if self.__candlestick_series is None:
            return self.__DEFAULT_VALUE_MIN
        else:
            return min([candlestick.low() for candlestick in self.__candlestick_series.sets()], default=self.__DEFAULT_VALUE_MIN)

    @property
    def max_value(self) -> float:
        if self.__candlestick_series is None:
            return self.__DEFAULT_VALUE_MAX
        else:
            return max([candlestick.high() for candlestick in self.__candlestick_series.sets()], default=self.__DEFAULT_VALUE_MAX)

    @property
    def range_value(self) -> tuple[float, float]:
        return self.min_value, self.max_value

    @range_value.setter
    def range_value(self, range_: tuple[float, float]):
        self.__vertical_axis.setRange(range_[0], range_[1])

    def __getCandlesFromDb(self, min_dt: datetime, max_dt: datetime) -> list[HistoricCandle]:
        """
        Извлекает и возвращает свечи из БД, находящиеся в заданном временном интервале.
        Входные параметры должны быть во временном поясе МСК (+3:00).
        """
        db: QtSql.QSqlDatabase = MainConnection.getDatabase()
        if db.transaction():
            select_candles_command: str = '''SELECT \"instrument_id\", \"interval\", \"open\", \"high\", \"low\", 
            \"close\", \"volume\", \"time\", \"is_complete\" FROM \"{0}\" WHERE \"instrument_id\" = :instrument_id AND 
            \"interval\" = :interval AND DATETIME(\"time\") >= DATETIME(:min_dt) AND DATETIME(\"time\") <= 
            DATETIME(:max_dt);'''.format(MyConnection.CANDLES_TABLE)

            query = QtSql.QSqlQuery(db)
            query.setForwardOnly(True)  # Возможно, это ускоряет извлечение данных.
            prepare_flag: bool = query.prepare(select_candles_command)
            assert prepare_flag, query.lastError().text()
            query.bindValue(':instrument_id', self.__instrument_uid)
            query.bindValue(':interval', self.__interval.name)
            query.bindValue(':min_dt', MyConnection.convertDateTimeToText(min_dt - timedelta(hours=3)))
            query.bindValue(':max_dt', MyConnection.convertDateTimeToText(max_dt - timedelta(hours=3)))
            exec_flag: bool = query.exec()
            assert exec_flag, query.lastError().text()

            candles: list[HistoricCandle] = []
            while query.next():
                candles.append(MyConnection.getHistoricCandle(query))

            commit_flag: bool = db.commit()  # Фиксирует транзакцию в базу данных.
            assert commit_flag, db.lastError().text()

            return candles
        else:
            raise SystemError('Не получилось начать транзакцию! db.lastError().text(): \'{0}\'.'.format(db.lastError().text()))

    def setInstrument(self, instrument_uid: str | None):
        self.__instrument_uid = instrument_uid
        self.__updateCandles(self.min_datetime, self.max_datetime)  # Обновляет список свечей в соответствии с текущим диапазоном дат.
        self.range_value = (self.min_value, self.max_value)

    def setInterval(self, interval: CandleInterval):
        self.__interval = interval
        current_dt: datetime = getMoscowDateTime()
        self.setDateTimeRange(current_dt - self.__getDefaultInterval(self.__interval), current_dt)
