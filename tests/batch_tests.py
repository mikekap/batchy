import itertools

from batchy.runloop import coro_return, runloop_coroutine
from batchy.batch_coroutine import batch_coroutine, class_batch_coroutine

from . import BaseTestCase

CALL_COUNT = 0

@batch_coroutine()
def increment(arg_lists):
    def increment_single(n):
        return n + 1

    global CALL_COUNT
    CALL_COUNT += 1
    coro_return([increment_single(*ar, **kw) for ar, kw in arg_lists])
    yield

class BatchClient(object):
    def __init__(self):
        self.get_call_count = 0
        self.set_call_count = 0
        self.run_call_count = 0

    @class_batch_coroutine(1)
    def get(self, arg_lists):
        self.get_call_count += 1
        yield self.run()
        coro_return([0] * len(arg_lists))

    @class_batch_coroutine(1)
    def set(self, _):
        self.set_call_count += 1
        yield self.run()

    @class_batch_coroutine(0)
    def run(self, _):
        self.run_call_count += 1
        yield

    def reset(self):
        self.get_call_count = self.set_call_count = self.run_call_count = 0

class BatchTests(BaseTestCase):
    def setup(self):
        global CALL_COUNT
        CALL_COUNT = 0

    def test_simple_batch(self):
        @runloop_coroutine()
        def test():
            a, b, c = yield increment(1), increment(2), increment(3)
            coro_return((a, b, c))

        self.assert_equals((2,3,4), test())
        self.assert_equals(1, CALL_COUNT)

    def test_multi_clients(self):
        client1, client2 = BatchClient(), BatchClient()

        @runloop_coroutine()
        def sub_1(client):
            rv = yield client.get()
            yield client.set()
            coro_return(rv)

        @runloop_coroutine()
        def sub_2(client):
            rv = yield client.get()
            yield client.set()
            coro_return(rv)

        @runloop_coroutine()
        def test1():
            rv = yield sub_1(client1), sub_2(client2)
            coro_return(rv)

        test1()

        self.assert_equal(1, client1.get_call_count)
        self.assert_equal(1, client1.set_call_count)
        self.assert_equal(2, client1.run_call_count)

        self.assert_equal(1, client2.get_call_count)
        self.assert_equal(1, client2.set_call_count)
        self.assert_equal(2, client2.run_call_count)

        client1.reset()
        client2.reset()

        @runloop_coroutine()
        def test2():
            rv = yield sub_1(client1), sub_2(client1)
            coro_return(rv)

        test2()

        self.assert_equal(1, client1.get_call_count)
        self.assert_equal(1, client1.set_call_count)
        self.assert_equal(2, client1.run_call_count)

        self.assert_equal(0, client2.get_call_count)
        self.assert_equal(0, client2.set_call_count)
        self.assert_equal(0, client2.run_call_count)
