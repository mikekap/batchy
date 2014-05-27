import sys

from .runloop import runloop_coroutine, current_run_loop, deferred, coro_return, future

def runloop_memoized_coroutine(*d_args, **d_kwargs):
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
            mgr = getattr(current_run_loop(), '_memoized', None)
            if mgr is None:
                current_run_loop()._memoized = mgr = dict()

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
