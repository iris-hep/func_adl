# Event dataset
from urllib import parse
from urllib.parse import ParseResult
from .ObjectStream import ObjectStream
from .util_ast import function_call, as_ast
from typing import Union, Iterable


class EventDatasetURLException (BaseException):
    '''
    Exception thrown if the dataset URL passed is not valid
    '''
    def __init__(self, message):
        BaseException.__init__(self, message)


def _fixup_url(url: str, parsed_url) -> str:
    '''
    Fix up the url if we need to normalize anything

    Arguments:
        url         The URL to fix up
        parsed_url  The output of the URL parsing

    Returns:
        url         The URL fixed up. If it is a windows path, remove the extra
                    directory divider, for example.
    '''
    if parsed_url.scheme != 'file':
        return url

    # For file, we need to deal with file://path and file:///path.
    # If netloc is something we can quickly recognize as a local path or empty,
    # then this url is in good shape.
    if len(parsed_url.netloc) == 0 or parsed_url.netloc == 'localhost':
        return f'file://{parsed_url.path}'

    # Assume that netloc was part of the path.
    path = parsed_url.netloc
    if len(parsed_url.path) > 0:
        path = path + parsed_url.path
    return f'file:///{path}'


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
    Represents a stream of events that originates from a dataset specified by some sort of URL.
    '''
    def __init__(self, url: Union[str, Iterable[str]] = None):
        r'''
        Create and hold an event dataset reference. From one file, to multiple
        files, to a dataset specified otherwise.

        Args:
            url (str):  Must be a valid URL that points to a valid dataset

        Raises:
            Invalid URL
        '''
        if url is not None:
            # Normalize the URL as a list
            if isinstance(url, str):
                url = [url]
            l_url = list(url)

            if len(l_url) == 0:
                raise EventDatasetURLException("EventDataset initialized with an empty URL")

            # Make sure we can parse this URL. We don't, at some level, care about the actual contents.
            self.url = [_fixup_url(u, _parse_and_check_dataset_url(u)) for u in l_url]
        else:
            self.url = None

        # We participate in the AST parsing - as a node. So make sure the fields that should be traversed are
        # set.
        self._ast = function_call('EventDataset', [as_ast(self.url), ])
