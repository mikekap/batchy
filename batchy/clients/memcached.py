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

    @class_batch_coroutine(0, accepts_kwargs=False)
    def get_multi(self, args_list):
        # args_list is a [(['a', 'b']), (['c', 'd'])]
        keys_to_fetch = frozenset(chain.from_iterable(chain.from_iterable(
            args_list)))
        results = self.client.get_multi(keys_to_fetch)
        coro_return([{k: results[k] for k in lst[0] if k in results}
                     for lst in args_list])
        yield

    @runloop_coroutine()
    def set(self, key, value, time=0):
        yield self.set_multi({key: value}, time=time)

    @class_batch_coroutine(0)
    def set_multi(self, args):
        by_time = defaultdict(dict)
        def fill_by_time(d, time=0):
            by_time[time].update(d)

        for ar, kw in args:
            fill_by_time(*ar, **kw)

        for time, d in iteritems(by_time):
            self.client.set_multi(d, time=time)

        coro_return(None)
        yield

    @runloop_coroutine()
    def delete(self, key):
        yield self.delete_multi([key])

    @class_batch_coroutine(0, accepts_kwargs=False)
    def delete_multi(self, args_list):
        keys_to_delete = frozenset(chain.from_iterable(chain.from_iterable(
            args_list)))
        self.client.delete_multi(keys_to_delete)
        yield

    @runloop_coroutine()
    def add(self, *args, **kwargs):
        coro_return(self.client.add(*args, **kwargs))
        yield

    @runloop_coroutine()
    def incr(self, *args, **kwargs):
        coro_return(self.client.incr(*args, **kwargs))
        yield

    @runloop_coroutine()
    def decr(self, *args, **kwargs):
        coro_return(self.client.decr(*args, **kwargs))
        yield

    @runloop_coroutine()
    def flush_all(self):
        self.client.flush_all()
        yield
