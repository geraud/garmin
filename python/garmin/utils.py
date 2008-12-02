import struct, logging, datetime, string
log = logging.getLogger('garmin.utils')

class UTC (datetime.tzinfo):
    def utcoffset(self, dt):
        return datetime.timedelta(0)
    def tzname(self, dt):
        return 'UTC'
    def dst(self, dt):
        return datetime.timedelta(0)

GARMIN_EPOCH = datetime.datetime(1989, 12, 31, 0, 0, 0, 0, UTC() )

ASCII_FILTER = ''.join( [ chr(i) in ( '-. ' + string.digits + string.ascii_letters) and chr(i) or ' ' for i in range(256)] )

class StructReaderException (Exception): pass

class StructReader:

    def __init__ (self, data, endianness='='):
        self.data = data
        self.index = 0
        self.endianness = endianness

    def read (self, format):
        if format[0] not in '=<>@':
            format = self.endianness + format
        size = struct.calcsize( format )
        result = struct.unpack_from( format, self.data, self.index )
        self.index += size
        if len(result) == 1:
            return result[0]
        else:
            return result

    def read_string (self):
        end = self.index
        for i in xrange( len(self.data) - self.index ):
            if 0 == self.data[end]:
                break
            else:
                end += 1
        result = self.data[self.index:end].tostring()
        self.index = end + 1 # skip the final zero
        return result.translate(ASCII_FILTER).strip()

    def read_fixed_string (self,length):
        return self.read('%ds'%length).split('\0')[0].translate(ASCII_FILTER).strip()

    def read_strings (self):
        result = []
        while not self.eof():
            result.append( self.read_string() )
        return result

    def read_time (self):
        return  GARMIN_EPOCH + datetime.timedelta( seconds = self.read('L') )

    def read_position (self):
        return self.read('2l')

    def eof(self):
        return self.index >= len(self.data)

    def skip (self, count):
        self.index += count

    def size (self):
        return len(self.data) - self.index

    def __len__(self):
        return len(self.data)

class Obj (dict):
    def __getattr__(self, attribute_name ):
        return self.__getitem__(attribute_name)
    def __setattr__(self, attribute_name, value ):
        return self.__setitem__(attribute_name,value)

def objectify (keys,values):
    return Obj(zip(keys,values))

FILTER=''.join([(len(repr(chr(x)))==3) and chr(x) or '.' for x in range(256)])

def hexdump (data,length=16):
    result = []
    for i in xrange(0, len(data), length):
        chunck = data[i:i+length]
        padding = length - len(chunck)
        hexa =  ' '.join( map( lambda x: '%02X' % x, chunck ) ) + '   ' * padding
        ascii = chunck.tostring().translate(FILTER)+ ' ' * padding
        result.append('%04X: %s |%s|' % (i, hexa, ascii) )
    return '\n'+'\n'.join(result)
