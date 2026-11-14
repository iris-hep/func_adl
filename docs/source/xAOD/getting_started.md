# Getting Started with xAOD

This section of the FuncADL documentation will cover:

- How to set up the environment to access xAOD data in ATLAS
- Access methods, attributes, and decorations on the xAOD Event Data Model (EDM).

This section assumes you have the following prerequisite knowledge:

- You have all the knowledge outlined in the ServiceX User Guide
- Basic knowledge of the ATLAS xAOD data model (at the level of a standard ATLAS tutorial)
- The names of the xAOD collections you are interested in, etc.

:::{seealso}
If you have not worked through it please see the [ServiceX User Guide](https://tryservicex.org/reference/yamlfeatures/) to get foundational knowledge or ServiceX before completing this user guide.
:::

This User Guide will give an understanding of how to build the queries that are passed to ServiceX.

## FuncADL xAOD Releases

Depending on what ATLAS release is needed, it is required to install and import different libraries. The libraries are:

- ``func_adl_servicex_xaodr21``
- ``func_adl_servicex_xaodr22``
- ``func_adl_servicex_xaodr25``

These can be installed using `pip`.

## Importing Query Function

All of the queries that are built in this user guide use a function to start the base query with. You can import the function that gives that base query like this:

```python
from func_adl_servicex_xaodr25 import FuncADLQueryPHYSLITE, FuncADLQueryPHYS
```

The correct release and type of data will need to be selected.