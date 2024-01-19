from datetime import datetime, timedelta
from PyQt6 import QtCharts, QtWidgets, QtCore, QtGui
from tinkoff.invest import HistoricCandle, CandleInterval
from MyDateTime import getMoscowDateTime
from MyQuotation import MyQuotation


def getQCandlestickSetFromHistoricCandle(candle: HistoricCandle, parent: QtCore.QObject | None = None) -> QtCharts.QCandlestickSet:
    return QtCharts.QCandlestickSet(open=MyQuotation.getFloat(candle.open),
                                    high=MyQuotation.getFloat(candle.high),
                                    low=MyQuotation.getFloat(candle.low),
                                    close=MyQuotation.getFloat(candle.close),
                                    timestamp=(candle.time.timestamp() * 1000),
                                    parent=parent)


class CandlesChartView(QtCharts.QChartView):
    class CandlestickSeries(QtCharts.QCandlestickSeries):
        def __init__(self, parent: QtCore.QObject | None = None):
            super().__init__(parent=parent)
            self.setDecreasingColor(QtCore.Qt.GlobalColor.red)
            self.setIncreasingColor(QtCore.Qt.GlobalColor.green)

    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)

        self.max_data: datetime
        self.min_data: datetime

        self.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)  # Указываем, что движок должен сглаживать края примитивов, если это возможно.

        chart = QtCharts.QChart()
        chart.setAnimationOptions(QtCharts.QChart.AnimationOption.SeriesAnimations)

        chart.setContentsMargins(-10.0, -10.0, -10.0, -10.0)  # Скрываем поля содержимого виджета.
        chart.layout().setContentsMargins(0, 0, 0, 0)  # Раздвигаем поля содержимого макета.
        chart.legend().hide()  # Скрываем легенду диаграммы.

        self.setChart(chart)

        self.setCandles([], CandleInterval.CANDLE_INTERVAL_UNSPECIFIED)

    @staticmethod
    def __createAxisX(parent: QtCore.QObject | None, min_: QtCore.QDateTime | datetime, max_: QtCore.QDateTime | datetime) -> QtCharts.QDateTimeAxis:
        axisX = QtCharts.QDateTimeAxis(parent=parent)
        # axisX.setFormat()
        axisX.setRange(min_, max_)
        axisX.setTitleText('Дата и время')
        return axisX

    @staticmethod
    def __createAxisY(parent: QtCore.QObject | None = None, min_: float = 0, max_: float = 110) -> QtCharts.QValueAxis:
        axisY = QtCharts.QValueAxis(parent=parent)
        axisY.setRange(min_, max_)
        # axisY.setTickCount(11)
        axisY.setTitleText('Цена')
        return axisY

    def removeAxes(self):
        """Удаляет оси chart()."""
        '''-------------------------Удаляем имеющиеся оси-------------------------'''
        for axis in self.chart().axes(QtCore.Qt.Orientation.Vertical, None):
            self.chart().removeAxis(axis)
        for axis in self.chart().axes(QtCore.Qt.Orientation.Horizontal, None):
            self.chart().removeAxis(axis)
        '''-----------------------------------------------------------------------'''

    @staticmethod
    def __getInterval(interval: CandleInterval) -> timedelta:
        """Возвращает временной интервал, отображаемый на графике."""
        minute_td: timedelta = timedelta(hours=2)
        day_td: timedelta = timedelta(days=60)

        match interval:
            case CandleInterval.CANDLE_INTERVAL_UNSPECIFIED:
                return day_td
            case CandleInterval.CANDLE_INTERVAL_1_MIN:
                return minute_td
            case CandleInterval.CANDLE_INTERVAL_5_MIN:
                return minute_td*5
            case CandleInterval.CANDLE_INTERVAL_15_MIN:
                return minute_td*15
            case CandleInterval.CANDLE_INTERVAL_HOUR:
                return minute_td*60
            case CandleInterval.CANDLE_INTERVAL_DAY:
                return day_td
            case CandleInterval.CANDLE_INTERVAL_2_MIN:
                return minute_td*2
            case CandleInterval.CANDLE_INTERVAL_3_MIN:
                return minute_td*3
            case CandleInterval.CANDLE_INTERVAL_10_MIN:
                return minute_td*10
            case CandleInterval.CANDLE_INTERVAL_30_MIN:
                return minute_td*30
            case CandleInterval.CANDLE_INTERVAL_2_HOUR:
                return minute_td*120
            case CandleInterval.CANDLE_INTERVAL_4_HOUR:
                return minute_td*240
            case CandleInterval.CANDLE_INTERVAL_WEEK:
                return day_td*7
            case CandleInterval.CANDLE_INTERVAL_MONTH:
                return day_td*31
            case _:
                raise ValueError('Некорректный временной интервал свечей!')

    def setCandles(self, candles: list[HistoricCandle], interval: CandleInterval):
        """Обновляем данные графика."""
        self.chart().removeAllSeries()
        self.removeAxes()  # Удаляет оси chart().
        candlestick_series = self.CandlestickSeries(self)

        self.max_data = getMoscowDateTime()
        self.min_data = self.max_data - self.__getInterval(interval)

        if candles:
            min_timestamp: float = self.min_data.timestamp()
            max_timestamp: float = self.max_data.timestamp()

            for candle in candles:
                assert candle.low <= candle.open and candle.low <= candle.close and candle.low <= candle.high
                assert candle.high >= candle.open and candle.high >= candle.close

                if min_timestamp <= candle.time.timestamp() <= max_timestamp:
                    candlestick = getQCandlestickSetFromHistoricCandle(candle=candle, parent=self)
                    candlestick_series.append(candlestick)

            if candlestick_series.sets():
                '''---Определяем минимальную цену на выбранном отрезке времени---'''
                min_price: float = min(candle.low() for candle in candlestick_series.sets())
                max_price: float = max(candle.high() for candle in candlestick_series.sets())
                '''--------------------------------------------------------------'''
                axisY: QtCharts.QValueAxis = self.__createAxisY(self.chart(), min_price, max_price)
            else:
                axisY: QtCharts.QValueAxis = self.__createAxisY(self.chart())
        else:
            axisY: QtCharts.QValueAxis = self.__createAxisY(self.chart())

        axisX: QtCharts.QDateTimeAxis = self.__createAxisX(self.chart(), self.min_data, self.max_data)
        self.chart().addAxis(axisX, QtCore.Qt.AlignmentFlag.AlignBottom)

        self.chart().addAxis(axisY, QtCore.Qt.AlignmentFlag.AlignLeft)

        self.chart().addSeries(candlestick_series)

        attachAxisX_flag: bool = candlestick_series.attachAxis(axisX)
        assert attachAxisX_flag, 'Не удалось прикрепить ось X к series.'
        attachAxisY_flag: bool = candlestick_series.attachAxis(axisY)
        assert attachAxisY_flag, 'Не удалось прикрепить ось Y к series.'


class CandlesSceneView(QtCharts.QChartView):
    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)
