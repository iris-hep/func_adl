# AST and friends that denote a note that will emit a TTree.
import ast
from collections import namedtuple


class ResultTTree(ast.AST):
    r'''
    An AST node that transforms a iterator into a TTree file.
    '''

    def __init__(self, source=None, column_names=None, tree_name=None, filename=None):
        r'''
        Initialize the resultTTree AST node.

        source - The iterator containing the data that is to be written out to a TTree.
        column_names - Names of each column to be written out. Each is a string.
        '''
        self.source = source
        self.column_names = (column_names,) if type(column_names) == str else column_names
        self.tree_name = tree_name
        self.filename = filename
        self._fields = ('source', 'column_names', 'tree_name')


# Tree result for an individual file. Contains the tree name and the filename url.
ROOTTreeFileInfo = namedtuple('ROOTTreeFileInfo', 'filename treename')
# The complete result, contains a list of files and something that indicates all possbile data
# is present.
ROOTTreeResult = namedtuple('ROOTTreeResult', 'is_complete fileinfo_list')


class ResultPandasDF(ast.AST):
    r'''
    An AST node that indicates we should be rendering everything
    coming into us as a Pandas DF. This will have restrictions on the
    data format - for example, it needs to be a flat array.
    '''

    def __init__(self, source=None, column_names=None):
        r'''
        Initialize the pandas df AST node.

        source - The iterator containing the data that is to be written into the DF
        column_names - The names of the columns that are going in.
        '''
        self.source = source
        self.column_names = column_names
        self._fields = ('source', 'column_names')


class ResultAwkwardArray(ast.AST):
    r'''
    An AST node that indicates we should be rendering everything
    coming into us as an awkward array.
    '''

    def __init__(self, source=None, column_names=None):
        r'''
        Initialize the awkward array AST node.

        source - The iterator containing the data that is to be written into the DF
        column_names - The names of the columns that are going in.
        '''
        self.source = source
        self.column_names = column_names
        self._fields = ('source', 'column_names')
