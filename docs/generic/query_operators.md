# Query Operators

FuncADL is inspired by functional languages and C#’s LINQ. If you would like to learn more about LINQ, you can refer to the following resources:

[See Wikipedia](https://en.wikipedia.org/wiki/Language_Integrated_Query)

<!-- TODO: Add full API reference page for the functions in FuncADL -->

## FuncADL Query Operators

In order to use FuncADL it is helpful to understand the query operators that are available. 

### SelectMany

Given that the current stream's object type is an array or other iterable, 
this both transforms and flattens it by returning the contained items one by one.

    Arguments:
        func:   The function that should be applied to this stream's objects to return
            a transformed object. Each item of the iterable is now the stream of objects.

    Returns:
        A new ObjectStream of the type of the elements.

    Notes:
        - The function can be a `lambda`, the name of a one-line function, a string that
            contains a lambda definition, or a python `ast` of type `ast.Lambda`.

### Select

Apply a transformation function to each object in the stream, yielding a new type of
object. There is a one-to-one correspondence between the input objects and output objects.

    Arguments:
        f: selection function (lambda)

    Returns:
        A new ObjectStream of the transformed elements.

    Notes:
        - The function can be a `lambda`, the name of a one-line function, a string that
        contains a lambda definition, or a python `ast` of type `ast.Lambda`.

<!-- ### SelectMany vs Select

    TODO: Add an example that illustrates the difference between these two things.

To help illustrate the difference between `Select` and `SelectMany`, consider the following example: -->

### Where

Filter the object stream, allowing only items for which `filter` evaluates as true through.

    Arguments:
        filter: A filter lambda that returns True/False.

    Returns:
        A new ObjectStream that contains only elements that pass the filter function

    Notes:
        - The function can be a `lambda`, the name of a one-line function, a string that
        contains a lambda definition, or a python `ast` of type `ast.Lambda`.

## Advanced Query Operators

### MetaData

Add metadata to the current object stream. The metadata is an arbitrary set of string key-value pairs. The backend must be able to properly interpret the metadata.

    Returns:
        ObjectStream: A new stream, of the same type and contents, but with metadata added.

### QMetaData

Add query metadata to the current object stream.

- Metadata is never transmitted to any back end
- Metadata is per-query, not per sample.

Warnings are issued if metadata is overwriting metadata.

    Args:
        metadata (Dict[str, Any]): Metadata to be used later

    Returns:
        ObjectStream[T]: The object stream, with metadata attached
