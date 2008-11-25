#!/usr/bin/python

import sys
import usb
import time
import struct
import array
import math

class USBError(Exception): pass

BULK_TIMEOUT=3000
INTR_TIMEOUT=3000
MAX_PACKET_SIZE=1024

class PacketID:
  # USB Protocol Layer
  DATA_AVAILABLE  = 0x02
  START_SESSION   = 0x05
  SESSION_STARTED = 0x06
  # Basic Link Information
  PRODUCT_REQUEST = 0xfe

class Packet:

  def __init__ (self,data):
    self.packet_id = None
    data_as_string  = ''.join( map(chr, data) )
    result = struct.unpack('<B3xH2xL',data_as_string[:12])
    self.parse_data()

  def id (self):
    print 'id'

  def parse_data (self):
    print 'should parse:', self.data

  def __len__ (self):
    return len(self.data)

  def __str__ (self):
    return str(self.data)

  @staticmethod
  def encode (packet_id, payload = None, is_usb = False ):
    payload_size = 0
    if payload is not None:
      payload_size = len(payload)
    if is_usb: protocol = 0
    else:      protocol = 20
    message = struct.pack('<B3xH2xL', protocol, packet_id, payload_size)
    if payload is not None and payload_size > 0:
     message += payload
    return message

  @staticmethod
  def dump ( data ):
    return ''.join( map( lambda x: '\\x%02x' % ord(x), data) )


class Garmin:
  VENDOR_ID =  0x091E
  PRODUCT_ID = 0x0003
  INTERFACE_ID = 0 # 0x1403

  def __init__ (self):
    self.device = None
    self.handle = None
    self.bulk_in = None
    self.bulk_out = None
    self.interrupt_in = None

  def is_open (self):
    return self.handle is not None

  def open (self):
    if self.is_open():
      return
    for bus in usb.busses():
      for device in bus.devices:
        if device.idVendor == Garmin.VENDOR_ID and device.idProduct == Garmin.PRODUCT_ID:
          self.device = device
          break
    if self.device is None:
      raise USBError, 'Device not found'

    interface = self.device.configurations[0].interfaces[0][0]
    for endpoint in interface.endpoints:
      address = endpoint.address & usb.ENDPOINT_ADDRESS_MASK
      if endpoint.type == usb.ENDPOINT_TYPE_BULK:
        if (endpoint.address & usb.ENDPOINT_DIR_MASK) == usb.ENDPOINT_IN:
          self.bulk_in = address
        else:
          self.bulk_out = address
      elif endpoint.type == usb.ENDPOINT_TYPE_INTERRUPT:
        if (endpoint.address & usb.ENDPOINT_DIR_MASK) == usb.ENDPOINT_IN:
          self.interrupt_in = address
    self.handle = self.device.open)
    self.handle.setConfiguration(1)
    self.handle.claimInterface(0)

  def close (self):
    if self.handle is not None:
      self.handle.releaseInterface()
      self.handle.reset()
      del self.handle
      self.handle = None
    if self.device is not None:
      del self.device
      self.device = None

  def read_packet (self):
    self.open()
    data = self.handle.interruptRead( self.interrupt_in, MAX_PACKET_SIZE, INTR_TIMEOUT )
    print 'received', data
    return Packet( data )

  def write_packet (self,packet):
    self.open()
    return self.handle.bulkWrite( self.bulk_out, packet, BULK_TIMEOUT )

  def start_session (self):
    packet = Packet.encode( PacketID.START_SESSION, is_usb = True )
    self.write_packet(packet)
    self.write_packet(packet)
    self.write_packet(packet)

    response = self.read_packet()
    if len(response) != 16:
      raise USBError, 'Could not initiate session'
    print 'session started'

  def read_a000_a0001 (self):
    self.write_packet( Packet.encode(PacketID.PRODUCT_REQUEST) )

    while True:
      response = self.read_packet()
      print respopnse
      if respopnse is None:
        break
      print response.id()

  def test (self):
    self.start_session()
    self.read_a000_a0001()
    #@message = encode_packet(254) #struct.pack('<B3xH2x4x', 20,254)
    #print 'Message:', dump_packet(message)
    #print 'length:', len(message)
    # data = self.handle.interruptRead(self.interrupt_in,64)
    #data = self.handle.bulkRead(self.bulk_in,64)
    #return self.handle.bulkRead( Garmin.BULK_IN, 8, 2 )

def main():
  dev = Garmin()
  try:
    dev.test()
  finally:
    dev.close()

if __name__=='__main__':
  main()
