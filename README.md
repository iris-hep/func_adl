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

## Captured Variables

Python supports closures in `lambda` values and functions. This library will resolve those closures at the point where the select method is called. For example (where `ds` is a dataset):

```python
met_cut = 40
good_met_expr = ds.Where(lambda e: e.met > met_cut).Select(lambda e: e.met)
met_cut = 50
good_met = good_met_expr.value()
```

The cut will be applied at 40, because that was the value of `met_cut` when the `Where` function was called. This will also work for variables captured inside functions.

## Syntatic Sugar

There are several python expressions and idioms that are translated behind your back to `func_adl`. Note that these must occur inside one of the `ObjectStream` method's `lambda` functions like `Select`, `SelectMany`, or `Where`.

|Name | Python Expression | `func_adl` Translation |
--- | --- | --- |
|List Comprehension | `[j.pt() for j in jets]` | `jets.Select(lambda j: j.pt())` |
|List Comprehension | `[j.pt() for j in jets if abs(j.eta()) < 2.4]` | `jets.Where(lambda j: abs(j.eta()) < 2.4).Select(lambda j: j.pt())` |
|List Comprehension | `[j.pt()+e.pt() for j in jets for e in electrons]` | `jets.Select(lambda j: electrons.Select(lambda e: j.pt()+e.pt())` |

Note: Everything that goes for a list comprehension also goes for a generator expression.

## Extensibility

There are two several extensibility points:

- `EventDataset` should be sub-classed to provide an executor.
- `EventDataset` can use Python's type hinting system to allow for editors and other intelligent typing systems to type check expressions. The more type data present, the more the system can help.
- Define a function that can be called inside a LINQ expression
- Define new stream methods
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

The code should work find in python 3.11 or if `from __future__ import annotations` is used.

### Type-based callbacks

By adding a function and a reference in the type system, arbitrary code can be executed during the traversing of the `func_adl`. Keeping the query the same and the `events` definition the same, we can add the info directly to the python type declarations using a decorator for a class definition:

```python
from func_adl import ObjectStream
from typing import TypeVar

# Generic type is required in order to preserve type checkers ability to see
# changes in the type
T = TypeVar('T')

def add_md_for_type(s: ObjectStream[T], a: ast.Call) -> Tuple[ObjectStream[T], ast.AST]:
    return s.MetaData({'hi': 'there'}), a


@func_adl_callback(add_md_for_type)
class dd_event:
    def Jets(self, bank: str) -> Iterable[dd_jet]:
        ...
```

- When the `.Jets()` method is processed, the `add_md_for_type` is called with the current object stream and the ast.
- `add_md_for_type` here adds metadata and returns the updated stream and ast.
- Nothing prevents the function from parsing the AST, removing or adding arguments, adding more complex metadata, or doing any of this depending on the arguments in the call site.

### Parameterized method calls

These are a very special form of callback that were implemented to support things like inter-op for templates in C++. It allows you to write something like:

```python
result = (ds
            .SelectMany(lambda e: e.Jets())
            .Select(lambda j: j.getAttribute[float]('moment0'))
            .AsAwkward('moment0')
)
```

Note the `[float]` in the call to `getAttribute`. This can only happen if the property `getAttribute` in the `Jet` class is marked with the decorator `func_adl_parameterized_call`:

```python
T = TypeVar('T')
def my_callback(s: ObjectStream[T], a: ast.Call, param_1) -> Tuple[ObjectStream[T], ast.AST, Type]:
    ...

class Jet:
    @func_adl_parameterized_call()
    @property
    def getAttribute(self):
        ...
```

Here, `param_1` will be called with set to `float`. Note that this means at the time when this is called the parameterized values must resolve to an actual value - they aren't converted to C++. In this case, the `my_callback` could inject `MetaData` to build a templated call to `getAttribute`. The tuple that `my_callback` returns is the same as for `add_md_for_type` above - except that the third parameter must return the return type of the call.

If more than one argument is used (`j.getAttribute['float','int'])['moment0']`), then `param_1` is a tuple with two items.

### Function Definitions

It is useful to have functions that can be called in the backend directly - or use a function call to artificially insert something into the `func_adl` query stream (like `MetaData`). For example, the C++ backend
uses this to insert inline-C++ code. The `func_adl_callable` decorator is used to do this:

```python
def MySqrtProcessor(s: ObjectStream[T], a: ast.Call) -> Tuple[ObjectStream[T], ast.Call]:
    'Can add items to the object stream'
    new_s = s.MetaData({'j': 'func_stuff'})
    return new_s, a

# Declare the typing and name of the function to func_adl
@func_adl_callable(MySqrtProcessor)
def MySqrt(x: float) -> float:
    ...

r = (events()
        .SelectMany(lambda e: e.Jets('jets'))
        .Select(lambda j: MySqrt(j.eta()))
        .value())
```

In the above sample, the call to `MySqrt` will be passed back to the backend. However, the `MetaData` will be inserted into the stream before the call. One can use C++ do define the `MySqrt` function (or similar).

Note that if `MySqrt` is defined always in the backend with no additional data needed, one can skip the `MySqrtProcessor` in the decorator call.

### Adding new Collection API's

Functions like `First` should not be present in `ObjectStream` as that is the top level set of definitions. However, inside the event context, they make a lot of sense. The type following code needs a way to track these (the type hint system needs no modification, just declare your collections in your `Event` object appropriately).

For examples, see the `test_type_based_replacement` file. The class-level decorator is called `register_func_adl_os_collection`.

## Development

After a new release has been built and passes the tests you can release it by creating a new release on `github`. An action that runs when a release is "created" will send it to `pypi`.
