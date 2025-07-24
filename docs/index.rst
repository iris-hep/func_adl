FuncADL documentation
=====================

FuncADL is an Analysis Description Language inspired by functional languages and C#’s LINQ. Sophisticated filtering and computation of new values can be expressed by chaining a series of simple functions. 
Because FuncADL is written independently of the underlying data libraries, it can run on many data formats.

This documentation provides an overview of the core concepts behind FuncADL, including its generic query operators and the philosophy of functional analysis. 
It then explores the two primary backends supported by FuncADL:

- **xAOD FuncADL:** Enables analysis of ATLAS xAOD data formats, providing tools for working with both calibrated and uncalibrated collections.
- **Uproot FuncADL:** Supports analysis of Flat Root TTrees and CMS NanoAOD the uproot library.

Documentation Structure
---------------------------

This documentation has four main sections:

- **Generic FuncADL:** Covers the core concepts and query operators that are applicable across different data formats.
- **xAOD FuncADL:** Focuses on the specific implementation for ATLAS xAOD data, detailing how to set up the environment, access samples, and work with calibrated and uncalibrated collections.
- **Uproot FuncADL:** Discusses the implementation for Uproot, including configuration and sample handling for Flat Root TTrees and CMS NanoAOD.
- **Tutorials:** Provides practical examples and tutorials to help users get started with FuncADL in both xAOD and Uproot contexts.

.. toctree::
   :maxdepth: 1
   :caption: Generic FuncADL:

   generic/query_operators
   generic/example_query

.. toctree::
   :maxdepth: 2
   :caption: xAOD FuncADL:

   xAOD/getting_setup
   xAOD/samples
   xAOD/calibrated_collections/index
   xAOD/uncalibrated_collections/index

.. toctree::
   :maxdepth: 2
   :caption: Uproot FuncADL:

   uproot/configuration
   uproot/samples

   