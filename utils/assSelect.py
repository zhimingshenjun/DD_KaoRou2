#!/usr/bin/python3
# -*- coding: utf-8 -*-

import codecs
from PySide2.QtWidgets import QWidget, QMainWindow, QGridLayout, QFileDialog, QToolBar,\
        QAction, QDialog, QStyle, QSlider, QLabel, QPushButton, QStackedWidget, QHBoxLayout,\
        QLineEdit, QTableWidget, QAbstractItemView, QTableWidgetItem, QGraphicsTextItem, QMenu,\
        QGraphicsScene, QGraphicsView, QGraphicsDropShadowEffect, QComboBox, QMessageBox, QColorDialog
from PySide2.QtMultimedia import QMediaPlayer
from PySide2.QtMultimediaWidgets import QGraphicsVideoItem
from PySide2.QtGui import QIcon, QKeySequence, QFont, QBrush, QColor
from PySide2.QtCore import Qt, QTimer, QEvent, QPoint, Signal, QSizeF, QUrl


def ms2ASSTime(ms):
    '''
    receive int
    return str
    ms -> h:m:s.ms
    '''
    h, m = divmod(ms, 3600000)
    m, s = divmod(m, 60000)
    s, ms = divmod(s, 1000)
    ms = ('%03d' % ms)[:2]
    return '%s:%02d:%02d.%s' % (h, m, s, ms)


def calSubTime(t):
    '''
    receive str
    return int
    h:m:s.ms -> ms in total
    '''
    t = t.replace(',', '.').replace('：', ':')
    h, m, s = t.split(':')
    if '.' in s:
        s, ms = s.split('.')
        ms = ('%s00' % ms)[:3]
    else:
        ms = 0
    h, m, s, ms = map(int, [h, m, s, ms])
    return h * 3600000 + m * 60000 + s * 1000 + ms


class assCheck(QDialog):
    getSub = Signal()
    position = Signal(int)

    def __init__(self, subtitleDict, index, styles, styleNameList):
        super().__init__()
        self.subtitleDict = subtitleDict
        self.index = index
        self.styles = styles
        self.resize(950, 800)
        self.setWindowTitle('检查字幕')
        layout = QGridLayout()
        self.setLayout(layout)
        layout.addWidget(QLabel('选择字幕轨道:'), 0, 0, 1, 1)
        layout.addWidget(QLabel(''), 0, 1, 1, 1)
        self.subCombox = QComboBox()
        self.subCombox.addItems(styleNameList)
        self.subCombox.setCurrentIndex(index)
        self.subCombox.currentIndexChanged.connect(self.selectChange)
        layout.addWidget(self.subCombox, 0, 2, 1, 1)
        self.subTable = QTableWidget()
        self.subTable.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.subTable.doubleClicked.connect(self.clickTable)
        self.subTable.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.subTable, 1, 0, 6, 3)
        self.refresh = QPushButton('刷新')
        self.refresh.clicked.connect(self.refreshSub)
        layout.addWidget(self.refresh, 7, 0, 1, 1)
        self.cancel = QPushButton('确定')
        self.cancel.clicked.connect(self.hide)
        layout.addWidget(self.cancel, 7, 2, 1, 1)
        self.refreshTable()

    def setDefault(self, subtitleDict, styles):
        self.subtitleDict = subtitleDict
        self.styles = styles
        self.refreshTable()

    def selectChange(self, index):
        self.index = index
        self.refreshTable()

    def refreshSub(self):
        self.getSub.emit()

    def refreshTable(self):
        style = self.styles[self.index]
        subDict = self.subtitleDict[self.index]
        self.subTable.clear()
        self.subTable.setRowCount(22 + len(subDict))
        self.subTable.setColumnCount(4)
        for col in range(3):
            self.subTable.setColumnWidth(col, 160)
        self.subTable.setColumnWidth(3, 350)
        for y, name in enumerate(['Fontname', 'Fontsize', 'PrimaryColour', 'SecondaryColour', 'OutlineColour', 'BackColour',
                                  'Bold', 'Italic', 'Underline', 'StrikeOut', 'ScaleX', 'ScaleY', 'Spacing', 'Angle', 'BorderStyle',
                                  'Outline', 'Shadow', 'Alignment', 'MarginL', 'MarginR', 'MarginV', 'Encoding']):
            self.subTable.setItem(y, 0, QTableWidgetItem(name))
            self.subTable.setItem(y, 1, QTableWidgetItem(str(style[y])))
        startList = sorted(subDict.keys())
        preConflict = False
        nextConflict = False
        for y, start in enumerate(startList):
            delta, text = subDict[start]
            end = start + delta
            if y < len(startList) - 1:
                nextStart = startList[y + 1]
                if end > nextStart:
                    nextConflict = True
                else:
                    nextConflict = False
            if delta < 500 or delta > 8000:  # 持续时间小于500ms或大于8s
                deltaError = 2
            elif delta > 4500:  # 持续时间大于4.5s且小于8s
                deltaError = 1
            else:
                deltaError = 0
            end = ms2ASSTime(start + delta)
            start = ms2ASSTime(start)
            s, ms = divmod(delta, 1000)
            ms = ('%03d' % ms)[:2]
            delta = '持续 %s.%ss' % (s, ms)
            self.subTable.setItem(y + 22, 0, QTableWidgetItem(start))  # 开始时间
            if preConflict:
                self.subTable.item(y + 22, 0).setBackground(QColor('#B22222'))  # 红色警告
            self.subTable.setItem(y + 22, 1, QTableWidgetItem(end))  # 结束时间
            if nextConflict:
                self.subTable.item(y + 22, 1).setBackground(QColor('#B22222'))  # 红色警告
            self.subTable.setItem(y + 22, 2, QTableWidgetItem(delta))  # 持续时间
            if deltaError == 2:
                self.subTable.item(y + 22, 2).setBackground(QColor('#B22222'))  # 红色警告
            elif deltaError == 1:
                self.subTable.item(y + 22, 2).setBackground(QColor('#FA8072'))  # 橙色警告
            self.subTable.setItem(y + 22, 3, QTableWidgetItem(text))  # 字幕文本
            preConflict = nextConflict  # 将重叠信号传递给下一条轴

    def clickTable(self):
        item = self.subTable.selectedItems()[0]
        row = item.row()
        if row > 21:
            pos = calSubTime(item.text())
            self.position.emit(pos)  # 发射点击位置


