#!/usr/bin/python3
# -*- coding: utf-8 -*-


from PySide2.QtWidgets import QGridLayout, QDialog, QLabel, QApplication
from PySide2.QtCore import Qt


def _translate(context, text, disambig):
    return QApplication.translate(context, text, disambig)


class hotKey_Info(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('快捷键说明')
        self.resize(520, 400)
        layout = QGridLayout()
        self.setLayout(layout)

        key_txt = u'\
q或1 \ w或2\n\n\
e或3 \ r或4\n\n\
c\n\n\
delete\n\n\
space\n\n\
ctrl+s\n\n\
ctrl+z\n\n\
ctrl+y\n\n\
↑ \ ↓\n\n\
← \ →'
        key_label = QLabel(key_txt)
        layout.addWidget(key_label, 0, 0, 3, 1)

        info_txt = u'\
在表格里选中字幕后 ，上沿快速加\减一行，即快速修改字幕开始时间\n\n\
在表格里选中字幕后 ，下沿快速加\减一行，即快速修改字幕结束时间\n\n\
按当前选择位置分割字幕\n\n\
删除表格里选中的字幕\n\n\
播放\暂停视频\n\n\
弹出保存字幕和输出视频页面\n\n\
后退一步\n\n\
前进一步\n\n\
视频音量+ \ -\n\n\
视频进度倒退 \ 前进一行'
        info_label = QLabel(info_txt)
        layout.addWidget(info_label, 0, 1, 3, 4)

        url_label = QLabel(u'更多DD烤肉机视频教程 请前往执鸣神君B站主页')
        layout.addWidget(url_label, 3, 0, 1, 3)

        bilibili_url = QLabel()
        bilibili_url.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        bilibili_url.setOpenExternalLinks(True)
        bilibili_url.setText(_translate("MainWindow", "<html><head/><body><p><a href=\"https://space.bilibili.com/637783\">\
<span style=\" text-decoration: underline; color:#cccccc;\">https://space.bilibili.com/637783</span></a></p></body></html>", None))
        layout.addWidget(bilibili_url, 3, 3, 1, 2)

        git_label = QLabel(u'烤肉机项目开源地址 ')
        layout.addWidget(git_label, 4, 0, 1, 2)

        github_url = QLabel()
        github_url.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        github_url.setOpenExternalLinks(True)
        github_url.setText(_translate("MainWindow", "<html><head/><body><p><a href=\"https://github.com/jiafangjun/DD_KaoRou2\">\
<span style=\" text-decoration: underline; color:#cccccc;\">https://github.com/jiafangjun/DD_KaoRou2</span></a></p></body></html>", None))
        layout.addWidget(github_url, 4, 2, 1, 3)
