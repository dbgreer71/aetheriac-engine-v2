"""
Concept compilation error definitions.

This module defines typed exceptions for concept card compilation errors.
"""


class ConceptCompileError(Exception):
    """Exception raised when concept card compilation fails.

    Args:
        code: Error code identifying the type of failure
        msg: Human-readable error message
    """

    def __init__(self, code: str, msg: str):
        self.code = code
        self.msg = msg
        super().__init__(f"{code}: {msg}")

    def __str__(self) -> str:
        return f"{self.code}: {self.msg}"