class assSelect(QDialog):
    assSummary = Signal(list)

    def __init__(self):
        super().__init__()
        self.subDict = {'': {'Fontname': '', 'Fontsize': '', 'PrimaryColour': '', 'SecondaryColour': '',
                             'OutlineColour': '', 'BackColour': '', 'Bold': '', 'Italic': '', 'Underline': '', 'StrikeOut': '',
                             'ScaleX': '', 'ScaleY': '', 'Spacing': '', 'Angle': '', 'BorderStyle': '', 'Outline': '',
                             'Shadow': '', 'Alignment': '', 'MarginL': '', 'MarginR': '', 'MarginV': '', 'Encoding': '',
                             'Tableview': [], 'Events': []}}
        self.resize(950, 800)
        self.setWindowTitle('选择要导入的ass字幕轨道')
        layout = QGridLayout()
        self.setLayout(layout)
        layout.addWidget(QLabel('检测到字幕样式:'), 0, 0, 1, 1)
        layout.addWidget(QLabel(''), 0, 1, 1, 1)
        self.subCombox = QComboBox()
        self.subCombox.currentTextChanged.connect(self.selectChange)
        layout.addWidget(self.subCombox, 0, 2, 1, 1)
        self.subTable = QTableWidget()
        self.subTable.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.subTable, 1, 0, 6, 3)
        self.confirm = QPushButton('导入')
        self.confirm.clicked.connect(self.sendSub)
        layout.addWidget(self.confirm, 7, 0, 1, 1)
        self.confirmStyle = QPushButton('导入样式')
        self.confirmStyle.clicked.connect(self.sendSubStyle)
        layout.addWidget(self.confirmStyle, 7, 1, 1, 1)
        self.cancel = QPushButton('取消')
        self.cancel.clicked.connect(self.hide)
        layout.addWidget(self.cancel, 7, 2, 1, 1)

    def setDefault(self, subtitlePath='', index=0):
        if subtitlePath:
            self.assCheck(subtitlePath)
            self.index = index

    def selectChange(self, styleName):
        self.subTable.clear()
        self.subTable.setRowCount(len(self.subDict[styleName]) + len(self.subDict[styleName]['Tableview']) - 2)
        self.subTable.setColumnCount(4)
        for col in range(3):
            self.subTable.setColumnWidth(col, 160)
        self.subTable.setColumnWidth(3, 350)
        y = 0
        for k, v in self.subDict[styleName].items():
            if k not in ['Tableview', 'Events']:
                self.subTable.setItem(y, 0, QTableWidgetItem(k))
                self.subTable.setItem(y, 1, QTableWidgetItem(v))
                y += 1
            elif k == 'Tableview':
                preConflict = False  # 上一条字幕时轴有重叠
                for cnt, line in enumerate(v):
                    nextConflict = False
                    start = calSubTime(line[0])
                    end = calSubTime(line[1])
                    if cnt < len(v) - 1:
                        nextStart = calSubTime(v[cnt + 1][0])
                        if end > nextStart:
                            nextConflict = True
                        else:
                            nextConflict = False
                    delta = end - start
                    if delta < 500 or delta > 8000:  # 持续时间小于500ms或大于8s
                        deltaError = 2
                    elif delta > 4500:  # 持续时间大于4.5s且小于8s
                        deltaError = 1
                    else:
                        deltaError = 0
                    s, ms = divmod(delta, 1000)
                    ms = ('%03d' % ms)[:2]
                    delta = '持续 %s.%ss' % (s, ms)
                    self.subTable.setItem(y, 0, QTableWidgetItem(line[0]))  # 开始时间
                    if preConflict:
                        self.subTable.item(y, 0).setBackground(QColor('#B22222'))  # 红色警告
                    self.subTable.setItem(y, 1, QTableWidgetItem(line[1]))  # 结束时间
                    if nextConflict:
                        self.subTable.item(y, 1).setBackground(QColor('#B22222'))  # 红色警告
                    self.subTable.setItem(y, 2, QTableWidgetItem(delta))  # 持续时间
                    if deltaError == 2:
                        self.subTable.item(y, 2).setBackground(QColor('#B22222'))  # 红色警告
                    elif deltaError == 1:
                        self.subTable.item(y, 2).setBackground(QColor('#FA8072'))  # 橙色警告
                    self.subTable.setItem(y, 3, QTableWidgetItem(line[2]))  # 字幕文本
                    y += 1
                    preConflict = nextConflict  # 将重叠信号传递给下一条轴

    def sendSub(self):
        self.assSummary.emit([self.index, self.subCombox.currentText(), self.subDict[self.subCombox.currentText()]])
        self.hide()

    def sendSubStyle(self):
        subData = self.subDict[self.subCombox.currentText()]
        subData['Events'] = {}
        self.assSummary.emit([self.index, self.subCombox.currentText(), subData])
        self.hide()

    def assCheck(self, subtitlePath):
        self.subDict = {'': {'Fontname': '', 'Fontsize': '', 'PrimaryColour': '', 'SecondaryColour': '',
                             'OutlineColour': '', 'BackColour': '', 'Bold': '', 'Italic': '', 'Underline': '', 'StrikeOut': '',
                             'ScaleX': '', 'ScaleY': '', 'Spacing': '', 'Angle': '', 'BorderStyle': '', 'Outline': '',
                             'Shadow': '', 'Alignment': '', 'MarginL': '', 'MarginR': '', 'MarginV': '', 'Encoding': '',
                             'Tableview': [], 'Events': {}}}
        ass = codecs.open(subtitlePath, 'r', 'utf_8_sig')
        f = ass.readlines()
        ass.close()
        V4Token = False
        styleFormat = []
        styles = []
        eventToken = False
        eventFormat = []
        events = []
        for line in f:
            if '[V4+ Styles]' in line:
                V4Token = True
            elif V4Token and 'Format:' in line:
                styleFormat = line.replace(' ', '').strip().split(':')[1].split(',')
            elif V4Token and 'Style:' in line and styleFormat:
                styles.append(line.strip().split(':')[1].split(','))
            elif '[Events]' in line:
                eventToken = True
                V4Token = False
            elif eventToken and 'Format:' in line:
                eventFormat = line.strip().split(':')[1].split(',')
            elif eventToken and 'Comment:' in line and eventFormat:
                events.append(line.strip().split('Comment:')[1].split(',', len(eventFormat) - 1))
            elif eventToken and 'Dialogue:' in line and eventFormat:
                events.append(line.strip().split('Dialogue:')[1].split(',', len(eventFormat) - 1))

        for cnt, _format in enumerate(eventFormat):
            _format = _format.replace(' ', '')
            if _format == 'Start':
                Start = cnt
            elif _format == 'End':
                End = cnt
            elif _format == 'Style':
                Style = cnt
            elif _format == 'Text':
                Text = cnt

        for style in styles:
            styleName = style[0]
            self.subDict[styleName] = {'Fontname': '', 'Fontsize': '', 'PrimaryColour': '', 'SecondaryColour': '',
                                       'OutlineColour': '', 'BackColour': '', 'Bold': '', 'Italic': '', 'Underline': '', 'StrikeOut': '',
                                       'ScaleX': '', 'ScaleY': '', 'Spacing': '', 'Angle': '', 'BorderStyle': '', 'Outline': '',
                                       'Shadow': '', 'Alignment': '', 'MarginL': '', 'MarginR': '', 'MarginV': '', 'Encoding': '',
                                       'Tableview': [], 'Events': {}}
            for cnt, _format in enumerate(styleFormat):
                if _format in self.subDict[styleName]:
                    self.subDict[styleName][_format] = style[cnt]
            for line in events:
                if styleName.replace(' ', '') == line[Style].replace(' ', ''):
                    start = calSubTime(line[Start]) // 10 * 10
                    delta = calSubTime(line[End]) - start // 10 * 10
                    self.subDict[styleName]['Tableview'].append([line[Start], line[End], line[Text]])
                    self.subDict[styleName]['Events'][start] = [delta, line[Text]]

        self.subCombox.clear()
        combox = []
        for style in self.subDict.keys():
            if style:
                combox.append(style)
        self.subCombox.addItems(combox)
