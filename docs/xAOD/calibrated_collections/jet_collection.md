# Jet Collection

## Basic Jet query

We can make a basic query to get the jets in the dataset. The following code will select the jets from the dataset and return their pt, eta, and phi values:

```python

    query = FuncADLQueryPHYSLITE()
    jets_per_event = (query
                        .Select(lambda e: e.Jets())
                        .Select(lambda jets: {
                                'pt': jets.Where(lambda j: (j.pt() / 1000 > 30)).Select(lambda j: j.pt() / 1000),
                                'eta': jets.Select(lambda j: j.eta()),
                                'phi': jets.Select(lambda j: j.phi()),
                            })
                    )

    jet_data = get_data(jets_per_event, ds_physlite)

```

```python

    plt.hist(ak.flatten(jet_data.pt), bins=100, range=(0, 100))
    plt.xlabel('Jet $p_T$ [GeV]')
    plt.ylabel('Number of jets')
    _ = plt.title('Jet $p_T$ distribution')

```

```{figure} img/jet_1.png
:alt: Plot of basic jet example
:width: 60%
:align: center
```

## Jet Moments

Attributes are called `moments` by the ATLAS Jet/ETMiss group. They are extra information that has been added into the jet object. 
The `Run 2 Moments Page <https://twiki.cern.ch/twiki/bin/view/AtlasProtected/Run2JetMoments>`_ lists all the moments. 
To access them you'll need to know the return type explicitly, and parameterize your call to ``getAttribute`` appropriately.

Here we grab the ``EMFrac`` moment, which is the EM Fraction of the jet. It is a single float for each jet. 
We specify the type with the ``cpp_float`` in the ``getAttribute[cpp_float]('EMFrac')`` call.
This is translated into C++ that looks something like ``j->getAttribute<float>("EMFrac")``.

```python

    query = FuncADLQueryPHYSLITE()
    jets_per_event = (query
                    .Select(lambda e: e.Jets())
                    .Select(lambda jets: {
                            'emf': jets.Where(lambda j: (j.pt() / 1000) > 30).Select(lambda j: j.getAttribute[cpp_float]('EMFrac')),
                        })
                    )

    moments_data = get_data(jets_per_event, ds_physlite)

```

```python

    plt.hist(ak.flatten(moments_data.emf), bins=100, range=(0, 1.1))
    plt.xlabel('EM Fraction')
    plt.ylabel('Number of jets')
    _ = plt.title('EM Fraction of Jets')

```

```{figure} img/jet_2.png
:alt: Plot of Jet EMF Example
:width: 60%
:align: center
```

More complex objects can come back as well. For example, vectors of floats ``std::vector<float>``. Here is a sample with the sum track :math:`p_T` when track :math:`p_T > 500` MeV.

```python

    query = FuncADLQueryPHYSLITE()
    jets_per_event = (query
                    .Select(lambda e: e.Jets())
                    .Select(lambda jets: {
                            'sum_pt': jets.Select(lambda j: j.getAttribute[cpp_vfloat]('SumPtTrkPt500') / 1000)
                        })
                    )

    moment_data = get_data(jets_per_event, ds_physlite)

```

```python

    plt.hist(ak.flatten(ak.flatten(moment_data.sum_pt)), bins=100, range=(0, 4))
    plt.xlabel('Sum track $p_T$ [GeV]')
    plt.ylabel('Number of jets')
    plt.yscale('log')
    _ = plt.title('Sum Track $p_T$ for tracks over 500 MeV')

```

```{figure} img/jet_3.png
:alt: Plot of Jet SumPt Example
:width: 60%
:align: center
```