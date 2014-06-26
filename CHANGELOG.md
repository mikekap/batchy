## 0.3
Features:
 - Contexts: coroutine-propagating locals. These work correctly in the presence of context-switching yields.
 - Added batchy.coro: a shorthand for the "default" @decorator to use on batchy functions; in case we ever need to change it.
   - Please migrate to this if you're using batchy! Coroutine-locals don't work correctly with the old @runloop_coroutine decorator.
 - Add ability to use gevent in the redis client - to parallelize io.
 - Better support more pylibmc features (unfortunately just support; they are not batched)
 - Add wait function which waits for k/n batchy futures (or deferreds, but you should never see those).
 - Support `return` in py3.
 - Add support to explicitly switch the thread-local implementation - greenlets and threads are available.
 - Support for using waiting on concurrent.futures .

Bugfixes:
 - coverage reports work better locally.
 - even earlier yelling about functions not returning generators.

## 0.2

Features:
  - Python 3 support. The next release will support using the regular `return` statement in python 3.
  - Add @runloop_memoized_coroutine, @rmap and @rfilter (in batchy.util).
  - Create a common RunLoopLocal class.
  - Tox testing config & integration with Travis.

Bugfixes:
  - tests.py now correctly returns a non-zero exit code when the tests fail.
  - yielding non-generators/deferreds now raises errors a lot earlier (with a root cause)

## 0.1

Initial release
