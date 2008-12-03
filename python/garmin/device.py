import array, logging
from garmin.protocol    import *
from garmin.command     import *
from garmin.utils       import *

log = logging.getLogger('garmin.device')

class Forerunner (USBPacketDevice):
    VENDOR_ID =  0x091E
    PRODUCT_ID = 0x0003

    def __init__ (self):
        USBPacketDevice.__init__(self, Forerunner.VENDOR_ID, Forerunner.PRODUCT_ID )
        self.product = None
        self.protocols = None

    def get_protocols (self):
        return self.protocols

    def start_session (self):
        self.send_command( StartSession )
        self.device_id = self.get_single_record(Packet.SESSION_STARTED)

    def get_device_capabilities (self):
        self.send_command( GetDeviceDescription )
        return self.execute_reader( self.device_capabilities_reader() )

    def get_fitness_profile (self):
        self.send_command( TransferFitnessUserProfile )
        return self.get_single_record(Packet.FITNESS_USER_PROFILE)

    def get_time (self):
        self.send_command( TransferTime )
        return self.get_single_record(Packet.DATE_TIME)

    def get_almanac (self):
        self.send_command( TransferAlmanac )
        return self.get_records(Packet.ALMANAC_DATA)

    def get_workouts (self):
        self.send_command( TransferWorkouts )
        workouts = self.get_records(Packet.WORKOUT)
        for workout in workouts:
            log.debug('\n'*5)
            log.debug('workout: %s', workout)
        workout_occurences = self.get_workout_occurences()
        return workouts, workout_occurences

    def get_workout_occurences (self):
        self.send_command( TransferWorkoutOccurrences )
        return self.get_records(Packet.WORKOUT_OCCURRENCE)

    def get_course_limits (self):
        self.send_command( TransferCourseLimits )
        return self.get_single_record( Packet.COURSE_LIMITS )

    def get_courses (self):
        self.send_command( TransferCourses )

    def get_runs (self):
        self.send_command( TransferRuns )
        runs = self.get_records( Packet.RUN )
        laps = self.get_laps()
        track_log = self.get_track_log()
        return runs, laps, track_log

    def get_laps (self):
        self.send_command( TransferLaps )
        return self.get_records( Packet.LAP )

    def get_track_log (self):
        self.send_command( TransferTrackLog )
        return self.execute_reader( self.track_log_reader() )

    def get_single_record (self, expected_packet_id):
        packet_id, response = self.read_response()
        if packet_id != expected_packet_id:
            raise UnexpectedPacketException(packet_id)
        return response

    def get_records (self, expected_packet_id):
        return self.execute_reader( self.record_reader( expected_packet_id ) )

    def device_capabilities_reader (self):
        packet_id, product_info = yield
        if packet_id != Packet.PRODUCT_DATA:
            raise UnexpectedPacketException(packet_id)
        self.product_info = product_info
        self.extended_product_info = []

        while True:
            packet_id, data = yield
            if packet_id != Packet.EXTENDED_PRODUCT_DATA:
                break
            self.extended_product_info.extend( data )

        if packet_id!= Packet.PROTOCOL_ARRAY:
            raise UnexpectedPacketException(packet_id)
        self.protocols = data

        yield True

    def record_reader (self, expected_packet_id ):
        records = []
        packet_id, record_count = yield
        if packet_id != Packet.RECORDS:
            raise UnexpectedPacketException(packet_id)

        for i in xrange(record_count):
            packet_id, record = yield
            if packet_id != expected_packet_id:
                raise UnexpectedPacketException(packet_id)
            records.append( record )

        packet_id, ignored_value = yield
        if packet_id != Packet.TRANSFER_COMPLETE:
            raise UnexpectedPacketException(packet_id)

        yield records

    def track_log_reader ( self ):
        records = []
        packet_id, record_count = yield
        if packet_id != Packet.RECORDS:
            raise UnexpectedPacketException(packet_id)

        last_track = Obj( header = None, data = [] )
        for i in xrange(record_count ):
            packet_id, data = yield
            if packet_id == Packet.TRACK_HEADER:
                if last_track.header is not None:
                    records.append( last_track )
                last_track = Obj( header = data, data = [] )
            elif packet_id == Packet.TRACK_DATA:
                last_track.data.extend( data )
            else:
                raise UnexpectedPacketException(packet_id)

        packet_id, ignored_value = yield
        if packet_id != Packet.TRANSFER_COMPLETE:
            raise UnexpectedPacketException(packet_id)

        yield records



