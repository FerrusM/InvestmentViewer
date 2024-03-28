from datetime import datetime, timedelta
from PyQt6 import QtCore, QtWidgets, QtCharts, QtSql
from tinkoff.invest import CandleInterval, HistoricCandle
from Classes import MyConnection
from MyDatabase import MainConnection
from MyDateTime import getUtcDateTime, getMoscowDateTime
from MyQuotation import MyQuotation
from PagesClasses import TitleLabel


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

    @property
    def historic_candle(self) -> HistoricCandle:
        return self.__historic_candle


class CandlesChart(QtCharts.QChart):
    class CandlestickSeries(QtCharts.QCandlestickSeries):
        def __init__(self, parent: QtCore.QObject | None = None):
            super().__init__(parent=parent)
            self.setDecreasingColor(QtCore.Qt.GlobalColor.red)
            self.setIncreasingColor(QtCore.Qt.GlobalColor.green)

    def __init__(self, instrument_uid: str | None, interval: CandleInterval, parent: QtWidgets.QGraphicsItem | None = None):
        super().__init__(parent=parent)

        '''---------------------------------Настройка---------------------------------'''
        self.setAnimationOptions(QtCharts.QChart.AnimationOption.SeriesAnimations)

        self.setContentsMargins(-10.0, -10.0, -10.0, -10.0)  # Скрываем поля содержимого виджета.
        self.layout().setContentsMargins(0, 0, 0, 0)  # Раздвигаем поля содержимого макета.
        self.legend().hide()  # Скрываем легенду диаграммы.
        '''---------------------------------------------------------------------------'''

        self.__instrument_uid: str | None = instrument_uid
        self.__interval: CandleInterval = interval
        self.__candlestick_series: CandlesChart.CandlestickSeries | None = None

        self.__max_datetime: datetime = getUtcDateTime()

        self.__update()

    @property
    def max_datetime(self) -> datetime:
        return self.__max_datetime

    @max_datetime.setter
    def max_datetime(self, dt: datetime):
        self.__max_datetime = dt
        self.__update()

    @property
    def current_timedelta(self) -> timedelta:
        def __getInterval(interval: CandleInterval) -> timedelta:
            """Возвращает временной интервал, отображаемый на графике."""
            minute_td: timedelta = timedelta(hours=2)
            day_td: timedelta = timedelta(days=30)

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
        # minute_td: timedelta = timedelta(days=11)
        return __getInterval(interval=self.__interval)

    @property
    def min_datetime(self) -> datetime:
        return self.max_datetime - self.current_timedelta

    @property
    def min_value(self) -> float:
        if self.__candlestick_series is None:
            return 0
        else:
            return min([candlestick.low() for candlestick in self.__candlestick_series.sets()], default=0)

    @property
    def max_value(self) -> float:
        if self.__candlestick_series is None:
            return 110
        else:
            return max([candlestick.high() for candlestick in self.__candlestick_series.sets()], default=110)

    def __getCandlesFromDb(self) -> list[HistoricCandle]:
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
            query.bindValue(':min_dt', MyConnection.convertDateTimeToText(self.min_datetime))
            query.bindValue(':max_dt', MyConnection.convertDateTimeToText(self.max_datetime))
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

    def __createAxisX(self, min_: datetime, max_: datetime) -> QtCharts.QDateTimeAxis:
        axisX = QtCharts.QDateTimeAxis(parent=self)
        # axisX.setFormat()
        axisX.setRange(min_, max_)
        axisX.setTitleText('Дата и время')
        return axisX

    def __createAxisY(self, min_: float = 0, max_: float = 110) -> QtCharts.QValueAxis:
        axisY = QtCharts.QValueAxis(parent=self)
        axisY.setRange(min_, max_)
        # axisY.setTickCount(11)
        axisY.setTitleText('Цена')
        return axisY

    def addSeries(self, series) -> None:
        self.__candlestick_series = series
        super().addSeries(series)

    def removeAllSeries(self) -> None:
        self.__candlestick_series = None
        super().removeAllSeries()

    def __update(self):
        def __removeAllAxes():
            """Удаляет все оси диаграммы."""
            for axis in self.axes(QtCore.Qt.Orientation.Vertical, None):
                self.removeAxis(axis)
            for axis in self.axes(QtCore.Qt.Orientation.Horizontal, None):
                self.removeAxis(axis)

        self.removeAllSeries()
        __removeAllAxes()  # Удаляет все оси диаграммы.

        self.__candlestick_series = self.CandlestickSeries(self)

        if self.__instrument_uid is not None:
            self.__candlestick_series.append([Candlestick(candle=candle, parent=self) for candle in self.__getCandlesFromDb()])

        axisX: QtCharts.QDateTimeAxis = self.__createAxisX(self.min_datetime, self.max_datetime)
        self.addAxis(axisX, QtCore.Qt.AlignmentFlag.AlignBottom)

        axisY: QtCharts.QValueAxis = self.__createAxisY(self.min_value, self.max_value)
        self.addAxis(axisY, QtCore.Qt.AlignmentFlag.AlignLeft)

        self.addSeries(self.__candlestick_series)

        attachAxisX_flag: bool = self.__candlestick_series.attachAxis(axisX)
        assert attachAxisX_flag, 'Не удалось прикрепить ось X к series.'
        attachAxisY_flag: bool = self.__candlestick_series.attachAxis(axisY)
        assert attachAxisY_flag, 'Не удалось прикрепить ось Y к series.'

        # if self.__candlestick_series.sets():
        #     print('Свечи:')
        #     for i, cs in enumerate(self.__candlestick_series.sets()):
        #         hc: HistoricCandle = cs.historic_candle
        #         ts: datetime = datetime.fromtimestamp(cs.timestamp() / 1000)
        #         print('{0}. time={1}, timestamp={2}, low={3}, high={4}'.format(i, hc.time, ts, MyQuotation.__repr__(hc.low), MyQuotation.__repr__(hc.high)))

    def setInstrument(self, instrument_uid: str | None):
        self.__instrument_uid = instrument_uid
        self.max_datetime = getMoscowDateTime()

    def setInterval(self, interval: CandleInterval):
        self.__interval = interval
        self.max_datetime = getMoscowDateTime()


class GroupBox_Chart(QtWidgets.QGroupBox):
    """Панель отображения свечей."""
    def __init__(self, instrument_uid: str | None, interval: CandleInterval, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)
        self.setEnabled(False)

        verticalLayout_main = QtWidgets.QVBoxLayout(self)
        verticalLayout_main.setContentsMargins(2, 2, 2, 2)
        verticalLayout_main.setSpacing(2)

        verticalLayout_main.addWidget(TitleLabel(text='ГРАФИК', parent=self), 0)

        '''---------------------QChartView---------------------'''
        self.chart_view = QtCharts.QChartView(parent=self)
        self.chart_view.setRubberBand(QtCharts.QChartView.RubberBand.RectangleRubberBand)
        self.chart = CandlesChart(instrument_uid=instrument_uid, interval=interval)
        self.chart_view.setChart(self.chart)
        verticalLayout_main.addWidget(self.chart_view, 1)
        '''----------------------------------------------------'''

        self.setEnabled(True)

    def setInstrument(self, instrument_uid: str | None):
        self.chart.setInstrument(instrument_uid)

    def setInterval(self, interval: CandleInterval):
        self.chart.setInterval(interval)
