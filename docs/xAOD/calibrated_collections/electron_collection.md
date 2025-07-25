# Electron Collection

## Basic Electron Query

The default electron we fetch is the `MediumLHElectron` electron with `NonIso` isolation. The next example will show how to change your working point.

```python

query = FuncADLQueryPHYSLITE()
electrons_per_event = (query
    .Select(lambda e: e.Electrons())
    .Select(lambda electrons: {
        'pt': electrons.Select(lambda j: j.pt() / 1000),
        'eta': electrons.Select(lambda j: j.eta()),
        'phi': electrons.Select(lambda j: j.phi()),
    })
)

electron_data = get_data(electrons_per_event, sx_f)

```

```python

plt.hist(ak.flatten(electron_data.pt), bins=100, range=(0, 100))
plt.xlabel('Electron $p_T$ [GeV]')
plt.ylabel('Number of electrons')
_ = plt.title('Electron $p_T$ distribution for $Z\\rightarrow ee$ events')

```

```{figure} img/ele_1.png
:alt: Plot of basic electron example
:width: 60%
:align: center
```

## Electron Working Points

Electrons come in several different flavors. We can look at the different $\eta$ distributions for the electrons. Isolation is another axis we can alter, not shown here, by changing the `electron_isolation` argument to `Electrons`.

On the Calibration page we pointed out we can't run multiple queries with different object setups due to limitations in the xAOD AnalysisBase when looking at calibrated objects. So we'll have to do this in three queries instead.

```python

working_points = ['LooseLHElectron', 'MediumLHElectron', 'TightLHElectron']
eta_results = {}

for wp in working_points:
    query = FuncADLQueryPHYS()
    q = (calib_tools.query_update(query, electron_working_point=wp)
            .Select(lambda e: e.Electrons())
            .Select(lambda electrons: {
                'eta': electrons.Select(lambda ele: ele.eta())
            }))
    eta_results[wp] = get_data(q, sx_f_phys)

```

```python

for wp, data in eta_results.items():
    plt.hist(ak.flatten(data.eta), bins=50, range=(-3, 3), label=wp)

plt.xlabel('Electron $\\eta$')
plt.ylabel('Number of electrons')
plt.title('Electron $\\eta$ distribution for different working points')
plt.legend()
plt.show()

```

```{figure} img/ele_2.png
:alt: Plot of basic electron example
:width: 60%
:align: center
```