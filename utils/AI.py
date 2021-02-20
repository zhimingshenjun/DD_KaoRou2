#!/usr/bin/python3
# -*- coding: utf-8 -*-

import base64
import copy
import enum
import hashlib
import json
import librosa
import numpy as np
import os
import pyqtgraph as pg
import shutil
import sklearn
import subprocess
import time
import urllib.error
import urllib.error
import urllib.parse
import urllib.parse
import urllib.request
import urllib.request
import wave
from PySide2.QtCore import QTimer, Signal, QThread, Qt, QPoint
from PySide2.QtGui import QIntValidator
from PySide2.QtWidgets import QGridLayout, QDialog, QPushButton, QProgressBar, QLabel, QComboBox, QLineEdit, QGroupBox, \
    QWidget, QSlider
from spleeter.audio.adapter import get_default_audio_adapter
from spleeter.separator import Separator


def getWave(audioPath):
    f = wave.open(audioPath, 'rb')  # 开始分析波形
    params = f.getparams()
    nchannels, _, framerate, nframes = params[:4]
    strData = f.readframes(nframes)
    f.close()
    w = np.fromstring(strData, dtype=np.int16)
    w = np.reshape(w, [nframes, nchannels])
    _time = [x * 1000 / framerate for x in range(0, nframes)]
    _wave = list(map(int, w[:, 0]))
    return _time, _wave


def vocalJudge(waveList):
    avg = np.mean(waveList)
    waveList = list(map(lambda x: x - avg, waveList))
    #     thres = -(np.mean(list(map(lambda x: abs(x), waveList))) ** 2) / 2
    dot = 0
    for cnt, i in enumerate(waveList[:-2]):
        #         pre = i * waveList[cnt - 1]
        #         nxt = i * waveList[cnt + 1]
        first = i * waveList[cnt + 1]
        secnd = waveList[cnt + 1] * waveList[cnt + 2]
        #         third = i * waveList[cnt + 2]
        if first < -10000 and secnd < -10000:
            dot += 1
    return dot


def setParams(array, key, value):
    array[key] = value


def genSignString(parser):
    uri_str = ''
    for key in sorted(parser.keys()):
        if key == 'app_key':
            continue
        uri_str += "%s=%s&" % (key, urllib.parse.quote(str(parser[key]), safe=''))
    sign_str = uri_str + 'app_key=' + parser['app_key']

    hash_md5 = hashlib.md5(sign_str.encode())
    return hash_md5.hexdigest().upper()


class Slider(QSlider):
    pointClicked = Signal(QPoint)

    def mousePressEvent(self, event):
        self.pointClicked.emit(event.pos())

    def mouseMoveEvent(self, event):
        self.pointClicked.emit(event.pos())

    def wheelEvent(self, event):  # 把进度条的滚轮事件去了 用啥子滚轮
        pass


class pingTencent(QThread):  # 测试网络
    pingResult = Signal(bool)

    def __init__(self):
        super().__init__()

    def run(self):
        result = os.system('ping www.qq.com')
        if result == 0:
            self.pingResult.emit(True)
        else:
            self.pingResult.emit(False)


class Sources(enum.Enum):
    jp = 0
    en = 1
    kr = 2
    zh = 3


