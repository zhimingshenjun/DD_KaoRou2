#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os, sys, random, requests
from PySide2.QtWidgets import QApplication, QSplashScreen
from PySide2.QtGui import QFont, QPixmap, QIcon
from PySide2.QtCore import Qt, QThread
from utils.main_ui import MainWindow


class downloadUpdates(QThread):
    def __init__(self, parent=None):
        super(downloadUpdates, self).__init__(parent)
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) \
 Chrome/49.0.2623.221 Safari/537.36 SE 2.X MetaSr 1.0'}

    def checkUtils(self):
        response = requests.get(r'https://github.com/jiafangjun/DD_KaoRou2/tree/master/utils', headers=self.headers)
        html = response.text.split('\n')
        return html

    def downloadSplash(self, html):
        for line in html:
            if '/splash_' in line and '.png' in line:
                splashPage = 'https://github.com/' + line.split('href="')[1].split('"')[0]
                localSplashPath = r'utils/%s' % splashPage.split('/')[-1]
                if not os.path.exists(localSplashPath):
                    response = requests.get(splashPage, headers=self.headers)
                    html = response.text.split('\n')
                    for l in html:
                        if localSplashPath + '?raw=true' in l:
                            splashLink = 'https://github.com' + l.split('src="')[1].split('"')[0]
                            response = requests.get(splashLink)
                            img = response.content
                            with open(localSplashPath, 'wb') as f:
                                f.write(img)  # 将图片按二进制写入本地文件

    def run(self):
        utilsHtml = self.checkUtils()
        self.downloadSplash(utilsHtml)


if __name__ == '__main__':
    qss = ''
    try:
        with open('utils/qdark.qss', 'r') as f:
            qss = f.read()
    except:
        print('警告！找不到QSS文件！请从github项目地址下载完整文件。')
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app = QApplication(sys.argv)
    app.setStyleSheet(qss)
    app.setFont(QFont('微软雅黑', 9))
    desktop = app.desktop()
    splashList = []
    for f in os.listdir('utils'):
        if f.endswith('.png') and 'splash_' in f:
            splashList.append(r'utils\%s' % f)
    if splashList:
        num = random.randint(0, len(splashList) - 1)  # 随机选择启动封面
        print(num)
        splashPath = splashList[num]
    else:
        splashPath = ''
    splash = QSplashScreen(QPixmap(splashPath))
    splash.show()
    mainWindow = MainWindow()
    mainWindow.setWindowIcon(QIcon(r'utils\favicon.ico'))
    screen = app.primaryScreen().geometry()
    mainWindow.resize(screen.width() * 0.75, screen.height() * 0.75)
    size = mainWindow.geometry()
    mainWindow.move((screen.width() - size.width()) / 2,
                    (screen.height() - size.height()) / 2)
    mainWindow.showMaximized()
    mainWindow.show()
    splash.finish(mainWindow)
    downloads = downloadUpdates()
    downloads.start()
    sys.exit(app.exec_())
