from setuptools import find_packages
from distutils.core import setup

# Use the readme as the long description.
with open("README.md", "r") as fh:
    long_description = fh.read()

setup(name="func_adl",
      version='1.0.0-alpha.5',
      packages=find_packages(exclude=['tests']),
      scripts=[],
      description="Functional Analysis Description Language Base Package",
      long_description=long_description,
      long_description_content_type="text/markdown",
      author="G. Watts (IRIS-HEP/UW Seattle)",
      author_email="gwatts@uw.edu",
      maintainer="Gordon Watts (IRIS-HEP/UW Seattle)",
      maintainer_email="gwatts@uw.edu",
      url="https://github.com/iris-hep/func_adl",
      license="TBD",
      test_suite="tests",
      install_requires=[],
      setup_requires=["pytest-runner"],
      tests_require=["pytest>=3.9"],
      classifiers=[
                   # "Development Status :: 1 - Planning",
                   "Development Status :: 2 - Pre-Alpha",
                   # "Development Status :: 3 - Alpha",
                   # "Development Status :: 4 - Beta",
                   # "Development Status :: 5 - Production/Stable",
                   # "Development Status :: 6 - Mature",
                   "Intended Audience :: Developers",
                   "Intended Audience :: Information Technology",
                   "Programming Language :: Python",
                   "Programming Language :: Python :: 3.7",
                   "Topic :: Software Development",
                   "Topic :: Utilities",
      ],
      data_files=[],
      python_requires='>=3.6',
      platforms="Any",
      )
