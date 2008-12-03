import struct

class UnexpectedPacketException (Exception):
    def __init__(self, packet_id):
        self.packet_id = packet_id
    def __str__ (self):
        msg = 'Unexpected packet with id [%04X] (%d)'
        return msg % ( self.packet_id, self.packet_id )

class Packet:

    # USB Protocol Layer
    DATA_AVAILABLE              = 0x0002
    START_SESSION               = 0x0005
    SESSION_STARTED             = 0x0006
    # Basic Link Information
    TRANSFER_COMPLETE           = 0x000C
    DATE_TIME                   = 0x000E
    RECORDS                     = 0x001B
    ALMANAC_DATA                = 0x001F
    TRACK_DATA                  = 0x0022
    TRACK_HEADER                = 0x0063
    LAP                         = 0x0095
    EXTENDED_PRODUCT_DATA       = 0x00F8
    PROTOCOL_ARRAY              = 0x00FD
    PRODUCT_DATA                = 0x00FF
    TRANSFER_RUNS               = 0x01C2
    RUN                         = 0X03DE
    WORKOUT                     = 0x03DF
    WORKOUT_OCCURRENCE          = 0x03E0
    FITNESS_USER_PROFILE        = 0x03E1
    COURSE                      = 0x0425
    COURSE_LAP                  = 0x0426
    COURSE_POINT                = 0x0427
    COURSE_TRACK_HEADER         = 0x0428
    COURSE_TRACK_DATA           = 0x0429
    COURSE_LIMITS               = 0x042A

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
