#!/usr/bin/python3
# -*- coding: utf-8 -*-


import images
import requests
from PySide2.QtWidgets import QGridLayout, QDialog, QLabel, QApplication, QTableWidget, QTableWidgetItem,\
    QAbstractItemView
from PySide2.QtCore import Qt, QUrl, QThread, Signal


def _translate(context, text, disambig):
    return QApplication.translate(context, text, disambig)


class thankToBoss(QThread):
    bossList = Signal(list)

    def __init__(self, parent=None):
        super(thankToBoss, self).__init__(parent)

    def run(self):
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.221 Safari/537.36 SE 2.X MetaSr 1.0'}
        response = requests.get(r'https://github.com/jiafangjun/DD_KaoRou2/blob/master/感谢石油王.csv', headers=headers)
        bossList = []
        html = response.text.split('\n')
        for cnt, line in enumerate(html):
            if 'RMB<' in line:
                boss = html[cnt - 1].split('>')[1].split('<')[0]
                rmb = line.split('>')[1].split('<')[0]
                bossList.append([boss, rmb])
        if bossList:
            self.bossList.emit(bossList)
        else:
            self.bossList.emit([['名单列表获取失败', '']])


class pay(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('赞助和支持')
        self.resize(600, 520)
        layout = QGridLayout()
        self.setLayout(layout)
        txt = u'DD烤肉机由B站up：执鸣神君 业余时间独立开发制作。\n\
\n所有功能全部永久免费给广大烤肉man使用，无需专门找我获取授权。\n\
\n有独立经济来源的老板们如觉得烤肉机好用的话，不妨小小支持亿下\n\
\n一元也是对我继续更新烤肉机的莫大鼓励。十分感谢！\n'
        label = QLabel(txt)
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label, 0, 0, 1, 1)

        bilibili_url = QLabel()
        bilibili_url.setAlignment(Qt.AlignCenter)
        bilibili_url.setOpenExternalLinks(True)
        bilibili_url.setText(_translate("MainWindow", "<html><head/><body><p><a href=\"https://space.bilibili.com/637783\">\
<span style=\" text-decoration: underline; color:#cccccc;\">执鸣神君B站主页: https://space.bilibili.com/637783</span></a></p></body></html>", None))
        layout.addWidget(bilibili_url, 1, 0, 1, 1)

        github_url = QLabel()
        github_url.setAlignment(Qt.AlignCenter)
        github_url.setOpenExternalLinks(True)
        github_url.setText(_translate("MainWindow", "<html><head/><body><p><a href=\"https://github.com/jiafangjun/DD_KaoRou2\">\
<span style=\" text-decoration: underline; color:#cccccc;\">烤肉机项目开源地址: https://github.com/jiafangjun/DD_KaoRou2</span></a></p></body></html>", None))
        layout.addWidget(github_url, 2, 0, 1, 1)

        layout.addWidget(QLabel(), 3, 0, 1, 1)
        alipay = QLabel()
        alipay.setFixedSize(260, 338)
        alipay.setStyleSheet('border-image: url(:/images/0.jpg)')
        layout.addWidget(alipay, 4, 0, 1, 1)
        weixin = QLabel()
        weixin.setFixedSize(260, 338)
        weixin.setStyleSheet('border-image: url(:/images/1.jpg)')
        layout.addWidget(weixin, 4, 1, 1, 1)
        layout.addWidget(QLabel(), 5, 0, 1, 1)

        self.bossTable = QTableWidget()
        self.bossTable.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.bossTable.setRowCount(3)
        self.bossTable.setColumnCount(2)
        for i in range(2):
            self.bossTable.setColumnWidth(i, 105)
        self.bossTable.setHorizontalHeaderLabels(['石油王', '打赏'])
        self.bossTable.setItem(0, 0, QTableWidgetItem('石油王鸣谢名单'))
        self.bossTable.setItem(0, 1, QTableWidgetItem('正在获取...'))
        layout.addWidget(self.bossTable, 0, 1, 3, 1)

        self.thankToBoss = thankToBoss()
        self.thankToBoss.bossList.connect(self.updateBossList)
        self.thankToBoss.start()

    def updateBossList(self, bossList):
        self.bossTable.clear()
        self.bossTable.setColumnCount(2)
        self.bossTable.setRowCount(len(bossList))
        if len(bossList) > 3:
            biggestBossList = []
            for _ in range(3):
                sc = 0
                for cnt, i in enumerate(bossList):
                    money = float(i[1].split(' ')[0])
                    if money > sc:
                        sc = money
                        bossNum = cnt
                biggestBossList.append(bossList.pop(bossNum))
            for y, i in enumerate(biggestBossList):
                self.bossTable.setItem(y, 0, QTableWidgetItem(i[0]))
                self.bossTable.setItem(y, 1, QTableWidgetItem(i[1]))
                self.bossTable.item(y, 0).setTextAlignment(Qt.AlignCenter)
                self.bossTable.item(y, 1).setTextAlignment(Qt.AlignCenter)
            for y, i in enumerate(bossList):
                self.bossTable.setItem(y + 3, 0, QTableWidgetItem(i[0]))
                self.bossTable.setItem(y + 3, 1, QTableWidgetItem(i[1]))
                self.bossTable.item(y + 3, 0).setTextAlignment(Qt.AlignCenter)
                self.bossTable.item(y + 3, 1).setTextAlignment(Qt.AlignCenter)
            self.bossTable.setHorizontalHeaderLabels(['石油王', '打赏'])