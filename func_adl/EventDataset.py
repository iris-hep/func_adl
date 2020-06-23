# Event dataset
from urllib import parse
from urllib.parse import ParseResult
from abc import ABC

from .ObjectStream import ObjectStream
from .util_ast import function_call


class EventDatasetURLException (Exception):
    '''
    Exception thrown if the dataset URL passed is not valid
    '''
    def __init__(self, message):
        Exception.__init__(self, message)


def _parse_and_check_dataset_url(u: str) -> ParseResult:
    '''
    Returns a parsed URL and the url, after checking the url's to make sure there
    is enough inforation in them. It throws if there is a problem.

    Args
        u       String

    Returns:
        u       The original URL
        parsed  The URL that was parsed by url2 lib.
    '''
    r = parse.urlparse(u)
    if r.scheme is None or len(r.scheme) == 0:
        raise EventDatasetURLException(f'EventDataSet({u}) has no scheme (file://, localds://, etc.)')
    if (r.netloc is None or len(r.netloc) == 0) and len(r.path) == 0:
        raise EventDatasetURLException(f'EventDataSet({u}) has no dataset or filename')

    return r


class EventDataset(ObjectStream):
    r'''
    Represents a stream of events that originates from a dataset. This class
    should be sub-classed with the information about the actual dataset.
    '''
    def __init__(self):
        '''
        Should not be called directly
        '''
        # We participate in the AST parsing - as a node. So make sure the fields that should be traversed are
        # set. This is mostly set as a way to show what a subclass would need to do in order
        # to change this into an actual ast. Extra info is only needed if the info about the dataset is meant
        # to leave the local computer.
        self._ast = function_call('EventDataset', [])
