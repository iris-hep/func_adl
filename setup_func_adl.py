# Need setuptools even though it isn't used - loads some plugins.
from setuptools import find_packages  # noqa: F401
from distutils.core import setup
import os

# Use the readme as the long description.
with open("README.md", "r") as fh:
    long_description = fh.read()

extras_require = {'develop': ['pytest', 'pytest-cov', 'flake8', 'coverage', 'twine']}
extras_require['complete'] = sorted(set(sum(extras_require.values(), [])))

version = os.getenv('func_adl_version')
if version is None:
    raise Exception('func_adl_version env var is not set')
version = version.split('/')[-1]

setup(name="func_adl",
      version=version,
      packages=['func_adl'],
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
      install_requires=["make-it-sync"],
      setup_requires=["pytest-runner"],
      tests_require=["pytest>=3.9"],
      extras_require=extras_require,
      classifiers=[
                   # "Development Status :: 3 - Alpha",
                   # "Development Status :: 4 - Beta",
                   # "Development Status :: 5 - Production/Stable",
                   # "Development Status :: 6 - Mature",
                   "Intended Audience :: Developers",
                   "Intended Audience :: Information Technology",
                   "Programming Language :: Python",
                   "Programming Language :: Python :: 3.7",
                   "Programming Language :: Python :: 3.6",
                   "Topic :: Software Development",
                   "Topic :: Utilities",
      ],
      data_files=[],
      python_requires='>=3.6, <3.8',
      platforms="Any",
      )
