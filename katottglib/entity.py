class KatottgEntity:
    def __init__(self, entity_id, name, category, parent=None):
        self.entity_id = entity_id
        self.name = name
        self.category = category
        self.parent = parent

    def add_parent(self, parent):
        if self.parent is None:
            self.parent = parent
        else:
            self.parent.add_parent(parent)

    def __str__(self, indent=""):
        output = f"{indent}{self.category} - {self.name} [{self.entity_id}]"
        if self.parent:
            output += "\n" + self.parent.__str__(indent + "\t")
        return output
