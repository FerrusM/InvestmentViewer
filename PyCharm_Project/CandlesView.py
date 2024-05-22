from datetime import datetime, timedelta
from PyQt6 import QtCharts, QtWidgets, QtCore
from tinkoff.invest import HistoricCandle, CandleInterval
from common.datetime_functions import getMoscowDateTime
from MyQuotation import MyQuotation


def getQCandlestickSetFromHistoricCandle(candle: HistoricCandle, parent: QtCore.QObject | None = None) -> QtCharts.QCandlestickSet:
    return QtCharts.QCandlestickSet(open=MyQuotation.getFloat(candle.open),
                                    high=MyQuotation.getFloat(candle.high),
                                    low=MyQuotation.getFloat(candle.low),
                                    close=MyQuotation.getFloat(candle.close),
                                    timestamp=(candle.time.timestamp() * 1000),
                                    parent=parent)


class CandlesChart(QtCharts.QChart):
    class CandlestickSeries(QtCharts.QCandlestickSeries):
        def __init__(self, parent: QtCore.QObject | None = None):
            super().__init__(parent=parent)
            self.setDecreasingColor(QtCore.Qt.GlobalColor.red)
            self.setIncreasingColor(QtCore.Qt.GlobalColor.green)

    def __init__(self, parent: QtWidgets.QGraphicsItem | None = None, interval: CandleInterval = CandleInterval.CANDLE_INTERVAL_UNSPECIFIED):
        super().__init__(parent=parent)

        self.setAnimationOptions(QtCharts.QChart.AnimationOption.SeriesAnimations)

        self.setContentsMargins(-10.0, -10.0, -10.0, -10.0)  # Скрываем поля содержимого виджета.
        self.layout().setContentsMargins(0, 0, 0, 0)  # Раздвигаем поля содержимого макета.
        self.legend().hide()  # Скрываем легенду диаграммы.

        self.max_data = getMoscowDateTime()
        self.min_data = self.max_data - self.__getInterval(interval)

        axisY: QtCharts.QValueAxis = self.__createAxisY()
        self.addAxis(axisY, QtCore.Qt.AlignmentFlag.AlignLeft)

        axisX: QtCharts.QDateTimeAxis = self.__createAxisX(self.min_data, self.max_data)
        self.addAxis(axisX, QtCore.Qt.AlignmentFlag.AlignBottom)

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

    def removeAllAxes(self):
        """Удаляет все оси диаграммы."""
        for axis in self.axes(QtCore.Qt.Orientation.Vertical, None):
            self.removeAxis(axis)
        for axis in self.axes(QtCore.Qt.Orientation.Horizontal, None):
            self.removeAxis(axis)

    def __createAxisX(self, min_: QtCore.QDateTime | datetime, max_: QtCore.QDateTime | datetime) -> QtCharts.QDateTimeAxis:
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

    def setCandles(self, candles: list[HistoricCandle], interval: CandleInterval):
        """Обновляем данные графика."""
        self.removeAllSeries()
        self.removeAllAxes()  # Удаляет все оси диаграммы.

        candlestick_series = self.CandlestickSeries(self)

        self.max_data = getMoscowDateTime()
        self.min_data = self.max_data - self.__getInterval(interval)

        '''==============================Если надо отображать все свечи=============================='''
        # if candles:
        #     min_timestamp: float = self.min_data.timestamp()
        #     max_timestamp: float = self.max_data.timestamp()
        #     interval_candles: list[QtCharts.QCandlestickSet] = []
        #
        #     '''------------------------------------Заполняем серию свечей------------------------------------'''
        #     for candle in candles:
        #         assert candle.low <= candle.open and candle.low <= candle.close and candle.low <= candle.high
        #         assert candle.high >= candle.open and candle.high >= candle.close
        #
        #         candlestick = getQCandlestickSetFromHistoricCandle(candle=candle, parent=self)
        #         candlestick_series.append(candlestick)
        #
        #         if min_timestamp <= candle.time.timestamp() <= max_timestamp:
        #             interval_candles.append(candlestick)
        #     '''----------------------------------------------------------------------------------------------'''
        #
        #     if interval_candles:
        #         '''---Определяем минимальную цену на выбранном отрезке времени---'''
        #         min_price: float = min(candle.low() for candle in interval_candles)
        #         max_price: float = max(candle.high() for candle in interval_candles)
        #         '''--------------------------------------------------------------'''
        #         axisY: QtCharts.QValueAxis = self.__createAxisY(min_price, max_price)
        #     else:
        #         axisY: QtCharts.QValueAxis = self.__createAxisY()
        # else:
        #     axisY: QtCharts.QValueAxis = self.__createAxisY()
        '''=========================================================================================='''

        '''========================Если надо отображать только последние свечи========================'''
        if candles:
            min_timestamp: float = self.min_data.timestamp()
            max_timestamp: float = self.max_data.timestamp()

            '''------------------------------------Заполняем серию свечей------------------------------------'''
            for candle in candles:
                assert candle.low <= candle.open and candle.low <= candle.close and candle.low <= candle.high
                assert candle.high >= candle.open and candle.high >= candle.close

                if min_timestamp <= candle.time.timestamp() <= max_timestamp:
                    candlestick = getQCandlestickSetFromHistoricCandle(candle=candle, parent=self)
                    candlestick_series.append(candlestick)
            '''----------------------------------------------------------------------------------------------'''

            if candlestick_series.sets():
                '''---Определяем минимальную цену на выбранном отрезке времени---'''
                min_price: float = min(candle.low() for candle in candlestick_series.sets())
                max_price: float = max(candle.high() for candle in candlestick_series.sets())
                '''--------------------------------------------------------------'''
                axisY: QtCharts.QValueAxis = self.__createAxisY(min_price, max_price)
            else:
                axisY: QtCharts.QValueAxis = self.__createAxisY()
        else:
            axisY: QtCharts.QValueAxis = self.__createAxisY()
        '''==========================================================================================='''

        self.addAxis(axisY, QtCore.Qt.AlignmentFlag.AlignLeft)

        axisX: QtCharts.QDateTimeAxis = self.__createAxisX(self.min_data, self.max_data)
        self.addAxis(axisX, QtCore.Qt.AlignmentFlag.AlignBottom)

        self.addSeries(candlestick_series)

        attachAxisX_flag: bool = candlestick_series.attachAxis(axisX)
        assert attachAxisX_flag, 'Не удалось прикрепить ось X к series.'
        attachAxisY_flag: bool = candlestick_series.attachAxis(axisY)
        assert attachAxisY_flag, 'Не удалось прикрепить ось Y к series.'


class CandlesChartView(QtCharts.QChartView):
    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)
        self.setRubberBand(QtCharts.QChartView.RubberBand.RectangleRubberBand)
        chart = CandlesChart()
        self.setChart(chart)

    def chart(self) -> CandlesChart | None:
        return super().chart()

    def setCandles(self, candles: list[HistoricCandle], interval: CandleInterval):
        """Обновляем данные графика."""
        chart = self.chart()
        assert type(chart) is CandlesChart
        self.chart().setCandles(candles, interval)
