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
        if packet_id != Packet.SESSION_STARTED:
            raise USBException, 'Could not initiate session'
        self.device_id = response

    def read_device_capabiliies(self):
        self.send_command( GetDeviceDescription() )
        for i in range(3):
            self.read_response()

    def get_runs(self):
        log.debug('Entering get_runs')
        self.send_command( TransferRuns() )
        runs = self.get_records( Packet.RUN )
        # now get the laps
        for run in runs:
            log.debug('drilling down for run:\n%s', run)
            log.debug('should get lap %d->%d',run.first_lap_index,run.last_lap_index)
        self.get_laps()
        log.debug('Leaving get_runs')


    def get_laps(self):
        log.debug('Entering get_laps')
        self.send_command( TransferLaps() )
        laps = self.get_records( Packet.LAP )
        log.debug('Leaving get_laps')


    def send_command( self, command ):
        log.debug('Sending command: %s', command )
        packet = command.encode_for_device( self.protocols )
        self.write_packet( packet )

    def read_response (self):
        packet = self.read_packet()
        if packet.payload is None:
            log.debug('done')
            return packet.id, None
        return self.decode( packet )

    def get_records (self, expected_packet_id):
        result = []
        while True:
            packet_id, response = self.read_response()
            if packet_id == Packet.RECORDS:
                record_count = response
            elif packet_id == expected_packet_id:
                result.append( response )
            elif packet_id == Packet.TRANSFER_COMPLETE:
                break
            else:
                msg = 'Unexpected packe with id [%04x]'
                raise ProtocolException, msg % expected_packet_id
        return result

    def decode (self, packet):
        # log.debug('decoding: %s/%03x %s', packet.id, packet.id, hexdump(packet.payload) )
        decoder = {
            0 : None
            , Packet.SESSION_STARTED        : 'ulong'
            , Packet.PROTOCOL_ARRAY         : 'protocols'
            , Packet.TRANSFER_COMPLETE      : 'ushort'
            , Packet.PRODUCT_DATA           : 'product_data'
            , Packet.EXTENDED_PRODUCT_DATA  : 'extended_product_data'
            , Packet.RECORDS                : 'ushort'
            , Packet.RUN                    : 'run_type'
            , Packet.LAP                    : 'lap_type'
        }.get( packet.id, None )
        if decoder is None:
            log.warn('Unknown packet with id [%04X]', packet.id )
            return None
        if decoder is '':
            return None
        return packet.id, getattr(self,'d_%s' % decoder)( StructReader(packet.payload, endianness ='<') )

    def d_ulong (self, sr):
        return sr.read('L')[0]

    def d_ushort (self, sr):
        return sr.read('H')[0]

    def d_run_type (self,sr):
        track_index, first_lap_index, last_lap_index = sr.read('3h')
        sport_type, program_type, multisport = sr.read('3B')
        sr.skip(3)
        time,distance = sr.read('2L')
        workout = self.d_workout_type(sr)
        # log.debug('-'*80)
        # log.debug( 'track_index first lap last lap: %d %d %d', track_index, first_lap_index, last_lap_index )
        # log.debug('       sport: %d', sport_type )
        # log.debug('program_type: %d', program_type )
        # log.debug('  multisport: %d', multisport )
        # log.debug('        time: %x', time )
        # log.debug('    duration: %x', distance )
        # log.debug('     workout: %s', workout )
        keys = ( 'track_index', 'first_lap_index', 'last_lap_index', 'sport_type', 'program_type','multisport','time', 'distance', 'workout')
        values = ( track_index, first_lap_index, last_lap_index, sport_type, program_type, multisport,time, distance, workout )
        return Obj(zip(keys,values))

    def d_lap_type (self,sr):
        index = sr.read('L')
        start_time = sr.read_time()
        log.debug('got time %s', start_time)
        # uint32 index; /* Unique among all laps received from device */
        #  time_type start_time; /* Start of lap time */
        #  uint32 total_time; /* Duration of lap, in hundredths of a second */
        #  float32 total_dist; /* Distance in meters */
        #  float32 max_speed; /* In meters per second */
        #  position_type begin; /* Invalid if both lat and lon are 0x7FFFFFFF */
        #  position_type end; /* Invalid if both lat and lon are 0x7FFFFFFF */
        #  uint16 calories; /* Calories burned this lap */
        #  uint8 avg_heart_rate; /* In beats-per-minute, 0 if invalid */
        #  uint8 max_heart_rate; /* In beats-per uint8 intensity; /* See below */



    def d_workout_type (self,sr):
        valid_steps_counts = sr.read('L')[0]
        steps = []
        for i in xrange(20):
            keys = [ 'custom_name','target_custom_zone_low','target_custom_zone_high'
                    ,'duration_value','intensity','duration_type','target_type'
                    ,'target_value']
            values = sr.read('16s 2f H 4B 2x')
            steps.append( Obj(zip(keys,values)) )
        name, sport_type =  sr.read('16s B')
        return name,sport_type,steps[:valid_steps_counts]

    def d_protocols (self, sr):
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
        self.protocols = ProtocolManager( physical, link, protocols )

    def d_product_data (self, sr):
        p = self.product
        p.product_id, p.software_version = sr.read('H h')
        p.description= sr.read_string()
        p.extra = p.get('extra',[])
        p.extra.extend( sr.read_strings() )

    def d_extended_product_data (self, sr):
        p = self.product
        p.extended_data = sr.read_strings()
