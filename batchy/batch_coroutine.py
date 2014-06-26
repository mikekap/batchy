import heapq
from functools import wraps, partial
import sys

from .local import RunLoopLocal
from .runloop import runloop_coroutine, current_run_loop, deferred, coro_return, requires_runloop
from .context import runloop_coroutine_with_context
from .hook import add_hook

BATCH_MANAGER_HOOK_PRIORITY = 10

class BatchManager(object):
    def __init__(self):
        self.batch_queue = []  # (priority, id)
        self.pending_batches = {}  # {id: (function, [(args, kwargs), ...], [deferred, deferred, ...])}

    def add(self, id_, function, priority, args_tuple, deferred_obj):
        add_hook(BATCH_MANAGER_HOOK_PRIORITY, self._on_queue_exhausted)

        if id_ not in self.pending_batches:
            heapq.heappush(self.batch_queue, (-priority, id_))
            self.pending_batches[id_] = (function, [args_tuple], [deferred_obj])
        else:
            _, arg_list, deferred_list = self.pending_batches[id_]
            arg_list.append(args_tuple)
            deferred_list.append(deferred_obj)

    @runloop_coroutine()
    def run_next(self):
        _, id_ = heapq.heappop(self.batch_queue)
        function, args, deferreds = self.pending_batches.pop(id_)

        try:
            results = yield function(args)
        except Exception:
            exc_info = sys.exc_info()
            for d in deferreds:
                d.set_exception(*exc_info)
        else:
            if results is None:
                results = [None] * len(deferreds)

            assert len(results) == len(deferreds), \
                'Batch function %s did not return enough results' % (function)

            for d, r in zip(deferreds, results):
                d.set_value(r)

        if self.batch_queue:
            add_hook(BATCH_MANAGER_HOOK_PRIORITY, self._on_queue_exhausted)

    def _on_queue_exhausted(self):
        current_run_loop().add(self.run_next())


class BatchManagerLocal(RunLoopLocal):
    def initialize(self):
        self.batch_manager = BatchManager()

BATCH_MANAGER = BatchManagerLocal()

@requires_runloop()
def _batch_defer(fn_id, fn, priority, args):
    d = yield deferred()

    BATCH_MANAGER.batch_manager.add(fn_id, fn, priority, args, d)

    result = yield d
    coro_return(result)

def batch_coroutine(priority=0, accepts_kwargs=True, **kwargs):
    def wrapper(fn):
        fn_id = id(fn)

        @runloop_coroutine_with_context(**kwargs)
        @wraps(fn)
        def wrap_kwargs(*args, **kwargs):
            return _batch_defer(fn_id, fn, priority, (args, kwargs))

        @runloop_coroutine_with_context(**kwargs)
        @wraps(fn)
        def wrap_no_kwargs(*args):
            return _batch_defer(fn_id, fn, priority, args)

        return wrap_kwargs if accepts_kwargs else wrap_no_kwargs
    return wrapper

def class_batch_coroutine(priority=0, accepts_kwargs=True, **kwargs):
    def wrapper(fn):
        fn_id = id(fn)

        @runloop_coroutine_with_context(**kwargs)
        @wraps(fn)
        def wrap_kwargs(self, *args, **kwargs):
            return _batch_defer((fn_id, id(self)),
                                partial(fn, self),
                                priority, (args, kwargs))

        @runloop_coroutine_with_context(**kwargs)
        @wraps(fn)
        def wrap_no_kwargs(self, *args):
            return _batch_defer((fn_id, id(self)),
                                partial(fn, self),
                                priority, args)

        return wrap_kwargs if accepts_kwargs else wrap_no_kwargs
    return wrapper
