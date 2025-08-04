from dataclasses import dataclass
from typing import List, Union

import awkward as ak
import numpy as np

from servicex_analysis_utils import to_awk

from servicex import deliver, dataset as servicex_dataset


@dataclass
class sample:
    "Location of data sample"

    # Shorthand name
    name: str

    ds: servicex_dataset.GenericDataSet

    # Codegen
    codegen: str


_samples = {
    "sx_f": sample(
        name="sx_f",
        ds=servicex_dataset.FileList(
            [
                "root://eospublic.cern.ch//eos/opendata/atlas/rucio/mc20_13TeV/DAOD_PHYSLITE.37622528._000013.pool.root.1"
            ]
        ),
        codegen="atlasr25",
    ),
    "sx_f_phys": sample(
        name="sx_f_phys",
        ds=servicex_dataset.Rucio(
            "mc23_13p6TeV:mc23_13p6TeV.902046.QBHPy8EG_QBH_photonjet_n1_Mth7000.deriv.DAOD_PHYS.e8557_e8528_s4162_s4114_r14622_r14663_p6026_tid37642334_00"
        ),
        codegen="atlasr25",
    ),
    "sx_f_zee": sample(
        name="sx_f_zee",
        ds=servicex_dataset.Rucio(
            "mc16_13TeV:mc16_13TeV.361022.Pythia8EvtGen_A14NNPDF23LO_jetjet_JZ2W.deriv.DAOD_EXOT15.e3668_s3126_r9364_r9315_p4696"
        ),
        codegen="atlasr25",
    ),
}

# sx_f means servicex-frontend documentation dataset, need to find a better name for this, will update after I learn how to find ds names
physlite_ds = _samples["sx_f"]
phys_ds = _samples["sx_f_phys"]
sx_f_zee = _samples["sx_f_zee"]


def get_data(query, s: sample):
    """Sends request for data to servicex backend.

    Args:
        query: FuncADLQueryPHYSLITE
         s (sample): The sample to create

    Returns:
        List of files returned from servicex backend

    """
    spec = {
        "Sample": [
            {
                "Name": s.name,
                "Dataset": s.ds,
                "Query": query,
                "Codegen": s.codegen,
            }
        ]
    }

    # Get the files from the ServiceX backend
    files = deliver(spec, servicex_name="servicex-release-prod")
    assert files is not None, "No files returned from deliver! Internal error"

    # Get the data into an akward array
    data = to_awk(files)

    # For these examples we are only using one sample, so we return just the array, not the dictionary.
    return data[s.name]


def match_eta_phi(jets, jets_to_match) -> ak.Record:
    """Match `jets_to_match` to the `jets` given. There will always be
    at least one jet found.

    The awkward array needs to have leaves called `pt`, `eta`, and `phi`.

    Args:
        jets (_type_): Source jets
        jets_to_match (_type_): Jets to match to `jets`

    Returns:
        _type_: Matched jets 1:1 in `jets` from `jets_to_match`.
    """

    to_match_pt = jets_to_match.pt
    to_match_eta = jets_to_match.eta
    to_match_phi = jets_to_match.phi

    jet_eta = jets.eta
    jet_phi = jets.phi

    pair_eta = ak.cartesian([jet_eta, to_match_eta], axis=1, nested=True)
    pair_phi = ak.cartesian([jet_phi, to_match_phi], axis=1, nested=True)

    delta_eta = np.abs(pair_eta[:, :, :]["0"] - pair_eta[:, :, :]["1"])
    # TODO: Missing wrap around fro phi
    delta_phi = np.abs(pair_phi[:, :, :]["0"] - pair_phi[:, :, :]["1"])

    delta = delta_eta**2 + delta_phi**2

    # TODO: remove anything larger that 0.2*0.2
    best_match = ak.argmin(delta, axis=2)

    return ak.Record(
        {
            "eta": to_match_eta[best_match],
            "phi": to_match_phi[best_match],
            "pt": to_match_pt[best_match],
        }
    )
