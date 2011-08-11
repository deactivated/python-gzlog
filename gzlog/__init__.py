"""
A binary safe, record-structured log file with zlib compression.

- Write and rotate operations use flock to maintain atomicity.
- The compressed record size must be less than 2**32 bits long.
"""

import re
import os
import struct
import glob
from zlib import compress, decompress
from fcntl import flock, LOCK_EX, LOCK_UN


_z_struct = struct.Struct("!I")
_z_pack = _z_struct.pack
_z_unpack = _z_struct.unpack


class GZLog(object):
    """
    GZLog is a nearly trivial object for logging binary strings to disk.

    Each entry is stored as the compressed length in big-endian format,
    followed by the compressed data, followed again by the compressed length.
    The length is stored at each end of the record to allow the log to be read
    in reverse.
    """

    def __init__(self, fn):
        """
        Initialize a GZLog object with a given base filename.

        Rotated log files will have a file name "<filename>.###".
        """
        self.name = fn

    def write(self, record):
        """
        Write a record to the log.
        """
        z_record = compress(record, 2)
        z_length = _z_pack(len(z_record))

        # Write a null after the record length to make it a little easier to
        # recover corrupt log files.
        f_record = "%s\0%s%s\0" % (z_length, z_record, z_length)

        with open(self.name, "ab") as f:
            flock(f, LOCK_EX)
            f.write(f_record)
            flock(f, LOCK_UN)

    def read(self, skip=0):
        """
        Yield records from the log file.  Optionally skip a given number of
        records.
        """
        with open(self.name, "r") as f:
            idx = 0
            while True:
                s_len = f.read(4)
                if len(s_len) < 4:
                    return

                r_len, = _z_unpack(s_len)
                f.seek(1, os.SEEK_CUR)
                if idx < skip:
                    f.seek(r_len, os.SEEK_CUR)
                else:
                    z = f.read(r_len)
                    if len(z) != r_len:
                        return

                    s = decompress(z)
                    yield s

                f.seek(5, os.SEEK_CUR)
                idx += 1

    __iter__ = read

    def rotate(self):
        """
        Rotate the current log file.
        """
        ext_re = re.compile(r"\.(\d+)$")
        if ext_re.match(self.name):
            return

        with open(self.name, "ab") as f:
            flock(f, LOCK_EX)

            try:
                next_id = max(int(ext_re.findall(fn)[0]) for fn in
                              glob.glob("%s.*[0-9]" % self.name)
                              if ext_re.search(fn)) + 1
            except ValueError:
                next_id = 1
            next_fn = "%s.%03d" % (self.name, next_id)
            os.rename(self.name, next_fn)

            flock(f, LOCK_UN)
        self.name = next_fn
