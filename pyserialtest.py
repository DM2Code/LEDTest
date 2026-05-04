import serial
import time

# import ecoRGBinterface
# print(ecoRGBinterface)
# print(ecoRGBinterface.RGB)
# print(ecoRGBinterface.RGB(10,0,1).r)
# print(ecoRGBinterface.RGB(10,0,1).g)
# print(ecoRGBinterface.RGB(10,0,1).b)

from ecoRGBinterface import *
print()
print(RGB)
print(RGB(10,0,1).r)
print(RGB(10,0,1).g)
print(RGB(10,0,1).b)
print(5)

# ser = serial.Serial(0)  # open first serial port

# ser = serial.Serial(
#     port='/dev/ttyACM0',
#     baudrate=9600,
#     parity=serial.PARITY_ODD,
#     # stopbits=serial.STOPBITS_TWO,
#     # bytesize=serial.SEVENBITS,
# )

for p in ['/dev/ttyACM0', '/dev/ttyACM1']:
  ser = serial.Serial(
      port = p,
      baudrate = 115200,
      # baudrate = 9600,
      parity = serial.PARITY_NONE,
      stopbits = serial.STOPBITS_ONE,
      bytesize = serial.EIGHTBITS,
      timeout=2.000
  )

  print(ser.isOpen())

  if (ser.isOpen()):
    break

print(ser.portstr)       # check which port was really used
# ser.write(b'\xFE')
# b0 = ser.read() # read one byte
# ser.write(b'ABCED')
# b5l = ser.read(5) #read 5 bytes (timeout)
# ser.write(b'ABCEDSDAFS\n')
# bn = ser.readline() #read till \n


# for i in range(10):
  # ser.write(b'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abcdefghijklmnopqrstuvwxyz\n')
  # print(ser.readline())
  
def flushserial():
  temp = ser.timeout=2.000
  ser.timeout=.100
  line='temp'
  while line:
    line = ser.readline()
    print(line)
  ser.timeout = temp

# hex is either string in ascii representing hex value: "deadbeef" "004BC" etc.
# or of type bytes

def test_(bytes):
  flushserial()             # good to flush if there's a lot of serial debug output
  # printhex(bytes, contig=2)   # print out the command
  # callonly(ser, bytes)           # Execute command
  # callresponse(ser, bytes)   # Execute command and print the response
  printcallresponse(ser, bytes)  # print command, execute, and print the response
  flushserial()             # good to flush if there's a lot of serial debug output
  time.sleep(0.250)


callresponse(ser, packbytes(getFWVersionBytes())) # initial serial byte IO hangs on arduino, just flush it

test_(packbytes(getFWVersionBytes()))
# test_(packbytes(getFWVersionBytes()))
test_(packbytes(getChannelInfoBytes(3)))
# test_(packbytes(getFWVersionBytes()))
# exit()
# test_(packbytes(setColorCorrectionBytes(RGB(255,147,41)))) #0xFF9329
test_(packbytes(setColorCorrectionBytes(RGB(255,100,170))))
# test_(packbytes(setColorCorrectionBytes(RGB(255,255,255))))
# flushserial()

# print("setChannelBytesBLINK(   _ci=5,_col1=RGB(12,0,0),_timeA=800):")
# test_(packbytes(setChannelBytesBLINK(   _ci=5,_col1=RGB(12,0,0),_timeA=800)))

# print("setChannelBytesBLINK(   _ci=4,_col1=RGB(12,0,0),_col2=RGB(0,80,0),_timeA=1000,_timeB=600, _timeOffset=200):")
# test_(packbytes(setChannelBytesBLINK(   _ci=4,_col1=RGB(12,0,0),_col2=RGB(0,80,0),_timeA=1000,_timeB=600, _timeOffset=200)))
# flushserial()

# print("setChannelBytesFADE(    _ci=1,_col1=RGB(0,0,150),_col2=RGB(0,20,0),_timeA=1500,_timeB=2500, _timeOffset=200, _timeABpause=1000, _timeBApause=1200):")
# test_(packbytes(setChannelBytesFADE(    _ci=1,_col1=RGB(0,0,150),_col2=RGB(0,20,0),_timeA=1500,_timeB=2500, _timeOffset=200, _timeABpause=1000, _timeBApause=1200)))

# print("setChannelBytesFADE(    _ci=1,_col1=RGB(0,0,150),_col2=RGB(100,0,0),_timeA=1500):")
# test_(packbytes(setChannelBytesFADE(    _ci=1,_col1=RGB(0,0,150),_col2=RGB(100,0,0),_timeA=1500)))
# flushserial()

