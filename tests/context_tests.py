from batchy.context import runloop_coroutine_with_context, runloop_coroutine_begin_context, get_context
from batchy.runloop import coro_return

from . import BaseTestCase

@runloop_coroutine_with_context()
def return_context(f):
    coro_return(getattr(get_context(), f, None))
    yield

class ContextTestCase(BaseTestCase):
    def test_context_propagate(self):
        @runloop_coroutine_with_context()
        def test_ctx(n):
            get_context().a = n
            self.assert_equals(n, (yield return_context('a')))

        @runloop_coroutine_begin_context()
        def test():
            yield test_ctx(1)
            self.assert_equals(1, (yield return_context('a')))
            self.assert_equals(1, get_context().a)

        test()

    def test_context_shared_state(self):
        @runloop_coroutine_with_context()
        def set_ctx(n):
            get_context().a = n
            yield

        @runloop_coroutine_begin_context()
        def test():
            yield set_ctx(3)
            self.assert_equals(3, (yield return_context('a')))
            self.assert_equals(3, get_context().a)

        test()

    def test_context_clear(self):
        @runloop_coroutine_begin_context()
        def cleared_return_context(f):
            coro_return(getattr(get_context(), f, None))
            yield

        @runloop_coroutine_begin_context()
        def test():
            self.assert_is_none((yield cleared_return_context('a')))
            get_context().a = 3
            self.assert_is_none((yield cleared_return_context('a')))

        test()

    def test_context_uncleared(self):
        @runloop_coroutine_with_context()
        def test():
            self.assert_raises(AssertionError, get_context)
            yield

        test()
