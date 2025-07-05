# Instructions for AI agents working in this repo

* Prefer using `Optional[int]` rather than `int | None`.
* If there is an error the user will see (e.g. `ValueError`), make sure there is enough context in the message for the user. For example, if it is during an expression parse, include the `ast.unparse(a)` in the error message.
