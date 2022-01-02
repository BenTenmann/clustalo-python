import logging
import os
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path

from setuptools import setup, Extension

DIR = Path(__file__).parent

OPENMP_DISABLED = os.environ.get('OPENMP_DISABLED', False)
libraries = ['clustalo', 'stdc++']


def download_argtable(system):
    commands = {
        'Darwin': [['brew', 'install', 'argtable']],
        'Linux': [['sudo', 'apt', 'update'], ['sudo', 'apt', 'install', 'libargtable2-dev']]
    }.get(system, [[]])

    for cmd in commands:
        subprocess.run(cmd, check=True)


def build_clustal(system):
    download_argtable(system)
    tmp_dir = tempfile.mkdtemp()

    tar_ball = 'clustal-omega-1.2.4.tar.gz'
    wd = Path(tmp_dir)
    shutil.unpack_archive(DIR / tar_ball, wd)

    subprocess.run('./configure --with-pic --with-openmp && make && sudo make install',
                   cwd=wd / 'clustal-omega-1.2.4', shell=True, check=True)


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

    def __init__(self, system):
        tool, formula = self._tools_formulae.get(system, ('apt', 'libomp-dev'))
        args = self._args.get(system, self._default_args)

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
    system = platform.system()

    build_clustal(system)
    flags = BuildFlags(system)
    module = Extension('clustalo',
                       sources=['clustalo.c'],
                       include_dirs=['/usr/include/clustalo', '/usr/local/include/clustalo'],
                       library_dirs=['/usr/local/lib'],
                       libraries=libraries,
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
