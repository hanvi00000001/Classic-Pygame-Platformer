"""Every sound is synthesised at runtime: chiptune sound effects plus a small
procedural composer that writes a looping track per biome. Music is rendered
bar by bar inside the game loop (a few ms per frame), so it also works in the
browser build where threads are not available."""
import array
import math
import random
import time

import pygame as pg

_audio = None

NOTE_A4 = 440.0


def midi(n):
    return NOTE_A4 * 2 ** ((n - 69) / 12)


SCALES = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "mixo": [0, 2, 4, 5, 7, 9, 10],
    "harmonic": [0, 2, 3, 5, 7, 8, 11],
    "phrygian": [0, 1, 3, 5, 7, 8, 10],
}

SONGS = {
    "title": dict(bpm=92, root=57, scale="dorian", prog=[0, 3, 5, 4], lead="tri", bass="soft", drums="soft", seed=3, echo=0.3),
    "meadow": dict(bpm=128, root=60, scale="major", prog=[0, 4, 5, 3], lead="sq", bass="bounce", drums="pop", seed=11),
    "caves": dict(bpm=88, root=57, scale="minor", prog=[0, 5, 2, 6], lead="tri", bass="soft", drums="soft", seed=5, echo=0.45),
    "sunset": dict(bpm=104, root=62, scale="mixo", prog=[0, 6, 3, 0], lead="sq", bass="walk", drums="pop", seed=21, echo=0.2),
    "frost": dict(bpm=80, root=59, scale="minor", prog=[0, 3, 5, 4], lead="bell", bass="soft", drums="soft", seed=8, echo=0.4),
    "volcano": dict(bpm=146, root=52, scale="phrygian", prog=[0, 1, 0, 6], lead="saw", bass="drive", drums="rock", seed=13),
    "boss": dict(bpm=162, root=52, scale="harmonic", prog=[0, 5, 1, 4], lead="sq", bass="drive", drums="rock", seed=99),
    "legacy": dict(bpm=140, root=60, scale="major", prog=[0, 3, 4, 0], lead="sq", bass="bounce", drums="pop", seed=2022),
    "map": dict(bpm=100, root=55, scale="major", prog=[0, 3, 0, 4], lead="tri", bass="walk", drums="soft", seed=7, echo=0.25),
}


