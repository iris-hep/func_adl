# Stuff to calculate a hash of an ast
import ast
import hashlib


def calc_ast_hash(a: ast.AST) -> str:
    '''Calculate the hash for an AST.

    This hash takes into account everything about the ast,
    including the input datasets
    '''

    b = bytearray()
    b.extend(map(ord, ast.dump(a)))
    return hashlib.md5(b).hexdigest()
