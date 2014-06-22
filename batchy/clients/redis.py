from itertools import starmap

from ..runloop import coro_return, runloop_coroutine
from ..batch_coroutine import class_batch_coroutine

@runloop_coroutine()
def call_fn(fn, *args, **kwargs):
    coro_return(fn(*args, **kwargs))
    yield

class BatchRedisClient(object):
    def __init__(self, redis_client, spawn_fn=call_fn):
        """Create a new batchy redis client.

         - redis_client: The underlying Redis/StrictRedis object
         - spawn_fn: the runloop coro to use when running
           pipeline.execute(); useful if you want concurrent
           calls to multiple backends (e.g. memcached, redis, db, etc)
        """
        self.redis = redis_client
        self.spawn_fn = spawn_fn

    def pipeline(self):
        raise NotImplementedError("There isn't much reason to use a pipeline "
                                  "in batch mode - it is used under the hood.")

    def brpop(self, key, timeout=0):
        raise NotImplementedError("Blocking not implemented.")

    def blpop(self, key, timeout=0):
        raise NotImplementedError("Blocking not implemented.")

    def _wrap_redis_method(self, name):
        @runloop_coroutine()
        def method(*args, **kwargs):
            result = yield self._batch_call(name, args, kwargs)
            coro_return(result)
        return method

    def __getattr__(self, name):
        method = self._wrap_redis_method(name)
        setattr(self, name, method)
        return method

    @class_batch_coroutine(0, accepts_kwargs=False)
    def _batch_call(self, args_list):
        pipeline = self.redis.pipeline()

        def call_on_pipeline(name, args, kwargs):
            getattr(pipeline, name)(*args, **kwargs)
        list(starmap(call_on_pipeline, args_list))

        coro_return((yield self.spawn_fn(pipeline.execute)))