# test_(packbytes(setChannelBytesON(      _ci=2,_col1=RGB(255,255,255))))
# test_(packbytes(setChannelBytesON(      _ci=3,_col1=RGB(255,255,255))))
# test_(packbytes(setChannelBytesON(      _ci=4,_col1=RGB(255,255,255))))
# flushserial()

# test_(packbytes(setColorCorrectionBytes(RGB(255,160,240))))
# test_(packbytes(setColorCorrectionBytes(RGB(16,16,16))))
# test_(packbytes(setColorCorrectionBytes(RGB(255,255,255))))
# test_(packbytes(getFWVersionBytes()))
# test_(packbytes(getChannelInfoBytes(3)))
# test_(packbytes(setTemperatureCorrectionBytes(_bright=100, _kel=5500)))
# # time.sleep(1)
# test_(packbytes(setTemperatureCorrectionBytes(_bright=50, _kel=5500)))
# # time.sleep(1)
# test_(packbytes(setTemperatureCorrectionBytes(_bright=25, _kel=5500)))
# # time.sleep(1)
# test_(packbytes(setTemperatureCorrectionBytes(_bright=100, _kel=15000)))
# # time.sleep(1)
# test_(packbytes(setTemperatureCorrectionBytes(_bright=50, _kel=15000)))
# # time.sleep(1)
# test_(packbytes(setTemperatureCorrectionBytes(_bright=25, _kel=15000)))
# # time.sleep(1)
# test_(packbytes(setTemperatureCorrectionBytes(_bright=100, _kel=2500)))
# # time.sleep(1)
# test_(packbytes(setTemperatureCorrectionBytes(_bright=50, _kel=2500)))
# # time.sleep(1)
# test_(packbytes(setTemperatureCorrectionBytes(_bright=25, _kel=2500)))
# flushserial()
# # time.sleep(1)
# test_(packbytes(setBrightnessBytes(_bright=100)))
# # time.sleep(1)
# test_(packbytes(setBrightnessBytes(_bright=50)))
# # time.sleep(1)
# test_(packbytes(setBrightnessBytes(_bright=25)))
# # time.sleep(1)
# test_(packbytes(setTemperatureCorrectionBytes(_bright=100, _kel=6500)))
# # time.sleep(1)
# test_(packbytes(setBrightnessBytes(_bright=100)))
# # time.sleep(1)
# test_(packbytes(setBrightnessBytes(_bright=50)))
# # time.sleep(1)
# test_(packbytes(setBrightnessBytes(_bright=25)))
# # time.sleep(1)
# # exit()
# flushserial()


# test_(packbytes(setChannelBytesOFF(  0)))
# print(ser.readline())
# test_(packbytes(setChannelBytesOFF(  1)))
# test_(packbytes(setChannelBytesON(      _ci=1,_col1=RGB(12,0,0))))
# test_(packbytes(getDebugTimingBytes()))
# test_(packbytes(setChannelBytesFADE(    _ci=0,_col1=RGB(104,104,104),_col2=RGB(50,50,50),_timeA=2000,_timeB=2000, _timeOffset=0000, _maintainTimestep=True, _gamma=True, _HSV=False, _dither=True, _forwardHue=True)))
# # time.sleep(.350)
# test_(packbytes(setChannelBytesFADE(    _ci=1,_col1=RGB(181,0,0),_col2=RGB(50,0,0),_timeA=2000,_timeB=2000, _timeOffset=0000, _maintainTimestep=True, _gamma=True, _HSV=False, _dither=True, _forwardHue=True)))
# # time.sleep(.350)
# test_(packbytes(setChannelBytesFADE(    _ci=2,_col1=RGB(0,181,0),_col2=RGB(0,50,0),_timeA=2000,_timeB=2000, _timeOffset=1000, _maintainTimestep=True, _gamma=True, _HSV=False, _dither=True, _forwardHue=True)))
# # time.sleep(.650)
# test_(packbytes(setChannelBytesFADE(    _ci=3,_col1=RGB(0,0,181),_col2=RGB(0,0,50),_timeA=2000,_timeB=2000, _timeOffset=2000, _maintainTimestep=True, _gamma=True, _HSV=False, _dither=True, _forwardHue=True)))
# # time.sleep(.650)
test_(packbytes(getDebugTimingBytes()))

