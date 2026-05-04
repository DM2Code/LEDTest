import serial
import time

import sys
import glob

def serial_ports():
  """ Lists serial port names
    :raises EnvironmentError:
      On unsupported or unknown platforms
    :returns:
      A list of the serial ports available on the system
  """
  if sys.platform.startswith('win'):
    ports = ['COM%s' % (i + 1) for i in range(256)]
  elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
    # this excludes your current terminal "/dev/tty"
    ports = glob.glob('/dev/tty[A-Za-z]*')
  elif sys.platform.startswith('darwin'):
    ports = glob.glob('/dev/tty.*')
  else:
    raise EnvironmentError('Unsupported platform')

  result = []
  for port in ports:
    # print(f"try: {port}")
    try:
      s = serial.Serial(port)
      s.close()
      result.append(port)
    except (OSError, serial.SerialException):
      pass
  return result

# for bytes to string, specify encoding:
# b"abcde".decode("utf-8") 

def connectArdSerial():
  print (serial_ports())
  for p in serial_ports():
    # print(1)
    try: 
      ser = serial.Serial(
          port = p,
          baudrate = 115200,
          # baudrate = 57600,
          # baudrate =  38400,
          # baudrate =  19200,
          # baudrate =   9600,
          parity = serial.PARITY_NONE,
          stopbits = serial.STOPBITS_ONE,
          bytesize = serial.EIGHTBITS,
          timeout=.500
      )

      print(ser)
      print(ser.isOpen())

      if (ser.isOpen()):
        # Validate we have the right device before returning
        time.sleep(0.5)
        for i in range(3):
          print(f"try {i} on {p}: ",end='')
          callonly(ser, packbytes(getFWVersionBytes()))
          time.sleep(0.1)
          pktid_, val_ = readandunpackbytes(ser, headout = 30)
          if val_ and b"error" not in val_.lower():
            # Got a good connection, sent a packet and received an expected response
            print(f"connected to device: <{val_}> on port: <{p}>")
            return ser
          #failed, close this and try the next one
        ser.close()
    except:
      print(f"Unable to open Serial on {p}.  Trying another port..")
      # print("error: " + traceback.format_exc())
  # TODO: clean up return here
  return "failed to open Serial connection"
  # print(ser.portstr)       # check which port was really used


def printhex(hex, header=True, contig = 4):
  if (isinstance(hex,bytes)):
    hex = hex.hex()
  length = len(hex)
  if (header):
    for i in range(len(hex)):
      if (i%contig == 0):
        print(  '{num:{fill}{align}{width}}'.
              format( num=int((i+contig)/2)-1, 
                  fill=' ', 
                  align='>', 
                  width=contig), 
            end=' ')
    print() #newline
  for i in range(len(hex)):
    if (i%contig == 0):
      print(hex[i:min(i+contig,len(hex))], end=' ')
  print() #newline

#Takes in bytes and prints bits
def printbits(bytes, header=True, perRow = 8):
  length = len(bytes)
  for i in range(len(bytes)):
    if (i%perRow == 0):
      if (i>0):
        print() #newline
      if (header):
        print(  '{num:{fill}{align}{width}}'.
              format( num=int(i), 
                  fill=' ', 
                  align='>', 
                  width=3), 
            end=' ')
    print(bin(bytes[i])[2:].zfill(8), end=' ')
  print() #newline 

def callresponse(ser, bytes):
  ser.write(bytes)
  printhex(ser.read(len(bytes)), contig=2)
  time.sleep(0.300) # debug, buffer for Serial

def printcallresponse(ser, bytes):
  printhex(bytes, contig=2)
  ser.write(bytes)
  # result = ser.read(len(bytes))
  result = readandunpackbytes(ser)
  printhex(result, contig=2)
  print(result)
  # time.sleep(0.300) # debug, buffer for Serial

def callonly(ser, bytes):
  # print(bytes)
  ser.write(bytes)
  # print(ser.read(len(bytes)))
  # time.sleep(0.300)


def packbytes(bytes_, packetid=17):
  head_   = b'\x7E'
  length_ = len(bytes_)
  pktid_  = packetid%256
  tail_   = b'\x81'

  sum_    = 0
  for b in bytes_:
    sum_ += b
  checksum_ = sum_%256
  
  packet_ = head_ + bytes([pktid_, length_]) + bytes_ + bytes([checksum_]) + tail_

  return packet_

