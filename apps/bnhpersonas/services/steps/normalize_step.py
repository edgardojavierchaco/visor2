class NormalizeStep:

    @staticmethod
    def apply(obj, user=None):

        if hasattr(obj, "normalize"):
            obj.normalize()

        return obj