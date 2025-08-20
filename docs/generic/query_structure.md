# Query Structure

This section explains the concepts without assuming a specific backend or file structure. To keep things general, the operator examples use minimal arguments.If you’re looking for more detailed examples tied to a specific data type or backend, you’ll find those later in the documentation.

When building a query it is helpful to think of .Select() as adding a loop to the query and .Where() as adding an if statement to the query. Each .Select() allows for accessing data another level deeper into the data structure.

The query object is what the FuncADL operators build upon when called and an updated version of the query gets return back ready for another operator or to be passed to ServiceX. The query object is created using a function specific to the datatype, but it generically looks like this:

```python
query = placeholderQueryFunction()
```

To learn what the functions are that will replace placeholderQueryFunction() please see the xAOD or Uproot parts of the documentation.

With this query object any operator can be applied to make modifications at the event level. For example, if a .Select() is added the events in the data are now accessible.

```python
query.Select(lambda event: {})
```

Effectively this is a loop over all the events in the data. The .Where() operator can also be applied on the event level, this will skim events based on the criteria specified. Here is an example of selecting all events after a cut is made.

```python
query.Where(lambda event: {}).Select(lambda event: {})
```

Adding an operator after the first .Select() goes a step deeper into the data. For xAOD this is going into containers and for uproot this is going into the branches. Here another .Where() could be added to make a cut on data in an ntuple branch, or another .Select() to go another step deeper into a DAOD. An example of getting container data from an xAOD:

```python
query.Select(lambda event: {}).Select(lambda container: {})
```

This can be continued to deeper and deeper levels within the data. For example, to get tracks from a jet object, first the events must be selected, then the jet container, then the jet objects, and finally the tracks. At any point in this query a .Where() can be added to make cuts.

Due to the flexible nature of FuncADL there are multiple ways to structure each query. Throughout this documentation different structures will be used for the sake of demonstration.

