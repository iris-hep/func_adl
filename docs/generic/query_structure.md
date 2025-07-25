# Query Structure

The information on this page is agnostic to the specific file structure and backend that you are using. To keep agnostic, the arguments used when the operators are called will be barebones. To understand fully how to implement these ideas datatype specific examples can be found later in the documentaion.

When building a query it is helpful to think of .Select() as adding a loop to the query and .Where() as adding an if statement to the query. Each .Select() allows for accessing data another level deeper into the data structure.

The query object is what the FuncADL operators build upon when called and an udpated version of the query gets return back ready for another operator or to be passed to ServiceX. The query object is created using a function specific to the datatype, but it generically looks like this:

```python
query = placeholderQueryFunction()
```

With this query object any operator can be applied to make modifications at the event level. For example, if a .Select() is added the events in the data are now accessable.

```python
query.Select(lambda event: {})
```

Effectivley this is a loop over all the events in the data. The .Where() operator can also be applied on the event level, this will skim events based on the critera specified. Here is an example of selecting all events after a cut is made.

```python
query.Where().Select(lambda event: {})
```

Adding an operator after the first .Select() goes a step deeper into the data. For xAOD this is going into containers and for uproot this is going into the branches. Here another .Where() could be added to make a cut on data in an ntuple branch, or another .Select() to go another step deeper into a DAOD. An example of getting container data from an xAOD:

```python
query.Select(lambda event: {}).Select(lambda container: {})
```

This can be continued to deeper and deeper levels within the data. For example, to get tracks from a jet object, first the events must be selected, then the jet container, then the jet objects, and finally the tracks. At any point in this query a .Where() can be added to make cuts.

Due to the flexible nature of FuncADL there are multiple ways to structure each query. Throughout this documentation different structures will be used for the sake of demonstration.

