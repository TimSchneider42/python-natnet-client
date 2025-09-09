class Event:
    def __init__(self):
        self.handlers = []

    def call(self, *args, **kwargs):
        for h in self.handlers:
            h(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        self.call(*args, **kwargs)
