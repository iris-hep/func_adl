# Specialty Functions

As shown in the [metadata](metadata.md) part of the documentation, functions using C++ code can be added to allow for more advanced code to be run.

There are some functions that are used so regularly that they have been added to the library by default so users don't have to create them if they need to use them. These functions are outlined on this page.

## Trigger Functions

There are a couple of functions that allow the user to get trigger decisions more easily.

### Decision Tool - Chain Fired

The Trigger Decision Tool (TDT) provides access to trigger decisions and whether a chain was fired for a specific event. A true or false value indicating whether the trigger has fired can be obtained using the `tdt_chain_fired()` function. The following example uses this function to filter events where the chain was fired.

```python
jets_per_event = (query
    .Where(lambda e: tdt_chain_fired('HLT_j30_momemfrac006_L1jJ160'))
    .Select(lambda e: (
        e.Jets())
    )
    .Select(lambda jets: {
        'jet_pt': jets.Select(lambda j: j.pt() / 1000),
    })
)
```

### Matching Tool - Matched Object

The Trigger Matching Tool (TMT) can be used in conjunction with `tdt_chain_fired()` to determine whether an offline object matches an online object that passed the trigger. This is done using the `tmt_match_object()` function, which takes the chain name, offline object, and ΔR threshold as arguments.

```python
jets_per_event = (query
    .Where(lambda e: tdt_chain_fired('HLT_j30_momemfrac006_L1jJ160'))
    .Select(lambda e: (
        e.Jets())
    )
    .Select(lambda jets: {
        'jet_pt': jets.Select(lambda j: j.pt() / 1000),
        "is_trig": tmt_match_object("HLT_e60_lhmedium_nod0", e, 0.7),
    })
)
```