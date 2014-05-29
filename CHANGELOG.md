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
