import pytest
import func_adl.type_based_replacement as tbr


@pytest.fixture(autouse=True)
def setup_and_teardown():
    tbr.reset_global_functions()
    yield
    tbr.reset_global_functions()
