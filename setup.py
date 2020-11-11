# Need setuptools even though it isn't used - loads some plugins.
from setuptools import find_packages  # noqa: F401
from distutils.core import setup

# Use the readme as the long description.
with open("README.md", "r") as fh:
    long_description = fh.read()

extras_require = {
    'test': [
                'pytest', 'pytest-asyncio', 'pytest-cov', 'flake8',
                'coverage', 'twine', 'wheel', 'astunparse'
            ]
                 }
extras_require['complete'] = sorted(set(sum(extras_require.values(), [])))

setup(name="func_adl_test",
      version='0.0.1a1',
      packages=['func_adl', 'func_adl/ast'],
      scripts=[],
      description="Functional Analysis Description Language - For Testing Only",
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
                   "Topic :: Software Development",
                   "Topic :: Utilities",
      ],
      data_files=[],
      python_requires='>=3.6, <3.10',
      platforms="Any",
      )
