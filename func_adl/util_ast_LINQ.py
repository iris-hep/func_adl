# Helpers for LINQ operators and LINQ expressions in AST form.
# Utility routines to manipulate LINQ expressions.
from func_adl import Select, SelectMany, Where, First
from func_adl.util_ast import lambda_unwrap
import ast
from typing import Union, Optional


def parse_as_ast(ast_source: Union[str, ast.AST]) -> ast.Lambda:
    r'''Return an AST for a lambda function from several sources.

    We are handed one of several things:
        - An AST that is a lambda function
        - An AST that is a pointer to a Module that wraps an AST
        - Text that contains properly formatted ast code for a lambda function.

    In all cases, return a lambda function as an AST starting from the AST top node.

    Args:
        ast_source:     An AST or text string that represnets the lambda.

    Returns:
        An ast starting from the Lambda AST node.
    '''
    if isinstance(ast_source, str):
        a = ast.parse(ast_source.strip())
        return lambda_unwrap(a)
    else:
        return lambda_unwrap(ast_source)


class ReplaceLINQOperators(ast.NodeTransformer):
    r'''
    A python 3 AST tranformer to replace function calls in the AST that are actually LINQ operators.

    ObjectStream has methods called Select and SelectMany. When they are called, they build up the AST tree. But they do that
    by creating Select and SelectMany, etc., ast nodes. When we parse a lambda passed as text, that does not happen. This
    NodeTransformer does that replacement in-place.
    '''

    def visit_Call(self, node: ast.Call) -> Optional[ast.AST]:
        '''Look for LINQ type calls and make a replacement with the appropriate AST entry
        TODO: Make sure this is recursive properly!
        '''
        if isinstance(node.func, ast.Attribute):
            func_name = node.func.attr
            if func_name == "Select":
                source = self.visit(node.func.value)
                selection = self.visit(node.args[0])
                return Select(source, selection)
            elif func_name == "SelectMany":
                source = self.visit(node.func.value)
                selection = self.visit(node.args[0])
                return SelectMany(source, selection)
            elif func_name == "Where":
                source = self.visit(node.func.value)
                filter = self.visit(node.args[0])
                return Where(source, filter)
            elif func_name == "First":
                source = self.visit(node.func.value)
                return First(source)
            # Fall through to process the inside in the next step.
        return self.generic_visit(node)
