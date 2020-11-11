import ast
import sys
from func_adl.util_ast import function_call
from typing import cast


def _generate_count_call(seq: ast.AST, lambda_string: str = "lambda acc,v: acc+1") -> ast.Call:
    r'''
        Given a sequence, generate an Aggregate call that will count the number
        of items in the sequence.

        seq: The sequence to be counted

        returns:
        agg_ast - An ast call to the Aggregate call.
    '''
    agg_lambda = cast(ast.Expr, ast.parse(lambda_string).body[0]).value
    agg_start = ast.Num(0) if sys.version_info < (3, 8, 0) else ast.Constant(0, kind=None)

    return function_call('Aggregate', [seq, cast(ast.AST, agg_start), cast(ast.AST, agg_lambda)])


class aggregate_node_transformer(ast.NodeTransformer):
    r'''
    Look for a few terminals and translate them into calls to Aggregate instead:

        Count()

    '''

    def visit_Call(self, node):
        if type(node.func) is ast.Name:
            if (node.func.id == 'len' or node.func.id == "Count") and (len(node.args) == 1):
                # This is a len(sequence) call, which should be turned into a .Count() call.
                return _generate_count_call(self.visit(node.args[0]))
            elif node.func.id == "Sum":
                return _generate_count_call(self.visit(node.args[0]), "lambda acc,v: acc + v")
            elif node.func.id == "Max":
                return _generate_count_call(self.visit(node.args[0]),
                                            "lambda acc,v: acc if acc > v else v")
            elif node.func.id == "Min":
                return _generate_count_call(self.visit(node.args[0]),
                                            "lambda acc,v: acc if acc < v else v")
        return self.generic_visit(node)
