import sys

from batchy.local import RunLoopLocal
from batchy.runloop import coro_return, runloop_coroutine, deferred, future, current_run_loop, wait

from . import BaseTestCase

@runloop_coroutine()
def increment(arg):
    coro_return(arg + 1)
    yield

@runloop_coroutine()
def add_2(arg):
    arg = yield increment(arg)
    arg = yield increment(arg)
    coro_return(arg)
    yield

@runloop_coroutine()
def return_none():
    coro_return(None)
    yield

@runloop_coroutine()
def raise_value_error():
    raise ValueError()
    yield  # pylint: disable-msg=W0101

@runloop_coroutine()
def block_loop(n):
    """Blocks the run loop for n iterations."""
    d = yield deferred()

    cnt = [n]
    def unblock(_):
        cnt[0] -= 1
        if cnt[0] == 0:
            d.set_value(1)

    with current_run_loop().on_queue_exhausted.connected_to(unblock):
        yield d

class RunLoopTests(BaseTestCase):
    def test_simple_runnable(self):
        self.assert_equal(1, increment(0))
        self.assert_equal(2, increment(1))

    def test_dependencies(self):
        self.assert_equal(2, add_2(0))
        self.assert_equal(3, add_2(1))

    def test_list_dependencies(self):
        @runloop_coroutine()
        def add_2_parallel(arg):
            arg1, arg2 = yield increment(arg), increment(0)
            coro_return(arg1+arg2)

        self.assert_equal(2, add_2_parallel(0))
        self.assert_equal(3, add_2_parallel(1))

    def test_list_dependency_ordering(self):
        result = []
        @runloop_coroutine()
        def append(x):
            result.append(x)
            yield

        @runloop_coroutine()
        def test():
            yield [append(x) for x in range(100)]

        test()
        self.assert_equals(list(range(100)), result)

    def test_dict_dependencies(self):
        @runloop_coroutine()
        def add_2_dict(arg):
            d = yield {'a': increment(arg), 'b': increment(0), 'c': return_none()}
            self.assert_equal(None, d['c'])
            coro_return(d['a'] + d['b'])

        self.assert_equal(2, add_2_dict(0))
        self.assert_equal(3, add_2_dict(1))

    def test_no_dependencies(self):
        @runloop_coroutine()
        def coro():
            yield

        self.assert_equals(None, coro())

    def test_local(self):
        local = RunLoopLocal()

        @runloop_coroutine()
        def test():
            local.hi = getattr(local, 'hi', 0) + 1
            local.hello = 'boo'
            del local.hello
            coro_return((local.hi, getattr(local, 'hello', None)))
            yield

        def set_something():
            local.hi = 1

        self.assert_raises(RuntimeError, set_something)
        self.assert_equals((1, None), test())
        self.assert_equals((1, None), test())

    def test_exception(self):
        @runloop_coroutine()
        def test(a):
            try:
                yield raise_value_error()
            except ValueError:
                v = yield increment(a)
                coro_return(v)

        self.assert_equals(2, test(1))
        self.assert_equals(3, test(2))

    def test_multiple_exception(self):
        @runloop_coroutine()
        def test(a):
            err = raise_value_error()
            try:
                yield err, block_loop(1)
            except ValueError:
                v = yield increment(a)
                coro_return(v)

        self.assert_equals(2, test(1))
        self.assert_equals(3, test(2))

    def test_deferred_simple(self):
        obj = [None]

        @runloop_coroutine()
        def task():
            obj[0] = d = yield deferred()
            if __debug__:
                self.assert_raises(ValueError, d.get)
            v = yield d
            coro_return(v)

        def set_value(_):
            obj[0].set_value(3)

        @runloop_coroutine()
        def test():
            with current_run_loop().on_queue_exhausted.connected_to(set_value):
                v = yield task()
                coro_return(v)

        self.assert_equal(3, test())

    def test_deferred_easy(self):
        obj = [None]

        @runloop_coroutine()
        def task():
            obj[0] = d = yield deferred()
            d.set_value(3)
            v = yield d
            coro_return(v)

        @runloop_coroutine()
        def test():
            v = yield task()
            coro_return(v)

        self.assert_equal(3, test())

    def test_deferred_exception(self):
        obj = [None]

        @runloop_coroutine()
        def task():
            obj[0] = d = yield deferred()
            v = yield d
            coro_return(v)

        def set_value(_):
            try:
                raise ValueError()
            except ValueError:
                obj[0].set_exception(*sys.exc_info())

        @runloop_coroutine()
        def test():
            with current_run_loop().on_queue_exhausted.connected_to(set_value):
                v = yield task()
                coro_return(v)

        @runloop_coroutine()
        def test2():
            with current_run_loop().on_queue_exhausted.connected_to(set_value):
                x = test()
                try:
                    yield x
                except ValueError:
                    coro_return(1)

        self.assert_raises(ValueError, test)
        self.assert_equals(1, test2())

    def test_block_loop(self):
        total_iterations = [0]
        def inc_total_iterations(_):
            total_iterations[0] += 1

        @runloop_coroutine()
        def test():
            with current_run_loop().on_iteration.connected_to(inc_total_iterations):
                yield block_loop(1)
                yield block_loop(1)
                yield block_loop(1)
                coro_return(1)

        self.assert_equal(1, test())
        self.assert_equal(total_iterations[0], 4-1) # the first loop isn't counted.

    def test_future(self):
        total_iterations = [0]
        def inc_total_iterations(_):
            total_iterations[0] += 1

        @runloop_coroutine()
        def test():
            with current_run_loop().on_iteration.connected_to(inc_total_iterations):
                v1 = yield future(block_loop(1))
                v2 = yield future(block_loop(1))
                v3 = yield future(block_loop(1))

                self.assert_equal(0, total_iterations[0])

                yield v1, v2, v3
                coro_return(1)

        self.assert_equal(1, test())
        self.assert_equal(total_iterations[0], 2-1)

    def test_future_exception(self):
        total_iterations = [0]
        def inc_total_iterations(_):
            total_iterations[0] += 1

        @runloop_coroutine()
        def test():
            with current_run_loop().on_iteration.connected_to(inc_total_iterations):
                exc = yield future(raise_value_error())
                v1 = yield future(block_loop(1))
                v2 = yield future(block_loop(1))
                v3 = yield future(block_loop(1))

                self.assert_equal(0, total_iterations[0])

                try:
                    yield exc
                except ValueError:
                    self.assert_equal(0, total_iterations[0])
                    yield v1, v2, v3
                    coro_return(1)

        self.assert_equal(1, test())
        self.assert_equal(total_iterations[0], 2-1)

    def test_future_exception_ignore(self):
        @runloop_coroutine()
        def test():
            exc, _, _ = yield future(raise_value_error()), future(block_loop(1)), future(block_loop(1))

            try:
                yield exc
            except ValueError:
                raise

        self.assert_raises(ValueError, test)

    def test_ready_wait(self):
        @runloop_coroutine()
        def test():
            d1, d2, d3 = yield deferred(), deferred(), deferred()
            d1.set_value(1)
            d2.set_exception(ValueError())

            ready = yield wait([d1, d2, d3], count=2)
            self.assert_in(d1, ready)
            self.assert_in(d2, ready)

        test()

    def test_wait_until_blocked(self):
        deferreds = []

        def set_value(_):
            deferreds[0].set_value(1)

        @runloop_coroutine()
        def test():
            with current_run_loop().on_queue_exhausted.connected_to(set_value):
                d = yield deferred()
                deferreds.append(d)
                yield wait([d])

        test()  # shouldn't block

    def test_wait_doesnt_change_list(self):
        deferreds = []

        def set_value(_):
            deferreds[0].set_value(1)

        @runloop_coroutine()
        def test():
            with current_run_loop().on_queue_exhausted.connected_to(set_value):
                d = yield deferred()
                deferreds.append(d)
                d2 = yield deferred()
                d2.set_value(2)

                ready = yield wait([d, d2], count=1)
                self.assert_equals(1, len(ready))

                ready2 = yield wait([d], count=1)
                self.assert_equals(1, len(ready))
                self.assert_equals(1, len(ready2))

        test()
