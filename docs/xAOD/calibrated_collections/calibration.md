# Calibration and Calibration Tools

When running on PHYS using ServiceX and FuncADL you are able to run systematics and cp tools using a build in calibration configuration class calib_tools.

You will need to import the class to use,

```python
from func_adl_servicex_xaodr25 import calib_tools
```

## Default Calibration

When you run without using calib_tools FuncADL uses a default configuration that is optimized for DAOD. Here is a list of all the properties available to be configured using calib_tools and their default values.

If you are intersted in seeing the default configuration in your workspace you can print it using this method:

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
    correct_pileup=True,
```

## Changing Configuration

If you are intersted in changing any of the values in the calibration configuration there are a couple of ways to do it. 

### Global Default Configuration

One way to change the configuration that you are running is by changing the global default configuration. Any changes that you make this way will be reflected in all queries that you send. 

Be careful when chaning the configuration here because it can cause unexpected results later!

Here is an example of changing the container we select the jets from:

```python
new_jet_selection = calib_tools.default_config()
new_jet_selection.jet_collection = 'AntiKt4EMTopoJets'
calib_tools.set_default_config(new_jet_selection)
```

You can also reset the default configuration:

```python
calib_tools.reset_config()
```

### Individual Query Configuration

You can also change the configuration for the specific query that you are building. The best way to do this is by using the `calib_tools.query_update()` function. This function takes in a query and a list of the configuration values you would like to change. The function returns a query.

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

Here is an example of turning off the calibration.

```python
query = FuncADLQueryPHYS()
electrons_per_event = (calib_tools.query_update(query, calibrate=False)
    .Select(lambda e: e.Electrons())
    .Select(lambda electrons: {
        'pt': electrons.Select(lambda j: j.pt() / 1000),
    })
)
```

If you want to change multiple values you can do that like this: 

```python
calib_tools.query_update(query, calibrate=False, correct_pileup=False)
```

You are also able to pass an entire `CalibrationEventConfig` object through the function:

```python
new_jet_selection = calib_tools.default_config()
new_jet_selection.jet_collection = 'AntiKt4EMTopoJets'

query = calib_tools.query_update(query, calib_config=new_jet_selection)
```

This is a better way to setup calibrations that will be reused many times than doing it globally. This way you can setup your calibration once and then reuse it with ease in a way that is less likley to cause issues.

## Running Systematics

Currently you are only able to run one systematic at a time using FuncADL. If you need to work with many at once, currently FuncADL is not the tool for your workflow.

To run on one systemtic at a time you can update the query similar to change the configuration using the `query_sys_error()` function. Here is an example of adding systematics to a jet call:

```python
jets_per_event = (func_adl.calib_tools.query_sys_error(query, "JET_Pileup_PtTerm__1up")
                    .Select(lambda j: j.Jets())
                    .Select(lambda jets: {
                            'pt': jets.Select(lambda j: j.pt() / 1000),
                        })
                    )

```