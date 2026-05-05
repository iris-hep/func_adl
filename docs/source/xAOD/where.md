# Using .Where()

:::{admonition} You Will Learn:
:class: note
- How `Where()` filters data at different levels of a query
- How the position of `Where()` relative to `Select()` changes the result
- How to skim events using `Where()` at the event level
:::

As discussed on the query structure page, the location of the `Where()` function determines the level in the data at which the cut applies. The examples on this page build a strong understanding of using `Where()` in xAOD queries.

## Applying pt Cuts

A `Where()` call can apply a pt cut at multiple positions in a query, and the position changes the resulting data. The difference comes from the location of `Where()` relative to the `Select()` functions. The two examples below illustrate this difference.

### Apply to All Values

The following code applies the pt cut before any values are selected from the jets. As a result, pt, eta, and phi all come only from jets with 30 GeV or higher.

```{eval-rst}
.. testsetup::

   from config import get_data, physlite_ds
   from func_adl_servicex_xaodr25 import FuncADLQueryPHYSLITE
   import io, contextlib

.. testcode::

    query = FuncADLQueryPHYSLITE()
    jets_per_event = (query
        .Select(lambda e: e.Jets().Where(lambda j: (j.pt() / 1000 > 30)))
        .Select(lambda jets: {
            'pt': jets.Select(lambda j: j.pt() / 1000),
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

### Apply only to pt Values

The following code applies the pt cut only before the pt `Select()` operator. As a result, only the pt values come from cut jets, while eta and phi come from all jets.

```{eval-rst}
.. testsetup::

   from config import get_data, physlite_ds
   from func_adl_servicex_xaodr25 import FuncADLQueryPHYSLITE
   import io, contextlib

.. testcode::

    query = FuncADLQueryPHYSLITE()
    jets_per_event = (query
        .Select(lambda e: e.Jets())
        .Select(lambda jets: {
                'pt': jets.Where(lambda j: (j.pt() / 1000 > 30)).Select(lambda j: j.pt() / 1000),
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

### Comparison

Plotting the Jet pt and Jet eta demonstrates the difference between these methods.

```{figure} img/where_1.png
:alt: Plot of Jet pt, Shows Values are Same
:width: 60%
:align: center
```

The plot above shows that the Jet pt data is identical between both methods of applying the cut, as expected.

```{figure} img/where_2.png
:alt: Plot of Jet Eta, Shows Values Differ
:width: 60%
:align: center
```

The eta plot above shows that the Jet eta values differ between the two methods. The eta values are not trimmed when `Where()` is not called before the eta `Select()`.

## Skimming Events

Skimming events requires using `Where()` at the event level of the query, which takes place before the first `Select()`. The example below builds a query that selects jets with pt > 30 GeV from events containing at least one jet of 100 GeV.

```{eval-rst}
.. testsetup::

   from config import get_data, physlite_ds
   from func_adl_servicex_xaodr25 import FuncADLQueryPHYSLITE
   import io, contextlib

.. testcode::

    query = FuncADLQueryPHYSLITE()
    jets_per_event = (query
        .Where(lambda e: e.Jets().Where(lambda j: (j.pt() / 1000 > 100)).Count() > 0)
        .Select(lambda e: e.Jets())
        .Select(lambda jets: {
                'pt': jets.Where(lambda j: j.pt() / 1000 > 30).Select(lambda j: j.pt() / 1000),
        })
    )

.. testcode::
    :hide:

    with contextlib.redirect_stdout(io.StringIO()):
        data = get_data(jets_per_event, physlite_ds)
    assert data.pt[0][0] == 118.1983671875

```

Comparing the results to the first set of examples shows far fewer jets, which is expected when looking at fewer events.

```{figure} img/where_3.png
:alt: Plot of Jet pt, Shows event skimming
:width: 60%
:align: center
```