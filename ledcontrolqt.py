# This Python file uses the following encoding: utf-8



import sys, os
import PyQt5
from PyQt5 import QtCore, QtGui, QtWidgets, uic
from PyQt5.QtWidgets import *
from PyQt5.QtCore import QSize, QTimer, QDateTime, Qt
from PyQt5.QtGui import *
from pathlib import Path

import faulthandler
faulthandler.enable()

# import numpy as np
# import PIL

# from pyqtgraph.Qt import QtGui, QtCore
# import pyqtgraph as pg
# import cv2

import re
import math
import array
import time
# import datetime
from datetime import datetime, timedelta
import logging
import traceback

import threading
import concurrent.futures

from ecoRGBinterface import *


# import multiprocessing
# from multiprocessing import Pool

from threading import Thread
from time import sleep
import re

channellock = threading.Lock() #for reading mode back into UI logic
updatelock = threading.Lock() #for autopush, checking for changes
logsignallock = threading.Lock() #for log signalling
loglock = threading.Lock() #for log
ioqlock = threading.Lock() #for queue
ioreqs = []

# If importing from pyuic5 command line:
# from test import HelloWindow
# from mainwindow import Ui_MainWindow

# Should the UI resend commands till it gets a response?
# Useful for Neopixel build which drops serial packets half the time
# Mand add latency and may overwhelm or serial input on the MCU (to be tested)
SEND_BYTES_THRESHOLD = 500 #50 # 100 # to not overflow anything
MAX_SEND_INTERVAL = .005 # .050  # sec
RESEND_VERIFY = True
RESEND_DELAY_MS = 5 #20 #5 #20 #based roughly around frame rate
RESEND_MAX_TRIES = 10 #plz don't overflow the poor serial buffer

STRESS_UPDATES = False
# STRESS_UPDATES = True

# Option A:
# https://www.geeksforgeeks.org/program-change-rgb-color-model-hsv-color-model/ :
def rgb_to_hsv(r, g, b): 
  r, g, b = r / 255.0, g / 255.0, b / 255.0
  h, s, v = 0, 0, 0

  cmax = max(r, g, b) 
  cmin = min(r, g, b) 
  diff = cmax-cmin    

  if cmax == cmin:  
    h = 0
  elif cmax == r:  
    h = (60 * ((g - b) / diff) + 360) % 360
  elif cmax == g: 
    h = (60 * ((b - r) / diff) + 120) % 360
  elif cmax == b: 
    h = (60 * ((r - g) / diff) + 240) % 360
  if cmax == 0: 
    s = 0
  else: 
    s = (diff / cmax) * 100
  v = cmax * 100
  return h, s, v 
  
def hsv_to_rgb(h, s, v):
  if s == 0.0: return (v, v, v)
  i = int(h*6.) # XXX assume int() truncates!
  f = (h*6.)-i
  p,q,t = v*(1.-s), v*(1.-s*f), v*(1.-s*(1.-f))
  i %= 6
  if i == 0: return (v, t, p)
  if i == 1: return (q, v, p)
  if i == 2: return (p, v, t)
  if i == 3: return (p, q, v)
  if i == 4: return (t, p, v)
  if i == 5: return (v, p, q)

# Option B:
# def rgb_to_hsv(r, g, b):
#     r = float(r)
#     g = float(g)
#     b = float(b)
#     high = max(r, g, b)
#     low = min(r, g, b)
#     h, s, v = high, high, high

#     d = high - low
#     s = 0 if high == 0 else d/high

#     if high == low:
#         h = 0.0
#     else:
#         h = {
#             r: (g - b) / d + (6 if g < b else 0),
#             g: (b - r) / d + 2,
#             b: (r - g) / d + 4,
#         }[high]
#         h /= 6

#     return h, s, v

# def hsv_to_rgb(h, s, v):
#     i = math.floor(h*6)
#     f = h*6 - i
#     p = v * (1-s)
#     q = v * (1-f*s)
#     t = v * (1-(1-f)*s)

#     r, g, b = [
#         (v, t, p),
#         (q, v, p),
#         (p, v, t),
#         (p, q, v),
#         (t, p, v),
#         (v, p, q),
#     ][int(i%6)]

#     return r, g, b

# custom log handler to forward log output to text widget
class QtHandler(logging.Handler):
  def __init__(self, ledqt_):
    self.ledqt = ledqt_
    logging.Handler.__init__(self)

  def emit(self, record):
    with loglock:
      record = self.format(record)
      self.ledqt.textBrowser_sb_log.append(record)
      self.ledqt.label_sb_status.setText(record)
      # We're getting way too much thread trouble for trying to keep the vertical scroll bar at the tail end here...
      # if self.ledqt.pushButton_misc_taillog.isChecked():
        # self.ledqt.textBrowser_sb_log.verticalScrollBar().setValue(self.ledqt.textBrowser_sb_log.verticalScrollBar().maximum());    
        # QCoreApplication.processEvents()
    print(record)

