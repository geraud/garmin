import struct

class UnexpectedPacketException(Exception):
    def __init__(self, packet_id):
        self.packet_id = packet_id
    def __repr__ (self):
        msg = 'Unexpected packet with id [%04x] (%d)'
        return msg % ( packet_id, packet_id )
        

class Packet:

    # USB Protocol Layer
    DATA_AVAILABLE              = 0x0002
    START_SESSION               = 0x0005
    SESSION_STARTED             = 0x0006
    # Basic Link Information
    TRANSFER_COMPLETE           = 0x000C
    RECORDS                     = 0x001B
    TRACK_DATA                  = 0x0022
    TRACK_HEADER                = 0x0063
    PROTOCOL_ARRAY              = 0x00FD
    PRODUCT_DATA                = 0x00FF
    EXTENDED_PRODUCT_DATA       = 0x00F8
    TRANSFER_RUNS               = 0x01C2
    RUN                         = 0X03DE
    LAP                         = 0x0095


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

        msg = "<Packet protocol: %s, id: %04X, length: %s, payload: %s>"
        return msg % ( type_name, self.id, len(self.payload), hexdump(self.payload) )


    @staticmethod
    def encode_usb( packet_id, payload = None):
        return Packet.encode_packet(0,packet_id,payload)

    @staticmethod
    def encode( packet_id, payload = None):
        return Packet.encode_packet(20,packet_id,payload)

    @staticmethod
    def encode_packet (protocol, packet_id, payload = None ):
        message = struct.pack('<B3xH2xL', protocol, packet_id, len(payload or '') )
        if payload is not None:
            message += payload
        return message

    @staticmethod
    def dump ( data ):
        return ''.join( map( lambda x: '\\x%02x' % ord(x), data) )
