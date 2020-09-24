# -*- coding: utf-8 -*-

import os, subprocess, copy, time, shutil, codecs
from PySide2.QtWidgets import QWidget, QMainWindow, QGridLayout, QFileDialog, QToolBar,\
        QAction, QDialog, QStyle, QSlider, QLabel, QPushButton, QStackedWidget, QHBoxLayout,\
        QLineEdit, QTableWidget, QAbstractItemView, QTableWidgetItem, QGraphicsTextItem, QMenu,\
        QGraphicsScene, QGraphicsView, QGraphicsDropShadowEffect, QComboBox, QMessageBox, QColorDialog, QDockWidget
from PySide2.QtMultimedia import QMediaPlayer
from PySide2.QtMultimediaWidgets import QGraphicsVideoItem
from PySide2.QtGui import QIcon, QKeySequence, QFont, QColor, QDesktopServices
from PySide2.QtCore import Qt, QTimer, QEvent, QPoint, Signal, QSizeF, QUrl, QItemSelectionModel
from utils.youtube_downloader import YoutubeDnld
from utils.subtitle import exportSubtitle
from utils.videoDecoder import VideoDecoder
from utils.AI import sepMainAudio, Separate
from utils.assSelect import assSelect, assCheck, subSelect
from utils.graph import graph_main, graph_vocal
from utils.pay import pay
from utils.hotKey import hotKey_Info
from utils.setting import settingPage
from utils.releases import releases
from utils.anime4k import Anime4KDialog


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


def calSubTime2(t):
    '''
    receive str
    return int
    m:s.ms -> ms in total
    '''
    t.replace(',', '.').replace('：', ':')
    m, s = t.split(':')
    if '.' in s:
        s, ms = s.split('.')
    else:
        ms = 0
    return int(m) * 60000 + int(s) * 1000 + int(ms)


def cnt2Time(cnt, interval):
    '''
    receive int
    return str
    count of interval times -> m:s.ms
    '''
    m, s = divmod(int(cnt * interval), 60000)
    s, ms = divmod(s, 1000)
    return ('%s:%02d.%03d' % (m, s, ms))[:-1]


def ms2Time(ms):
    '''
    receive int
    return str
    ms -> m:s.ms
    '''
    m, s = divmod(ms, 60000)
    s, ms = divmod(s, 1000)
    return ('%s:%02d.%03d' % (m, s, ms))[:-1]


def ms2SRTTime(ms):
    '''
    receive int
    return str
    ms -> h:m:s,ms
    '''
    h, m = divmod(ms, 3600000)
    m, s = divmod(m, 60000)
    s, ms = divmod(s, 1000)
    return '%s:%02d:%02d,%03d' % (h, m, s, ms)


def splitTime(position):
    '''
    ms -> m:s
    '''
    position = position // 1000
    m, s = divmod(position, 60)
    return '%02d:%02d' % (m, s)


class Slider(QSlider):
    pointClicked = Signal(QPoint)

    def mousePressEvent(self, event):
        self.pointClicked.emit(event.pos())

    def mouseMoveEvent(self, event):
        self.pointClicked.emit(event.pos())

    def wheelEvent(self, event):  # 把进度条的滚轮事件去了 用啥子滚轮
        pass


class LineEdit(QLineEdit):
    clicked = Signal()

    def mousePressEvent(self, event):
        self.clicked.emit()


class Label(QLabel):
    clicked = Signal()

    def mouseReleaseEvent(self, QMouseEvent):
        self.clicked.emit()


class GraphicsVideoItem(QGraphicsVideoItem):
    wheel = Signal(int)
    dropFile = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

    def wheelEvent(self, QEvent):
        self.wheel.emit(QEvent.delta())

    def dropEvent(self, QEvent):
        if QEvent.mimeData().hasUrls:
            self.dropFile.emit(QEvent.mimeData().urls()[0].toLocalFile())

class editStyleNameDialog(QDialog):
    styleName = Signal(str)

    def __init__(self):
        super().__init__()
        self.resize(325, 50)
        self.setWindowTitle('设置样式名')
        layout = QGridLayout()
        self.setLayout(layout)
        self.styleNameEdit = QLineEdit()
        layout.addWidget(self.styleNameEdit, 0, 0, 1, 1)
        confirmButton = QPushButton('确定')
        confirmButton.setFixedWidth(50)
        layout.addWidget(confirmButton, 0, 1, 1, 1)
        confirmButton.clicked.connect(self.sendNewName)

    def setDefaultName(self, name):
        self.styleNameEdit.setText(name)

    def sendNewName(self):
        newName = self.styleNameEdit.text()
        if newName:
            self.styleName.emit(newName)
            self.hide()