class LEDControlQT(QMainWindow):
  ''' Handle events and controls in QT UI '''
  def __init__(self):
    super().__init__()

    if not os.path.exists('logs'):
      os.makedirs('logs')
    self.initlogging()
    self.initUI()
    self.initvalues()
    # time.sleep(.5)


  def initlogging(self):
    self.log = logging.getLogger('ledcontrolqt')
    
    # DEBUG < INFO < WARNING < ERROR < CRITICAL
    self.log.setLevel(logging.DEBUG)
    
    # create file handler which logs even debug messages
    fh = logging.FileHandler(os.path.join(os.getcwd(), 'logs', 'full.log'))
    fh.setLevel(logging.DEBUG)
    
    # create console handler:
    # ch = logging.StreamHandler()
    # create widget handler:
    ch = QtHandler(self)
    # with whatever output filter needed
    ch.setLevel(logging.DEBUG) #ERROR)

    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
    fh.setFormatter(formatter)
    # ch.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    ch.setFormatter(logging.Formatter("%(message)s"))
    
    # add the handlers to the log
    self.log.addHandler(fh)
    self.log.addHandler(ch)

  def thlog_(self, message, mode='info'):
    with logsignallock:
      try:
        exec("self.log."+mode+"(message)")
      except:
        print("logging error.")
        print("Unexpected error: " + traceback.format_exc())

  def thlog_debug(self, message):
    self.thlog_(message, 'debug')
    # with logsignallock:
      # self.log.debug(message)

  def thlog_info(self, message):
    self.thlog_(message, 'info')
    # with logsignallock:
      # self.log.info(message)

  def thlog_warning(self, message):
    self.thlog_(message, 'warning')
    # with logsignallock:
      # self.log.warning(message)

  def thlog_error(self, message):
    self.thlog_(message, 'error')
    # with logsignallock:
      # self.log.error(message)

  def initvalues(self):
    # self.key_events = {
    #                     Qt.Key_Escape: self.stage_abort_pushed,
    #                     Qt.Key_Left: self.jog_left_pushed,
    #                     Qt.Key_Right: self.jog_right_pushed,
    #                     Qt.Key_Up: self.jog_up_pushed,
    #                     Qt.Key_Down: self.jog_down_pushed,
    #                     Qt.Key_A: self.jog_left_pushed,
    #                     Qt.Key_D: self.jog_right_pushed,
    #                     Qt.Key_W: self.jog_up_pushed,
    #                     Qt.Key_S: self.jog_down_pushed,
    #                     Qt.Key_R: self.jog_Z_raise_pushed,
    #                     Qt.Key_F: self.jog_Z_lower_pushed,
                        # Qt.Key_Escape: tuple([self.stage_abort_pushed, True,]),
                        # Qt.Key_Left: tuple([self.jog_left_pushed, True,]),
                        # Qt.Key_Right: tuple([self.jog_right_pushed, True,]),
                        # Qt.Key_Up: tuple([self.jog_up_pushed, True,]),
                        # Qt.Key_Down: tuple([self.jog_down_pushed, True,]),
    #                     }
    self.latest_ci          = 0
    self.latest_style       = 0
    self.latest_R1          = 0
    self.latest_G1          = 0
    self.latest_B1          = 0
    self.latest_R2          = 0
    self.latest_G2          = 0
    self.latest_B2          = 0
    self.latest_timeA       = 0
    self.latest_timeB       = 0
    self.latest_timeOffset  = 0
    self.latest_timeABpause = 0
    self.latest_timeBApause = 0
    self.latest_flags       = 0
    self.latest_size        = 0
    self.latest_spoffset    = 0

    self.pendingUpdates = 0
    self.manualRequest = False

    # for resend/verify:
    self.ser_lastpktid = 0  
    self.awaitingconfirmations = False
    self.ser_responsespending = 0
    self.ser_msgs=['']*256   # index on pktid, send msgs
    self.ser_rsps=[b'x']*256  # index on pktid, receive msgs. '' indicates waiting.
    self.ser_sends=[0]*256   # number of (re)sends so far, stop at RESEND_MAX_TRIES
    self.ser_lastsenddt=[datetime.now()]*256   # datetime of last resend, for timing next one

    self.cmdlist=[]
    self.isSerConnected = False
    self.num_channels = self.comboBox_channel.count()
    self.channels_requested = [False]*self.num_channels
    self.channel_responses = [b'']*self.num_channels
    

  def initUI(self):

    # uic internal instead of pyuic5:
    self.call     = uic.loadUi("mainwindow.ui", baseinstance=self)

    self.pushButton_hooks()
  
    self.label_sb_status.setStyleSheet("color: black")
    # print("###############   Globals   ################")
    # print(globals())
    # print("###############   Locals['self']    ################")
    # print(locals()['self'])
    # print("###############   dir    ################")
    # print(dir(self))
    # print("###############   getattr    ################")
    # print(getattr(self, "pushButton_LED_52"))
    self.show()
    # self.cdialog.show()

  ### Event Handlers - key press ###

  def keyPressEvent(self, event):
    fwidg = self.focusWidget()
    # if fwidg in [self.doubleSpinBox_stage_X,
    #              self.doubleSpinBox_stage_Y,
    #              self.doubleSpinBox_stage_Z]:
    #   if event.key() == Qt.Key_Return:
    #     self.stage_goto_XYZ()
    if fwidg in [self.lineEdit_sb_cmd]:
      if event.key() == Qt.Key_Return:
        self.exec_cmd()
      if event.key() == Qt.Key_Up:
        self.up_cmd()
      if event.key() == Qt.Key_Down:
        self.down_cmd()
    # elif event.key() in self.key_events:
    #   self.key_events[event.key()](True)
    # if event.key() in self.key_events:
    #   (req, *args) = self.key_events[event.key()]
    #   if not args:
    #     req()
    #   else:
    #     # I don't love this solution, but req(*args) is giving grief so unroll this explicitly:
    #     if   len(args)==1:
    #       req(args[0])
    #     # elif len(args)==2:
    #     #   req(args[0], args[1])
    #     # elif len(args)==3:
    #     #   req(args[0], args[1], args[2])
    #     # ...

  ###  CMD  ####

  def recall_cmd(self, dir):
    if dir=="UP":
      if self.cmdi==-1:
        self.cmdi=len(self.cmdlist)-1
      elif self.cmdi>0:
        self.cmdi=self.cmdi-1
      else: # 0, ignore
        return
    if dir=="DOWN":
      if self.cmdi==-1: #ignore
        return
      elif self.cmdi<len(self.cmdlist)-1:
        self.cmdi=self.cmdi+1
    self.lineEdit_sb_cmd.setText(self.cmdlist[self.cmdi])

  def up_cmd(self):
    self.recall_cmd("UP")

  def down_cmd(self):
    self.recall_cmd("DOWN")

  def exec_cmd(self):
    _cmd = self.lineEdit_sb_cmd.text()
    if _cmd in self.cmdlist:
      del self.cmdlist[self.cmdlist.index(_cmd)]
    self.cmdlist.append(_cmd)
    try:
      exec(_cmd)
    except:
      self.thlog_error("Unexpected error: " + traceback.format_exc())

    self.lineEdit_sb_cmd.setText("")
    self.cmdi=-1

  # def pb_hidestats_pushed(self, pressed):
  #   self.thlog_debug("pb_hidestats_pushed")
  #   if (pressed):
  #     self.groupBox_pbstats.setVisible(False)
  #   else:
  #     self.groupBox_pbstats.setVisible(True)
  
  
  def misc_showlog_pushed(self, pressed):
    self.thlog_debug("misc_showlog_pushed")

  def timeupdated(self, pressed):
    # self.thlog_debug("timeupdated")
    total_time = 0
    if self.spinBox_timeA.isEnabled():
      total_time += self.spinBox_timeA.value()
    if self.spinBox_timeB.isEnabled():
      total_time += self.spinBox_timeB.value()
    if self.spinBox_timeOffset.isEnabled():
      total_time += self.spinBox_timeOffset.value()
    if self.spinBox_timeABpause.isEnabled():
      total_time += self.spinBox_timeABpause.value()
    if self.spinBox_timeBApause.isEnabled():
      total_time += self.spinBox_timeBApause.value()
    self.lineEdit_totaltime.setText(str(total_time))

  #Access only in serial - should only be one request at a time...
  def getChannelInfoResponse(self, i):
    with channellock:
      self.channel_responses[i] = 0
      self.getChannelInfo(i, response_requested=True)

    start_time = datetime.now()
    while True:
      with channellock:
        if self.channel_responses[i]:
          # Got a response
          self.channels_requested[i] = False
          return self.channel_responses[i]
      time_delta = datetime.now() - start_time
      if time_delta.total_seconds() >= 10:
        # No response, timeout
        return b'timeout'
      time.sleep(.05)


  def getChannelInfo(self, i, response_requested=False):
    self.thlog_debug(f"getChannelInfo [{i}]")
    with updatelock: # A little dangery, will hold until ioqlock
      self.pendingUpdates+=1
      with ioqlock:
        if response_requested:
          self.channels_requested[i] = True
        if self.pendingUpdates > 1:  # Drop other requests in queue
          for ri in range(len(ioreqs)-1,-1,-1):
            if ioreqs[ri][1] == SPC_READSTATE: #get channel info
              if ioreqs[ri][0] >= self.num_channels:
                self.thlog_warning("Bad ioreq? outside channel range:") 
                self.thlog_warning(ioreqs[ri]) 
              if self.channels_requested[ioreqs[ri][0]]: 
                #Don't purge it - response especially requested
                self.thlog_debug("keeping extra query at request.")
              else:
                self.thlog_debug(f'Recent update, dropping update request to channel {ioreqs[ri][0]}')
                # print(ioreqs)
                ioreqs.pop(ri)
                # print(ioreqs)
                self.pendingUpdates -= 1
          # ioreqs.append(getChannelInfoBytes(i))
          # print(ioreqs)
        # else:
          # ioreqs.append(getChannelInfoBytes(i))
        ioreqs.append(getChannelInfoBytes(i))

  def textBrowser_sb_log_range_changed(self, min, max):
    # self.thlog_debug("textBrowser_sb_log_range_changed")
    if self.pushButton_misc_taillog.isChecked():
      with loglock:
        self.textBrowser_sb_log.verticalScrollBar().setValue(max);    
        # self.textBrowser_sb_log.verticalScrollBar().setValue(self.textBrowser_sb_log.verticalScrollBar().maximum());    

  def update_pushed(self, pressed):
    # self.thlog_debug("update_pushed")
    self.setChannelByFields()

  def pushPending_pushed(self, pressed):
    self.thlog_debug("pushPending_pushed")
    with ioqlock:
      ioreqs.append(getUpdatePendingBytes())

  def getVerboseChannelInfo_pushed(self, pressed):
    # self.thlog_debug("getVerboseChannelInfo_pushed")
    # self.manualRequest = True
    self.getVerboseChannelInfoByCurrent()

  def getVerboseChannelInfoByCurrent(self):
    i = self.comboBox_channel.currentIndex()
    # self.thlog_debug(f"getting verbose channel info: {i} ")
    self.getVerboseChannelInfo(i)
    # self.doubleSpinBox_stage_X.setValue(self.posxyz.X)

  def getVerboseChannelInfo(self, i):
    self.thlog_debug(f"getVerboseChannelInfo[{i}]:")
    with ioqlock:
      ioreqs.append(getVerboseChannelInfoBytes(i))

  def getChannelInfo_pushed(self, pressed):
    # self.thlog_debug("getChannelInfo_pushed")
    self.manualRequest = True
    self.getChannelInfoByCurrent()

  def getChannelInfoByCurrent(self):
    i = self.comboBox_channel.currentIndex()
    # self.thlog_debug(f"getting channel info: {i} ")
    self.getChannelInfo(i)
    # self.doubleSpinBox_stage_X.setValue(self.posxyz.X)

  def getFWVersion_pushed(self, pressed):
    # self.thlog_debug("getFWVersion_pushed")
    self.getFWVersion()

  def getFWVersion(self):
    self.thlog_debug("getFWVersion:")
    with ioqlock:
      ioreqs.append(getFWVersionBytes())

  def saveFlash_pushed(self, pressed):
    self.thlog_debug("saveFlash_pushed")
    self.saveFlash()

  def saveFlash(self):
    self.thlog_debug("saveFlash:")
    with ioqlock:
      ioreqs.append(saveFlashBytes())

  def loadFlash_pushed(self, pressed):
    self.thlog_debug("loadFlash_pushed")
    self.loadFlash()

  def loadFlash(self):
    self.thlog_debug("loadFlash:")
    with updatelock:
      self.pendingUpdates = 0
    with ioqlock:
      while ioreqs:
        ioreqs.pop()
      ioreqs.append(loadFlashBytes())

  def setColorCorrection_pushed(self, pressed):
    self.thlog_debug("setColorCorrection_pushed")
    if self.pushButton_switchCorrectionMode.isChecked():
      # Temperature
      with ioqlock:
        ioreqs.append(setTemperatureCorrectionBytes(
                        _bright=self.spinBox_Brightcor.value(), 
                        _kel=self.spinBox_Tempcor.value()))
    else: 
      # RGB White point
      with ioqlock:
        ioreqs.append(setColorCorrectionBytes(_col=RGB(self.spinBox_Rcor.value(), 
                                                  self.spinBox_Gcor.value(), 
                                                  self.spinBox_Bcor.value())))

  def b1_hsvassign_pushed(self, pressed):
    self.thlog_debug("b1_hsvassign_pushed")
    self.update_rgbhsvlabels()

  def update_rgbhsvlabels(self):
    if self.checkBox_b1_hsvassign.isChecked() or self.comboBox_ledstyle.currentText() in ['LS_RAINBOW']:
      # HSV
      if (self.label_R1.text() == "R:"):
        # Convert values as well, from RGB to HSV
        h1, s1, v1 = rgb_to_hsv(self.spinBox_R1.value()/255.0, self.spinBox_G1.value()/255.0, self.spinBox_B1.value()/255.0)
        h2, s2, v2 = rgb_to_hsv(self.spinBox_R2.value()/255.0, self.spinBox_G2.value()/255.0, self.spinBox_B2.value()/255.0)
        self.spinBox_R1.setValue(min(max(int(h1*255/360),0),255))
        self.spinBox_G1.setValue(min(max(int(s1*255/100),0),255))
        self.spinBox_B1.setValue(min(max(int(v1*255*2.56),0),255))
        self.spinBox_R2.setValue(min(max(int(h2*255/360),0),255))
        self.spinBox_G2.setValue(min(max(int(s2*255/100),0),255))
        self.spinBox_B2.setValue(min(max(int(v2*255*2.56),0),255))
      self.label_R1.setText("Hue:")
      self.label_G1.setText("Sat:")
      self.label_B1.setText("Val:")
      self.label_R2.setText("Hue:")
      self.label_G2.setText("Sat:")
      self.label_B2.setText("Val:")
    else: 
      # RGB
      if (self.label_R1.text() == "Hue:"):
        # Convert values as well, from HSV to RGB
        r1, g1, b1 = hsv_to_rgb(self.spinBox_R1.value()/255.0, self.spinBox_G1.value()/255.0, self.spinBox_B1.value()/255.0)
        r2, g2, b2 = hsv_to_rgb(self.spinBox_R2.value()/255.0, self.spinBox_G2.value()/255.0, self.spinBox_B2.value()/255.0)
        self.spinBox_R1.setValue(min(max(int(r1*255),0),255))
        self.spinBox_G1.setValue(min(max(int(g1*255),0),255))
        self.spinBox_B1.setValue(min(max(int(b1*255),0),255))
        self.spinBox_R2.setValue(min(max(int(r2*255),0),255))
        self.spinBox_G2.setValue(min(max(int(g2*255),0),255))
        self.spinBox_B2.setValue(min(max(int(b2*255),0),255))
      self.label_R1.setText("R:")
      self.label_G1.setText("G:")
      self.label_B1.setText("B:")
      self.label_R2.setText("R:")
      self.label_G2.setText("G:")
      self.label_B2.setText("B:")

  def switchCorrectionMode_pushed(self, pressed):
    self.thlog_debug("switchCorrectionMode_pushed")
    self.horizontalSlider_Rcor.setEnabled(not pressed) 
    self.horizontalSlider_Gcor.setEnabled(not pressed) 
    self.horizontalSlider_Bcor.setEnabled(not pressed) 
    self.spinBox_Rcor.setEnabled(not pressed) 
    self.spinBox_Gcor.setEnabled(not pressed) 
    self.spinBox_Bcor.setEnabled(not pressed) 

    self.horizontalSlider_Tempcor.setEnabled(pressed) 
    self.horizontalSlider_Brightcor.setEnabled(pressed) 
    self.spinBox_Tempcor.setEnabled(pressed) 
    self.spinBox_Brightcor.setEnabled(pressed) 

    if (pressed):
      self.pushButton_setColorCorrection.setText("Set->")
      self.pushButton_switchCorrectionMode.setText("switch\n<-----")
    else:
      self.pushButton_setColorCorrection.setText("<-Set")
      self.pushButton_switchCorrectionMode.setText("switch\n----->")




  def loadsetup_pushed(self, pressed):
    self.thlog_debug("loadsetup_pushed")
    home_dir = str(Path.cwd())
    _dir = home_dir
    config_dir = os.path.join(home_dir, 'config')
    if not os.path.exists(config_dir):
      os.makedirs(config_dir)
    if os.path.exists(config_dir):
      _dir = config_dir

    filters = "LED Config files (*.lcg);;Text files (*.txt);;All files (*.*)";
    defaultFilter = "LED Config files (*.lcg)";
    fname = QFileDialog.getOpenFileName(self, 'Open LED config file', _dir, filters, defaultFilter)
    if fname[0]:
      self.loadConfig(fname[0])


  def savesetup_pushed(self, pressed):
    self.thlog_debug("savesetup_pushed")
    home_dir = str(Path.cwd())
    _dir = home_dir
    config_dir = os.path.join(home_dir, 'config')
    if not os.path.exists(config_dir):
      os.makedirs(config_dir)
    if os.path.exists(config_dir):
      _dir = config_dir

    filters = "LED Config files (*.lcg);;Text files (*.txt);;All files (*.*)";
    defaultFilter = "LED Config files (*.lcg)";

    fname = QFileDialog.getSaveFileName(self, 'Save LED config file', _dir, filters, defaultFilter)
    if fname[0]:
      self.saveConfig(fname[0])

  def loadConfig(self, _path):
    with open(_path, "rb") as in_file: # opening for [r]eading as [b]inary
      data = in_file.read() # if you only wanted to read 512 bytes, do .read(512)
      try:
        _num_channels = int(data[0])
        bytesperchannel = int(data[1])

        self.thlog_debug(f"opened file: c:{_num_channels} bpc:{bytesperchannel}")
        # TODO: add color correction etc
        if _num_channels != self.num_channels:
          self.thlog_error("Error - mismatch in channel count when loading config.") 
        elif len(data) < _num_channels*bytesperchannel + 2:
          self.thlog_error("Error - insufficient data in config file for pushing to controller.") 
        else:
          with ioqlock:
            self.thlog_debug("making updates from open file:")
            for i in range(_num_channels):
              self.thlog_debug(data[(2+i*bytesperchannel):(2+(i+1)*bytesperchannel)])
              ioreqs.append(data[(2+i*bytesperchannel):(2+(i+1)*bytesperchannel)])
      except:
        _ledqt.thlog_error("Issue with loadConfig. ")
        _ledqt.thlog_error("Unexpected error: " + traceback.format_exc())


  def saveConfig(self, _path):
    with open(_path, "wb") as out_file: # open for [w]riting as [b]inary
      out_file.write(bytes([self.num_channels,MODE_BYTE_SIZE]))
      for i in range(self.num_channels):
        self.thlog_debug(f"getting channel from selection: {i} ")
        modebytes = self.getChannelInfoResponse(i)
        self.thlog_debug(modebytes)
        out_file.write(modebytes)


  def channel_selected(self, pressed):
    self.thlog_debug("channel_selected")
    if (self.checkBox_ardtoPC.isChecked()):
      i = self.comboBox_channel.currentIndex()
      self.thlog_debug(f"getting channel from selection: {i} ")
      self.getChannelInfo(i)

  def horizontalSliders_colorUpdated(self, pressed):
    # self.thlog_debug("horizontalSliders_colorUpdated")
    self.spinBox_R1.setValue(self.horizontalSlider_R1.value())
    self.spinBox_G1.setValue(self.horizontalSlider_G1.value())
    self.spinBox_B1.setValue(self.horizontalSlider_B1.value())
    self.spinBox_R2.setValue(self.horizontalSlider_R2.value())
    self.spinBox_G2.setValue(self.horizontalSlider_G2.value())
    self.spinBox_B2.setValue(self.horizontalSlider_B2.value())

  def spinBoxes_colorUpdated(self, pressed):
    # self.thlog_debug("spinBoxes_colorUpdated")
    self.horizontalSlider_R1.setValue(self.spinBox_R1.value())
    self.horizontalSlider_G1.setValue(self.spinBox_G1.value())
    self.horizontalSlider_B1.setValue(self.spinBox_B1.value())
    self.horizontalSlider_R2.setValue(self.spinBox_R2.value())
    self.horizontalSlider_G2.setValue(self.spinBox_G2.value())
    self.horizontalSlider_B2.setValue(self.spinBox_B2.value())
 
  def horizontalSliders_colorCorrectUpdated(self, pressed):
    # self.thlog_debug("horizontalSliders_colorCorrectUpdated")
    self.spinBox_Rcor.setValue(self.horizontalSlider_Rcor.value())
    self.spinBox_Gcor.setValue(self.horizontalSlider_Gcor.value())
    self.spinBox_Bcor.setValue(self.horizontalSlider_Bcor.value())
    self.spinBox_Tempcor.setValue(self.horizontalSlider_Tempcor.value())
    self.spinBox_Brightcor.setValue(self.horizontalSlider_Brightcor.value())

  def spinBoxes_colorCorrectUpdated(self, pressed):
    # self.thlog_debug("spinBoxes_colorCorrectUpdated")
    self.horizontalSlider_Rcor.setValue(self.spinBox_Rcor.value())
    self.horizontalSlider_Gcor.setValue(self.spinBox_Gcor.value())
    self.horizontalSlider_Bcor.setValue(self.spinBox_Bcor.value())
    self.horizontalSlider_Tempcor.setValue(self.spinBox_Tempcor.value())
    self.horizontalSlider_Brightcor.setValue(self.spinBox_Brightcor.value())
 
  def setChannelByFields(self):
    # with updatelock:
    _ci =           self.comboBox_channel.currentIndex()
    _style =        self.comboBox_ledstyle.currentIndex()
    _R1 =           self.spinBox_R1.value()
    _G1 =           self.spinBox_G1.value()
    _B1 =           self.spinBox_B1.value()
    # _R1 =           self.horizontalSlider_R1.value()
    # _G1 =           self.horizontalSlider_G1.value()
    # _B1 =           self.horizontalSlider_B1.value()
    _R2 =           self.spinBox_R2.value()
    _G2 =           self.spinBox_G2.value()
    _B2 =           self.spinBox_B2.value()
    # _R2 =           self.horizontalSlider_R2.value()
    # _G2 =           self.horizontalSlider_G2.value()
    # _B2 =           self.horizontalSlider_B2.value()
    _timeA =        self.spinBox_timeA.value()
    _timeB =        self.spinBox_timeB.value()
    _timeOffset =   self.spinBox_timeOffset.value()
    _timeABpause =  self.spinBox_timeABpause.value()
    _timeBApause =  self.spinBox_timeBApause.value()
    _flags = 0
    if self.checkBox_b7_sync.isChecked():
      _flags |= 0b10000000 
    if self.checkBox_b6_huedir.isChecked():
      _flags |= 0b01000000 
    if self.checkBox_b5_down.isChecked():
      _flags |= 0b00100000 
    if self.checkBox_b4_gamma.isChecked():
      _flags |= 0b00010000 
    if self.checkBox_b3_hold_update.isChecked():
      _flags |= 0b00001000 
    if self.checkBox_b2_nodither.isChecked():
      _flags |= 0b00000100 
    if self.checkBox_b1_hsvassign.isChecked():
      _flags |= 0b00000010 
    if self.checkBox_b0_hsvtrans.isChecked():
      _flags |= 0b00000001 
    _size     =  int(10*self.doubleSpinBox_size.value() + 0.001)
    _spoffset =  int(10*self.doubleSpinBox_spoffset.value() + 0.001)

    cmd = setChannelBytes_f(_ci=_ci, _style=_style, _col1=RGB(_R1,_G1,_B1), _col2=RGB(_R2,_G2,_B2), 
                          _size=_size, _spoffset=_spoffset,  _flags=_flags, 
                          _timeA=_timeA, _timeB=_timeB, _timeOffset=_timeOffset, 
                          _timeABpause=_timeABpause, _timeBApause=_timeBApause)
    with ioqlock:
      ioreqs.append(cmd)

    self.latest_ci          = _ci
    self.latest_style       = _style
    self.latest_R1          = _R1
    self.latest_G1          = _G1
    self.latest_B1          = _B1
    self.latest_R2          = _R2
    self.latest_G2          = _G2
    self.latest_B2          = _B2
    self.latest_timeA       = _timeA
    self.latest_timeB       = _timeB
    self.latest_timeOffset  = _timeOffset
    self.latest_timeABpause = _timeABpause
    self.latest_timeBApause = _timeBApause
    self.latest_flags       = _flags
    self.latest_size        = _size
    self.latest_spoffset    = _spoffset


  def setFieldsByBytes(self, _bytes):
    if (len(_bytes)<MODE_BYTE_SIZE):
      self.thlog_error(f"Cannot set field with _bytes, too short: {_bytes}")
      return
    _ci, _style = _bytes[0], _bytes[1]
    _R1, _G1, _B1, _R2, _G2, _B2 = _bytes[2], _bytes[3], _bytes[4], _bytes[5], _bytes[6], _bytes[7], 
    _timeA = 256*_bytes[8] + _bytes[9] 
    _timeB = 256*_bytes[10] + _bytes[11] 
    _timeOffset = 256*_bytes[12] + _bytes[13] 
    _timeABpause = 256*_bytes[14] + _bytes[15] 
    _timeBApause = 256*_bytes[16] + _bytes[17] 
    _timeBApause = 256*_bytes[16] + _bytes[17] 
    _size        = 256*_bytes[18] + _bytes[19]
    _spoffset    = 256*_bytes[20] + _bytes[21]
    _flags       = _bytes[22]

    # printhex(_bytes)
    # print(f"rgb fore : {_R1},{_G1},{_B1}")

    if _ci != self.comboBox_channel.currentIndex():
      self.thlog_warning(f"channel status packet index {_ci} does not match current selected channel index {self.comboBox_channel.currentIndex()}. Not pushing update..")
      with updatelock:
        self.pendingUpdates -= 1
      return

    # Set checkBoxes first - it may swap RGB/HSV spinBoxes
    self.checkBox_b7_sync.setChecked(        _flags & 0b10000000)
    self.checkBox_b6_huedir.setChecked(      _flags & 0b01000000)
    self.checkBox_b5_down.setChecked(        _flags & 0b00100000)
    self.checkBox_b4_gamma.setChecked(       _flags & 0b00010000)
    self.checkBox_b3_hold_update.setChecked( _flags & 0b00001000)
    self.checkBox_b2_nodither.setChecked(    _flags & 0b00000100)
    self.checkBox_b1_hsvassign.setChecked(   _flags & 0b00000010)
    self.checkBox_b0_hsvtrans.setChecked(    _flags & 0b00000001)


    self.comboBox_channel.setCurrentIndex(_ci)
    self.comboBox_ledstyle.setCurrentIndex(_style)

    self.updateEnabledByStyle() #dis/enable appropriate boxen
    # self.update_rgbhsvlabels() #called by updateEnabledByStyle() above
    # This will do value conversion, but we will replace it with the values provided by Bytes momentarily.

    self.spinBox_R1.setValue(_R1)          # May be H if _hsvassign
    self.spinBox_G1.setValue(_G1)          # May be S if _hsvassign
    self.spinBox_B1.setValue(_B1)          # May be V if _hsvassign
    self.horizontalSlider_R1.setValue(_R1) # May be H if _hsvassign
    self.horizontalSlider_G1.setValue(_G1) # May be S if _hsvassign
    self.horizontalSlider_B1.setValue(_B1) # May be V if _hsvassign
    self.spinBox_R2.setValue(_R2)          # May be H if _hsvassign
    self.spinBox_G2.setValue(_G2)          # May be S if _hsvassign
    self.spinBox_B2.setValue(_B2)          # May be V if _hsvassign
    self.horizontalSlider_R2.setValue(_R2) # May be H if _hsvassign
    self.horizontalSlider_G2.setValue(_G2) # May be S if _hsvassign
    self.horizontalSlider_B2.setValue(_B2) # May be V if _hsvassign
    self.spinBox_timeA.setValue(_timeA)
    self.spinBox_timeB.setValue(_timeB)
    self.spinBox_timeOffset.setValue(_timeOffset)
    self.spinBox_timeABpause.setValue(_timeABpause)
    self.spinBox_timeBApause.setValue(_timeBApause)
    self.doubleSpinBox_size.setValue(float(_size+.001)/10 + 0.001)
    self.doubleSpinBox_spoffset.setValue(float(_spoffset+.001)/10 + 0.001)

    self.latest_ci          = _ci
    self.latest_style       = _style
    self.latest_R1          = _R1
    self.latest_G1          = _G1
    self.latest_B1          = _B1
    self.latest_R2          = _R2
    self.latest_G2          = _G2
    self.latest_B2          = _B2
    self.latest_timeA       = _timeA
    self.latest_timeB       = _timeB
    self.latest_timeOffset  = _timeOffset
    self.latest_timeABpause = _timeABpause
    self.latest_timeBApause = _timeBApause
    self.latest_flags       = _flags
    self.latest_size        = _size
    self.latest_spoffset    = _spoffset

    with updatelock:
      self.pendingUpdates -= 1


  def recentChanges(self):
    if (not self.isSerConnected):
      return False
    i = 0
    while (self.pendingUpdates):
      time.sleep(.2)
      i+=1
      if i>10:
        self.thlog_error(f"Pending Updates: {self.pendingUpdates}, unable to verify changes!")
        self.thlog_error(f"Resetting Pending Updates...")
        self.pendingUpdates = 0
        break
        return False

    _ci =           self.comboBox_channel.currentIndex()
    _style =        self.comboBox_ledstyle.currentIndex()
    _R1 =           self.spinBox_R1.value()
    _G1 =           self.spinBox_G1.value()
    _B1 =           self.spinBox_B1.value()
    _R2 =           self.spinBox_R2.value()
    _G2 =           self.spinBox_G2.value()
    _B2 =           self.spinBox_B2.value()
    _timeA =        self.spinBox_timeA.value()
    _timeB =        self.spinBox_timeB.value()
    _timeOffset =   self.spinBox_timeOffset.value()
    _timeABpause =  self.spinBox_timeABpause.value()
    _timeBApause =  self.spinBox_timeBApause.value()
    _flags = 0
    if self.checkBox_b7_sync.isChecked():
      _flags |= 0b10000000 
    if self.checkBox_b6_huedir.isChecked():
      _flags |= 0b01000000 
    if self.checkBox_b5_down.isChecked():
      _flags |= 0b00100000 
    if self.checkBox_b4_gamma.isChecked():
      _flags |= 0b00010000 
    if self.checkBox_b3_hold_update.isChecked():
      _flags |= 0b00001000 
    if self.checkBox_b2_nodither.isChecked():
      _flags |= 0b00000100 
    if self.checkBox_b1_hsvassign.isChecked():
      _flags |= 0b00000010 
    if self.checkBox_b0_hsvtrans.isChecked():
      _flags |= 0b00000001 
    _size     =  int(10*self.doubleSpinBox_size.value() + 0.001)
    _spoffset =  int(10*self.doubleSpinBox_spoffset.value() + 0.001)

    if (   # self.latest_ci          == _ci   # Don't simply reassign channel when changing, if auto PC<-Ard is disabled but PC->Ard is enabled.
            self.latest_style       == _style
        and self.latest_R1          == _R1
        and self.latest_G1          == _G1
        and self.latest_B1          == _B1
        and self.latest_R2          == _R2
        and self.latest_G2          == _G2
        and self.latest_B2          == _B2
        and self.latest_timeA       == _timeA
        and self.latest_timeB       == _timeB
        and self.latest_timeOffset  == _timeOffset
        and self.latest_timeABpause == _timeABpause
        and self.latest_timeBApause == _timeBApause
        and self.latest_flags       == _flags
        and self.latest_size        == _size
        and self.latest_spoffset    == _spoffset):
      return False

    if 1: #debug
      if self.latest_ci          != _ci:
        print(f"latest_ci: {self.latest_ci} != {_ci}")
      if self.latest_style       != _style:
        print(f"latest_style: {self.latest_style} != {_style}")
      if self.latest_R1          != _R1:
        print(f"latest_R1: {self.latest_R1} != {_R1}")
      if self.latest_G1          != _G1:
        print(f"latest_G1: {self.latest_G1} != {_G1}")
      if self.latest_B1          != _B1:
        print(f"latest_B1: {self.latest_B1} != {_B1}")
      if self.latest_R2          != _R2:
        print(f"latest_R2: {self.latest_R2} != {_R2}")
      if self.latest_G2          != _G2:
        print(f"latest_G2: {self.latest_G2} != {_G2}")
      if self.latest_B2          != _B2:
        print(f"latest_B2: {self.latest_B2} != {_B2}")
      if self.latest_timeA       != _timeA:
        print(f"latest_timeA: {self.latest_timeA} != {_timeA}")
      if self.latest_timeB       != _timeB:
        print(f"latest_timeB: {self.latest_timeB} != {_timeB}")
      if self.latest_timeOffset  != _timeOffset:
        print(f"latest_timeOffset: {self.latest_timeOffset} != {_timeOffset}")
      if self.latest_timeABpause != _timeABpause:
        print(f"latest_timeABpause: {self.latest_timeABpause} != {_timeABpause}")
      if self.latest_timeBApause != _timeBApause:
        print(f"latest_timeBApause: {self.latest_timeBApause} != {_timeBApause}")
      if self.latest_flags       != _flags:
        print(f"latest_flags: {self.latest_flags} != {_flags}")
      if self.latest_size        != _size:
        print(f"latest_size: {self.latest_size} != {_size}")
      if self.latest_spoffset        != _spoffset:
        print(f"latest_spoffset: {self.latest_spoffset} != {_spoffset}")

    return True

  def setEnabled(self, col1=True, col2=True, timeA=True, timeB=True, timeOffset=True, 
                 timeABpause=True, timeBApause=True, flags=True, 
                 size=True, spoffset=True, update=True):
    for item in [self.spinBox_R1, self.spinBox_G1, self.spinBox_B1, 
         self.horizontalSlider_R1, self.horizontalSlider_G1, self.horizontalSlider_B1]:
      item.setEnabled(col1)
    for item in [self.spinBox_R2, self.spinBox_G2, self.spinBox_B2, 
         self.horizontalSlider_R2, self.horizontalSlider_G2, self.horizontalSlider_B2]:
      item.setEnabled(col2)
    self.spinBox_timeA.setEnabled(timeA)
    self.spinBox_timeB.setEnabled(timeB)
    self.spinBox_timeOffset.setEnabled(timeOffset)
    self.spinBox_timeABpause.setEnabled(timeABpause)
    self.spinBox_timeBApause.setEnabled(timeBApause)
    self.lineEdit_totaltime.setEnabled(timeA or timeB or timeOffset or timeABpause or timeBApause)
    self.timeupdated(False)
    for item in [self.checkBox_b7_sync, self.checkBox_b6_huedir, self.checkBox_b5_down, 
                 self.checkBox_b4_gamma, self.checkBox_b3_hold_update, self.checkBox_b2_nodither, 
                 self.checkBox_b1_hsvassign, self.checkBox_b0_hsvtrans]:
      item.setEnabled(flags)
    self.doubleSpinBox_size.setEnabled(size)
    self.doubleSpinBox_spoffset.setEnabled(spoffset)
    self.pushButton_update.setEnabled(update)


  def ledstyle_selected(self, pressed):
    self.thlog_debug("ledstyle_selected")
    self.updateEnabledByStyle()

  def updateEnabledByStyle(self):
    selected = self.comboBox_ledstyle.currentText()
    if selected in ['LS_OFF']:
      self.setEnabled(col1=False, col2=False, timeA=False, timeB=False, timeOffset=False, 
                      timeABpause=False, timeBApause=False, flags=False, 
                      size=False, spoffset=False, update=True)
    if selected in ['LS_ON']:
      self.setEnabled(col1=True, col2=False, timeA=False, timeB=False, timeOffset=False, 
                      timeABpause=False, timeBApause=False, flags=True, 
                      size=False, spoffset=False, update=True)
    if selected in ['LS_BLINK']:
      self.setEnabled(col1=True, col2=True, timeA=True, timeB=True, timeOffset=True, 
                      timeABpause=False, timeBApause=False, flags=True, 
                      size=False, spoffset=False, update=True)
    if selected in ['LS_CHASE']:
      self.setEnabled(col1=True, col2=True, timeA=True, timeB=True, timeOffset=True, 
                      timeABpause=True, timeBApause=True, flags=True, 
                      size=True, spoffset=False, update=True)
    if selected in ['LS_RAINBOW']:
      self.setEnabled(col1=True, col2=False, timeA=True, timeB=True, timeOffset=True, 
                      timeABpause=False, timeBApause=False, flags=True, 
                      size=True, spoffset=False, update=True)
    if selected in ['LS_FADE']:
      self.setEnabled(col1=True, col2=True, timeA=True, timeB=True, timeOffset=True, 
                      timeABpause=True, timeBApause=True, flags=True, 
                      size=False, spoffset=False, update=True)
    if selected in ['LS_INWARDS', 'LS_OUTWARDS']:
      self.setEnabled(col1=True, col2=True, timeA=True, timeB=True, timeOffset=True, 
                      timeABpause=True, timeBApause=True, flags=True, 
                      size=True, spoffset=True, update=True)
    if selected in ['LS_BREATH', 'LS_HEARTBEAT', 'LS_FLARE', 'LS_CYLON']:
      self.setEnabled(col1=True, col2=True, timeA=True, timeB=True, timeOffset=True, 
                      timeABpause=True, timeBApause=True, flags=True, 
                      size=True, spoffset=True, update=True)
    if selected in ['LS_WALL']:
      self.setEnabled(col1=False, col2=False, timeA=False, timeB=False, timeOffset=False, 
                      timeABpause=False, timeBApause=False, flags=False, 
                      size=False, spoffset=False, update=False)
    if selected in ['LS_GROW']:
      self.setEnabled(col1=False, col2=False, timeA=False, timeB=False, timeOffset=False, 
                      timeABpause=False, timeBApause=False, flags=False, 
                      size=False, spoffset=False, update=False)

    self.update_rgbhsvlabels()
    # if selected in ['LS_RAINBOW']:
    #   self.label_R1.setText("Val:")
    #   self.label_G1.setText("Sat:")
    #   # self.label_timeB.setText("size*10")
    #   # self.label_size.setText("size(<5 ) ")
    #   # self.spinBox_timeB.setSingleStep(1)
    # else:
    #   self.label_R1.setText("R:")
    #   self.label_G1.setText("G:")
    #   # self.label_timeB.setText("timeB:")
    #   # self.spinBox_timeB.setSingleStep(100)

  def misc_showlog_pushed(self, pressed):
    self.thlog_debug("misc_showlog_pushed")
    with loglock:
      if (pressed):
        self.textBrowser_sb_log.setVisible(False)
      else:
        self.textBrowser_sb_log.setVisible(True)

  def pushButton_hooks(self): #assumes self.cdialog
    ### Event handling hooks - pushButton s ###
    self.call.spinBox_timeA.valueChanged.connect(self.timeupdated)
    self.call.spinBox_timeB.valueChanged.connect(self.timeupdated)
    self.call.spinBox_timeOffset.valueChanged.connect(self.timeupdated)
    self.call.spinBox_timeABpause.valueChanged.connect(self.timeupdated)
    self.call.spinBox_timeBApause.valueChanged.connect(self.timeupdated)

    self.call.pushButton_misc_showlog.clicked.connect(self.misc_showlog_pushed)
    
    self.call.pushButton_update.clicked.connect(self.update_pushed)
    self.call.pushButton_pushPending.clicked.connect(self.pushPending_pushed)

    self.call.pushButton_getFWVersion.clicked.connect(self.getFWVersion_pushed)
    self.call.pushButton_saveFlash.clicked.connect(self.saveFlash_pushed)
    self.call.pushButton_getChannelInfo.clicked.connect(self.getChannelInfo_pushed)
    self.call.pushButton_getVerboseChannelInfo.clicked.connect(self.getVerboseChannelInfo_pushed)
    self.call.pushButton_loadFlash.clicked.connect(self.loadFlash_pushed)

    self.call.pushButton_loadsetup.clicked.connect(self.loadsetup_pushed)
    self.call.pushButton_savesetup.clicked.connect(self.savesetup_pushed)

    self.call.comboBox_channel.activated.connect(self.channel_selected)
    self.call.comboBox_ledstyle.activated.connect(self.ledstyle_selected)

    self.call.horizontalSlider_R1.valueChanged.connect(self.horizontalSliders_colorUpdated)
    self.call.horizontalSlider_G1.valueChanged.connect(self.horizontalSliders_colorUpdated)
    self.call.horizontalSlider_B1.valueChanged.connect(self.horizontalSliders_colorUpdated)
    self.call.horizontalSlider_R2.valueChanged.connect(self.horizontalSliders_colorUpdated)
    self.call.horizontalSlider_G2.valueChanged.connect(self.horizontalSliders_colorUpdated)
    self.call.horizontalSlider_B2.valueChanged.connect(self.horizontalSliders_colorUpdated)
    self.call.spinBox_R1.valueChanged.connect(self.spinBoxes_colorUpdated)
    self.call.spinBox_G1.valueChanged.connect(self.spinBoxes_colorUpdated)
    self.call.spinBox_B1.valueChanged.connect(self.spinBoxes_colorUpdated)
    self.call.spinBox_R2.valueChanged.connect(self.spinBoxes_colorUpdated)
    self.call.spinBox_G2.valueChanged.connect(self.spinBoxes_colorUpdated)
    self.call.spinBox_B2.valueChanged.connect(self.spinBoxes_colorUpdated)


    self.call.horizontalSlider_Rcor.valueChanged.connect(self.horizontalSliders_colorCorrectUpdated)
    self.call.horizontalSlider_Gcor.valueChanged.connect(self.horizontalSliders_colorCorrectUpdated)
    self.call.horizontalSlider_Bcor.valueChanged.connect(self.horizontalSliders_colorCorrectUpdated)
    self.call.spinBox_Rcor.valueChanged.connect(self.spinBoxes_colorCorrectUpdated)
    self.call.spinBox_Gcor.valueChanged.connect(self.spinBoxes_colorCorrectUpdated)
    self.call.spinBox_Bcor.valueChanged.connect(self.spinBoxes_colorCorrectUpdated)

    self.call.horizontalSlider_Tempcor.valueChanged.connect(self.horizontalSliders_colorCorrectUpdated)
    self.call.horizontalSlider_Brightcor.valueChanged.connect(self.horizontalSliders_colorCorrectUpdated)
    self.call.spinBox_Tempcor.valueChanged.connect(self.spinBoxes_colorCorrectUpdated)
    self.call.spinBox_Brightcor.valueChanged.connect(self.spinBoxes_colorCorrectUpdated)

    self.call.pushButton_setColorCorrection.clicked.connect(self.setColorCorrection_pushed)
    self.call.pushButton_switchCorrectionMode.clicked.connect(self.switchCorrectionMode_pushed)

    self.call.checkBox_b1_hsvassign.clicked.connect(self.b1_hsvassign_pushed)

    # self.call.textBrowser_sb_log.verticalScrollBar().rangeChanged.connect(self.textBrowser_sb_log_range_changed)






    # self.call.verticalSlider_pb_imageselector.valueChanged.connect(self.imageselector_changed)
    
    return
  


