class Concrete():
    pass

class Unassigned():
    def __eq__(self, other) -> bool:
        return isinstance(other, Unassigned)

    def __repr__(self) -> str:
        return "lattice<Unassigned>"


class Unknown:
    def __eq__(self, other) -> bool:
        return isinstance(other, Unknown)

    def __repr__(self) -> str:
        return "lattice<Unknown>"

class Union():
    def __init__(self) -> None:
        self.members: set = set()

    def __str__(self) -> str:
        return " | ".join(
            sorted(
                getattr(m, "__name__", str(m))
                for m in self.members
                if m is not Unassigned
            )
        )

    def __repr__(self) -> str:
        return f"lattice.Union({{{self.__str__()}}})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, Union):
            return NotImplemented
        return self.members == other.members

    def __hash__(self) -> int:
        return hash(frozenset(self.members))

def join(a, b) -> type:
    # ⊥ disappears
    if isinstance(a, Unassigned):
        return b
    if isinstance(b, Unassigned):
        return a
    # ⊤ absorbs
    if isinstance(a, Unknown) or isinstance(b, Unknown):
        return Unknown()
    # identical — no union needed
    if a == b:
        return a
    # case 2a: concrete + concrete
    if not isinstance(a, Union) and not isinstance(b, Union):
        u = Union()
        u.members = {a, b}
        return u
    # case 2b: one is Union, one is concrete
    if isinstance(a, Union) and not isinstance(b, Union):
        u = Union()
        u.members = a.members | {b}
        return u
    if isinstance(b, Union) and not isinstance(a, Union):
        u = Union()
        u.members = b.members | {a}
        return u
    # case 2c: both Union
    u = Union()
    u.members = a.members | b.members
    return u
    