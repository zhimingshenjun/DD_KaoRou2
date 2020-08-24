#!/usr/bin/python3
# -*- coding: utf-8 -*-


import os
from PySide2.QtWidgets import QGridLayout, QDialog, QLabel, QComboBox
from PySide2.QtCore import Qt, Signal


class label(QLabel):
    def __init__(self, txt, parent=None):
        super().__init__(parent)
        self.setText(txt)
        self.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)


class settingPage(QDialog):
    settingSignal = Signal(dict)

    def __init__(self):
        super().__init__()
        self.settingDict = {'tableRefresh': 0,  # 0: 开启, 1: 关闭
                            'tableRefreshFPS': 0,  # 0: 60FPS, 1: 30FPS, 2: 20FPS, 3: 10FPS
                            'graphRefreshFPS': 1,  # 0: 60FPS, 1: 30FPS, 2: 20FPS, 3: 10FPS
                            }

        self.setWindowTitle('设置')
        self.resize(300, 200)
        layout = QGridLayout()
        self.setLayout(layout)

        if os.path.exists('config'):  # 导入已存在的设置
            with open('config', 'r') as cfg:
                for line in cfg:
                    if '=' in line:
                        try:
                            cfgName, cfgValue = line.strip().replace(' ', '').split('=')
                            if cfgName in self.settingDict:
                                self.settingDict[cfgName] = int(cfgValue)
                        except Exception as e:
                            print(str(e))
        self.settingSignal.emit(self.settingDict)  # 发射默认配置给主界面

        layout.addWidget(label('表格进度跟随鼠标'), 0, 0, 1, 1)
        self.tableRefreshCombox = QComboBox()
        self.tableRefreshCombox.addItems(['开启', '关闭'])
        self.tableRefreshCombox.setCurrentIndex(self.settingDict['tableRefresh'])
        self.tableRefreshCombox.currentIndexChanged.connect(self.changeSetting)
        layout.addWidget(self.tableRefreshCombox, 0, 1, 1, 1)

        layout.addWidget(label('限制表格刷新率'), 1, 0, 1, 1)
        self.tableRefreshFPSCombox = QComboBox()
        self.tableRefreshFPSCombox.addItems(['60FPS (有点吃配置)', '30FPS (推荐)', '20FPS', '10FPS'])
        self.tableRefreshFPSCombox.setCurrentIndex(self.settingDict['tableRefreshFPS'])
        self.tableRefreshFPSCombox.currentIndexChanged.connect(self.changeSetting)
        layout.addWidget(self.tableRefreshFPSCombox, 1, 1, 1, 1)

        layout.addWidget(label('限制波形图刷新率'), 2, 0, 1, 1)
        self.graphRefreshFPSCombox = QComboBox()
        self.graphRefreshFPSCombox.addItems(['60FPS (比较吃配置)', '30FPS (推荐)', '20FPS', '10FPS'])
        self.graphRefreshFPSCombox.setCurrentIndex(self.settingDict['graphRefreshFPS'])
        self.graphRefreshFPSCombox.currentIndexChanged.connect(self.changeSetting)
        layout.addWidget(self.graphRefreshFPSCombox, 2, 1, 1, 1)

    def changeSetting(self):
        self.settingDict['tableRefresh'] = self.tableRefreshCombox.currentIndex()
        self.settingDict['tableRefreshFPS'] = self.tableRefreshFPSCombox.currentIndex()
        self.settingDict['graphRefreshFPS'] = self.graphRefreshFPSCombox.currentIndex()
        try:
            with open('config', 'w') as cfg:  # 尝试更新配置文件
                for cfgName, cfgValue in self.settingDict.items():
                    cfg.write('%s=%s\n' % (cfgName, cfgValue))
        except Exception as e:
            print(str(e))
        self.settingSignal.emit(self.settingDict)  # 发射修改后的配置参数给主界面