def SerialArdHandler(_ledqt, repeat_sec=.1):
  while True:
    try:
      _ledqt.thlog_info("Connecting to Serial...")
      ser = connectArdSerial()
      while type(ser) == type('just a string'):
        _ledqt.thlog_debug("Unable to connect to COM port... retrying.")
        time.sleep(2)
        ser = connectArdSerial()
      ser.read() # flush initial IO from Arduino
      # _ledqt.getFWVersion()
      # _ledqt.getChannelInfoByCurrent()

      cmdbytes_list=[]
      while True:
        # print (_ledqt)
        # print (ser)
        # print('waiting?')
        if (ser.isOpen()):
          # print('waiting!')
          # print(f'pending updates: {_ledqt.pendingUpdates}')
          just_sent=False
          # cmdbytes=""
          # with ioqlock:
          #   # print('waiting...')
          #   # with ioqlock:
          #   if ioreqs:
          #     cmdbytes = ioreqs.pop(0)
          # if cmdbytes:
          #   callonly(ser, packbytes(cmdbytes))
          #   # printcallresponse(ser, packbytes(cmdbytes))
          #   just_sent = True
          with ioqlock:
            while ioreqs:
              cmdbytes_list.append(ioreqs.pop(0))
          bigbytes=b''
          if RESEND_VERIFY:
            if (_ledqt.ser_responsespending):
              #Check for any pending responses needed, queue up commands to send again
              prs_checked = 0 
              pr_i        = _ledqt.ser_lastpktid

              while prs_checked < _ledqt.ser_responsespending and (len(bigbytes) < SEND_BYTES_THRESHOLD):
                if not _ledqt.ser_rsps[pr_i]: #no response yeti
                  #check if time passed is sufficient to resend:
                  if (datetime.now() - _ledqt.ser_lastsenddt[pr_i]).microseconds/1000 > RESEND_DELAY_MS:
                    _ledqt.ser_sends[pr_i] += 1
                    if _ledqt.ser_sends[pr_i] > RESEND_MAX_TRIES:
                      # don't resend, we just failed to get a response
                      _ledqt.thlog_error(f"Failed to get a response on command: {_ledqt.ser_msgs[pr_i]} at pktid: {pr_i} after {_ledqt.ser_sends[pr_i]-1} sends.")
                      _ledqt.ser_rsps[pr_i] = 'fail'
                      _ledqt.ser_responsespending -= 1
                    else:
                      # Check that this isn't a special command that would tank the MCU:
                      if (_ledqt.ser_msgs[pr_i][1] in [SPC_DEBUGTIMING, SPC_READVERBOSESTATE]):
                        _ledqt.thlog_info(f"Foregoing resend for SPC command[{pr_i}]: <{_ledqt.ser_msgs[pr_i][1]}>.")
                      else:
                        print(f"Resend: [{pr_i}] ({_ledqt.ser_responsespending} pending)")
                        _ledqt.ser_lastsenddt[pr_i] = datetime.now()
                        bigbytes = bigbytes + packbytes(_ledqt.ser_msgs[pr_i], packetid=pr_i)

                  prs_checked += 1
                pr_i = (pr_i-1)%256
                if pr_i == _ledqt.ser_lastpktid: #looped around, hmm
                  _ledqt.thlog_error(f"Could not account for all pending responses! {prs_checked} of {_ledqt.ser_responsespending} ")
                  break


          while cmdbytes_list and (len(bigbytes) < SEND_BYTES_THRESHOLD):  # Send all pending commands at once!  Good luck!
            # callonly(ser, packbytes(cmdbytes_list.pop(0)))
                # for resend/verify:
            _ledqt.ser_lastpktid = (_ledqt.ser_lastpktid + 1) % 256 # inc
            if RESEND_VERIFY:
              _ledqt.awaitingconfirmations = True
              _ledqt.ser_responsespending += 1
              _ledqt.ser_msgs[_ledqt.ser_lastpktid] = cmdbytes_list.pop(0)
              # print(f"start pktid[{_ledqt.ser_lastpktid}] for ch[{_ledqt.ser_msgs[_ledqt.ser_lastpktid][0]}]")
              _ledqt.ser_rsps[_ledqt.ser_lastpktid] = b'' # flag that we're awaiting a response here
              _ledqt.ser_sends[_ledqt.ser_lastpktid] = 1
              _ledqt.ser_lastsenddt[_ledqt.ser_lastpktid] = datetime.now()
              bigbytes = bigbytes + packbytes(_ledqt.ser_msgs[_ledqt.ser_lastpktid], packetid=_ledqt.ser_lastpktid)
            else:
              bigbytes = bigbytes + packbytes(cmdbytes_list.pop(0), packetid=_ledqt.ser_lastpktid)
          if bigbytes:
            callonly(ser, bigbytes)
            just_sent = True
          # purge waiting output
          while (ser.in_waiting):

            pktid, result = readandunpackbytes(ser, headout=5) #packetidcheck_=False, packetid_=0,
            # print(f"got response: {pktid}, {result}")
            if result: # ignore empty/ timeouts on listen
              if result[0] < _ledqt.num_channels and len(result)==MODE_BYTE_SIZE: # a channel report (not verbose)
                # print('Command packet')
                # with updatelock:
                
                # If we already have a pending request for another channel info update, don't push the fields to UI
                # _currreqisupdate = True
                _nextreqisupdate = False
                with ioqlock:
                  if ioreqs and ioreqs[0][1] == SPC_READSTATE:  # TODO: ONLY works with individual messages - get to work with compound, 'bigbyte' send
                    _nextreqisupdate = True
                  # elif (not ioreqs) or ioreqs[0][1] != SPC_READSTATE:
                  # else: # either next req is not for an update (eg timing) or no ioreqs remaining
                    # _currreqisupdate = True
                
                # Check to see if this channel has a request on the results, pass it along if it does.
                with channellock:
                  if _ledqt.channels_requested[result[0]]: 
                    _ledqt.channel_responses[result[0]] = result

                if RESEND_VERIFY:
                  #first response for this message? - ignore future incoming repeat responses on same pktid
                  if not _ledqt.ser_rsps[int(pktid[0])]: 
                    _moreupdateswaiting = False
                    #todo: could make this faster by not checking the whole lot..
                    #TODO: use highest pktid for refresh...
                    for i in range(256):
                      if not _ledqt.ser_rsps[i]:
                        if _ledqt.ser_msgs[i][1] == SPC_READSTATE:
                          if i != int(pktid[0]):
                            #we found other commands waiting for status - 
                            _moreupdateswaiting = True
                    # if not _nextreqisupdate:
                    if not _moreupdateswaiting:
                      # print('update with latest')
                      _ledqt.setFieldsByBytes(result)  # Update UI fields if we don't have more reqs waiting
                    else:
                      print("<<<don't push update, more requests waiting>>>")
                      with updatelock:
                        _ledqt.pendingUpdates -= 1 # Drop current update, don't push to fields
                    if (_ledqt.manualRequest):
                      printhex(result, contig=2)
                      _ledqt.manualRequest = False
                else: #not RESEND_VERIFY:
                  if not _nextreqisupdate:
                    # print('update with latest')
                    _ledqt.setFieldsByBytes(result)  # Update UI fields if we don't have more reqs waiting
                  else:
                    print("<<<don't push update, latest coming>>>")
                    with updatelock:
                      _ledqt.pendingUpdates -= 1 # Drop current update, don't push to fields
                  if (_ledqt.manualRequest):
                    printhex(result, contig=2)
                    _ledqt.manualRequest = False
                # _ledqt.pendingUpdates -= 1
              else:
                # print(f"result:{result.decode('utf-8')}")
                # _ledqt.thlog_info(f"ARD: {result.decode('utf-8')}")
                try:
                  # result_string = result.decode('utf-8')
                  if type(pktid) is bytes and len(pktid):
                    if (_ledqt.ser_rsps[int(pktid[0])]): # repeat response
                      if result != _ledqt.ser_rsps[int(pktid[0])]:
                        _ledqt.thlog_info(f"ARD [{pktid[0]}]++: {result.decode('utf-8')} ")
                    else: # first response
                      _ledqt.thlog_info(f"ARD [{pktid[0]}]  : {result.decode('utf-8')} ")
                  else: # empty packet id?? returned as int??
                    _ledqt.thlog_info(f"bad pktid: {pktid} of {type(pktid)}.")
                  # if b_ and b_[0] >= 32 and b_[0] <= 126:
                    # print(b_.decode('utf-8'), end='')
                  # else:
                    # print(b_.hex(), end='')
                # except UnicodeDecodeError:
                except:
                  _ledqt.thlog_info(f"ARD [{pktid[0]}]:    \\x{result.hex()} ")
                  # result_string = result.hex()
                  # print(int(b_), end='')
                # printhex(result, header=False, contig=2)
              #What do do with any result:
              if RESEND_VERIFY:
                if type(pktid) is bytes and len(pktid): #valid pktid:
                  if (_ledqt.ser_rsps[int(pktid[0])]):
                    #well shoot-dang.  We got a repeated response.  No worries.
                    #This is to be expected if it's a long string like READVERBOSESTATE or DEBUGTIMING
                    # if _ledqt.ser_msgs[int(pktid[0])]: #ignore empty responses
                    # print(int(pktid[0]))
                    # print(_ledqt.ser_msgs[int(pktid[0])])
                    # print(_ledqt.ser_msgs[int(pktid[0])][1])
                    if not _ledqt.ser_msgs[int(pktid[0])]:
                      _ledqt.thlog_error(f"Unexpected pktid returned: {int(pktid[0])}")
                    else:
                      if _ledqt.ser_msgs[int(pktid[0])][1] in [SPC_READVERBOSESTATE, SPC_DEBUGTIMING]:
                        # _ledqt.thlog_info(f"ARD [{pktid[0]}]++: {_ledqt.ser_msgs[int(pktid[0])]} : {_ledqt.ser_rsps[int(pktid[0])]} and then {result}")
                        # _ledqt.thlog_info(f"ARD [{pktid[0]}]++: {_ledqt.ser_msgs[int(pktid[0])]} : {result}")
                        _ledqt.ser_rsps[int(pktid[0])] += result
                        pass
                      else:
                        # _ledqt.thlog_warning(f"repeat response for cmd[{pktid[0]}]: {_ledqt.ser_msgs[int(pktid[0])]} : {_ledqt.ser_rsps[int(pktid[0])]} and then {result}")
                        pass
                  else:
                    # Got a response, have been waiting for this one:
                    if not _ledqt.ser_msgs[int(pktid[0])]:
                      _ledqt.thlog_error(f"No cmd msg for response provided.")
                    else:
                              # [0] can be a channel index
                              # [1] can be an effect or SPC_ index:
                              # 
                              # SPC_READVERBOSESTATE   = 248
                              # SPC_LOADEEPROM         = 249
                              # SPC_STOREEEPROM        = 250
                              # SPC_DEBUGTIMING        = 251
                              # SPC_CORRECTTEMPERATURE = 252
                              # SPC_CORRECTCOLOR       = 253
                              # SPC_GETFWVER           = 254
                              # SPC_READSTATE          = 255
                      if _ledqt.ser_msgs[int(pktid[0])][1] in [SPC_READVERBOSESTATE, SPC_LOADEEPROM, SPC_STOREEEPROM, SPC_GETFWVER,
                                                               SPC_CORRECTTEMPERATURE, SPC_CORRECTCOLOR, SPC_DEBUGTIMING]:
                        # Just accept whatever comes through
                        _ledqt.ser_responsespending -= 1
                        _ledqt.ser_rsps[int(pktid[0])] = result
                        pass
                      elif _ledqt.ser_msgs[int(pktid[0])][1] == SPC_UPDATEPENDING:
                        if result[0] in [b'K'[0]]: # success
                          _ledqt.ser_responsespending -= 1
                          _ledqt.ser_rsps[int(pktid[0])] = result
                        pass
                      elif _ledqt.ser_msgs[int(pktid[0])][1] == SPC_READSTATE:
                        #TODO: make sure this looks right..
                        _ledqt.ser_responsespending -= 1
                        _ledqt.ser_rsps[int(pktid[0])] = result
                        pass
                      # Is this a channel assignment packet? Check for 'K', make sure response confirms success
                      elif _ledqt.ser_msgs[int(pktid[0])][1] <= MAX_LS_MODE:
                        if result[0] in [b'M'[0], b'V'[0], b'L'[0], b'F'[0], b'E'[0]]: # no good - malformed packet, value missing
                          # ignore = and retry asap.  hack the last-sent time to resend on the next round
                          _ledqt.ser_lastsenddt[int(pktid[0])] = datetime.now() - timedelta(milliseconds=RESEND_DELAY_MS)
                        elif result[0] in [b'K'[0]]: # success
                          _ledqt.ser_responsespending -= 1
                          _ledqt.ser_rsps[int(pktid[0])] = result
                          pass
                        elif _ledqt.ser_msgs[int(pktid[0])][1] == SPC_READSTATE:
                          #TODO: make sure this looks right..
                          _ledqt.ser_responsespending -= 1
                          _ledqt.ser_rsps[int(pktid[0])] = result
                          pass
                        # Is this a channel assignment packet? Check for 'K', make sure response confirms success
                        elif _ledqt.ser_msgs[int(pktid[0])][1] <= MAX_LS_MODE:
                          if result[0] in [b'M'[0], b'V'[0], b'L'[0], b'F'[0], b'E'[0]]: # no good - malformed packet, value missing
                            # ignore = and retry asap.  hack the last-sent time to resend on the next round
                            _ledqt.ser_lastsenddt[int(pktid[0])] = datetime.now() - timedelta(milliseconds=RESEND_DELAY_MS)
                          elif result[0] in [b'K'[0]]: # success
                            _ledqt.ser_responsespending -= 1
                            _ledqt.ser_rsps[int(pktid[0])] = result
                          else: # Not sure what that was.. assume retry
                            _ledqt.thlog_error(f"Unexpected response {result} on cmd[{pktid[0]}] ({_ledqt.ser_msgs[int(pktid[0])]}): trying to resend...")
                        else:
                          _ledqt.thlog_error(f"Unrecognized response type {result} on cmd[{pktid[0]}] ({_ledqt.ser_msgs[int(pktid[0])]}): trying to resend...")

                        # else if _ledqt.ser_msgs[int(pktid[0])][1] in [SPC_DEBUGTIMING, SPC_READSTATE]:
                          # if result[0] in [b'M'[0], b'V'[0], b'L'[0], b'F'[0], b'E'[0]]: # ...
                          # ...
                else:
                  _ledqt.thlog_info(f"bad pktid (resend branch): {pktid} of {type(pktid)}.")

          if just_sent:
            # TODO: make this a little cleaner, faster, more elegant...
            time.sleep(MAX_SEND_INTERVAL);
            just_sent = False
          else:
            if _ledqt.ser_responsespending: #If we need to resend, don't wait, reloop now
              time.sleep(.020) #wait but not very much 
              pass
            else:  #If we don't need to resend, all responses are accounted for 
              #first check if we _just_ got all responses:
              if _ledqt.awaitingconfirmations:
                # with ioqlock  # DEBUG
                  # ioreqs.append(getUpdatePendingBytes())
                _ledqt.awaitingconfirmations = False
              else: #we're good, just hang out, chill for 1 tenth of a second
                time.sleep(repeat_sec) 
          _ledqt.isSerConnected = True
        else:
          _ledqt.isSerConnected = False
          _ledqt.thlog_warning(f"serial not open, attempting to reconnect...")
          time.sleep(1)
          ser = connectArdSerial()
          # return
    except:
      _ledqt.thlog_error("Issue with updatePos loop. ")
      _ledqt.thlog_error("Unexpected error: " + traceback.format_exc())
    _ledqt.thlog_warning('Error with SerialArdHandler, trying again..')

    time.sleep(3)

