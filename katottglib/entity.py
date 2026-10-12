class KatottgEntity:
    """One object of the codifier, with its chain of ancestors."""

    def __init__(
        self, entity_id, name, category, parent=None, category_code=None
    ):
        self.entity_id = entity_id
        self.name = name
        self.category = category
        self.category_code = category_code
        self.parent = parent

    def add_parent(self, parent):
        if self.parent is None:
            self.parent = parent
        else:
            self.parent.add_parent(parent)

    @property
    def parents(self):
        """Ancestors from the direct parent outwards."""
        chain = []
        current = self.parent
        while current is not None:
            chain.append(current)
            current = current.parent
        return chain

    @property
    def is_top_level(self) -> bool:
        return self.parent is None

    @property
    def path(self) -> str:
        """``Київська, Бориспільський, ... , Кийлів`` — broadest first."""
        return ", ".join(
            entity.name for entity in [*reversed(self.parents), self]
        )

    def __eq__(self, other):
        if not isinstance(other, KatottgEntity):
            return NotImplemented
        return self.entity_id == other.entity_id

    def __hash__(self):
        return hash(self.entity_id)

    def __repr__(self):
        return (
            f"KatottgEntity({self.entity_id!r}, {self.name!r}, "
            f"{self.category_code!r})"
        )

    def __str__(self, indent=""):
        output = f"{indent}{self.category} - {self.name} [{self.entity_id}]"
        if self.parent:
            output += "\n" + self.parent.__str__(indent + "\t")
        return output
