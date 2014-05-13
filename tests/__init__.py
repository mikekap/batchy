try:
    from gevent import monkey
except ImportError:
    pass
else:
    monkey.patch_all()

import unittest

class BaseTestCase(unittest.TestCase):
    def setup(self):
        pass

    def teardown(self):
        pass

    def setUp(self):
        self.setup()

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        self.teardown()

    def assert_line_equal(self, x, y):
        assert x == y, "lines not equal\n a = %r\n b = %r" % (x, y)

    def assert_equal(self, x, y, msg=None):
        return self.assertEqual(x, y, msg)

    assert_equals = assert_equal

    def assert_not_equal(self, x, y):
        return self.assertNotEqual(x, y)

    def assert_is_none(self, x):
        self.assertIsNone(x)

    def assert_is_not_none(self, x):
        self.assertIsNotNone(x)

    def assert_in(self, x, y):
        self.assertIn(x, y)

    def assert_is_instance(self, x, y):
        self.assertIsInstance(x, y)

    def assert_not_in(self, x, y):
        self.assertNotIn(x, y)

    def assert_is(self, x, y):
        self.assertIs(x, y)

    def assert_is_not(self, x, y):
        self.assertIsNot(x, y)

    def assert_true(self, x):
        self.assertTrue(x)

    def assert_false(self, x):
        self.assertFalse(x)

    def assert_sequence_equal(self, x, y):
        self.assertSequenceEqual(x, y)

    def assert_raises(self, exc, *args):
        return self.assertRaises(exc, *args)
