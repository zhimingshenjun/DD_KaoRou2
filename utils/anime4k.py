# -*- coding: utf-8 -*-

import os, subprocess, time, psutil, shutil
from PySide2.QtWidgets import QWidget, QGridLayout, QFileDialog, QDialog, QSlider, QApplication,\
                              QLabel, QPushButton, QHBoxLayout, QLineEdit, QComboBox, QTabWidget, QMessageBox
from PySide2.QtGui import QPixmap, QPainter, QWheelEvent, QMouseEvent
from PySide2.QtCore import Qt, QTimer, QPoint, QThread, Signal, QSize


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


def processingArg(processingTokenList):  # 计算并返回预处理和后处理的参数
    # 中性模糊，平均模糊，CAS锐化，高斯模糊，双向过滤
    processingList = [1, 2, 4, 16, 32]
    tmp = []
    for cnt, token in enumerate(processingTokenList):
        if token:
            tmp.append(processingList[cnt])
    if tmp:
        r = tmp[0]
        for i in tmp[1:]:
            r += i
        return str(r)
    else:
        return None


class label(QLabel):
    def __init__(self, name):
        super().__init__()
        self.setText(name)
        self.setAlignment(Qt.AlignCenter)


class pushButton(QPushButton):
    def __init__(self, name, pushToken=False):
        super().__init__()
        self.setText(name)
        self.pushToken = pushToken
        self.clicked.connect(self.push)

    def push(self):
        self.pushToken = not self.pushToken
        if self.pushToken:  # 按下状态
            self.setStyleSheet('background-color:#3daee9')
        else:
            self.setStyleSheet('background-color:#31363b')


