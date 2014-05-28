import time
from unittest.case import SkipTest

from batchy.clients.redis import BatchRedisClient
from batchy.runloop import coro_return, runloop_coroutine

from . import BaseTestCase

try:
    import redis

    redis_client = redis.StrictRedis(socket_timeout=1)
    redis_client.get('hello')
except ImportError:
    print('Please install redis to run the redis client tests.')
    redis_client = None
except Exception:
    redis_client = None

class RedisClientTests(BaseTestCase):
    def setup(self):
        if redis_client is None:
            raise SkipTest()

        self.client = BatchRedisClient(redis_client)

        self.key_prefix = '%s|' % (time.time(),)

    def test_simple_get(self):
        @runloop_coroutine()
        def get_thing(t, v):
            a = self.client.delete(self.key_prefix + 'hi' + t)
            b = self.client.set(self.key_prefix + 'hi' + t, v)
            c = self.client.get(self.key_prefix + 'hi' + t)
            _, _, result = yield a, b, c
            coro_return(int(result))

        @runloop_coroutine()
        def test():
            a, b = yield get_thing('a', 1), get_thing('b', 2)
            coro_return(a + b)

        self.assert_equals(3, test())
        
