# This Python file uses the following encoding: utf-8

# Submit series of state changes to USB/Serial-attached PCA 
# to test ecoATM LED control board.
# 
# - Nathaniel Gustafson 27 Jan 2021

import sys, os
# from pathlib import Path

import faulthandler
faulthandler.enable()

# import PyQt5
# from PyQt5 import QtCore, QtGui, QtWidgets, uic
# from PyQt5 import QtCore, QtWidgets
# from PyQt5.QtWidgets import QMainWindow
# from PyQt5.QtWidgets import *
# from PyQt5.QtCore import QSize, QTimer, QDateTime, Qt
# from PyQt5.QtGui import *

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
RESEND_DELAY_MS = 20 #20 #5 #20 #based roughly around frame rate
RESEND_MAX_TRIES = 10 #plz don't overflow the poor serial buffer

STRESS_UPDATES = False
# STRESS_UPDATES = True

READ_TIMING = False

NUM_CHANNELS = 12

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
    print(record)


class LEDControl(): #QMainWindow):
  def __init__(self):
    super().__init__()

    if not os.path.exists('logs'):
      os.makedirs('logs')
    self.initlogging()
    self.initvalues()
    # time.sleep(.5)


  def initlogging(self):
    self.log = logging.getLogger('ecoatmledtest')
    
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
    # fh.setFormatter(formatter)
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
    self.num_channels = NUM_CHANNELS
    self.channels_requested = [False]*self.num_channels
    self.channel_responses = [b'']*self.num_channels
    
    self.total_success_responses = 0
    self.total_fail_responses = 0

    self.connectedForSerialTest = False


  ### Event Handlers - key press ###


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



def SerialArdHandler(_ledqt, repeat_sec=.1):
  while True:
    try:
      # Open in main loop for serial test, don't need redundancy here?
      _ledqt.thlog_info("Connecting to Serial...")
      ser = connectArdSerial()
      # ser.write(b'1') 
      # print(ser)
      while type(ser) == type('just a string'):
        _ledqt.thlog_debug("Unable to connect to COM port... retrying.")
        time.sleep(2)
        ser = connectArdSerial()
      ser.read() # flush initial IO from Arduino
      # _ledqt.getFWVersion()
      # _ledqt.getChannelInfoByCurrent()
      _ledqt.connectedForSerialTest = True

      bigbytes=b''
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
                      # _ledqt.setFieldsByBytes(result)  # Update UI fields if we don't have more reqs waiting
                      pass
                    else:
                      # print("<<<don't push update, more requests waiting>>>")
                      with updatelock:
                        _ledqt.pendingUpdates -= 1 # Drop current update, don't push to fields
                    # if (_ledqt.manualRequest):
                      # printhex(result, contig=2)
                      # _ledqt.manualRequest = False
                    printhex(result, contig=2)
                else: #not RESEND_VERIFY:
                  if not _nextreqisupdate:
                    # print('update with latest')
                    # _ledqt.setFieldsByBytes(result)  # Update UI fields if we don't have more reqs waiting
                    pass
                  else:
                    print("<<<don't push update, latest coming>>>")
                    with updatelock:
                      _ledqt.pendingUpdates -= 1 # Drop current update, don't push to fields
                  # if (_ledqt.manualRequest):
                    # printhex(result, contig=2)
                    # _ledqt.manualRequest = False
                  printhex(result, contig=2)
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
                          _ledqt.total_success_responses += 1
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
                          _ledqt.total_fail_responses += 1
                          _ledqt.ser_lastsenddt[int(pktid[0])] = datetime.now() - timedelta(milliseconds=RESEND_DELAY_MS)
                        elif result[0] in [b'K'[0]]: # success
                          _ledqt.total_success_responses += 1
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
                            _ledqt.total_fail_responses += 1
                            _ledqt.ser_lastsenddt[int(pktid[0])] = datetime.now() - timedelta(milliseconds=RESEND_DELAY_MS)
                          elif result[0] in [b'K'[0]]: # success
                            _ledqt.total_success_responses += 1
                            _ledqt.ser_responsespending -= 1
                            _ledqt.ser_rsps[int(pktid[0])] = result
                          else: # Not sure what that was.. assume retry
                            _ledqt.total_fail_responses += 1
                            _ledqt.thlog_error(f"Unexpected response {result} on cmd[{pktid[0]}] ({_ledqt.ser_msgs[int(pktid[0])]}): trying to resend...")
                        else:
                          _ledqt.thlog_error(f"Unrecognized response type {result} on cmd[{pktid[0]}] ({_ledqt.ser_msgs[int(pktid[0])]}): trying to resend...")

                        # else if _ledqt.ser_msgs[int(pktid[0])][1] in [SPC_DEBUGTIMING, SPC_READSTATE]:
                          # if result[0] in [b'M'[0], b'V'[0], b'L'[0], b'F'[0], b'E'[0]]: # ...
                          # ...
                else:
                  _ledqt.total_fail_responses += 1
                  _ledqt.thlog_info(f"bad pktid (resend branch): {pktid} of {type(pktid)}.")

          bigbytes=b''
          if RESEND_VERIFY:
            if (_ledqt.ser_responsespending):
              #Check for any pending responses needed, queue up commands to send again
              prs_checked = 0 
              pr_i        = _ledqt.ser_lastpktid

              while prs_checked < _ledqt.ser_responsespending and (len(bigbytes) < SEND_BYTES_THRESHOLD):
                if not _ledqt.ser_rsps[pr_i]: #no response yet
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
          
          if just_sent:
            # TODO: make this a little cleaner, faster, more elegant...
            # time.sleep(MAX_SEND_INTERVAL);
            time.sleep(.005);
            just_sent = False
          else:
            if _ledqt.ser_responsespending: #If we need to resend, don't wait, reloop now
              time.sleep(.005) #wait but not very much 
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
            # for i in range(NUM_CHANNELS):
            # for i in range(8):
            #   ioreqs.append(setChannelBytesOFF(i+3))
            # for i in range(8):
            #   ioreqs.append(setChannelBytesOFF(i+3))
            for i in range(NUM_CHANNELS):
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
            for i in range(NUM_CHANNELS):
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

  except:
    _ledqt.thlog_error("Issue with PushChannel loop. ")
    _ledqt.thlog_error("Unexpected error: " + traceback.format_exc())