def regularPushChannel(_ledqt, repeat_sec=.250):
  count_ = 40 
  time.sleep(5)
  try:
    while True:
      time.sleep(repeat_sec)
      # if _ledqt.pushButton_misc_update_timing.isChecked():
      if STRESS_UPDATES:
        count_ -= 1 # DEBUG - set all channels at once, check timing
        if count_ == 20:
          with ioqlock:
            # for i in range(11):
            # for i in range(8):
            #   ioreqs.append(setChannelBytesOFF(i+3))
            # for i in range(8):
            #   ioreqs.append(setChannelBytesOFF(i+3))
            for i in range(11):
              ioreqs.append(setChannelBytes(i, _style=LS_INWARDS, 
                              _col1=RGB((120+i*10)%256,210,20), _col2=RGB((160+i*10)%256,210,20), 
                              _maintainTimestep=True, _forwardHue=False, _forwardSpace=True, _gamma=False, 
                              _holdUpdate=False, _dither=True, _HSVassign=True, _HSVtrans=False,
                              _size=4, _spoffset=0, 
                              _timeA=1000, _timeB=1000))
        if count_ == 0:
          with ioqlock:
            # ioreqs.append(setChannelBytesON(0, RGB(10,0,0)))
            # ioreqs.append(setChannelBytesON(1, RGB(0,10,0)))
            # ioreqs.append(setChannelBytesON(2, RGB(0,0,10)))
            # ioreqs.append(setChannelBytesON(3, RGB(10,0,0)))
            # ioreqs.append(setChannelBytesON(4, RGB(0,10,0)))
            # ioreqs.append(setChannelBytesON(5, RGB(0,0,10)))
            # ioreqs.append(setChannelBytesON(6, RGB(10,0,0)))
            # ioreqs.append(setChannelBytesON(7, RGB(0,10,0)))
            # ioreqs.append(setChannelBytesON(8, RGB(0,0,10)))
            # ioreqs.append(setChannelBytesON(9, RGB(10,0,0)))
            # ioreqs.append(setChannelBytesON(10, RGB(0,10,0)))
            # for i in range(8):
            #   ioreqs.append(setChannelBytes(i+3, _style=LS_INWARDS, 
            #                   _col1=RGB((20+i*10)%256,210,20), _col2=RGB((180+i*10)%256,210,20), 
            #                   _maintainTimestep=True, _forwardHue=False, _forwardSpace=True, _gamma=False, 
            #                   _holdUpdate=False, _dither=True, _HSVassign=True, _HSVtrans=False,
            #                   _size=100, _spoffset=0, 
            #                   _timeA=1000, _timeB=1000))
            for i in range(11):
              ioreqs.append(setChannelBytes(i, _style=LS_INWARDS, 
                              _col1=RGB((230+i*10)%256,210,20), _col2=RGB((270+i*10)%256,210,20), 
                              _maintainTimestep=True, _forwardHue=False, _forwardSpace=True, _gamma=False, 
                              _holdUpdate=False, _dither=True, _HSVassign=True, _HSVtrans=False,
                              _size=4, _spoffset=0, 
                              _timeA=1000, _timeB=1000))
            # printhex(setChannelBytes((3), _style=LS_INWARDS, 
            #                 _col1=RGB((230+(3)*10)%256,210,20), _col2=RGB((270+(3)*10)%256,210,20), 
            #                 _maintainTimestep=True, _forwardHue=False, _forwardSpace=True, _gamma=False, 
            #                 _holdUpdate=False, _dither=True, _HSVassign=True, _HSVtrans=False,
            #                 _size=4, _spoffset=0, 
            #                 _timeA=1025, _timeB=1025))
            # printhex(setChannelBytes((3), _style=LS_INWARDS, 
            #                 _col1=RGB((230+(3)*10)%256,210,20), _col2=RGB((270+(3)*10)%256,210,20), 
            #                 _maintainTimestep=True, _forwardHue=False, _forwardSpace=True, _gamma=False, 
            #                 _holdUpdate=True, _dither=True, _HSVassign=True, _HSVtrans=False,
            #                 _size=4, _spoffset=0, 
            #                 _timeA=1025, _timeB=1025))
            # printhex(setChannelBytes((3), _style=LS_INWARDS, 
            #                 _col1=RGB((230+(3)*10)%256,210,20), _col2=RGB((270+(3)*10)%256,210,20), 
            #                 _maintainTimestep=True, _forwardHue=False, _forwardSpace=True, _gamma=False, 
            #                 _holdUpdate=True, _dither=False, _HSVassign=True, _HSVtrans=False,
            #                 _size=4, _spoffset=0, 
            #                 _timeA=1025, _timeB=1025))
            # printhex(setChannelBytes((3), _style=LS_INWARDS, 
            #                 _col1=RGB((230+(3)*10)%256,210,20), _col2=RGB((270+(3)*10)%256,210,20), 
            #                 _maintainTimestep=True, _forwardHue=False, _forwardSpace=True, _gamma=False, 
            #                 _holdUpdate=False, _dither=False, _HSVassign=True, _HSVtrans=False,
            #                 _size=4, _spoffset=0, 
            #                 _timeA=1025, _timeB=1025))
              # ioreqs.append(setChannelBytesCHASE(i+3, 
              #                 _col1=RGB((20+i*10)%256,200,10), _col2=RGB((180+i*10)%256,100,10), 
              #                 _maintainTimestep=True, _dither=True, _HSVassign=True, _HSVtrans=True,
              #                 _forwardSpace=True, _gamma=False, _forwardHue=False, _holdUpdate=True, 
              #                 _timeA=1000, _timeB=1000, _timeOffset=0, _timeABpause=50, _timeBApause=50,
              #                 _size=10, _spoffset=0))
          count_ = 40

      if _ledqt.checkBox_PCtoard.isChecked():
        if _ledqt.recentChanges():
          # print('changes')
          _ledqt.setChannelByFields()
        else:
          # print('No changes!')
          pass
  except:
    _ledqt.thlog_error("Issue with PushChannel loop. ")
    _ledqt.thlog_error("Unexpected error: " + traceback.format_exc())

