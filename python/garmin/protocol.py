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

    @classmethod
    def start_session (self):
        return self.encode_usb( self.START_SESSION )


class ProtocolManager:
    DECODED_NAMES = {
        # FORMAT : CODE, DATA0, DATA1....
        100:   [ 'waypoint', 'waypoint' ]
        , 101: [ 'waypoint.category', 'waypoint.category' ]
        , 200: [ 'route', 'route.header', 'route.waypoint' ]
        , 201: [ 'route', 'route.header', 'route.waypoint', 'route.link' ]
        , 300: [ 'track', 'track.data' ]
        , 301: [ 'track', 'track.header', 'track.data' ]
        , 302: [ 'track', 'track.header', 'track.data' ]
        , 400: [ 'waypoint.proximity', 'waypoint.proximity' ]
        , 500: [ 'almanac', 'almanac' ]
        , 600: [ 'date_time', 'date_time' ]
        , 650: [ 'flightbook', 'flightbook' ]
        , 700: [ 'position', 'position']
        , 800: [ 'pvt', 'pvt' ]
        , 906: [ 'lap', 'lap' ]
        ,1000: [ 'run', 'run' ]
        ,1002: [ 'workout', 'workout' ]
        ,1003: [ 'workout.occurrences', 'workout.occurrences' ]
        ,1004: [ 'fitness', 'fitness' ]
        ,1005: [ 'workout.limits', 'workout.limits' ]
        ,1006: [ 'course', 'course' ]
        ,1007: [ 'course.lap', 'course.lap' ]
        ,1008: [ 'course.point', 'course.point' ]
        ,1009: [ 'course.limits', 'course.limits' ]
        ,1012: [ 'course.track', 'course.track.header', 'course.track.data' ]
    }

    def __init__ (self,pysical,link, protocols):
        self.protocols = { 'protocol.physical' : pysical, 'protocol.link' : int(link) }
        for proto_code, proto_values in protocols.items():
            names = self.DECODED_NAMES.get(proto_code,None)
            if names is None:
                continue
            self.protocols['protocol.%s' % names[0]] = proto_code
            for index, value_name in enumerate(names[1:]):
                self.protocols['datatype.%s' % value_name] = proto_values[ index ]

    def __getattr__(self,name):
        if name.startswith('has_'):
            return self.supports( name[4:] )
        elif name.startswith('supports_'):
            return self.supports( name[9:] )
        else:
            value = self.protocols.get('protocol.%s'%name,None)
            if value is not None:
                return value
        return super(object,self).__getattr__(name)

    def supports (self, name):
        return self.protocols.get('protocol.%s' % name, None) is not None

    def _code (self, name):
        return self.protocols['protocol.%s' % name]

    def datatype (self, name):
        return self.protocols['datatype.%s' % name]

    def enforce_support (self,name):
        if self.supports(name):
            return
        raise ProtocolException, 'Protocol [%s] not supported by device' % name

