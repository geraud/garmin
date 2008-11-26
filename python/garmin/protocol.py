import struct
import logging
log = logging.getLogger('garmin.protocol')

from garmin.utils import StructReader

class ProtocolException(Exception): pass

class PacketID:
    # USB Protocol Layer
    DATA_AVAILABLE  = 0x02
    START_SESSION   = 0x05
    SESSION_STARTED = 0x06
    # Basic Link Information
    PROTOCOL_ARRAY                = 0x00FD
    PRODUCT_REQUEST               = 0x00FE
    PRODUCT_DATA                  = 0x00FF
    EXTENDED_PRODUCT_DATA         = 0x00F8

    TRANSFER_RUNS                 = 0x01C2


class Packet(PacketID):

    def __init__ (self,data):
        self.protocol, self.id, payload_length = struct.unpack('<B3xH2xL',data[:12])
        self.payload = data[12:]
        if len(self.payload) != payload_length:
            raise ProtocolException, 'Incorrect payload length'

    def __len__ (self):
        return len(self.payload) + 12

    def __str__ (self):
        if self.protocol == 0:
            type_name = 'USB'
        else:
            type_name = 'APP'
        payload = ' '.join( map(lambda x: '%02X' % x, self.payload) )
        return "<Packet protocol: %s, id: %04X, length: %s, payload: %s>" % (type_name, self.id, len(self.payload), payload )

    @staticmethod
    def encode_usb( packet_id, payload = None):
        return Packet.encode(0,packet_id,payload)

    @staticmethod
    def encode_app( packet_id, payload = None):
        return Packet.encode(20,packet_id,payload)

    @staticmethod
    def encode (protocol, packet_id, payload = None ):
        message = struct.pack('<B3xH2xL', protocol, packet_id, len(payload or '') )
        if payload is not None:
            message += payload
        return message

    @staticmethod
    def dump ( data ):
        return ''.join( map( lambda x: '\\x%02x' % ord(x), data) )

    @classmethod
    def start_session (self):
        return self.encode_usb( self.START_SESSION )

