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


class CandlesSceneView(QtWidgets.QGraphicsView):
    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)

        # self.chart = CandlesChart()
        #
        # scene = QtWidgets.QGraphicsScene(parent=self)
        # scene.addItem(self.chart)
        # self.setScene(scene)
        # # scene.setSceneRect(0, 0, self.width(), self.height())
        # # u = scene.sceneRect()
        # # print('x: {0}, y: {0}'.format(u.x(), u.y()))
        # self.show()
        # u1 = self.chart.pos()
        # print('x: {0}, y: {1}'.format(u1.x(), u1.y()))

        '''-----Пробую отобразить в QGraphicsScene другую серию-----'''
        series = QtCharts.QLineSeries()
        series.append(0, 6)
        series.append(2, 4)
        series.append(3, 8)
        series.append(7, 4)
        series.append(10, 5)
        series.append(11, 1)
        series.append(13, 3)
        series.append(17, 6)
        series.append(20, 2)

        self.chart = QtCharts.QChart()
        self.chart.addSeries(series)
        self.chart.createDefaultAxes()

        scene = QtWidgets.QGraphicsScene(parent=self)
        scene.addItem(self.chart)

        def printParams():
            chart_mts: QtCore.QPointF = self.chart.mapToScene(0, 0)
            print('chart_mts: x: {0}, y: {1}.'.format(chart_mts.x(), chart_mts.y()))

            scene_rect: QtCore.QRectF = scene.sceneRect()
            print('scene_rect: x: {0}, y: {1}, width: {2}, height: {3}.'.format(scene_rect.x(), scene_rect.y(), scene_rect.width(), scene_rect.height()))

            view_mts: QtCore.QPointF = self.mapToScene(0, 0)
            print('view_mts: x: {0}, y: {1}.'.format(view_mts.x(), view_mts.y()))

            chart_point: QtCore.QPointF = self.chart.scenePos()
            print('Позиция chart в координатах сцены: x: {0}, y: {1}.'.format(chart_point.x(), chart_point.y()))

            viewport_rect: QtCore.QRect = self.viewport().rect()
            print('viewport_rect: x: {0}, y: {1}, width: {2}, height: {3}.'.format(viewport_rect.x(), viewport_rect.y(), viewport_rect.width(), viewport_rect.height()))

            scene_bounding_rect: QtCore.QRectF = scene.itemsBoundingRect()
            print('Ограничивающий прямоугольник элементов сцены: x: {0}, y: {1}, width: {2}, height: {3}.'.format(
                scene_bounding_rect.x(), scene_bounding_rect.y(), scene_bounding_rect.width(), scene_bounding_rect.height()))

        # self.setSceneRect(QtCore.QRectF(0, 0, self.viewport().width(), self.viewport().height()))

        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignBottom)

        self.setScene(scene)

        print('\nДо setSceneRect:')
        printParams()

        # viewport_rect: QtCore.QRect = self.viewport().rect()
        # scene.setSceneRect(QtCore.QRectF(viewport_rect))

        # scene_rect: QtCore.QRectF = scene.sceneRect()
        # self.fitInView(scene_rect, QtCore.Qt.AspectRatioMode.KeepAspectRatio)
        self.fitInView(self.chart, QtCore.Qt.AspectRatioMode.KeepAspectRatio)

        # self.mapToScene(QtCore.QRect(0, 0, self.viewport().width(), self.viewport().height()))
        # scene.setSceneRect(-0.5, -0.5, self.viewport().width(), self.viewport().height())
        # scene.setSceneRect(0, 0, 100, 100)

        print('\nПосле setSceneRect:')
        printParams()

        # '''------------Рисуем зелёный круг------------'''
        # rect = QtCore.QRectF(0, 0, 90, 90)
        # color = QtCore.Qt.GlobalColor.green
        #
        # item = QtWidgets.QGraphicsEllipseItem(rect)
        # item.setPen(QtGui.QPen(color))
        # item.setBrush(color)
        # self.scene().addItem(item)
        #
        # # self.scene().addEllipse(rect, QtGui.QPen(color), QtGui.QBrush(color))
        # '''-------------------------------------------'''
        '''---------------------------------------------------------'''

    def setCandles(self, candles: list[HistoricCandle], interval: CandleInterval):
        """Обновляем данные графика."""
        # self.chart.setCandles(candles, interval)
        #
        # # self.setSceneRect(0, 0, self.width(), self.height())
        # u: QtCore.QRectF = self.sceneRect()
        # print('x: {0}, y: {1}, width: {2}, height: {3}'.format(u.x(), u.y(), u.width(), u.height()))
        #
        # u1 = self.chart.pos()
        # print('x: {0}, y: {1}'.format(u1.x(), u1.y()))


        # self.chart = CandlesChart()
        # self.chart.setCandles(candles, interval)
        #
        # scene = QtWidgets.QGraphicsScene(parent=self)
        # scene.addItem(self.chart)
        # # scene.addText("Hello, world!")
        # self.setScene(scene)
        #
        # self.show()


        # '''------------Рисуем зелёный круг------------'''
        # rect = QtCore.QRectF(0, 0, 90, 90)
        # color = QtCore.Qt.GlobalColor.green
        #
        # item = QtWidgets.QGraphicsEllipseItem(rect)
        # item.setPen(QtGui.QPen(color))
        # item.setBrush(color)
        # self.scene().addItem(item)
        #
        # # self.scene().addEllipse(rect, QtGui.QPen(color), QtGui.QBrush(color))
        # '''-------------------------------------------'''

        '''-----Пробую отобразить в QGraphicsScene другую серию-----'''
        series = QtCharts.QLineSeries()
        series.append(0, 6)
        series.append(2, 4)
        series.append(3, 8)
        series.append(7, 4)
        series.append(10, 5)
        series.append(11, 1)
        series.append(13, 3)
        series.append(17, 6)
        series.append(20, 2)

        self.chart = QtCharts.QChart()
        self.chart.addSeries(series)
        self.chart.createDefaultAxes()

        scene = QtWidgets.QGraphicsScene(parent=self)
        scene.addItem(self.chart)

        self.setScene(scene)
        self.mapToScene(QtCore.QRect(0, 0, self.viewport().width(), self.viewport().height()))
        '''---------------------------------------------------------'''
