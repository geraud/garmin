import usb
import array, logging
from garmin.protocol import *
from garmin.utils import *

log = logging.getLogger('garmin.device')

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

        # slots for infos gathered
        self.product = Objectified()
        self.protocols = []
        # self.extended_product = Objectified()

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
        bytes = self.handle.interruptRead( self.interrupt_in, Garmin.MAX_PACKET_SIZE, Garmin.INTR_TIMEOUT )
        return Packet( array.array('B', bytes) )

    def write_packet (self,packet):
        self.open()
        return self.handle.bulkWrite( self.bulk_out, packet, Garmin.BULK_TIMEOUT )

    def start_session (self):
        packet = Packet.start_session()
        self.write_packet(packet)
        # self.write_packet(packet)
        # self.write_packet(packet)

        response = self.read_packet()
        if len(response) != 16:
            raise USBException, 'Could not initiate session'
        log.debug('Session started')

    def read_a000_a001 (self):
        log.debug('Entering read_a000_a001')
        self.write_packet( Packet.encode_app(PacketID.PRODUCT_REQUEST) )
        for i in range(3):
            packet = self.read_packet()
            self.decode(packet)
            # if packet.id in [ PacketID.PRODUCT_DATA, PacketID.EXTENDED_PRODUCT_DATA ]:
            #     log.debug('product [%s] [%s]',self.product,self.extended_product)
            # elif packet.id == PacketID.PROTOCOL_ARRAY:
            #     self.decode(packet)
            #     print 'protocol_array'
            #     print packet
            #     break

        log.debug('Leaving read_a000_a001')

    def get_runs(self):
        log.debug('Entering get_runs')
        log.debug('Leaving get_runs')
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

    def decode (self, packet):
        decoder = {
            0 : None
            , PacketID.PROTOCOL_ARRAY : 'protocols'
            , PacketID.PRODUCT_DATA : 'product_data'
            , PacketID.EXTENDED_PRODUCT_DATA : '' # skip 'extended_product_data'
        }.get( packet.id, None )
        if decoder is None:
            log.warn('Unknown packet with id [%04X]', packet.id )
            return None
        if decoder is '':
            return None
        return getattr(self,'d_%s' % decoder)( StructReader(packet.payload) )

    def d_protocols (self, sr):
        size = len(sr)
        for i in range( size/3 ):
            tag, data = sr.read('<BH')
            log.debug('processing protocol %d %s %s',i, tag, data )

            # self.protocols.append( Objectified(tag =  ))
        log.debug('packet size [%s] -> [%s]', size, size / 3 )
        return {}

    def d_product_data (self, sr):
        p = self.product
        p.product_id, p.software_version = sr.read('<Hh')
        p.description= sr.read_string()
        p.extra = p.get('extra',[])

    def test (self):
        self.start_session()
        self.read_a000_a001()
        self.get_runs()
