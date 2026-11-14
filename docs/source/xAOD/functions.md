# Specialty Functions

:::{admonition} You Will Learn:
:class: note
- What built-in specialty functions FuncADL provides
- How to use the Trigger Decision Tool (TDT) with `tdt_chain_fired()` to filter events by trigger chain
- How to use the Trigger Matching Tool (TMT) with `tmt_match_object()` to match offline objects to trigger objects
:::

As shown in the [metadata](metadata.md) section of the documentation, functions using C++ code can be added to run more advanced logic.

Some functions are used so regularly that they are included in the library by default, so users do not have to recreate them. These functions are outlined on this page.

## Trigger Functions

Several functions provide easier access to trigger decisions.

### Decision Tool - Chain Fired

The Trigger Decision Tool (TDT) provides access to trigger decisions, including whether a chain fired for a given event. The `tdt_chain_fired()` function returns a true or false value indicating whether the trigger fired. The following example uses this function to filter events where the chain fired.

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

The Trigger Matching Tool (TMT) is used in conjunction with `tdt_chain_fired()` to determine whether an offline object matches an online object that passed the trigger. The `tmt_match_object()` function performs this match, taking the chain name, offline object, and ΔR threshold as arguments.

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