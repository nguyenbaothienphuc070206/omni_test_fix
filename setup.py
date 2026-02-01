from setuptools import setup, Extension
from Cython.Build import cythonize
import numpy
import os

# Define extensions for the sovereign financial system
extensions = [
    # Core Math Kernels (HPC)
    Extension(
        name="math_core",
        sources=["math_core.pyx"],
        include_dirs=[numpy.get_include()],
        # Enable OpenMP for parallel execution
        extra_compile_args=["/openmp" if os.name == 'nt' else "-fopenmp", "-O3"],
        extra_link_args=["/openmp" if os.name == 'nt' else "-fopenmp"],
        define_macros=[("NPY_NO_DEPRECATED_API", "NPY_1_7_API_VERSION")]
    ),
    # Optimized Data Models (Extension Types)
    Extension(
        name="data_models",
        sources=["data_models.pyx"],
        include_dirs=[numpy.get_include()],
        extra_compile_args=["-O3"],
        # language="c" # Removing language=c to allow standard cython compilation
    ),
    Extension(
        name="preprocessing.ingestor",
        sources=["preprocessing/ingestor.pyx"],
        extra_compile_args=["-O3"]
    )
]

setup(
    name="project_omni_hpc",
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
