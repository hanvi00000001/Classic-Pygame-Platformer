"""Keyboard + gamepad mapped to abstract actions with pressed / held / released states."""
import pygame as pg

KEYMAP = {
    "left": (pg.K_LEFT, pg.K_a, pg.K_q),
    "right": (pg.K_RIGHT, pg.K_d),
    "up": (pg.K_UP, pg.K_w, pg.K_z),
    "down": (pg.K_DOWN, pg.K_s),
    "jump": (pg.K_SPACE, pg.K_k, pg.K_c),
    "dash": (pg.K_LSHIFT, pg.K_RSHIFT, pg.K_x, pg.K_l),
    "fire": (pg.K_f, pg.K_j, pg.K_v),
    "pause": (pg.K_ESCAPE, pg.K_p),
    "confirm": (pg.K_RETURN, pg.K_SPACE, pg.K_KP_ENTER),
    "back": (pg.K_ESCAPE, pg.K_BACKSPACE),
}
# Xbox-style layout: A=0 B=1 X=2 Y=3 start=7
PADMAP = {"jump": (0,), "dash": (2, 5), "fire": (1, 3), "pause": (7, 6), "confirm": (0, 7), "back": (1,)}


class Input:
    def __init__(self):
        self.held = {a: False for a in KEYMAP}
        self.prev = dict(self.held)
        self.injected = set()  # actions forced on by scripts (demo / capture mode)
        self.pads = []
        self.refresh_pads()

    def refresh_pads(self):
        self.pads = []
        try:
            for i in range(pg.joystick.get_count()):
                j = pg.joystick.Joystick(i)
                j.init()
                self.pads.append(j)
        except pg.error:
            pass

    def update(self):
        self.prev = dict(self.held)
        keys = pg.key.get_pressed()
        for action, codes in KEYMAP.items():
            self.held[action] = any(keys[c] for c in codes) or action in self.injected
        for pad in self.pads:
            try:
                for action, buttons in PADMAP.items():
                    for b in buttons:
                        if b < pad.get_numbuttons() and pad.get_button(b):
                            self.held[action] = True
                if pad.get_numaxes() >= 2:
                    ax, ay = pad.get_axis(0), pad.get_axis(1)
                    if ax < -0.4: self.held["left"] = True
                    if ax > 0.4: self.held["right"] = True
                    if ay < -0.5: self.held["up"] = True
                    if ay > 0.5: self.held["down"] = True
                if pad.get_numhats():
                    hx, hy = pad.get_hat(0)
                    if hx < 0: self.held["left"] = True
                    if hx > 0: self.held["right"] = True
                    if hy > 0: self.held["up"] = True
                    if hy < 0: self.held["down"] = True
            except pg.error:
                pass

    def pressed(self, action):
        return self.held[action] and not self.prev[action]

    def released(self, action):
        return self.prev[action] and not self.held[action]

    def axis_x(self):
        return (1 if self.held["right"] else 0) - (1 if self.held["left"] else 0)

    def consume(self, action):
        """Mark a press as handled so a following scene doesn't also see it."""
        self.prev[action] = True
