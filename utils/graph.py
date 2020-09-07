#!/usr/bin/python3
# -*- coding: utf-8 -*-

import shutil
import pyqtgraph as pg
pg.setConfigOption('background', '#232629')
from PySide2.QtWidgets import QWidget, QMainWindow, QGridLayout, QFileDialog, QToolBar,\
        QAction, QDialog, QStyle, QSlider, QLabel, QPushButton, QStackedWidget, QHBoxLayout,\
        QLineEdit, QTableWidget, QAbstractItemView, QTableWidgetItem, QGraphicsTextItem, QMenu,\
        QGraphicsScene, QGraphicsView, QGraphicsDropShadowEffect, QComboBox, QMessageBox, QColorDialog,\
    QVBoxLayout
from PySide2.QtMultimedia import QMediaPlayer
from PySide2.QtMultimediaWidgets import QGraphicsVideoItem
from PySide2.QtGui import QIcon, QKeySequence, QFont, QColor, QPen
from PySide2.QtCore import Qt, QTimer, QEvent, QPoint, Signal, QSizeF, QUrl


x_range = [-1, 1]
x_ticks = []


def ms2Time(ms):
    '''
    receive int
    return str
    ms -> m:s.ms
    '''
    m, s = divmod(ms, 60000)
    s, ms = divmod(s, 1000)
    return ('%s:%02d.%03d' % (m, s, ms))[:-1]


class graph_main(QWidget):  # 主音轨波形图
    clicked = Signal()

    def __init__(self):
        super().__init__()
        self.mp3Path = ''
        layout = QVBoxLayout(self)
        self.graph = pg.PlotWidget()
        self.graph.addLegend(offset=(0, 1))  # 图例
        layout.addWidget(self.graph)
        self.graph.setMenuEnabled(False)

        self.wavePlot = self.graph.plot([0], name='原音轨', pen=pg.mkPen('#CCCCCC'))  # 主音轨波形
        self.subShow = []
        for _ in range(5):  # 存放5条时轴的绘图对象
            self.subShow.append([self.graph.plot([0], fillLevel=0, brush=(173, 216, 230, 50)),  # 字幕轴显示(上层)
                                 self.graph.plot([0], fillLevel=0, brush=(173, 216, 230, 50))])  # 字幕轴显示(下层)
        self.currentPos = self.graph.addLine(0, pen=pg.mkPen('#d93c30', width=2))  # 当前红线位置
        self.ax = self.graph.getAxis('bottom')  # 底部时间戳

    def mousePressEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.clicked.emit()
        elif event.buttons() == Qt.RightButton:
            self.popTableMenu(event.pos())

    def popTableMenu(self, pos):
        pos = QPoint(pos.x() + 3, pos.y() - 4)
        menu = QMenu()
        exportAudio = menu.addAction('导出音频文件')
        action = menu.exec_(self.graph.mapToGlobal(pos))
        if action == exportAudio:
            if not self.mp3Path:
                QMessageBox.warning(self, '未检测到音轨文件', '请导入视频并确保视频音轨正常', QMessageBox.Ok)
            else:
                mp3Path = QFileDialog.getSaveFileName(self, "选择音频输出文件夹", None, "(*.acc)")[0]
                if mp3Path:
                    shutil.copy(self.mp3Path, mp3Path)
                    QMessageBox.information(self, '导出音轨文件', '导出完成', QMessageBox.Ok)

    def plot(self, x, y, h, step, limit=[-200, 200], subtitle={}):
        # self.graph.setTitle(mp3Path)
        self.wavePlot.setData(x, y)
        self.currentPos.setValue(h)
        for num, subLine in subtitle.items():
            sub_x = []
            subUp_y = []
            subDown_y = []
            limit_y = limit[1] * 2
            for subTime in subLine:
                sub_x += [subTime[0], subTime[0], subTime[1], subTime[1]]
                subUp_y += [0, limit_y, limit_y, 0]
                subDown_y += [0, -limit_y, -limit_y, 0]
            self.subShow[num][0].setData(sub_x, subUp_y)
            self.subShow[num][1].setData(sub_x, subDown_y)
        self.graph.setXRange(x[0], x[-1])  # 设置坐标轴范围
        self.graph.setYRange(limit[0], limit[1])
        global x_range
        x_range = [x[0], x[-1]]

        interval = len(x) // 10
        x = [x[0] + i * interval * step for i in range(11)]  # 设置x label为时间戳
        ticks = [ms2Time(int(ms)) for ms in x]
        modifiedTick = [[(x[i], ticks[i]) for i in range(11)]]
        self.ax.setTicks(modifiedTick)
        global x_ticks
        x_ticks = modifiedTick


