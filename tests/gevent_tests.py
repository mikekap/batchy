from unittest.case import SkipTest

from batchy.runloop import coro_return, runloop_coroutine
from batchy.batch_coroutine import batch_coroutine, class_batch_coroutine

try:
    import gevent
    from gevent.coros import Semaphore

    import batchy.gevent as batchy_gevent
except ImportError:
    batchy_gevent = None
    print('Gevent not installed; skipping gevent tests.')

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
        if not batchy_gevent:
            raise SkipTest()

        # Quiet gevent's internal exception printing.
        self.old_print_exception = gevent.get_hub().print_exception
        gevent.get_hub().print_exception = lambda context, type, value, tb: None

        global CALL_COUNT
        CALL_COUNT = 0

    def tear_down(self):
        gevent.get_hub().print_exception = self.old_print_exception

    def test_simple_gevent(self):
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
            r1, r2 = yield batchy_gevent.spawn(acq), rel()
            coro_return(r1 + r2)

        self.assert_equals(3, test())

    def test_gevent_exceptions(self):
        def throw():
            raise ValueError()

        @runloop_coroutine()
        def test():
            yield batchy_gevent.spawn(throw)

        self.assert_raises(ValueError, test)

    def test_batch_with_gevent(self):
        def call_increment(i):
            return increment(i)

        @runloop_coroutine()
        def test():
            a, b = yield batchy_gevent.spawn(call_increment, 2), increment(3)
            coro_return(a + b)

        self.assert_equals(7, test())
        self.assert_equals(2, CALL_COUNT)

    def test_gevent_out_of_order(self):
        def acq(s):
            s.acquire()

        @runloop_coroutine()
        def test():
            s = Semaphore(0)
            future1 = yield batchy_gevent.greenlet_future(gevent.spawn(acq, s))
            future2 = yield batchy_gevent.greenlet_future(gevent.spawn(acq, s))

            s.release()
            yield future1
            s.release()
            yield future2

        test()  # shouldn't hang
