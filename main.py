#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
from PySide2.QtWidgets import QApplication, QSplashScreen
from PySide2.QtGui import QFont, QPixmap
from utils.main_ui import MainWindow


if __name__ == '__main__':
    qss = ''
    try:
        with open('utils/qdark.qss', 'r') as f:
            qss = f.read()
    except:
        print('警告！找不到QSS文件！请从github项目地址下载完整文件。')
    app = QApplication(sys.argv)
    app.setStyleSheet(qss)
    app.setFont(QFont('微软雅黑', 9))
    desktop = app.desktop()
    splash = QSplashScreen(QPixmap(r'utils\splash.jpg'))
    splash.show()
    mainWindow = MainWindow()
    screen = app.primaryScreen().geometry()
    mainWindow.resize(screen.width() * 0.75, screen.height() * 0.75)
    size = mainWindow.geometry()
    mainWindow.move((screen.width() - size.width()) / 2,
                    (screen.height() - size.height()) / 2)
    mainWindow.show()
    splash.finish(mainWindow)
    sys.exit(app.exec_())
