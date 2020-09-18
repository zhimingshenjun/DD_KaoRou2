#!/usr/bin/python3
# -*- coding: utf-8 -*-


from PySide2.QtWidgets import QGridLayout, QDialog, QLabel, QApplication
from PySide2.QtCore import Qt


def _translate(context, text, disambig):
    return QApplication.translate(context, text, disambig)


class label(QLabel):
    def __init__(self, txt, parent=None):
        super().__init__(parent)
        self.setText(txt)
        self.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)


class releases(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('版本更新')
        self.resize(400, 200)
        layout = QGridLayout()
        self.setLayout(layout)
        layout.addWidget(label('当前版本'), 0, 0, 1, 1)
        layout.addWidget(label('DD烤肉机2.0.1'), 0, 1, 1, 1)
        layout.addWidget(label('检查更新'), 1, 0, 1, 1)

        releases_url = label('')
        releases_url.setOpenExternalLinks(True)
        releases_url.setText(_translate("MainWindow", "<html><head/><body><p><a href=\"https://github.com/jiafangjun/DD_KaoRou2/releases\">\
        <span style=\" text-decoration: underline; color:#cccccc;\">https://github.com/jiafangjun/DD_KaoRou2/releases</span></a></p></body></html>", None))
        layout.addWidget(releases_url, 1, 1, 1, 1)