# def readandunpackbytes(ser, packetidcheck_=False, packetid_=0, headout=255):
def readandunpackbytes(ser, headout=255):
  head_   = b'\x7E'
  tail_   = b'\x81'
  
  temp = ser.timeout
  ser.timeout=.100

  # t_ = ser.read()
  # while (t_ != head_):
    # print('.')
    # print(t_)
    # t_=ser.read()
    # pass
  bytesread=0
  b_=ser.read()
  while (b_ != head_ and bytesread<headout):
    bytesread+=1 
    if bytesread == headout:
      print(" No head byte.")
      return b'', b'<Error: no head byte found>'
    try:
      print('-',end='')
      print(b_.hex(), end='')
      # if b_:
      #   print(b_[0])
      #   print(bytes("taco").hex())
      #   b_[0]+=100
      #   print(b_.hex(), end='')
      # if b_:
        # print(hex(b_.decode('utf-8')), end='')
      # if b_ and b_[0] >= 32 and b_[0] <= 126:
        # print(b_.decode('utf-8'), end='')
      # else:
        # print(b_.hex(), end='')
    # except:
    except UnicodeDecodeError:
      print(f"Can't decode input byte: {int(b_)} ")
      # print(int(b_), end='')
    print('-' + b_.hex(), end='') # debug
    b_=ser.read()

  pktid_ = ser.read()
  if type(pktid_) is not bytes or not pktid_:
    print("Error reading pktid.")
    return b'', b'<error reading pktid>'
  # print('-p' + pktid_.hex(), end='') # debug
  # print (type(pktid_))
  # print (pktid_)
  payloadlength_ = ser.read()
  # print('-l' + payloadlength_.hex(), end='') # debug
  # print("l"+str(payloadlength_))
  sum_=0
  if payloadlength_:
    payload = ser.read( payloadlength_[0] )
    # print('-c' + payload.hex(), end='') # debug
    result = payload
    for b in payload:
      # print('-'+str(b))
      sum_ += b
    checksum_ = ser.read()
    if type(checksum_) is not bytes or not checksum_:
      print("Error reading checksum.")
      return b'', b'<error reading checksum>'
    # print(' -s' + str(checksum_[0]) + "_" + str(sum_) + "_" + str(sum_%256))
    if checksum_[0] != sum_%256:
      print(f"Error with checksum: {checksum_[0]} instead of {sum_%256}")
      result = b'<Error with checksum>'
    last_byte = ser.read()
    if last_byte != tail_:
      print(f"Error with tail: {last_byte}")
      result = b'<Error with tail>'
    # if packetidcheck_ and packetid_ != pktid_:
    #   print('Error with packet, wrong packet id vs <{packetid_}>')
    #   result = b'<packetid error>'

  ser.timeout = temp
  return pktid_, result

def unpackbytes(packetbytes_):
  head_   = b'\x7E'
  tail_   = b'\x81'

  packetlength_ = len(packetbytes_)
  if packetlength_ < 5:
    print('Error with packet:<{packetbytes_}>, too short')
    return 0, b'<short packet error>'
  if bytes_[0] != head_ or bytes_[-1] != tail_: 
    print('Error with packet:<{packetbytes_}>, wrong head/tail')
    return 0, '<head/tail error>'
  pktid_  = bytes_[1]
  # if packetidcheck_ and packetid_ != pktid_:
  #   print('Error with packet:<{packetbytes_}>, wrong packet id vs <{packetid_}>')
  #   return False, '<packetid error>'
  payloadlength_ = bytes_[2] 
  checksum_ = bytes_[-2] 
  if payloadlength_ != packetlength_-5:
    print('Error with packet:<{packetbytes_}>, wrong payload length')
    return pktid_, '<length error>'

  sum_    = 0
  for b in bytes_[3:-2]:
    sum_ += b
  if sum_%256 != checksum_:
    print('Error with packet:<{packetbytes_}>, wrong checksum')
    return pktid_, '<CRC error>'
  
  return pktid_, packetbytes_[3:-2]

MODE_BYTE_SIZE = 23