# Test sync animation:
# test_(packbytes(setChannelBytesFADE(    _ci=3,_col1=RGB(0,0,50),_col2=RGB(0,0,5),_timeA=1500,_timeB=1500, _timeOffset=000, _maintainTimestep=True, _HSV=False, _dither=True, _forwardHue=True)))
# time.sleep(.650)
# test_(packbytes(setChannelBytesFADE(    _ci=3,_col1=RGB(0,0,50),_col2=RGB(0,0,5),_timeA=1500,_timeB=1500, _timeOffset=000, _maintainTimestep=True, _HSV=False, _dither=True, _forwardHue=True)))
# time.sleep(.850)
# test_(packbytes(setChannelBytesFADE(    _ci=3,_col1=RGB(0,50,0),_col2=RGB(0,0,5),_timeA=1500,_timeB=1500, _timeOffset=000, _maintainTimestep=True, _HSV=False, _dither=True, _forwardHue=True)))
# time.sleep(.850)
# test_(packbytes(setChannelBytesFADE(    _ci=3,_col1=RGB(50,0,0),_col2=RGB(0,0,5),_timeA=1500,_timeB=1500, _timeOffset=000, _maintainTimestep=True, _HSV=False, _dither=True, _forwardHue=True)))
# time.sleep(.850)
# test_(packbytes(setChannelBytesFADE(    _ci=3,_col1=RGB(50,0,0),_col2=RGB(0,0,5),_timeA=1500,_timeB=1500, _timeOffset=000, _maintainTimestep=True, _HSV=False, _dither=True, _forwardHue=True)))
# time.sleep(.850)
# test_(packbytes(setChannelBytesFADE(    _ci=3,_col1=RGB(0,50,0),_col2=RGB(0,0,5),_timeA=1500,_timeB=1500, _timeOffset=000, _maintainTimestep=True, _HSV=False, _dither=True, _forwardHue=True)))
# time.sleep(.850)
# test_(packbytes(setChannelBytesFADE(    _ci=3,_col1=RGB(0,0,50),_col2=RGB(0,0,5),_timeA=1500,_timeB=1500, _timeOffset=000, _maintainTimestep=True, _HSV=False, _dither=True, _forwardHue=True)))
# time.sleep(.850)
# test_(packbytes(setChannelBytesFADE(    _ci=4,_col1=RGB(50,50,50),_col2=RGB(5,5,5),_timeA=300,_timeB=300, _timeOffset=0000, _timeABpause=1200, _timeBApause=1200, _maintainTimestep=True, _gamma=False, _HSV=False, _dither=True, _forwardHue=True)))
# # time.sleep(.300)
# test_(packbytes(setChannelBytesFADE(    _ci=5,_col1=RGB(150,0,0),_col2=RGB(5,0,0),_timeA=300,_timeB=300, _timeOffset=0000, _timeABpause=1200, _timeBApause=1200, _maintainTimestep=True, _gamma=False, _HSV=False, _dither=True, _forwardHue=True)))
# # time.sleep(.150)
# test_(packbytes(setChannelBytesFADE(    _ci=6,_col1=RGB(0,150,0),_col2=RGB(0,5,0),_timeA=300,_timeB=300, _timeOffset=1000, _timeABpause=1200, _timeBApause=1200, _maintainTimestep=True, _gamma=False, _HSV=False, _dither=True, _forwardHue=True)))
# # time.sleep(.150)
# test_(packbytes(setChannelBytesFADE(    _ci=7,_col1=RGB(0,0,150),_col2=RGB(0,0,5),_timeA=300,_timeB=300, _timeOffset=2000, _timeABpause=1200, _timeBApause=1200, _maintainTimestep=True, _gamma=False, _HSV=False, _dither=True, _forwardHue=True)))
# # time.sleep(.650)
# flushserial()
# test_(packbytes(setChannelBytesFADE(    _ci=4,_col1=RGB(50,50,50),_col2=RGB(5,5,5),_timeA=2000,_timeB=2000, _timeOffset=0000, _timeABpause=200, _timeBApause=200, _maintainTimestep=True, _gamma=True, _HSV=True, _dither=True, _forwardHue=True)))
# # time.sleep(.300)
# test_(packbytes(setChannelBytesFADE(    _ci=5,_col1=RGB(150,0,0),_col2=RGB(5,0,0),_timeA=2000,_timeB=2000, _timeOffset=0000, _timeABpause=200, _timeBApause=200, _maintainTimestep=True, _gamma=True, _HSV=True, _dither=True, _forwardHue=True)))
# # time.sleep(.150)
# test_(packbytes(setChannelBytesFADE(    _ci=6,_col1=RGB(0,150,0),_col2=RGB(0,5,0),_timeA=2000,_timeB=2000, _timeOffset=1000, _timeABpause=200, _timeBApause=200, _maintainTimestep=True, _gamma=True, _HSV=True, _dither=True, _forwardHue=True)))
# # time.sleep(.150)
# test_(packbytes(setChannelBytesFADE(    _ci=7,_col1=RGB(0,0,150),_col2=RGB(0,0,5),_timeA=2000,_timeB=2000, _timeOffset=2000, _timeABpause=200, _timeBApause=200, _maintainTimestep=True, _gamma=True, _HSV=True, _dither=True, _forwardHue=True)))
# time.sleep(.650)

