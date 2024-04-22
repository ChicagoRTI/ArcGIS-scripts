
from setuptools import setup
from Cython.Build import cythonize


ext_modules=cythonize(r'pp\cython\main.pyx', annotate=True, compiler_directives={'boundscheck': False, 'wraparound': False})

setup(
    name='Main',
    ext_modules=ext_modules
)


