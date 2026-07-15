from enum import Enum
from dataclasses import dataclass, field
from uuid import UUID

class Scope(Enum):
    BUILTIN = "B"
    GLOBAL = "G"
    ENCLOSING = "E"
    LOCAL = "L"
    CLASS = "C"

@dataclass
class ScopeFrame:
    namespace_id: UUID
    symbol_table: object
    scope_kind: Scope
    start_line: int = 0
    end_line: int = 0
    mutated_symbols: dict = field(default_factory=dict)
