from collections import defaultdict
from itertools import chain

from ..compat import iteritems, itervalues
from ..runloop import coro_return, runloop_coroutine
from ..batch_coroutine import class_batch_coroutine

class BatchMemcachedClient(object):
    def __init__(self, real_client):
        self.client = real_client

    @runloop_coroutine()
    def get(self, k):
        results = yield self.get_multi([k])
        coro_return(next(itervalues(results), None))

    @class_batch_coroutine(0)
    def get_multi(self, args_list):
        """get_multi(iterable_of_keys, key_prefix=b'')"""
        saved_key_lists = []
        for args, kwargs in args_list:
            assert len(args) == 1, 'get_multi only accepts a single argument: ' + args
            key_prefix = kwargs.pop('key_prefix', b'')
            assert not kwargs, 'get_multi only accepts the `key_prefix` kwarg'

            # In case args[0] is a generator, save the entire list for later merging.
            saved_key_lists.append([key_prefix + k for k in args[0]])

        results = self.client.get_multi(frozenset(chain.from_iterable(saved_key_lists)))
        coro_return([{k: results[k] for k in lst if k in results}
                     for lst in saved_key_lists])
        yield  # pragma: no cover

    @runloop_coroutine()
    def set(self, key, value, time=0):
        failed = yield self.set_multi({key: value}, time=time)
        coro_return(key not in failed)

    @class_batch_coroutine(0)
    def set_multi(self, args):
        """set_multi(dict, key_prefix=b'', time=0)"""
        coro_return(self._do_set_command(self.client.set_multi, args))
        yield  # pragma: no cover

    @runloop_coroutine()
    def delete(self, key, time=None):
        yield self.delete_multi([key], time=time)

    @class_batch_coroutine(0)
    def delete_multi(self, args_list):
        """delete_multi(iterable, time=0, key_prefix=b'')"""
        by_time = defaultdict(set)
        def fill_by_time(it, key_prefix=b'', time=None):
            by_time[time].update(key_prefix + k for k in it)

        for ar, kw in args_list:
            fill_by_time(*ar, **kw)

        for time, d in iteritems(by_time):
            self.client.delete_multi(d, **({'time': time} if time is not None else {}))

        coro_return(None)
        yield  # pragma: no cover

    @runloop_coroutine()
    def add(self, key, value, time=0):
        failed = yield self.add_multi({key: value}, time=time)
        coro_return(key not in failed)

    @class_batch_coroutine(0)
    def add_multi(self, args_list):
        """add_multi(dict, key_prefix=b'', time=0)"""
        coro_return(self._do_set_command(self.client.add_multi, args_list))
        yield  # pragma: no cover

    def _do_set_command(self, fn, args):
        """add & set implementation."""
        by_time = defaultdict(dict)
        def fill_by_time(d, key_prefix=b'', time=0):
            by_time[time].update((key_prefix + k, v) for k, v in iteritems(d))

        for ar, kw in args:
            fill_by_time(*ar, **kw)

        failed_keys = frozenset(chain.from_iterable(
            fn(d, time=time)
            for time, d in iteritems(by_time)))

        return [list(failed_keys & frozenset(ar[0].keys())) for ar, _ in args]

    @runloop_coroutine()
    def incr(self, *args, **kwargs):
        coro_return(self.client.incr(*args, **kwargs))
        yield  # pragma: no cover

    @runloop_coroutine()
    def incr_multi(self, *args, **kwargs):
        """pylibmc's incr_multi is NOT a superset of incr - it does not return the new value."""
        coro_return(self.client.incr_multi(*args, **kwargs))
        yield  # pragma: no cover

    @runloop_coroutine()
    def decr(self, *args, **kwargs):
        coro_return(self.client.decr(*args, **kwargs))
        yield  # pragma: no cover

    @runloop_coroutine()
    def replace(self, *args, **kwargs):
        coro_return(self.client.replace(*args, **kwargs))
        yield  # pragma: no cover

    @runloop_coroutine()
    def append(self, *args, **kwargs):
        coro_return(self.client.append(*args, **kwargs))
        yield  # pragma: no cover

    @runloop_coroutine()
    def prepend(self, *args, **kwargs):
        coro_return(self.client.prepend(*args, **kwargs))
        yield  # pragma: no cover

    @runloop_coroutine()
    def flush_all(self):
        self.client.flush_all()
        yield  # pragma: no cover
