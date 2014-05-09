import heapq
from functools import wraps, partial

from .runloop import runloop_coroutine, current_run_loop, deferred, coro_return

class BatchManager(object):
    def __init__(self):
        self.batch_queue = []  # (priority, id)
        self.pending_batches = {}  # {id: (function, [(args, kwargs), ...], [deferred, deferred, ...])}

        current_run_loop().on_queue_exhausted.connect(self._on_queue_exhausted)

    def add(self, id_, function, priority, args_tuple, deferred_obj):
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

        results = yield function(args)
        if results is None:
            results = [None] * len(deferreds)
        for d, r in zip(deferreds, results):
            d.set_value(r)

    def _on_queue_exhausted(self, _):
        if not self.batch_queue:
            return

        current_run_loop().add(self.run_next())


def batch_coroutine(priority=0, accepts_kwargs=True, **kwargs):
    def wrapper(fn):
        fn_id = id(fn)

        @runloop_coroutine(**kwargs)
        @wraps(fn)
        def wrap_kwargs(*args, **kwargs):
            d = yield deferred()
            if not hasattr(current_run_loop(), '_batch_manager'):
                current_run_loop()._batch_manager = BatchManager()

            current_run_loop()._batch_manager.add(fn_id, fn, priority, (args, kwargs), d)

            result = yield d
            coro_return(result)

        @runloop_coroutine(**kwargs)
        @wraps(fn)
        def wrap_no_kwargs(*args):
            d = yield deferred()
            if not hasattr(current_run_loop(), '_batch_manager'):
                current_run_loop()._batch_manager = BatchManager()

            current_run_loop()._batch_manager.add(fn_id, fn, priority, args, d)

            result = yield d
            coro_return(result)

        return wrap_kwargs if accepts_kwargs else wrap_no_kwargs
    return wrapper

def class_batch_coroutine(priority=0, accepts_kwargs=True, **kwargs):
    def wrapper(fn):
        fn_id = id(fn)

        @runloop_coroutine(**kwargs)
        @wraps(fn)
        def wrap_kwargs(self, *args, **kwargs):
            d = yield deferred()
            if not hasattr(current_run_loop(), '_batch_manager'):
                current_run_loop()._batch_manager = BatchManager()

            current_run_loop()._batch_manager.add((fn_id, id(self)),
                                                  partial(fn, self),
                                                  priority, (args, kwargs), d)

            result = yield d
            coro_return(result)

        @runloop_coroutine(**kwargs)
        @wraps(fn)
        def wrap_no_kwargs(self, *args):
            d = yield deferred()
            if not hasattr(current_run_loop(), '_batch_manager'):
                current_run_loop()._batch_manager = BatchManager()

            current_run_loop()._batch_manager.add((fn_id, id(self)),
                                                  partial(fn, self),
                                                  priority, args, d)

            result = yield d
            coro_return(result)

        return wrap_kwargs if accepts_kwargs else wrap_no_kwargs
    return wrapper
