# Simplify tuple access.
import ast


class remove_tuple_subscripts(ast.NodeTransformer):
    r'''
    Turns (e1, e2, e3)[0] into just e1.
    '''

    def visit_Subscript(self, subscript):
        '''If the index is on a tuple, then we extract the data from the tuple
        and return that instead. This allows one to use a tuple as shorthand without having
        to worry about evaluating things that aren't required.
        '''
        if type(subscript.value) is ast.Tuple:
            # We have to deal with the index
            if type(subscript.slice) is not ast.Index:
                raise BaseException("Tuples can only be indexed by simple index object")
            if type(subscript.slice.value) is not ast.Num:
                raise BaseException("Tuples can only be indexed by simple number")
            index = subscript.slice.value.n

            if index >= len(subscript.value.elts):
                raise BaseException("Attempt to index tuple out of bounds")

            return self.visit(subscript.value.elts[index])

        return self.generic_visit(subscript)
