# Implement a call stack which can be used in all our ast parsers


class argument_stack:
    '''
    Simple stack class to hold name definitions. Each level
    can hide variables in the previous level if their names are the same.
    Otherwise it is possible to see them. When you pop a frame off,
    then all defined variables go away.
    '''
    def __init__(self):
        self._arg_transformer = [{}]

    def push_stack_frame(self):
        'Create a new frame in which to define variables'
        self._arg_transformer.append({})

    def pop_stack_frame(self):
        'Remove the top most stack frame and discard the varables defined there'
        del self._arg_transformer[-1]

    def lookup_name(self, name, default=None):
        '''
        Look up name starting from the deepest frame
        on up until it is found.
        Return name if it is not found.

        name - the name we should look up. Any object that can be a key in a dict
        default - If none, if the name can't be found, return the name. Otherwise return whatever
        default is.
        '''
        for frames in reversed(self._arg_transformer):
            if name in frames:
                return frames[name]
        return name if default is None else default

    def define_name(self, name, val):
        'Add a definition to the current deepest stack frame'
        self._arg_transformer[-1][name] = val


class stack_frame:
    '''
    Python resource management class to deal with
    putting a stack frame on.
    '''
    def __init__(self, arg_stack):
        self._arg_stack = arg_stack

    def __enter__(self):
        self._arg_stack.push_stack_frame()
        return None

    def __exit__(self, type, value, traceback):
        self._arg_stack.pop_stack_frame()
        return None
