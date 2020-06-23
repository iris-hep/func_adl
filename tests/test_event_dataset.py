# Test that the event dataset works correctly.
import sys
sys.path += ['.']
from func_adl import EventDataset

import pytest

def test_cannot_create():
    EventDataset()

