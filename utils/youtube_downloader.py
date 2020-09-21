#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os
import time
import shutil
import subprocess
from PySide2.QtWidgets import QGridLayout, QFileDialog, QDialog, QPushButton,\
        QLineEdit, QTableWidget, QTableWidgetItem, QProgressBar, QLabel
from PySide2.QtCore import QTimer, Signal, QThread


class dnldThread(QThread):
    downloading = Signal(str)
    percent = Signal(str)
    done = Signal(str)

    def __init__(self, dnldNum, videoType, resolution, savePath, title, args, url, parent=None):
        super(dnldThread, self).__init__(parent)
        self.dnldNum = dnldNum
        self.videoType = videoType
        self.resolution = resolution
        self.savePath = savePath.replace('/', '\\')
        if not os.path.isdir(self.savePath):
            self.savePath = os.path.split(self.savePath)[0]
        self.title = title
        self.args = args
        self.url = url

    def run(self):
        for cnt, num in enumerate(self.dnldNum):
            modifyName = '%s_%s_%s.%s' % (self.title, num, self.resolution[cnt], self.videoType[cnt])
            outputPath = os.path.join(self.savePath, modifyName.replace(':', ' -'))  # 文件路径里不能带冒号
            if not os.path.exists(outputPath):
                self.downloading.emit(outputPath)
                cmd = ['utils/youtube-dl.exe', '-f', num]
                if not cnt:
                    cmd += self.args
                cmd.append(self.url)
                cmd.append('-o')
                cmd.append(outputPath)
                p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                while p.poll() is None:
                    line = p.stdout.read(100).decode('utf8', 'ignore')
                    print(line)
                    self.percent.emit(line)
                    time.sleep(1)
                # if '?v=' in self.url:
                #     _id = self.url.split('?v=')[-1]
                # else:
                #     _id = self.url.split('/')[-1]
                # if self.savePath != os.getcwd():
                #     for f in os.listdir(os.getcwd()):
                #         if _id in f:
                #             if f.endswith('.vtt') or f.endswith('.srt') or f.endswith('.jpg') or f.endswith('.webp'):
                #                 if os.path.exists(os.path.join(self.savePath, f)):
                #                     os.remove(f)
                #                 else:
                #                     shutil.move(f, self.savePath)
                #             elif f.endswith('.mp4') or f.endswith('.webm') or f.endswith('.m4a') or f.endswith('.part'):
                #                 if os.path.exists(os.path.join(self.savePath, f)):
                #                     os.remove(f)
                #                 else:
                #                     shutil.move(f, outputPath)
                # else:
                #     for f in os.listdir(os.getcwd()):
                #         if _id in f and 'part' not in f and not f.endswith('.vtt') and\
                #         not f.endswith('.srt') and not f.endswith('.jpg') and not f.endswith('.webp'):
                #             if os.path.exists(modifyName):
                #                 os.remove(f)
                #             else:
                #                 os.rename(f, modifyName)
                self.done.emit('单项完成')
            else:
                self.done.emit('文件已存在 跳过')
        self.done.emit('下载完成')


class dnldCheck(QThread):
    searchCnt = Signal(int)
    checkStatus = Signal(bool)
    videoTitle = Signal(str)
    videoResults = Signal(list)

    def __init__(self, url, parent=None):
        super(dnldCheck, self).__init__(parent)
        self.url = url

    def run(self):
        cnt = 0
        p = subprocess.Popen(['utils/youtube-dl.exe', '-e', self.url], stdout=subprocess.PIPE)
        while not p.poll() in [0, 1]:
            cnt += 1
            self.searchCnt.emit(cnt % 3 + 1)
            time.sleep(0.3)
            pass
        if p.poll():
            self.checkStatus.emit(False)
            self.searchCnt.emit(0)
        else:
            self.checkStatus.emit(True)
            title = p.stdout.read().decode('gb18030').strip().replace('/', '_')
            self.videoTitle.emit(title)
            p = subprocess.Popen(['utils/youtube-dl.exe', '-F', self.url], stdout=subprocess.PIPE)
            while not p.poll() in [0, 1]:
                cnt += 1
                self.searchCnt.emit(cnt % 3 + 1)
                time.sleep(0.3)
                pass
            results = p.stdout.read().decode().split('\n')
            self.videoResults.emit(results[::-1])
            self.searchCnt.emit(0)