LS_OFF       = 0    # Off
LS_ON        = 1    # On, single color
LS_BLINK     = 2    # On, single color, for X time, Off or On second color for Y time
LS_FLARE     = 3    # 
LS_CHASE     = 4    # 
LS_CYLON     = 5    # TODO: like chase but back and forth?
LS_GROW      = 6    # 
LS_INWARDS   = 7    # 
LS_OUTWARDS  = 8    # 
LS_STROBE    = 9    # Flash X times each for timeA, wait for timeB, repeat
LS_HEARTBEAT = 10   # TODO: fade or chase but with custom brightness curve
LS_WALL      = 11   # 
LS_RAINBOW   = 12   # 
LS_FADE      = 13   # Gradual transition col1->col2. X time for transition 1->2, Y time waiting at 2, W time back to col2, Z time waiting at col1.
                    # TODO:  FADE with HSV Similar to RGB, probably looks better, using Hue.

# Stated modes: (uses loopcnt + state variables)
LS_FLAME     = 14   # Emits temperature-colored 
LS_BOUNDING  = 15   # 
LS_TWINKLE   = 16   # 
LS_SPARKLE   = 17   # 
LS_METEOR    = 18   # Much like Chase, but has some pixels carry persistent extra brightness (which burns out)

MAX_LS_MODE  = LS_METEOR

SPC_READVERBOSESTATE   = 247
SPC_LOADEEPROM         = 248
SPC_STOREEEPROM        = 249
SPC_DEBUGTIMING        = 250
SPC_UPDATEPENDING      = 251
SPC_CORRECTTEMPERATURE = 252
SPC_CORRECTCOLOR       = 253
SPC_GETFWVER           = 254
SPC_READSTATE          = 255

# NUM_CHANNELS           = 11

class RGB():
  def __init__(self, r, g, b):
    self.r=r
    self.g=g
    self.b=b
 
  def __add__(self, o): 
    return RGB(max(self.r + o.r,255), max(self.g + o.g,255), max(self.b + o.b,255))

  def __sub__(self, o): 
    return RGB(min(self.r - o.r,0), min(self.g - o.g,0), min(self.b - o.b,0))

  def __eq__(self, o): 
    return self.r == o.r and self.g == o.g and self.b == o.b 


def getflags(_maintainTimestep, _forwardHue, _forwardSpace, _gamma, _holdUpdate, _dither, _HSVassign, _HSVtrans):
  _flags = 0
  if _maintainTimestep:
    _flags |= 0b10000000
  if not _forwardHue:
    _flags |= 0b01000000
  if not _forwardSpace:
    _flags |= 0b00100000
  if _gamma:
    _flags |= 0b00010000
  if _holdUpdate:
    _flags |= 0b00001000
  if not _dither:
    _flags |= 0b00000100
  if _HSVassign:
    _flags |= 0b00000010
  if _HSVtrans:
    _flags |= 0b00000001
  return _flags

def loadFlashBytes():
  return bytes([0, SPC_LOADEEPROM])

def saveFlashBytes():
  return bytes([0, SPC_STOREEEPROM])

def getUpdatePendingBytes():
  return bytes([0, SPC_UPDATEPENDING])

def getDebugTimingBytes():
  return bytes([0, SPC_DEBUGTIMING])

def setBrightnessBytes(_bright=255):
  return setColorCorrection(RGB(_bright,_bright,_bright))

def setTemperatureCorrectionBytes(_bright=255, _kel=5500):
  return bytes([0, SPC_CORRECTTEMPERATURE, _bright, int(_kel/256), _kel%256 ])

def setColorCorrectionBytes(_col=RGB(255,255,255)):
  return bytes([0, SPC_CORRECTCOLOR, _col.r, _col.g, _col.b ])

def getFWVersionBytes():
  return bytes([0, SPC_GETFWVER])

def getVerboseChannelInfoBytes(_ci):
  return bytes([_ci, SPC_READVERBOSESTATE])

