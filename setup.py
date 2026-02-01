from setuptools import setup, Extension
from Cython.Build import cythonize
import numpy
import os

# Define extensions for the sovereign financial system
extensions = [
    # Core Math Kernels (HPC)
    Extension(
        name="aegis_math",
        sources=["aegis_math.pyx"],
        include_dirs=[numpy.get_include()],
        # Enable OpenMP for parallel execution
        extra_compile_args=["/openmp" if os.name == 'nt' else "-fopenmp", "-O3"],
        extra_link_args=["/openmp" if os.name == 'nt' else "-fopenmp"],
        define_macros=[("NPY_NO_DEPRECATED_API", "NPY_1_7_API_VERSION")]
    ),
    # Optimized Data Models (Extension Types)
    Extension(
        name="aegis_types",
        sources=["aegis_types.pyx"],
        include_dirs=[numpy.get_include()],
        extra_compile_args=["-O3"],
        # language="c" # Removing language=c to allow standard cython compilation
    ),
    Extension(
        name="intake.decoder",
        sources=["intake/decoder.pyx"],
        extra_compile_args=["-O3"]
    )
]

setup(
    name="aegis_hpc",
    ext_modules=cythonize(
        extensions,
        compiler_directives={
            'language_level': "3",
            'boundscheck': False,
            'wraparound': False,
            'cdivision': True,
            'initializedcheck': False
        }
    ),
)