class YoutubeDnld(QDialog):
    def __init__(self):
        super().__init__()
        self.downloadToken = False
        self.downloadName = ''
        self.downloadPercent = ''
        self.downloadSpeed = ''
        self.oldDownloadPercent = 0
        self.setWindowTitle('Youtube下载器 （此窗口可关闭至后台下载 支持断点下载 需要自备梯子）')
        self.resize(1000, 600)
        self.layout = QGridLayout()
        self.setLayout(self.layout)
        self.tipLabel = QLabel('Youtube链接：')
        self.layout.addWidget(self.tipLabel, 0, 0, 1, 2)
        self.urlInput = QLineEdit('请输入Youtube视频链接')
        self.layout.addWidget(self.urlInput, 0, 2, 1, 5)
        self.searchButton = QPushButton('查询')
        self.searchButton.clicked.connect(self.checkURL)
        self.layout.addWidget(self.searchButton, 0, 7, 1, 1)
        self.searchToken = False
        self.videoInfo = QTableWidget()
        self.videoInfo.verticalHeader().setHidden(True)
        self.videoInfo.setRowCount(10)
        self.videoInfo.setColumnCount(6)
        self.videoInfo.setColumnWidth(0, 100)
        self.videoInfo.setColumnWidth(1, 100)
        self.videoInfo.setColumnWidth(2, 100)
        self.videoInfo.setColumnWidth(3, 100)
        self.videoInfo.setColumnWidth(4, 100)
        self.videoInfo.setColumnWidth(5, 450)
        self.videoInfo.setHorizontalHeaderLabels(['序号', '后缀名', '分辨率', '码率', '类型', '备注'])
        self.layout.addWidget(self.videoInfo, 1, 0, 4, 8)
        self.dnldInput = QLineEdit()
        self.layout.addWidget(self.dnldInput, 5, 0, 1, 2)
        self.dnldLabel = QLabel('输入要下载的视频/音频序号，多个序号用空格隔开    ')
        self.layout.addWidget(self.dnldLabel, 5, 2, 1, 2)

        self.jaCheck = QPushButton('下载日语字幕(自动识别)')
        self.zhCheck = QPushButton('下载中文字幕(油管机翻)')
        self.thumbnailCheck = QPushButton('下载封面')
        self.jaCheck.setStyleSheet('background-color:#3daee9')
        self.zhCheck.setStyleSheet('background-color:#3daee9')
        self.thumbnailCheck.setStyleSheet('background-color:#3daee9')
        self.jaCheckStatus = True
        self.zhCheckStatus = True
        self.thumbnailCheckStatus = True
        self.jaCheck.clicked.connect(self.jaCheckClick)
        self.zhCheck.clicked.connect(self.zhCheckClick)
        self.thumbnailCheck.clicked.connect(self.thumbnailCheckClick)
        self.layout.addWidget(self.jaCheck, 5, 4, 1, 1)
        self.layout.addWidget(self.zhCheck, 5, 5, 1, 1)
        self.layout.addWidget(self.thumbnailCheck, 5, 6, 1, 1)

        self.savePath = QLineEdit()
        self.layout.addWidget(self.savePath, 6, 0, 1, 4)
        self.saveButton = QPushButton('保存路径')
        self.saveButton.setFixedWidth(115)
        self.saveButton.clicked.connect(self.setSavePath)
        self.layout.addWidget(self.saveButton, 6, 4, 1, 1)
        self.processInfo = QLabel()
        self.layout.addWidget(self.processInfo, 6, 5, 1, 2)
        self.progress = QProgressBar()
        self.layout.addWidget(self.progress, 7, 0, 1, 7)
        self.startButton = QPushButton('开始下载')
        self.startButton.setFixedWidth(140)
        self.startButton.setFixedHeight(120)
        self.startButton.setEnabled(False)
        self.startButton.clicked.connect(self.dnldStart)
        self.layout.addWidget(self.startButton, 5, 7, 3, 1)
        self.timer = QTimer()
        self.timer.setInterval(500)
        self.timer.start()
        self.timer.timeout.connect(self.dnldProgress)

    def jaCheckClick(self):
        self.jaCheckStatus = not self.jaCheckStatus
        if self.jaCheckStatus:
            self.jaCheck.setStyleSheet('background-color:#3daee9')
        else:
            self.jaCheck.setStyleSheet('background-color:#31363b')

    def zhCheckClick(self):
        self.zhCheckStatus = not self.zhCheckStatus
        if self.zhCheckStatus:
            self.zhCheck.setStyleSheet('background-color:#3daee9')
        else:
            self.zhCheck.setStyleSheet('background-color:#31363b')

    def thumbnailCheckClick(self):
        self.thumbnailCheckStatus = not self.thumbnailCheckStatus
        if self.thumbnailCheckStatus:
            self.thumbnailCheck.setStyleSheet('background-color:#3daee9')
        else:
            self.thumbnailCheck.setStyleSheet('background-color:#31363b')

    def checkURL(self):
        self.url = self.urlInput.text()
        if self.url:
            if '&' in self.url:
                self.url = self.url.split('&')[0]
            self.videoInfo.clearContents()
            self.dnldCheck = dnldCheck(self.url)
            self.dnldCheck.searchCnt.connect(self.refreshSearchButton)
            self.dnldCheck.checkStatus.connect(self.setCheckStatus)
            self.dnldCheck.videoTitle.connect(self.setTitle)
            self.dnldCheck.videoResults.connect(self.setVideoInfo)
            self.dnldCheck.start()

    def refreshSearchButton(self, cnt):
        if cnt:
            self.searchButton.setText('搜索中' + '.' * cnt)
        else:
            self.searchButton.setText('查询')

    def setCheckStatus(self, checkStatus):
        if not checkStatus:
            self.searchToken = False
            self.videoInfo.setItem(0, 5, QTableWidgetItem('解析错误 请检查视频链接和网络（梯子）是否正确'))
        else:
            self.searchToken = True

    def setTitle(self, title):
        self.title = title
        self.urlInput.setText(title)

    def setVideoInfo(self, results):
        self.videoInfo.setRowCount(len(results) - 4)
        for y, l in enumerate(results[1:-3]):
            l = l.split(' ')
            while '' in l:
                l.remove('')
            if ',' in l:
                l.remove(',')
            if 'tiny' in l:
                l.remove('tiny')
            lineData = l[:2]
            if l[2] == 'audio':
                lineData.append('无')
            else:
                lineData.append('%s %s' % tuple(l[2:4]))
            lineData.append(l[4])
            tip = ''
            for i in l[4:]:
                tip += i + ' '
            if l[2] == 'audio':
                lineData.append('audio only')
            elif 'video only' in tip:
                lineData.append('video only')
            else:
                lineData.append('video + audio')
            lineData.append(tip[:-1])
            for x, data in enumerate(lineData):
                self.videoInfo.setItem(y, x, QTableWidgetItem(data))

    def setSavePath(self):
        savePath = QFileDialog.getExistingDirectory(self, '选择视频保存文件夹')
        if savePath:
            self.savePath.setText(savePath)

    def dnldProgress(self):
        if self.searchToken and self.dnldInput.text() and self.savePath.text():
            self.startButton.setEnabled(True)
        else:
            self.startButton.setEnabled(False)

    def dnldStart(self):
        if not self.downloadToken:
            self.startButton.setText('暂停')
            self.startButton.setStyleSheet('background-color:#3daee9')
            self.processInfo.setText('下载速度：')
            dnldNum = self.dnldInput.text().split(' ')
            videoType = []
            resolution = []
            for num in dnldNum:
                for y in range(self.videoInfo.rowCount()):
                    if self.videoInfo.item(y, 0).text() == num:
                        videoType.append(self.videoInfo.item(y, 1).text())
                        resolution.append(self.videoInfo.item(y, 2).text())
                        break
            savePath = self.savePath.text()
            ja = self.jaCheckStatus
            zh = self.zhCheckStatus
            if ja and zh:
                args = ['--write-auto-sub', '--sub-lang', 'ja,zh-Hans']
            elif ja and not zh:
                args = ['--write-auto-sub', '--sub-lang', 'ja']
            elif zh and not ja:
                args = ['--write-auto-sub', '--sub-lang', 'zh-Hans']
            else:
                args = []
            if self.thumbnailCheckStatus:
                args.append('--write-thumbnail')
            self.dnldThread = dnldThread(dnldNum, videoType, resolution, savePath, self.title, args, self.url)
