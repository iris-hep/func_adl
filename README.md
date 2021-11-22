# func_adl

 Construct hierarchical data queries using SQL-like concepts in python.

[![GitHub Actions Status](https://github.com/iris-hep/func_adl/workflows/CI/CD/badge.svg)](https://github.com/iris-hep/func_adl/actions)
[![Code Coverage](https://codecov.io/gh/iris-hep/func_adl/graph/badge.svg)](https://codecov.io/gh/iris-hep/func_adl)

[![PyPI version](https://badge.fury.io/py/func-adl.svg)](https://badge.fury.io/py/func-adl)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/func-adl.svg)](https://pypi.org/project/func-adl/)

`func_adl` Uses an SQL like language, and extracts data and computed values from a ROOT file or an ATLAS xAOD file
and returns them in a columnar format. It is currently used as a central part of two of the ServiceX transformers.

This is the base package that has the backend-agnostic code to query hierarchical data. In all likelihood you will want to install
one of the following packages:

- func_adl_xAOD: for running on an ATLAS & CMS experiment xAOD file hosted in ServiceX
- func_adl_uproot: for running on flat root files
- func_adl.xAOD.backend: for running on a local file using docker

See the documentation for more information on what expressions and capabilities are possible in each of these backends.

## Extensibility

There are two several extensibility points:

- `EventDataset` should be sub-classed to provide an executor.
- `EventDataset` can use Python's type system to allow for editors and other intelligent typing systems to type check expressions. The more type data present, the more the system can help.
- It is possible to insert a call back at a function or method call site that will allow for modification of the `ObjectStream` or the call site's `ast`.

### EventDataSet

An example `EventDataSet`:

```python
class events(EventDataset):
    async def execute_result_async(self, a: ast.AST, title: Optional[str] = None):
        await asyncio.sleep(0.01)
        return a
```

and some `func_adl` code that uses it:

```python
    r = (events()
         .SelectMany(lambda e: e.Jets('jets'))
         .Select(lambda j: j.eta())
         .value())
```

- When the `.value()` method is invoked, the `execute_result_async` with a complete `ast` representing the query is called. This is the point that one would send it to the backend to actually be processed.
- Normally, the constructor of `events` would take in the name of the dataset to be processed, which could then be used in `execute_result_async`.

### Typing EventDataset

A minor change to the declaration above, and no change to the query:

```python
class dd_jet:
    def pt(self) -> float:
        ...

    def eta(self) -> float:
        ...

class dd_event:
    def Jets(self, bank: str) -> Iterable[dd_jet]:
        ...
    
    def EventNumber(self, bank='default') -> int
        ...

class events(EventDataset[dd_event]):
    async def execute_result_async(self, a: ast.AST, title: Optional[str] = None):
        await asyncio.sleep(0.01)
        return a
```

This is not required, but when this is done:

- Editors that use types to give one a list of options/guesses will now light up as long as they have reasonable type-checking built in.
- If a required argument is missed, an error will be generated
- If a default argument is missed, it will be automatically filled in.

It should be noted that the type and expression follower is not very sophisticated! While it can follow method calls, it won't follow much else!

### Type-based callbacks

By adding a function and a reference in the type system, arbitrary code can be executed during the traversing of the `func_adl`. Keeping the query the same and the `events` definition the same, we can add the info directly to the python type declarations:

```python
from func_adl import ObjectStream
from typing import TypeVar

# Generic type is required in order to preserve type checkers ability to see
# changes in the type
T = TypeVar('T')

def add_md_for_type(s: ObjectStream[T], a: ast.Call) -> Tuple[ObjectStream[T], ast.AST]:
    return s.MetaData({'hi': 'there'}), a


class dd_event:
    _func_adl_type_info = add_md_for_type

    def Jets(self, bank: str) -> Iterable[dd_jet]:
        ...
```

- When the `.Jets()` method is processed, the `add_md_for_type` is called with the current object stream and the ast.
- `add_md_for_type` here adds metadata and returns the updated stream and ast.
- Nothing prevents the function from parsing the AST, removing or adding arguments, adding more complex metadata, or doing any of this depending on the arguments in the call site.

## Development

After a new release has been built and passes the tests you can release it by creating a new release on `github`. An action that runs when a release is "created" will send it to `pypi`.
