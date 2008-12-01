import struct, logging
from garmin.usbio   import GarminUSB
from garmin.packet  import *
from garmin.utils   import Obj
log = logging.getLogger('garmin.protocol')

from garmin.utils import StructReader, hexdump

class ProtocolException(Exception): pass


class USBPacketDevice( GarminUSB ):

    def get_protocols (self):
        raise Exception, 'Please override me and by a method that returns a ProtocolManager'

    def execute_reader( self, reader ):
        reader.next()
        while True:
            result = reader.send( self.read_response() )
            if result is not None:
                return result

    def send_command (self, command):
        log.debug('Sending command: %s', command )
        packet = command.encode_for_device( self.get_protocols() )
        self.write_packet( packet )

    def read_response (self):
        packet = self.read_packet()
        if packet.payload is None:
            log.debug('done')
            return packet.id, None
        return self.decode( packet )

    def decode (self, packet):
        # log.debug('decoding: %04X (%d) length: %d %s', packet.id, packet.id, len(packet.payload), hexdump(packet.payload) )
        decoder = {
            0 : None
            , Packet.SESSION_STARTED        : 'ulong'
            , Packet.PROTOCOL_ARRAY         : 'protocol_array'
            , Packet.TRANSFER_COMPLETE      : 'ushort'
            , Packet.PRODUCT_DATA           : 'product_data'
            , Packet.EXTENDED_PRODUCT_DATA  : 'extended_product_data'
            , Packet.RECORDS                : 'ushort'
            , Packet.RUN                    : 'run'
            , Packet.LAP                    : 'lap'
            , Packet.TRACK_HEADER           : 'track_header'
            , Packet.TRACK_DATA             : 'track_data'
        }.get( packet.id, None )
        if decoder is None:
            log.warn('Skipping unknown packet with id [%04X] (%d)', packet.id, packet.id )
            return None
        if decoder is '':
            return None
        return packet.id, getattr(self,'d_%s' % decoder)( StructReader(packet.payload, endianness ='<') )

    def d_ulong (self, sr):
        return sr.read('L')

    def d_ushort (self, sr):
        return sr.read('H')

    def d_run (self,sr):
        track_index, first_lap_index, last_lap_index = sr.read('3h')
        sport, program, multisport = sr.read('3B 3x')
        time,distance = sr.read('2L')
        workout = self.d_workout(sr)

        keys = ( 'track_index', 'first_lap_index', 'last_lap_index', 'sport', 'program','multisport','time', 'distance', 'workout')
        values = ( track_index, first_lap_index, last_lap_index, sport, program, multisport,time, distance, workout )
        return Obj(zip(keys,values))

    def d_lap (self,sr):
        index = sr.read('H 2x')
        start_time = sr.read_time()
        duration, distance, max_speed  = sr.read('L 2f')
        begin = sr.read_position()
        end = sr.read_position()
        calories, average_heart_rate, maximum_heart_rate, intensity, average_cadence, trigger_method = sr.read('H 5B')

        keys = ( 'index', 'start_time', 'duration', 'distance', 'max_speed', 'begin', 'end', 'calories', 'average_heart_rate', 'maximum_heart_rate', 'intensity', 'average_cadence', 'trigger_method' )
        values = ( index, start_time, duration, distance, max_speed, begin, end, calories, average_heart_rate, maximum_heart_rate, intensity, average_cadence, trigger_method )
        return Obj(zip(keys,values))

    def d_workout (self,sr):
        valid_steps_counts = sr.read('L')
        steps = []
        for i in xrange(20):
            keys = [ 'custom_name','target_custom_zone_low','target_custom_zone_high'
                    ,'duration_value','intensity','duration','target'
                    ,'target_value']
            values = sr.read('16s 2f H 4B 2x')
            steps.append( Obj(zip(keys,values)) )
        name, sport =  sr.read('16s B')
        return name,sport,steps[:valid_steps_counts]

    def d_track_header (self, sr):
        log.debug('should decode track header %s', hexdump(sr.data) )
        protocols = self.get_protocols()
        datatype = protocols.datatype('track.header')

        if datatype == 311:
            return sr.read('H')

        elif datatype in [ 310, 312 ]:
            display, color = sr.read('2B')
            identifier = sr.read_string()
            return Obj( display = display, color = color, identifier = identifier )
        else:
            raise ProtocolException, 'Cannot decode Track Header with datatype [%d]' % datatype
        

        return None

    def d_track_data (self,sr):
        # log.debug('should decode track data %s', hexdump(sr.data) )
        return '.'

    def d_protocol_array (self, sr):
        physical = None
        link = None
        protocols = {}
        last_protocol = None
        for i in range( len(sr)/3 ):
            tag, data = sr.read('c H')
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
        return ProtocolManager( physical, link, protocols )

    def d_product_data (self, sr):
        p = Obj()
        p.product_id, p.software_version = sr.read('H h')
        p.description = sr.read_string()
        p.extra =  sr.read_strings()
        return p

    def d_extended_product_data (self, sr):
        return sr.read_strings()

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

    def enforce_support (self, name):
        if self.supports(name):
            return
        raise ProtocolException, 'Protocol [%s] not supported by device' % name