#             self.dnldThread.downloading.connect(self.dnldName)
            self.dnldThread.percent.connect(self.dnldPercent)
            self.dnldThread.done.connect(self.dnldFinish)
            self.dnldThread.start()
        else:
            self.oldDownloadPercent = 0
            self.processInfo.setText('下载速度：0KiB/s')
            self.startButton.setText('开始下载')
            self.startButton.setStyleSheet('background-color:#31363b')
            self.dnldThread.terminate()
            self.dnldThread.quit()
            self.dnldThread.wait()
        self.downloadToken = not self.downloadToken

#     def dnldName(self, name):
#         print(name)
#         self.savePath.setText(name)

    def dnldPercent(self, percent):
        if r'%' in percent:
            self.downloadPercent = percent.split(r'%')[0].split(' ')[-1]
        if 'B/s' in percent:
            self.downloadSpeed = percent.split('B/s')[0].split(' ')[-1] + 'B/s'
        if '.' in self.downloadSpeed:
            self.processInfo.setText('下载速度：%s' % self.downloadSpeed)
        if self.downloadPercent:
            percent = float(self.downloadPercent)
            if percent > self.oldDownloadPercent:
                self.progress.setValue(percent)
                self.oldDownloadPercent = percent

    def dnldFinish(self, done):
        self.processInfo.setText(done)
        if done == '下载完成':
            self.progress.setValue(0)
            self.oldDownloadPercent = 0
            self.startButton.setText('开始下载')
            self.startButton.setStyleSheet('background-color:#31363b')
            self.dnldThread.terminate()
            self.dnldThread.quit()
            self.dnldThread.wait()
            self.downloadToken = not self.downloadToken
        elif done == '单项完成':
            self.progress.setValue(0)
            self.oldDownloadPercent = 0
