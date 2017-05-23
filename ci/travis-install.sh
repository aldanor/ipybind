#!/usr/bin/env sh

if [[ "$(uname -s)" == "Darwin" ]]; then
    brew update || brew update
    (brew list | grep -q pyenv) || brew install pyenv
    brew outdated pyenv || brew upgrade pyenv
    if which -s pyenv; then
        eval "$(pyenv init -)"
    fi
    case "${TOXENV}" in
        py34) pyenv install 3.4.6 && pyenv global 3.4.6 ;;
        py35) pyenv install 3.5.3 && pyenv global 3.5.3 ;;
        py36) pyenv install 3.6.1 && pyenv global 3.6.1 ;;
    esac
    pyenv rehash
    python -m pip install --user virtualenv
else
    pip install virtualenv
fi
python -m virtualenv ~/.venv
source ~/.venv/bin/activate
pip install -U tox