# test_(packbytes(setChannelBytesFADE(    _ci=1,_col1=RGB(180,180,180),_col2=RGB(80,80,80),_timeA=3000,_timeB=3000, _HSV=False, _dither=True, _forwardHue=True)))
# test_(packbytes(setChannelBytesON(      _ci=2,_col1=RGB(0,12,0))))
# test_(packbytes(setChannelBytesFADE(    _ci=2,_col1=RGB(80,80,80),_col2=RGB(10,10,10),_timeA=3000,_timeB=3000, _HSV=False, _dither=True, _forwardHue=True)))
# test_(packbytes(setChannelBytesON(      _ci=3,_col1=RGB(0,0,12))))
# test_(packbytes(setChannelBytesON(      _ci=3,_col1=RGB(20,20,20))))
# test_(packbytes(setChannelBytesBLINK(   _ci=4,_col1=RGB(12,0,0),_col2=RGB(0,0,12),_timeA=1500)))
# test_(packbytes(setChannelBytesBLINK(   _ci=5,_col1=RGB(0,10,9),_col2=RGB(9,9,0),_timeA=1500)))
# flushserial()
# test_(packbytes(setChannelBytesFADE(    _ci=6,_col1=RGB(80,80,0),_col2=RGB(20,20,20),_timeA=3000,_timeB=3000, _HSV=True, _dither=True, _forwardHue=True)))
# test_(packbytes(setChannelBytesFADE(    _ci=7,_col1=RGB(80,80,0),_col2=RGB(20,20,20),_timeA=3000,_timeB=3000, _HSV=True, _dither=True, _forwardHue=False)))
# test_(packbytes(setChannelBytesFADE(    _ci=8,_col1=RGB(80,80,0),_col2=RGB(20,20,20),_timeA=3000,_timeB=3000, _HSV=False, _dither=True, _forwardHue=True)))
# test_(packbytes(setChannelBytesFADE(    _ci=9,_col1=RGB(80,80,0),_col2=RGB(20,20,20),_timeA=3000,_timeB=3000, _HSV=False, _dither=True, _forwardHue=False)))
# flushserial()
# # test_(packbytes(setChannelBytesOFF(  0)))
# test_(packbytes(setChannelBytesON(      _ci=10,_col1=RGB(0,9,0))))
# test_(packbytes(setChannelBytesRAINBOW( _ci=0,_forwardHue=True, _forwardSpace=True, _dither=True, _timeA=3000)))
# test_(packbytes(setChannelBytesRAINBOW( _ci=1,_forwardHue=True, _forwardSpace=False, _dither=True, _timeA=3000)))
# test_(packbytes(setChannelBytesRAINBOW( _ci=2,_forwardHue=False, _forwardSpace=True, _dither=True, _timeA=3000)))
# test_(packbytes(setChannelBytesRAINBOW( _ci=3,_forwardHue=False, _forwardSpace=False, _dither=True, _timeA=3000)))

# test_(packbytes(setColorCorrectionBytes(RGB(255,10,10))))
# # time.sleep(1)
# test_(packbytes(setColorCorrectionBytes(RGB(10,255,10))))
# # time.sleep(1)
# test_(packbytes(setColorCorrectionBytes(RGB(10,10,255))))
# # time.sleep(1)
# test_(packbytes(setColorCorrectionBytes(RGB(255,160,240))))
# # time.sleep(1)
# test_(packbytes(setColorCorrectionBytes(RGB(16,16,16))))
# # time.sleep(1)
# test_(packbytes(setColorCorrectionBytes(RGB(255,255,255))))
# # time.sleep(1)
# test_(packbytes(setColorCorrectionBytes(RGB(255,147,41)))) #0xFF9329
# time.sleep(1)

