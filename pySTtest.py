import time
from pySerialTransfer import pySerialTransfer as txfer

link = txfer.SerialTransfer('/dev/ttyACM1')

def structBackAndForth():
  # link = txfer.SerialTransfer('COM17')
  # link = txfer.SerialTransfer('/dev/ttyACM1')
  
  link.open()
  time.sleep(2) # allow some time for the Arduino to completely reset
  
  while True:
    start_setup = time.time()
    send_size = 0
    
    ###################################################################
    # Send a list
    ###################################################################
    list_ = [1, 3]
    list_size = link.tx_obj(list_)
    send_size += list_size
    
    ###################################################################
    # Send a string
    ###################################################################
    # str_ = 'hello'
    # str_size = link.tx_obj(str_, send_size) - send_size
    # send_size += str_size
    
    ###################################################################
    # Send a float
    ###################################################################
    # float_ = 5.234
    # float_size = link.tx_obj(float_, send_size) - send_size
    # send_size += float_size
    
    ###################################################################
    # Transmit all the data to send in a single packet
    ###################################################################
    start_send1 = time.time()
    link.send(send_size)
    end_send1 = time.time()
    
    ###################################################################
    # Wait for a response and report any errors while receiving packets
    ###################################################################
    while not link.available():
      if link.status < 0:
        if link.status == txfer.CRC_ERROR:
          print('ERROR: CRC_ERROR')
        elif link.status == txfer.PAYLOAD_ERROR:
          print('ERROR: PAYLOAD_ERROR')
        elif link.status == txfer.STOP_BYTE_ERROR:
          print('ERROR: STOP_BYTE_ERROR')
        else:
          print('ERROR: {}'.format(link.status))
    
    link_avl1 = time.time()
    ###################################################################
    # Parse response list
    ###################################################################
    start_rcv1 = time.time()
    rec_list_  = link.rx_obj(obj_type=type(list_),
                 obj_byte_size=list_size,
                 list_format='i')
    end_rcv1 = time.time()
    # str_ = 'hellothere'
    str_ = 'hellotherefromtheothersideoftheUSBconnectionIhopeyouaredoingsowelloverthereandmaybeyouwouldliketocomeoverforteasometime?'
    str_size = link.tx_obj(str_)
    send_size = str_size
    start_send2 = time.time()
    print(send_size)
    link.send(send_size)
    end_send2 = time.time()
    while not link.available():
      if link.status < 0:
        if link.status == txfer.CRC_ERROR:
          print('ERROR: CRC_ERROR')
        elif link.status == txfer.PAYLOAD_ERROR:
          print('ERROR: PAYLOAD_ERROR')
        elif link.status == txfer.STOP_BYTE_ERROR:
          print('ERROR: STOP_BYTE_ERROR')
        else:
          print('ERROR: {}'.format(link.status))
    
    link_avl2 = time.time()

    rec_str_  = link.rx_obj(obj_type=type(str_),
                 obj_byte_size=str_size,
                 start_pos=0)
    # rec_list_  = link.rx_obj(obj_type=type(list_),
    #              obj_byte_size=list_size,
    #              list_format='i')
    end_rcv2 = time.time()
    
    ###################################################################
    # Parse response string
    ###################################################################
    # rec_str_   = link.rx_obj(obj_type=type(str_),
                 # obj_byte_size=str_size,
                 # start_pos=list_size)
    
    ###################################################################
    # Parse response float
    ###################################################################
    # rec_float_ = link.rx_obj(obj_type=type(float_),
                 # obj_byte_size=float_size,
                 # start_pos=(list_size + str_size))
    
    ###################################################################
    # Display the received data
    ###################################################################
    parse_end = time.time()
    # print('SENT: {}'.format(list_))
    # print('RCVD: {}'.format(rec_list_))
    print('SENT: {} {}'.format(list_, str_))
    print('RCVD: {} {}'.format(rec_list_, rec_str_))
    # print('SENT: {} {} {}'.format(list_, str_, float_))
    # print('RCVD: {} {} {}'.format(rec_list_, rec_str_, rec_float_))
    print_end = time.time()
    print(' ')
    print(f"setup1:          {1000*(start_send1 - start_setup):0.8f}")
    print(f"send1:           {1000*(end_send1   - start_send1):0.8f}")
    print(f"avail1:          {1000*(link_avl1   - end_send1):0.8f}")
    print(f"rcv1:            {1000*(end_rcv1    - link_avl1):0.8f}")
    print(f"setup2:          {1000*(start_send2 - end_rcv1):0.8f}")
    print(f"send2:           {1000*(end_send2   - start_send2):0.8f}")
    print(f"avail2:          {1000*(link_avl2   - end_send2):0.8f}")
    print(f"rcv2:            {1000*(end_rcv2    - link_avl2):0.8f}")
    print(f"print:           {1000*(print_end   - end_rcv2):0.8f}")
    print(f"loop time:       {1000*(time.time() - start_setup):0.8f}\n")

    time.sleep(.5)


def hi():
  '''
  Callback function that will automatically be called by link.tick() whenever
  a packet with ID of 0 is successfully parsed.
  '''
    
  print("hi")
    
'''
list of callback functions to be called during tick. The index of the function
reference within this list must correspond to the packet ID. For instance, if
you want to call the function hi() when you parse a packet with an ID of 0, you
would write the callback list with "hi" being in the 0th place of the list:
'''
callback_list = [ hi ]

def callbackTest():
  # link = txfer.SerialTransfer('COM17')
    
  link.set_callbacks(callback_list)
  link.open()
  time.sleep(2) # allow some time for the Arduino to completely reset
    
  while True:
    link.tick()

if __name__ == '__main__':
  try:
    # structBackAndForth()
    callbackTest()
 
  except KeyboardInterrupt:
    try:
      link.close()
    except:
      pass
  
  except:
    import traceback
    traceback.print_exc()
    
    try:
      link.close()
    except:
      pass 