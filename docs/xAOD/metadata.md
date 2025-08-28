# Using .MetaData()

Some analyses require more complex code to be run than what .Select() and .Where() are able to generate. This is where the .MetaData() operator comes in. Through the use of .MetaData() C++ code can directly be injected into the query and run as if the C++ was written in the EventLoop code.

## Adding a Basic C++ Function

To best illustrate the basics of how to run C++ code with FuncADL this example demonstrates how to implement a C++ function that squares the input values. While squaring a number is something can can be easily done using the .Select() operator, it is a simply operation used to showcase the process of running C++ code.

To use this functionality there are some additional imports:

```python
import ast
from func_adl import ObjectStream, func_adl_callable
from typing import Tuple, TypeVar
```

A new type is also created to be used in the creation of the functions:

```python
T = TypeVar("T")
```

Now the function that setups the C++ code can be setup. Here the function square_callback is create. The reason for the _callback in the function name will be explained later.

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

First the function is defined with the arguments of type ObjectStream[T] and ast.Call. The ObjectStream is what is being passed into and out of each of the operators that are called. The ast.Call is used to facilitate the callable that is setup shortly.

Next, the .MetaData() operator is called on the current ObjectStream. This adds the metadata into the ObjectStream. Here the metadata being added is the C++ Function. When adding a C++ function the function name, code body, arguments, and return types must be defined.

Here the input integer is called x. Then x is multiplied with itself to square it, the int result is assigned that value. In the metadata result is setup to be the result variable. The return type is also set to an int.

To setup to actually be able to call this function in the FuncADL query a dummy function that is call must be setup.

```python
    @func_adl_callable(square_callable)
    def square(x: int) -> int:
        """Take an input number and return that value squared.

        Args:
            x (int): The value to square

        NOTE: This is a dummy function that injects C++ into the object stream to do the
        actual work.

        Returns:
            int: result of squaring the input
        """
        ...
```

Here the @func_adl_callable decorator is used to link the dummy function to the callable function that is setup above. This dummy function is what is called in the FuncADL query.

```python
squared_numbers = (query
    .Select(lambda e: {
        "squared": square(2)
    })
)
```

This simple query will square the number 2 for each event. While not a very useful call it does a good job of simply showing how to call the function that was setup. This call gives this result for a dataset with 1410 events:

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

Note: It is important that the dummy function and the C++ function share the same name or there will be an error.

## Adding a C++ Function from an Analysis

In the analysis used in this example track summary values are required. The summaryValue() function returns a true/false if the value exists, and provides the value by passing it by reference to an argument. This is not a functional design pattern because the value that is wanted is not returned directly by the function. This means that it cannot be used by FuncADL directly and a C++ function using .MetaData() is required to get this information.

The code that is used to setup the function that will be called in the FuncADL query is as follows:

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

    NOTE: This is a dummy function that injects C++ into the object stream to do the
    actual work.

    Returns:
        int: Value requested or -1 if not available.
    """
    ...

```

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

## Adding and Calling a Selection Tool

In the analysis used in the example a jet selection tools must be used to select jets. To do this first the tool needs to be added and then it needs to be called.

To add the tool the metadata_type inject_code can be used. In this analysis multiple jet selection tools are needed so a function will be created to add multiple tools.

```python
def add_jet_selection_tool(
    stream: ObjectStream[T], tool_name: str, cut_name: str
) -> ObjectStream[T]:
    """
    Adds a JetCleaningTool to the given ObjectStream with specified properties.
    This function modifies the metadata of the provided ObjectStream to include
    a JetCleaningTool instance. The tool is initialized with the given name and
    configured with the specified cut level. Declared at a global level.

    Note:
        To access use the following code:

        {tool_name}->keep(*jet);

    Args:
        stream (ObjectStream[T]): The object stream to which the JetCleaningTool
            will be added.
        tool_name (str): The name of the JetCleaningTool instance.
        cut_name (str): The cut level to be set for the JetCleaningTool.
    Returns:
        ObjectStream[T]: The modified object stream with the added JetCleaningTool.
    """
    return stream.MetaData(
        {
            "metadata_type": "inject_code",
            "name": "jet_tool_{tool_name}",
            "header_includes": ["JetSelectorTools/JetCleaningTool.h"],
            "private_members": [f"IJetSelector *{tool_name};"],
            "instance_initialization": [
                f'{tool_name}(new JetCleaningTool("{tool_name}"))'
            ],
            # TODO: These should be in the initialize command, with an ANA_CHECK.
            "initialize_lines": [
                f'ANA_CHECK(asg::setProperty({tool_name}, "CutLevel", "{cut_name}"));',
                f"ANA_CHECK({tool_name}->initialize());",
            ],
            "link_libraries": ["JetSelectorToolsLib"],
        }
    )
```

This can be implemented into our query:

```python
query = FuncADLQueryPHYS()
query_with_tool = add_jet_selection_tool(
    query, "m_jetCleaning_llp", "LooseBadLLP"
)
```

Then there needs to be a way to use the tool. This requires adding a C++ function.

```python
def jet_clean_llp_callback(
    s: ObjectStream[T], a: ast.Call
) -> Tuple[ObjectStream[T], ast.Call]:
    new_s = s.MetaData(
        {
            "metadata_type": "add_cpp_function",
            "name": "jet_clean_llp",
            "code": ["bool result = m_jetCleaning_llp->keep(*jet)"],
            "result": "result",
            "include_files": [],
            "arguments": ["jet"],
            "return_type": "bool",
        }
    )
    return new_s, a


@func_adl_callable(jet_clean_llp_callback)
def jet_clean_llp(jet: Jet_v1) -> bool:
    """Call the jet selection on the jet.

    * return true or false if the jet passes the selection cut.

    Args:
        jet (Jet_v1): The jet we are operating against
        value_selector (int): Which value (pixel holes, etc.)

    NOTE: This is a dummy function that injects C++ into the object stream to do the
    actual work.

    Returns:
        bool: Did the jet pass?
    """
    ...
```

TODO: Add the rest of the code. This will require some more stuff in the .select() page.