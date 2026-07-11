from enum import Enum

class Scope(Enum):
    BUILTIN = "B"
    GLOBAL = "G"
    ENCLOSING = "E"
    LOCAL = "L"
