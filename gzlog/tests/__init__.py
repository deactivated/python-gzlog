import os
import unittest
import tempfile

import gzlog


class GZLogTest(unittest.TestCase):

    def test_write_then_read(self):
        temp = tempfile.NamedTemporaryFile()
        zl = gzlog.GZLog(temp.name)
        test_string = "\xe4\x7f\xec\xa1\xc7;\xfee:\xd5\xac\x91J\xb5\x8eO\x8b\xb4"

        for n in range(10):
            zl.write(test_string)

        read_count = 0
        for l in zl.read():
            read_count += 1
            self.assertEqual(l, test_string)
        self.assertEqual(read_count, 10)

        read_count = 0
        for l in zl.read(5):
            read_count += 1
            self.assertEqual(l, test_string)
        self.assertEqual(read_count, 5)

    def test_write_then_rotate(self):
        temp = tempfile.NamedTemporaryFile()
        zl = gzlog.GZLog(temp.name)
        test_string = "\xe4\x7f\xec\xa1\xc7;\xfee:\xd5\xac\x91J\xb5\x8eO\x8b\xb4"

        for n in range(10):
            zl.write(test_string)

        zl.rotate()
        self.assertEqual(zl.name, "%s.001" % temp.name)
        self.assertTrue(os.path.exists(zl.name))

        read_count = 0
        for l in zl.read():
            read_count += 1
            self.assertEqual(l, test_string)
        self.assertEqual(read_count, 10)

        temp.name = zl.name

    def test_rotation_names(self):
        def touch(fn):
            open(fn, "w").close()

        def check_rotate_name(name):
            zl = gzlog.GZLog(temp.name)
            zl.rotate()
            self.assertEqual(zl.name, "%s.%s" % (temp.name, name))
            self.assertTrue(os.path.exists(zl.name))

        temp = tempfile.NamedTemporaryFile()

        # Basic rotation
        check_rotate_name("001")
        check_rotate_name("002")

        # Rotation with spaces
        touch("%s.050" % temp.name)
        check_rotate_name("051")

        # Rotation outside of the padded range.
        touch("%s.999" % temp.name)
        check_rotate_name("1000")
        check_rotate_name("1001")

        # Rotation in presence of weird file names
        touch("%s.999.z" % temp.name)
        touch("%s.999." % temp.name)
        touch("%s.9a9999" % temp.name)
        check_rotate_name("1002")

        touch(temp.name)