def getChannelInfoBytes(_ci):
  return bytes([_ci, SPC_READSTATE])

  #             //  0 ci  1 LS    r1    g1  4 b1    r2    g2    b2   
  # byte cmd[23] = {0x00, 0x00, 0x40, 0x00, 0x00, 0x00, 0x00, 0x00, 
  #             //  8tAh   tAl   tBh   tBl 12tOfh tOfl  tABh  tABl
  #                 0x07, 0xD0, 0x07, 0xD0, 0x00, 0x00, 0x00, 0x32, 
  #             // 6tBAh  tBAl   szh   szl  spfh  spfl   flg  
  #                 0x00, 0x32, 0x00, 0x20, 0x00, 0x00, 0x00 };
def setChannelBytes_f(_ci, _style=LS_ON, _col1=RGB(30,0,0), _col2=RGB(0,0,12), _size=32, _spoffset=0, _flags=0, 
                    _timeA=1000, _timeB=1000, _timeOffset=0, _timeABpause=50, _timeBApause=50):
  return bytes([_ci, _style, _col1.r, _col1.g, _col1.b, _col2.r, _col2.g, _col2.b, 
                int(_timeA/256), _timeA%256, int(_timeB/256), _timeB%256, 
                    int(_timeOffset/256), _timeOffset%256, int(_timeABpause/256), _timeABpause%256, 
                int(_timeBApause/256), _timeBApause%256, int(_size/256), _size%256, 
                    int(_spoffset/256), _spoffset%256, _flags])

def setChannelBytes(_ci, _style=LS_ON, _col1=RGB(30,0,0), _col2=RGB(0,0,12), _size=32, _spoffset=0, #_flags=0, 
              _maintainTimestep=True, _forwardHue=True, _forwardSpace=True, _gamma=False, 
              _holdUpdate=False, _dither=False, _HSVassign=False, _HSVtrans=False,
              _timeA=1000, _timeB=1000, _timeOffset=0, _timeABpause=50, _timeBApause=50):
  _flags = getflags(_maintainTimestep=_maintainTimestep, _forwardHue=_forwardHue, 
                    _forwardSpace=_forwardSpace, _gamma=_gamma, 
                    _holdUpdate=_holdUpdate, _dither=_dither, 
                    _HSVassign=_HSVassign, _HSVtrans=_HSVtrans)
  return bytes([_ci, _style, _col1.r, _col1.g, _col1.b, _col2.r, _col2.g, _col2.b, 
                int(_timeA/256), _timeA%256, int(_timeB/256), _timeB%256, 
                    int(_timeOffset/256), _timeOffset%256, int(_timeABpause/256), _timeABpause%256, 
                int(_timeBApause/256), _timeBApause%256, int(_size/256), _size%256, 
                    int(_spoffset/256), _spoffset%256, _flags])

def setChannelBytesOFF(_ci):
  return bytes([_ci, LS_OFF])  

def setChannelBytesON(_ci, _col1=RGB(30,0,0)):
  return bytes([_ci, LS_ON, _col1.r, _col1.g, _col1.b])  

def setChannelBytesBLINK(_ci, _col1=RGB(30,0,0), _col2=RGB(0,0,0), _flags=0, 
              _timeA=1000, _timeB=1000, _timeOffset=0):
  # for ob in [_ci, LS_BLINK, _col1.r, _col1.g, _col1.b, _col2.r, _col2.g, _col2.b, 0, _flags, 
  #               int(_timeA/256), _timeA%256, int(_timeB/256), _timeB%256, int(_timeOffset/256), _timeOffset%256]:
  #   print(f"{ob}:{type(ob)}\n")
  # if _timeB == -1: #temp.. cut short:
    # return bytes([_ci, LS_FADE, _col1.r, _col1.g, _col1.b, _col2.r, _col2.g, _col2.b, 
                  # int(_timeA/256), _timeA%256])
    # _timeB = _timeA

  return bytes([_ci, LS_BLINK, _col1.r, _col1.g, _col1.b, _col2.r, _col2.g, _col2.b, 
                int(_timeA/256), _timeA%256, int(_timeB/256), _timeB%256, int(_timeOffset/256), _timeOffset%256])
                # 0, _flags])  

