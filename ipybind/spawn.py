# -*- coding: utf-8 -*-

import contextlib
import os
import subprocess
import sys

import distutils.errors
import distutils.spawn


def spawn_fn(stdout, stderr):
    stdout = stdout and subprocess.PIPE or subprocess.DEVNULL
    stderr = stderr and subprocess.PIPE or subprocess.DEVNULL

    def spawn(cmd, search_path=True, verbose=False, dry_run=False):
        cmd = list(cmd)
        executable = cmd[0]
        if search_path:
            executable = distutils.spawn.find_executable(executable) or executable
        if os.name == 'nt':
            cmd = distutils.spawn._nt_quote_args(cmd)
        if dry_run:
            return
        try:
            p = subprocess.Popen([executable] + cmd[1:], stdout=stdout, stderr=stderr)
            out, err = p.communicate()
            if out is not None:
                sys.stdout.write(out)
            if err is not None:
                sys.stderr.write(err)
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
def spawn_capture(stdout=False, stderr=False):
    orig_spawn = distutils.spawn.spawn
    distutils.spawn.spawn = spawn_fn(stdout, stderr)
    try:
        yield
    finally:
        distutils.spawn.spawn = orig_spawn
