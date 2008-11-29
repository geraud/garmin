import usb
import array, logging
from garmin.protocol import *
from garmin.command import *
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
        self.product = Obj()
        self.protocols = None

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
        self.send_command( StartSession() )
        packet_id, response = self.read_response()
        packet = self.read_packet()
        if packet.id != PacketID.SESSION_STARTED:
            raise USBException, 'Could not initiate session'
        log.debug('Session started')

    def read_device_capabiliies(self):
        log.debug('Entering read_device_capabiliies')
        self.send_command( GetDeviceDescription() )
        for i in range(3):
            self.read_response()
        log.debug('Leaving read_device_capabiliies')

    def get_runs(self):
        log.debug('Entering get_runs')
        self.send_command( TransferRuns() )
        while True:
            data = self.read_response()
            if data is None:
                break
            log.debug('should do something with the data: [%s]', data )
        log.debug('Leaving get_runs')

    def send_command( self, command ):
        log.debug('Sending command: %s', command )
        packet = command.encode_for_device( self.protocols )
        self.write_packet( packet )

    def read_response (self):
        packet = self.read_packet()
        if packet.payload is None:
            return None
        return self.decode( packet )

    def decode (self, packet):
        decoder = {
            0 : None
            , PacketID.SESSION_STARTED : 'session_started'
            , PacketID.PROTOCOL_ARRAY : 'protocols'
            , PacketID.PRODUCT_DATA : 'product_data'
            , PacketID.EXTENDED_PRODUCT_DATA : 'extended_product_data'
        }.get( packet.id, None )
        if decoder is None:
            log.warn('Unknown packet with id [%04X]', packet.id )
            return None
        if decoder is '':
            return None
        return packet.id, getattr(self,'d_%s' % decoder)( StructReader(packet.payload) )

    def d_session_started (self, sr):
        log.debug('session started')
        self.device_id = sr.read('<l')

    def d_protocols (self, sr):
        physical = None
        link = None
        protocols = {}
        last_protocol = None
        for i in range( len(sr)/3 ):
            tag, data = sr.read('<cH')
            if tag == 'P':
                physical, last_protocol = data, None
            elif tag == 'L':
                link, last_protocol = data, None
            elif tag == 'A':
                protocols[data], last_protocol = [], data
            elif tag== 'D':
                if last_protocol is None:
                    msg = 'Not Protocol data [%s] no associated with a protocol!'
                    raise ProtocolException, msg % data
                protocols[last_protocol].append( data )
        self.protocols = ProtocolManager( physical, link, protocols )

    def d_product_data (self, sr):
        p = self.product
        p.product_id, p.software_version = sr.read('<Hh')
        p.description= sr.read_string()
        p.extra = p.get('extra',[])
        p.extra.extend( sr.read_strings() )
        log.debug('product id %d',p.product_id)
        log.debug('software_version: %s', p.software_version )

    def d_extended_product_data (self, sr):
        p = self.product
        p.extended_data = sr.read_strings()



    def test (self):
        self.start_session()
        self.read_device_capabiliies()
        self.get_runs()
