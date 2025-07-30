# Using .Select()

The foundation to building any query is the .Select() function. Without it no data will be returned! The examples on this page are designed showcase all the different uses and quirk of the .Select() function.

## Objects that can be selection

In any query many physics objects can be selected. Here is a list of many, but not all of them:

```python
e.Jets()
e.Muons()
e.Electrons()
e.TauJets()
e.MissingET()
e.TrackParticles()
e.Vertices()
e.CaloClusters()
```

## Selecting Single Physics Object

The simplest query that can be made is selecting a single object and getting multiple values from it. The following example selects pt, eta, and phi from all jets in the dataset. It also converts jet pt to GeV by dividing by 1000. A useful feature of FuncADL is that it can do simple mathematic operations right in the query!

```python
query = FuncADLQueryPHYSLITE()
jets_per_event = (query
                    .Select(lambda e: e.Jets()) # This select loops over the events and specifies which containers we pass to the next loop
                    .Select(lambda jets: { # This select opens those containers
                            'pt': jets.Select(lambda j: j.pt() / 1000), # This .Select() loops over each object in the container and provides to data specified.
                            'eta': jets.Select(lambda j: j.eta()),
                            'phi': jets.Select(lambda j: j.phi()),
                        })
                 )

jet_data = get_data(jets_per_event, physlite_ds)
```

### Query Structure

It is useful provide additional context to the general Query Structure page by looking at how the .Select() function works in the example above. The first .Select() loops over the events in the dataset. In this function the .Jets() function specifies the physics objects/container that data will be drawn from. The next .Select() gives access to the data in each of those containers. The final select is what pulls the data from the physic object.

## Selecting Multiple Physics Objects

Most analyses require more than one physics object to be selected and manipulated. To build a query with multiple objects addition structure is required in the code. In this example a dictionary will be used, but for more complex examples custom objects could the right answer. This example will select pt for both jets and muons.

```python
query = FuncADLQueryPHYSLITE()
jets_muons_per_event = (query
                    .Select(lambda e: {
                        'jets': e.Jets(),
                        'muons': e.Muons(),
                    })
                    .Select(lambda po: {
                        'jet_pt': po['jets'].Select(lambda j: j.pt() / 1000),
                        'muon_pt': po['muons'].Select(lambda m: m.pt() / 1000),
                    })
                 )

data = get_data(jets_muons_per_event, physlite_ds)
```

While using a dictionary in the query to store our objects is less complex upfront as when the queries are more complex adding a custom object can simplify code downstream in the analysis. This is emphasized by the need for the naming used in the pt dictionary. In an analysis that requires more field this can become difficult to manage.

## Selecting Moments Using .getAttribute[]()

Sometimes it is required to select more than the basic properties of the physics object being looked at. Objects moments can be selected using the .getAttribute[]() function. In order to use this function the data type of the attribute being selected must be specified. These data types need to be important to python like this:

```python
from func_adl_servicex_xaodr25 import cpp_float, cpp_vfloat
```

Here the type float and vector float are imported. There are many types that can be imported the list is:

TODO: Add type list here.

Once the type of the attribute is imported then the attribute can be selected as shown in the example below:

```python
query = FuncADLQueryPHYSLITE()
jets_per_event = (query
                  .Select(lambda e: e.Jets())
                  .Select(lambda jets: {
                        'emf': jets..Select(lambda j: j.getAttribute[cpp_float]('EMFrac')),
                     })
                 )

moments_data = get_data(jets_per_event, sx_f)
```

Understanding what attributes are able to be selected from data is important and there is a utilities library associated with ServiceX that allows for this to be done easily.

TODO: Add serviceX utils example here, if you can do this with it right now.

## Selecting from Specific Container

By default FuncADL selects the most common containers used for each object. This however is not always what is needed when building a query. To specify a container outside of the default container a query can be created like this:

```python
query = FuncADLQueryPHYSLITE()
jets_per_event = (query
                    .Select(lambda e: e.Jets("AntiKt10UFOCSSKJets")
                    .Select(lambda jets: {
                            'pt': jets.Select(lambda j: j.pt() / 1000),
                        })
                 )

data = get_data(jets_per_event, physlite_ds)
```

The list of all default configurations are listed on the calibration page. Please see here for specific defaults.

## Using .SelectMany()

As described in the query_operators section, .SelectMany() is similar to .Select(), but is flattens the data. This allows for simplifying some queries. For example getting jet constituents. Here is an example using .Select():

```python
TODO: Example using only select for jet constituents
```

A query that provides the same result, but is much simpler can be created using .SelectMany():

```python
TODO: Add example for select many of jet constituents
```