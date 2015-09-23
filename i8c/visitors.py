class Visitable(object):
    @property
    def classname(self):
        result = self.__class__.__name__
        if result.startswith("Synthetic"):
            result = result[len("Synthetic"):] + "Op"
        return result

    def accept(self, visitor):
        getattr(visitor, "visit_" + self.classname.lower())(self)