class Audio:
    def __init__(self):
        self.ok = False
        self.rate = 22050
        self.channels = 1
        try:
            if not pg.mixer.get_init():
                pg.mixer.init(22050, -16, 1, 512)
            self.rate, _, self.channels = pg.mixer.get_init()
            pg.mixer.set_num_channels(24)
            self.ok = True
        except (pg.error, TypeError):
            self.ok = False
        self.sfx = {}
        self.sfx_volume = 0.7
        self.music_volume = 0.5
        self.tracks = {}
        self.jobs = {}
        self.want = None
        self.playing = None
        self.channel = None
        if self.ok:
            self._build_sfx()

    # ------------------------------------------------------------------ util
    def _sound(self, samples, vol=1.0):
        peak = max(1e-6, max(abs(s) for s in samples))
        k = min(1.0, 0.95 / peak) * vol * 32767
        ints = array.array("h", (int(s * k) for s in samples))
        if self.channels == 2:
            st = array.array("h", bytes(len(ints) * 4))
            st[0::2] = ints
            st[1::2] = ints
            ints = st
        return pg.mixer.Sound(buffer=ints.tobytes())

    def _tone(self, f0, f1, dur, wave="sq", vol=1.0, duty=0.5, attack=0.005, curve=1.0, vib=0.0, noise_mix=0.0):
        n = int(self.rate * dur)
        out = [0.0] * n
        ph = 0.0
        lp = 0.0
        for i in range(n):
            t = i / n
            f = f0 + (f1 - f0) * (t ** curve)
            if vib:
                f *= 1 + vib * math.sin(i / self.rate * 38)
            ph += f / self.rate
            p = ph % 1.0
            if wave == "sq":
                v = 1.0 if p < duty else -1.0
            elif wave == "tri":
                v = 4 * abs(p - 0.5) - 1
            elif wave == "saw":
                v = 2 * p - 1
            elif wave == "sine":
                v = math.sin(ph * math.tau)
            else:
                v = 0.0
            if noise_mix:
                lp += (random.uniform(-1, 1) - lp) * 0.5
                v = v * (1 - noise_mix) + lp * noise_mix
            env = min(1.0, (i / self.rate) / attack) if attack else 1.0
            env *= (1 - t) ** 1.4
            out[i] = v * env * vol
        return out

    def _noise(self, dur, vol=1.0, cutoff0=0.9, cutoff1=0.05, decay=1.5):
        n = int(self.rate * dur)
        out = [0.0] * n
        y = 0.0
        for i in range(n):
            t = i / n
            a = cutoff0 + (cutoff1 - cutoff0) * t
            y += (random.uniform(-1, 1) - y) * a
            out[i] = y * (1 - t) ** decay * vol
        return out

    def _seq(self, parts):
        out = []
        for p in parts:
            out.extend(p)
        return out

    def _mix(self, *bufs):
        n = max(len(b) for b in bufs)
        out = [0.0] * n
        for b in bufs:
            for i, v in enumerate(b):
                out[i] += v
        return out

    def _arp(self, notes, step, wave="sq", vol=0.6, duty=0.5, tail=1.0):
        parts = []
        for k, n in enumerate(notes):
            d = step * (tail if k == len(notes) - 1 else 1)
            parts.append(self._tone(midi(n), midi(n), d, wave, vol, duty))
        return self._seq(parts)

    def _build_sfx(self):
        T, N = self._tone, self._noise
        s = {}
        s["jump"] = T(280, 620, 0.13, "sq", 0.5, 0.25, curve=0.6)
        s["jump2"] = self._mix(T(420, 900, 0.16, "tri", 0.6, curve=0.5), T(840, 1800, 0.16, "sq", 0.15, 0.125))
        s["walljump"] = T(340, 700, 0.12, "sq", 0.45, 0.5, curve=0.5)
        s["land"] = N(0.07, 0.5, 0.5, 0.05, 2.0)
        s["step"] = N(0.025, 0.25, 0.6, 0.2, 2.0)
        s["coin"] = self._seq([T(988, 988, 0.05, "sq", 0.4, 0.5), T(1319, 1319, 0.22, "sq", 0.4, 0.5)])
        s["gem"] = self._mix(self._arp([76, 81, 85, 88, 93], 0.06, "tri", 0.7, tail=4),
                             self._arp([88, 93, 97, 100, 105], 0.06, "sq", 0.12, 0.125, tail=4))
        s["stomp"] = self._mix(T(520, 110, 0.16, "sq", 0.5, 0.5, curve=0.5), N(0.08, 0.4, 0.7, 0.1))
        s["hurt"] = self._mix(T(700, 90, 0.35, "saw", 0.5, curve=0.6), N(0.2, 0.3, 0.8, 0.1))
        s["dash"] = self._mix(N(0.24, 0.8, 0.08, 0.6, 1.2), T(200, 90, 0.2, "sine", 0.3))
        s["powerup"] = self._arp([60, 64, 67, 72, 76, 79, 84, 88], 0.045, "sq", 0.5, 0.25, tail=3)
        s["heart"] = self._seq([T(659, 659, 0.08, "tri", 0.7), T(988, 988, 0.25, "tri", 0.7)])
        s["break"] = self._mix(N(0.3, 0.9, 0.9, 0.05, 1.3), T(160, 50, 0.2, "sq", 0.4))
        s["bump"] = T(180, 120, 0.09, "sq", 0.5, 0.5)
        s["fire"] = self._mix(N(0.12, 0.4, 0.9, 0.2), T(900, 300, 0.12, "sq", 0.3, 0.25))
        s["explode"] = self._mix(N(0.6, 1.0, 0.5, 0.01, 1.1), T(120, 30, 0.5, "sine", 0.6))
        s["spring"] = T(180, 700, 0.32, "sine", 0.8, vib=0.12, curve=0.5)
        s["checkpoint"] = self._mix(self._arp([72, 76, 79, 84], 0.08, "tri", 0.7, tail=5),
                                    self._arp([84, 88, 91, 96], 0.08, "sq", 0.1, 0.125, tail=5))
        s["portal"] = self._mix(T(200, 1200, 1.1, "sine", 0.6, vib=0.05, curve=2.0), T(100, 600, 1.1, "tri", 0.3, curve=2.0))
        s["chest"] = self._seq([N(0.12, 0.3, 0.2, 0.05), self._arp([67, 71, 74, 79, 83, 86], 0.05, "sq", 0.45, 0.25, tail=4)])
        s["blip"] = T(880, 880, 0.035, "sq", 0.35, 0.5)
        s["confirm"] = self._seq([T(660, 660, 0.05, "sq", 0.4, 0.5), T(990, 990, 0.12, "sq", 0.4, 0.5)])
        s["back"] = T(500, 300, 0.08, "sq", 0.35, 0.5)
        s["roar"] = self._mix(T(110, 60, 0.9, "saw", 0.6, vib=0.08), N(0.9, 0.5, 0.3, 0.02, 0.8))
        s["crumble"] = N(0.35, 0.45, 0.3, 0.05, 0.9)
        s["death"] = self._arp([72, 67, 64, 60, 55, 48], 0.07, "sq", 0.5, 0.5, tail=3)
        s["shoot"] = T(700, 400, 0.08, "sq", 0.3, 0.25)
        s["shield"] = self._mix(T(300, 900, 0.3, "sine", 0.6, vib=0.08), T(600, 1800, 0.3, "tri", 0.2))
        s["kill"] = self._mix(N(0.15, 0.5, 0.8, 0.1), T(300, 900, 0.12, "sq", 0.25, 0.25))
        s["slam"] = self._mix(N(0.5, 1.0, 0.3, 0.01, 1.0), T(70, 30, 0.45, "sine", 0.9))
        s["fanfare"] = self._mix(self._arp([60, 64, 67, 72, 67, 72, 76, 79], 0.11, "sq", 0.5, 0.5, tail=6),
                                 self._arp([48, 52, 55, 60, 55, 60, 64, 67], 0.11, "tri", 0.6, tail=6))
        for k, v in s.items():
            self.sfx[k] = self._sound(v, 0.9)

    # ------------------------------------------------------------- playback
    def play(self, name, vol=1.0):
        if not self.ok or name not in self.sfx or self.sfx_volume <= 0:
            return
        snd = self.sfx[name]
        ch = pg.mixer.find_channel(False)
        if ch is not None:
            ch.set_volume(self.sfx_volume * vol)
            ch.play(snd)

    def music(self, name):
        if not self.ok:
            return
        if name == self.want:
            return
        self.want = name
        if name and name not in self.tracks and name not in self.jobs:
            self.jobs[name] = compose(SONGS.get(name, SONGS["meadow"]), self.rate)
        self._switch()

    def _switch(self):
        if self.want in self.tracks and self.playing != self.want:
            if self.channel is not None:
                self.channel.fadeout(400)
            self.channel = pg.mixer.Channel(0)
            self.channel.set_volume(self.music_volume)
            self.channel.play(self.tracks[self.want], loops=-1, fade_ms=900)
            self.playing = self.want
        elif self.want is None and self.channel is not None:
            self.channel.fadeout(500)
            self.playing = None

    def set_music_volume(self, v):
        self.music_volume = v
        if self.channel is not None:
            self.channel.set_volume(v)

    def update(self, budget_ms=5.0):
        """Advance background composition for the wanted track."""
        if not self.ok:
            return
        name = self.want if self.want in self.jobs else next(iter(self.jobs), None)
        if name is None:
            return
        job = self.jobs[name]
        end = time.perf_counter() + budget_ms / 1000
        try:
            while time.perf_counter() < end:
                next(job)
        except StopIteration as stop:
            del self.jobs[name]
            self.tracks[name] = self._sound(stop.value, 0.85)
            self._switch()

    def prebuild(self, names, budget_s=30):
        """Synchronously render tracks (used by the desktop loading screen)."""
        for n in names:
            if n not in self.tracks and n not in self.jobs:
                self.jobs[n] = compose(SONGS.get(n, SONGS["meadow"]), self.rate)