class graph_vocal(QWidget):  # 人声音轨波形图
    clicked = Signal()

    def __init__(self):
        super().__init__()
        self.mp3Path = ''
        layout = QVBoxLayout(self)
        self.graph = pg.PlotWidget()
        self.graph.addLegend(offset=(0, 1))  # 图例
        layout.addWidget(self.graph)
        self.graph.setMenuEnabled(False)
        self.subShow = []
        for _ in range(5):  # 存放5条时轴的绘图对象
            self.subShow.append([self.graph.plot([0], fillLevel=0, brush=(173, 216, 230, 50)),  # 字幕轴显示(上层)
                                 self.graph.plot([0], fillLevel=0, brush=(173, 216, 230, 50))])  # 字幕轴显示(下层)
        self.voiceWaveUp = self.graph.plot([0], name='人声音轨', fillLevel=0, brush=(179, 220, 253), pen=pg.mkPen('#b3dcfd'))  # 人声有效值波形(上层)
        self.voiceWaveDown = self.graph.plot([0], fillLevel=0, brush=(179, 220, 253), pen=pg.mkPen('#b3dcfd'))  # 人声有效值波形(下层)
        self.bgmPlot = self.graph.plot([0], name='背景音轨', pen=pg.mkPen('#fdfdb3'))  # 背景音轨波形
        self.currentPos = self.graph.addLine(0, pen=pg.mkPen('#D93C30', width=2))  # 当前红线位置
        self.ax = self.graph.getAxis('bottom')  # 底部时间戳

    def mousePressEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.clicked.emit()
        elif event.buttons() == Qt.RightButton:
            self.popTableMenu(event.pos())

    def popTableMenu(self, pos):
        pos = QPoint(pos.x() + 3, pos.y() - 4)
        menu = QMenu()
        exportAudio = menu.addAction('导出音频文件')
        action = menu.exec_(self.graph.mapToGlobal(pos))
        if action == exportAudio:
            if not self.mp3Path:
                QMessageBox.warning(self, '未检测到音轨文件', '请先完成AI打轴以生成人声音轨和背景音轨', QMessageBox.Ok)
            else:
                mp3Path = QFileDialog.getSaveFileName(self, "选择音频输出文件夹", None, "(*.mp3)")[0]
                if mp3Path:
                    vocalPath = self.mp3Path + r'\vocals.mp3'
                    bgmPath = self.mp3Path + r'\bgm.mp3'
                    shutil.copy(vocalPath, mp3Path[:-4] + '_人声.mp3')
                    shutil.copy(bgmPath, mp3Path[:-4] + '_背景声.mp3')
                    QMessageBox.information(self, '导出音轨文件', '导出完成', QMessageBox.Ok)

    def plot(self, x, y, voiceToken, h, step, limit=[-200, 200], subtitle={}):
        # self.graph.setTitle(mp3Path)
        if voiceToken:  # 绘制人声音轨波形
            self.voiceWaveUp.setData(x, y)
            self.voiceWaveDown.setData(x, list(map(lambda x: -x, y)))
            self.bgmPlot.clear()
        else:  # 绘制背景音轨波形
            self.bgmPlot.setData(x, y)
            self.voiceWaveUp.clear()
            self.voiceWaveDown.clear()
        self.currentPos.setValue(h)
        for num, subLine in subtitle.items():
            sub_x = []
            subUp_y = []
            subDown_y = []
            limit_y = limit[1] * 2
            for subTime in subLine:
                sub_x += [subTime[0], subTime[0], subTime[1], subTime[1]]
                subUp_y += [0, limit_y, limit_y, 0]
                subDown_y += [0, -limit_y, -limit_y, 0]
            self.subShow[num][0].setData(sub_x, subUp_y)
            self.subShow[num][1].setData(sub_x, subDown_y)
        self.graph.setXRange(x_range[0], x_range[-1])  # 设置坐标轴范围
        self.graph.setYRange(limit[0], limit[1])

        self.ax.setTicks(x_ticks)
