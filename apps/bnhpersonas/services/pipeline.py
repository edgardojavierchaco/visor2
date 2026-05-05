class Pipeline:

    def __init__(self, steps):
        self.steps = steps

    def run(self, obj, user=None):
        for step in self.steps:
            obj = step.apply(obj, user)
        return obj