# ---------------------------------------------------------------- composer
def compose(song, rate):
    """Generator: yields once per bar, returns the finished mono sample list."""
    rng = random.Random(song["seed"])
    bpm = song["bpm"]
    beat = 60.0 / bpm
    bar_len = int(beat * 4 * rate)
    scale = SCALES[song["scale"]]
    root = song["root"]
    prog = song["prog"]
    bars = 16
    total = bar_len * bars
    buf = [0.0] * total
    eighth = bar_len // 8

    def degree_to_midi(deg, octave=0):
        o, d = divmod(deg, 7)
        return root + scale[d] + 12 * (o + octave)

    rhythms = [
        [1, 0, 1, 1, 1, 0, 1, 0], [1, 1, 1, 0, 1, 0, 1, 1], [1, 0, 0, 1, 1, 0, 1, 0],
        [1, 0, 1, 0, 1, 1, 1, 0], [1, 1, 0, 1, 0, 1, 1, 0], [1, 0, 1, 0, 0, 0, 1, 1],
    ]
    if song["lead"] in ("bell", "tri") and bpm < 100:
        rhythms = [[1, 0, 0, 1, 0, 0, 1, 0], [1, 0, 1, 0, 1, 0, 0, 0], [1, 0, 0, 0, 1, 0, 1, 0]]

    def make_phrase(start_deg):
        phrase = []
        deg = start_deg
        for b in range(4):
            chord = prog[b % len(prog)]
            rhythm = rng.choice(rhythms)
            notes = []
            for i, on in enumerate(rhythm):
                if not on:
                    notes.append(None)
                    continue
                if i in (0, 4):
                    tones = [chord, chord + 2, chord + 4, chord + 7]
                    deg = min(tones, key=lambda d: abs(d - deg) + rng.random() * 2)
                else:
                    deg += rng.choice([-2, -1, -1, 1, 1, 2, 0, 3])
                deg = max(0, min(11, deg))
                notes.append(deg)
            phrase.append(notes)
        return phrase

    A = make_phrase(7)
    B = make_phrase(9)
    A2 = [list(bar) for bar in A]
    A2[3] = [prog[3] + 7, None, None, None, prog[0] + 7, None, None, None]
    sections = A + A2 + B + A2

    def note(start, length, f, wave, vol, duty=0.5, decay=1.0, attack=0.004, vib=0.0):
        n = min(length, total - start)
        if n <= 0:
            return
        inc = f / rate
        ph = 0.0
        a = attack * rate
        for i in range(n):
            ph += inc * (1 + vib * math.sin(i / rate * 33)) if vib else inc
            p = ph % 1.0
            if wave == "sq":
                v = 1.0 if p < duty else -1.0
            elif wave == "tri":
                v = 4 * abs(p - 0.5) - 1
            elif wave == "saw":
                v = 2 * p - 1
            else:
                v = math.sin(ph * 6.283185307)
            t = i / n
            env = (i / a if i < a else 1.0) * (1 - t) ** decay
            buf[start + i] += v * env * vol

    def drum(start, kind, vol):
        if kind == "kick":
            n = int(0.16 * rate)
            ph = 0.0
            for i in range(min(n, total - start)):
                t = i / n
                ph += (150 * (1 - t) ** 3 + 45) / rate
                buf[start + i] += math.sin(ph * 6.2831853) * (1 - t) ** 2 * vol
        else:
            n = int((0.05 if kind == "hat" else 0.14) * rate)
            y = 0.0
            hp_prev = 0.0
            for i in range(min(n, total - start)):
                t = i / n
                x = random.uniform(-1, 1)
                if kind == "hat":
                    v = x - hp_prev
                    hp_prev = x
                    v *= 0.5
                else:
                    y += (x - y) * 0.45
                    v = y
                buf[start + i] += v * (1 - t) ** 2.5 * vol

    lead = song["lead"]
    for bi in range(bars):
        s0 = bi * bar_len
        chord = prog[bi % len(prog)]
        # lead melody
        mel = sections[bi]
        for i, d in enumerate(mel):
            if d is None:
                continue
            length = eighth
            j = i + 1
            while j < 8 and mel[j] is None and j - i < 3:
                length += eighth
                j += 1
            f = midi(degree_to_midi(d, 1))
            if lead == "sq":
                note(s0 + i * eighth, int(length * 0.95), f, "sq", 0.16, 0.25 if bi % 8 < 4 else 0.5, 0.6, vib=0.004)
            elif lead == "saw":
                note(s0 + i * eighth, int(length * 0.9), f, "saw", 0.13, decay=0.8)
            elif lead == "bell":
                note(s0 + i * eighth, int(length * 1.6), f, "sine", 0.22, decay=2.2)
                note(s0 + i * eighth, int(length * 0.8), f * 2, "sine", 0.06, decay=3)
            else:
                note(s0 + i * eighth, int(length * 0.95), f, "tri", 0.26, decay=0.9)
        # bass
        bstyle = song["bass"]
        bf = midi(degree_to_midi(chord, -1))
        if bstyle == "bounce":
            for i in range(8):
                note(s0 + i * eighth, int(eighth * 0.8), bf * (2 if i % 2 else 1), "tri", 0.34, decay=0.5)
        elif bstyle == "drive":
            for i in range(8):
                note(s0 + i * eighth, int(eighth * 0.85), bf, "sq", 0.12, 0.5, 0.4)
                note(s0 + i * eighth, int(eighth * 0.85), bf, "tri", 0.25, decay=0.4)
        elif bstyle == "walk":
            for i, step in enumerate((0, 2, 4, 5)):
                f = midi(degree_to_midi(chord + step, -1))
                note(s0 + i * 2 * eighth, int(eighth * 1.8), f, "tri", 0.34, decay=0.6)
        else:
            note(s0, bar_len, bf, "tri", 0.3, decay=0.7)
            note(s0, bar_len, bf * 1.5, "sine", 0.08, decay=0.7)
        # arpeggio / pad
        tones = [degree_to_midi(chord + k) for k in (0, 2, 4, 7)]
        if song["drums"] != "rock":
            for i in range(16):
                f = midi(tones[i % 4])
                note(s0 + i * eighth // 2, eighth // 2, f, "sq" if song["lead"] != "bell" else "sine", 0.035, 0.125, 1.5)
        else:
            for i in range(4):
                for k in (0, 2, 4):
                    note(s0 + i * 2 * eighth, int(eighth * 1.5), midi(degree_to_midi(chord + k)), "saw", 0.03, decay=1.2)
        # drums
        dk = song["drums"]
        for i in range(8):
            t = s0 + i * eighth
            if dk == "soft":
                if i == 0:
                    drum(t, "kick", 0.35)
                if i in (2, 6):
                    drum(t, "hat", 0.06)
            elif dk == "pop":
                if i in (0, 3, 4):
                    drum(t, "kick", 0.5)
                if i in (2, 6):
                    drum(t, "snare", 0.22)
                drum(t, "hat", 0.07)
            elif dk == "rock":
                if i in (0, 2, 3, 4, 6):
                    drum(t, "kick", 0.55)
                if i in (2, 6):
                    drum(t, "snare", 0.3)
                drum(t, "hat", 0.09)
                drum(t + eighth // 2, "hat", 0.05)
        yield bi
    echo = song.get("echo", 0)
    if echo:
        d = int(beat * 0.75 * rate)
        for i in range(d, total):
            buf[i] += buf[i - d] * echo
            if i % 40000 == 0:
                yield -1
    # soft clip
    out = [math.tanh(v * 1.4) for v in buf]
    return out


def init():
    global _audio
    _audio = Audio()
    return _audio


def get():
    return _audio


def play(name, vol=1.0):
    if _audio is not None:
        _audio.play(name, vol)


def music(name):
    if _audio is not None:
        _audio.music(name)
