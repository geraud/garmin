#!/usr/bin/python
import os, sys, array, logging
import usb
from garmin.protocol import *

log = logging.getLogger('main')

class USBException(Exception): pass


class Garmin:
    VENDOR_ID =  0x091E
    PRODUCT_ID = 0x0003
    INTERFACE_ID = 0 # 0x1403
    BULK_TIMEOUT=3000
    INTR_TIMEOUT=3000
    MAX_PACKET_SIZE=1024

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
                log.debug('Inpsecting device %s', device)
                if device.idVendor == Garmin.VENDOR_ID and device.idProduct == Garmin.PRODUCT_ID:
                    self.device = device
                    log.debug('Found device')
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
        bytes = self.handle.interruptRead( self.interrupt_in, Garmin.MAX_PACKET_SIZE, Garmin.INTR_TIMEOUT )
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
        log.debg('Session started')

    def read_a000_a001 (self):
        self.write_packet( Packet.encode_app(PacketID.PRODUCT_REQUEST) )

        while True:
            response = self.read_packet()
            print response.decode()
            packed_id = response.id()
            if packed_id == PacketID.PRODUCT_DATA:
                print 'product_data'
                print response
            elif packed_id == PacketID.EXTENDED_PRODUCT_DATA:
                print 'ext_product_data'
                print response
            elif packed_id == PacketID.PROTOCOL_ARRAY:
                print 'protocol_array'
                print response
                break


    def get_runs(self):
        log.debug('Reading runs')
        # # Read the runs, then the laps, then the track log.
        #
        #
        #   if ( garmin_send_command(garmin,Cmnd_Transfer_Runs) != 0 ) {
        #     d = garmin_alloc_data(data_Dlist);
        #     l = d->data;
        #     garmin_list_append(l,garmin_read_records(garmin,Pid_Run,
        #                garmin->datatype.run));
        #     garmin_list_append(l,garmin_read_a906(garmin));
        #     garmin_list_append(l,garmin_read_a302(garmin));
        #   }
        #
        #   return d;
        # }

    def test (self):
        self.start_session()
        self.read_a000_a001()
        self.get_runs()

def init_logging ():
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(levelname)s %(name)s: %(message)s")
    ch.setFormatter(formatter)
    logger.addHandler(ch)

def main():
    init_logging()

    dev = Garmin()
    try:
        dev.test()
    finally:
        dev.close()

if __name__=='__main__':
    main()