def regularTimingQuery(_ledqt, repeat_sec=3):
  try:
    while True:
      time.sleep(repeat_sec)
      # if _ledqt.pushButton_misc_update_timing.isChecked():
      if READ_TIMING == True:
        with ioqlock:
          ioreqs.append(getDebugTimingBytes())
  except:
    _ledqt.thlog_error("Issue with reqTiming loop. ")
    _ledqt.thlog_error("Unexpected error: " + traceback.format_exc())

###  Main  ###

def run_test_cycle(ledqt):
  snap_success = ledqt.total_success_responses
  snap_fail    = ledqt.total_fail_responses
  # Everything off:
  ledqt.thlog_info("     ***  Everything Off  ***     ")
  time.sleep(1)
  for i in range(NUM_CHANNELS):
    ioreqs.append(setChannelBytes(i, _style=LS_OFF))
  time.sleep(1)

  # Each section one color (rgb):
  ledqt.thlog_info("     ***  Color by Color test  ***     ")
  time.sleep(1)
  for mask in [[1,0,0],[0,1,0],[0,0,1],[1,1,0],[1,0,1],[0,1,1],[1,1,1]]:
    for cb in range(8):
      with ioqlock:
        min_ = 20
        for i in range(NUM_CHANNELS):
          ioreqs.append(setChannelBytes(i, _style=LS_ON,
                          _col1=RGB((int)(((((mask[0]*(((i%2)*100)+i*20+cb*64))%256)**2)/(256))*(255-min_)/(256)+min_*mask[0]),
                                    (int)(((((mask[1]*(((i%2)*100)+i*20+cb*64))%256)**2)/(256))*(255-min_)/(256)+min_*mask[1]),
                                    (int)(((((mask[2]*(((i%2)*100)+i*20+cb*64))%256)**2)/(256))*(255-min_)/(256)+min_*mask[2]) )))
      time.sleep(0.5)

  # Each section max bright alternating:
  ledqt.thlog_info("     ***  Color test max bright, alternating  ***     ")
  time.sleep(1)
  for j in [0,1,2,3,4,5]:
    with ioqlock:
      for i in range(NUM_CHANNELS):
        ioreqs.append(setChannelBytes(i, _style=LS_ON,
                        _col1=RGB(((i+j)%2)*255,
                                  ((i+j)%2)*255,
                                  ((i+j)%2)*255 )))
    time.sleep(1)
    # time.sleep(3)

  # Each section max bright oww (rgb WHITE:
  ledqt.thlog_info("     ***  Color test MAX BRIGHT  ***     ")
  time.sleep(1)
  for mask in [[1,0,0],[0,1,0],[0,0,1],[1,1,1],[1,1,1],[1,1,1],[1,1,1],[1,1,1]]:
    with ioqlock:
      for i in range(NUM_CHANNELS):
        ioreqs.append(setChannelBytes(i, _style=LS_ON,
                        _col1=RGB(mask[0]*255,
                                  mask[1]*255,
                                  mask[2]*255 )))
    time.sleep(2)
    # time.sleep(3)

  # Each section max Rainbow bright oww (hue):
  ledqt.thlog_info("     ***  BRIGHT  ***     ")
  time.sleep(1)
  with ioqlock:
    for i in range(NUM_CHANNELS):
      ioreqs.append(setChannelBytes(i, _style=LS_RAINBOW, 
                      _col1=RGB(0,255,255), _col2=RGB(0,255,255), 
                      _maintainTimestep=True, _forwardHue=(True if (i)%2 else False), _forwardSpace=(True if (i)%4>1 else False), 
                      _gamma=False, 
                      _holdUpdate=False, _dither=False, _HSVassign=True, _HSVtrans=True,
                      _size=10, _spoffset=0, 
                      _timeA=1000, _timeB=1000))
  time.sleep(3)

  # Each section one color (hue):
  ledqt.thlog_info("     ***  Color by Hue  ***     ")
  time.sleep(1)
  for cb in range(6):
    with ioqlock:
      for i in range(NUM_CHANNELS):
        ioreqs.append(setChannelBytes(i, _style=LS_ON,
                        _col1=RGB((cb*30+i*30)%256,235,80),  _HSVassign=True, _holdUpdate=False, _dither=False))
    time.sleep(1)

  # Some animations:
  ledqt.thlog_info("     ***  Inwards (Chase var)  ***     ")
  time.sleep(1)
  for cb in range(4):
    with ioqlock:
      for i in range(NUM_CHANNELS):
        ioreqs.append(setChannelBytes(i, _style=LS_INWARDS, 
                        _col1=RGB((120+i*10 + cb*64)%256,255,80), _col2=RGB((160+i*10 + cb*64)%256,255,80), 
                        _maintainTimestep=True, _forwardHue=False, _forwardSpace=True, _gamma=False, 
                        _holdUpdate=False, _dither=False, _HSVassign=True, _HSVtrans=False,
                        _size=4, _spoffset=0, 
                        _timeA=1000, _timeB=1000))
    time.sleep(2)
  ledqt.thlog_info("     ***  Fade  ***     ")
  time.sleep(1)
  for cb in range(5):
    with ioqlock:
      for i in range(NUM_CHANNELS):
        ioreqs.append(setChannelBytes(i, _style=LS_FADE, 
                        _col1=RGB((120+i*10 + cb*64)%256,210,80), _col2=RGB((180+i*10 + cb*64)%256,210,20), 
                        _maintainTimestep=True, _forwardHue=False, _forwardSpace=True, _gamma=False, 
                        _holdUpdate=False, _dither=False, _HSVassign=True, _HSVtrans=False,
                        _size=4, _spoffset=0, 
                        _timeA=1000, _timeB=1000))
    time.sleep(2)
  ledqt.thlog_info("     ***  More Rainbow  ***     ")
  time.sleep(1)
  for cb in range(4):
    with ioqlock:
      for i in range(NUM_CHANNELS):
        ioreqs.append(setChannelBytes(i, _style=LS_RAINBOW, 
                        _col1=RGB(0,255,80), _col2=RGB(0,255,80), 
                        _maintainTimestep=True, _forwardHue=(True if (i+cb)%2 else False), _forwardSpace=(True if (i+cb)%4>1 else False), 
                        _gamma=False, 
                        _holdUpdate=False, _dither=False, _HSVassign=True, _HSVtrans=True,
                        _size=10, _spoffset=0, 
                        _timeA=1000, _timeB=1000))
    time.sleep(2)

  ledqt.thlog_info("     ***  Get Channel Info  ***     ")
  time.sleep(1)
  # get ch info
  for cb in range(3):
    for i in range(NUM_CHANNELS):
      with ioqlock:
        ioreqs.append(getChannelInfoBytes(i))
      time.sleep(.3)

  ledqt.thlog_info("     ***  Setting Temperature  ***     ")
  time.sleep(1)
  # set temp
  for ct in [4500, 2500, 3500, 4500, 5500, 6500, 8500, 12000]:
    with ioqlock:
      ioreqs.append(setTemperatureCorrectionBytes(_bright=255, _kel=ct))
    time.sleep(1)

  ledqt.thlog_info("     ***  Setting Color Correction  ***     ")
  time.sleep(1)
  # set color correction 
  for cc in [[255,200,255],[120,70,100],[255,160,240],[140,180,255],[230,120,255],[255,255,180],[255,255,255]]:
    with ioqlock:
      ioreqs.append(setColorCorrectionBytes(RGB(cc[0],cc[1],cc[2])))
    time.sleep(1.5)

  # End on high contrast
  ledqt.thlog_info("     ***  High contrast between sections  ***     ")
  # R B G R B G R B G R B 
  time.sleep(1)
  for mask in [[1,0,0]]:
    with ioqlock:
      for i in range(NUM_CHANNELS):
        ioreqs.append(setChannelBytes(i, _style=LS_ON,
                        _col1=RGB(mask[(0+i)%3]*255,
                                  mask[(1+i)%3]*255,
                                  mask[(2+i)%3]*255 )))

  ledqt.thlog_info("\n")
  ledqt.thlog_info("     ***  get FW version  ***     ")
  with ioqlock:
    ioreqs.append(getFWVersionBytes())
  time.sleep(.5)

  ledqt.thlog_info("\n")
  ledqt.thlog_info(f"  This cycle  - successful: {ledqt.total_success_responses - snap_success},  repeated/error: {ledqt.total_fail_responses - snap_fail}.")
  ledqt.thlog_info(f"  Cumulative  - successful: {ledqt.total_success_responses},  repeated/error: {ledqt.total_fail_responses}.")
  time.sleep(1)


def main():
  num_cycles = int(sys.argv[1]) if len(sys.argv) > 1 else 1
  print(f"  Running {num_cycles} cycle(s).")
  # app = QtWidgets.QApplication(sys.argv)

  # ser = connectArdSerial()

  # LEDControl, 
  ledqt = LEDControl() 

  # Threading for IO - Should be safer and easier
  SerialArdHandler_ = Thread(target=SerialArdHandler, args=(ledqt,), daemon=True)
  # pushChannelthread = Thread(target=regularPushChannel, args=(ledqt,), daemon=True)
  # updateTimingthread = Thread(target=regularTimingQuery, args=(ledqt,), daemon=True)

  SerialArdHandler_.start()
  # pushChannelthread.start()
  # updateTimingthread.start()

  # run
  # sys.exit(app.exec_())

  # connect

  time.sleep(1)
  print("  << Exit early with ctrl-C. >>  ")
  # set several different animations:
  while(not ledqt.connectedForSerialTest):
    time.sleep(.5)
  for cycle in range(num_cycles):
    if num_cycles > 1:
      ledqt.thlog_info(f"\n  === Cycle {cycle + 1} of {num_cycles} ===")
    run_test_cycle(ledqt)


### Start ###

if __name__ == "__main__":
  main()





