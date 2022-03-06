import ast
import sys
from typing import Any, List

from func_adl.util_ast import lambda_build

if sys.version_info >= (3, 9):

    def unparse_ast(a: ast.AST) -> str:
        return ast.unparse(a)

else:  # pragma: no cover

    def unparse_ast(a: ast.AST) -> str:
        return ast.dump(a)


def resolve_syntatic_sugar(a: ast.AST) -> ast.AST:
    """Transforms python idioms into func_adl statements where it makes sense

    * List comprehensions are turned into `Select` statements
    * Generator expressions are turned into `Select` statements

    Args:
        a (ast.AST): The AST to scan for syntatic sugar

    Returns:
        ast.AST: The resolved syntax
    """

    class syntax_transformer(ast.NodeTransformer):
        def resolve_generator(
            self, lambda_body: ast.AST, generators: List[ast.comprehension], node: ast.AST
        ) -> ast.AST:
            """Translate a list comprehension or a generator to Select statements.

            `[j.pt() for j in jets] -> jets.Select(lambda j: j.pt())`

            Args:
                lambda_body (ast.AST): The target of the lambda expression
                generators (List[ast.comprehension]): The list of generators
                node (ast.AST): The original AST node

            Returns:
                ast.AST: The reformed ast (untouched if no expression detected)
            """
            a = node
            for c in reversed(generators):
                target = c.target
                if not isinstance(target, ast.Name):
                    raise ValueError(
                        f"Comprehension variable must be a name, but found {target}"
                        f" - {unparse_ast(node)}."
                    )
                if c.is_async:
                    raise ValueError(f"Comprehension can't be async - {unparse_ast(node)}.")
                source_collection = c.iter

                # Turn the if clauses into Where statements
                for a_if in c.ifs:
                    where_function = lambda_build(target.id, a_if)
                    source_collection = ast.Call(
                        func=ast.Attribute(attr="Where", value=source_collection, ctx=ast.Load()),
                        args=[where_function],
                        keywords=[],
                    )

                lambda_function = lambda_build(target.id, lambda_body)
                a = ast.Call(
                    func=ast.Attribute(attr="Select", value=source_collection, ctx=ast.Load()),
                    args=[lambda_function],
                    keywords=[],
                )

                # In case we have chained comprehensions
                lambda_body = a
            return a

        def visit_ListComp(self, node: ast.ListComp) -> Any:
            "Translate a list comprehension into a Select statement"
            a = self.generic_visit(node)

            if isinstance(a, ast.ListComp):
                a = self.resolve_generator(a.elt, a.generators, node)

            return a

        def visit_GeneratorExp(self, node: ast.GeneratorExp) -> Any:
            "Translate a generator into a Select statement"
            a = self.generic_visit(node)

            if isinstance(a, ast.GeneratorExp):
                a = self.resolve_generator(a.elt, a.generators, node)

            return a

    return syntax_transformer().visit(a)
