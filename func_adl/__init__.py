# flake8: noqa

# Dataset accessors
from .event_dataset import EventDataset, find_EventDataset

# Extra LINQ-like functions
from .functions import Range

# Main streaming object
from .object_stream import ObjectStream

# Decorators to add extra functionally to the module
from .type_based_replacement import (
    func_adl_callable,
    func_adl_callback,
    func_adl_parameterized_call,
    register_func_adl_os_collection,
)
