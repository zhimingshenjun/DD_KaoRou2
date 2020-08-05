#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os
from PySide2.QtWidgets import QGridLayout, QFileDialog, QDialog, QLabel, QPushButton, QLineEdit
from PySide2.QtGui import QFont
from PySide2.QtCore import Qt, Signal


class exportSubtitle(QDialog):
    exportArgs = Signal(list)

    def __init__(self):
        super().__init__()
        self.subNum = 1
        self.setWindowTitle('字幕裁剪: 第%s列字幕' % self.subNum)
        self.resize(800, 200)
        self.layout = QGridLayout()
        self.setLayout(self.layout)

        self.layout.addWidget(QLabel('视频起始时间: '), 0, 0, 1, 1)
        self.startEdit = QLineEdit('00:00.0')
        self.layout.addWidget(self.startEdit, 0, 1, 1, 1)
        self.startEdit.setAlignment(Qt.AlignRight)
        self.startEdit.setFixedWidth(100)
        self.startEdit.setFont(QFont('Timers', 14))
        self.startEdit.textChanged.connect(self.setSubtStart)
        self.layout.addWidget(QLabel(), 0, 2, 1, 1)

        self.layout.addWidget(QLabel('视频结束时间: '), 0, 3, 1, 1)
        self.endEdit = QLineEdit('00:00.0')
        self.layout.addWidget(self.endEdit, 0, 4, 1, 1)
        self.endEdit.setAlignment(Qt.AlignRight)
        self.endEdit.setFixedWidth(100)
        self.endEdit.setFont(QFont('Timers', 14))
        self.layout.addWidget(QLabel(), 0, 5, 1, 1)

        self.layout.addWidget(QLabel('字幕起始时间: '), 0, 6, 1, 1)
        self.subStartEdit = QLineEdit('00:00.0')
        self.layout.addWidget(self.subStartEdit, 0, 7, 1, 1)
        self.subStartEdit.setAlignment(Qt.AlignRight)
        self.subStartEdit.setFixedWidth(100)
        self.subStartEdit.setFont(QFont('Timers', 14))

        self.outputPath = QLineEdit()
        self.layout.addWidget(self.outputPath, 1, 0, 1, 6)
        self.outputButton = QPushButton('保存路径')
        self.outputButton.setFixedHeight(28)
        self.layout.addWidget(self.outputButton, 1, 6, 1, 1)
        self.outputButton.clicked.connect(self.outputChoose)
        self.startButton = QPushButton('开始导出')
        self.startButton.setFixedHeight(28)
        self.layout.addWidget(self.startButton, 1, 7, 1, 1)
        self.startButton.clicked.connect(self.export)

    def setSubtStart(self, t):
        self.subStartEdit.setText(t)

    def setDefault(self, start, end, subNum):
        self.startEdit.setText(start)
        self.endEdit.setText(end)
        self.subNum = subNum
        self.setWindowTitle('字幕裁剪: 第%s列字幕' % self.subNum)
        if self.outputPath.text():
            fPath, _ = os.path.split(self.outputPath.text())
            self.outputPath.setText(os.path.join(fPath, '未命名_第%s列字幕_%s-%s.srt' % (self.subNum, start.replace(':', '.'), end.replace(':', '.'))))

    def outputChoose(self):
        start = self.startEdit.text().replace('：', ':').replace(':', '.')
        end = self.endEdit.text().replace('：', ':').replace(':', '.')
        subtitlePath = QFileDialog.getSaveFileName(self, "选择输出字幕文件夹", './未命名_第%s列字幕_%s-%s.srt' % (self.subNum, start, end), "字幕文件 (*.srt)")[0]
        if subtitlePath:
            self.outputPath.setText(subtitlePath)

    def export(self):
        start = self.startEdit.text().replace('：', ':')
        end = self.endEdit.text().replace('：', ':')
        subStart = self.subStartEdit.text().replace('：', ':')
        self.exportArgs.emit([start, end, subStart, self.subNum, self.outputPath.text()])
