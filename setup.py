import os
import sys

from setuptools import find_packages, setup  # noqa: F401


# Taken from Numba
def _guard_python_version(max_python):
    version_module = None
    try:
        from packaging import version as version_module
    except ImportError:
        try:
            from setuptools._vendor.packaging import version as version_module
        except ImportError:
            pass

    if version_module is None:
        return

    current_python = version_module.parse(".".join(map(str, sys.version_info[:3])))
    max_python = version_module.parse(max_python)

    if not current_python < max_python:
        raise RuntimeError(
            f"Cannot install on Python version {current_python} as Python {max_python}+ is not yet supported."
        )


_guard_python_version(max_python="3.13")

# Use the readme as the long description.
with open("README.md", "r") as fh:
    long_description = fh.read()


extras_require = {
    "test": [
        "pytest",
        "pytest-asyncio",
        "pytest-cov",
        "flake8",
        "coverage",
        "twine",
        "wheel",
        "astunparse",
        "black",
        "isort",
        "numpy",
    ]
}
extras_require["complete"] = sorted(set(sum(extras_require.values(), [])))
extras_require["complete"] = sorted(set(sum(extras_require.values(), [])))

version = os.getenv("func_adl_version")
if version is None:
    import logging

    logging.error("func_adl_version environment variable not set")
    version = "0.0.1a1"
version = version.split("/")[-1]

setup(
    name="func_adl",
    version=version,
    packages=["func_adl", "func_adl/ast"],
    scripts=[],
    description="Functional Analysis Description Language Base Package",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="G. Watts (IRIS-HEP/UW Seattle)",
    author_email="gwatts@uw.edu",
    maintainer="Gordon Watts (IRIS-HEP/UW Seattle)",
    maintainer_email="gwatts@uw.edu",
    url="https://github.com/iris-hep/func_adl",
    license="MIT",
    test_suite="tests",
    install_requires=["make-it-sync"],
    setup_requires=["pytest-runner"],
    tests_require=["pytest>=3.9"],
    extras_require=extras_require,
    classifiers=[
        # "Development Status :: 3 - Alpha",
        # "Development Status :: 4 - Beta",
        "Development Status :: 5 - Production/Stable",
        # "Development Status :: 6 - Mature",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.7",
        "Topic :: Software Development",
        "Topic :: Utilities",
    ],
    data_files=[],
    python_requires=">=3.7",
    platforms="Any",
)
