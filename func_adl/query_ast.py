# Contains AST classes for the query part of an expression.
# This is an extension of the python AST, and is written in that same style.
#
# AST's are designed to have only data, no code. In that sense, they could
# be transmitted over the wire and received at the other end.
#
# Of course, this being python, it is possible to add new things to the class
# member variables.
import ast

###############################
# First, the sequences


class SelectMany(ast.AST):
    r"""
    AST node for SelectMany. A selection function picks out
    a collection, and then one iterates over that collection.
    """

    def __init__(self, source=None, selection_function=None):
        r"""
        AST node that represents a SelectMany operation. It's resulting type is an iterator
        over the collection selected by ``selection_function``.

        Args:
            source:                 An AST that represents the source stream of objects.
            selection_function:     A lambda that selects a collection to iterate over when applied to source.
                                    The lambda is unwrapped (e.g. it is a Lambda ast node)
        """
        self.source = source
        self.selection = selection_function
        self._fields = ('source', 'selection')


class Select(ast.AST):
    r"""
    AST node for Select. Transforms the input to the output by applying
    a selection function.
    """

    def __init__(self, source=None, select_function=None):
        r"""
        Initialize an AST node that represents a Select operation. As input takes an iterator
        and transforms it to another iterator by applying ``select_function`` to each individual
        object.

        Args:
            source:             An AST that represents the source iterator.
            select_function:    function that operates on each item of the source.
                                The lambda is unwrapped (e.g. it is a Lambda ast node)
        """
        self.selection = select_function
        self.source = source
        self._fields = ('source', 'selection')


class Where(ast.AST):
    r'''
    AST node for filtering: Where. Filters input, only allowing parts of the sequence that
    satisfy the operator to move on.
    '''

    def __init__(self, source=None, filter=None):
        r'''
        Initialize an AST node that represents a filter operation (Where). As input takes
        an iterator and only lets through items in the sequence that pass the `filter_lambda`
        criteria.

        Args:
            source:         An AST that represents the source sequence.
            filter_lambda:  a filter function to be applied to the sequence.
                            The lambda is unwrapped (e.g. it is a Lambda ast node)
        '''
        self.source = source
        self.filter = filter
        self._fields = ('source', 'filter')


# The terminals
class First(ast.AST):
    r'''
    AST Node for taking the first element of a sequence. Returns the object for use, and also pops the sequence
    up one level.
    '''

    def __init__(self, source=None):
        r'''
        Initialize the First AST node.

        source - AST of the source sequence.
        '''
        self.source = source
        self._fields = ('source',)