class ImageWithMouseControl(QWidget):
    wheelSignal = Signal(QWheelEvent, QSize)
    moveSignal = Signal(QMouseEvent, QPoint, QPoint)

    def __init__(self, imgPath, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.img = QPixmap(imgPath)
        self.scaled_img = self.img
        self.point = QPoint(0, 0)

    def setImagePath(self, imgPath, scaleSize=''):
        self.img = QPixmap(imgPath)
        if scaleSize:
            self.scaled_img = self.img.scaled(scaleSize)
        else:
            self.scaled_img = self.img
        if self.scaled_img.height() and self.scaled_img.width():
            self.heightScale = 100 * self.scaled_img.height() // self.scaled_img.width()
        else:
            self.heightScale = 56
        self.point = QPoint(0, 0)
        self.update()

    def paintEvent(self, e):
        painter = QPainter()
        painter.begin(self)
        self.draw_img(painter)
        painter.end()

    def recivePaintEvent(self, point):
        painter = QPainter()
        painter.begin(self)
        self.draw_img(painter, point)
        painter.end()

    def draw_img(self, painter, point=''):
        if not point:
            painter.drawPixmap(self.point, self.scaled_img)
        else:
            self.point = point
            painter.drawPixmap(self.point, self.scaled_img)

    def mouseMoveEvent(self, e):  # 重写移动事件
        if self.left_click:
            self._endPos = e.pos() - self._startPos
            self.point = self.point + self._endPos
            self.moveSignal.emit(e, self._startPos, self.point)  # 向主函数发送坐标信息
            self._startPos = e.pos()
            self.repaint()

    def reciveMoveEvent(self, e, startPos):
        self._endPos = e.pos() - startPos
        self.point = self.point + self._endPos
        self._startPos = e.pos()
        self.repaint()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.left_click = True
            self._startPos = e.pos()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.left_click = False

    def wheelEvent(self, e):
        if e.angleDelta().y() < 0:
            # 放大图片
            self.scaled_img = self.img.scaled(self.scaled_img.width() - 100, self.scaled_img.height() - self.heightScale)
            new_w = e.x() - (self.scaled_img.width() * (e.x() - self.point.x())) / (self.scaled_img.width() + 100)
            new_h = e.y() - (self.scaled_img.height() * (e.y() - self.point.y())) / (self.scaled_img.height() + self.heightScale)
            self.point = QPoint(new_w, new_h)
            self.repaint()
        elif e.angleDelta().y() > 0:
            # 缩小图片
            self.scaled_img = self.img.scaled(self.scaled_img.width() + 100, self.scaled_img.height() + self.heightScale)
            try:
                new_w = e.x() - (self.scaled_img.width() * (e.x() - self.point.x())) / (self.scaled_img.width() - 100)
                new_h = e.y() - (self.scaled_img.height() * (e.y() - self.point.y())) / (self.scaled_img.height() - self.heightScale)
                self.point = QPoint(new_w, new_h)
                self.repaint()
            except:
                pass
        self.wheelSignal.emit(e, self.scaled_img.size())

    def reciveWheelEvent(self, e):
        if e.angleDelta().y() < 0:
            # 放大图片
            self.scaled_img = self.img.scaled(self.scaled_img.width() - 100, self.scaled_img.height() - self.heightScale)
            new_w = e.x() - (self.scaled_img.width() * (e.x() - self.point.x())) / (self.scaled_img.width() + 100)
            new_h = e.y() - (self.scaled_img.height() * (e.y() - self.point.y())) / (self.scaled_img.height() + self.heightScale)
            self.point = QPoint(new_w, new_h)
            self.repaint()
        elif e.angleDelta().y() > 0:
            # 缩小图片
            self.scaled_img = self.img.scaled(self.scaled_img.width() + 100, self.scaled_img.height() + self.heightScale)
            try:
                new_w = e.x() - (self.scaled_img.width() * (e.x() - self.point.x())) / (self.scaled_img.width() - 100)
                new_h = e.y() - (self.scaled_img.height() * (e.y() - self.point.y())) / (self.scaled_img.height() - self.heightScale)
                self.point = QPoint(new_w, new_h)
                self.repaint()
            except:
                pass

    def resizeEvent(self, e):
        if self.parent is not None:
            self.scaled_img = self.img.scaled(self.size())
            self.point = QPoint(0, 0)
            self.update()


class preview(QThread):
    finish = Signal()

    def __init__(self, args, parent=None):
        super(preview, self).__init__(parent)
        self.args = args

    def run(self):
        preProcessing = processingArg(self.args['preProcessing'])
        postProcessing = processingArg(self.args['postProcessing'])
        cmd = ['Anime4KCPP_CLI.exe', '-i', 'temp_origin.jpg', '-o', 'temp_4k.jpg', '-p', self.args['passes'],
               '-n', self.args['pushColorCount'], '-c', self.args['strengthColor'], '-g', self.args['strengthGradient'],
               '-z', self.args['zoomFactor'], self.args['fastMode']]
        if preProcessing:
            cmd += ['-b', '-r', preProcessing]
        if postProcessing:
            cmd += ['-a', '-e', postProcessing]
        if self.args['ACNet']:
            cmd += [self.args['ACNet'], self.args['hdnMode']]
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        p.wait()
        self.finish.emit()


class expand(QThread):
    fail = Signal()

    def __init__(self, args, parent=None):
        super(expand, self).__init__(parent)
        self.args = args

    def run(self):
        initToken = True
        try:
            if os.path.exists('temp_video'):
                shutil.rmtree('temp_video')
            os.mkdir('temp_video')
        except:
            try:
                for f in os.listdir('temp_video'):
                    os.remove('temp_video/%s' % f)
            except:
                initToken = False
                self.fail.emit()  # 清空temp_video文件夹失败
        if initToken:
            shutil.copy(self.args['videoPath'], 'temp_video/tempVideo')
            preProcessing = processingArg(self.args['preProcessing'])
            postProcessing = processingArg(self.args['postProcessing'])
            cmd = ['Anime4KCPP_CLI.exe', '-i', 'temp_video/tempVideo', '-o', 'temp_video/tempVideo_4K', '-p', self.args['passes'],
                   '-n', self.args['pushColorCount'], '-c', self.args['strengthColor'], '-g', self.args['strengthGradient'],
                   '-t', self.args['threads'], '-z', self.args['zoomFactor'], self.args['fastMode'], self.args['gpuMode'], '-v']
            if preProcessing:
                cmd += ['-b', '-r', preProcessing]
            if postProcessing:
                cmd += ['-a', '-e', postProcessing]
            if self.args['ACNet']:
                cmd += [self.args['ACNet'], self.args['hdnMode']]
            with open('expand.bat', 'w') as batch:
                batch.write('@echo off\nstart cmd /k "')
                for c in cmd[:-1]:
                    batch.write(c + ' ')
                batch.write(cmd[-1] + '"')
            os.system('expand.bat')
            finish = False
            while not finish:
                for f in os.listdir('temp_video'):
                    if 'tempVideo_4K' in f:
                        finish = True
                        time.sleep(5)
                        shutil.move('temp_video/%s' % f, self.args['outputPath'])
                        shutil.rmtree('temp_video')
                        QMessageBox.information(self, 'Anime4K扩展', '扩展完成', QMessageBox.Ok)
                time.sleep(5)


class Slider(QSlider):
    pointClicked = Signal(QPoint)

    def mousePressEvent(self, event):
        self.pointClicked.emit(event.pos())

    def mouseMoveEvent(self, event):
        self.pointClicked.emit(event.pos())


class Anime4KDialog(QWidget):
    def __init__(self):
        super().__init__()
        screenRect = QApplication.primaryScreen().geometry()
        screenHeight = screenRect.height() * 2 / 3
        screenWidth = screenRect.width() * 3 / 4
        self.resize(screenWidth, screenHeight)
        self.setWindowTitle('Anime4K画质扩展')
        self.showMaximized()
        self.videoPath = ''
        self.outputPath = ''
        self.videoWidth = 0
        self.videoHeight = 0
        # self.scaleSize = QSize(self.videoWidth * 1.5, self.videoHeight * 1.5)
        self.duration = 0
        self.videoPos = 0
        self.gpuMode = ''
        self.acnetMode = ''
        self.hdnMode = ''
        self.processing = [False for _ in range(10)]  # 5种预处理 + 5种后处理

        layout = QGridLayout()
        self.setLayout(layout)

        self.previewTab = QTabWidget()
        layout.addWidget(self.previewTab, 0, 0, 4, 3)

        # self.preview = QLabel('效果预览')
        # self.preview.setFixedSize(screenWidth * 4 / 5, screenWidth * 9 / 20)
        #
        # self.preview.setScaledContents(True)
        # self.preview.setAlignment(Qt.AlignCenter)
        # self.preview.setStyleSheet("QLabel{background:white;}")
        self.preview = ImageWithMouseControl('')
        previewWidget = QWidget()
        previewWidgetLayout = QGridLayout()
        previewWidget.setLayout(previewWidgetLayout)
        previewWidgetLayout.addWidget(self.preview)
        self.previewTab.addTab(previewWidget, '预览')

        compareWidget = QWidget()
        compareLayout = QHBoxLayout()
        compareWidget.setLayout(compareLayout)
        self.originPreview = ImageWithMouseControl('')
        self.scaledPreview = ImageWithMouseControl('')
        self.originPreview.wheelSignal.connect(self.scaledReciveWheelEvent)
        self.originPreview.moveSignal.connect(self.scaledReciveMoveEvent)
        self.scaledPreview.wheelSignal.connect(self.originReciveWheelEvent)
        self.scaledPreview.moveSignal.connect(self.originReciveMoveEvent)
        compareLayout.addWidget(self.originPreview)
        compareLayout.addWidget(self.scaledPreview)
        self.previewTab.addTab(compareWidget, '对比')
        self.previewTab.setCurrentIndex(1)
        self.point = ''

        self.previewSlider = Slider()
        self.previewSlider.setOrientation(Qt.Horizontal)
        self.previewSlider.setMinimum(0)
        self.previewSlider.setMaximum(1000)
        self.previewSlider.pointClicked.connect(self.setPreviewSlider)
        layout.addWidget(self.previewSlider, 4, 0, 1, 3)

        optionWidget = QWidget()
        layout.addWidget(optionWidget, 0, 3, 5, 1)
        optionLayout = QGridLayout()
        optionLayout.setVerticalSpacing(screenHeight / 15)
        optionWidget.setLayout(optionLayout)

        optionLayout.addWidget(QLabel(), 0, 0, 1, 1)
        self.videoPathButton = QPushButton('选择视频')
        self.videoPathButton.clicked.connect(self.selectVideo)
        optionLayout.addWidget(self.videoPathButton, 1, 0, 1, 1)
        self.videoPathEdit = QLineEdit()
        optionLayout.addWidget(self.videoPathEdit, 1, 1, 1, 5)
        self.outputPathButton = QPushButton('输出路径')
        self.outputPathButton.clicked.connect(self.setSavePath)
        optionLayout.addWidget(self.outputPathButton, 2, 0, 1, 1)
        self.outputPathEdit = QLineEdit()
        optionLayout.addWidget(self.outputPathEdit, 2, 1, 1, 5)

        optionLayout.addWidget(label('处理次数'), 3, 0, 1, 1)
        self.passes = QComboBox()
        self.passes.addItems([str(i) for i in range(1, 6)])
        self.passes.setCurrentIndex(1)
        optionLayout.addWidget(self.passes, 3, 1, 1, 1)

        optionLayout.addWidget(label('细化边缘'), 3, 2, 1, 1)
        self.strengthColor = QComboBox()
        self.strengthColor.addItems([str(i) for i in range(11)])
        self.strengthColor.setCurrentIndex(3)
        optionLayout.addWidget(self.strengthColor, 3, 3, 1, 1)

        optionLayout.addWidget(label('细化次数'), 3, 4, 1, 1)
        self.pushColorCount = QComboBox()
        self.pushColorCount.addItems([str(i) for i in range(1, 6)])
        self.pushColorCount.setCurrentIndex(1)
        optionLayout.addWidget(self.pushColorCount, 3, 5, 1, 1)

        optionLayout.addWidget(label('锐化程度'), 4, 0, 1, 1)
        self.strengthGradient = QComboBox()
        self.strengthGradient.addItems([str(i) for i in range(11)])
        self.strengthGradient.setCurrentIndex(10)
        optionLayout.addWidget(self.strengthGradient, 4, 1, 1, 1)

        optionLayout.addWidget(label('放大倍数'), 4, 2, 1, 1)
        self.zoomFactor = QComboBox()
        self.zoomFactor.addItems([str(i * 0.5) for i in range(3, 9)])
        self.zoomFactor.setCurrentIndex(1)
        self.zoomFactor.currentIndexChanged.connect(self.setTip)
        optionLayout.addWidget(self.zoomFactor, 4, 3, 1, 1)

        optionLayout.addWidget(label('快速模式'), 4, 4, 1, 1)
        self.fastMode = QComboBox()
        self.fastMode.addItems(['关闭', '开启'])
        optionLayout.addWidget(self.fastMode, 4, 5, 1, 1)

        preProcessingLabel = QLabel('预处理')
        preProcessingLabel.setAlignment(Qt.AlignCenter)
        optionLayout.addWidget(preProcessingLabel, 5, 0, 1, 1)
        preMedianBlur = pushButton('中性模糊')
        preMedianBlur.clicked.connect(lambda: self.setProcessing(0))
        optionLayout.addWidget(preMedianBlur, 5, 1, 1, 1)
        preMeanBlur = pushButton('平均模糊')
        preMeanBlur.clicked.connect(lambda: self.setProcessing(1))
        optionLayout.addWidget(preMeanBlur, 5, 2, 1, 1)
        preCAS = pushButton('CAS锐化')
        preCAS.clicked.connect(lambda: self.setProcessing(2))
        optionLayout.addWidget(preCAS, 5, 3, 1, 1)
        preGaussianBlur = pushButton('高斯模糊')
        preGaussianBlur.clicked.connect(lambda: self.setProcessing(3))
        optionLayout.addWidget(preGaussianBlur, 5, 4, 1, 1)
        preBilateralFilter = pushButton('双向过滤')
        preBilateralFilter.clicked.connect(lambda: self.setProcessing(4))
        optionLayout.addWidget(preBilateralFilter, 5, 5, 1, 1)

        postProcessingLabel = QLabel('后处理')
        postProcessingLabel.setAlignment(Qt.AlignCenter)
        optionLayout.addWidget(postProcessingLabel, 6, 0, 1, 1)
        postMedianBlur = pushButton('中性模糊')
        postMedianBlur.clicked.connect(lambda: self.setProcessing(5))
        optionLayout.addWidget(postMedianBlur, 6, 1, 1, 1)
        postMeanBlur = pushButton('平均模糊')
        postMeanBlur.clicked.connect(lambda: self.setProcessing(6))
        optionLayout.addWidget(postMeanBlur, 6, 2, 1, 1)
        postCAS = pushButton('CAS锐化')
        postCAS.clicked.connect(lambda: self.setProcessing(7))
        optionLayout.addWidget(postCAS, 6, 3, 1, 1)
        postGaussianBlur = pushButton('高斯模糊')
        postGaussianBlur.clicked.connect(lambda: self.setProcessing(8))
        optionLayout.addWidget(postGaussianBlur, 6, 4, 1, 1)
        postBilateralFilter = pushButton('双向过滤')
        postBilateralFilter.clicked.connect(lambda: self.setProcessing(9))
        optionLayout.addWidget(postBilateralFilter, 6, 5, 1, 1)

        self.decoder = pushButton('GPU加速')
        self.decoder.clicked.connect(self.setGPUMode)
        optionLayout.addWidget(self.decoder, 7, 0, 1, 2)
        self.acnet = pushButton('开启ACNet')
        self.acnet.clicked.connect(self.setACNetMode)
        optionLayout.addWidget(self.acnet, 7, 2, 1, 2)
        self.hdn = pushButton('HDN模式')
        self.hdn.setEnabled(False)
        self.hdn.clicked.connect(self.setHDNMode)
        optionLayout.addWidget(self.hdn, 7, 4, 1, 2)

        threadsLabel = QLabel('线程数')
        threadsLabel.setAlignment(Qt.AlignCenter)
        optionLayout.addWidget(threadsLabel, 8, 0, 1, 1)
        self.threads = QComboBox()
        cpuCount = psutil.cpu_count()
        self.threads.addItems([str(i) for i in range(1, cpuCount + 1)])
        self.threads.setCurrentIndex(cpuCount - 1)
        optionLayout.addWidget(self.threads, 8, 1, 1, 1)

        zoom = float(self.zoomFactor.currentText())
        self.tipLabel = label('扩展后视频分辨率：%d x %d' % (self.videoWidth * zoom, self.videoHeight * zoom))
        optionLayout.addWidget(self.tipLabel, 8, 2, 1, 4)

        self.startButton = QPushButton('开始扩展')
        self.startButton.setStyleSheet('background-color:#3daee9')
        self.startButton.clicked.connect(self.expandVideo)
        self.startButton.setFixedHeight(75)
        optionLayout.addWidget(self.startButton, 9, 0, 2, 6)

        self.args = {'videoPath': self.videoPathEdit.text(), 'outputPath': self.outputPathEdit.text(),
                     'passes': self.passes.currentText(), 'pushColorCount': self.pushColorCount.currentText(),
                     'strengthColor': str(self.strengthColor.currentIndex() / 10), 'strengthGradient': str(self.strengthGradient.currentIndex() / 10),
                     'zoomFactor': self.zoomFactor.currentText(), 'fastMode': '' if self.fastMode.currentIndex() == 0 else '-f',
                     'preProcessing': self.processing[:5], 'postProcessing': self.processing[5:], 'gpuMode': self.gpuMode,
                     'ACNet': self.acnetMode, 'hdnMode': self.hdnMode, 'position': self.videoPos}

        self.timer = QTimer()
        self.timer.setInterval(50)
        self.timer.timeout.connect(self.collectArgs)
        self.timer.start()

    def selectVideo(self):
        videoPath = QFileDialog.getOpenFileName(self, "请选择视频文件", None, "视频文件 (*.mp4 *.avi *.flv);;所有文件(*.*)")[0]
        if videoPath:
            self.videoPathEdit.setText(videoPath)
            self.videoPath = videoPath
            _path, _type = os.path.splitext(self.videoPath)
            self.outputPathEdit.setText(_path + '_Anime4K' + _type)

            cmd = ['ffmpeg.exe', '-i', self.videoPath]
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            p.wait()
            try:
                for l in p.stdout.readlines():  # FFMpeg这蛋疼的视频信息格式
                    l = l.decode('gb18030', 'ignore')
                    if 'Duration' in l:
                        self.duration = calSubTime(l.split(' ')[3][:-1])
                    if 'Stream' in l and 'DAR' in l:
                        args = l.split(',')
                        for resolution in args[2:5]:
                            resolution = resolution.replace(' ', '')
                            if '[' in resolution:
                                resolution = resolution.split('[')[0]
                            if 'x' in resolution:
                                self.videoWidth, self.videoHeight = map(int, resolution.split('x'))
                        break
            except:
                self.duration = 114514  # 万一读取不上来视频长度就先随便分配个
            self.setTip()

    def setSavePath(self):
        outputPath = QFileDialog.getSaveFileName(self, "选择视频输出文件夹", None, "视频文件 (*.mp4 *.avi *.flv);;所有文件(*.*)")[0]
        if outputPath:
            self.outputPathEdit.setText(outputPath)
            self.outputPath = outputPath

    def setDefault(self, videoPath, duration, videoWidth, videoHeight):
        if videoPath:
            self.videoPath = videoPath
            self.duration = duration
            self.videoWidth = videoWidth
            self.videoHeight = videoHeight
            self.videoPathEdit.setText(self.videoPath)
            _path, _type = os.path.splitext(self.videoPath)
            self.outputPathEdit.setText(_path + '_Anime4K' + _type)
            self.setTip()

    def setPreviewSlider(self, p):
        pos = p.x() / self.previewSlider.width() * 1000
        if pos > 1000:
            pos = 1000
        elif pos < 0:
            pos = 0
        self.previewSlider.setValue(pos)
        self.videoPos = pos * self.duration / 1000000

    def setGPUMode(self):
        if not self.gpuMode:
            self.gpuMode = '-q'
        else:
            self.gpuMode = ''

    def setACNetMode(self):
        if not self.acnetMode:
            self.acnetMode = '-w'
            self.hdn.setEnabled(True)
        else:
            self.acnetMode = ''
            self.hdn.setEnabled(False)

    def setHDNMode(self):
        if not self.hdnMode:
            self.hdnMode = '-H'
        else:
            self.hdnMode = ''

    def setProcessing(self, index):
        self.processing[index] = not self.processing[index]

    def setTip(self):
        zoom = float(self.zoomFactor.currentText())
        self.tipLabel.setText('扩展后视频分辨率：%d x %d' % (self.videoWidth * zoom, self.videoHeight * zoom))
        self.scaleSize = QSize(self.videoWidth * zoom, self.videoHeight * zoom)

    def collectArgs(self):
        args = {'videoPath': self.videoPathEdit.text(), 'outputPath': self.outputPathEdit.text(),
                'passes': self.passes.currentText(), 'pushColorCount': self.pushColorCount.currentText(),
                'strengthColor': str(self.strengthColor.currentIndex() / 10), 'strengthGradient': str(self.strengthGradient.currentIndex() / 10),
                'zoomFactor': self.zoomFactor.currentText(), 'fastMode': '' if self.fastMode.currentIndex() == 0 else '-f',
                'preProcessing': self.processing[:5], 'postProcessing': self.processing[5:], 'gpuMode': self.gpuMode,
                'ACNet': self.acnetMode, 'hdnMode': self.hdnMode, 'threads': self.threads.currentText(), 'position': self.videoPos}
        if args != self.args and self.videoPath:
            self.args = args
            self.generatePreview()

    def generatePreview(self):
        cmd = ['ffmpeg.exe', '-y', '-ss', str(self.videoPos), '-i', self.videoPath, '-frames', '1', '-q:v', '1', '-f', 'image2', 'temp_origin.jpg']
        p = subprocess.Popen(cmd)
        p.wait()
        # pixmap = QPixmap('temp_origin.jpg')
        self.preview.setImagePath('temp_origin.jpg', self.scaleSize)
        self.originPreview.setImagePath('temp_origin.jpg', self.scaleSize)
        if self.point:
            self.originPreview.recivePaintEvent(self.point)
        self.previewThread = preview(self.args)
        self.previewThread.finish.connect(self.refreshPreview)
        self.previewThread.start()
        self.previewThread.exec_()

    def refreshPreview(self):
        self.timer.start()
        # pixmap = QPixmap('temp_4k.jpg')
        self.preview.setImagePath('temp_4k.jpg', self.scaleSize)
        self.scaledPreview.setImagePath('temp_4k.jpg', self.scaleSize)
        self.originPreview.setImagePath('temp_origin.jpg', self.scaleSize)
        if self.point:
            self.scaledPreview.recivePaintEvent(self.point)
            self.originPreview.recivePaintEvent(self.point)

    def scaledReciveWheelEvent(self, e, size):
        self.scaleSize = size
        self.scaledPreview.reciveWheelEvent(e)

    def originReciveWheelEvent(self, e, size):
        self.scaleSize = size
        self.originPreview.reciveWheelEvent(e)

    def scaledReciveMoveEvent(self, e, startPos, point):
        self.point = point
        self.scaledPreview.reciveMoveEvent(e, startPos)

    def originReciveMoveEvent(self, e, startPos, point):
        self.point = point
        self.originPreview.reciveMoveEvent(e, startPos)

    def expandVideo(self):
        if not self.args['videoPath']:
            self.tipLabel.setText('请先选择输入视频')
        elif not self.args['outputPath']:
            self.tipLabel.setText('请先选择输出路径')
        else:
            zoom = float(self.zoomFactor.currentText())
            self.tipLabel.setText('扩展后视频分辨率：%d x %d' % (self.videoWidth * zoom, self.videoHeight * zoom))
            
            self.expand = expand(self.args)
            self.expand.fail.connect(self.initFail)
            self.expand.start()

#             with open('expand.bat', 'w') as batch:
#                 batch.write('@echo off\nstart cmd /k "')
#                 for c in cmd[:-1]:
#                     batch.write(c + ' ')
#                 batch.write(cmd[-1] + '"')
#             batch = codecs.open('expand.bat', 'w')
#             batch.write('@echo off\nstart cmd /k "')
#             for c in cmd[:-1]:
#                 batch.write(c + ' ')
#             batch.write(cmd[-1] + '"')
#             batch.close()
#             subprocess.Popen(['expand.bat'])

    def initFail(self):
        errorInfo = "请检查是否有另一个Anime4K进程正在运行，并手动删除烤肉机文件夹下的'temp_video'文件夹，如果存在的话"
        QMessageBox.information(self, '4K扩展初始化失败', errorInfo, QMessageBox.Ok)