class translateThread(QThread):  # AI翻译线程
    percent = Signal(float)
    result = Signal(list)
    finish = Signal(bool)

    url = 'https://api.ai.qq.com/fcgi-bin/nlp/nlp_speechtranslate'

    def __init__(self, voiceDict: dict, videoStart, videoEnd, source, target, APPID, APPKEY):
        super().__init__()
        self.voiceDict = copy.deepcopy(voiceDict)
        self.videoStart = videoStart
        self.videoEnd = videoEnd
        self.source = Sources(source).value
        self.target = Sources(target).value
        if self.source == 'zh':
            self.interval = 9
        else:
            self.interval = 4
        self.app_id = APPID
        self.app_key = APPKEY
        self.data = {}

    def invoke(self, params):
        self.url_data = urllib.parse.urlencode(params)
        req = urllib.request.Request(self.url, self.url_data.encode())
        try:
            rsp = urllib.request.urlopen(req)
            str_rsp = rsp.read()
            dict_rsp = json.loads(str_rsp)
            return dict_rsp
        except urllib.error.URLError as e:
            dict_error = {"ret": -1, "httpcode": -1, "msg": "Unknown"}
            if hasattr(e, "code"):
                dict_error['httpcode'] = e.code
                dict_error['msg'] = "sdk http post err"
            if hasattr(e, "reason"):
                dict_error['msg'] = e.reason
            else:
                dict_error['msg'] = "system error"
            return dict_error

    def getAISpeech(self, chunk, end_flag, format_id, seq, *args):
        request_header = {
            "app_id": self.app_id,
            "app_key": self.app_key,
            "time_stamp": int(time.time()),
            "nonce_str": int(time.time()),
            "speech_chunk": base64.b64encode(chunk).decode('utf8'),
            "session_id": "DD_KaoRou",
            "end": end_flag,
            "format": format_id,
            "seq": seq,
            "source": self.source,
            "target": self.target,
            "sign": genSignString(self.data),
        }
        return self.invoke(request_header)

    def prepareParams(self, file_path):
        self.data = {}
        seq = 0
        for_mat = 8
        rate = 16000
        bits = 16
        cont_res = 1
        once_size = 50000
        f = open(file_path, 'rb')
        md5obj = hashlib.md5()
        md5obj.update(f.read())
        _hash = md5obj.hexdigest()
        speech_id = str(_hash).upper()
        f.close()
        f = open(file_path, 'rb')
        file_size = os.path.getsize(file_path)
        try:
            while True:
                chunk = f.read(once_size)
                if not chunk:
                    break
                else:
                    chunk_size = len(chunk)
                    if (seq + chunk_size) == file_size:
                        end = 1
                    else:
                        end = 0
                rsp = self.getAISpeech(chunk, speech_id, end, for_mat, rate, bits, seq, chunk_size, cont_res)
                if rsp['msg'] != 'ok':
                    self.sourceText += '翻译未成功 请重试'
                    self.targetText += '翻译未成功 请重试'
                else:
                    self.sourceText += rsp['data']['source_text']
                    self.targetText += rsp['data']['target_text']
                    self.sourceText = '翻译内容识别为空 请重试' if not self.sourceText else self.sourceText
                    self.targetText = '翻译内容识别为空 请重试' if not self.targetText else self.targetText
                seq += chunk_size
        finally:
            f.close()

    def run(self):
        total = len(self.voiceDict.keys())
        for cnt, start in enumerate(self.voiceDict.keys()):
            if start >= 0 and start >= self.videoStart * 60000 and start <= (self.videoEnd + 1) * 60000:  # 开始值不能为负数
                self.sourceText = ''
                self.targetText = ''
                delta = self.voiceDict[start][0]
                cuts, remain = divmod(delta, 10000)
                for _ in range(cuts):
                    cutPath = r'temp_audio\vocals_translate_%s.mp3' % start
                    cmd = ['ffmpeg.exe', '-y', '-i', r'temp_audio\audio_original.aac', '-ss', str(start // 1000), '-t',
                           '10000',
                           '-sample_fmt', 's16', '-ac', '1', '-ar', '16000', cutPath]
                    p = subprocess.Popen(cmd)
                    p.wait()
                    time.sleep(1)
                    start += 10000
                    self.prepareParams(cutPath)
                    time.sleep(self.interval)
                cutPath = r'temp_audio\vocals_translate_%s.mp3' % start
                cmd = ['ffmpeg.exe', '-y', '-i', r'temp_audio\audio_original.aac', '-ss', str(start // 1000), '-t',
                       str(remain // 1000 + 1),
                       '-sample_fmt', 's16', '-ac', '1', '-ar', '16000', cutPath]
                p = subprocess.Popen(cmd)
                p.wait()
                time.sleep(1)  # 等一秒确保音频文件写入硬盘
                self.prepareParams(cutPath)
                time.sleep(self.interval)  # 腾讯这蛋疼的请求间隔 按1s请求就疯狂报错； 如果源语言是中文的话 间隔必须开到10s 否则一直返回重复字符
                self.result.emit([start, delta, self.sourceText, self.targetText])
                self.percent.emit((cnt + 1) / total * 100)
        self.finish.emit(True)


class sepMainAudio(QThread):  # 创建原音轨文件
    mainAudioWave = Signal(list, list)

    def __init__(self, videoPath, duration):
        super().__init__()
        self.videoPath = videoPath
        self.duration = duration

    def run(self):
        if os.path.exists('temp_audio'):  # 创建和清空temp_audio文件夹
            try:
                for i in os.listdir('temp_audio'):
                    os.remove(r'temp_audio\%s' % i)
            except:
                pass
        else:
            os.mkdir('temp_audio')
        timeStamp = time.strftime("%Y_%m_%d_%H_%M_%S", time.localtime(time.time()))
        wavePath = r'temp_audio\main_audio_%s.wav' % timeStamp
        cmd = ['ffmpeg.exe', '-y', '-i', self.videoPath, '-vn', '-ar', '1000', wavePath]
        p = subprocess.Popen(cmd)
        p.wait()
        _time, _wave = getWave(wavePath)
        self.mainAudioWave.emit(_time, _wave)  # 发送主音频波形
        os.remove(wavePath)  # 删除wav文件  太大了
        self.audioPath = r'temp_audio\audio_original.aac'  # 分离原音轨
        if not os.path.exists(self.audioPath):
            cmd = ['ffmpeg.exe', '-y', '-i', self.videoPath, '-vn', '-c', 'copy', self.audioPath]
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            p.wait()
            if p.poll() == 1:  # 复制编码转码出错则按ffmpeg默认编码重新转一遍
                cmd = ['ffmpeg.exe', '-y', '-i', self.videoPath, '-vn', self.audioPath]
                p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


class manualVocalWindow(QWidget):  # 自选阈值弹窗
    def __init__(self):
        super().__init__()
        self.resize(600, 400)
        layout = QGridLayout()
        self.setLayout(layout)

    def plot(self):
        self.graph.plot([1, 2, 3], [1, 2, 3])


class separateQThread(QThread):  # AI分离人声音轨及打轴的核心线程
    position = Signal(int)
    percent = Signal(float)
    voiceList = Signal(list)
    voiceWave = Signal(list, list, list, list, list)
    finish = Signal(bool)
    varList = Signal(list)

    def __init__(self, videoPath, duration, videoStart, videoEnd, before, after, flash, mode, level, multiThread,
                 parent=None):
        super(separateQThread, self).__init__(parent)
        for f in os.listdir('temp_audio'):
            if '_wave' in f:
                temp_wave = r'temp_audio\%s' % f
                if os.path.getsize(temp_wave) < 250000:
                    os.remove(temp_wave)  # 每次开始打轴前删除静音的临时文件
        self.videoPath = videoPath
        self.audioPath = r'temp_audio\audio_original.aac'
        while not os.path.exists(self.audioPath):  # 等待原音轨生成
            time.sleep(0.5)
        self.duration = duration
        self.videoStart = videoStart
        self.videoEnd = videoEnd
        self.before = int(before)
        self.after = int(after)
        self.flash = int(flash)
        self.mode = int(mode)
        self.level = int(level)
        if self.flash < 1:
            self.flash = 1
        if self.after == 0:  # 向后查询至少要等于1
            self.after = 1
        self.separate = Separator('spleeter:2stems', stft_backend='tensorflow', multiprocess=multiThread)
        self.audioLoader = get_default_audio_adapter()
        self.terminalToken = False

    def run(self):
        manualVocalList = []
        cuts = self.duration // 60000 + 1
        preStart = 0  # 前一分钟结尾人声预留
        start = 0  # 人声开始时间
        lastVoiceTime = 0
        voiceWaveTime = []
        voiceWave = []
        bgmWave = []
        voiceWave_smooth = []
        voiceWave_smooth_scale = []
        for cut in range(cuts):
            if cut >= self.videoStart and cut <= self.videoEnd and not self.terminalToken:  # 只分析选中时间区域
                audioPath = 'temp_audio.m4a'
                cmd = ['ffmpeg.exe', '-y', '-i', self.audioPath, '-vn', '-ss', str(cut * 60), '-t', '60', audioPath]
                p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                p.wait()
                for line in p.stdout.readlines():
                    try:
                        line = line.decode('gb18030', 'ignore')
                        if 'Audio:' in line:
                            break
                    except:
                        pass
                try:
                    line = line.lower()
                    for hz in line.split(','):
                        if 'hz' in hz:
                            hz = int(hz.split('hz')[0])
                            break
                except:
                    hz = 44100
                self.separate.separate_to_file(audioPath, '.\\', codec='wav')  # 分离人声音轨
                mp3Path_vocal = r'temp_audio\vocals_wave_%s_temp.mp3' % cut  # 截取转码成mp3格式片段方便上传和播放
                mp3Path_bgm = r'temp_audio\bgm_wave_%s_temp.mp3' % cut  # 背景音转码成mp3格式
                cmd = ['ffmpeg.exe', '-y', '-i', r'temp_audio\vocals.wav', mp3Path_vocal]
                p = subprocess.Popen(cmd)
                p.wait()
                cmd = ['ffmpeg.exe', '-y', '-i', mp3Path_vocal, '-ss', '0', '-t', '60', '-c', 'copy',
                       mp3Path_vocal.replace('_temp', '')]
                p = subprocess.Popen(cmd)  # 裁剪成精确的60s
                p.wait()
                os.remove(mp3Path_vocal)

                cmd = ['ffmpeg.exe', '-y', '-i', r'temp_audio\accompaniment.wav', mp3Path_bgm]
                p = subprocess.Popen(cmd)  # 转码保留背景音轨
                p.wait()
                cmd = ['ffmpeg.exe', '-y', '-i', mp3Path_bgm, '-ss', '0', '-t', '60', '-c', 'copy',
                       mp3Path_bgm.replace('_temp', '')]
                p = subprocess.Popen(cmd)  # 裁剪成精确的60s
                p.wait()
                os.remove(mp3Path_bgm)

                wavePath = r'temp_audio\bgm_downsample.wav'  # 获取bgm音轨波形
                cmd = ['ffmpeg.exe', '-y', '-i', r'temp_audio\accompaniment.wav', '-vn', '-ar', '1000',
                       wavePath]  # 用ffmpeg再降一次采样
                p = subprocess.Popen(cmd)
                p.wait()
                _, _wave = getWave(wavePath)  # 发送人声波形
                if len(_wave) > 60000:
                    _wave = _wave[:60000]
                bgmWave += _wave  # 拼接波形

                wavePath = r'temp_audio\vocals_downsample.wav'  # 获取人声音轨波形
                cmd = ['ffmpeg.exe', '-y', '-i', r'temp_audio\vocals.wav', '-vn', '-ar', '1000',
                       wavePath]  # 用ffmpeg再降一次采样
                p = subprocess.Popen(cmd)
                p.wait()
                _time, _wave = getWave(wavePath)  # 发送人声波形
                if len(_time) > 60000:
                    _time = _time[:60000]  # 裁剪至一分钟
                    _wave = _wave[:60000]
                _time = list(map(lambda x: x + cut * 60000, _time))
                __wave = []  # 全部取绝对值
                for w in _wave:
                    if w < 0:
                        __wave.append(abs(w))
                    else:
                        __wave.append(w)
                wave_smooth = __wave[:5]  # 平滑波形曲线 每10个点取平均
                for i in range(5, len(__wave) - 5):
                    wave_smooth.append(np.mean(__wave[i - 5:i + 6]))
                wave_smooth += __wave[-5:]
                voiceWaveTime += _time  # 拼接时间
                voiceWave += _wave  # 拼接波形

                # 如果采用灵敏模式 进行一步spleeter分离人声特征波形
                if self.mode:
                    waveform, _ = self.audioLoader.load(audioPath, sample_rate=hz)  # 加载音频
                    prediction = self.separate.separate(waveform)  # 核心部分 调用spleeter分离音频
                    msList = []
                    varList = []
                    voiceList = [[-9999, 1000]]
                    hz1000 = hz // 1000  # 1ms
                    for cnt, l in enumerate(prediction['vocals']):  # 只提取人声键值
                        for i in l:
                            msList.append(i)
                        if not cnt % hz1000:  # 每1ms取一次方差
                            varList.append(np.var(msList))
                            msList = []
                    if len(varList) > 60000:  # 裁剪至一分钟
                        varList = varList[:60000]
                    if self.mode == 1:  # 灵敏模式
                        varList = list(sklearn.preprocessing.minmax_scale(varList, axis=0))  # 缩放区间至0-1
                        med = np.median(varList)  # 1分钟内所有方差中位数
                        avg = np.median(varList)  # 1分钟内所有方差平均值
                        thres = avg if avg > med else med
                        # thres /= 2  # 灵敏模式阈值
                    elif self.mode == 2:  # 自选模式
                        manualVocalList += varList  # 将所有方差值先保存至内存
                else:
                    varList = [0 for _ in range(len(_wave) + 10)]
                    thres = 1

                # librosa
                audio_path = r"temp_audio\vocals.wav"
                x, sr = librosa.load(audio_path, sr=None)
                spectral_rolloffs = librosa.feature.spectral_rolloff(x + 0.1, sr=sr)[0]
                frames = range(len(spectral_rolloffs))
                t = list(map(lambda x: x * 500, librosa.frames_to_time(frames)))
                rolloffs_vocal = list(np.interp(list(range(len(_time))), t, spectral_rolloffs))
                rolloffPlusSmooth = []
                for i in range(len(_time)):
                    rolloffPlusSmooth.append((rolloffs_vocal[i] * wave_smooth[i]) ** 0.5)  # 光谱衰减x波形平滑值然后开平方
                voiceWave_smooth += rolloffPlusSmooth
                rolloffPlusSmoothScale = list(sklearn.preprocessing.minmax_scale(rolloffPlusSmooth, axis=0))  # 缩放区间至0-1
                voiceWave_smooth_scale += rolloffPlusSmoothScale

                if self.level == 0:  # 宽松断轴
                    cutLevel = 3600
                elif self.level == 1:  # 中等断轴
                    cutLevel = 1200
                elif self.level == 2:  # 严格断轴
                    cutLevel = 600
                if self.mode != 2:  # 非自选模式
                    voiceList = [[-9999, 1000]]
                    start = 0
                    end = 0  # 人声结束时间
                    cnt = self.before  # 用户设置打轴前侧预留时间(ms)
                    while cnt < len(_wave) - 1:  # 开始判断人声区域
                        rolloffToken = rolloffPlusSmoothScale[cnt] > 0.05 and rolloffPlusSmooth[cnt] > 100
                        waveToken = abs(_wave[cnt]) > 800
                        varToken = varList[cnt] > thres
                        if rolloffToken or waveToken or varToken or preStart:  # 以上条件满足
                            startCnt = copy.deepcopy(cnt)  # 打轴起始计数
                            if preStart:  # 接上一分钟
                                start = preStart
                                preStart = 0
                            if not start:
                                start = cut * 60000 + cnt - self.before  # 开始时间为当前时间-用户前侧留白时间
                            lastVoiceTime = sum(voiceList[-1])
                            if start - lastVoiceTime <= self.flash:  # 向前检测闪轴
                                lastStart, _ = voiceList.pop()
                                voiceList.append([lastStart, start - lastStart])  # 将上一条轴结尾延续到下一条开头
                            # cnt += 10  # +10ms后开始向后查询
                            if cnt < len(_wave) - 1:  # 没超出一分钟则开始往后查询
                                finishToken = False
                                tooLongToken = False
                                while not finishToken:
                                    try:  # 查询超出长度一律跳出循环
                                        while rolloffPlusSmoothScale[cnt] > 0.05 or varList[cnt] > thres:
                                            cnt += 1
                                            if cnt - startCnt > 2000:  # 字幕太长了！！！一旦响度小于轴内最大值/5立刻强制退出
                                                if rolloffPlusSmoothScale[cnt] < 0.2:
                                                    tooLongToken = True
                                                    break
                                        finishToken = True
                                        searchRange = self.after + self.before
                                        smallerThan10 = 0
                                        for _ in range(searchRange):  # 往后查询
                                            cnt += 1
                                            if rolloffPlusSmooth[cnt] < 10 and tooLongToken:
                                                smallerThan10 += 1
                                            else:
                                                smallerThan10 = 0
                                            if smallerThan10 >= searchRange / 2:
                                                break
                                            thresTime = (cnt - startCnt) / cutLevel
                                            if thresTime < 1:
                                                thresTime = 1
                                            if cnt - startCnt <= 2500:
                                                if rolloffPlusSmoothScale[cnt] > 0.1 * thresTime or \
                                                        varList[cnt] > thres * thresTime or \
                                                        rolloffPlusSmoothScale[cnt] > 0.25 or rolloffPlusSmooth[
                                                    cnt] > 100:
                                                    finishToken = False  # 若未触发字幕过长token 则依旧延续字幕轴
                                                    break
                                            elif cnt - startCnt <= 4500:
                                                if rolloffPlusSmoothScale[cnt] > 0.1 * thresTime or \
                                                        varList[cnt] > thres * thresTime or \
                                                        rolloffPlusSmoothScale[cnt] > 0.25:
                                                    finishToken = False  # 若未触发字幕过长token 则依旧延续字幕轴
                                                    break
                                            else:
                                                if rolloffPlusSmoothScale[cnt] > 0.1 * thresTime or \
                                                        varList[cnt] > thres * thresTime:
                                                    finishToken = False  # 若未触发字幕过长token 则依旧延续字幕轴
                                                    break
                                    except:
                                        break
                                if cnt < len(_wave) - self.before - self.after:
                                    for tempCnt in range(self.before + self.after):
                                        tempCnt += cnt
                                        if rolloffPlusSmoothScale[tempCnt] > 0.1 * thresTime or \
                                                varList[tempCnt] > thres * thresTime or \
                                                rolloffPlusSmoothScale[tempCnt] > 0.4:
                                            cnt = tempCnt - self.before
                                            break
                            if cnt < len(_wave):
                                end = cut * 60000 + cnt  # 结束时间即结束向后查询的时间
                                delta = end - start
                                lastStart, lastDelta = voiceList[-1]
                                if lastStart + lastDelta > start:  # 越界检测
                                    lastDelta = start - lastStart  # 修改上一个delta值
                                    voiceList = voiceList[:-1] + [[lastStart, lastDelta]]
                                if self.level == 0:  # 宽松断轴
                                    # 若相邻的两条轴其中一方短于1.25s则连起来
                                    if lastStart + lastDelta >= start - self.flash - 300 and (
                                            lastDelta <= 2000 or delta <= 2000) \
                                            and lastDelta <= 3000 and delta <= 3000:  # 双方中若有一方大于3s则不合并
                                        voiceList = voiceList[:-1] + [[lastStart, end - lastStart]]
                                    else:
                                        voiceList.append([start, delta])  # 添加起止时间给信号槽发送
                                elif self.level == 1:  # 中等断轴
                                    if lastStart + lastDelta >= start - self.flash - 300 and (
                                            lastDelta <= 1500 or delta <= 1500) \
                                            and lastDelta <= 2500 and delta <= 2500:  # 双方中若有一方大于2.5s则不合并
                                        voiceList = voiceList[:-1] + [[lastStart, end - lastStart]]
                                    else:
                                        voiceList.append([start, delta])  # 添加起止时间给信号槽发送
                                elif self.level == 2:  # 严格断轴
                                    if lastStart + lastDelta >= start - self.flash and (
                                            lastDelta <= 800 or delta <= 800) \
                                            and lastDelta <= 1500 and delta <= 1500:  # 双方中若有一方大于1.5s则不合并
                                        voiceList = voiceList[:-1] + [[lastStart, end - lastStart]]
                                    else:
                                        voiceList.append([start, delta])  # 添加起止时间给信号槽发送
                                start = 0
                                cnt += 1
                        else:
                            cnt += 1  # 没检测到人声则+1
                    if cnt >= len(_wave) and start:
                        preStart = start  # 每分钟结尾若超出则传递给下一分钟接着计算
                    else:
                        preStart = 0
                    modifyVoiceList = []
                    for sub in voiceList:
                        if sub[0] >= 0:  # 删除默认的起始时间小于0的轴
                            if sub[1] >= 500:  # 过滤长度小于500ms的碎轴
                                modifyVoiceList.append(sub)
                    self.position.emit(cut + 1)
                    self.percent.emit((cut + 1) / cuts * 100)
                    self.voiceList.emit(modifyVoiceList)
                else:  # 自选模式打轴
                    self.varList.emit(varList)  # 直接发送每分钟的方差列表
                    self.position.emit(cut + 1)
                    self.percent.emit((cut + 1) / cuts * 100)
            else:  # 未选中的时间区域
                if cut == cuts - 1:
                    mp3Path_vocal = r'temp_audio\vocals_wave_%s.mp3' % cut  # 创建静音文件填补空白
                    remain = self.duration % 60000
                    cmd = ['ffmpeg.exe', '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=mono', '-t', str(remain / 1000),
                           '-q:a', '9',
                           '-acodec', 'libmp3lame', '-y', mp3Path_vocal]
                    p = subprocess.Popen(cmd)
                    p.wait()
                    shutil.copy(mp3Path_vocal, mp3Path_vocal.replace('vocals', 'bgm'))  # 复制一份作为静音bgm片段
                    voiceWaveTime += [x + cut * 60000 for x in range(remain)]
                    zeroList = [0 for _ in range(remain)]
                    voiceWave += zeroList
                    voiceWave_smooth += zeroList
                    voiceWave_smooth_scale += zeroList
                    bgmWave += zeroList
                    self.percent.emit((cut + 1) / cuts * 100)
                    if self.mode == 2:  # 自选模式
                        manualVocalList += [0 for _ in range(remain)]
                        self.varList.emit([0 for _ in range(remain)])
                else:
                    mp3Path_vocal = r'temp_audio\vocals_wave_%s.mp3' % cut  # 创建静音文件填补空白
                    cmd = ['ffmpeg.exe', '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=mono', '-t', '60', '-q:a', '9',
                           '-acodec', 'libmp3lame', '-y', mp3Path_vocal]
                    p = subprocess.Popen(cmd)
                    p.wait()
                    shutil.copy(mp3Path_vocal, mp3Path_vocal.replace('vocals', 'bgm'))  # 复制一份作为静音bgm片段
                    voiceWaveTime += [x + cut * 60000 for x in range(60000)]
                    zeroList = [0 for _ in range(60000)]
                    voiceWave += zeroList
                    voiceWave_smooth += zeroList
                    voiceWave_smooth_scale += zeroList
                    bgmWave += zeroList
                    self.percent.emit((cut + 1) / cuts * 100)
                    if self.mode == 2:  # 自选模式
                        manualVocalList += [0 for _ in range(60000)]
                        self.varList.emit([0 for _ in range(60000)])
        self.voiceWave.emit(voiceWaveTime, voiceWave, voiceWave_smooth, voiceWave_smooth_scale, bgmWave)
        with open('vocalsList.txt', 'w') as f:  # 合并mp3
            for cut in range(cuts):
                f.write('file temp_audio/vocals_wave_%s.mp3\n' % cut)
        with open('bgmList.txt', 'w') as f:  # 合并mp3
            for cut in range(cuts):
                f.write('file temp_audio/bgm_wave_%s.mp3\n' % cut)
        cmd = ['ffmpeg.exe', '-y', '-f', 'concat', '-safe', '0', '-i', 'vocalslist.txt', '-c', 'copy',
               r'temp_audio\vocals.mp3']
        subprocess.Popen(cmd)
        cmd = ['ffmpeg.exe', '-y', '-f', 'concat', '-safe', '0', '-i', 'bgmList.txt', '-c', 'copy',
               r'temp_audio\bgm.mp3']
        subprocess.Popen(cmd)
        self.finish.emit(True)


class reprocessSub(QDialog):
    def __init__(self, videoStart, videoEnd, index):
        super().__init__()
        self.resize(400, 40)
        self.setWindowTitle('修改第%s —— %s分钟时轴至第%s列字幕轨道' % (videoStart, videoEnd, index + 1))
        layout = QGridLayout()
        self.setLayout(layout)
        self.processBar = QProgressBar()
        layout.addWidget(self.processBar)


class reprocessQThread(QThread):  # 自选模式下 AI分离人声音轨及打轴的核心线程
    percent = Signal(float)
    voiceList = Signal(list)

    def __init__(self, before, after, flash, level, thres, videoStart, voiceWave, voiceWave_smooth_scale,
                 voiceWave_smooth, varList, parent=None):
        super(reprocessQThread, self).__init__(parent)
        self.before = int(before)
        self.after = int(after)
        self.flash = int(flash)
        self.level = level
        self.thres = thres
        self.videoStart = videoStart
        self.voiceWave = voiceWave
        self.voiceWave_smooth_scale = voiceWave_smooth_scale
        self.voiceWave_smooth = voiceWave_smooth
        self.varList = varList

    def run(self):
        if self.level == 0:  # 宽松断轴
            cutLevel = 3600
        elif self.level == 1:  # 中等断轴
            cutLevel = 1200
        elif self.level == 2:  # 严格断轴
            cutLevel = 600
        end = 0
        cnt = self.before  # 用户设置打轴前侧预留时间(ms)
        voiceList = [[-9999, 1000]]
        while cnt < len(self.voiceWave) - 1:  # 开始判断人声区域
            if not cnt % 3000:
                self.percent.emit(cnt / (len(self.voiceWave) - 1) * 100)
            rolloffToken = self.voiceWave_smooth[cnt] > 800
            varToken = self.varList[cnt] > self.thres  # 大于用户手动选择的阈值
            if rolloffToken or varToken:  # 以上条件满足
                startCnt = copy.deepcopy(cnt)  # 打轴起始计数
                start = cnt - self.before  # 开始时间为当前时间-用户前侧留白时间
                lastVoiceTime = sum(voiceList[-1])
                if start - lastVoiceTime <= self.flash:  # 向前检测闪轴
                    lastStart, _ = voiceList.pop()
                    voiceList.append([lastStart, start - lastStart])  # 将上一条轴结尾延续到下一条开头
                if cnt < len(self.voiceWave) - 1:  # 没超出一分钟则开始往后查询
                    finishToken = False
                    tooLongToken = False
                    while not finishToken:
                        try:  # 查询超出长度一律跳出循环
                            while self.varList[cnt] > self.thres:
                                cnt += 1
                                if cnt - startCnt > 2000:  # 字幕太长了！！！一旦响度小于轴内最大值/5立刻强制退出
                                    if self.voiceWave_smooth_scale[cnt] < 0.2:
                                        tooLongToken = True
                                        break
                            finishToken = True
                            searchRange = self.after + self.before
                            smallerThan10 = 0
                            for _ in range(searchRange):  # 往后查询
                                cnt += 1
                                if self.voiceWave_smooth[cnt] < 10 and tooLongToken:
                                    smallerThan10 += 1
                                else:
                                    smallerThan10 = 0
                                if smallerThan10 >= searchRange / 2:
                                    break
                                thresTime = (cnt - startCnt) / cutLevel
                                if thresTime < 1:
                                    thresTime = 1
                                if cnt - startCnt <= 4500:
                                    if self.varList[cnt] > self.thres * thresTime or \
                                            self.voiceWave_smooth_scale[cnt] > 0.1 * thresTime or \
                                            self.voiceWave_smooth_scale[cnt] > 0.25:
                                        finishToken = False  # 若未触发字幕过长token 则依旧延续字幕轴
                                        break
                                else:
                                    if self.varList[cnt] > self.thres * thresTime or \
                                            self.voiceWave_smooth_scale[cnt] > 0.1 * thresTime:
                                        finishToken = False  # 若未触发字幕过长token 则依旧延续字幕轴
                                        break
                        except:
                            break
                    for tempCnt in range(self.before + self.after):
                        tempCnt += cnt
                        if self.varList[tempCnt] > self.thres * thresTime or \
                                self.voiceWave_smooth_scale[tempCnt] > 0.1 * thresTime or \
                                self.voiceWave_smooth_scale[tempCnt] > 0.25:
                            cnt = tempCnt - self.before
                            break
                end = cnt  # 结束时间即结束向后查询的时间
                delta = end - start
                lastStart, lastDelta = voiceList[-1]
                if lastStart + lastDelta > start:  # 越界检测
                    lastDelta = start - lastStart  # 修改上一个delta值
                    voiceList = voiceList[:-1] + [[lastStart, lastDelta]]
                if self.level == 0:  # 宽松断轴
                    # 若相邻的两条轴其中一方短于1.25s则连起来
                    if lastStart + lastDelta >= start - self.flash - 300 and (lastDelta <= 2000 or delta <= 2000) \
                            and lastDelta <= 3000 and delta <= 3000:  # 双方中若有一方大于3s则不合并
                        voiceList = voiceList[:-1] + [[lastStart, end - lastStart]]
                    else:
                        voiceList.append([start, delta])  # 添加起止时间给信号槽发送
                elif self.level == 1:  # 中等断轴
                    if lastStart + lastDelta >= start - self.flash - 300 and (lastDelta <= 1500 or delta <= 1500) \
                            and lastDelta <= 2500 and delta <= 2500:  # 双方中若有一方大于2.5s则不合并
                        voiceList = voiceList[:-1] + [[lastStart, end - lastStart]]
                    else:
                        voiceList.append([start, delta])  # 添加起止时间给信号槽发送
                elif self.level == 2:  # 严格断轴
                    if lastStart + lastDelta >= start - self.flash and (lastDelta <= 800 or delta <= 800) \
                            and lastDelta <= 1500 and delta <= 1500:  # 双方中若有一方大于1.5s则不合并
                        voiceList = voiceList[:-1] + [[lastStart, end - lastStart]]
                    else:
                        voiceList.append([start, delta])  # 添加起止时间给信号槽发送
                cnt += 1
            else:
                cnt += 1  # 没检测到人声则+1
        modifyVoiceList = []
        for sub in voiceList:
            if sub[0] >= 0:  # 删除默认的起始时间小于0的轴
                sub[0] += self.videoStart * 60000
                if sub[1] >= 500:  # 过滤长度小于500ms的碎轴
                    modifyVoiceList.append(sub)
        self.voiceList.emit(modifyVoiceList)
        self.percent.emit(100)


class Separate(QDialog):  # 界面
    videoPath = ''
    duration = 60000
    processToken = False
    voiceList = Signal(list)
    voiceWave_graph = Signal(list, list, list)
    tablePreset = Signal(list)
    translateResult = Signal(list)
    clearSub = Signal(int, int, int)  # 清空轴 传的是轴序号, 起始分钟, 结束分钟
    multipleThread = False  # 写死单进程

    def __init__(self):
        super().__init__()
        self.settingDict = {'before': 30,  # 前侧留白
                            'after': 300,  # 后侧留白
                            'flash': 300,  # 防止闪轴
                            'mode': 0,  # 打轴模式 0: 快速, 1: 灵敏, 2: 自选
                            'level': 1,  # 断轴标准 0: 宽松, 1: 正常, 2: 严格
                            'fill': 'AI自动打轴',
                            }
        if os.path.exists('config'):  # 导入已存在的设置
            with open('config', 'r') as cfg:
                for line in cfg:
                    if '=' in line:
                        try:
                            cfgName, cfgValue = line.strip().replace(' ', '').split('=')
                            self.settingDict[cfgName] = cfgValue
                        except Exception as e:
                            print(str(e))

        self.resize(1000, 200)
        self.setWindowTitle('AI智能打轴')
        layout = QGridLayout()
        self.setLayout(layout)
        self.varList = []
        layout.addWidget(QLabel('视频/音频开始时间'), 0, 0, 1, 1)
        self.videoStart = QComboBox()
        self.videoStart.setMaximumWidth(100)
        layout.addWidget(self.videoStart, 0, 1, 1, 1)
        layout.addWidget(QLabel(), 0, 2, 1, 1)
        layout.addWidget(QLabel('视频/音频结束时间'), 0, 3, 1, 1)
        self.videoEnd = QComboBox()
        self.videoEnd.setMaximumWidth(100)
        layout.addWidget(self.videoEnd, 0, 4, 1, 1)
        endMinute, remain = divmod(self.duration, 60000)
        endMinute = endMinute + 1 if not remain else endMinute + 2
        self.videoStart.addItems(['第%s分钟' % i for i in range(0, endMinute - 1)])
        self.videoStart.setCurrentIndex(0)
        self.videoStart.currentIndexChanged.connect(self.resetStartEnd)
        self.videoEnd.addItems(['第%s分钟' % i for i in range(1, endMinute)])
        self.videoEnd.setCurrentIndex(endMinute - 1)
        self.videoEnd.currentIndexChanged.connect(self.refreshGraph)

        trackGroup = QGroupBox('AI自动打轴')  # 自动打轴部分
        trackLayout = QGridLayout()
        trackGroup.setLayout(trackLayout)
        layout.addWidget(trackGroup, 1, 0, 2, 5)

        beforeLabel = QLabel('  前侧留白(ms)')
        beforeLabel.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        trackLayout.addWidget(beforeLabel, 0, 0, 1, 1)
        self.beforeEdit = QLineEdit(str(self.settingDict['before']))
        self.beforeEdit.textChanged.connect(self.changeSetting)
        validator = QIntValidator()
        validator.setRange(0, 5000)
        self.beforeEdit.setValidator(validator)
        self.beforeEdit.setFixedWidth(50)
        trackLayout.addWidget(self.beforeEdit, 0, 1, 1, 1)

        afterLabel = QLabel('  后侧留白(ms)')
        afterLabel.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        trackLayout.addWidget(afterLabel, 0, 2, 1, 1)
        self.afterEdit = QLineEdit(str(self.settingDict['after']))
        self.afterEdit.textChanged.connect(self.changeSetting)
        self.afterEdit.setValidator(validator)
        self.afterEdit.setFixedWidth(50)
        trackLayout.addWidget(self.afterEdit, 0, 3, 1, 1)

        antiFlashLabel = QLabel('  防止闪轴(ms)')
        antiFlashLabel.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        trackLayout.addWidget(antiFlashLabel, 0, 4, 1, 1)
        self.antiFlash = QLineEdit(str(self.settingDict['flash']))
        self.antiFlash.textChanged.connect(self.changeSetting)
        self.antiFlash.setValidator(validator)
        self.antiFlash.setFixedWidth(50)
        trackLayout.addWidget(self.antiFlash, 0, 5, 1, 1)

        trackModeLabel = QLabel('  打轴模式')
        trackModeLabel.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        trackLayout.addWidget(trackModeLabel, 0, 6, 1, 1)
        self.trackMode = QComboBox()
        self.trackMode.addItems(['快速', '灵敏', '自选'])
        self.trackMode.setCurrentIndex(int(self.settingDict['mode']))
        self.trackMode.currentIndexChanged.connect(self.changeSetting)
        self.trackMode.currentIndexChanged.connect(self.showGraph)
        trackLayout.addWidget(self.trackMode, 0, 7, 1, 1)

        cutLabel = QLabel('  断轴标准')
        cutLabel.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        trackLayout.addWidget(cutLabel, 0, 8, 1, 1)
        self.cutLevel = QComboBox()
        self.cutLevel.addItems(['宽松', '正常', '严格'])
        self.cutLevel.setCurrentIndex(int(self.settingDict['level']))
        self.cutLevel.currentIndexChanged.connect(self.changeSetting)
        trackLayout.addWidget(self.cutLevel, 0, 9, 1, 1)
        fillLabel = QLabel('  填充字符')
        fillLabel.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        trackLayout.addWidget(fillLabel, 0, 10, 1, 1)
        self.fillWord = QLineEdit()
        self.fillWord.setMinimumWidth(100)
        self.fillWord.setText(str(self.settingDict['fill']))
        self.fillWord.textChanged.connect(self.changeSetting)
        trackLayout.addWidget(self.fillWord, 0, 11, 1, 1)
        self.outputIndex = QComboBox()
        self.outputIndex.addItems(['输出至第%s列' % i for i in range(1, 6)])
        trackLayout.addWidget(self.outputIndex, 0, 12, 1, 1)
        self.processBar = QProgressBar()
        trackLayout.addWidget(self.processBar, 1, 0, 1, 12)
        self.checkButton = QPushButton('开始')
        self.checkButton.setFixedWidth(100)
        self.checkButton.clicked.connect(self.separateProcess)
        trackLayout.addWidget(self.checkButton, 1, 12, 1, 1)

        self.levelGraph = pg.PlotWidget()  # 自选模式下的方差图
        self.levelGraph.setMenuEnabled(False)
        trackLayout.addWidget(self.levelGraph, 2, 0, 1, 13)
        self.levelGraph.hide()
        self.levelSlider = Slider()  # 自选阈值滑动轴
        self.levelSlider.setOrientation(Qt.Horizontal)
        self.levelSlider.setMaximum(self.levelSlider.width())
        self.levelSlider.setFixedWidth(self.levelSlider.width())
        self.levelSlider.pointClicked.connect(self.refreshLevelLine)
        trackLayout.addWidget(self.levelSlider, 3, 0, 1, 11)
        self.levelSlider.hide()
        self.levelEdit = QLabel()  # 显示和修改当前阈值
        trackLayout.addWidget(self.levelEdit, 3, 11, 1, 1)
        self.levelEdit.hide()
        self.levelConfirm = QPushButton('使用该阈值')
        self.levelConfirm.clicked.connect(self.resetSubtitle)  # 按照用户手选阈值重置字幕轴
        self.levelConfirm.setEnabled(False)  # 禁用确认阈值按钮
        trackLayout.addWidget(self.levelConfirm, 3, 12, 1, 1)
        self.levelConfirm.hide()

        translateGroup = QGroupBox('AI语音翻译 (注意：腾讯旧版翻译接口现已关闭新用户注册，此功能已处于半废弃状态，预留等以后新接口出现)')  # 自动翻译部分
        translateLayout = QGridLayout()
        translateGroup.setLayout(translateLayout)
        # layout.addWidget(translateGroup, 3, 0, 2, 5)

        self.sourceLanguage = QComboBox()
        self.sourceLanguage.addItems(['源语言 - 日语 ', '源语言 - 英语 ', '源语言 - 韩语 ', '源语言 - 中文'])
        translateLayout.addWidget(self.sourceLanguage, 0, 0, 1, 2)
        self.sourceOutput = QComboBox()
        self.sourceOutput.addItems(['输出至第%s列' % i for i in range(1, 6)] + ['不保存'])
        self.sourceOutput.setCurrentIndex(5)
        translateLayout.addWidget(self.sourceOutput, 0, 2, 1, 1)

        self.targetLanguage = QComboBox()
        self.targetLanguage.addItems(['目标语言 - 日语 ', '目标语言 - 英语 ', '目标语言 - 韩语 ', '目标语言 - 中文'])
        self.targetLanguage.setCurrentIndex(3)
        translateLayout.addWidget(self.targetLanguage, 1, 0, 1, 2)
        self.targetOutput = QComboBox()
        self.targetOutput.addItems(['翻译第%s列' % i for i in range(1, 6)])
        translateLayout.addWidget(self.targetOutput, 1, 2, 1, 1)

        self.tipLabel = QLabel('腾讯AI翻译(需联网)  翻译前请确认翻译列有打好的轴。  APPID、APPKEY申请地址: https://ai.qq.com/')
        self.tipLabel.setTextInteractionFlags(Qt.TextSelectableByMouse)
        translateLayout.addWidget(self.tipLabel, 0, 4, 1, 7)

        self.APPID = ''
        self.APPKEY = ''
        if os.path.exists('translate_account.log'):  # 检测账号信息
            try:
                with open('translate_account.log', 'r') as f:
                    f = f.readlines()
                self.APPID = f[0].strip()
                self.APPKEY = f[1].strip()
            except:
                pass
        translateLayout.addWidget(QLabel('APPID'), 1, 4, 1, 1)
        self.APPIDEdit = QLineEdit(self.APPID)
        translateLayout.addWidget(self.APPIDEdit, 1, 5, 1, 2)
        translateLayout.addWidget(QLabel('APPKEY'), 1, 8, 1, 1)
        self.APPKEYEdit = QLineEdit(self.APPKEY)
        translateLayout.addWidget(self.APPKEYEdit, 1, 9, 1, 2)

        self.translateProcessBar = QProgressBar()
        translateLayout.addWidget(self.translateProcessBar, 2, 0, 1, 10)
        self.translateButton = QPushButton('开始')
        self.translateButton.setFixedWidth(100)
        #         self.translateButton.setEnabled(False)
        self.translateButton.clicked.connect(self.startTranslate)
        translateLayout.addWidget(self.translateButton, 2, 10, 1, 1)
        self.networkToken = False
        self.translateToken = False
        self.voiceDict = {}
        # self.ping = pingTencent()  # 检查网络线程
        # self.ping.pingResult.connect(self.checkNetwork)
        # self.ping.start()

    def setDefault(self, videoPath, duration, subtitleDict):
        self.videoPath = videoPath
        self.duration = duration
        self.subtitleDict = subtitleDict
        self.resetStartEnd()

    def changeSetting(self):
        self.settingDict = {'before': self.beforeEdit.text(),  # 前侧留白
                            'after': self.afterEdit.text(),  # 后侧留白
                            'flash': self.antiFlash.text(),  # 防止闪轴
                            'mode': self.trackMode.currentIndex(),  # 打轴模式 0: 快速, 1: 灵敏, 2: 自选
                            'level': self.cutLevel.currentIndex(),  # 断轴标准 0: 宽松, 1: 正常, 2: 严格
                            'fill': self.fillWord.text(),
                            }
        try:
            with open('config', 'w') as cfg:  # 尝试更新配置文件
                for cfgName, cfgValue in self.settingDict.items():
                    cfg.write('%s=%s\n' % (cfgName, cfgValue))
        except Exception as e:
            print(str(e))

    def showGraph(self, index):  # 隐藏或显示阈值图
        if index != 2:
            self.levelGraph.hide()
            self.levelSlider.hide()
            self.levelEdit.hide()
            self.levelConfirm.hide()
            self.resize(1000, 200)
        else:
            self.levelGraph.show()
            self.levelSlider.show()
            self.levelEdit.show()
            self.levelConfirm.show()
            self.resize(1000, 650)

    def resetStartEnd(self, startIndex=0):  # 重置视频起止时间
        self.videoStart.currentIndexChanged.disconnect(self.resetStartEnd)  # 清空combobox前要断开signal 否则会崩溃
        self.videoEnd.currentIndexChanged.disconnect(self.refreshGraph)
        old_endIndex = self.videoEnd.currentIndex()
        self.videoStart.clear()
        self.videoEnd.clear()
        endMinute, remain = divmod(self.duration, 60000)
        endMinute = endMinute + 1 if not remain else endMinute + 2
        self.videoStart.addItems(['第%s分钟' % i for i in range(0, endMinute - 1)])
        self.videoStart.setCurrentIndex(startIndex)
        endIndex = old_endIndex if old_endIndex >= startIndex else endMinute - 2
        self.videoEnd.addItems(['第%s分钟' % i for i in range(1, endMinute)])
        for i in range(startIndex):
            self.videoEnd.model().item(i).setEnabled(False)
        self.videoEnd.setCurrentIndex(endIndex)
        self.videoStart.currentIndexChanged.connect(self.resetStartEnd)
        self.videoEnd.currentIndexChanged.connect(self.refreshGraph)
        self.refreshGraph()

    def separateProcess(self):
        if self.videoPath:
            self.processToken = not self.processToken
            if self.processToken:
                self.processBar.setValue(0)
                self.checkButton.setText('初始化中')
                if not self.beforeEdit.text():
                    self.beforeEdit.setText('0')
                self.before = self.beforeEdit.text()
                if not self.afterEdit.text():
                    self.afterEdit.setText('0')
                self.after = self.afterEdit.text()
                if not self.antiFlash.text():
                    self.antiFlash.setText('0')
                self.flash = self.antiFlash.text()
                mode = self.trackMode.currentIndex()
                self.level = self.cutLevel.currentIndex()
                try:
                    fillWord = self.fillWord.text()
                except:
                    fillWord = ' '
                index = self.outputIndex.currentIndex()
                videoStart = self.videoStart.currentIndex()
                videoEnd = self.videoEnd.currentIndex()
                self.sepProc = separateQThread(self.videoPath, self.duration, videoStart, videoEnd, self.before,
                                               self.after, self.flash, mode, self.level, self.multipleThread)
                self.sepProc.position.connect(self.setTitle)  # 设置标题分析至第几分钟
                self.sepProc.percent.connect(self.setProgressBar)  # 设置滚动条进度
                self.sepProc.voiceList.connect(self.sendVoiceList)  # 二次传球给主界面标记表格
                self.sepProc.voiceWave.connect(self.sendVoiceWave)  # 二次传球给主界面绘制人声音频图
                self.clearSub.emit(index, videoStart, videoEnd)  # 清空原有字幕轴 防止叠轴

                self.levelGraph.clear()
                self.varList = []  # 初始化总体方差分布列表
                self.thres = 0  # 初始化阈值为0
                self.levelLine = None  # 初始化阈值横线为空
                self.levelConfirm.setEnabled(False)  # 禁用确认阈值按钮
                self.sepProc.varList.connect(self.replotGraph)  # 接受spleeter线程每分钟返回来的方差列表并绘制到图里用于用户自选打轴

                self.tablePreset.emit([fillWord, index])  # 填充文本 输出列
                self.sepProc.finish.connect(self.sepFinished)
                self.sepProc.start()
            else:
                self.checkButton.setText('停止中')
                self.checkButton.setEnabled(False)
                self.processToken = not self.processToken
                self.sepProc.terminalToken = True

    def setTitle(self, pos):
        self.setWindowTitle('AI智能打轴 (已分析至第%s分钟)' % pos)

    def setProgressBar(self, percent):
        self.checkButton.setText('停止')
        self.checkButton.setStyleSheet('background-color:#3daee9')
        self.processBar.setValue(percent)

    def sendVoiceList(self, voiceList):
        for voice in voiceList:
            start, delta = voice
            self.voiceDict[start] = delta  # 记录人声音轨以便后续翻译使用
        self.voiceList.emit(voiceList)

    def sendVoiceWave(self, x, y, y2, y3, bgm):
        self.voiceWaveTime, self.voiceWave, self.voiceWave_smooth = x, y, y2  # 创建变量用于自选模式打轴
        self.voiceWave_smooth_scale = y3  # 缩放至0-1区间的数据
        self.voiceWave_graph.emit(x, y2, bgm)

    def replotGraph(self, varList):  # 自选模式下每分钟刷新方差分布直方图
        self.varList += varList  # 将每分钟的方差添加至总体方差列表
        videoStart = self.videoStart.currentIndex()
        videoEnd = self.videoEnd.currentIndex() + 1
        varList = varList[::videoEnd - videoStart]  # 按选择时长降采样
        replotToken = False
        for i in varList:
            if i > 0:
                replotToken = True
                break
        if replotToken:
            med = np.median(self.varList)
            avg = np.mean(self.varList)
            self.autoThres = avg if avg > med else med
            self.autoThres *= 4
            thres = self.autoThres / 32  # 灵敏模式下的默认阈值
            if not self.levelLine:
                self.levelLine = self.levelGraph.addLine(y=thres, pen=pg.mkPen('#d93c30', width=2))
                self.levelLine.setZValue(10)
            else:
                self.levelLine.setValue(thres)
            self.levelSlider.setValue(self.levelSlider.width() / 2)
            self.levelEdit.setText('%.10f' % thres)
            self.levelGraph.plot(range(len(varList)), varList, pen=None, symbol='o', symbolSize=1,
                                 symbolBrush=(100, 100, 100, 100))

    def refreshGraph(self):
        if self.varList:
            videoStart = self.videoStart.currentIndex()
            videoEnd = self.videoEnd.currentIndex() + 1
            varEnd = videoEnd * 60000 if videoEnd * 60000 < len(self.varList) else len(self.varList)
            varList = self.varList[videoStart * 60000:varEnd:videoEnd - videoStart]  # 按选择时长降采样
            replotToken = False
            for i in varList:
                if i > 0:
                    replotToken = True
                    break
            if replotToken:
                med = np.median(varList)
                avg = np.mean(varList)
                self.autoThres = avg if avg > med else med
                self.autoThres *= 4
                thres = self.autoThres / 32  # 灵敏模式下的默认阈值
                if not self.levelLine:
                    self.levelLine = self.levelGraph.addLine(y=thres, pen=pg.mkPen('#d93c30', width=2))
                    self.levelLine.setZValue(10)
                else:
                    self.levelLine.setValue(thres)
                self.levelSlider.setValue(self.levelSlider.width() / 2)
                self.levelEdit.setText('%.10f' % thres)
                self.levelGraph.plot(range(len(varList)), varList, pen=None, symbol='o', symbolSize=1,
                                     symbolBrush=(100, 100, 100, 100), clear=True)
                self.levelLine = self.levelGraph.addLine(y=thres, pen=pg.mkPen('#d93c30', width=2))
                self.levelLine.setZValue(10)

    def refreshLevelLine(self, p):  # 滑动条跟随鼠标
        x = p.x()
        if x < 0:  # 限制
            x = 0
        elif x > self.levelSlider.width():
            x = self.levelSlider.width()
        self.levelSlider.setValue(x)
        if self.levelLine and self.autoThres:
            if self.autoThres < 0.0005:
                self.autoThres = 0.0005
            self.thres = x * self.autoThres / self.levelSlider.width()  # 用户手动选择阈值
            self.levelLine.setValue(self.thres)
            self.levelEdit.setText('%.10f' % self.thres)

    def resetSubtitle(self):  # 自选模式下根据用户选择阈值重新打轴
        index = self.outputIndex.currentIndex()
        videoStart = self.videoStart.currentIndex()
        videoEnd = self.videoEnd.currentIndex() + 1
        self.clearSub.emit(index, videoStart, videoEnd)  # 重新调整轴之前先清空一次
        try:
            fillWord = self.fillWord.text()
        except:
            fillWord = ' '
        index = self.outputIndex.currentIndex()
        self.tablePreset.emit([fillWord, index])  # 填充文本 输出列

        self.reprocessSub = reprocessSub(videoStart, videoEnd, index)
        self.reprocessSub.show()

        before = int(self.beforeEdit.text())
        after = int(self.afterEdit.text())
        flash = int(self.antiFlash.text())
        level = self.cutLevel.currentIndex()
        voiceWave = self.voiceWave[videoStart * 60000:videoEnd * 60000]
        voiceWave_smooth_scale = self.voiceWave_smooth_scale[videoStart * 60000:videoEnd * 60000]
        voiceWave_smooth = self.voiceWave_smooth[videoStart * 60000:videoEnd * 60000]
        varList = self.varList[videoStart * 60000:videoEnd * 60000]
        self.reprocessThread = reprocessQThread(before, after, flash, level, self.thres, videoStart,
                                                voiceWave, voiceWave_smooth_scale, voiceWave_smooth, varList)
        self.reprocessThread.percent.connect(self.refreshReprocessBar)
        self.reprocessThread.voiceList.connect(self.sendVoiceList)
        self.reprocessThread.start()
        self.reprocessThread.exec_()

    def refreshReprocessBar(self, percent):
        self.reprocessSub.processBar.setValue(percent)

    def sepFinished(self, result):
        if result:
            self.processToken = not self.processToken
            self.setWindowTitle('AI智能打轴')
            self.processBar.setValue(100)
            self.checkButton.setText('开始')
            self.checkButton.setEnabled(True)
            self.checkButton.setStyleSheet('background-color:#31363b')
            self.sepProc.terminate()
            self.sepProc.quit()
            self.sepProc.wait()
            if self.varList:  # 若视频方差值有效 则开启自选阈值确认按钮
                self.levelConfirm.setEnabled(True)

    def checkNetwork(self, pingResult):
        self.networkToken = pingResult

    def startTranslate(self):  # 开始翻译
        if not self.translateToken:
            sourceIndex = self.sourceLanguage.currentIndex()
            targetIndex = self.targetLanguage.currentIndex()
            self.sourceOutputIndex = self.sourceOutput.currentIndex()
            self.targetOutputIndex = self.targetOutput.currentIndex()
            if not self.networkToken:
                self.tipLabel.setTExt('无法连接至腾讯AI平台 请检查网络')  # 若无法连接网络则重新检查一次
                self.ping.start()
            else:
                vocalPath = os.path.join(os.getcwd(), r'temp_audio\audio_original.aac')
                if not os.path.exists(vocalPath):
                    self.tipLabel.setText('未检测到视频音轨%s 请尝试重新加载视频以生成音轨文件' % vocalPath)
                elif not self.APPIDEdit.text() or not self.APPKEYEdit.text():
                    self.tipLabel.setText('APPID和APPKEY不能为空 请到腾讯AI开放平台申请一份: https://ai.qq.com/')
                else:
                    APPID = self.APPIDEdit.text()
                    APPKEY = self.APPKEYEdit.text()
                    with open('translate_account.log', 'w') as f:  # 保存APPID和APPKEY副本以便下次启动直接填入
                        f.write('%s\n%s\n' % (APPID, APPKEY))
                    self.tipLabel.setText('开始翻译第%s列' % (self.targetOutputIndex + 1))
                    self.translateButton.setText('停止')
                    self.translateButton.setStyleSheet('background-color:#3daee9')
                    translateDict = self.subtitleDict[self.targetOutputIndex]
                    videoStart = self.videoStart.currentIndex()
                    videoEnd = self.videoEnd.currentIndex()
                    self.translate = translateThread(translateDict, videoStart, videoEnd, sourceIndex, targetIndex,
                                                     APPID, APPKEY)
                    self.translate.percent.connect(self.setTranslateProcessBar)
                    self.translate.result.connect(self.sendTranslateResults)
                    self.translate.finish.connect(self.translateFinished)
                    self.translate.start()
        else:
            self.translateButton.setText('开始')
            self.translateButton.setStyleSheet('background-color:#31363b')
            self.translateProcessBar.setValue(0)
            self.translate.terminate()
            self.translate.quit()
            self.translate.wait()
        self.translateToken = not self.translateToken

    def setTranslateProcessBar(self, percent):
        self.translateProcessBar.setValue(percent)

    def sendTranslateResults(self, result):  # start, delta, source, target, sourceIndex, targetIndex
        self.translateResult.emit(result + [self.sourceOutputIndex, self.targetOutputIndex])

    def translateFinished(self, result):
        if result:
            self.translate.terminate()
            self.translate.quit()
            self.translate.wait()
            self.translateButton.setText('开始')
            self.translateButton.setStyleSheet('background-color:#31363b')
            self.translateProcessBar.setValue(100)
