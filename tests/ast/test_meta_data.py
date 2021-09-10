

import ast
from func_adl.ast.meta_data import extract_metadata
from typing import Dict, List


def compare_metadata(with_metadata: str, without_metadata: str) -> List[Dict[str, str]]:
    '''
    Compares two AST expressions after first removing all metadata references from the
    first expression. Returns a list of dictionaries of the found metadata
    '''
    a_with = ast.parse(with_metadata)
    a_without = ast.parse(without_metadata)

    a_removed, metadata = extract_metadata(a_with)

    assert ast.dump(a_removed) == ast.dump(a_without)
    return metadata


def test_no_metadata():
    'Make sure expression with no metadata is not changed'
    meta = compare_metadata("Select(jets, lambda j: j*2)", "Select(jets, lambda j: j*2)")
    assert len(meta) == 0


def test_simple_metadata():
    'Make sure expression with metadata correctly cleaned up and removed'
    meta = compare_metadata("MetaData(Select(jets, lambda j: j*2), {'hi': 'there'})", "Select(jets, lambda j: j*2)")
    assert len(meta) == 1
    assert meta[0] == {'hi': 'there'}


def test_two_metadata():
    'Make sure expression with no metadata is not changed'
    meta = compare_metadata("MetaData(Select(MetaData(jets, {'fork': 'dude'}), lambda j: j*2), {'hi': 'there'})", "Select(jets, lambda j: j*2)")
    assert len(meta) == 2
    assert meta[0] == {'hi': 'there'}
    assert meta[1] == {'fork': 'dude'}
