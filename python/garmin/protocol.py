import struct, logging, datetime
from garmin.usbio   import GarminUSB
from garmin.packet  import *
from garmin.utils   import objectify, Obj, UTC
import garmin.command
log = logging.getLogger('garmin.protocol')

from garmin.utils import StructReader, hexdump

class ProtocolException(Exception): pass

class UnsupportedDatatypeExecption (ProtocolException):
    def __init__(self, datatype):
        self.datatype = datatype
    def __str__ (self):
        msg = 'Unsupported datatype [%04X] (%d)'
        return msg % ( self.datatype, self.datatype )

class USBPacketDevice( GarminUSB ):

    def get_protocols (self):
        raise Exception, 'Please override me and by a method that returns a ProtocolManager'

    def datatype_for (self, datatype_name, *implemented ):
        value = self.get_protocols().datatype(datatype_name)
        if len(implemented)>0:
            if value not in implemented:
                raise UnsupportedDatatypeExecption(value)
        return value

    def execute_reader( self, reader ):
        reader.next()
        while True:
            result = reader.send( self.read_response() )
            if result is not None:
                return result

    def send_command (self, command):
        if not isinstance(command,garmin.command.Base):
            # intanciate the class
            command = command()
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
            , Packet.DATE_TIME              : 'date_time'
            , Packet.PROTOCOL_ARRAY         : 'protocol_array'
            , Packet.ALMANAC_DATA           : 'almanac_data'
            , Packet.TRANSFER_COMPLETE      : 'ushort'
            , Packet.PRODUCT_DATA           : 'product_data'
            , Packet.EXTENDED_PRODUCT_DATA  : 'extended_product_data'
            , Packet.FITNESS_USER_PROFILE   : 'fitness_user_profile'
            , Packet.RECORDS                : 'ushort'
            , Packet.RUN                    : 'run'
            , Packet.LAP                    : 'lap'
            , Packet.WORKOUT                : 'workout'
            , Packet.WORKOUT_OCCURRENCE     : 'workout_occurrence'
            , Packet.TRACK_HEADER           : 'track_header'
            , Packet.TRACK_DATA             : 'track_data'
            , Packet.COURSE                 : 'course'
            , Packet.COURSE_LAP             : 'course_lap'
            , Packet.COURSE_POINT           : 'course_point'
            , Packet.COURSE_TRACK_HEADER    : 'course_track_header'
            , Packet.COURSE_TRACK_DATA      : 'course_track_data'
            , Packet.COURSE_LIMITS          : 'course_limits'
        }.get( packet.id, None )
        if decoder is None:
            log.warn('Skipping unknown packet with id [%04X] (%d)', packet.id, packet.id )
            return 0, None
        if decoder is '':
            return packet.id, None
        return packet.id, getattr(self,'d_%s' % decoder)( StructReader(packet.payload, endianness ='<') )

    def d_ulong (self, sr):
        return sr.read('L')

    def d_ushort (self, sr):
        return sr.read('H')

    def d_date_time (self, sr):
        datatype = self.datatype_for('date_time', 600)
        month, day, year, hour, minute, second = sr.read('2B 2H 2B')
        return datetime.datetime( year, month, day, hour, minute, second, 0, UTC() )

    def d_fitness_user_profile (self, sr):
        datatype = self.datatype_for('fitness', 1004)
        activities =  Obj()
        for activity in [ 'running', 'biking', 'other' ]:
            heart_rate_zones = []
            for i in xrange(5):
                low, high = sr.read('2B 2x')
                heart_rate_zones.append( Obj(low = low, high = high) )
            speed_zones = []
            for i in xrange(10):
                low, high = sr.read('2f')
                name = sr.read_fixed_string(16)
                speed_zones.append( Obj( name = name, low = low, high = high) )
            gear_weight, maximum_heart_rate = sr.read('f B 3x')
            keys = ( 'heart_rate_zones', 'speed_zones', 'gear_weight','maximum_heart_rate' )
            values = ( heart_rate_zones, speed_zones, gear_weight, maximum_heart_rate )
            activities[ activity ] = objectify(keys,values)

        weight, birth_year, birth_month, birth_day, gender = sr.read('f H 3B')
        birthdate = datetime.date( birth_year, birth_month, birth_day)

        keys = ( 'activities', 'weight', 'birthdate', 'gender' )
        values = ( activities, weight, birthdate, gender )
        return objectify(keys,values)

    def d_run (self, sr):
        datatype = self.datatype_for('run', 1009)
        track_index, first_lap_index, last_lap_index = sr.read('3H')
        sport, program, multisport = sr.read('3B 3x')
        quick_wokrout = objectify( ( 'time', 'distance' ), sr.read('L f') )
        workout = self.d_workout(sr, forced_datatype = 1008)
        keys = ( 'track_index', 'first_lap_index', 'last_lap_index', 'sport', 'program', 'multisport', 'quick_wokrout', 'workout')
        values = ( track_index, first_lap_index, last_lap_index, sport, program, multisport, quick_wokrout, workout )
        return objectify(keys,values)

    def d_lap (self, sr):
        datatype = self.datatype_for('lap', 1011, 1015)
        index = sr.read('H 2x')
        start_time = sr.read_time()
        duration, distance, max_speed  = sr.read('L 2f')
        begin = sr.read_position()
        end = sr.read_position()
        calories, average_heart_rate, maximum_heart_rate, intensity, average_cadence, trigger_method = sr.read('H 5B')

        keys = ( 'index', 'start_time', 'duration', 'distance', 'max_speed', 'begin', 'end', 'calories', 'average_heart_rate', 'maximum_heart_rate', 'intensity', 'average_cadence', 'trigger_method' )
        values = ( index, start_time, duration, distance, max_speed, begin, end, calories, average_heart_rate, maximum_heart_rate, intensity, average_cadence, trigger_method )
        return objectify(keys,values)

    def d_workout (self, sr, forced_datatype= None):
        datatype = forced_datatype or self.datatype_for('workout', 1008)
        valid_steps_counts = sr.read('L')
        steps = []
        for i in xrange(20):
            keys = ( 'custom_name', 'target_custom_zone_low', 'target_custom_zone_high', 'duration_value', 'intensity', 'duration', 'target', 'target_value')
            custom_name = sr.read_fixed_string(16)
            values = ( custom_name, ) + sr.read('2f H 4B 2x')
            steps.append( objectify(keys,values) )
        name = sr.read_fixed_string(16)
        sport = sr.read('B')
        return name, sport, steps[:valid_steps_counts]

    def d_workout_occurrence(self, sr):
        datatype = self.datatype_for('workout.occurrence', 1003)
        workout_name = sr.read_fixed_string(16)
        day = sr.read_time()
        return Obj( workout_name = workout_name, day = day )

    def d_track_header (self, sr):
        datatype = self.datatype_for('track.header', 310, 311, 312)
        if datatype == 311:
            return sr.read('H')
        elif datatype in [ 310, 312 ]:
            display, color = sr.read('2B')
            identifier = sr.read_string()
            return Obj( display = display, color = color, identifier = identifier )
        else:
            raise UnsupportedDatatypeExecption(datatype)

    def d_track_data (self,sr):
        datatype = self.datatype_for('track.data', 304)

        position = sr.read_position()
        time = sr.read_time()
        altitude, distance, heart_rate, cadence, sensor = sr.read('2f 3B')
        keys = ( 'position', 'time', 'altitude', 'distance', 'heart_rate', 'cadence', 'sensor' )
        values = ( position, time, altitude, distance, heart_rate, cadence, sensor )
        return objectify(keys,values)

    def d_almanac_data (self, sr):
        datatype = self.datatype_for('almanac', 501)
        keys = ( 'week_number', 'af0', 'af1', 'eccentricity', 'sqrta', 'm0', 'w', 'omg0', 'odot', 'inclination', 'health' )
        return objectify(keys,sr.read('H 10f B'))


    def d_course (self, sr):
        datatype = self.datatype_for('course',0)

    def d_course_point (self, sr):
        datatype = self.datatype_for('course.point',0)

    def d_course_lap (self, sr):
        datatype = self.datatype_for('course.lap',0)

    def d_course_track_header (self, sr):
        datatype = self.datatype_for('course.track.header',0)

    def d_course_track_data (self, sr):
        datatype = self.datatype_for('course.track.data',0)

    def d_course_limits (self, sr):
        dataype = self.datatype_for('course.limits', 1013)
        keys = ('max_courses','max_course_laps','max_course_points','max_course_track_poins')
        return objectify(keys,sr.read('4L'))


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
        ,1003: [ 'workout.occurrence', 'workout.occurrence' ]
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

