from batchy.runloop import coro_return, runloop_coroutine, deferred, future, current_run_loop

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

    def test_deferred_simple(self):
        obj = [None]

        @runloop_coroutine()
        def task():
            obj[0] = d = yield deferred()
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
