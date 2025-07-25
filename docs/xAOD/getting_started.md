# Getting Started with xAOD

This section of the FuncADL documentation will cover:

- How to set up your environment to access xAOD data in ATLAS
- Access methods, attributes, and decorations on the xAOD Event Data Model (EDM).

This section assumes you have the following prerequisites:

- Access to an ATLAS xAOD ServiceX backend
- Basic knowledge of the ATLAS xAOD data model (at the level of a standard ATLAS tutorial)
- The names of the xAOD collections you are interested in, etc.

For more information on the ServiceX, see the documentation linked in the navigation bar.

## FuncADL xAOD Releases

Depending on what ATLAS release you are using, you will need to install and import different libraries. The libraries are:

- ``func_adl_servicex_xaodr21``
- ``func_adl_servicex_xaodr22``
- ``func_adl_servicex_xaodr25``

## Other Tools

In the examples we will be building we will be using various other tools. These should be pip installed to follow the examples present:

- ``servicex``
- ``servicex_analysis_utils``
- ``awkward``
- ``matplotlib``
- ``numpy``

To install the tools, run:

```bash

   pip install servicex servicex_analysis_utils awkward matplotlib numpy

```