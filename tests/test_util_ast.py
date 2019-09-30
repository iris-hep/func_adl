# Tests for ast_util.py

# Now the real test code starts.
from func_adl.util_ast import lambda_is_identity, lambda_test, lambda_is_true
import ast

# Identity
def test_identity_is():
    assert lambda_is_identity(ast.parse('lambda x: x')) == True

def test_identity_isnot_body():
    assert lambda_is_identity(ast.parse('lambda x: x+1')) == False

def test_identity_isnot_args():
    assert lambda_is_identity(ast.parse('lambda x,y: x')) == False

def test_identity_isnot_body_var():
    assert lambda_is_identity(ast.parse('lambda x: x1')) == False

# Is this a lambda?
def test_lambda_test_expression():
    assert lambda_test(ast.parse("x")) == False

def test_lambda_test_lambda_module():
    assert lambda_test(ast.parse('lambda x: x')) == True

def test_lambda_test_raw_lambda():
    rl = ast.parse('lambda x: x').body[0].value
    assert lambda_test(rl) == True

# Is this lambda always returning true?
def test_lambda_is_true_yes():
    assert lambda_is_true(ast.parse("lambda x: True")) == True

def test_lambda_is_true_no():
    assert lambda_is_true(ast.parse("lambda x: False")) == False

def test_lambda_is_true_expression():
    assert lambda_is_true(ast.parse("lambda x: x")) == False
    