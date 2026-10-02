"""Scene base class."""


class Scene:
    def __init__(self, app):
        self.app = app

    def update(self):
        pass

    def draw(self, surf):
        pass

    def enter(self):
        """Called when the scene becomes the top of the stack again."""
        pass
