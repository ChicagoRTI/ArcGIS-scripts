
from distutils.core import setup
from distutils.extension import Extension
from Cython.Distutils import build_ext
import numpy

e_m1 = Extension('pp.cython.test_cython', [r'pp\cython\test_cython.pyx'])

ext_mods = [e_m1]
  
setup( cmdclass = {'build_ext': build_ext},
      include_dirs=[numpy.get_include()],
      ext_modules = ext_mods
)