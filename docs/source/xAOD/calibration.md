# Calibration Tools

:::{admonition} You Will Learn:
:class: note
- What the default calibration configurations are for PHYS and PHYSLite
- How to change calibration settings globally or per query
- How to use `calib_tools.query_update()` to override configuration values
- How to run a single systematic with `calib_tools.query_sys_error()`
:::

FuncADL runs Combined Performance (CP) tools and systematics through a built-in calibration configuration class, `calib_tools`. Import this class as follows:

```python
from func_adl_servicex_xaodr25 import calib_tools
```

## Default Calibration

When `calib_tools` is not used, FuncADL applies a default configuration optimized for DAOD. The list below shows all properties available for configuration through `calib_tools` and their default values.

To print the default configuration at any time, run this code:

```python
print(calib_tools.default_config())
```

### PHYS

```python
jet_collection="AntiKt4EMPFlowJets",
jet_calib_truth_collection="AntiKt4TruthDressedWZJets",
run_jet_ghost_muon_association=True,
electron_collection="Electrons",
electron_working_point="MediumLHElectron",
electron_isolation="NonIso",
photon_collection="Photons",
photon_working_point="Tight",
photon_isolation="FixedCutTight",
muon_collection="Muons",
muon_working_point="Medium",
muon_isolation="NonIso",
tau_collection="TauJets",
tau_working_point="Tight",
met_collection="MissingET",
perform_overlap_removal=True,
datatype="mc",
calibrate=True,
uncalibrated_possible=True,
correct_pileup=True
```

### PHYSLite

```python
jet_collection="AnalysisJets",
jet_calib_truth_collection="AntiKt4TruthDressedWZJets",
run_jet_ghost_muon_association=False,
electron_collection="AnalysisElectrons",
electron_working_point="MediumLHElectron",
electron_isolation="NonIso",
photon_collection="AnalysisPhotons",
photon_working_point="Tight",
photon_isolation="FixedCutTight",
muon_collection="AnalysisMuons",
muon_working_point="Medium",
muon_isolation="NonIso",
tau_collection="AnalysisTaus",
tau_working_point="Tight",
met_collection="MET_Core_AnalysisMET",
perform_overlap_removal=True,
datatype="mc",
calibrate=False,
uncalibrated_possible=False,
correct_pileup=True
```

## Changing Configuration

Sometimes it is necessary to deviate from the default configuration. There are several ways to change these values, each suited to a different use case.

### Using the calib_tools class

Multiple examples use the `CalibrationEventConfig` object. The example below creates a new configuration based on the default config and changes the value of the jet collection. All values listed above can be changed in a similar way.

```python
jet_topo_config = calib_tools.default_config()
jet_topo_config.jet_collection = 'AntiKt4EMTopoJets'
```

### Global Default Configuration

One way to change the configuration is by setting a new global default. Any change made this way is reflected in all future queries. Be careful when changing the configuration globally, since it can cause unexpected results later, especially in Jupyter notebooks. Prefer one of the techniques described below to avoid bugs.

Change the global configuration like this:

```python
calib_tools.set_default_config(jet_topo_config)
```

Reset the default configuration like this:

```python
calib_tools.reset_config()
```

### Multiple Query Configuration

Although changing the configuration globally is not recommended, the configuration object created above can be passed into each query. This allows the configuration to be reused while making explicit which configuration each query uses.

To change the configuration that a query uses, use the `calib_tools.query_update()` function. This function takes a query and a set of changes, and returns the modified query object.

`query_update()` definition:

    Add metadata to a query to indicate a change in the calibration configuration for the query.

    Args:
        query (ObjectStream[T]): The query to update.

        calib_config (Optional[CalibrationEventConfig]): The new calibration
            configuration to use. If specified will override all calibration
            configuration options in the query.

        jet_collection, ...: Use any property name from the `CalibrationEventConfig`
            class to override that particular options for this query. You may
            specify as many of them as you like.

In addition to updating individual configuration properties (shown in the next example), the entire configuration of a query can be replaced using a `CalibrationEventConfig` object. Pass a `CalibrationEventConfig` to the query like this:

```python
query = calib_tools.query_update(query, calib_config=new_jet_selection)
```

### Individual Query Configuration

Sometimes it is useful to change the calibration settings for each individual query. The following example turns the calibration off using `query_update()`:

```python
query = FuncADLQueryPHYS()
electrons_per_event = (calib_tools.query_update(query, calibrate=False)
    .Select(lambda e: e.Electrons())
    .Select(lambda electrons: {
        'pt': electrons.Select(lambda j: j.pt() / 1000),
    })
)
```

Multiple properties can be changed using `query_update()`:

```python
calib_tools.query_update(query, calibrate=False, correct_pileup=False)
```

## Running Systematics

FuncADL with ServiceX and xAOD can run full systematics, but the current setup returns only one systematic from a query. If the analysis requires many systematics at once, FuncADL may not be the correct tool.

To change the systematic that FuncADL returns, use the `calib_tools.query_sys_error()` function. This function works similarly to `query_update()`: a query is passed in and the modified query is returned. Building a query to return jets with the `JET_Pileup_PtTerm__1up` systematic looks like this:

```python
jets_per_event = (func_adl.calib_tools.query_sys_error(query, "JET_Pileup_PtTerm__1up")
                    .Select(lambda j: j.Jets())
                    .Select(lambda jets: {
                            'pt': jets.Select(lambda j: j.pt() / 1000),
                        })
                    )

```