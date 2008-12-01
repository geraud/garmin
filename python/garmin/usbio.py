import usb, array

from garmin.packet import *

class USBException(Exception): pass

class GarminUSB:
    MAX_PACKET_SIZE = 1024
    BULK_TIMEOUT    = 3000
    INTR_TIMEOUT    = 3000

    def __init__ (self, vendor_id, product_id ):
        self.vendor_id = vendor_id
        self.product_id = product_id
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
                if device.idVendor == self.vendor_id and device.idProduct == self.product_id:
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
        bytes = self.handle.interruptRead( self.interrupt_in, GarminUSB.MAX_PACKET_SIZE, GarminUSB.INTR_TIMEOUT )
        return Packet( array.array('B', bytes) )

    def write_packet (self,packet):
        self.open()
        return self.handle.bulkWrite( self.bulk_out, packet, GarminUSB.BULK_TIMEOUT )
