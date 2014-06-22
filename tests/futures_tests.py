from threading import Semaphore
from unittest.case import SkipTest

from batchy.runloop import coro_return, runloop_coroutine
from batchy.batch_coroutine import batch_coroutine, class_batch_coroutine

try:
    from concurrent.futures import ThreadPoolExecutor

    import batchy.futures as batchy_futures
except ImportError:
    batchy_futures = None
    print('Futures not installed; skipping futures tests.')

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

class GeventTests(BaseTestCase):
    def setup(self):
        if not batchy_futures:
            raise SkipTest()

        self.pool = ThreadPoolExecutor(1)

        global CALL_COUNT
        CALL_COUNT = 0

    def test_simple_futures(self):
        sema = Semaphore(0)

        def acq():
            sema.acquire()
            return 1

        @runloop_coroutine()
        def rel():
            sema.release()
            coro_return(2)
            yield

        @runloop_coroutine()
        def test():
            r1, r2 = yield batchy_futures.submit(self.pool, acq), rel()
            coro_return(r1 + r2)

        self.assert_equals(3, test())

    def test_futures_exceptions(self):
        def throw():
            raise ValueError()

        @runloop_coroutine()
        def test():
            yield batchy_futures.submit(self.pool, throw)

        self.assert_raises(ValueError, test)

    def test_batch_with_gevent(self):
        def call_increment(i):
            return increment(i)

        @runloop_coroutine()
        def test():
            a, b = yield batchy_futures.submit(self.pool, call_increment, 2), increment(3)
            coro_return(a + b)

        self.assert_equals(7, test())
        self.assert_equals(2, CALL_COUNT)

    def test_gevent_out_of_order(self):
        def acq(s):
            s.acquire()

        @runloop_coroutine()
        def test():
            s = Semaphore(0)
            future1 = yield batchy_futures.future(self.pool.submit(acq, s))
            future2 = yield batchy_futures.future(self.pool.submit(acq, s))

            s.release()
            yield future1
            s.release()
            yield future2

        test()  # shouldn't hang