def setChannelBytesFADE(_ci, _col1=RGB(20,0,0), _col2=RGB(0,0,12), 
              _maintainTimestep=False, _forwardSpace=True, _gamma=False, _holdUpdate=True,    # _flags=0, 
              _forwardHue=True, _dither=True, _HSVassign=True, _HSVtrans=True,
              _timeA=1000, _timeB=1000, _timeOffset=0, _timeABpause=50, _timeBApause=50):
  _flags = getflags(_maintainTimestep=_maintainTimestep, _forwardHue=_forwardHue, 
                    _forwardSpace=_forwardSpace, _gamma=_gamma, 
                    _holdUpdate=_holdUpdate, _dither=_dither, 
                    _HSVassign=_HSVassign, _HSVtrans=_HSVtrans)

  # if _timeB == -1: #temp.. cut short:
    # return bytes([_ci, LS_FADE, _col1.r, _col1.g, _col1.b, _col2.r, _col2.g, _col2.b, 
                  # int(_timeA/256), _timeA%256])
    # _timeB = _timeA

  return bytes([_ci, LS_FADE, _col1.r, _col1.g, _col1.b, _col2.r, _col2.g, _col2.b, 
                int(_timeA/256), _timeA%256, int(_timeB/256), _timeB%256, int(_timeOffset/256), _timeOffset%256, 
                int(_timeABpause/256), _timeABpause%256, int(_timeBApause/256), _timeBApause%256,
                int(_size/256), _size%256, int(_spoffset/256), _spoffset%256, _flags])  

def setChannelBytesCHASE(_ci, _col1=RGB(20,0,0), _col2=RGB(0,0,12), 
              _maintainTimestep=False, _forwardSpace=True, _gamma=False, _holdUpdate=True,    # _flags=0, 
              _forwardHue=True, _dither=True, _HSVassign=True, _HSVtrans=True,
              _timeA=1000, _timeB=1000, _timeOffset=0, _timeABpause=50, _timeBApause=50,
              _size=100, _spoffset=0):
  _flags = getflags(_maintainTimestep=_maintainTimestep, _forwardHue=_forwardHue, 
                    _forwardSpace=_forwardSpace, _gamma=_gamma, 
                    _holdUpdate=_holdUpdate, _dither=_dither, 
                    _HSVassign=_HSVassign, _HSVtrans=_HSVtrans)

  return bytes([_ci, LS_CHASE, _col1.r, _col1.g, _col1.b, _col2.r, _col2.g, _col2.b, 
                int(_timeA/256), _timeA%256, int(_timeB/256), _timeB%256, int(_timeOffset/256), _timeOffset%256, 
                int(_timeABpause/256), _timeABpause%256, int(_timeBApause/256), _timeBApause%256,
                int(_size/256), _size%256, int(_spoffset/256), _spoffset%256, _flags])  

def setChannelBytesRAINBOW(_ci, _val=200, _sat=255,  # _col1=RGB(20,0,0), _col2=RGB(0,0,12), 
              _maintainTimestep=False, _forwardHue=True, _forwardSpace=True, _gamma=False, 
              _holdUpdate=True, _dither=True, _HSVassign=True, _HSVtrans=True,
              _timeA=1000, _timeB=1000, _timeOffset=0, _timeABpause=50, _timeBApause=50, _size=32):
  _flags = getflags(_maintainTimestep=_maintainTimestep, _forwardHue=_forwardHue, 
                    _forwardSpace=_forwardSpace, _gamma=_gamma, 
                    _holdUpdate=_holdUpdate, _dither=_dither, 
                    _HSVassign=_HSVassign, _HSVtrans=_HSVtrans)

  return bytes([_ci, LS_RAINBOW, _val, _sat, 0, 0, 0, 0, 
                int(_timeA/256), _timeA%256, int(_timeB/256), _timeB%256, int(_timeOffset/256), _timeOffset%256, 
                int(_timeABpause/256), _timeABpause%256, int(_timeBApause/256), _timeBApause%256,
                int(_size/256), _size%256, 0, 0, _flags])

# void setChannel_RAINBOW(int _ci, CRGB _col1, int _timeA, CRGB _col2, int _timeB, int _timeOffset=0, int _size=32)
# { setChannel(_ci, LS_RAINBOW, _col1, _timeA, _col2, _timeB, _timeOffset, _size); 
# }


# cmd     0x7E 00 0A 05 02 0C 00 00 00 00 00 03 20 36 81
# rsp ‘K’ 0x7E 00 01 4B 4B 81





