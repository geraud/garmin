import struct
import logging
log = logging.getLogger('garmin.utils')

class StructReaderException(Exception): pass

class StructReader:

    def __init__ (self, data):
        self.data = data
        self.index = 0

    def read (self, format):
        size = struct.calcsize( format )
        result = struct.unpack_from( format, self.data, self.index )
        self.index += size
        return result

    def read_string (self):
        # Reads a 0 terminated string
        end = self.index
        for i in range( len(self.data) - self.index ):
            if 0 == self.data[end]:
                break
            else:
                end += 1
        result = self.data[self.index:end-1].tostring()
        self.index = end + 1 # skip the final zero
        return result

    def read_strings (self):
        result = []
        while not self.eof():
            result.append( self.read_string() )
        return result

    def eof(self):
        return self.index >= len(self.data)

    def skip (self, count):
        self.index += count

    def size (self):
        return len(self.data) - self.index

    def __len__(self):
        return len(self.data)


class Objectified(dict):
    def __getattr__(self, attribute_name ):
        return self.__getitem__(attribute_name)
    def __setattr__(self, attribute_name, value ):
        return self.__setitem__(attribute_name,value)