def regularTimingQuery(_ledqt, repeat_sec=3):
  try:
    while True:
      time.sleep(repeat_sec)
      # if _ledqt.pushButton_misc_update_timing.isChecked():
      if _ledqt.checkBox_timing.isChecked():
        with ioqlock:
          ioreqs.append(getDebugTimingBytes())
  except:
    _ledqt.thlog_error("Issue with reqTiming loop. ")
    _ledqt.thlog_error("Unexpected error: " + traceback.format_exc())

###  Main  ###

def main():
  # app = QtWidgets.QApplication(sys.argv)
  app = QApplication(sys.argv)

  # ser = connectArdSerial()

  # LEDControlQt, handles events from and updates to UI
  ledqt = LEDControlQT() 

  # Threading for IO - Should be safer and easier
  SerialArdHandler_ = Thread(target=SerialArdHandler, args=(ledqt,), daemon=True)
  pushChannelthread = Thread(target=regularPushChannel, args=(ledqt,), daemon=True)
  updateTimingthread = Thread(target=regularTimingQuery, args=(ledqt,), daemon=True)

  SerialArdHandler_.start()
  pushChannelthread.start()
  updateTimingthread.start()

  # run
  sys.exit(app.exec_())

### Start ###

if __name__ == "__main__":
  main()





### TEST ###
