# -*- coding: utf-8 -*-

import contextlib
import os
import subprocess
import sys

import distutils.errors
import distutils.spawn


class inject:
    def __init__(self, fn):
        self.orig = fn
        self.set(fn)

    def set(self, fn):
        self.fn = fn

    def reset(self):
        self.fn = self.orig

    def __call__(self, *args, **kwargs):
        return self.fn(*args, **kwargs)


def patch_spawn():
    distutils.spawn.spawn = inject(distutils.spawn.spawn)


def spawn_fn(mode, handler=None, log_commands=False):
    def spawn(cmd, search_path=True, verbose=False, dry_run=False):
        cmd = list(cmd)
        if search_path:
            cmd[0] = distutils.spawn.find_executable(cmd[0]) or cmd[0]
        if dry_run:
            return
        if log_commands:
            distutils.log.info(' '.join(distutils.spawn._nt_quote_args(list(cmd))))
        try:
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            out, _ = p.communicate()
            if out:
                out = out.decode('utf-8')
                if handler is not None:
                    out = handler(out) or ''
                if mode == 'always' or (mode == 'on_error' and p.returncode != 0):
                    sep = '-' * 80 + '\n'
                    sys.stdout.write(sep)
                    sys.stdout.write(out)
                    if not out.endswith('\n'):
                        sys.stdout.write('\n')
                    sys.stdout.write(sep)
                    sys.stdout.flush()
            if p.returncode != 0:
                raise subprocess.CalledProcessError(p.returncode, cmd)
        except OSError as e:
            raise distutils.errors.DistutilsExecError(
                'command {!r} failed with exit status {}: {}'
                .format(os.path.basename(cmd[0]), e.errno, e.strerror)) from None
        except:
            raise distutils.errors.DistutilsExecError(
                'command {!r} failed'
                .format(os.path.basename(cmd[0]))) from None
    return spawn


@contextlib.contextmanager
def spawn_capture(mode='on_error', handler=None, log_commands=False):
    distutils.spawn.spawn.set(spawn_fn(mode, handler=handler, log_commands=log_commands))
    try:
        yield
    finally:
        distutils.spawn.spawn.reset()
