from batchy.runloop import coro_return, runloop_coroutine, future
from batchy.util import runloop_memoized_coroutine, rmap

from . import BaseTestCase

class UtilTestCase(BaseTestCase):
    def test_memoized(self):
        call_count = [0, 0]

        @runloop_memoized_coroutine()
        def memoized(idx):
            call_count[idx] += 1
            coro_return(call_count[idx])
            yield

        @runloop_coroutine()
        def test():
            values = yield memoized(0), memoized(0), memoized(1)
            coro_return(values)

        self.assert_equals([1, 1, 1], test())
        self.assert_equals([1, 1], call_count)

    def test_memoized_exception(self):
        call_count = [0, 0]

        @runloop_memoized_coroutine()
        def memoized(idx):
            call_count[idx] += 1
            raise ValueError(call_count[idx])
            yield

        @runloop_coroutine()
        def test():
            values = yield future(memoized(0)), future(memoized(0)), future(memoized(1))
            result = []
            for i in values:
                try:
                    yield i
                except ValueError as ex:
                    result.append(ex.args[0])
                else:
                    result.append(None)
            coro_return(result)

        self.assert_equals([1, 1, 1], test())
        self.assert_equals([1, 1], call_count)

    def test_rmap(self):
        @runloop_coroutine()
        def do_thing(i):
            coro_return(i+1)
            yield

        self.assert_equals([1,2,3], rmap(do_thing, [0,1,2]))
