# Using .MetaData()

Some analyses require more complex logic than what .Select() and .Where() can provide. In such cases, the .MetaData() operator allows C++ code to be injected directly into the query, executing as if it were written natively in the EventLoop code. Use of .MetaData() and the following examples is recommended only when specific analysis tasks cannot be achieved with .Select() or .Where(). 

This section is not intended for a first pass through the documentation.

## When to Use .MetaData()

Some values in an analysis are unable to be acquired using the functional style of FuncADL. Some of these cases are as follows:

- An example of this is when the value needed is returned by reference/pointer and not returned by the function. This is a time that the .MetaData() operator is needed.
- Adding a selection tool

TODO: Get more instances from Gordon

## Adding a Basic C++ Function

This example demonstrates how to use FuncADL to inject and run C++ code by implementing a simple function that squares input values. Although squaring a number can easily be done with the .Select() operator, this example uses it to illustrate the basic process of executing C++ code within FuncADL.

The added complexity of injecting a C++ function arises because the .MetaData() operator cannot be used inline like .Select() or .Where() in previous examples. This is due to the need to create a callable function that can be invoked within the FuncADL query. Showing the end result can help illustrate this process:

```python
squared_numbers = (query
    .Select(lambda e: {
        "squared": square(2)
    })
)
```

In this example, the function square() must exist in Python for the query to run without errors. To achieve this, a dummy function is created and linked to a function containing the .MetaData() operator. Both functions must be set up before creating the query.

The first step to setting up these functions is that several additional imports are required, and a type is defined for later use.

```python
import ast
from func_adl import ObjectStream, func_adl_callable
from typing import Tuple, TypeVar
T = TypeVar("T")
```

Next, the dummy function is created and linked to the function that injects .MetaData() into the query using the `@func_adl_callable` decorator. The `square_callable` function will be defined in the following part.

```python
@func_adl_callable(square_callable)
def square(x: int) -> int:
    """Take an input number and return that value squared.

    Args:
        x (int): The value to square

    Returns:
        int: result of squaring the input
    """
    ...
```

Next, a function is defined to add the C++ function to the query. This must be done inside a function rather than directly in the query so that Python can recognize the previously defined function. The function takes the ObjectStream to which .MetaData() is applied, along with an ast.Call object, which is passed through unchanged.

```python
def square_callable(
    s: ObjectStream[T], a: ast.Call
) -> Tuple[ObjectStream[T], ast.Call]:
    new_s = s.MetaData(
        {
            "metadata_type": "add_cpp_function",
            "name": "square",
            "code": [
                "int result = x * x;\n"
            ],
            "result": "result",
            "include_files": [],
            "arguments": ["x"],
            "return_type": "int",
        }
    )
    return new_s, a
```

Next, the .MetaData() operator is called on the current ObjectStream, adding the metadata to the stream. In this case, the metadata being added is the C++ function. When adding a C++ function, the function name, code body, arguments, and return type must be specified.

In this example, the input integer is named x. It is multiplied by itself to produce the squared value, which is assigned to the variable result. The metadata sets result as the output, with a return type of int. It is essential that the dummy function and the C++ function share the same name; otherwise, an error will occur.

With these two functions defined, the target query can now be executed.

This call gives this result for a dataset with 1410 events:

```python
[{squared: 4},
 {squared: 4},
 ...,
 {squared: 4},
 {squared: 4}]
--------------
type: 1410 * {
    squared: int32
}
```

## Adding a C++ Function from an Analysis

The code implemented using the .MetaData() operator is analysis-specific and is therefore not detailed in this documentation. However, an example from an analysis can illustrate how similar code might be structured.

In the example analysis, track summary values are required. The summaryValue() function returns a boolean indicating whether the value exists and provides the value via a reference argument. Because the function does not return the value directly, it cannot be used by FuncADL on its own. A C++ function using .MetaData() is required to access this information.

The following code sets up the function that will be called in the FuncADL query:

```python

from func_adl_servicex_xaodr25.xAOD.trackparticle_v1 import TrackParticle_v1
from func_adl_servicex_xaodr25.xaod import xAOD, add_enum_info

def track_summary_value_callable(
    s: ObjectStream[T], a: ast.Call
) -> Tuple[ObjectStream[T], ast.Call]:
    """The trackSummary method returns true/false if the value is there,
    and alter an argument passed by reference. In short, this isn't functional,
    so it won't work in `func_adl`. This wraps it to make it "work".

    Args:
        s (ObjectStream[T]): The stream we are operating against
        a (ast.Call): The actual call

    Returns:
        Tuple[ObjectStream[T], ast.Call]: Return the updated stream with the metadata code.
    """
    new_s = s.MetaData(
        {
            "metadata_type": "add_cpp_function",
            "name": "track_summary_value",
            "code": [
                "uint8_t result;\n"
                "xAOD::SummaryType st (static_cast<xAOD::SummaryType>(value_selector));\n"
                "if (!(*trk).summaryValue(result, st)) {\n"
                "  result = -1;\n"
                "}\n"
            ],
            "result": "result",
            "include_files": [],
            "arguments": ["trk", "value_selector"],
            "return_type": "int",
        }
    )
    new_s = add_enum_info(new_s, "SummaryType")
    return new_s, a


@func_adl_callable(track_summary_value_callable)
def track_summary_value(trk: TrackParticle_v1, value_selector: xAOD.SummaryType) -> int:
    """Call the `trackSummary` method on a track.

    * Return the value of the value_selector for the track
    * If it isn't present, return -1.

    Args:
        trk (TrackParticle_v1): The track we are operating against
        value_selector (int): Which value (pixel holes, etc.)

    Returns:
        int: Value requested or -1 if not available.
    """
    ...

```

The code to then run this example is as follows:

```python
track_values = (query
    .Select(lambda e: {
       "track_SCTHits": [
            track_summary_value(t, xAOD.SummaryType.numberOfSCTHits)
            for t in e.TrackParticles("InDetTrackParticles")
        ],
    })
)
```