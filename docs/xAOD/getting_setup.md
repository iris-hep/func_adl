# Setting up for xAOD

To use FuncADL with Atlas xAOD the dataset/sample being used needs to be specified. To do this it is useful to setup a datatype for passing samples to the ServiceX frontend.

## Setting up Samples

When passing samples to the ServiceX frontend, it is convenient to use a simple data structure that contains the name of the sample, the dataset location, and the codegen to use. This will allows easy management and reference of the samples in the analysis.

```python

    from dataclasses import dataclass
    from typing import List, Union

    @dataclass
    class sample:
        "Location of data sample"
        # Shorthand name
        name: str

        ds: Union[List[str], str]

        # Codegen
        codegen: str

```

Now that a datatype is setup to make it easier to define samples a list of samples that is used in the analysis can be created:

```python

    from servicex import dataset as servicex_dataset

    _samples = {
        "ds_physlite": sample(
            name="physlite",
            ds = servicex_dataset.FileList(["root://eospublic.cern.ch//eos/opendata/atlas/rucio/mc20_13TeV/DAOD_PHYSLITE.37622528._000013.pool.root.1"]),
            codegen="atlasr25"
        ),
        "ds_phys": sample(
            name="phys",
            ds = servicex_dataset.Rucio("mc23_13p6TeV:mc23_13p6TeV.902046.QBHPy8EG_QBH_photonjet_n1_Mth7000.deriv.DAOD_PHYS.e8557_e8528_s4162_s4114_r14622_r14663_p6026_tid37642334_00"),
            codegen="atlasr25",
        ),
    }

```

Then these can be mapped to variables to make it easier to reference them later:

``` python

    ds_physlite = _samples["ds_physlite"]
    ds_phys = _samples["ds_phys"]
    
```

## Getting Data from ServiceX

Now that the samples have been defined they are ready to be passed to ServiceX deliver() to get the files from the ServiceX backend. To make it easier later a function can be defined that will take a sample and return the data:

```python

    from servicex_analysis_utils import to_awk
    from servicex import deliver

    def get_data(query, s: sample):
        """Sends request for data to servicex backend.
        
        Args:
            query: FuncADLQueryPHYSLITE
            s (sample): The sample to create

        Returns:
            List of files returned from servicex backend
        
        """
        spec = {
            'Sample': [{
                'Name': s.name,
                'Dataset': s.ds,
                'Query': query,
                'Codegen': s.codegen,
            }]
        }

        # Get the files from the ServiceX backend
        files = deliver(spec, servicex_name="servicex")
        assert files is not None, "No files returned from deliver! Internal error"

        # Get the data into an awkward array
        data = to_awk(files)

        # For these examples we are only using one sample, so we return just the array, not the dictionary.
        return data[s.name]

```

This example uses the to_awk() function from `servicex_analysis_utils.to_awk`. This takes the list of files that are from ServiceX and returns an awkward array.