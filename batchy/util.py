import sys

from .local import RunLoopLocal
from .runloop import runloop_coroutine, current_run_loop, deferred, coro_return, future

class _MemoizedLocal(RunLoopLocal):
    def initialize(self):
        self.locals = {}
_MEMOIZED = _MemoizedLocal()

def runloop_memoized_coroutine(*d_args, **d_kwargs):
    """Use this on a coroutine that should be memoized for the duration of the
    run loop.

    For example, if you want to fetch a list, but do so only once per request,
    you can annotate the getter with @runloop_memoized_coroutine."""
    def wrap(fn):
        fn = fn
        fn_id = id(fn)

        @runloop_coroutine()
        def do_call(args, kwargs, lst):
            try:
                v = yield fn(*args, **kwargs)
            except Exception:
                for d in lst:
                    d.set_exception(*sys.exc_info())
                raise
            else:
                for d in lst:
                    d.set_value(v)

                coro_return(v)                

        @runloop_coroutine(*d_args, **d_kwargs)
        def wrapper(*args, **kwargs):
            mgr = _MEMOIZED.locals

            ckey = (fn_id, args, frozenset(kwargs))
            cvalue = mgr.get(ckey, None)
            if cvalue is None:
                lst = list()
                cvalue = mgr[ckey] = [None, lst]
                cvalue[0] = yield future(do_call(args, kwargs, lst))

            d = yield deferred()
            if cvalue[0] is not None and cvalue[0].ready:
                coro_return(cvalue[0].get())
            else:
                cvalue[1].append(d)
                value = yield d
                coro_return(value)

        return wrapper
    return wrap

@runloop_coroutine()
def rmap(fn, *things):
    values = yield list(map(fn, *things))
    coro_return(values)

@runloop_coroutine()
def rfilter(fn, values):
    values = list(values)
    futures = yield rmap(fn, values)
    results = [v for v, f in zip(values, futures) if f]
    coro_return(results)