# test_(packbytes(setColorCorrectionBytes(RGB(255,255,255))))

# time.sleep(1)

# test_(packbytes(setChannelBytesFADE(    _ci=0,_col1=RGB(50,50,50),_col2=RGB(5,5,5),_timeA=1500,_timeB=1500, _maintainTimestep=True, _HSV=False, _dither=True, _forwardHue=True)))
# test_(packbytes(setChannelBytesFADE(    _ci=1,_col1=RGB(50,0,0),_col2=RGB(5,0,0),_timeA=1500,_timeB=1500, _timeOffset=000, _maintainTimestep=True, _HSV=False, _dither=True, _forwardHue=True)))
# test_(packbytes(setChannelBytesFADE(    _ci=2,_col1=RGB(0,50,0),_col2=RGB(0,5,0),_timeA=1500,_timeB=1500, _timeOffset=1000, _maintainTimestep=True, _HSV=False, _dither=True, _forwardHue=True)))
# test_(packbytes(setChannelBytesFADE(    _ci=3,_col1=RGB(0,0,50),_col2=RGB(0,0,5),_timeA=1500,_timeB=1500, _timeOffset=2000, _maintainTimestep=True, _HSV=False, _dither=True, _forwardHue=True)))
# time.sleep(1)

# test_(packbytes(setChannelBytesFADE(    _ci=0,_col1=RGB(50,50,50),_col2=RGB(5,5,5),_timeA=1500,_timeB=1500, _maintainTimestep=False, _HSV=False, _dither=True, _forwardHue=True)))
# test_(packbytes(setChannelBytesFADE(    _ci=1,_col1=RGB(50,0,0),_col2=RGB(5,0,0),_timeA=1500,_timeB=1500, _timeOffset=000, _maintainTimestep=False, _HSV=False, _dither=True, _forwardHue=True)))
# test_(packbytes(setChannelBytesFADE(    _ci=2,_col1=RGB(0,50,0),_col2=RGB(0,5,0),_timeA=1500,_timeB=1500, _timeOffset=1000, _maintainTimestep=False, _HSV=False, _dither=True, _forwardHue=True)))
# test_(packbytes(setChannelBytesFADE(    _ci=3,_col1=RGB(0,0,50),_col2=RGB(0,0,5),_timeA=1500,_timeB=1500, _timeOffset=2000, _maintainTimestep=False, _HSV=False, _dither=True, _forwardHue=True)))
# time.sleep(1)

# test_(packbytes(setChannelBytesFADE(    _ci=0,_col1=RGB(50,50,50),_col2=RGB(5,5,5),_timeA=1500,_timeB=1500, _maintainTimestep=False, _HSV=False, _dither=True, _forwardHue=True)))
# test_(packbytes(setChannelBytesFADE(    _ci=1,_col1=RGB(50,0,0),_col2=RGB(5,0,0),_timeA=1500,_timeB=1500, _timeOffset=000, _maintainTimestep=False, _HSV=False, _dither=True, _forwardHue=True)))
# test_(packbytes(setChannelBytesFADE(    _ci=2,_col1=RGB(0,50,0),_col2=RGB(0,5,0),_timeA=1500,_timeB=1500, _timeOffset=1000, _maintainTimestep=False, _HSV=False, _dither=True, _forwardHue=True)))
# test_(packbytes(setChannelBytesFADE(    _ci=3,_col1=RGB(0,0,50),_col2=RGB(0,0,5),_timeA=1500,_timeB=1500, _timeOffset=2000, _maintainTimestep=False, _HSV=False, _dither=True, _forwardHue=True)))
# time.sleep(1)

# test_(packbytes(setChannelBytesFADE(    _ci=0,_col1=RGB(50,50,50),_col2=RGB(5,5,5),_timeA=1500,_timeB=1500, _maintainTimestep=True, _HSV=False, _dither=True, _forwardHue=True)))
# test_(packbytes(setChannelBytesFADE(    _ci=1,_col1=RGB(50,0,0),_col2=RGB(5,0,0),_timeA=1500,_timeB=1500, _timeOffset=000, _maintainTimestep=True, _HSV=False, _dither=True, _forwardHue=True)))
# test_(packbytes(setChannelBytesFADE(    _ci=2,_col1=RGB(0,50,0),_col2=RGB(0,5,0),_timeA=1500,_timeB=1500, _timeOffset=1000, _maintainTimestep=True, _HSV=False, _dither=True, _forwardHue=True)))
# test_(packbytes(setChannelBytesFADE(    _ci=3,_col1=RGB(0,0,50),_col2=RGB(0,0,5),_timeA=1500,_timeB=1500, _timeOffset=2000, _maintainTimestep=True, _HSV=False, _dither=True, _forwardHue=True)))
# time.sleep(1)

