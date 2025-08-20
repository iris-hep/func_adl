# Calibration Tools

FuncADL allows for CP Tools and systematics to be run using a built in calibration configuration class `calib_tools`. To use this class it will need to be imported like this:

```python
from func_adl_servicex_xaodr25 import calib_tools
```

## Default Calibration

When running without using calib_tools FuncADL uses a default configuration that is optimized for DAOD. Here is a list of all the properties available to be configured using calib_tools and their default values.

To print the default configuration at any time run this code:

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

Sometimes it is required to deviate from the default configuration. There are a couple of ways that these values can be changed, each best for different use cases.

### Using the calib_tool class

Multiple examples use the `CalibrationEventConfig` object. To demonstrate this the example below creates a new configuration based on the default config. Then the value of the jet collection is changed. All the values listed above can be changed in a similar way.

```python
jet_topo_config = calib_tools.default_config()
jet_topo_config.jet_collection = 'AntiKt4EMTopoJets'
```

### Global Default Configuration

One way to change the configuration is by changing the global default configuration. Any changes made this way will be reflected in all future queries. Be careful when changing the configuration globally because it can cause unexpected results later, especially in Juypter notebooks! It is recommended that one of the techniques following this section is used to avoid bugs.

The global configuration can be changed like this:

```python
calib_tools.set_default_config(jet_topo_config)
```

The default configuration can be reset like this:

```python
calib_tools.reset_config()
```

### Multiple Query Configuration

While using changing the configuration globally isn't recommended, the configuration object created above can be passed into each query. This allows for reuse of your configuration while making it explicit what configuration is being used for each query.

To change the configuration that a query uses the `calib_tools.query_update()` function can be used. This function takes in a query and the changes to that query and then outputs the modified query object. 

query_update() definition:

    Add metadata to a query to indicate a change in the calibration configuration for the query.

    Args:
        query (ObjectStream[T]): The query to update.

        calib_config (Optional[CalibrationEventConfig]): The new calibration
            configuration to use. If specified will override all calibration
            configuration options in the query.

        jet_collection, ...: Use any property name from the `CalibrationEventConfig`
            class to override that particular options for this query. You may
            specify as many of them as you like.

Not only can individual configuration properties be updated using this function as shown in the next example, the entire configuration of a query can be updated using a `CalibrationEventConfig` object. A `CalibrationEventConfig` can be passed to the query like this:

```python
query = calib_tools.query_update(query, calib_config=new_jet_selection)
```

### Individual Query Configuration

Sometimes it is useful to change the calibration settings for each individual query. This example shows how to turn the calibration off using `.query_update()`:

```python
query = FuncADLQueryPHYS()
electrons_per_event = (calib_tools.query_update(query, calibrate=False)
    .Select(lambda e: e.Electrons())
    .Select(lambda electrons: {
        'pt': electrons.Select(lambda j: j.pt() / 1000),
    })
)
```

Multiple properties can be changed using `.query_update()`:

```python
calib_tools.query_update(query, calibrate=False, correct_pileup=False)
```

## Running Systematics

While when using FuncADL and ServiceX with xAOD full systematics can be run how FuncADL is currently setup only one systematic can be returned from a query. If the analysis requires many at once, FuncADL may not be the correct tool.

To change the systematic being selected by FuncADL to be returned the `calib_tools.query_sys_error()` function can be used. This function works similarly to `.query_update()` meaning a query is passed in and the modified one is returned. Building a query to return jets with the `JET_Pileup_PtTerm__1up` systematic looks like this:

```python
jets_per_event = (func_adl.calib_tools.query_sys_error(query, "JET_Pileup_PtTerm__1up")
                    .Select(lambda j: j.Jets())
                    .Select(lambda jets: {
                            'pt': jets.Select(lambda j: j.pt() / 1000),
                        })
                    )

```