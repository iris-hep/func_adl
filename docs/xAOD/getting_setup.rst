Setting up for xAOD
=====================

Now that you have all the important libraries installed we can setup some helpful classes and functions that will make you analysis easier.
First we will want to setup a datatype for passing samples to the ServiceX frontend.

Setting up Samples
----------------------------

When passing samples to the ServiceX frontend, we will want to use a simple data structure that contains the name of the sample, the dataset location, 
and the codegen to use. This will allow us to easily manage and reference our samples in our analysis.

.. code-block:: python

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

Now that we have a datatype setup to make it easier to define samples, we can create a list of samples that we will use in our analysis:

.. code-block:: python

    from servicex import dataset as servicex_dataset

    _samples = {
        "physlite": sample(
            name="physlite",
            ds = servicex_dataset.FileList(["root://eospublic.cern.ch//eos/opendata/atlas/rucio/mc20_13TeV/DAOD_PHYSLITE.37622528._000013.pool.root.1"]),
            codegen="atlasr25"
        ),
        "phys": sample(
            name="phys",
            ds = servicex_dataset.Rucio("mc23_13p6TeV:mc23_13p6TeV.902046.QBHPy8EG_QBH_photonjet_n1_Mth7000.deriv.DAOD_PHYS.e8557_e8528_s4162_s4114_r14622_r14663_p6026_tid37642334_00"),
            codegen="atlasr25",
        ),
    }

Then we can map these to variables to make it easier to reference them in our analysis:

.. code-block:: python

    physlite = _samples["physlite"]
    phys = _samples["phys"]

Getting Data from ServiceX
----------------------------

Now that we have defined our samples we can use ServiceX deliver() to get the files from the ServiceX backend. To make it easier later we can define a 
function that will take a sample and return the data:

.. code-block:: python

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
        files = deliver(spec, servicex_name="servicex-release-prod")
        assert files is not None, "No files returned from deliver! Internal error"

        # Get the data into an akward array
        data = to_awk(files)

        # For these examples we are only using one sample, so we return just the array, not the dictionary.
        return data[s.name]

A note about this function is that we are using the `servicex_analysis_utils.to_awk` function to convert the files returned from ServiceX into an Awkward Array.