import os, time, copy, codecs, subprocess, psutil
from PySide2.QtWidgets import QGridLayout, QFileDialog, QDialog, QPushButton,\
        QLineEdit, QTableWidget, QTableWidgetItem, QCheckBox, QProgressBar, QLabel,\
        QComboBox, QCheckBox, QWidget, QSlider, QFontDialog, QColorDialog, QTabWidget, QMessageBox
from PySide2.QtCore import Qt, QTimer, Signal, QThread, QPoint
from PySide2.QtGui import QFontInfo, QPixmap, QIntValidator, QDoubleValidator


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
    h:m:s.ms -> s in total
    '''
    h = int(t[:2])
    m = int(t[3:5])
    s = int(t[6:8])
    return h * 3600 + m * 60 + s


class Slider(QSlider):
    pointClicked = Signal(QPoint)

    def mousePressEvent(self, event):
        self.pointClicked.emit(event.pos())

    def mouseMoveEvent(self, event):
        self.pointClicked.emit(event.pos())


class videoEncoder(QThread):
    processBar = Signal(int)
    currentPos = Signal(str)
    encodeResult = Signal(bool)

    def __init__(self, videoPath, cmd, parent=None):
        super(videoEncoder, self).__init__(parent)
        self.videoPath = videoPath
        self.cmd = cmd

    def run(self):
        self.p = subprocess.Popen(['ffmpeg.exe', '-i', self.videoPath, '-map', '0:v:0', '-c', 'copy', '-f', 'null', '-'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        self.p.wait()
        frames = self.p.stdout.readlines()[-2].decode('gb18030').split('frame=')[-1].split(' ')
        for f in frames:
            if f:
                totalFrames = int(f)
                break
        self.p = subprocess.Popen(self.cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        cnt = 0
        while self.p.poll() is None:
            console = self.p.stdout.read(1000).decode('gb18030', 'ignore')
            if 'frame=' in console:
                break
        while self.p.poll() is None:
            console = self.p.stdout.read(300).decode('gb18030', 'ignore')
            if '\r' in console:
                console = console.split('\r')[-2]
                if 'frame=' in console:
                    frameArgs = console.split('frame=')[-1].split(' ')
                    for frame in frameArgs:
                        if frame:
                            self.processBar.emit(int(frame) * 100 // totalFrames)
                            break
                cnt += 1
                if not cnt % 4:
                    if 'time=' in console:
                        videoPos = console.split('time=')[-1].split(' ')[0]
                        self.currentPos.emit(videoPos)
        if self.p.poll() == 1:
            self.encodeResult.emit(False)
        elif self.p.poll() == 0:
            self.encodeResult.emit(True)


class label(QLabel):
    clicked = Signal()

    def mouseReleaseEvent(self, QMouseEvent):
        self.clicked.emit()


class encodeOption(QWidget):
    def __init__(self):
        super().__init__()
        self.resize(600, 300)
        self.setWindowTitle('编码设置')
        layout = QGridLayout()
        self.setLayout(layout)
        resolution = QWidget()
        resolutionLayout = QGridLayout()
        resolution.setLayout(resolutionLayout)
        layout.addWidget(resolution, 0, 0, 1, 1)
        resolutionLayout.addWidget(QLabel('分辨率 '), 0, 0, 1, 1)
        self.exportVideoWidth = QLineEdit()
        self.exportVideoWidth.setMaximumWidth(100)
        self.exportVideoWidth.setAlignment(Qt.AlignCenter)
        self.exportVideoWidth.setValidator(QIntValidator(100, 10000))
        self.exportVideoHeight = QLineEdit()
        self.exportVideoHeight.setMaximumWidth(100)
        self.exportVideoHeight.setAlignment(Qt.AlignCenter)
        self.exportVideoHeight.setValidator(QIntValidator(100, 10000))
        resolutionLayout.addWidget(self.exportVideoWidth, 0, 1, 1, 1)
        xLabel = QLabel('x')
        xLabel.setAlignment(Qt.AlignCenter)
        resolutionLayout.addWidget(xLabel, 0, 2, 1, 1)
        resolutionLayout.addWidget(self.exportVideoHeight, 0, 3, 1, 1)

        layout.addWidget(QLabel(), 0, 2, 1, 1)
        layout.addWidget(QLabel('码率(k)'), 0, 3, 1, 1)
        self.exportVideoBitrate = QLineEdit()
        self.exportVideoBitrate.setValidator(QIntValidator(100, 10000))
        layout.addWidget(self.exportVideoBitrate, 0, 4, 1, 1)
        layout.addWidget(QLabel(), 0, 5, 1, 1)
        layout.addWidget(QLabel('帧率'), 0, 6, 1, 1)
        self.exportVideoFPS = QLineEdit()
        self.exportVideoFPS.setValidator(QIntValidator(10, 200))
        layout.addWidget(self.exportVideoFPS, 0, 7, 1, 1)

        self.anime4k = QPushButton('使用Anime4K扩展画质 ')
#         self.anime4k.clicked.connect(self.anime4kClick)
        layout.addWidget(self.anime4k, 1, 0, 1, 1)
        layout.addWidget(QLabel('压缩比'), 1, 3, 1, 1)
        self.exportVideoPreset = QComboBox()
        self.exportVideoPreset.addItems(['极致(最慢)', '较高(较慢)', '中等(中速)', '较低(较快)', '最低(最快)'])
        self.exportVideoPreset.setCurrentIndex(2)
        layout.addWidget(self.exportVideoPreset, 1, 4, 1, 1)
        layout.addWidget(QLabel(), 1, 5, 1, 1)
        layout.addWidget(QLabel('编码器'), 1, 6, 1, 1)
        self.encoder = QComboBox()
        self.encoder.addItems(['CPU', 'N卡 H264', 'N卡 HEVC', 'A卡 H264', 'A卡 HEVC'])
        self.encoder.currentIndexChanged.connect(self.encoderChange)
        layout.addWidget(self.encoder, 1, 7, 1, 1)

        self.mixAudioPath = QLineEdit()
        layout.addWidget(self.mixAudioPath, 2, 0, 1, 1)
        self.mixAudioButton = QPushButton('音频混流')
        self.mixAudioButton.clicked.connect(self.openAudio)
        layout.addWidget(self.mixAudioButton, 2, 1, 1, 1)
        self.confirm = QPushButton('确定')
        self.confirm.clicked.connect(self.hide)
        layout.addWidget(self.confirm, 2, 6, 1, 2)

#     def anime4kClick(self):
#         self.anime4KToken = not self.anime4KToken
#         if self.anime4KToken:
#             self.anime4k.setStyleSheet('background-color:#3daee9')
#         else:
#             self.anime4k.setStyleSheet('background-color:#31363b')

    def openAudio(self):
        self.audioPath = QFileDialog.getOpenFileName(self, "请选择音频文件", None, "音频文件 (*.m4a *.mp3 *.wav *.wma);;所有文件(*.*)")[0]
        if self.audioPath:
            self.mixAudioPath.setText(self.audioPath)

    def encoderChange(self, index):
        self.exportVideoPreset.clear()
        if not index:
            self.exportVideoPreset.addItems(['极致(最慢)', '较高(较慢)', '中等(中速)', '较低(较快)', '最低(最快)'])
        else:
            self.exportVideoPreset.addItems(['较高(较慢)', '中等(中速)', '较低(较快)'])


class advanced(QWidget):
    def __init__(self, videoWidth, videoHeight):
        super().__init__()
        layout = QGridLayout()
        self.setLayout(layout)
        layout.addWidget(QLabel('Title:'), 0, 0, 1, 1)
        self.title = QLineEdit()
        layout.addWidget(self.title, 0, 1, 1, 4)
        layout.addWidget(QLabel('Script:'), 1, 0, 1, 1)
        self.originalScript = QLineEdit()
        layout.addWidget(self.originalScript, 1, 1, 1, 1)
        layout.addWidget(QLabel('Translation:'), 1, 3, 1, 1)
        self.translation = QLineEdit()
        layout.addWidget(self.translation, 1, 4, 1, 1)
        layout.addWidget(QLabel('Editing:'), 2, 0, 1, 1)
        self.editing = QLineEdit()
        layout.addWidget(self.editing, 2, 1, 1, 1)
        layout.addWidget(QLabel('Timing:'), 2, 3, 1, 1)
        self.timing = QLineEdit()
        layout.addWidget(self.timing, 2, 4, 1, 1)

        layout.addWidget(QLabel('Script Type:'), 3, 0, 1, 1)
        self.scriptType = QLineEdit('v4.00+')
        layout.addWidget(self.scriptType, 3, 1, 1, 1)
        layout.addWidget(QLabel('Collisions:'), 3, 3, 1, 1)
        self.collisions = QComboBox()
        self.collisions.addItems(['Normal', 'Reverse'])
        layout.addWidget(self.collisions, 3, 4, 1, 1)
        layout.addWidget(QLabel('PlayResX:'), 4, 0, 1, 1)
        self.playResX = QLineEdit(str(videoWidth))
        layout.addWidget(self.playResX, 4, 1, 1, 1)
        layout.addWidget(QLabel('PlayResY:'), 4, 3, 1, 1)
        self.playResY = QLineEdit(str(videoHeight))
        layout.addWidget(self.playResY, 4, 4, 1, 1)
        layout.addWidget(QLabel('Timer:'), 5, 0, 1, 1)
        self.timer = QLineEdit('100.0000')
        layout.addWidget(self.timer, 5, 1, 1, 1)
        layout.addWidget(QLabel('WrapStyle:'), 5, 3, 1, 1)
        self.warpStyle = QComboBox()
        self.warpStyle.addItems(['0: 上行更长', '1: 行尾换行', '2: 不换行', '3: 下行更长'])
        layout.addWidget(self.warpStyle, 5, 4, 1, 1)
        layout.addWidget(QLabel('Scaled Border And Shadow:'), 6, 0, 1, 3)
        self.scaleBS = QComboBox()
        self.scaleBS.addItems(['yes', 'no'])
        layout.addWidget(self.scaleBS, 6, 4, 1, 1)

    def setPlayRes(self, videoWidth, videoHeight):
        self.playResX.setText(str(videoWidth))
        self.playResY.setText(str(videoHeight))


class fontWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.fontName = '微软雅黑'
        self.fontSize = 90
        self.fontBold = True
        self.fontItalic = False
        self.fontUnderline = False
        self.fontStrikeout = False
        self.fontColor = '#ffffff'
        self.secondColor = '#ff5cf7'
        self.outlineColor = '#000000'
        self.shadowColor = '#696969'

        fontBold = '粗体' if self.fontBold else ''
        fontItalic = '斜体' if self.fontItalic else ''
        fontUnderline = '下划线' if self.fontUnderline else ''
        fontStrikeOut = '删除线' if self.fontStrikeout else ''
        self.optionLayout = QGridLayout()
        self.setLayout(self.optionLayout)
        self.fontSelect = QPushButton('%s%s号%s%s%s%s' % (self.fontName, self.fontSize, fontBold, fontItalic, fontUnderline, fontStrikeOut))
        self.fontSelect.setFixedWidth(150)
        self.fontSelect.clicked.connect(self.getFont)
        self.optionLayout.addWidget(self.fontSelect, 0, 0, 1, 2)
        self.optionLayout.addWidget(QLabel(''), 0, 2, 1, 1)
        self.fontColorSelect = label()
        self.fontColorSelect.setAlignment(Qt.AlignCenter)
        self.fontColorSelect.setText(self.fontColor)
        self.fontColorSelect.setStyleSheet('background-color:%s;color:%s' % (self.fontColor, self.colorReverse(self.fontColor)))
        self.fontColorSelect.clicked.connect(self.getFontColor)
        self.optionLayout.addWidget(self.fontColorSelect, 0, 3, 1, 1)
        self.fontColorLabel = QLabel('字体颜色')
        self.optionLayout.addWidget(self.fontColorLabel, 0, 4, 1, 1)
        self.karaoke = QPushButton('卡拉OK模式')
        self.karaoke.setFixedWidth(150)
        self.karaokeStatus = False
        self.karaoke.clicked.connect(self.setKaraoke)
        self.optionLayout.addWidget(self.karaoke, 1, 0, 1, 2)
        self.secondColorSelect = label()
        self.secondColorSelect.setAlignment(Qt.AlignCenter)
        self.secondColorSelect.setText(self.secondColor)
        self.secondColorSelect.setStyleSheet('background-color:%s;color:%s' % (self.secondColor, self.colorReverse(self.secondColor)))
        self.secondColorSelect.clicked.connect(self.getSecondFontColor)
        self.secondColorSelect.hide()
        self.optionLayout.addWidget(self.secondColorSelect, 1, 3, 1, 1)
        self.secondColorLabel = QLabel('次要颜色')
        self.secondColorLabel.hide()
        self.optionLayout.addWidget(self.secondColorLabel, 1, 4, 1, 1)

        validator = QIntValidator()
        self.horizontalMoveEdit = QLineEdit('100')
        self.horizontalMoveEdit.setValidator(validator)
        self.horizontalMoveEdit.setFixedWidth(100)
        self.horizontalMoveEdit.hide()
        self.optionLayout.addWidget(self.horizontalMoveEdit, 2, 0, 1, 1)
        self.horizontalMoveLabel = QLabel('水平移动')
        self.horizontalMoveLabel.hide()
        self.optionLayout.addWidget(self.horizontalMoveLabel, 2, 1, 1, 1)

        self.verticalMoveEdit = QLineEdit('0')
        self.verticalMoveEdit.setValidator(validator)
        self.verticalMoveEdit.setFixedWidth(100)
        self.verticalMoveEdit.hide()
        self.optionLayout.addWidget(self.verticalMoveEdit, 2, 3, 1, 1)
        self.verticalMoveLabel = QLabel('竖直移动')
        self.verticalMoveLabel.hide()
        self.optionLayout.addWidget(self.verticalMoveLabel, 2, 4, 1, 1)

        validator = QDoubleValidator()
        self.outlineSizeEdit = QLineEdit('2')
        self.outlineSizeEdit.setValidator(validator)
        self.outlineSizeEdit.setFixedWidth(100)
        self.optionLayout.addWidget(self.outlineSizeEdit, 3, 0, 1, 1)
        self.outlineSizeLabel = QLabel('描边大小')
        self.optionLayout.addWidget(self.outlineSizeLabel, 3, 1, 1, 1)
        self.outlineColorSelect = label()
        self.outlineColorSelect.setAlignment(Qt.AlignCenter)
        self.outlineColorSelect.setText(self.outlineColor)
        self.outlineColorSelect.setStyleSheet('background-color:%s;color:%s' % (self.outlineColor, self.colorReverse(self.outlineColor)))
        self.outlineColorSelect.clicked.connect(self.getOutlineColor)
        self.optionLayout.addWidget(self.outlineColorSelect, 3, 3, 1, 1)
        self.outlineColorLabel = QLabel('描边颜色')
        self.optionLayout.addWidget(self.outlineColorLabel, 3, 4, 1, 1)
        self.shadowSizeEdit = QLineEdit('2')
        self.shadowSizeEdit.setValidator(validator)
        self.shadowSizeEdit.setFixedWidth(100)
        self.optionLayout.addWidget(self.shadowSizeEdit, 4, 0, 1, 1)
        self.shadowSizeLabel = QLabel('阴影大小')
        self.optionLayout.addWidget(self.shadowSizeLabel, 4, 1, 1, 1)
        self.shadowColorSelect = label()
        self.shadowColorSelect.setAlignment(Qt.AlignCenter)
        self.shadowColorSelect.setText(self.shadowColor)
        self.shadowColorSelect.setStyleSheet('background-color:%s;color:%s' % (self.shadowColor, self.colorReverse(self.shadowColor)))
        self.shadowColorSelect.clicked.connect(self.getShadowColor)
        self.optionLayout.addWidget(self.shadowColorSelect, 4, 3, 1, 1)
        self.shadowColorLabel = QLabel('阴影颜色')
        self.optionLayout.addWidget(self.shadowColorLabel, 4, 4, 1, 1)
        self.align = QComboBox()
        self.align.addItems(['1: 左下', '2: 中下', '3: 右下', '4: 中左', '5: 中间', '6: 中右', '7: 左上', '8: 中上', '9: 右上'])
        self.align.setCurrentIndex(1)
        self.align.setFixedWidth(100)
        self.optionLayout.addWidget(self.align, 5, 0, 1, 1)
        self.alignLabel = QLabel('对齐方式')
        self.optionLayout.addWidget(self.alignLabel, 5, 1, 1, 1)

        validator = QIntValidator()
        self.VAlignSlider = QLineEdit('100')
        self.VAlignSlider.setValidator(validator)
        self.VAlignSlider.setFixedWidth(100)
        self.optionLayout.addWidget(self.VAlignSlider, 5, 3, 1, 1)
        self.VAlignLabel = QLabel('垂直边距')
        self.optionLayout.addWidget(self.VAlignLabel, 5, 4, 1, 1)

        self.LAlignSlider = QLineEdit('0')
        self.LAlignSlider.setValidator(validator)
        self.LAlignSlider.setFixedWidth(100)
        self.optionLayout.addWidget(self.LAlignSlider, 6, 0, 1, 1)
        self.LAlignLabel = QLabel('左边距')
        self.optionLayout.addWidget(self.LAlignLabel, 6, 1, 1, 1)
        self.RAlignSlider = QLineEdit('0')
        self.RAlignSlider.setValidator(validator)
        self.RAlignSlider.setFixedWidth(100)
        self.optionLayout.addWidget(self.RAlignSlider, 6, 3, 1, 1)
        self.RAlignLabel = QLabel('右边距')
        self.optionLayout.addWidget(self.RAlignLabel, 6, 4, 1, 1)

    def getFont(self):
        status, font = QFontDialog.getFont()
        if status:
            self.font = QFontInfo(font)
            self.fontName = self.font.family()
            self.fontSize = self.font.pointSize()
            self.fontBold = self.font.bold()
            self.fontItalic = self.font.italic()
            self.fontUnderline = self.font.underline()
            self.fontStrikeout = self.font.strikeOut()
            fontBold = '粗体' if self.fontBold else ''
            fontItalic = '斜体' if self.fontItalic else ''
            fontUnderline = '下划线' if self.fontUnderline else ''
            fontStrikeOut = '删除线' if self.fontStrikeout else ''
            self.fontSelect.setText('%s%s号%s%s%s%s' % (self.fontName, self.fontSize, fontBold, fontItalic, fontUnderline, fontStrikeOut))

    def setKaraoke(self):
        self.karaokeStatus = not self.karaokeStatus
        if self.karaokeStatus:
            self.secondColorSelect.show()
            self.secondColorLabel.show()
            self.horizontalMoveEdit.show()
            self.horizontalMoveLabel.show()
            self.verticalMoveEdit.show()
            self.verticalMoveLabel.show()
            self.karaoke.setStyleSheet('background-color:#3daee9')
        else:
            self.secondColorSelect.hide()
            self.secondColorLabel.hide()
            self.horizontalMoveEdit.hide()
            self.horizontalMoveLabel.hide()
            self.verticalMoveEdit.hide()
            self.verticalMoveLabel.hide()
            self.karaoke.setStyleSheet('background-color:#31363b')

    def getFontColor(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.fontColor = color.name()
            self.fontColorSelect.setText(self.fontColor)
            self.fontColorSelect.setStyleSheet('background-color:%s;color:%s' % (self.fontColor, self.colorReverse(self.fontColor)))

    def getSecondFontColor(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.secondColor = color.name()
            self.secondColorSelect.setText(self.secondColor)
            self.secondColorSelect.setStyleSheet('background-color:%s;color:%s' % (self.secondColor, self.colorReverse(self.secondColor)))

    def getOutlineColor(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.outlineColor = color.name()
            self.outlineColorSelect.setText(self.outlineColor)
            self.outlineColorSelect.setStyleSheet('background-color:%s;color:%s' % (self.outlineColor, self.colorReverse(self.outlineColor)))

    def getShadowColor(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.shadowColor = color.name()
            self.shadowColorSelect.setText(self.shadowColor)
            self.shadowColorSelect.setStyleSheet('background-color:%s;color:%s' % (self.shadowColor, self.colorReverse(self.shadowColor)))

    def colorReverse(self, color):
        r = 255 - int(color[1:3], 16)
        g = 255 - int(color[3:5], 16)
        b = 255 - int(color[5:7], 16)
        return '#%s%s%s' % (hex(r)[2:], hex(g)[2:], hex(b)[2:])


class VideoDecoder(QDialog):
    saveToken = Signal(bool)
    popAnime4K = Signal()

    def __init__(self):
        self.videoPath = ''
        self.subPreview = ''
        self.videoWidth = 1920
        self.videoHeight = 1080
        self.subtitles = {x: {} for x in range(5)}
        self.styleNameList = [str(x) for x in range(1, 6)]
        self.setEncode = encodeOption()
        self.setEncode.anime4k.clicked.connect(lambda: self.popAnime4K.emit())

        super().__init__()
        self.setWindowTitle('字幕输出及合成')
        self.resize(1700, 770)
        self.layout = QGridLayout()
        self.setLayout(self.layout)

        self.preview = QLabel('效果预览')
        self.preview.setMaximumHeight(720)
        self.preview.setMaximumWidth(1280)
        self.layout.addWidget(self.preview, 0, 0, 6, 10)
        self.preview.setScaledContents(True)
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setStyleSheet("QLabel{background:white;}")

        self.previewSlider = Slider()
        self.previewSlider.setOrientation(Qt.Horizontal)
        self.previewSlider.setMinimum(0)
        self.previewSlider.setMaximum(1000)
        self.previewSlider.pointClicked.connect(self.setPreviewSlider)
        self.layout.addWidget(self.previewSlider, 6, 0, 1, 10)

        self.option = QTabWidget()
        self.option.setMaximumWidth(450)
        self.layout.addWidget(self.option, 0, 10, 3, 1)
        self.subDict = {x: fontWidget() for x in range(5)}
        for subNumber, tabPage in self.subDict.items():
            self.option.addTab(tabPage, '字幕 %s' % (subNumber + 1))
        self.advanced = advanced(self.videoWidth, self.videoHeight)
        self.option.addTab(self.advanced, 'ASS字幕信息')

        self.startGrid = QWidget()
        self.layout.addWidget(self.startGrid, 3, 10, 3, 1)
        self.startLayout = QGridLayout()
        self.startGrid.setLayout(self.startLayout)
        self.sub1Check = QPushButton('字幕 1')
        self.sub1Check.setStyleSheet('background-color:#3daee9')
        self.sub2Check = QPushButton('字幕 2')
        self.sub2Check.setStyleSheet('background-color:#3daee9')
        self.sub3Check = QPushButton('字幕 3')
        self.sub3Check.setStyleSheet('background-color:#3daee9')
        self.sub4Check = QPushButton('字幕 4')
        self.sub4Check.setStyleSheet('background-color:#3daee9')
        self.sub5Check = QPushButton('字幕 5')
        self.sub5Check.setStyleSheet('background-color:#3daee9')
        self.sub1CheckStatus = True
        self.sub2CheckStatus = True
        self.sub3CheckStatus = True
        self.sub4CheckStatus = True
        self.sub5CheckStatus = True
        self.sub1Check.clicked.connect(self.sub1CheckButtonClick)
        self.sub2Check.clicked.connect(self.sub2CheckButtonClick)
        self.sub3Check.clicked.connect(self.sub3CheckButtonClick)
        self.sub4Check.clicked.connect(self.sub4CheckButtonClick)
        self.sub5Check.clicked.connect(self.sub5CheckButtonClick)
        self.startLayout.addWidget(self.sub1Check, 0, 0, 1, 1)
        self.startLayout.addWidget(self.sub2Check, 0, 1, 1, 1)
        self.startLayout.addWidget(self.sub3Check, 0, 2, 1, 1)
        self.startLayout.addWidget(self.sub4Check, 0, 3, 1, 1)
        self.startLayout.addWidget(self.sub5Check, 0, 4, 1, 1)
        self.layerCheck = QPushButton('禁止字幕重叠')
        self.layerCheck.setStyleSheet('background-color:#3daee9')
        self.layerCheckStatus = True
        self.layerCheck.clicked.connect(self.layerButtonClick)
        self.startLayout.addWidget(self.layerCheck, 1, 0, 1, 2)
        self.encodeSetup = QPushButton('编码设置')
        self.encodeSetup.clicked.connect(self.setEncodeArgs)
        self.startLayout.addWidget(self.encodeSetup, 1, 3, 1, 2)
        self.outputEdit = QLineEdit()
        self.startLayout.addWidget(self.outputEdit, 2, 0, 1, 4)
        self.outputButton = QPushButton('保存路径')
        self.startLayout.addWidget(self.outputButton, 2, 4, 1, 1)
        self.outputButton.clicked.connect(self.setSavePath)
        self.exportSubButton = QPushButton('导出字幕')
        self.exportSubButton.clicked.connect(self.exportSub)
        self.exportSubButton.setFixedHeight(50)
        self.startLayout.addWidget(self.exportSubButton, 3, 0, 1, 2)
        self.startButton = QPushButton('开始压制')
        self.startButton.clicked.connect(self.exportVideo)
        self.startButton.setFixedHeight(50)
        self.startLayout.addWidget(self.startButton, 3, 3, 1, 2)

        self.processBar = QProgressBar()
        self.processBar.setStyleSheet("QProgressBar{border:1px;text-align:center;background:white}")
        self.processBar.setMaximumWidth(450)
        self.layout.addWidget(self.processBar, 6, 10, 1, 1)

        self.totalFrames = 0
        self.old_decodeArgs = []
        self.videoPos = 1
        self.old_videoPos = 1
        self.duration = 0
        self.previewTimer = QTimer()
        self.previewTimer.setInterval(50)
        self.previewTimer.start()
        self.previewTimer.timeout.connect(self.generatePreview)

    def sub1CheckButtonClick(self):
        self.sub1CheckStatus = not self.sub1CheckStatus
        if self.sub1CheckStatus:
            self.sub1Check.setStyleSheet('background-color:#3daee9')
        else:
            self.sub1Check.setStyleSheet('background-color:#31363b')

    def sub2CheckButtonClick(self):
        self.sub2CheckStatus = not self.sub2CheckStatus
        if self.sub2CheckStatus:
            self.sub2Check.setStyleSheet('background-color:#3daee9')
        else:
            self.sub2Check.setStyleSheet('background-color:#31363b')

    def sub3CheckButtonClick(self):
        self.sub3CheckStatus = not self.sub3CheckStatus
        if self.sub3CheckStatus:
            self.sub3Check.setStyleSheet('background-color:#3daee9')
        else:
            self.sub3Check.setStyleSheet('background-color:#31363b')

    def sub4CheckButtonClick(self):
        self.sub4CheckStatus = not self.sub4CheckStatus
        if self.sub4CheckStatus:
            self.sub4Check.setStyleSheet('background-color:#3daee9')
        else:
            self.sub4Check.setStyleSheet('background-color:#31363b')

    def sub5CheckButtonClick(self):
        self.sub5CheckStatus = not self.sub5CheckStatus
        if self.sub5CheckStatus:
            self.sub5Check.setStyleSheet('background-color:#3daee9')
        else:
            self.sub5Check.setStyleSheet('background-color:#31363b')

    def layerButtonClick(self):
        self.layerCheckStatus = not self.layerCheckStatus
        if self.layerCheckStatus:
            self.layerCheck.setStyleSheet('background-color:#3daee9')
        else:
            self.layerCheck.setStyleSheet('background-color:#31363b')

    def setSavePath(self):
        savePath = QFileDialog.getSaveFileName(self, "选择视频输出文件夹", None, "MP4格式 (*.mp4)")[0]
        if savePath:
            self.outputEdit.setText(savePath)

    def setDefault(self, videoPath, videoWidth, videoHeight, duration, bitrate, fps, subtitles, styleNameList):
        self.videoPath = videoPath
        self.subPreview = os.path.splitext(self.videoPath)[0] + '.ass'
        self.videoWidth = videoWidth
        self.videoHeight = videoHeight
        self.setEncode.exportVideoWidth.setText(str(videoWidth))
        self.setEncode.exportVideoHeight.setText(str(videoHeight))
        self.setEncode.exportVideoBitrate.setText(str(bitrate))
        self.setEncode.exportVideoFPS.setText(str(fps))
        self.duration = duration
        self.advanced.setPlayRes(videoWidth, videoHeight)
        self.subtitles = copy.deepcopy(subtitles)
        for index in self.subtitles:
            if -1 in self.subtitles[index]:
                del self.subtitles[index][-1]
        self.styleNameList = styleNameList

    def copySubtitle(self, subtitles):
        self.subtitles = copy.deepcopy(subtitles)
        for index in self.subtitles:
            if -1 in self.subtitles[index]:
                del self.subtitles[index][-1]

    def setSubDictStyle(self, assSummary):
        subNumber = assSummary[0]
        styleName = assSummary[1]
        assDict = assSummary[2]
        fontName = assDict['Fontname']
        fontSize = assDict['Fontsize']
        fontBold = True if assDict['Bold'] == '-1' else False
        fontItalic = True if assDict['Italic'] == '-1' else False
        fontUnderline = True if assDict['Underline'] == '-1' else False
        fontStrikeOut = True if assDict['StrikeOut'] == '-1' else False
        fontColor = self.rgbColor(assDict['PrimaryColour'])
        secondColor = self.rgbColor(assDict['SecondaryColour'])
        outlineColor = self.rgbColor(assDict['OutlineColour'])
        shadowColor = self.rgbColor(assDict['BackColour'])
        outline = assDict['Outline']
        shadow = assDict['Shadow']
        alignment = int(assDict['Alignment']) - 1
        VA = assDict['MarginV']
        LA = assDict['MarginL']
        RA = assDict['MarginR']

        tabPage = self.subDict[subNumber]
        tabPage.fontName = fontName
        tabPage.fontSize = fontSize
        tabPage.fontBold = fontBold
        tabPage.fontItalic = fontItalic
        tabPage.fontUnderline = fontUnderline
        tabPage.fontStrikeout = fontStrikeOut
        tabPage.fontColor = fontColor
        tabPage.secondColor = secondColor
        tabPage.outlineColor = outlineColor
        tabPage.shadowColor = shadowColor

        fontBold = '粗体' if fontBold else ''
        fontItalic = '斜体' if fontItalic else ''
        fontUnderline = '下划线' if fontUnderline else ''
        fontStrikeOut = '删除线' if fontStrikeOut else ''

        tabPage.fontSelect.setText('%s%s号%s%s%s%s' % (fontName, fontSize, fontBold, fontItalic, fontUnderline, fontStrikeOut))
        tabPage.fontColorSelect.setText(fontColor)
        tabPage.fontColorSelect.setStyleSheet('background-color:%s;color:%s' % (fontColor, self.colorReverse(fontColor)))
        tabPage.secondColorSelect.setText(secondColor)
        tabPage.secondColorSelect.setStyleSheet('background-color:%s;color:%s' % (secondColor, self.colorReverse(secondColor)))
        tabPage.outlineSizeEdit.setText(outline)
        tabPage.outlineColorSelect.setText(outlineColor)
        tabPage.outlineColorSelect.setStyleSheet('background-color:%s;color:%s' % (outlineColor, self.colorReverse(outlineColor)))
        tabPage.shadowSizeEdit.setText(shadow)
        tabPage.shadowColorSelect.setText(shadowColor)
        tabPage.shadowColorSelect.setStyleSheet('background-color:%s;color:%s' % (shadowColor, self.colorReverse(shadowColor)))
        tabPage.align.setCurrentIndex(alignment)
        tabPage.VAlignSlider.setText(VA)
        tabPage.LAlignSlider.setText(LA)
        tabPage.RAlignSlider.setText(RA)

    def returnSubDictStyle(self):
        selectedSubDict = {}
        for subNumber in range(5):
            selectedSubDict[subNumber] = self.subDict[subNumber]
        subtitleArgs = {}
        self.karaokDict = {}
        for subNumber, font in selectedSubDict.items():
            if font.karaokeStatus:
                try:
                    self.karaokDict[subNumber] = [True, self.ffmpegColor(font.secondColor), int(font.LAlignSlider.text()),
                                                  int(font.VAlignSlider.text()), int(font.horizontalMoveEdit.text()),
                                                  int(font.verticalMoveEdit.text())]
                except:
                    self.karaokDict[subNumber] = [True, self.ffmpegColor(font.secondColor), int(font.LAlignSlider.text()),
                                                  int(font.VAlignSlider.text()), 0, 0]
            else:
                self.karaokDict[subNumber] = [False, '&H00000000']
            fontBold = -1 if font.fontBold else 0
            fontItalic = -1 if font.fontItalic else 0
            fontUnderline = -1 if font.fontUnderline else 0
            fontStrikeout = -1 if font.fontStrikeout else 0
            subtitleArgs[subNumber] = [font.fontName, font.fontSize, self.ffmpegColor(font.fontColor), self.karaokDict[subNumber][1],
                                       self.ffmpegColor(font.outlineColor), self.ffmpegColor(font.shadowColor),
                                       fontBold, fontItalic, fontUnderline, fontStrikeout, 100, 100, 0, 0, 1,
                                       font.outlineSizeEdit.text()[:4], font.shadowSizeEdit.text()[:4],
                                       font.align.currentText().split(':')[0],
                                       int(font.LAlignSlider.text()), int(font.RAlignSlider.text()), int(font.VAlignSlider.text()), 1]
        return subtitleArgs

    def setPreviewSlider(self, p):
        pos = p.x() / self.previewSlider.width() * 1000
        if pos > 1000:
            pos = 1000
        elif pos < 0:
            pos = 0
        self.previewSlider.setValue(pos)
        self.videoPos = pos * self.duration // 1000000

    def ffmpegColor(self, color):
        '''
        rgb color --> ffmpeg color
        '''
        color = color.upper()
        r = color[1:3]
        g = color[3:5]
        b = color[5:7]
        return '&H00%s%s%s' % (b, g, r)

    def rgbColor(self, color):
        '''
        ffmpeg color --> rgb color
        '''
        color = color[-6:].lower()
        b = color[:2]
        g = color[2:4]
        r = color[4:6]
        return '#%s%s%s' % (r, g, b)

    def colorReverse(self, color):
        r = 255 - int(color[1:3], 16)
        g = 255 - int(color[3:5], 16)
        b = 255 - int(color[5:7], 16)
        return '#%s%s%s' % (hex(r)[2:], hex(g)[2:], hex(b)[2:])

    def collectArgs(self, allSub=False):
        self.decodeArgs = [[self.advanced.title.text(), self.advanced.originalScript.text(), self.advanced.translation.text(),
                           self.advanced.editing.text(), self.advanced.timing.text(), self.advanced.scriptType.text(),
                           self.advanced.collisions.currentText(), self.advanced.playResX.text(), self.advanced.playResY.text(),
                           self.advanced.timer.text(), self.advanced.warpStyle.currentText().split(':')[0], self.advanced.scaleBS.currentText()]]
        self.selectedSubDict = {}
        for subNumber, subCheck in enumerate([self.sub1CheckStatus, self.sub2CheckStatus, self.sub3CheckStatus, self.sub4CheckStatus, self.sub5CheckStatus]):
            if subCheck or allSub:
                self.selectedSubDict[subNumber] = self.subDict[subNumber]
        self.subtitleArgs = {}
        self.karaokDict = {}
        font = ''
        for subNumber, font in self.selectedSubDict.items():
            if not font.LAlignSlider.text():
                font.LAlignSlider.setText('0')
            if not font.RAlignSlider.text():
                font.RAlignSlider.setText('0')
            if not font.VAlignSlider.text():
                font.VAlignSlider.setText('0')
            if font.karaokeStatus:
                try:
                    self.karaokDict[subNumber] = [True, self.ffmpegColor(font.secondColor), int(font.LAlignSlider.text()),
                                                  int(font.VAlignSlider.text()), int(font.horizontalMoveEdit.text()),
                                                  int(font.verticalMoveEdit.text())]
                except:
                    self.karaokDict[subNumber] = [True, self.ffmpegColor(font.secondColor), int(font.LAlignSlider.text()),
                                                  int(font.VAlignSlider.text()), 0, 0]
            else:
                self.karaokDict[subNumber] = [False, '&H00000000']
            fontBold = -1 if font.fontBold else 0
            fontItalic = -1 if font.fontItalic else 0
            fontUnderline = -1 if font.fontUnderline else 0
            fontStrikeout = -1 if font.fontStrikeout else 0
            self.subtitleArgs[subNumber] = [font.fontName, font.fontSize, self.ffmpegColor(font.fontColor), self.karaokDict[subNumber][1],
                                            self.ffmpegColor(font.outlineColor), self.ffmpegColor(font.shadowColor),
                                            fontBold, fontItalic, fontUnderline, fontStrikeout, 100, 100, 0, 0, 1,
                                            font.outlineSizeEdit.text()[:4], font.shadowSizeEdit.text()[:4],
                                            font.align.currentText().split(':')[0],
                                            int(font.LAlignSlider.text()), int(font.RAlignSlider.text()), int(font.VAlignSlider.text()), 1]
        self.decodeArgs.append(self.subtitleArgs)
        if font:
            self.decodeArgs.append([self.videoPath, self.layerCheckStatus, font.karaokeStatus])
        else:
            self.decodeArgs.append([self.videoPath, self.layerCheckStatus, ''])

    def exportSub(self):
        subtitlePath = QFileDialog.getSaveFileName(self, "选择字幕输出文件夹", None, "ASS字幕文件 (*.ass)")[0]
        if subtitlePath:
            self.writeAss(subtitlePath, False, True)
            QMessageBox.information(self, '导出字幕', '导出完成', QMessageBox.Yes)
            self.saveToken.emit(True)

    def writeAss(self, outputPath='temp_sub.ass', preview=True, tip=False, pos=0, allSub=False):
        if allSub:
            self.collectArgs(True)
        if outputPath:
            ass = codecs.open(outputPath, 'w', 'utf_8_sig')
            ass.write('[Script Info]\n')
            ass.write('; Script generated by DD烤肉机2.0; Powered by 执鸣神君\n')
            ass.write('; B站个人空间：https://space.bilibili.com/637783；Github项目地址：https://github.com/jiafangjun/DD_KaoRou2\n')
            ass.write('Title: %s\n' % self.advanced.title.text())
            ass.write('OriginalScript: %s\n' % self.advanced.originalScript.text())
            ass.write('OriginalTranslation: %s\n' % self.advanced.translation.text())
            ass.write('OriginalEditing: %s\n' % self.advanced.editing.text())
            ass.write('OriginalTiming: %s\n' % self.advanced.timing.text())
            ass.write('ScriptType: %s\n' % self.advanced.scriptType.text())
            ass.write('Collisions: %s\n' % self.advanced.collisions.currentText())
            ass.write('PlayResX: %s\n' % self.advanced.playResX.text())
            ass.write('PlayResY: %s\n' % self.advanced.playResY.text())
            ass.write('Timer: %s\n' % self.advanced.timer.text())
            ass.write('WrapStyle: %s\n' % self.advanced.warpStyle.currentText().split(':')[0])
            ass.write('ScaledBorderAndShadow: %s\n\n' % self.advanced.scaleBS.currentText())

            ass.write('[V4+ Styles]\n')
            ass.write('Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ')
            ass.write('ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n')
            for subNumber, fontArgs in self.subtitleArgs.items():
                style = 'Style: %s' % self.styleNameList[subNumber]
                for i in fontArgs:
                    style += ',%s' % i
                ass.write('%s\n\n' % style)

            ass.write('[Events]\n')
            ass.write('Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n')
            if preview:
                for subNumber in self.subtitleArgs:
                    num = subNumber + 1
                    if self.karaokDict[subNumber][0]:
                        karaX = self.karaokDict[subNumber][2]
                        karaY = self.karaokDict[subNumber][3]
                        moveX = self.karaokDict[subNumber][4]
                        moveY = self.karaokDict[subNumber][5]
                        if self.layerCheckStatus:
                            line = 'Dialogue: 0,0:00:00.00,0:00:10.00,%s,#%s,0,0,0,,{\\K10\\move(%s,%s,%s,%s)}%s\n' % \
                            (self.styleNameList[num - 1], num, karaX, karaY, karaX + moveX, karaY + moveY, r'Hi! 我是第%s列歌词。' % num)
                        else:
                            line = 'Dialogue: %s,0:00:00.00,0:00:10.00,%s,#%s,0,0,0,,{\\K10\\move(%s,%s,%s,%s)}%s\n' % \
                            (subNumber, self.styleNameList[num - 1], num, karaX, karaY, karaX + moveX, karaY + moveY, 'Hi! 我是第%s列歌词。' % num)
                        ass.write(line)
                    else:
                        if self.layerCheckStatus:
                            line = 'Dialogue: 0,0:00:00.00,0:00:10.00,%s,#%s,0,0,0,,%s\n' % \
                            (self.styleNameList[num - 1], num, r'Hi! 我是第%s列字幕。' % num)
                        else:
                            line = 'Dialogue: %s,0:00:00.00,0:00:10.00,%s,#%s,0,0,0,,%s\n' % \
                            (subNumber, self.styleNameList[num - 1], num, 'Hi! 我是第%s列字幕。' % num)
                        ass.write(line)
                if tip:
                    QMessageBox.information(self, '导出字幕', '导出完成', QMessageBox.Yes)
            else:
                if not pos:
                    for subNumber in self.subtitleArgs:
                        for start in sorted(self.subtitles[subNumber].keys()):
                            subData = self.subtitles[subNumber][start]
                            if start >= 0:
                                num = subNumber + 1
                                if self.karaokDict[subNumber][0]:
                                    karaX = self.karaokDict[subNumber][2]
                                    karaY = self.karaokDict[subNumber][3]
                                    moveX = self.karaokDict[subNumber][4]
                                    moveY = self.karaokDict[subNumber][5]
                                    if self.layerCheckStatus:
                                        line = 'Dialogue: 0,%s,%s,%s,#%s,0,0,0,,{\\K%s\\move(%s,%s,%s,%s)\\fad(500,500)}%s\n' % \
                                        (ms2ASSTime(start), ms2ASSTime(start + subData[0]), self.styleNameList[num - 1], num, subData[0] // 10 - 100, karaX, karaY, karaX + moveX, karaY + moveY, subData[1])
                                    else:
                                        line = 'Dialogue: %s,%s,%s,%s,#%s,0,0,0,,{\\K%s\\move(%s,%s,%s,%s)\\fad(500,500)}%s\n' % \
                                        (subNumber, ms2ASSTime(start), ms2ASSTime(start + subData[0]), self.styleNameList[num - 1], num, subData[0] // 10 - 100, karaX, karaY, karaX + moveX, karaY + moveY, subData[1])
                                    ass.write(line)
                                else:
                                    if self.layerCheckStatus:
                                        line = 'Dialogue: 0,%s,%s,%s,#%s,0,0,0,,%s\n' % (ms2ASSTime(start), ms2ASSTime(start + subData[0]), self.styleNameList[num - 1], num, subData[1])
                                    else:
                                        line = 'Dialogue: %s,%s,%s,%s,#%s,0,0,0,,%s\n' % (subNumber, ms2ASSTime(start), ms2ASSTime(start + subData[0]), self.styleNameList[num - 1], num, subData[1])
                                    ass.write(line)
                else:
                    for subNumber in self.subtitleArgs:
                        startKeys = sorted(self.subtitles[subNumber].keys())
                        for cnt, start in enumerate(startKeys):
                            if start / 1000 > pos and cnt:
                                start = startKeys[cnt - 1]
                                subData = self.subtitles[subNumber][start]
                                num = subNumber + 1
                                if self.karaokDict[subNumber][0]:
                                    karaX = self.karaokDict[subNumber][2]
                                    karaY = self.karaokDict[subNumber][3]
                                    moveX = self.karaokDict[subNumber][4]
                                    moveY = self.karaokDict[subNumber][5]
                                    if self.layerCheckStatus:
                                        line = 'Dialogue: 0,0:00:00.00,0:00:10.00,%s,#%s,0,0,0,,{\\K1000\\move(%s,%s,%s,%s)}%s\n' % \
                                        (self.styleNameList[num - 1], num, karaX, karaY, karaX + moveX, karaY + moveY, subData[1])
                                    else:
                                        line = 'Dialogue: %s,0:00:00.00,0:00:10.00,%s,#%s,0,0,0,,{\\K1000\\move(%s,%s,%s,%s)}%s\n' % \
                                        (subNumber, self.styleNameList[num - 1], num, karaX, karaY, karaX + moveX, karaY + moveY, subData[1])
                                    ass.write(line)
                                    break
                                else:
                                    if self.layerCheckStatus:
                                        line = 'Dialogue: 0,0:00:00.00,0:00:10.00,%s,#%s,0,0,0,,%s\n' % \
                                        (self.styleNameList[num - 1], num, subData[1])
                                    else:
                                        line = 'Dialogue: %s,0:00:00.00,0:00:10.00,%s,#%s,0,0,0,,%s\n' % \
                                        (subNumber, self.styleNameList[num - 1], num, subData[1])
                                    ass.write(line)
                                    break
            ass.close()

    def generatePreview(self, force=False):
        self.collectArgs()
        if not self.selectedSubDict:
            self.exportSubButton.setEnabled(False)
        else:
            self.exportSubButton.setEnabled(True)
        if not self.videoPath or not self.outputEdit.text():
            self.startButton.setEnabled(False)
        else:
            self.startButton.setEnabled(True)
        if self.decodeArgs != self.old_decodeArgs or self.videoPos != self.old_videoPos or force:
            if os.path.exists('temp_sub.jpg'):
                os.remove('temp_sub.jpg')
            if self.decodeArgs != self.old_decodeArgs:
                self.old_decodeArgs = self.decodeArgs
                self.writeAss()
                if self.subPreview:
                    self.writeAss(self.subPreview, False, True, allSub=True)  # 字幕样式修改的同时修改主界面预览字幕样式
            elif self.videoPos != self.old_videoPos:
                self.old_videoPos = self.videoPos
                self.writeAss(preview=False, pos=self.videoPos)
            else:
                self.writeAss()
            videoWidth = self.setEncode.exportVideoWidth.text()
            videoHeight = self.setEncode.exportVideoHeight.text()
            bit = self.setEncode.exportVideoBitrate.text() + 'k'
            preset = ['veryslow', 'slow', 'medium', 'fast', 'ultrafast'][self.setEncode.exportVideoPreset.currentIndex()]
            cmd = ['ffmpeg.exe', '-y', '-ss', str(self.videoPos), '-i', self.videoPath, '-frames', '1', '-vf', 'ass=temp_sub.ass',
                   '-s', '%sx%s' % (videoWidth, videoHeight), '-b:v', bit, '-preset', preset, '-q:v', '1', '-f', 'image2', 'temp_sub.jpg']
            if not self.videoPath:
                self.preview.setText('请先在主界面选择视频')
                self.preview.setStyleSheet("QLabel{background:white;color:#232629}")
            else:
                p = subprocess.Popen(cmd)
                p.wait()
                pixmap = QPixmap('temp_sub.jpg')
                self.preview.setPixmap(pixmap)
        else:
            pass

    def setEncodeArgs(self):
        self.setEncode.hide()
        self.setEncode.show()

    def exportVideo(self):
        self.startButton.setText('停止')
        self.startButton.setStyleSheet('background-color:#3daee9')
        self.startButton.clicked.disconnect(self.exportVideo)
        self.startButton.clicked.connect(self.terminateEncode)
        self.processBar.setValue(0)
        outputPath = self.outputEdit.text()
        try:
            if os.path.exists(outputPath):
                os.remove(outputPath)
            encodeOK = True
        except:
            self.preview.setText('渲染失败 是否有进程正在占用：\n%s' % outputPath)
            self.preview.setStyleSheet("QLabel{background:white;color:#232629}")
            encodeOK = False
        if encodeOK:
            if os.path.exists('temp_sub.ass'):
                os.remove('temp_sub.ass')
            self.previewTimer.stop()
            self.collectArgs()
            self.writeAss(preview=False)

            videoWidth = self.setEncode.exportVideoWidth.text()
            videoHeight = self.setEncode.exportVideoHeight.text()
            audio = ''
            if self.setEncode.mixAudioPath.text():
                audio = self.setEncode.mixAudioPath.text()
            encoder = self.setEncode.encoder.currentIndex()
            if not encoder:
                preset = ['veryslow', 'slow', 'medium', 'fast', 'ultrafast'][self.setEncode.exportVideoPreset.currentIndex()]
            else:
                preset = ['slow', 'medium', 'fast'][self.setEncode.exportVideoPreset.currentIndex()]
            bit = self.setEncode.exportVideoBitrate.text() + 'k'
            fps = self.setEncode.exportVideoFPS.text()
            cmd = ['ffmpeg.exe', '-y', '-i', self.videoPath]
            if audio:
                cmd += ['-i', audio, '-c:a', 'aac']
            cmd += ['-s', '%sx%s' % (videoWidth, videoHeight), '-preset', preset, '-vf', 'ass=temp_sub.ass']
            if encoder == 1:
                cmd += ['-c:v', 'h264_nvenc']
            elif encoder == 2:
                cmd += ['-c:v', 'hevc_nvenc']
            elif encoder == 3:
                cmd += ['-c:v', 'h264_amf']
            elif encoder == 4:
                cmd += ['-c:v', 'hevc_amf']
            cmd += ['-b:v', bit, '-r', fps]
            cmd.append(outputPath)

            self.videoEncoder = videoEncoder(self.videoPath, cmd)
            self.videoEncoder.processBar.connect(self.setProcessBar)
            self.videoEncoder.currentPos.connect(self.setEncodePreview)
            self.videoEncoder.encodeResult.connect(self.encodeFinish)
            self.videoEncoder.start()

    def setProcessBar(self, value):
        self.processBar.setValue(value)
        self.previewSlider.setValue(value * 10)

    def setEncodePreview(self, currentPos):
        self.writeAss(preview=False, pos=calSubTime(currentPos))
        cmd = ['ffmpeg.exe', '-y', '-ss', currentPos, '-i', self.videoPath, '-frames', '1', '-vf', 'ass=temp_sub.ass', '-q:v', '1', '-f', 'image2', 'temp_sub.jpg']
        p = subprocess.Popen(cmd)
        p.wait()
        pixmap = QPixmap('temp_sub.jpg')
        self.preview.setPixmap(pixmap)

    def encodeFinish(self, result):
        self.startButton.setText('开始压制')
        self.startButton.setStyleSheet('background-color:#31363b')
        self.startButton.clicked.disconnect(self.terminateEncode)
        self.startButton.clicked.connect(self.exportVideo)
        if result:
            self.previewTimer.start()
            self.processBar.setValue(100)
            QMessageBox.information(self, '导出视频', '导出完成', QMessageBox.Yes)
        else:
            self.previewTimer.start()
            self.processBar.setValue(0)
            QMessageBox.information(self, '导出视频', '导出视频失败！请检查参数或编码器是否选择正确', QMessageBox.Yes)
        self.generatePreview(force=True)

    def terminateEncode(self):
        self.startButton.setText('开始压制')
        self.startButton.setStyleSheet('background-color:#31363b')
        self.startButton.clicked.disconnect(self.terminateEncode)
        self.startButton.clicked.connect(self.exportVideo)
        try:
            p = psutil.Process(self.videoEncoder.p.pid)
            for proc in p.children(True):
                proc.kill()
            p.kill()
        except:
            pass
        self.videoEncoder.terminate()
        self.videoEncoder.quit()
        self.videoEncoder.wait()
        del self.videoEncoder
        self.processBar.setValue(0)
        QMessageBox.information(self, '导出视频', '中止导出', QMessageBox.Yes)
        self.generatePreview(force=True)
        self.previewTimer.start()
