#!/usr/bin/python

import sys
import usb
import time
import struct
import array
import math

class USBError(Exception): pass

def encode_packet (packet_id, payload = None, is_usb = false ):
  payload_size = 0
  if payload is not None:
    payload_size = len(payload)
  if is_usb: protocol = 0
  else:      protocol = 20
  message = struct.pack('<B3xH2xL', protocol, packet_id, payload_size)
  if payload is not None and payload_size > 0:
   message += payload
  return message

def dump_packet ( data ):
  return ''.join( map( lambda x: '\\x%02x' % ord(x), data) )

BULK_TIMEOUT=3000
INTR_TIMEOUT=3000

class Garmin:
  VENDOR_ID =  0x091E
  PRODUCT_ID = 0x0003
  INTERFACE_ID = 0 # 0x1403

  def __init__ (self):
    print 'Searching for suitable devices'
    for bus in usb.busses():
      for device in bus.devices:
        if device.idVendor == Garmin.VENDOR_ID and device.idProduct == Garmin.PRODUCT_ID:
          self.device = device
          print 'Bus [%s] Device [%s]' % (bus.dirname, device)
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
    print 'found bulk_in [%s] bulk_out [%s] interrupt_in [%s]' % (self.bulk_in,self.bulk_out,self.interrupt_in)

  def isOpen (self):
    self.handle is not None

  def open (self):
    if self.isOpen():
      return
    self.handle = self.device.open()
    self.handle.setConfiguration(1)
    self.handle.claimInterface( Garmin.INTERFACE_ID )

  def close (self):
    self.handle.releaseInterface()

  def read_packet (self):
    self.open()

  def write_packet (self,packet):
    self.open()
    self.handle.bulkWrite( self.bulk_out, message )

  def start_session (self):
    pass

  def test (self):
    message = encode_packet(254) #struct.pack('<B3xH2x4x', 20,254)
    print 'Message:', dump_packet(message)
    print 'length:', len(message)
    # data = self.handle.interruptRead(self.interrupt_in,64)
    data = self.handle.bulkRead(self.bulk_in,64)
    #return self.handle.bulkRead( Garmin.BULK_IN, 8, 2 )


def main():
  dev = Garmin()
  dev.open()
  dev.test()
  dev.close()

if __name__=='__main__':
  main()
