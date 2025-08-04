# Using .Select()

The foundation to building any query is the .Select() function. Without it no data will be returned! The examples on this page are designed showcase all the different uses of the .Select() function.

## Objects that can be selected

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

```{eval-rst}
.. testsetup::

   from config import get_data, physlite_ds
   from func_adl_servicex_xaodr25 import FuncADLQueryPHYSLITE
   import io, contextlib

.. testcode::

    query = FuncADLQueryPHYSLITE()
    jets_per_event = (query
        .Select(lambda e: e.Jets()) # This select loops over the events and specifies which containers we pass to the next loop
        .Select(lambda jets: { # This select opens those containers
                'pt': jets.Select(lambda j: j.pt() / 1000), # This .Select() loops over each object in the container and provides to data specified.
                'eta': jets.Select(lambda j: j.eta()),
                'phi': jets.Select(lambda j: j.phi()),
        })
    )

.. testcode::
    :hide:

    with contextlib.redirect_stdout(io.StringIO()):
        data = get_data(jets_per_event, physlite_ds)
    assert data.pt[0][0] == 99.4445390625

```

### Query Structure

It is useful provide additional context to the general Query Structure page by looking at how the .Select() function works in the example above. The first .Select() loops over the events in the dataset. In this function the .Jets() function specifies the physics objects/container that data will be drawn from. The next .Select() gives access to the data in each of those containers. The final select is what pulls the data from the physic object.

## Selecting Multiple Physics Objects

Most analyses require more than one physics object to be selected and manipulated. To build a query with multiple objects additional structure is required in the code. In this example a dictionary will be used but for more complex examples custom objects could the right answer. This example will select pt for both jets and muons.

```{eval-rst}
.. testsetup::

   from config import get_data, physlite_ds
   from func_adl_servicex_xaodr25 import FuncADLQueryPHYSLITE
   import io, contextlib

.. testcode::

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

.. testcode::
    :hide:

    with contextlib.redirect_stdout(io.StringIO()):
        data = get_data(jets_per_event, physlite_ds)
    assert data.pt[0][0] == 99.4445390625

```

While using a dictionary in the query to store our objects is less complex upfront as when the queries are more complex adding a custom object can simplify code downstream in the analysis. This is emphasized by the need for the naming used in the pt dictionary. In an analysis that requires more field this can become difficult to manage.

## Selecting Moments Using .getAttribute\[\]\(\)

Sometimes it is required to select more than the basic properties of the physics object being looked at. An object's moments can be selected using the .getAttribute\[\]\(\) function. In order to use this function the data type of the attribute being selected must be specified. These data types need to be important to python like this:

```python
from func_adl_servicex_xaodr25 import cpp_float, cpp_vfloat
```

Here the type `float` and `vector<float>` are imported. There are many types that can be imported:

```python
cpp_float
cpp_int
cpp_double
cpp_string
cpp_vfloat
cpp_vint
cpp_vdouble
```

Once the type of the attribute is imported then the attribute can be selected as shown in the example below:


```{eval-rst}
.. testsetup::

   from config import get_data, physlite_ds
   from func_adl_servicex_xaodr25 import FuncADLQueryPHYSLITE, cpp_float
   import io, contextlib

.. testcode::

    query = FuncADLQueryPHYSLITE()
    jets_per_event = (query
        .Select(lambda e: e.Jets())
        .Select(lambda jets: {
            'emf': jets.Select(lambda j: j.getAttribute[cpp_float]('EMFrac')),
        })
    )

.. testcode::
    :hide:

    with contextlib.redirect_stdout(io.StringIO()):
        data = get_data(jets_per_event, physlite_ds)
    assert data.emf[0][0] == 0.93529713
```

## Selecting from Specific Container

By default FuncADL selects the most common containers used for each object. This however is not always what is needed when building a query. To specify a container outside of the default container a query can be created like this:

```{eval-rst}
.. testsetup::

   from config import get_data, physlite_ds
   from func_adl_servicex_xaodr25 import FuncADLQueryPHYSLITE, cpp_float
   import io, contextlib

.. testcode::

    jets_per_event = (query
        .Select(lambda e: e.Jets("AntiKt10UFOCSSKJets"))
        .Select(lambda jets: {
                'pt': jets.Select(lambda j: j.pt() / 1000),
        })
    )

.. testcode::
    :hide:

    with contextlib.redirect_stdout(io.StringIO()):
        data = get_data(jets_per_event, physlite_ds)
    assert data.pt[0][0] == 84.1220703125
```

The list of all default configurations are listed on the calibration page along with more examples on how to the configuration of your query. Please see here for specific defaults.

## Using .SelectMany()

As described in the query_operators section, .SelectMany() is similar to .Select(), but is flattens the data. This allows for the simplification of some queries. For example getting jet constituents. Here is an example of using `.SelectMany()`

<!-- TODO: Add an example of to get the jet constituents without .SelectMany() to show how they differ. -->
<!-- TODO: Find the right dataset to turn this example into something that can be tested. -->

```python
query = FuncADLQueryPHYS()
jets_con_per_event = (query
    .SelectMany(lambda e: e.Jets())
    .SelectMany(lambda j: j.getConstituents())
    .Select(lambda tc: tc.pt())
)

topo_clusters = get_data(jets_con_per_event,sx_f)
```