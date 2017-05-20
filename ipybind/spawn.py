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


def spawn_fn(mode, fmt=None):
    def spawn(cmd, search_path=True, verbose=False, dry_run=False):
        cmd = list(cmd)
        executable = cmd[0]
        if search_path:
            executable = distutils.spawn.find_executable(executable) or executable
        if dry_run:
            return
        try:
            p = subprocess.Popen([executable] + cmd[1:],
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            out, _ = p.communicate()
            if mode == 'always' or (mode == 'on_error' and p.returncode != 0):
                if fmt is not None:
                    out = fmt(out.decode('utf-8')).encode('utf-8')
                sys.stdout.write(out)
                sys.stdout.flush()
            if p.returncode != 0:
                raise subprocess.CalledProcessError
        except OSError as e:
            raise distutils.errors.DistutilsExecError(
                'command {!r} failed with exit status {}: {}'
                .format(executable, e.errno, e.strerror)) from None
        except:
            raise distutils.errors.DistutilsExecError(
                'command {!r} failed'
                .format(executable)) from None
    return spawn


@contextlib.contextmanager
def spawn_capture(mode='on_error', fmt=None):
    distutils.spawn.spawn.set(spawn_fn(mode, fmt=fmt))
    try:
        yield
    finally:
        distutils.spawn.spawn.reset()
