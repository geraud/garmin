import struct, logging

from garmin.protocol import Packet

log = logging.getLogger('garmin.command')

class CommandException (Exception): pass

class Base:

    def check_device_support (self, device):
        self.check_protocol_support( device )
        self.check_link_support( device )

    def check_protocol_support (self, device):
        for protocol in self.RequiredProtocol:
            if not device.supports( protocol ):
                raise CommandException, 'Command not supported'

    def check_link_support (self, device):
        code = self.command_code( device.link )
        if code is None:
            raise CommandException, 'Command not supported'

    def command_code (self,link_type):
        if link_type == 1:
            return self.Codes[0]
        else:
            return self.Codes[1]

    def link_code (self, link_type):
        return { 1: 0x0A, 2:0x0B }[ link_type ]

    def encode_for_device (self, device):
        self.check_device_support( device )
        link = self.link_code( device.link )
        command = self.command_code( device.link )
        return Packet.encode( link, struct.pack('<H',command) )

class StartSession (Base):
    Codes = [ 0x05, None ]
    def encode_for_device (self,device):
        return Packet.encode_usb( self.Codes[0] )

class GetDeviceDescription (Base):
    Codes = [ 254 , None]
    def encode_for_device (self,device):
        return Packet.encode( self.Codes[0] )

class AbortTransfer (Base):
    Codes = [ 0, 0 ]
    RequiredProtocol = []

class TransferAlmanac (Base):
    Codes = [ 1, 4]
    RequiredProtocol = [ 'almanac' ]

class TransferPosition (Base):
    Codes = [ 2, None ]
    RequiredProtocol = [ 'position' ]

class TransferProximityWaypoints (Base):
    Codes = [ 3, 17 ]
    RequiredProtocol = [ 'waypoint.proximity' ]

class TransferRoute (Base):
    Codes = [ 4, 8 ]
    RequiredProtocol = [ 'route' ]

class TransferTime (Base):
    Codes = [ 5, 20 ]
    RequiredProtocol = [ 'date_time' ]

class TransferTrackLog (Base):
    Codes = [ 6, None ]
    RequiredProtocol = [ 'track' ]

class TransferWaypoints (Base):
    Codes = [ 7, 21 ]
    RequiredProtocol = [ 'waypoint' ]

class PowerOff (Base):
    Codes = [ 8, 26 ]
    RequiredProtocol= []

class StartPVTDownload (Base):
    Codes = [ 49, None ]
    RequiredProtocol = [ 'pvt' ]

class StopPVTDownload (Base):
    Codes = [ 50, None ]
    RequiredProtocol = [ 'pvt' ]

class TransferFlightBook (Base):
    Codes = [ 92, None ]
    RequiredProtocol = [ 'flightbook' ]

class TransferLaps (Base):
    Codes = [ 117, None ]
    RequiredProtocol = [ 'lap' ]

class TransferWaypointCategories (Base):
    Codes = [ 121, None ]
    RequiredProtocol = [ 'waypoint.category' ]

class TransferRuns (Base):
    Codes = [ 450, None ]
    RequiredProtocol = [ 'run' ]

class TransferWorkouts (Base):
    Codes = [ 451, None ]
    RequiredProtocol = [ 'workout' ]

class TransferWorkoutOccurrences (Base):
    Codes = [ 452, None ]
    RequiredProtocol = [ 'workout.occurrence' ]

class TransferFitnessUserProfile (Base):
    Codes = [ 453, None ]
    RequiredProtocol = [ 'fitness' ]

class TransferWorkoutLimits (Base):
    Codes = [ 454, None ]
    RequiredProtocol = [ 'workout.limits' ]

class TransferCourses (Base):
    Codes = [ 561, None ]
    RequiredProtocol = [ 'course' ]

class TransferCourseLaps (Base):
    Codes = [ 562, None ]
    RequiredProtocol = [ 'course.lap' ]

class TransferCoursePoints (Base):
    Codes = [ 563, None ]
    RequiredProtocol = [ 'course.lap' ]

class TransferCourseTracks (Base):
    Codes = [ 564, None ]

    def check_protocol_support( self, device ):
        return device.supports('track') or device.supports('course.track')

class TransferCourseLimits (Base):
    Codes = [ 565, None ]
    RequiredProtocol = [ 'course.limits' ]

