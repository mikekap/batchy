import time
from unittest.case import SkipTest

from batchy.compat import PY3
from batchy.clients.memcached import BatchMemcachedClient
from batchy.runloop import coro_return, runloop_coroutine

from . import BaseTestCase

try:
    import pylibmc

    mc_client = pylibmc.Client(["127.0.0.1"], behaviors={
        'connect_timeout': 1
    })
    mc_client.get('hello')
except ImportError:
    print('Please install pylibmc to run the memcached client tests.')
    mc_client = None
except Exception:
    mc_client = None

class MemcachedClientTests(BaseTestCase):
    def setup(self):
        if mc_client is None:
            raise SkipTest()

        self.client = BatchMemcachedClient(mc_client)

        if PY3:
            self.key_prefix = bytes('%s|' % (time.time(),), 'ascii')
        else:
            self.key_prefix = b'%s|' % (time.time(),)

    def test_multi_get(self):
        @runloop_coroutine()
        def set_thing(a, b):
            yield self.client.set(self.key_prefix + b'hi' + a, b, time=100)

        @runloop_coroutine()
        def get_thing(a):
            v = yield self.client.get(self.key_prefix + b'hi' + a)
            coro_return(v)

        @runloop_coroutine()
        def test():
            yield set_thing(b'a', 1), set_thing(b'b', 2)
            a, b = yield get_thing(b'a'), get_thing(b'b')
            coro_return(a + b)

        self.assert_equals(3, test())

    def test_multi_delete(self):
        @runloop_coroutine()
        def set_thing(a, b):
            yield self.client.set(self.key_prefix + b'hi' + a, b, time=100)

        @runloop_coroutine()
        def get_thing(a):
            v = yield self.client.get(self.key_prefix + b'hi' + a)
            coro_return(v)

        @runloop_coroutine()
        def delete_thing(a):
            yield self.client.delete(self.key_prefix + b'hi' + a)

        @runloop_coroutine()
        def test():
            yield set_thing(b'a', 1), set_thing(b'b', 2)
            yield delete_thing(b'a'), delete_thing(b'b')
            a, b = yield get_thing(b'a'), get_thing(b'b')
            coro_return((a, b))

        self.assert_equals((None, None), test())

    def test_other_methods(self):
        self.assert_equals(1, self.client.add(self.key_prefix + b'hello', 0))
        self.assert_equals(0, self.client.add(self.key_prefix + b'hello', 0))
        self.assert_equals([self.key_prefix + b'hello'],
                           self.client.add_multi({self.key_prefix + b'hello': 0}))
        self.assert_equals(1, self.client.incr(self.key_prefix + b'hello', 1))
        self.assert_equals(0, self.client.decr(self.key_prefix + b'hello', 1))

        self.assert_equals(1, self.client.replace(self.key_prefix + b'hello', 3))
        self.assert_equals(3, self.client.get(self.key_prefix + b'hello'))

        self.client.incr_multi([self.key_prefix + b'hello'], delta=2)
        self.assert_equals(5, self.client.get(self.key_prefix + b'hello'))

        self.client.append(self.key_prefix + b'hello', b'0')
        self.assert_equals(50, self.client.get(self.key_prefix + b'hello'))

        self.client.prepend(self.key_prefix + b'hello', b'1')
        self.assert_equals(150, self.client.get(self.key_prefix + b'hello'))
