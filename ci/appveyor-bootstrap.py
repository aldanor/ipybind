from __future__ import print_function

import os
import subprocess

try:
    from urllib.request import urlretrieve
except ImportError:
    from urllib import urlretrieve

BASE_URL = "https://www.python.org/ftp/python/"
URLS = {
    ("3.5", "64"): BASE_URL + "3.5.3/python-3.5.3-amd64.exe",
    ("3.5", "32"): BASE_URL + "3.5.3/python-3.5.3.exe",
    ("3.6", "64"): BASE_URL + "3.6.1/python-3.6.1-amd64.exe",
    ("3.6", "32"): BASE_URL + "3.6.1/python-3.6.1.exe",
}

INSTALL_ARGS = ["/quiet", "TargetDir={home}", "Include_pip=1", "Include_launcher=0",
                "Include_doc=0", "Include_test=0", "Include_tcltk=0", "Shortcuts=0"]

INSTALL_CMD = {
    "3.5": [["{path}"] + INSTALL_ARGS],
    "3.6": [["{path}"] + INSTALL_ARGS],
}


def download_file(url, path):
    print("Downloading: {} (into {})".format(url, path))
    progress = [0, 0]

    def report(count, size, total):
        progress[0] = count * size
        if progress[0] - progress[1] > 1000000:
            progress[1] = progress[0]
            print("Downloaded {:,}/{:,} ...".format(progress[1], total))

    dest, _ = urlretrieve(url, path, reporthook=report)
    return dest


def install_python(version, arch, home):
    print("Installing Python", version, "for", arch, "bit architecture to", home)
    if os.path.exists(home):
        return

    path = download_python(version, arch)
    print("Installing", path, "to", home)
    success = False
    for cmd in INSTALL_CMD[version]:
        cmd = [part.format(home=home, path=path) for part in cmd]
        print("Running:", " ".join(cmd))
        try:
            subprocess.check_call(cmd)
        except Exception as exc:
            print("Failed command", cmd, "with:", exc)
            if os.path.exists("install.log"):
                with open("install.log") as fh:
                    print(fh.read())
        else:
            success = True
    if success:
        print("Installation complete!")
    else:
        print("Installation failed")


def download_python(version, arch):
    for _ in range(3):
        try:
            return download_file(URLS[version, arch], "installer.exe")
        except Exception as exc:
            print("Failed to download:", exc)
        print("Retrying ...")


def install_packages(home, *packages):
    cmd = [os.path.join(home, 'Scripts', 'pip.exe'), 'install']
    subprocess.check_call(cmd + list(packages))


if __name__ == "__main__":
    install_python(os.environ['PYTHON_VERSION'], os.environ['PYTHON_ARCH'], os.environ['PYTHON_HOME'])
    install_packages(os.environ['PYTHON_HOME'], 'setuptools', 'wheel', 'tox', 'virtualenv')