class PreviewSubtitle(QDialog):  # 设置字幕预览效果的窗口
    fontColor = '#ffffff'
    fontSize = 60
    bold = True
    italic = False
    shadowOffset = 4

    def __init__(self):
        super().__init__()
        self.resize(400, 200)
        self.setWindowTitle('设置预览字幕')
        layout = QGridLayout()
        self.setLayout(layout)
        layout.addWidget(QLabel('字体大小'), 0, 0, 1, 1)
        self.fontSizeBox = QComboBox()
        self.fontSizeBox.addItems([str(x * 10 + 30) for x in range(15)])
        self.fontSizeBox.setCurrentIndex(3)
        self.fontSizeBox.currentIndexChanged.connect(self.getFontSize)
        layout.addWidget(self.fontSizeBox, 0, 1, 1, 1)
        layout.addWidget(QLabel(''), 0, 2, 1, 1)
        layout.addWidget(QLabel('字体颜色'), 0, 3, 1, 1)
        self.fontColorSelect = Label()
        self.fontColorSelect.setAlignment(Qt.AlignCenter)
        self.fontColorSelect.setText(self.fontColor)
        self.fontColorSelect.setStyleSheet('background-color:%s;color:%s' % (self.fontColor, self.colorReverse(self.fontColor)))
        self.fontColorSelect.clicked.connect(self.getFontColor)
        layout.addWidget(self.fontColorSelect, 0, 4, 1, 1)
        self.boldCheckBox = QPushButton('粗体')
        self.boldCheckBox.setStyleSheet('background-color:#3daee9')
        self.boldCheckBox.clicked.connect(self.boldChange)
        layout.addWidget(self.boldCheckBox, 1, 0, 1, 1)
        self.italicCheckBox = QPushButton('斜体')
        self.italicCheckBox.clicked.connect(self.italicChange)
        layout.addWidget(self.italicCheckBox, 1, 1, 1, 1)
        layout.addWidget(QLabel('阴影距离'), 1, 3, 1, 1)
        self.shadowBox = QComboBox()
        self.shadowBox.addItems([str(x) for x in range(5)])
        self.shadowBox.setCurrentIndex(4)
        self.shadowBox.currentIndexChanged.connect(self.getShadow)
        layout.addWidget(self.shadowBox, 1, 4, 1, 1)

    def getFontSize(self, index):
        self.fontSize = [x * 10 + 30 for x in range(15)][index]

    def getFontColor(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.fontColor = color.name()
            self.fontColorSelect.setText(self.fontColor)
            self.fontColorSelect.setStyleSheet('background-color:%s;color:%s' % (self.fontColor, self.colorReverse(self.fontColor)))

    def colorReverse(self, color):
        r = 255 - int(color[1:3], 16)
        g = 255 - int(color[3:5], 16)
        b = 255 - int(color[5:7], 16)
        return '#%s%s%s' % (hex(r)[2:], hex(g)[2:], hex(b)[2:])

    def boldChange(self):
        self.bold = not self.bold
        if self.bold:
            self.boldCheckBox.setStyleSheet('background-color:#3daee9')
        else:
            self.boldCheckBox.setStyleSheet('background-color:#31363b')

    def italicChange(self):
        self.italic = not self.italic
        if self.italic:
            self.italicCheckBox.setStyleSheet('background-color:#3daee9')
        else:
            self.italicCheckBox.setStyleSheet('background-color:#31363b')

    def getShadow(self, index):
        self.shadowOffset = index


class MainWindow(QMainWindow):  # Main window
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.installEventFilter(self)
        self.subtitle = QTableWidget()  # 重载表格滚轮事件 需提前到渲染UI界面之前才不会报错
        self.subtitle.verticalScrollBar().installEventFilter(self)
        self.oldScrollBarValue = 0
        self.editStyleNameDialog = editStyleNameDialog()  # 编辑样式名的小弹窗
        self.editStyleNameDialog.styleName.connect(self.updateStyleName)
        self.editIndex = 0
        self.styleNameList = ['1', '2', '3', '4', '5']  # 样式名列表
        if not os.path.exists('temp_audio'):
            os.mkdir('temp_audio')

        self.setWindowTitle = 'DD烤肉机'
        self.dir = os.getcwd()  # 运行目录
        self.mainWidget = QWidget()
        self.mainLayout = QGridLayout()  # Grid layout
        self.mainLayout.setSpacing(10)
        self.mainWidget.setLayout(self.mainLayout)
        self.duration = 60000
        self.position = 0
        self.oldPosition = 0
        self.playRange = [0, self.duration]
        self.replay = 0  # 0: 播放完整视频; 1: 循环播放选择区间; 2: 单次播放选择区间
        self.bitrate = 2000
        self.fps = 60
        self.tablePreset = ['#AI自动识别', True]
        self.refreshMainAudioToken = False
        self.refreshVoiceToken = False  # 刷新AI识别人声音频

        self.assSelect = assSelect()
        self.assSelect.assSummary.connect(self.addASSSub)
        self.subSelect = subSelect()
        self.subSelect.select.connect(self.addSub)
        self.previewSubtitle = PreviewSubtitle()
        self.separate = Separate()
        self.separate.voiceList.connect(self.setAutoSubtitle)
        self.separate.voiceWave_graph.connect(self.addVoiceWave)  # AI分离出来的人声波形
        self.separate.tablePreset.connect(self.setTablePreset)
        self.separate.clearSub.connect(self.clearSubtitle)
        self.separate.translateResult.connect(self.updateTranslateResult)
        self.dnldWindow = YoutubeDnld()
        self.exportWindow = exportSubtitle()
        self.videoDecoder = VideoDecoder()
        self.videoDecoder.hide()
        self.videoDecoder.saveToken.connect(self.setSaveToken)
        self.videoDecoder.popAnime4K.connect(self.popAnime4K)
        self.exportWindow.exportArgs.connect(self.exportSubtitle)
        self.anime4KWindow = Anime4KDialog()
        self.anime4KWindow.hide()

        self.stack = QStackedWidget()

        # self.playerDock = QDockWidget('视频预览', self)
        # self.playerDock.setFloating(False)
        # self.playerDock.setWidget(self.stack)
        # self.addDockWidget(Qt.LeftDockWidgetArea, self.playerDock)

        self.mainLayout.addWidget(self.stack, 0, 0, 6, 4)
        buttonWidget = QWidget()
        buttonLayout = QHBoxLayout()
        buttonWidget.setLayout(buttonLayout)
        self.playButton = QPushButton('从本地打开')
        self.playButton.clicked.connect(self.open)
        self.playButton.setFixedWidth(400)
        self.playButton.setFixedHeight(75)
        self.dnldButton = QPushButton('Youtube下载器')
        self.dnldButton.clicked.connect(self.popDnld)
        self.dnldButton.setFixedWidth(400)
        self.dnldButton.setFixedHeight(75)
        buttonLayout.addWidget(self.playButton)
        buttonLayout.addWidget(self.dnldButton)
        self.stack.addWidget(buttonWidget)
        self.pay = pay()
        self.hotKeyInfo = hotKey_Info()
        self.releases = releases()
        self.videoPath = ''
        self.videoWidth = 1920
        self.videoHeight = 1080
        self.globalInterval = 100 / 3
        self.oldGlobalInterval = 50
        self.tableRefreshLimit = self.globalInterval
        self.timer = QTimer()
        self.timer.setInterval(self.globalInterval)
        self.graphTimer = QTimer()  # 刷新音频图的timer
        self.graphTimer.setInterval(33)
        self.setting = settingPage()
        self.setting.settingSignal.connect(self.changeSetting)

        self.tableRefresh = True
        self.settingDict = {'layoutType': '0',  # 0: 风格1, 1: 风格2
                            'redLinePos': '5',
                            'tableRefresh': '0',  # 0: 开启, 1: 关闭
                            'tableRefreshFPS': '0',  # 0: 60FPS, 1: 30FPS, 2: 20FPS, 3: 10FPS
                            'graphRefreshFPS': '1',  # 0: 60FPS, 1: 30FPS, 2: 20FPS, 3: 10FPS
                            }
        if os.path.exists('config'):  # 导入已存在的设置
            with open('config', 'r') as cfg:
                for line in cfg:
                    if '=' in line:
                        try:
                            cfgName, cfgValue = line.strip().replace(' ', '').split('=')
                            if cfgName in self.settingDict:
                                self.settingDict[cfgName] = cfgValue
                        except Exception as e:
                            print(str(e))
        self.tableRefresh = [True, False][int(self.settingDict['tableRefresh'])]
        self.changeSetting(self.settingDict)

        self.sepMain = sepMainAudio(self.videoPath, self.duration)  # 创建切片主音频线程对象
        self.videoWindowSizePreset = {0: (640, 360), 1: (800, 450), 2: (1176, 664), 3: (1280, 720),
                                      4: (1366, 768), 5: (1600, 900), 6: (1920, 1080), 7: (2560, 1600)}
        self.videoWindowSizeIndex = 1
        self.setPlayer()
        self.setGraph()
        self.setSubtitle()

        self.setToolBar()
        self.setCentralWidget(self.mainWidget)
        self.editToken = False
        self.playStatus = False
        self.volumeStatus = True
        self.volumeValue = 100
        self.subSelectedTxt = ''
        self.subReplayTime = 1
        self.subtitleSelected = 0
        self.clipBoard = []
        self.subPreview = ''
        self.saveToken = True
        self.grabKeyboard()
        self.show()

    def setPlayer(self):
        self.playerWidget = GraphicsVideoItem()
        self.playerWidget.wheel.connect(self.changeVideoWindowSize)
        self.playerWidget.dropFile.connect(self.openVideo)
        w, h = self.videoWindowSizePreset[self.videoWindowSizeIndex]
        self.playerWidget.setSize(QSizeF(w, h))
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.scene.addItem(self.playerWidget)
        self.stack.addWidget(self.view)
        self.player = QMediaPlayer()
        self.player.setVideoOutput(self.playerWidget)
        self.view.installEventFilter(self)
        self.view.show()
        self.tipText = QGraphicsTextItem()
        self.scene.addItem(self.tipText)
        w = self.width()
        h = self.height()
        self.view.setFixedSize(w, h)
        self.scene.setSceneRect(5, 5, w - 10, h - 10)
        self.playerWidget.setSize(QSizeF(w, h))

        self.playerWidget_vocal = GraphicsVideoItem()
        self.scene_vocal = QGraphicsScene()
        self.view_vocal = QGraphicsView(self.scene_vocal)
        self.scene_vocal.addItem(self.playerWidget_vocal)
        self.stack.addWidget(self.view_vocal)
        self.player_vocal = QMediaPlayer(self, QMediaPlayer.VideoSurface)
        self.player_vocal.setVideoOutput(self.playerWidget_vocal)
        self.view_vocal.show()

    def changeVideoWindowSize(self, delta):
        if delta < 0:
            self.videoWindowSizeIndex -= 1
            if self.videoWindowSizeIndex < 0:
                self.videoWindowSizeIndex = 0
        else:
            self.videoWindowSizeIndex += 1
            if self.videoWindowSizeIndex > 7:
                self.videoWindowSizeIndex = 7
        w, h = self.videoWindowSizePreset[self.videoWindowSizeIndex]
        if h > self.height() * 0.65:
            self.videoWindowSizeIndex -= 1
        else:
            self.stack.setFixedSize(w, h)
            self.view.setFixedSize(w, h)
            self.scene.setSceneRect(5, 5, w - 10, h - 10)
            self.playerWidget.setSize(QSizeF(w, h))

    def setGraph(self):  # 绘制音频图
        self.mainAudio = graph_main()
        self.mainAudio.clicked.connect(self.playMainAudio)
        self.voiceAudio = graph_vocal()
        self.voiceAudio.clicked.connect(self.playVocal)
        self.graphWidget = QWidget()
        graphWidgetLayout = QGridLayout()
        self.graphWidget.setLayout(graphWidgetLayout)
        graphWidgetLayout.addWidget(self.mainAudio, 0, 0, 1, 1)
        graphWidgetLayout.addWidget(self.voiceAudio, 1, 0, 1, 1)

        # self.graphDock = QDockWidget('波形图', self)
        # self.graphDock.setFloating(False)
        # self.graphDock.setWidget(self.graphWidget)
        # self.addDockWidget(Qt.LeftDockWidgetArea, self.graphDock)

        if self.settingDict['layoutType'] == '0':
            self.mainLayout.addWidget(self.mainAudio, 6, 0, 1, 4)
            self.mainLayout.addWidget(self.voiceAudio, 7, 0, 1, 4)
        elif self.settingDict['layoutType'] == '1':
            self.mainLayout.addWidget(self.mainAudio, 6, 0, 1, 20)
            self.mainLayout.addWidget(self.voiceAudio, 7, 0, 1, 20)

    def setSubtitle(self):
        self.subtitleDict = {0: {}, 1: {}, 2: {}, 3: {}, 4: {}}  # 初始字幕字典
        self.subTimer = QTimer()
        self.subTimer.setInterval(10)
        self.subtitle.setAutoScroll(False)
        self.subtitle.setEditTriggers(QAbstractItemView.NoEditTriggers)

        # self.subtitleDock = QDockWidget('字幕编辑', self)
        # self.subtitleDock.setFloating(False)
        # self.subtitleDock.setWidget(self.subtitle)
        # self.addDockWidget(Qt.RightDockWidgetArea, self.subtitleDock)

        if self.settingDict['layoutType'] == '0':
            self.mainLayout.addWidget(self.subtitle, 0, 4, 8, 16)
        elif self.settingDict['layoutType'] == '1':
            self.mainLayout.addWidget(self.subtitle, 0, 4, 6, 16)
        self.subtitle.setColumnCount(5)
        self.subtitle.setRowCount(101)
        for index in range(5):
            self.subtitle.setColumnWidth(index, 130)
        for row in range(101):
            self.subtitle.setRowHeight(row, 15)
        self.refreshTable()
        self.row = 0
        self.subtitle.selectRow(self.row)
        self.subtitle.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.subtitle.setEditTriggers(QAbstractItemView.DoubleClicked)
        self.subtitle.horizontalHeader().sectionClicked.connect(self.editStyleName)
        self.subtitle.doubleClicked.connect(self.startEdit)  # 双击单元格开始编辑
        self.subtitle.verticalHeader().sectionClicked.connect(self.subHeaderClick)
        self.subtitle.setContextMenuPolicy(Qt.CustomContextMenu)
        self.subtitle.customContextMenuRequested.connect(self.popTableMenu)
        self.subtitle.cellEntered.connect(self.followMouse)
        self.subtitleBackend = []
        self.subtitleBackendPoint = 0

    def followMouse(self, row, col):  # 鼠标按住拖动时 全局进度跟随鼠标
        if self.player.duration() and self.tableRefresh:
            position = int(row * self.globalInterval) + self.position  # 进度为 点击行号x间隔 +全局进度
            self.player.setPosition(position)
            self.player_vocal.setPosition(position)
            self.videoSlider.setValue(position * self.videoSlider.width() // self.player.duration())
            self.setTimeLabel(position)

    def refreshTable(self, position=0, select=0, scroll=0):  # 实时刷新表格
        self.subtitle.clearSpans()
        self.subtitle.clear()
        if not position:
            self.position = self.player.position()
        else:
            self.position = position
        self.row, remain = divmod(self.position, self.globalInterval)  # 当前进度行号
        self.row = int(self.row)
        if remain:
            self.row += 1
        self.subtitle.selectRow(select)  # 永远选在第一行
        self.subtitle.verticalScrollBar().setValue(scroll)  # 滚动条选在第一行
        self.subtitle.setVerticalHeaderLabels([cnt2Time(i, self.globalInterval) for i in range(self.row, self.row + 101)])  # 刷新行号
        self.subtitle.setHorizontalHeaderLabels(self.styleNameList)  # 设置列名（样式名）
        subtitleViewUp = self.position  # 表格视窗开始时间（ms）
        subtitleViewDown = self.position + int(100 * self.globalInterval)  # 表格视窗结束时间（ms）
        for x, subData in self.subtitleDict.items():  # 只刷新进度 +100行范围内的字幕
            for start in sorted(subData):  # 字幕字典格式 {开始时间（ms）：[持续时间（ms），字幕]}
                delta, text = subData[start]
                if delta < 500 or delta > 8000:  # 持续时间小于500ms或大于8s
                    tableColor = '#B22222'
                elif delta > 4500:  # 持续时间大于4.5s且小于8s
                    tableColor = '#FA8072'
                else:
                    tableColor = '#35545d'
                if start >= subtitleViewDown or not delta:  # 超出表格视窗则跳出
                    break
                elif start + delta >= subtitleViewUp:  # 计算字幕条位于表格视窗的位置
                    startRow, remain = divmod(start, self.globalInterval)  # 起始行
                    if remain:
                        startRow += 1
                    startRow = int(startRow - self.row)
                    endRow, remain = divmod(start + delta, self.globalInterval)  # 结束行
                    if remain:
                        endRow += 1
                    endRow = int(endRow - self.row)
                    if startRow < 0:  # 防止超出表格视窗
                        startRow = 0
                    if endRow > 101:
                        endRow = 101
                    if endRow > startRow:  # 小于一行的跳过
                        for y in range(startRow, endRow):
                            self.subtitle.setItem(y, x, QTableWidgetItem(text))
                        self.subtitle.item(startRow, x).setBackground(QColor(tableColor))
                        self.subtitle.setSpan(startRow, x, endRow - startRow, 1)  # 跨行合并
                        self.subtitle.item(startRow, x).setTextAlignment(Qt.AlignTop)  # 字幕居上

    def editStyleName(self, index):  # 点击表头弹出修改样式名弹窗
        self.editIndex = index
        self.releaseKeyboard()
        self.editStyleNameDialog.setDefaultName(self.styleNameList[index])
        self.editStyleNameDialog.hide()
        self.editStyleNameDialog.show()

    def updateStyleName(self, styleName):  # 更新表头（样式名）
        self.styleNameList[self.editIndex] = styleName
        self.subtitle.setHorizontalHeaderLabels(self.styleNameList)

    def addSubtitle(self, index, subtitlePath=''):
        self.editIndex = index
        if not subtitlePath:
            subtitlePath = QFileDialog.getOpenFileName(self, "请选择字幕", None, "字幕文件 (*.srt *.vtt *.ass *.lrc)")[0]
        if subtitlePath:
            subData = {}
            if subtitlePath.endswith('.ass'):
                self.assSelect.setDefault(subtitlePath, index)
                self.assSelect.hide()
                self.assSelect.show()
            else:
                with open(subtitlePath, 'r', encoding='utf-8') as f:
                    f = f.readlines()
                if subtitlePath.endswith('.vtt'):
                    format = 'vtt'
                    for cnt, l in enumerate(f):
                        if '<c>' in l:  # 油管vtt字幕格式——逐字识别字幕
                            lineData = l.split('c>')
                            if len(lineData) > 3:
                                subText, start, _ = lineData[0].split('<')
                                start = calSubTime(start[:-1]) // 10 * 10
                                # if start not in self.subtitleDict[index]:
                                end = calSubTime(lineData[-3][1:-2]) // 10 * 10
                                for i in range(len(lineData) // 2):
                                    subText += lineData[i * 2 + 1][:-2]
                                subData[start] = [end - start, subText]
                            else:  # 油管自动识别出来的那种超短单行字幕
                                subText, start, _ = lineData[0].split('<')
                                start = calSubTime(start[:-1]) // 10 * 10
                                # if start not in self.subtitleDict[index]:
                                subText += lineData[1][:-2]
                                subData[start] = [int(self.globalInterval), subText]
                        elif '-->' in l and f[cnt + 2].strip() and '<c>' not in f[cnt + 2]:  # 油管vtt字幕——单行类srt格式字幕
                            subText = f[cnt + 2][:-1]
                            start, end = l.strip().replace(' ', '').split('-->')
                            start = calSubTime(start) // 10 * 10
                            # if start not in self.subtitleDict[index]:
                            if 'al' in end:  # align
                                end = end.split('al')[0]
                            end = calSubTime(end) // 10 * 10
                            subData[start] = [end - start, subText]
                elif subtitlePath.endswith('.srt'):
                    format = 'srt'
                    for cnt, l in enumerate(f):
                        if '-->' in l and f[cnt + 1].strip():  # srt字幕格式
                            start, end = l.strip().replace(' ', '').split('-->')
                            start = calSubTime(start) // 10 * 10
                            # if start not in self.subtitleDict[index]:
                            end = calSubTime(end) // 10 * 10
                            delta = end - start
                            if delta > 10:
                                if '<b>' in f[cnt + 1]:  # 有的字幕里带<b> 好像是通过ffmpeg把ass转srt出来的
                                    subData[start] = [delta, f[cnt + 1].split('<b>')[1].split('<')[0]]
                                else:
                                    subData[start] = [delta, f[cnt + 1][:-1]]
                elif subtitlePath.endswith('.lrc'):
                    format = 'lrc'
                    while '\n' in f:
                        f.remove('\n')
                    for cnt, l in enumerate(f[:-1]):
                        try:
                            if len(l) > 9:
                                if l[0] == '[' and l[9] == ']':
                                    start = calSubTime2(l[1:9])
                                    delta = calSubTime2(f[cnt + 1][1:9]) - start
                                    text = l.strip()[10:]
                                    subData[start] = [delta, text]
                        except Exception as e:
                            print(str(e))
                    if len(f[:-1]) > 9:
                        if f[:-1][0] == '[' and f[:-1][9] == ']':
                            try:
                                start = calSubTime2(f[:-1][1:9])
                                delta = self.duration - start
                                text = f[:-1].strip()[10:]
                                subData[start] = [delta, text]
                            except Exception as e:
                                print(str(e))
                self.subSelect.setDefault(subData, index, format)
                self.subSelect.hide()
                self.subSelect.show()
                # self.subtitleDict[index].update(subData)
                # self.updateBackend()
                # self.refreshTable()

    def addASSSub(self, assSummary):  # 解析返回的ass字幕
        index = assSummary[0]  # 列号
        styleName = assSummary[1]  # 样式名
        assDict = assSummary[2]  # 字幕信息
        self.styleNameList[self.editIndex] = styleName  # 更新样式名
        self.videoDecoder.setSubDictStyle(assSummary)  # 设置输出页面字幕样式
        subData = assDict['Events']
        self.subtitleDict[index].update(subData)  # 更新读取ass的对话字典
        self.updateBackend()
        self.refreshTable()

    def addSub(self, subData, index):  # 导入其他类型字幕
        self.subtitleDict[index].update(subData)
        self.updateBackend()
        self.refreshTable()

    def subTimeOut(self):  # 刷新预览字幕
        if self.dnldWindow.isHidden() and self.exportWindow.isHidden() and self.videoDecoder.isHidden()\
        and self.separate.isHidden() and self.editStyleNameDialog.isHidden() and not self.editToken\
        and self.anime4KWindow.isHidden() and self.hotKeyInfo.isHidden() and self.videoPositionEdit.isReadOnly():
            self.grabKeyboard()
        fontColor = self.previewSubtitle.fontColor  # 预览字幕样式
        fontSize = (self.previewSubtitle.fontSize + 5) / 2.5
        fontBold = self.previewSubtitle.bold
        fontItalic = self.previewSubtitle.italic
        fontShadowOffset = self.previewSubtitle.shadowOffset
        font = QFont()
        font.setFamily("微软雅黑")
        font.setPointSize(fontSize)
        font.setBold(fontBold)
        font.setItalic(fontItalic)
        srtTextShadow = QGraphicsDropShadowEffect()  # 设置阴影
        srtTextShadow.setOffset(fontShadowOffset)
        txt = ''
        self.tipText.setDefaultTextColor(fontColor)
        self.tipText.setFont(font)
        self.tipText.setGraphicsEffect(srtTextShadow)
        if self.replay == 1:  # 循环播放提示
            txt += '循环播放: %s —— %s\n' % tuple(map(ms2Time, self.playRange))
        elif self.replay == 2:  # 单次播放提示
            txt += '单次播放: %s —— %s\n' % tuple(map(ms2Time, self.playRange))
        if self.secondeMedia:  # 切换第二音轨时视频左上角提示文字
            if self.voiceMedia:
                txt += '当前播放: 人声音轨\n'
            else:
                txt += '当前播放: 背景音轨\n'
        self.tipText.setPlainText(txt)

    def subHeaderClick(self, row):  # 点击行号跳转
        if self.player.duration():
            position = int(row * self.globalInterval) + self.position  # 进度为 点击行号x间隔 +全局进度
            self.player.setPosition(position)
            self.player_vocal.setPosition(position)
            self.videoSlider.setValue(position * self.videoSlider.width() // self.player.duration())
            self.setTimeLabel(position)

    def startEdit(self):
        self.releaseKeyboard()
        self.editToken = True
        try:
            self.subtitle.cellChanged.disconnect(self.subEdit)  # 在连接cellchanged信号前先尝试断开
        except:
            pass
        self.subtitle.cellChanged.connect(self.subEdit)

    def subEdit(self, row, col):
        self.subtitle.cellChanged.disconnect(self.subEdit)  # cellChanged信号只是用来进入subEdit函数 进来就断开
        repeat = self.subtitle.rowSpan(row, col)  # 获取合并格数
        text = self.subtitle.item(row, col).text()
        containToken = False
        newS = int((row + self.row) * self.globalInterval)
        subData = self.subtitleDict[col]
        for start, subLine in subData.items():
            delta = subLine[0]
            end = start + delta
            if newS >= start and newS < end:
                self.subtitleDict[col][start] = [delta, text]
                containToken = True
                break
        if not containToken:
            self.setSubtitleDict(row, col, repeat, text)  # 更新字典
        else:
            self.updateBackend()  # 备份并刷新显示
        for y in range(repeat):
            self.subtitle.setItem(row + y, col, QTableWidgetItem(text))  # 更新表格
            self.subtitle.item(row + y, col).setTextAlignment(Qt.AlignTop)  # 字幕居上
        delta = int(repeat * self.globalInterval)
        self.subtitle.item(row, col).setBackground(QColor('#35545d'))
        self.grabKeyboard()

    def setSubtitleDict(self, row, col, repeat, text, concat=False, delete=False):
        newSRow = row + self.row  # 编辑起始位置（行数）
        newERow = newSRow + repeat  # 编辑结束位置（行数）
        newS = int(newSRow * self.globalInterval)
        newE = int(newERow * self.globalInterval)
        start_end = [99999999, 0]
        old_start_end = [99999999, 0]
        keyList = copy.deepcopy(list(self.subtitleDict[col].keys()))
        for oldS in keyList:
            oldE = self.subtitleDict[col][oldS][0] + oldS
            if (newS <= oldS and newE > oldS + int(self.globalInterval)) or \
                    (newS < oldE - int(self.globalInterval) and newE >= oldE):
                del self.subtitleDict[col][oldS]
                if oldS < old_start_end[0]:
                    old_start_end[0] = oldS
                if oldE > old_start_end[1]:
                    old_start_end[1] = oldE
            if concat:
                if newS > oldS and newS < oldE - int(self.globalInterval):
                    newS = oldS
                    if oldS < start_end[0]:
                        start_end[0] = oldS
                if newE > oldS + int(self.globalInterval) and newE < oldE:
                    newE = oldE
                    if oldE > start_end[1]:
                        start_end[1] = oldE
        if concat:
            if start_end[0] != 99999999 and start_end[1]:
                self.subtitleDict[col][start_end[0]] = [start_end[1] - start_end[0], text]
            else:
                start = newS
                end = newE
                subStartList = sorted(self.subtitleDict[col].keys())
                for subStart in subStartList:
                    subEnd = self.subtitleDict[col][subStart][0] + subStart
                    if start < subEnd and end > subEnd:
                        start = subEnd
                    if end > subStart and end < subEnd:
                        end = subStart
                self.subtitleDict[col][int(start)] = [int(end - start), text]  # 更新字典
        elif old_start_end[0] != 99999999 and old_start_end[1]:
            start, end = old_start_end
            subStartList = sorted(self.subtitleDict[col].keys())
            for subStart in subStartList:
                subEnd = self.subtitleDict[col][subStart][0] + subStart
                if start < subEnd and end > subEnd:
                    start = subEnd
                if end > subStart and end < subEnd:
                    end = subStart
            self.subtitleDict[col][start] = [end - start, text]
        else:
            start = newS
            end = newE
            self.subtitleDict[col][round(start)] = [round(end - start), text]  # 更新字典
        if delete:
            try:
                del self.subtitleDict[col][newS]
            except:
                pass
        self.updateBackend()

    def updateBackend(self):  # 保存修改记录
        selected = self.subtitle.selectionModel().selection().indexes()
        if selected:
            y = selected[0].row()
        else:
            y = 0
        scrollValue = self.subtitle.verticalScrollBar().value()
        self.subtitleBackend = self.subtitleBackend[:self.subtitleBackendPoint + 1]
        self.subtitleBackend.append([copy.deepcopy(self.subtitleDict), self.position, y, scrollValue])
        self.subtitleBackendPoint = len(self.subtitleBackend) - 1
        if len(self.subtitleBackend) > 100:  # 超出100次修改 则删除最早的修改
            self.subtitleBackend.pop(0)
        if self.subPreview:
            self.refreshSubPreview()

    def refreshSubPreview(self):  # 修改实时预览字幕
        self.videoDecoder.copySubtitle(self.subtitleDict)  # 更新字幕内容给输出
        self.videoDecoder.writeAss(self.subPreview, False, True, allSub=True)  # 写入ass文件
        self.player.setPosition(self.position)  # 刷新视频

    def popTableMenu(self, pos):  # 右键菜单
        pos = QPoint(pos.x() + 55, pos.y() + 30)
        menu = QMenu()
        setSpan = menu.addAction('合并')
        cutSpan = menu.addAction('切割')
        clrSpan = menu.addAction('拆分')
        cut = menu.addAction('剪切')
        _copy = menu.addAction('复制')
        paste = menu.addAction('粘贴')
        delete = menu.addAction('删除')
        check = menu.addAction('检查')
        addSub = menu.addAction('导入')
        replay = menu.addAction('循环播放')
        cancelReplay = menu.addAction('取消循环')
        action = menu.exec_(self.subtitle.mapToGlobal(pos))
        selected = self.subtitle.selectionModel().selection().indexes()
        xList = []  # 选中行
        for i in range(len(selected)):
            x = selected[i].column()
            if x not in xList:  # 剔除重复选择
                xList.append(x)
        yList = [selected[0].row(), selected[-1].row()]
        if action == cut:  # 剪切
            selectRange = [int((y + self.row) * self.globalInterval) for y in range(yList[0], yList[1] + 1)]
            self.clipBoard = []
            for x in xList:
                for start, subData in self.subtitleDict[x].items():
                    end = subData[0] + start
                    for position in selectRange:
                        if start < position and position < end:
                            self.clipBoard.append([start, subData])
                            break
                for i in self.clipBoard:
                    start = i[0]
                    try:
                        del self.subtitleDict[x][start]
                    except:
                        pass
                for y in range(yList[0], yList[1] + 1):
                    if self.subtitle.item(y, x):
                        self.subtitle.setSpan(y, x, 1, 1)
                        self.subtitle.setItem(y, x, QTableWidgetItem(''))
                        self.subtitle.item(y, x).setBackground(QColor('#232629'))  # 没内容颜色
                break  # 只剪切选中的第一列
        elif action == _copy:  # 复制
            selectRange = [int((y + self.row) * self.globalInterval) for y in range(yList[0], yList[1] + 1)]
            self.clipBoard = []
            for x in xList:
                for start, subData in self.subtitleDict[x].items():
                    end = subData[0] + start
                    for position in selectRange:
                        if start < position and position < end:
                            self.clipBoard.append([start, subData])
                            break
                break  # 只复制选中的第一列
        elif action == paste:  # 粘贴
            if self.clipBoard:
                clipBoard = []
                for i in self.clipBoard:
                    clipBoard.append([i[0] - self.clipBoard[0][0], i[1]])  # 减去复制的字幕的起始偏移量
                startOffset = int((yList[0] + self.row) * self.globalInterval)
                for x in xList:
                    for subData in clipBoard:
                        start, subData = subData
                        delta, text = subData
                        start += startOffset
                        end = start + delta
                        for subStart in list(self.subtitleDict[x].keys()):
                            subEnd = self.subtitleDict[x][subStart][0] + subStart
                            if subStart < end and end < subEnd or subStart < start and start < subEnd:
                                del self.subtitleDict[x][subStart]
                        self.subtitleDict[x][start] = [delta, text]
                scrollValue = self.subtitle.verticalScrollBar().value()
                self.refreshTable(int(self.row * self.globalInterval), yList[0], scrollValue)
                self.updateBackend()
                self.refreshGraph(True)
        elif action == delete:  # 删除选中
            selectRange = [int((y + self.row) * self.globalInterval) for y in yList]
            for x in xList:
                startList = sorted(self.subtitleDict[x].keys())
                for start in startList:
                    end = self.subtitleDict[x][start][0] + start
                    for position in range(selectRange[0], selectRange[-1] + 1):
                        if start <= position and position < end:
                            try:
                                del self.subtitleDict[x][start]
                            except:
                                pass
            for x in xList:
                for y in range(yList[0], yList[1] + 1):
                    if self.subtitle.item(y, x):
                        self.subtitle.setSpan(y, x, 1, 1)
                        self.subtitle.setItem(y, x, QTableWidgetItem(''))
                        self.subtitle.item(y, x).setBackground(QColor('#232629'))  # 没内容颜色
            self.updateBackend()
            self.refreshGraph(True)
        elif action == check:  # 检查字幕
            styles = self.videoDecoder.returnSubDictStyle()
            self.assCheck = assCheck(self.subtitleDict, xList[0], styles, self.styleNameList)
            self.assCheck.getSub.connect(self.sendSubtitleToAssCheck)  # 刷新检查表格
            self.assCheck.position.connect(self.setPlayerPosition)
            self.assCheck.show()
        elif action == setSpan:  # 合并函数
            if yList[0] < yList[-1]:
                for x in xList:  # 循环所有选中的列
                    firstItem = ''
                    for y in range(yList[0], yList[1] + 1):  # 从选中行开始往下查询到第一个有效值后退出 一直没找到则为空
                        if self.subtitle.item(y, x):
                            if self.subtitle.item(y, x).text():
                                firstItem = self.subtitle.item(y, x).text()
                                break
                    for y in range(yList[0], yList[1] + 1):
                        if self.subtitle.rowSpan(y, x) > 1:
                            self.subtitle.setSpan(y, x, 1, 1)  # 清除合并格子
                    self.subtitle.setItem(yList[0], x, QTableWidgetItem(firstItem))  # 全部填上firstItem
                    self.subtitle.item(yList[0], x).setTextAlignment(Qt.AlignTop)  # 字幕居上
                    self.subtitle.setSpan(yList[0], x, yList[1] - yList[0] + 1, 1)  # 合并单元格
                    self.subtitle.item(yList[0], x).setBackground(QColor('#35545d'))  # 第一个单元格填上颜色即可
                    self.setSubtitleDict(yList[0], x, yList[1] - yList[0] + 1, firstItem, concat=True)  # 更新表格
        elif action == cutSpan:  # 切割
            y = yList[0]
            cutToken = False
            selectTime = int((y + self.row) * self.globalInterval)
            copySubtitleDict = copy.deepcopy(self.subtitleDict)
            for x in copySubtitleDict.keys():
                for start, subData in copySubtitleDict[x].items():
                    delta, text = subData
                    if selectTime >= start and selectTime <= start + delta:
                        cutToken = True
                        self.subtitleDict[x][start] = [selectTime - start, text]
                        self.subtitleDict[x][selectTime] = [start + delta - selectTime, text]
            if cutToken:
                scrollValue = self.subtitle.verticalScrollBar().value()
                self.refreshTable(int(self.row * self.globalInterval), y, scrollValue)
                self.refreshGraph(True)
                self.updateBackend()
        elif action == clrSpan:  # 拆分
            clearToken = False
            for x in xList:
                startList = sorted(self.subtitleDict[x].keys())  # 对起始时间排序
                for cnt, start in enumerate(startList):
                    delta, text = self.subtitleDict[x][start]
                    selectList = [int((y + self.row) * self.globalInterval) for y in range(yList[0], yList[1] + 1)]
                    for select in selectList:
                        if select >= start and select < start + delta:  # 确认选中的轴
                            clearToken = True
                            for i in range(int(delta / self.globalInterval)):
                                self.subtitleDict[x][start] = [int(self.globalInterval), text]
                                start += int(self.globalInterval)
            if clearToken:
                scrollValue = self.subtitle.verticalScrollBar().value()
                self.refreshTable(int(self.row * self.globalInterval), yList[0], scrollValue)
                self.updateBackend()
                self.refreshGraph(True)
        elif action == addSub:  # 添加字幕
            for x in xList:
                self.addSubtitle(x)
                break  # 只添加选中的第一列
        elif action == replay:  # 循环播放
            self.replay = 1
            self.playRange = [int((yList[0] + self.row) * self.globalInterval),
                              int((yList[1] + self.row + 1) * self.globalInterval)]
        elif action == cancelReplay:  # 取消循环
            self.replay = 0
            self.playRange = [0, self.duration]

    def sendSubtitleToAssCheck(self):
        styles = self.videoDecoder.returnSubDictStyle()
        self.assCheck.setDefault(self.subtitleDict, styles)  # 检查字幕里的刷新

    def setPlayerPosition(self, position):  # 响应检查表格里的双击
        self.player.setPosition(position)
        self.player_vocal.setPosition(position)
        self.videoSlider.setValue(position * self.videoSlider.width() // self.player.duration())
        self.setTimeLabel(position)
        self.refreshTable(position)

    def setToolBar(self):
        '''
        menu bar, file menu, play menu, tool bar.
        '''
        toolBar = QToolBar()
        self.setContextMenuPolicy(Qt.NoContextMenu)
        self.addToolBar(toolBar)
        fileMenu = self.menuBar().addMenu('&文件')
        openAction = QAction(QIcon.fromTheme('document-open'), '&打开...', self, shortcut=QKeySequence.Open, triggered=self.open)
        fileMenu.addAction(openAction)
        downloadAction = QAction(QIcon.fromTheme('document-open'), '&Youtube下载器', self, triggered=self.popDnld)
        fileMenu.addAction(downloadAction)
        exitAction = QAction(QIcon.fromTheme('application-exit'), '&退出', self, shortcut='Ctrl+Q', triggered=self.close)
        fileMenu.addAction(exitAction)

        playMenu = self.menuBar().addMenu('&功能')
        self.playIcon = self.style().standardIcon(QStyle.SP_MediaPlay)
        self.pauseIcon = self.style().standardIcon(QStyle.SP_MediaPause)
        self.playAction = toolBar.addAction(self.playIcon, '播放')
        self.playAction.triggered.connect(self.mediaPlay)
        self.volumeIcon = self.style().standardIcon(QStyle.SP_MediaVolume)
        self.volumeMuteIcon = self.style().standardIcon(QStyle.SP_MediaVolumeMuted)
        self.volumeAction = toolBar.addAction(self.volumeIcon, '静音')
        self.volumeAction.triggered.connect(self.volumeMute)
        separateAction = QAction(QIcon.fromTheme('document-open'), '&AI自动打轴', self, triggered=self.popSeparate)
        playMenu.addAction(separateAction)
        previewAction = QAction(QIcon.fromTheme('document-open'), '&设置字幕样式', self, triggered=self.decode)
        playMenu.addAction(previewAction)
        anime4KAction = QAction(QIcon.fromTheme('document-open'), '&Anime4K画质扩展', self, triggered=self.popAnime4K)
        playMenu.addAction(anime4KAction)
        reloadVideo = QAction(QIcon.fromTheme('document-open'), '&尝试解决字幕卡死', self, triggered=self.reloadVideo)
        playMenu.addAction(reloadVideo)

        decodeMenu = self.menuBar().addMenu('&输出')
        decodeAction = QAction(QIcon.fromTheme('document-open'), '&输出字幕及视频', self, triggered=self.decode)
        decodeMenu.addAction(decodeAction)

        helpMenu = self.menuBar().addMenu('&帮助')
        settingAction = QAction(QIcon.fromTheme('document-open'), '&设置', self, triggered=self.popSettingPage)
        helpMenu.addAction(settingAction)
        tutorialAction = QAction(QIcon.fromTheme('document-open'), '&B站教程', self, triggered=self.popTutorial)
        helpMenu.addAction(tutorialAction)
        releasesAction = QAction(QIcon.fromTheme('document-open'), '&版本更新', self, triggered=self.popReleases)
        helpMenu.addAction(releasesAction)
        helpInfoAction = QAction(QIcon.fromTheme('document-open'), '&快捷键说明', self, triggered=self.popHotKeyInfo)
        helpMenu.addAction(helpInfoAction)

        payMenu = self.menuBar().addMenu('&赞助')
        payAction = QAction(QIcon.fromTheme('document-open'), '&赞助和打赏', self, triggered=self.popPayment)
        payMenu.addAction(payAction)

        self.volSlider = Slider()
        self.volSlider.setOrientation(Qt.Horizontal)
        self.volSlider.setMinimum(0)
        self.volSlider.setMaximum(100)
        self.volSlider.setFixedWidth(120)
        self.volSlider.setValue(self.player.volume())
        self.volSlider.setToolTip(str(self.volSlider.value()))
        self.volSlider.pointClicked.connect(self.setVolume)
        toolBar.addWidget(self.volSlider)

        self.videoPositionEdit = LineEdit('00:00')
        self.videoPositionEdit.setAlignment(Qt.AlignRight)
        self.videoPositionEdit.setFixedWidth(75)
        self.videoPositionEdit.setFont(QFont('Timers', 14))
        self.videoPositionEdit.setReadOnly(True)
        self.videoPositionEdit.clicked.connect(self.mediaPauseOnly)
        self.videoPositionEdit.editingFinished.connect(self.mediaPlayOnly)
        self.videoPositionLabel = QLabel(' / 00:00  ')
        self.videoPositionLabel.setFont(QFont('Timers', 14))
        toolBar.addWidget(QLabel('    '))
        toolBar.addWidget(self.videoPositionEdit)
        toolBar.addWidget(self.videoPositionLabel)


        self.videoSlider = Slider()
        self.videoSlider.setEnabled(False)
        self.videoSlider.setOrientation(Qt.Horizontal)
        self.videoSlider.setFixedWidth(self.width() * 0.8)
        self.videoSlider.setMaximum(self.videoSlider.width())
        self.videoSlider.sliderMoved.connect(self.timeStop)
        self.videoSlider.sliderReleased.connect(self.timeStart)
        self.videoSlider.pointClicked.connect(self.videoSliderClick)
        toolBar.addWidget(self.videoSlider)

        toolBar.addWidget(QLabel('  '))
        self.playRateComBox = QComboBox()
        self.playRateComBox.addItems(['倍速 x0.1', '倍速 x0.25', '倍速 x0.5', '倍速 x0.75', '倍速 x1',
                                      '倍速 x1.25', '倍速 x1.5', '倍速 x1.75', '倍速 x2'])
        self.playRateComBox.setCurrentIndex(4)
        self.playRateComBox.currentIndexChanged.connect(self.setPlayRate)
        toolBar.addWidget(self.playRateComBox)
        toolBar.addWidget(QLabel('  '))
        self.globalIntervalComBox = QComboBox()
        self.globalIntervalComBox.addItems(['间隔 10ms', '间隔 16ms(60FPS)', '间隔 20ms', '间隔 33ms(30FPS)',
                                            '间隔 50ms(20FPS)', '间隔 100ms', '间隔 200ms', '间隔 500ms', '间隔 1s'])
        self.globalIntervalComBox.setCurrentIndex(3)
        self.globalIntervalComBox.currentIndexChanged.connect(self.setGlobalInterval)
        toolBar.addWidget(self.globalIntervalComBox)
        toolBar.addWidget(QLabel('  '))
        self.subEditComBox = QComboBox()
        for i in range(self.subtitle.columnCount()):
            self.subEditComBox.addItem('字幕 ' + str(i + 1))
        toolBar.addWidget(self.subEditComBox)
        toolBar.addWidget(QLabel('  '))
        addSub = QPushButton('导入')
        addSub.setFixedWidth(50)
        addSub.setFixedHeight(31)
        toolBar.addWidget(addSub)
        toolBar.addWidget(QLabel('  '))
        clearSub = QPushButton('清空')
        clearSub.setFixedWidth(50)
        clearSub.setFixedHeight(31)
        toolBar.addWidget(clearSub)
        toolBar.addWidget(QLabel('  '))
        addSub.clicked.connect(lambda: self.addSubtitle(self.subEditComBox.currentIndex()))
        clearSub.clicked.connect(self.clearSub)

    def setGlobalInterval(self, index):  # 设置全局间隔
        if not self.playStatus:
            self.mediaPlay()
        self.globalInterval = {0: 10, 1: 50 / 3, 2: 20, 3: 100 / 3, 4: 50, 5: 100, 6: 200, 7: 500, 8: 1000}[index]
        if self.globalInterval > self.tableRefreshLimit:
            self.timer.setInterval(self.globalInterval)
        else:
            self.timer.setInterval(self.tableRefreshLimit)
        self.refreshTable()

    def setPlayRate(self, index):  # 倍速功能
        playRate = {0: 0.1, 1: 0.25, 2: 0.5, 3: 0.75, 4: 1, 5: 1.25, 6: 1.5, 7: 1.75, 8: 2}[index]
        self.player.setPlaybackRate(playRate)
        self.player_vocal.setPlaybackRate(playRate)

    def clearSub(self):
        row = self.subEditComBox.currentIndex()
        reply = QMessageBox.information(self, '清空字幕', '清空第 %s 列字幕条？' % (row + 1), QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.subtitleDict[row] = {}
            self.updateBackend()
            self.refreshTable()

    def exportSubWindow(self, start=0, end=0, index=None):
        self.releaseKeyboard()
        self.exportWindow.hide()
        self.exportWindow.show()
        start = '00:00.0' if not start else splitTime(start)
        end = splitTime(self.duration) if not end else splitTime(end)
        if not index:
            index = self.subEditComBox.currentIndex() + 1
        self.exportWindow.setDefault(start, end, index)

    def exportSubtitle(self, exportArgs):
        videostart = calSubTime2(exportArgs[0])
        videoend = calSubTime2(exportArgs[1])
        subStart = calSubTime2(exportArgs[2])
        index = exportArgs[3] - 1
        subData = self.subtitleDict[index]
        rowList = sorted(subData.keys())
        exportRange = []
        for t in rowList:
            if t >= videostart and t <= videoend:
                exportRange.append(t)
        subNumber = 1
        if exportArgs[-1]:  # 有效路径
            with open(exportArgs[-1], 'w', encoding='utf-8') as exportFile:
                for t in exportRange:
                    text = subData[t][1]
                    if text:
                        start = ms2SRTTime(t - videostart + subStart)
                        end = ms2SRTTime(t - videostart + subStart + subData[t][0])
                        exportFile.write('%s\n%s --> %s\n%s\n\n' % (subNumber, start, end, text))
                        subNumber += 1
            QMessageBox.information(self, '导出字幕', '导出完成', QMessageBox.Yes)
            self.exportWindow.hide()

    def open(self):
        self.videoPath = QFileDialog.getOpenFileName(self,"请选择视频文件", None,
        "视频文件 (*.mp4 *.avi *.flv);;音频文件 (*.mp3 *.wav *.aac);;所有文件 (*.*)")[0]
        if self.videoPath:
            self.openVideo(self.videoPath)

    def openVideo(self, videoPath):
        self.videoPath = videoPath
        if not self.saveToken:
            reply = QMessageBox.information(self, '字幕文件未保存', '是否保存字幕？', QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            if reply == QMessageBox.Yes:
                self.videoDecoder.hide()
                self.videoDecoder.show()  # 弹出输出保存界面
            elif reply == QMessageBox.No:
                if self.subPreview:
                    os.remove(self.subPreview)  # 删除预览字幕文件
                    if self.backupASS:
                        originalASS = os.path.splitext(self.videoPath)[0] + '.ass'
                        try:
                            os.rename(self.backupASS, originalASS)  # 将备份ass文件改回去
                        except:
                            pass
                self.saveToken = True
            elif reply == QMessageBox.Cancel:
                self.saveToken = False
        if self.saveToken:
            for f in os.listdir('temp_audio'):
                os.remove('temp_audio\%s' % f)
            cmd = ['ffmpeg.exe', '-i', videoPath]
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            p.wait()
            try:
                for l in p.stdout.readlines():  # FFMpeg这蛋疼的视频信息格式
                    l = l.decode('gb18030', 'ignore')
                    if 'Duration' in l:
                        self.duration = calSubTime(l.split(' ')[3][:-1])
                        self.bitrate = int(l.split(' ')[-2])
                    if 'Stream' in l and 'DAR' in l:
                        args = l.split(',')
                        for resolution in args[2:5]:
                            resolution = resolution.replace(' ', '')
                            if '[' in resolution:
                                resolution = resolution.split('[')[0]
                            if 'x' in resolution:
                                self.videoWidth, self.videoHeight = map(int, resolution.split('x'))
                        for arg in args:
                            if 'fps' in arg:
                                self.fps = float(arg.split('fps')[0])
                        break
            except:
                self.duration = 114514  # 万一读取不上来视频长度就先随便分配个 之后在timeout修正
            # 向输出页面发送视频信息
            self.videoDecoder.setDefault(videoPath, self.videoWidth, self.videoHeight, self.duration,
                                         self.bitrate, self.fps, self.subtitleDict, self.styleNameList)
            self.subPreview = os.path.splitext(videoPath)[0]  # 设置主界面实时预览字幕路径 采用k-lite解码器读取视频目录下同名的ass文件来加载
            if os.path.exists(self.subPreview + '.ass'):  # 防止覆盖已存在的ass文件 若有 复制一个备份
                with codecs.open(self.subPreview + '.ass', 'r', 'utf_8_sig') as sub:
                    sub = sub.readlines()
                if os.path.getsize(self.subPreview + '.ass') != 682 or len(sub) != 20:  # 字幕文件大小不等于烤肉机默认输出大小或行数不等于20
                    self.backupASS = '%s_备份_%s.ass' % (self.subPreview, time.strftime("%H%M%S", time.localtime()))
                    shutil.copy(self.subPreview + '.ass', self.backupASS)
            else:
                self.backupASS = ''
            self.subPreview += '.ass'
            self.videoDecoder.writeAss(self.subPreview, False, True)  # 创建空白文件
            self.position = 0
            self.oldPosition = 0
            url = QUrl.fromLocalFile(videoPath)
            self.stack.setCurrentIndex(1)
            self.player.stop()
            self.player.setMedia(url)
            self.player.setPlaybackRate(1)
            self.playStatus = True
            self.saveToken = False
            self.videoSlider.setEnabled(True)
            w, h = self.videoWindowSizePreset[self.videoWindowSizeIndex]
            self.stack.setFixedSize(w, h)
            self.view.setFixedSize(w, h)
            self.scene.setSceneRect(5, 5, w - 10, h - 10)
            self.playerWidget.setSize(QSizeF(w, h))
            self.playRange = [0, self.duration]  # 播放范围
            if self.sepMain.isRunning:  # 检测上一个视频的切片主音频进程是否还在进行
                self.sepMain.terminate()
                self.sepMain.quit()
                self.sepMain.wait()
            self.sepMain = sepMainAudio(videoPath, self.duration)  # 开始切片主音频
            self.sepMain.mainAudioWave.connect(self.addMainAudioWave)
            self.sepMain.start()
            self.refreshMainAudioToken = False  # 刷新主音频
            self.mainAudioWaveX = []
            self.mainAudioWaveY = []
            self.refreshVoiceToken = False  # 刷新AI识别人声音频
            self.voiceWaveX = []
            self.voiceWaveY = []
            self.bgmWaveY = []
            self.secondeMedia = False  # False: 播放原音轨；True: 播放第二音轨
            self.voiceMedia = True  # True: 人声音轨；False: BGM音轨
            self.mainAudio.plot([0], [0], 0, 1)
            self.voiceAudio.plot([0], [0], True, 0, 1)
            self.mediaPlay()
            self.timer.stop()
            self.subTimer.stop()
            self.graphTimer.stop()
            try:  # 尝试断开三个timer
                self.timer.timeout.disconnect(self.timeOut)
            except:
                pass
            try:
                self.subTimer.timeout.disconnect(self.subTimeOut)
            except:
                pass
            try:
                self.graphTimer.timeout.disconnect(self.refreshGraph)
            except:
                pass
            self.timer.start()
            self.timer.timeout.connect(self.timeOut)
            self.subTimer.start()
            self.subTimer.timeout.connect(self.subTimeOut)
            self.graphTimer.start()  # 音频图timer启动
            self.graphTimer.timeout.connect(self.refreshGraph)

    def changeSetting(self, settingDict):  # 配置设置参数
        self.settingDict = settingDict
        self.tableRefresh = [True, False][int(settingDict['tableRefresh'])]
        self.redLineLeft = [10 * x for x in range(11)][int(settingDict['redLinePos'])]
        self.redLineRight = 100 - self.redLineLeft
        self.tableRefreshLimit = [15, 30, 50, 100][int(settingDict['tableRefreshFPS'])]
        self.timer.setInterval(self.tableRefreshLimit)
        self.graphTimer.setInterval([15, 30, 50, 100][int(settingDict['graphRefreshFPS'])])

    def popDnld(self):
        self.releaseKeyboard()
        self.dnldWindow.hide()
        self.dnldWindow.show()

    def popPreview(self):
        self.releaseKeyboard()
        self.previewSubtitle.hide()
        self.previewSubtitle.show()

    def popSeparate(self):
        self.releaseKeyboard()
        self.separate.setDefault(self.videoPath, self.duration, self.subtitleDict)
        self.separate.hide()
        self.separate.show()

    def popAnime4K(self):
        self.releaseKeyboard()
        self.anime4KWindow.setDefault(self.videoPath, self.duration, self.videoWidth, self.videoHeight)
        self.anime4KWindow.hide()
        self.anime4KWindow.show()

    def reloadVideo(self):
        position = self.player.position()
        self.player.stop()
        self.player.setMedia(QUrl.fromLocalFile(''))
        self.player.stop()
        self.player.setMedia(QUrl.fromLocalFile(self.videoPath))
        self.player.setPosition(position)

    def addMainAudioWave(self, x, y):  # 添加主音频数据
        self.mainAudioWaveX = x
        self.mainAudioWaveY = y
        self.mainAudioMax = max(self.mainAudioWaveY) // 100 * 50  # 50%
        self.refreshMainAudioToken = True

    def addVoiceWave(self, x, y, bgm):  # 添加人声音轨
        self.voiceWaveX = x
        self.voiceWaveY = y
        self.bgmWaveY = bgm
        self.refreshVoiceToken = True

    def refreshGraph(self, force=False):
        position = self.player.position()
        step = int(self.globalInterval / 100) + 1  # 波形列表切片步长
        if self.oldPosition != position or self.oldGlobalInterval != self.globalInterval or force:
            self.oldPosition = position
            self.oldGlobalInterval = self.globalInterval
            if self.refreshMainAudioToken:  # 绘制主音频波形
                pos = int((position / self.duration) * len(self.mainAudioWaveX))
                if pos > len(self.mainAudioWaveX):
                    pos = len(self.mainAudioWaveX) - int(self.globalInterval * self.redLineRight) - 1
                start = pos - int(self.globalInterval * self.redLineLeft)
                if start < 0:
                    start = 0
                start = start // step * step
                end = pos + int(self.globalInterval * self.redLineRight)  # 显示当前间隔x100的区域
                if end > len(self.mainAudioWaveX):
                    end = len(self.mainAudioWaveX)
                end = end // step * step
                xList = self.mainAudioWaveX[start:end:step]
                yList = self.mainAudioWaveY[start:end:step]
                subtitleLine = {0: [], 1: [], 2: [], 3: [], 4: []}
                for x, subData in self.subtitleDict.items():
                    for sub_start in subData.keys():
                        sub_end = sub_start + subData[sub_start][0]
                        if (sub_start > start and sub_start < end) or (sub_end > start and sub_end < end) or\
                           (sub_start < start and sub_end > end):
                            subtitleLine[x].append([sub_start, sub_end])
                self.mainAudio.mp3Path = os.path.join(self.dir, r'temp_audio\audio_original.aac')
                self.mainAudio.plot(xList, yList, position, step, [-self.mainAudioMax, self.mainAudioMax], subtitleLine)

            if self.refreshVoiceToken:  # 绘制AI产生的人声波形
                pos = int((position / self.duration) * len(self.voiceWaveX))
                if pos > len(self.voiceWaveX):
                    pos = len(self.voiceWaveX) - int(self.globalInterval * self.redLineRight) - 1
                start = pos - int(self.globalInterval * self.redLineLeft)
                if start < 0:
                    start = 0
                start = start // step * step
                end = pos + int(self.globalInterval * self.redLineRight)  # 显示当前间隔x100的区域
                if end > len(self.voiceWaveX):
                    end = len(self.voiceWaveX)
                end = end // step * step
                xList = self.voiceWaveX[start:end:step]
                if self.voiceMedia:
                    yList = self.voiceWaveY[start:end:step]
                    # mp3Path = os.path.join(self.dir, r'temp_audio\vocals.mp3')
                else:
                    yList = self.bgmWaveY[start:end:step]
                    # mp3Path = os.path.join(, r'temp_audio\bgm.mp3')
                self.voiceAudio.mp3Path = self.dir + r'\temp_audio'
                self.voiceAudio.plot(xList, yList, self.voiceMedia, position, step,
                                     [-self.mainAudioMax, self.mainAudioMax], subtitleLine)

    def playMainAudio(self):  # 播放主音频
        # if not self.playStatus:
        self.secondeMedia = False
        self.player_vocal.setMuted(True)
        self.player.setMuted(False)

    def playVocal(self):  # 播放人声音频
        if os.path.exists(r'temp_audio\vocals.mp3') and self.videoPath:
            self.player.setMuted(True)
            self.player_vocal.setMuted(False)
            if not self.secondeMedia:  # 从原音轨切换至第二音轨
                self.secondeMedia = not self.secondeMedia
                if self.player_vocal.mediaStatus() == QMediaPlayer.MediaStatus.NoMedia:
                    url = QUrl.fromLocalFile(r'temp_audio\vocals.mp3')
                    self.player_vocal.setMedia(url)
            else:  # 第二音轨在人声音轨和背景音轨之间来回切换
                if self.voiceMedia:  # 人声音轨切换至背景音轨
                    url = QUrl.fromLocalFile(r'temp_audio\bgm.mp3')
                    self.player_vocal.setMedia(url)
                else:  # 背景音轨切换至人声音轨
                    url = QUrl.fromLocalFile(r'temp_audio\vocals.mp3')
                    self.player_vocal.setMedia(url)
                self.voiceMedia = not self.voiceMedia
                self.refreshGraph(True)
            self.player_vocal.setPosition(self.player.position())
            if not self.playStatus:
                self.player_vocal.play()
            else:
                self.player_vocal.pause()

    def setTablePreset(self, preset):
        self.tablePreset = preset  # 填充字符 输出列

    def clearSubtitle(self, index, videoStart, videoEnd):  # 清空字幕轴
        startTime = videoStart * 60000
        endTime = videoEnd * 60000
        subtitle = copy.deepcopy(self.subtitleDict[index])
        for start, subData in subtitle.items():
            end = start + subData[0]
            if start >= startTime and start <= endTime or end >= startTime and end <= endTime:  # 判断是否落在所选范围内
                del self.subtitleDict[index][start]
        self.updateBackend()
        self.refreshTable()

    def setAutoSubtitle(self, voiceList):  # AI自动打轴更新至字幕字典里
        for t in voiceList:
            start, delta = t
            txt, index = self.tablePreset
            self.subtitleDict[index][start] = [delta, txt]
        self.updateBackend()
        self.refreshTable()  # 刷新表格
        self.refreshSubPreview()

    def updateTranslateResult(self, result):
        start, delta, source, target, sourceIndex, targetIndex = result  # 更新翻译结果至字典里
        if sourceIndex != 5:
            self.subtitleDict[sourceIndex][start] = [delta, source]
        self.subtitleDict[targetIndex][start] = [delta, target]
        self.refreshTable()  # 刷新表格
        self.refreshSubPreview()

    def decode(self):
        self.releaseKeyboard()
        self.videoDecoder.setDefault(self.videoPath, self.videoWidth, self.videoHeight, self.duration,
                                     self.bitrate, self.fps, self.subtitleDict, self.styleNameList)
        self.videoDecoder.hide()
        self.videoDecoder.show()

    def popPayment(self):
        self.pay.hide()
        self.pay.show()

    def popHotKeyInfo(self):
        self.hotKeyInfo.hide()
        self.hotKeyInfo.show()

    def popSettingPage(self):
        self.setting.hide()
        self.setting.show()

    def popTutorial(self):
        QDesktopServices.openUrl(QUrl('https://www.bilibili.com/video/BV1p5411b7o7'))

    def popReleases(self):
        self.releases.hide()
        self.releases.show()

    def mediaPlay(self):
        if self.playStatus:
            self.stack.setCurrentIndex(1)
            self.player.play()
            try:
                self.player_vocal.play()
            except:
                pass
            self.grabKeyboard()
            self.timeStart()
            self.playStatus = False
            self.playAction.setIcon(self.pauseIcon)
            self.playAction.setText('暂停')
        else:
            self.player.pause()
            try:
                self.player_vocal.pause()
            except:
                pass
            self.timeStop()
            self.playStatus = True
            self.playAction.setIcon(self.playIcon)
            self.playAction.setText('播放')

    def mediaPlayOnly(self):
        self.grabKeyboard()
        try:
            timeText = self.videoPositionEdit.text().replace('：', ':').split(':')
            m, s = timeText[:2]
            if not m:
                m = '00'
            if not s:
                s = '00'
            if len(m) > 3:
                m = m[:3]
            if len(s) > 2:
                s = s[:2]
            m = int(m)
            s = int(s)
            if s > 60:
                s = 60
            total_m = self.player.duration() // 60000
            if m > total_m:
                m = total_m
            self.player.setPosition(m * 60000 + s * 1000)
            self.player_vocal.setPosition(m * 60000 + s * 1000)
            # self.videoSlider.setValue(self.player.position() * self.videoSlider.width() / self.player.duration())
        except:
            pass
        self.videoPositionEdit.setReadOnly(True)
        self.videoSlider.setValue(self.player.position() * self.videoSlider.width() // self.player.duration())

    def mediaPauseOnly(self):
        self.releaseKeyboard()
        self.videoPositionEdit.setReadOnly(False)
        self.player.pause()
        self.timeStop()
        self.playStatus = True
        self.playAction.setIcon(self.playIcon)
        self.playAction.setText('播放')

    def timeOut(self):
        if self.duration == 114514 or not self.duration:
            self.duration = self.player.duration()
        position = 0
        if self.player.position() <= self.playRange[0] or self.player.position() >= self.playRange[1]:  # 循环播放
            if self.player.position() >= self.playRange[1] and self.replay == 2: # 单次播放超出范围
                position = self.playRange[0]
                self.player.setPosition(position)
                self.player_vocal.setPosition(position)
                self.videoSlider.setValue(position * self.videoSlider.width() // self.player.duration())
                self.setTimeLabel(position)
                self.replay = 0  # 恢复播放范围
                self.playRange = [0, self.duration]
                if not self.playStatus:
                    self.mediaPlay()
            else:
                self.player.setPosition(self.playRange[0])
                self.player_vocal.setPosition(self.playRange[0])
        self.refreshTable(position)
        try:
            self.videoSlider.setValue(self.player.position() * self.videoSlider.width() / self.player.duration())
            self.setTimeLabel()
        except:
            pass

    def timeStop(self):
        self.timer.stop()

    def timeStart(self):
        self.timer.start()

    def videoSliderClick(self, p):
        x = p.x()
        if x < 0:  # 限制
            x = 0
        if x > self.videoSlider.width():
            x = self.videoSlider.width()
        self.videoSlider.setValue(x)
        position = x * self.duration // self.videoSlider.width()
        self.player.setPosition(position)
        self.player_vocal.setPosition(position)
        self.refreshTable(position)
        self.setTimeLabel(position)

    def setVolume(self, p):
        self.volumeValue = p.x()
        if self.volumeValue > 100:
            self.volumeValue = 100
        if self.volumeValue < 0:
            self.volumeValue = 0
        self.volSlider.setValue(self.volumeValue)
        self.player.setVolume(self.volumeValue)
        self.player_vocal.setVolume(self.volumeValue)
        self.volSlider.setToolTip(str(self.volSlider.value()))
        if self.volumeValue:
            self.volumeStatus = True
            self.volumeAction.setIcon(self.volumeIcon)
        else:
            self.volumeStatus = False
            self.volumeAction.setIcon(self.volumeMuteIcon)

    def volumeMute(self):
        if self.volumeStatus:
            self.volumeStatus = False
            self.old_volumeValue = self.player.volume()
            self.player.setVolume(0)
            self.volSlider.setValue(0)
            self.volumeAction.setIcon(self.volumeMuteIcon)
        else:
            self.volumeStatus = True
            self.player.setVolume(self.old_volumeValue)
            self.volSlider.setValue(self.old_volumeValue)
            self.volumeAction.setIcon(self.volumeIcon)

    def setTimeLabel(self, pos=0):
        if not pos:
            now = splitTime(self.player.position())
        else:
            now = splitTime(pos)
        total = splitTime(self.player.duration())
        self.videoPositionEdit.setText(now)
        self.videoPositionLabel.setText(' / %s  ' % total)

    def setSaveToken(self, token):
        self.saveToken = token

    def eventFilter(self, obj, event):
        if obj == self.subtitle.verticalScrollBar():  # 过滤表格滚轮事件 用于刷新超出表格视窗范围的滚动
            if event.type() == QEvent.Wheel:
                scrollBarValue = self.subtitle.verticalScrollBar().value()
                if scrollBarValue == self.oldScrollBarValue:
                    delta = event.delta() // 30  # 滚轮四倍速！！！（120 / 30）
                    if scrollBarValue > 0 and delta < 0:  # 向下滚动超出范围
                        self.position -= int(delta * self.globalInterval)  # 前进3行 同时重置视频进度及刷新
                        if self.position > self.duration:
                            self.position = int(self.duration - self.globalInterval)
                        self.player.setPosition(self.position)
                        self.player_vocal.setPosition(self.position)
                        self.videoSlider.setValue(self.position * self.videoSlider.width() / self.duration)
                        self.refreshTable(self.position, scroll=scrollBarValue)  # 向下滚的时候选择要特殊处理下
                        self.setTimeLabel(self.position)
                    elif scrollBarValue == 0 and delta > 0:  # 向上滚动超出范围
                        self.position = self.player.position() - int(delta * self.globalInterval)  # 倒退3行 同时重置视频进度及刷新
                        if self.position < 0:
                            self.position = 0
                        self.player.setPosition(self.position)
                        self.player_vocal.setPosition(self.position)
                        self.videoSlider.setValue(self.position * self.videoSlider.width() / self.duration)
                        self.refreshTable(self.position)
                        self.setTimeLabel(self.position)
                self.oldScrollBarValue = scrollBarValue
        elif obj == self.view:  # 点击视频窗口播放/暂停
            if event.type() == QEvent.MouseButtonPress:
                self.mediaPlay()
        return QMainWindow.eventFilter(self, obj, event)

    def closeEvent(self, QCloseEvent):  # 重写关闭函数 捕获关闭主界面信号 删除临时字幕
        if not self.saveToken:
            reply = QMessageBox.information(self, '字幕文件未保存', '是否保存字幕？', QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            if reply == QMessageBox.Yes:
                QCloseEvent.ignore()
                self.videoDecoder.hide()
                self.videoDecoder.show()  # 弹出输出保存界面
            elif reply == QMessageBox.No:
                if self.subPreview:
                    os.remove(self.subPreview)  # 删除预览字幕文件
                    if self.backupASS:
                        originalASS = os.path.splitext(self.videoPath)[0] + '.ass'
                        os.rename(self.backupASS, originalASS)  # 将备份ass文件改回去
                for wind in [self.dnldWindow, self.exportWindow, self.videoDecoder, self.separate, self.editStyleNameDialog]:
                    if not wind.isHidden():
                        wind.hide()
                QCloseEvent.accept()
            elif reply == QMessageBox.Cancel:
                QCloseEvent.ignore()
        else:
            for wind in [self.dnldWindow, self.exportWindow, self.videoDecoder, self.separate, self.editStyleNameDialog]:
                    if not wind.isHidden():
                        wind.hide()

    def dragEnterEvent(self, QDragEnterEvent):  # 启用拖入文件功能
        QDragEnterEvent.accept()

    def dropEvent(self, QEvent):  # 检测拖入的文件
        if QEvent.mimeData().hasUrls:
            dropFile = QEvent.mimeData().urls()[0].toLocalFile()
            _, format = os.path.splitext(dropFile)
            if format in ['.ass', '.srt', '.vtt', '.lrc']:
                self.addSubtitle(self.subEditComBox.currentIndex(), dropFile)
            else:
                self.openVideo(dropFile)

    def keyPressEvent(self, QKeyEvent):
        key = QKeyEvent.key()
        if key == Qt.Key_Left:
            if self.videoSlider.isEnabled():
                self.position = self.player.position() - self.globalInterval  # ←键倒退1行 同时重置视频进度及刷新
                if self.position < 0:
                    self.position = 0
                self.player.setPosition(self.position)
                self.player_vocal.setPosition(self.position)
                self.videoSlider.setValue(self.position * self.videoSlider.width() / self.duration)
                self.refreshTable(self.position)
                self.setTimeLabel(self.position)
        elif key == Qt.Key_Right:
            if self.videoSlider.isEnabled():
                self.position = self.player.position() + self.globalInterval  # →键前进1行 同时重置视频进度及刷新
                if self.position > self.duration:
                    self.position = self.duration - self.globalInterval
                self.player.setPosition(self.position)
                self.player_vocal.setPosition(self.position)
                self.videoSlider.setValue(self.position * self.videoSlider.width() / self.duration)
                self.refreshTable(self.position)
                self.setTimeLabel(self.position)
        elif key == Qt.Key_Up:  # ↑键跳转至上一条字幕
            y = self.subtitle.selectionModel().selection().indexes()[0].row()
            position = int((y + self.row) * self.globalInterval)
            startList = []
            for subDict in self.subtitleDict.values():
                startList += list(subDict.keys())
            startList = sorted(startList)
            if len(startList) > 1:
                refreshToken = False
                for cnt, i in enumerate(startList[1:]):
                    if i >= position:
                        self.position = startList[cnt]
                        position = startList[cnt] - 10 * self.globalInterval  # 预留10行
                        refreshToken = True
                        break
                if not refreshToken:
                    self.position = startList[-1]
                    position = startList[-1] - 10 * self.globalInterval  # 预留10行
                self.refreshTable(position, select=10)  # 刷新表格
                self.subHeaderClick(10)  # 重置当前视频时间
                self.refreshGraph(True)
        elif key == Qt.Key_Down:  # ↓键跳转至下一条字幕
            y = self.subtitle.selectionModel().selection().indexes()[0].row()
            position = int((y + self.row) * self.globalInterval)
            startList = []
            for subDict in self.subtitleDict.values():
                startList += list(subDict.keys())
            startList = sorted(startList)
            if len(startList) > 1:
                refreshToken = False
                for cnt, i in enumerate(startList):
                    if i > position:
                        self.position = startList[cnt]
                        position = startList[cnt] - 10 * self.globalInterval  # 预留10行
                        refreshToken = True
                        break
                if not refreshToken:
                    self.position = startList[-1]
                    position = startList[-1] - 10 * self.globalInterval  # 预留10行
                self.refreshTable(position, select=10)  # 刷新表格
                self.subHeaderClick(10)  # 重置当前视频时间
                self.refreshGraph(True)
        elif key == Qt.Key_Space:  # 空格暂停/播放 需要主界面处于grabkeyboard状态
            self.mediaPlay()
        elif key == Qt.Key_Delete:  # 删除选择字幕 等效右键菜单删除
            selected = self.subtitle.selectionModel().selection().indexes()
            xList = []  # 选中行
            for i in range(len(selected)):
                x = selected[i].column()
                if x not in xList:  # 剔除重复选择
                    xList.append(x)
            yList = [selected[0].row(), selected[-1].row()]
            selectRange = [int((y + self.row) * self.globalInterval) for y in yList]
            for x in xList:
                startList = sorted(self.subtitleDict[x].keys())
                for start in startList:
                    end = self.subtitleDict[x][start][0] + start
                    for position in range(selectRange[0], selectRange[-1] + 1):
                        if start <= position and position < end:
                            try:
                                del self.subtitleDict[x][start]
                            except:
                                pass
            for x in xList:
                for y in range(yList[0], yList[1] + 1):
                    if self.subtitle.item(y, x):
                        self.subtitle.setSpan(y, x, 1, 1)
                        self.subtitle.setItem(y, x, QTableWidgetItem(''))
                        self.subtitle.item(y, x).setBackground(QColor('#232629'))  # 没内容颜色
            self.updateBackend()
            self.refreshGraph(True)

        elif key in [Qt.Key_Q, Qt.Key_W, Qt.Key_E, Qt.Key_R, Qt.Key_1, Qt.Key_2, Qt.Key_3, Qt.Key_4]:
            self.graphTimer.stop()
            try:
                selected = self.subtitle.selectionModel().selection().indexes()
                x = selected[0].column()
                if len(selected) == 1:  # 特殊情况 当刚合并完后选择该单个单元格 选中的只有第一个格子 需要修正一下
                    y = selected[0].row()
                    yList = [y, y + self.subtitle.rowSpan(y, x) - 1]
                else:
                    yList = [selected[0].row(), selected[-1].row()]
                select = (yList[0] + self.row) * self.globalInterval
                startList = sorted(self.subtitleDict[x].keys())  # 对起始时间排序
                for cnt, start in enumerate(startList):
                    delta, text = self.subtitleDict[x][start]
                    if select >= start and select < start + delta:  # 确认选中的轴
                        if key in [Qt.Key_Q, Qt.Key_1]:
                            if start >= self.globalInterval:
                                if cnt > 0:
                                    preStart = startList[cnt - 1]  # 向前检测叠轴
                                    if start - self.globalInterval >= preStart + self.subtitleDict[x][preStart][0]:
                                        checkToken = 1
                                    elif start > preStart + self.subtitleDict[x][preStart][0]:
                                        checkToken = 2
                                    else:
                                        checkToken = 0
                                else:  # 第一条轴就跳过向前检测
                                    checkToken = 1
                                if checkToken:
                                    del self.subtitleDict[x][start]  # 删除旧轴
                                    if checkToken == 1:
                                        start -= int(self.globalInterval)  # 向前+1间隔时长
                                        self.position = start - int(10 * self.globalInterval)  # 预留10行
                                        self.subtitleDict[x][start] = [int(delta + self.globalInterval), text]  # 更新至字典
                                    elif checkToken == 2:
                                        end = delta + start
                                        start = preStart + self.subtitleDict[x][preStart][0]
                                        self.position = start - int(9 * self.globalInterval)  # 预留10行
                                        self.subtitleDict[x][start] = [end - start, text]  # 更新至字典
                                    self.refreshTable(self.position, select=10)  # 刷新表格
                                    self.subHeaderClick(10)  # 重置当前视频时间
                        elif key in [Qt.Key_W, Qt.Key_2]:
                            if delta > self.globalInterval:
                                del self.subtitleDict[x][start]  # 删除旧轴
                                start += int(self.globalInterval)  # 向后-1间隔时长
                                self.subtitleDict[x][start] = [int(delta - self.globalInterval), text]  # 更新至字典
                                self.position = start - int(10 * self.globalInterval)  # 预留10行
                                self.refreshTable(self.position, select=10)  # 刷新表格
                                self.subHeaderClick(10)  # 重置当前视频时间
                        elif key in [Qt.Key_E, Qt.Key_3]:
                            if delta > self.globalInterval:
                                self.subtitleDict[x][start] = [delta - int(self.globalInterval), text]  # 轴下沿上移间隔
                                self.position = start + delta - int(12 * self.globalInterval)  # 预留10行
                                self.refreshTable(self.position, select=10)  # 刷新表格
                                self.subHeaderClick(10)  # 重置当前视频时间
                        elif key in [Qt.Key_R, Qt.Key_4]:
                            if start + delta + self.globalInterval < self.duration:
                                if cnt < len(startList) - 1:  # 向后检测叠轴
                                    nxtStart = startList[cnt + 1]
                                    if start + delta + self.globalInterval <= nxtStart:
                                        checkToken = 1
                                    elif start + delta < nxtStart:
                                        checkToken = 2
                                    else:
                                        checkToken = 0
                                else:  # 最后一条轴就跳过向后检测
                                    checkToken = 1
                                if checkToken:
                                    if checkToken == 1:
                                        self.subtitleDict[x][start] = [int(delta + self.globalInterval), text]  # 轴下沿下移间隔
                                        self.position = int(start + delta - 10 * self.globalInterval)  # 预留10行
                                    elif checkToken == 2:
                                        self.subtitleDict[x][start] = [nxtStart - start, text]  # 轴下沿下移间隔
                                        self.position = int(start + delta - 11 * self.globalInterval)  # 预留10行
                                    self.refreshTable(self.position, select=10)  # 刷新表格
                                    self.subHeaderClick(10)  # 重置当前视频时间
                        self.subtitle.selectionModel().select(self.subtitle.model().index(10, x), QItemSelectionModel.ClearAndSelect)
                        self.updateBackend()
                        self.refreshGraph(True)
                        break
            except Exception as e:
                print(str(e))
            self.graphTimer.start()
        elif QKeyEvent.modifiers() == Qt.ControlModifier and key == Qt.Key_X:  # 剪切
            selected = self.subtitle.selectionModel().selection().indexes()
            xList = []  # 选中行
            for i in range(len(selected)):
                x = selected[i].column()
                if x not in xList:  # 剔除重复选择
                    xList.append(x)
            yList = [selected[0].row(), selected[-1].row()]
            selectRange = [int((y + self.row) * self.globalInterval) for y in range(yList[0], yList[1] + 1)]
            self.clipBoard = []
            for x in xList:
                for start, subData in self.subtitleDict[x].items():
                    end = subData[0] + start
                    for position in selectRange:
                        if start < position and position < end:
                            self.clipBoard.append([start, subData])
                            break
                for i in self.clipBoard:
                    start = i[0]
                    try:
                        del self.subtitleDict[x][start]
                    except:
                        pass
                for y in range(yList[0], yList[1] + 1):
                    if self.subtitle.item(y, x):
                        self.subtitle.setSpan(y, x, 1, 1)
                        self.subtitle.setItem(y, x, QTableWidgetItem(''))
                        self.subtitle.item(y, x).setBackground(QColor('#232629'))  # 没内容颜色
                break  # 只剪切选中的第一列
        elif QKeyEvent.modifiers() == Qt.ControlModifier and key == Qt.Key_C:  # 复制
            selected = self.subtitle.selectionModel().selection().indexes()
            xList = []  # 选中行
            for i in range(len(selected)):
                x = selected[i].column()
                if x not in xList:  # 剔除重复选择
                    xList.append(x)
            yList = [selected[0].row(), selected[-1].row()]
            selectRange = [int((y + self.row) * self.globalInterval) for y in range(yList[0], yList[1] + 1)]
            self.clipBoard = []
            for x in xList:
                for start, subData in self.subtitleDict[x].items():
                    end = subData[0] + start
                    for position in selectRange:
                        if start < position and position < end:
                            self.clipBoard.append([start, subData])
                            break
                break  # 只复制选中的第一列
        elif QKeyEvent.modifiers() == Qt.ControlModifier and key == Qt.Key_V:  # 粘贴
            selected = self.subtitle.selectionModel().selection().indexes()
            xList = []  # 选中行
            for i in range(len(selected)):
                x = selected[i].column()
                if x not in xList:  # 剔除重复选择
                    xList.append(x)
            yList = [selected[0].row(), selected[-1].row()]
            if self.clipBoard:
                clipBoard = []
                for i in self.clipBoard:
                    clipBoard.append([i[0] - self.clipBoard[0][0], i[1]])  # 减去复制的字幕的起始偏移量
                startOffset = int((yList[0] + self.row) * self.globalInterval)
                for x in xList:
                    for subData in clipBoard:
                        start, subData = subData
                        delta, text = subData
                        start += startOffset
                        end = start + delta
                        for subStart in list(self.subtitleDict[x].keys()):
                            subEnd = self.subtitleDict[x][subStart][0] + subStart
                            if subStart < end and end < subEnd or subStart < start and start < subEnd:
                                del self.subtitleDict[x][subStart]
                        self.subtitleDict[x][start] = [delta, text]
                scrollValue = self.subtitle.verticalScrollBar().value()
                self.refreshTable(int(self.row * self.globalInterval), yList[0], scrollValue)
                self.updateBackend()
                self.refreshGraph(True)
        elif key == Qt.Key_5:  # 按当前选择位置裁剪字幕
            selected = self.subtitle.selectionModel().selection().indexes()
            y = selected[0].row()
            cutToken = False
            selectTime = int((y + self.row) * self.globalInterval)
            copySubtitleDict = copy.deepcopy(self.subtitleDict)
            for x in copySubtitleDict.keys():
                for start, subData in copySubtitleDict[x].items():
                    delta, text = subData
                    if selectTime >= start and selectTime <= start + delta:
                        cutToken = True
                        self.subtitleDict[x][start] = [selectTime - start, text]
                        self.subtitleDict[x][selectTime] = [start + delta - selectTime, text]
            if cutToken:
                scrollValue = self.subtitle.verticalScrollBar().value()
                self.refreshTable(int(self.row * self.globalInterval), y, scrollValue)
                self.refreshGraph(True)
                self.updateBackend()
        elif QKeyEvent.modifiers() == Qt.ControlModifier and key == Qt.Key_S:  # 保存
            self.videoDecoder.hide()
            self.videoDecoder.show()  # 弹出输出保存界面
        elif key == Qt.Key_S:  # 播放当前选择字幕
            selectedToken = False
            selected = self.subtitle.selectionModel().selection().indexes()
            x = selected[0].column()
            yList = [selected[0].row(), selected[-1].row()]
            selectRange = [int((y + self.row) * self.globalInterval) for y in yList]
            startList = sorted(self.subtitleDict[x].keys())
            for start in startList:
                end = self.subtitleDict[x][start][0] + start
                for position in range(selectRange[0], selectRange[-1] + 1):
                    if start <= position and position < end:
                        selectedToken = True
                        break
                if selectedToken:
                    break
            if selectedToken:
                position = start
                self.player.setPosition(position)
                self.player_vocal.setPosition(position)
                self.videoSlider.setValue(position * self.videoSlider.width() // self.player.duration())
                self.setTimeLabel(position)

                end = self.subtitleDict[x][start][0] + start
                self.replay = 2  # 单次播放选择区间
                self.playRange = [start, end]
                if self.playStatus:  # 若处于暂停状态则开始播放
                    self.mediaPlay()
        elif QKeyEvent.modifiers() == Qt.ControlModifier and key == Qt.Key_Z:  # 撤回
            if self.subtitleBackendPoint > 0:
                self.subtitleBackendPoint -= 1
                backupData = copy.deepcopy(self.subtitleBackend[self.subtitleBackendPoint])
                self.subtitleDict, self.position, y, scrollValue = backupData
                self.refreshTable(self.position, y, scrollValue)
                self.refreshSubPreview()
        elif QKeyEvent.modifiers() == Qt.ControlModifier and key == Qt.Key_Y:  # 取消撤回
            if self.subtitleBackendPoint < len(self.subtitleBackend) - 1:
                self.subtitleBackendPoint += 1
                backupData = copy.deepcopy(self.subtitleBackend[self.subtitleBackendPoint])
                self.subtitleDict, self.position, y, scrollValue = backupData
                self.refreshTable(self.position, y, scrollValue)
                self.refreshSubPreview()
