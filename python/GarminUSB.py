#!/usr/bin/python
import os, sys, array
import usb

from garmin.protocol import *
class USBException(Exception): pass

BULK_TIMEOUT=3000
INTR_TIMEOUT=3000
MAX_PACKET_SIZE=1024


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
      raise USBException, 'Device not found'

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
    self.handle = self.device.open()
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
    bytes = self.handle.interruptRead( self.interrupt_in, MAX_PACKET_SIZE, INTR_TIMEOUT )
    return Packet( array.array('B', bytes) )

  def write_packet (self,packet):
    self.open()
    return self.handle.bulkWrite( self.bulk_out, packet, BULK_TIMEOUT )

  def start_session (self):
    packet = Packet.start_session()
    self.write_packet(packet)
    self.write_packet(packet)
    self.write_packet(packet)

    response = self.read_packet()
    if len(response) != 16:
      raise USBException, 'Could not initiate session'
    print 'session started'

  def read_a000_a0001 (self):
    self.write_packet( Packet.encode_app(PacketID.PRODUCT_REQUEST) )

    while True:
      response = self.read_packet()
      packed_id = response.id()
      if packed_id == PacketID.PRODUCT_DATA:
        print 'product_data'
        print response
      elif packed_id == PacketID.EXT_PRODUCT_DATA:
        print 'ext_product_data'
        print response
      elif packed_id == PacketID.PROTOCOL_ARRAY:
        print 'protocol_array'
        print response
        break

  def test (self):
    self.start_session()
    self.read_a000_a0001()

def main():
  dev = Garmin()
  try:
    dev.test()
  finally:
    dev.close()

if __name__=='__main__':
  main()
