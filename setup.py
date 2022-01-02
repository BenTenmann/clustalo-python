from __future__ import print_function
import sys
if sys.version_info < (3,):
    print('Python 2 has reached end-of-life and is not supported by setriq.')
    sys.exit(-1)
if sys.platform == 'win32' and sys.maxsize.bit_length() == 31:
    print('32-bit Windows Python runtime is not supported. Please switch to 64-bit Python.')
    sys.exit(-1)

import logging
import os
import platform
import shutil
import subprocess
from pathlib import Path

from setuptools import setup, Extension

DIR = Path(__file__).parent

OPENMP_DISABLED = os.environ.get('OPENMP_DISABLED', False)
LIBRARIES = ['clustalo', 'stdc++']


def check_arg_table(system: str) -> bool:
    cmd = {
        'Darwin': ['brew', 'list'],
        'Linux': ['apt', 'list']
    }.get(system, [])

    response = subprocess.check_output(cmd)
    out = 'argtable' in response.decode()
    return out


def download_arg_table(system):
    commands = {
        'Darwin': [['brew', 'install', 'argtable']],
        'Linux': [['sudo', 'apt', 'update'], ['sudo', 'apt', 'install', 'libargtable2', '-y']]
    }.get(system, [[]])

    for cmd in commands:
        subprocess.run(cmd, check=True)


def build_clustal():
    system = platform.system()
    if not check_arg_table(system):
        download_arg_table(system)

    wd = (DIR / 'clustal-omega')
    subprocess.run('./configure --with-pic --with-openmp && make && sudo make install',
                   cwd=wd, check=True)


class BuildFlags:
    _tools_formulae = {
        'Darwin': ('brew', 'libomp'),
    }
    _args = {
        'Darwin': {
            'compiler': ['-Xpreprocessor', '-fopenmp'],
            'linker': ['-lomp']
        }
    }
    _default_args = {
        'compiler': ['-fopenmp'],
        'linker': ['-fopenmp']
    }
    compiler: list
    linker: list

    def __init__(self):
        self._system = platform.system()
        tool, formula = self._tools_formulae.get(self._system, ('apt', 'libomp-dev'))
        args = self._args.get(self._system, self._default_args)

        not_found = self._libomp_check(tool, formula)
        if not_found is not None:
            logging.warning(f'{repr(not_found)} not found -- cannot compile parallelized code')
            for key in args:
                args[key] = []

        for key, val in args.items():
            self.__setattr__(key, val)

    @staticmethod
    def _libomp_check(tool, formula):
        if shutil.which(tool) is None:
            return tool

        formulae = subprocess.check_output([tool, 'list']).decode()
        if formula not in formulae:
            return formula

        return None


def main():
    build_clustal()

    flags = BuildFlags()
    module = Extension('clustalo',
                       sources=['clustalo.c'],
                       include_dirs=['/usr/include/clustalo', '/usr/local/include/clustalo'],
                       library_dirs=['/usr/local/lib'],
                       libraries=LIBRARIES,
                       extra_compile_args=flags.compiler,
                       extra_link_args=flags.linker)

    setup(name='clustalo',
          version='0.1.2',
          description='Python wrapper around libclustalo',
          author='Benchling Engineering',
          author_email='eng@benchling.com',
          url='https://github.com/benchling/clustalo-python',
          ext_modules=[module])


if __name__ == '__main__':
    main()
