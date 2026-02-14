import ast
from typing import Dict, List, Optional

from func_adl import EventDataset
from func_adl.ast.meta_data import (
    extract_metadata,
    lookup_query_metadata,
    remove_duplicate_metadata,
    remove_empty_metadata,
)


def compare_metadata(with_metadata: str, without_metadata: str) -> List[Dict[str, str]]:
    """
    Compares two AST expressions after first removing all metadata references from the
    first expression. Returns a list of dictionaries of the found metadata
    """
    a_with = ast.parse(with_metadata)
    a_without = ast.parse(without_metadata)

    a_removed, metadata = extract_metadata(a_with)

    assert ast.dump(a_removed) == ast.dump(a_without)
    return metadata


def test_no_metadata():
    "Make sure expression with no metadata is not changed"
    meta = compare_metadata("Select(jets, lambda j: j*2)", "Select(jets, lambda j: j*2)")
    assert len(meta) == 0


def test_simple_metadata():
    "Make sure expression with metadata correctly cleaned up and removed"
    meta = compare_metadata(
        "MetaData(Select(jets, lambda j: j*2), {'hi': 'there'})", "Select(jets, lambda j: j*2)"
    )
    assert len(meta) == 1
    assert meta[0] == {"hi": "there"}


def test_two_metadata():
    "Make sure expression with no metadata is not changed"
    meta = compare_metadata(
        "MetaData(Select(MetaData(jets, {'fork': 'dude'}), lambda j: j*2), {'hi': 'there'})",
        "Select(jets, lambda j: j*2)",
    )
    assert len(meta) == 2
    assert meta[0] == {"hi": "there"}
    assert meta[1] == {"fork": "dude"}


class my_event(EventDataset):
    async def execute_result_async(self, a: ast.AST, title: Optional[str] = None):
        return a


def test_query_metadata_found():
    r = (
        my_event()
        .QMetaData({"one": "two", "two": "three"})
        .SelectMany("lambda e: e.jets()")
        .Select("lambda j: j.pT()")
    )

    assert lookup_query_metadata(r, "one") == "two"


def test_query_metadata_not_found():
    r = (
        my_event()
        .QMetaData({"one": "two", "two": "three"})
        .SelectMany("lambda e: e.jets()")
        .Select("lambda j: j.pT()")
    )

    assert lookup_query_metadata(r, "three") is None


def test_query_metadata_burried():
    r = (
        my_event()
        .QMetaData({"three": "forks"})
        .SelectMany("lambda e: e.jets()")
        .QMetaData({"one": "two", "two": "three"})
        .Select("lambda j: j.pT()")
    )

    assert lookup_query_metadata(r, "three") == "forks"


def test_query_metadata_updated():
    """This is testing code in QMetaData, but we need lookup_query_metadata which we are
    testing in this file"""
    r = my_event().QMetaData({"one": "two"}).QMetaData({"one": "three"})

    assert lookup_query_metadata(r, "one") == "three"


def test_remove_empty_metadata_empty():
    r = remove_empty_metadata(my_event().MetaData({}).query_ast)
    assert "MetaData" not in ast.dump(r)


def test_remove_empty_metadata_not_empty():
    r = remove_empty_metadata(my_event().MetaData({"hi": "there"}).query_ast)
    assert "MetaData" in ast.dump(r)


def test_remove_metadata_no_change():
    "Removing metadata should not alter original query"
    orig = my_event().MetaData({})
    remove_empty_metadata(orig.query_ast)

    assert "MetaData" in ast.dump(orig.query_ast)


def test_remove_metadata_no_change_2_levels():
    "Removing metadata should not alter original query"
    orig = my_event().MetaData({}).MetaData({})
    remove_empty_metadata(orig.query_ast)

    assert "MetaData" in ast.dump(orig.query_ast)


def test_remove_duplicate_metadata_nested_duplicate_calls():
    orig = my_event().MetaData({"k": "v"}).MetaData({"k": "v"}).MetaData({"x": "y"})

    r = remove_duplicate_metadata(orig.query_ast)

    assert ast.dump(r).count("MetaData") == 2
    assert "'k': 'v'" in ast.unparse(r)
    assert "'x': 'y'" in ast.unparse(r)


def test_remove_duplicate_metadata_not_duplicate_payloads_retained():
    r = remove_duplicate_metadata(my_event().MetaData({"k": "v"}).MetaData({"k": "vv"}).query_ast)

    assert ast.dump(r).count("MetaData") == 2


def test_remove_empty_and_duplicate_metadata_together():
    r = remove_duplicate_metadata(
        remove_empty_metadata(my_event().MetaData({}).MetaData({}).query_ast)
    )

    assert "MetaData" not in ast.dump(r)