# test_(packbytes(setChannelBytesFADE(    _ci=0,_col1=RGB(50,50,50),_col2=RGB(5,5,5),_timeA=1500,_timeB=1500, _maintainTimestep=True, _HSV=False, _dither=True, _forwardHue=True)))
# test_(packbytes(setChannelBytesFADE(    _ci=1,_col1=RGB(50,0,0),_col2=RGB(5,0,0),_timeA=1500,_timeB=1500, _timeOffset=000, _maintainTimestep=True, _HSV=False, _dither=True, _forwardHue=True)))
# test_(packbytes(setChannelBytesFADE(    _ci=2,_col1=RGB(0,50,0),_col2=RGB(0,5,0),_timeA=1500,_timeB=1500, _timeOffset=1000, _maintainTimestep=True, _HSV=False, _dither=True, _forwardHue=True)))
# test_(packbytes(setChannelBytesFADE(    _ci=3,_col1=RGB(0,0,50),_col2=RGB(0,0,5),_timeA=1500,_timeB=1500, _timeOffset=2000, _maintainTimestep=True, _HSV=False, _dither=True, _forwardHue=True)))
# time.sleep(1)


# while (1):
#   for c in ['r','g','b']:
#     for i in [1,2,3,4,5,6,7,8]:
#       test_(packbytes(setChannelBytesON(      _ci=10,_col1=RGB(i,0,0)))) # R on at 2 (barely)
#       time.sleep(.3)
#     for i in [1,2,3,4,5,6,7,8]:
#       test_(packbytes(setChannelBytesON(      _ci=10,_col1=RGB(0,i,0)))) # G on at 2 (more significantly)
#       time.sleep(.3)
#     for i in [1,2,3,4,5,6,7,8]:
#       test_(packbytes(setChannelBytesON(      _ci=10,_col1=RGB(0,0,i)))) # B on at 2 (barely)
#       time.sleep(.3)


while (1):
  test_(packbytes(getChannelInfoBytes(3)))
  time.sleep(2)
  test_(packbytes(setChannelBytesRAINBOW(    _ci=1,_val=50,_sat=200,_timeA=3000, _size=32, _timeOffset=0000, _maintainTimestep=True, _gamma=False, _dither=True, _forwardHue=True)))
  time.sleep(3)
  test_(packbytes(getChannelInfoBytes(1)))
  time.sleep(2)
  test_(packbytes(setChannelBytesRAINBOW(    _ci=1,_val=200,_sat=200,_timeA=300, _size=32, _timeOffset=0000, _maintainTimestep=True, _gamma=False, _dither=True, _forwardHue=True)))
  time.sleep(3)
  test_(packbytes(getChannelInfoBytes(1)))
  time.sleep(2)
  # test_(packbytes(setChannelBytesFADE(    _ci=10,_col1=RGB(50,0,0),_col2=RGB(0,0,0),_timeA=3000,_timeB=3000, _timeOffset=0000, _maintainTimestep=True, _gamma=True, _HSV=False, _dither=True, _forwardHue=True)))
  # time.sleep(5)
  # test_(packbytes(getDebugTimingBytes()))
  # test_(packbytes(setChannelBytesFADE(    _ci=10,_col1=RGB(0,50,0),_col2=RGB(0,0,0),_timeA=3000,_timeB=3000, _timeOffset=0000, _maintainTimestep=True, _gamma=True, _HSV=False, _dither=True, _forwardHue=True)))
  # time.sleep(5)
  # test_(packbytes(setChannelBytesFADE(    _ci=10,_col1=RGB(0,0,50),_col2=RGB(0,0,0),_timeA=3000,_timeB=3000, _timeOffset=0000, _maintainTimestep=True, _gamma=True, _HSV=False, _dither=True, _forwardHue=True)))
  # time.sleep(5)
  # test_(packbytes(getDebugTimingBytes()))

while (ser.isOpen()):
  test_(packbytes(getDebugTimingBytes()))
  print(ser.readline())

# ser.write("hello")      # write a string
ser.close()             # close port

