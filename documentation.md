# Documentation for func_adl

func_adl is an SQL-like language used to construct hierarchical data queries for `servicex` (https://pypi.org/project/servicex/). func_adl is written to work with both `servicex` service modes, and requires either `func_adl_xAOD` (https://pypi.org/project/func-adl-xAOD/) or `func_adl_uproot` (https://pypi.org/project/func-adl-uproot/) for full functionality.

### Example of a func_adl_xAOD query

```
data = ServiceXDatasetSource(dataset) \
    .Select('lambda e: (e.Electrons("Electrons"), e.Muons("Muons"))') \
    .Select('lambda ls: (ls[0].Select(lambda e: e.pt()), ls[0].Select(lambda e: e.eta()), \
                         ls[0].Select(lambda e: e.phi()), ls[0].Select(lambda e: e.e()), \
                         ls[1].Select(lambda m: m.pt()), ls[1].Select(lambda m: m.eta()), \
                         ls[1].Select(lambda m: m.phi()), ls[1].Select(lambda m: m.e()))') \
    .AsAwkwardArray(('ElePt', 'EleEta', 'ElePhi', 'EleE', 'MuPt', 'MuEta', 'MuPhi', 'MuE')) \
    .value()
```

This is an example of a request submitted to ServiceX using func_adl_xAOD. In this case, this query is meant to pull the electron and muon four-vector components from a dataset identified using a rucio DID and return them to the user in the form of an `awkward` array. The request can be broken into several parts:

The top line, `data = ServiceXDatasetSource(dataset)` specifies which dataset the program should look for. The `dataset` argument is the scope and name of the dataset that the user is specifically looking for.

The following lines are each func_adl transformations on the dataset. func_adl functions by examining lists and transforming them into different types of lists. Top level commands operate directly on lists of events, while nested commands can operate on objects inside those lists. Notice that in each case, the command must be submitted with a lambda function telling it the transformation to be performed. The first command, `.Select('lambda e:...`, creates a tuple consisting of the information in the databanks for electrons and muons. The second command, `.Select('lambda ls:...`, selects a list of all events with either electron or muon information. From there, the nested commands `ls[0].Select(lambda...` operate on the nested lists, and select specific attributes about the leptons. Finally, third command, `.AsAwkwardArray(...` tells ServiceX to return the data as an `awkward` array, and then the command `.value()` executes the query and sends it to `ServiceX`.

It should be noted that all commands except for `.value()` are used only to construct the query, and do not send any information or request anything from `ServiceX`. The entire query is sent using the `.value()` command, and there is no data exchange until that command is sent.

### Commands in a func_adl_xAOD query:

There are a variety of useful operators that can be submitted in a func_adl query. Here, they are listed and explained:

`.Select(...)`
This command transforms the list you are working with, allowing you to select only objects in the list that possess the desired attributes.

`.SelectMany(...)`
This command pulls a nested list up one level. For example, the command `.SelectMany('lambda e: (e.Jets("AntiKt4EMTopoJets"))')` acts on a list of events containing jets (that is, a list of lists - each event is a list of jets), and pulls the jets up one level, so that you are left with a list comprised of the jets that were contained in every event.

`.Where(...)`
This command is a filter that looks for objects in the selection matching the argument. For example, the command `.Where(lambda jpt: jpt>10.0)` filters a selection to only select jets with transverse momentum greater than 10.0.

`.Count()`
This command replaces the list with its length, counting the number of elements. For instance, the command `.Where(lambda jpt: jpt>10.0).Count()` tells the program to count the number of jets in the selection with a transverse momentum greater than 10.0.

`.AsAwkwardArray(...)`
`.AsPandasDF(...)`
These commands specifies how the query should return the selection. Currently, the xAOD backend can return selections as either awkward arrays or pandas dataframes.

`.value()`
This command actually executes the query built by the other commands, sending it to `ServiceX` and then returning the data. 