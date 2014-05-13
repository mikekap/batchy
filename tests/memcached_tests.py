from unittest.case import SkipTest

from batchy.runloop import coro_return, runloop_coroutine
from batchy.clients.memcached import BatchMemcachedClient

from . import BaseTestCase

try:
    import pylibmc

    mc_client = pylibmc.Client(["127.0.0.1"], behaviors={
        'connect_timeout': 1
    })
    mc_client.get('hello')
except ImportError:
    print 'Please install pylibmc to run the memcached client tests.'
    mc_client = None
except Exception:
    mc_client = None

class MemcachedClientTests(BaseTestCase):
    def setup(self):
        if mc_client is None:
            raise SkipTest()

        self.client = BatchMemcachedClient(mc_client)

    def test_multi_get(self):
        @runloop_coroutine()
        def set_thing(a, b):
            yield self.client.set('hi' + a, b, time=100)

        @runloop_coroutine()
        def get_thing(a):
            v = yield self.client.get('hi' + a)
            coro_return(v)

        @runloop_coroutine()
        def test():
            yield set_thing('a', 1), set_thing('b', 2)
            a, b = yield get_thing('a'), get_thing('b')
            coro_return(a + b)

        self.assert_equals(3, test())


    def test_multi_delete(self):
        @runloop_coroutine()
        def set_thing(a, b):
            yield self.client.set('hi' + a, b, time=100)

        @runloop_coroutine()
        def get_thing(a):
            v = yield self.client.get('hi' + a)
            coro_return(v)

        @runloop_coroutine()
        def delete_thing(a):
            yield self.client.delete('hi' + a)

        @runloop_coroutine()
        def test():
            yield set_thing('a', 1), set_thing('b', 2)
            yield delete_thing('a'), delete_thing('b')
            a, b = yield get_thing('a'), get_thing('b')
            coro_return((a, b))

        self.assert_equals((None, None), test())
