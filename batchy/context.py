"""Support for "contexts" between that propagate between coroutines.

These are a little like thread-locals, in that they implicitly propagate,
but the propagation is controlled - a simple @clears_context will remove
contexts from any coroutines that the current coroutine calls.

This can be useful if implementing microservices - inter-service calls
must pass all parameters explicitly, but intra-service calls get a shared
context.
"""

from functools import wraps

from .compat import is_nextable
from .local import RunLoopLocal
from .runloop import runloop_coroutine, requires_runloop

class _Context(object):
    """Empty object that is used as the context."""
    pass

class _ContextLocal(RunLoopLocal):
    def initialize(self):
        self.context = None

_CURRENT_CONTEXT = _ContextLocal()

def runloop_coroutine_with_context(new_context=False, **dec_kwargs):
    def wrap(fn):
        # Used to wrap the methods below
        def _with_context(method):
            @wraps(method)
            def method_wrapper(self, *args, **kwargs):
                old_value, _CURRENT_CONTEXT.context = _CURRENT_CONTEXT.context, self._ctx
                try:
                    return method(self, *args, **kwargs)
                finally:
                    self._ctx, _CURRENT_CONTEXT.context = _CURRENT_CONTEXT.context, old_value
            return method_wrapper

        @runloop_coroutine(**dec_kwargs)
        class Wrapper(object):
            def __init__(self, *args, **kwargs):
                if new_context:
                    self._ctx = _CURRENT_CONTEXT.context = _Context()
                else:
                    self._ctx = _CURRENT_CONTEXT.context
                self._it = fn(*args, **kwargs)
                assert is_nextable(self._it), '%s did not return an iterator' % (fn)

            @_with_context
            def __next__(self):
                return next(self._it)

            next = __next__

            @_with_context
            def send(self, *args, **kwargs):
                return self._it.send(*args, **kwargs)

            @_with_context
            def throw(self, *args, **kwargs):
                return self._it.throw(*args, **kwargs)

            # Useful for .ready, .on_add_to_loop, .set_value, etc.
            # This isn't possible without a custom coroutine (i.e. a class),
            # but we want to support that anyway.
            def __getattr__(self, name):
                return getattr(self._it, name)

        # wraps(fn)(Wrapper) doesn't work because __doc__ is immutable on
        # classes. wraps(fn)(partial(Wrapper)) breaks in magnificent ways.
        #pylint: disable-msg=W0108
        return wraps(fn)(lambda *args, **kwargs: Wrapper(*args, **kwargs))
    return wrap

@requires_runloop()
def get_context():
    ctx = _CURRENT_CONTEXT.context
    assert ctx, 'Not running in a context. Did you use @runloop_coroutine_clears_context ?'
    return ctx

def runloop_coroutine_begin_context(**kwargs):
    def wrap(fn):
        return runloop_coroutine_with_context(new_context=True, **kwargs)(fn)
    return wrap
