import builtins
import re
from collections import deque

from dmoj.executors.compiled_executor import CompiledExecutor
from dmoj.utils.unicode import utf8bytes, utf8text

retraceback = re.compile(r'Traceback \(most recent call last\):\n.*?\n([a-zA-Z_]\w*)(?::[^\n]*?)?$', re.S | re.M)


class PythonExecutor(CompiledExecutor):
    loader_script = '''\
import runpy, sys, os
del sys.argv[0]
sys.stdin = os.fdopen(0, 'r', 65536)
sys.stdout = os.fdopen(1, 'w', 65536)
runpy.run_path(sys.argv[0], run_name='__main__')
'''

    unbuffered_loader_script = '''\
import runpy, sys
del sys.argv[0]
runpy.run_path(sys.argv[0], run_name='__main__')
'''
    address_grace = 131072
    ext = 'py'

    def get_compile_args(self):
        return [self.get_command(), '-m', 'compileall', '-q', self._dir]

    def get_cmdline(self, **kwargs):
        # -B: Don't write .pyc/.pyo, since sandbox will kill those writes
        # -S: Disable site module for speed (no loading dist-packages nor site-packages)
        return [self.get_command(), '-BS' + ('u' if self.unbuffered else ''), self._loader, self._code]

    def get_executable(self):
        return self.get_command()

    def create_files(self, problem_id, source_code, **kwargs):
        super().create_files(problem_id, source_code, **kwargs)
        self._loader = self._file('-loader.py')
        with open(self._code, 'wb') as fo, open(self._loader, 'w') as loader:
            # We want source code to be UTF-8, but the normal (Python 2) way of having
            # "# -*- coding: utf-8 -*-" in header changes line numbers, so we write
            # UTF-8 BOM instead.
            fo.write(b'\xef\xbb\xbf')
            fo.write(utf8bytes(source_code))
            loader.write(self.unbuffered_loader_script if self.unbuffered else self.loader_script)

    def parse_feedback_from_stderr(self, stderr, process):
        if not stderr or len(stderr) > 2048:
            return ''
        match = deque(retraceback.finditer(utf8text(stderr, 'replace')), maxlen=1)
        if not match:
            return ''
        exception = match[0].group(1)
        if exception in builtins.__dict__ and issubclass(builtins.__dict__[exception], BaseException):
            return exception
        else:
            return ''

    @classmethod
    def get_version_flags(cls, command):
        return ['-V']
