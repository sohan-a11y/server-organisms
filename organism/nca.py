"""Neural Cellular Automata organism grid (hackathon simplification).

Each cell holds [health, damage, signal]. Update is local-only: a cell sees
its 4 neighbours, like Mordvintsev et al. Growing NCA. Damage spreads from an
exploited endpoint; healthy neighbours regenerate damaged cells.
Grid maps to API endpoints: centre = /api/user, ring = host services.
"""
import random

W = H = 16

class NCAGrid:
    def __init__(self):
        self.reset()

    def reset(self):
        # health 1.0 = healthy, 0 = dead; damage 0..1; signal = swarm pheromone
        self.health = [[1.0 for _ in range(W)] for _ in range(H)]
        self.damage = [[0.0 for _ in range(W)] for _ in range(H)]
        self.signal = [[0.0 for _ in range(W)] for _ in range(H)]
        self.alive = True

    def exploit(self, strength=1.0):
        cx, cy = W // 2, H // 2
        for y in range(H):
            for x in range(W):
                d = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
                if d < 4:
                    self.damage[y][x] = min(1.0, strength * (1 - d / 5))
                    self.signal[y][x] = 1.0

    def step(self, genome=None):
        if not self.alive:
            return
        # Genome phenotype: the leader organism's heritable weights drive the tissue.
        harm_w = genome.harm_rate if genome is not None else 0.25
        heal_w = genome.heal_rate if genome is not None else 0.12
        decay = genome.signal_decay if genome is not None else 0.85
        nh = [row[:] for row in self.health]
        nd = [row[:] for row in self.damage]
        ns = [row[:] for row in self.signal]
        for y in range(H):
            for x in range(W):
                n_h, n_d, n_s, cnt = 0.0, 0.0, 0.0, 0
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < W and 0 <= ny < H:
                        n_h += self.health[ny][nx]; n_d += self.damage[ny][nx]; n_s += self.signal[ny][nx]; cnt += 1
                n_h /= max(cnt, 1); n_d /= max(cnt, 1); n_s /= max(cnt, 1)
                # local rule: damage hurts health, healthy neighbours heal
                harm = harm_w * self.damage[y][x] + 0.08 * n_d
                heal = heal_w * n_h if self.damage[y][x] < 0.9 else 0.02
                nh[y][x] = max(0.0, min(1.0, self.health[y][x] - harm + heal))
                nd[y][x] = max(0.0, self.damage[y][x] - 0.10 * n_h + 0.03 * n_d)
                ns[y][x] = max(0.0, min(1.0, self.signal[y][x] * decay + 0.3 * n_s + 0.4 * self.damage[y][x]))
        self.health, self.damage, self.signal = nh, nd, ns

    def heal_all(self):
        for y in range(H):
            for x in range(W):
                self.damage[y][x] *= 0.2

    def snapshot(self):
        cells = []
        alive = 0
        for y in range(H):
            row = []
            for x in range(W):
                h = round(self.health[y][x], 2)
                if h > 0.3:
                    alive += 1
                row.append({"h": h, "d": round(self.damage[y][x], 2), "s": round(self.signal[y][x], 2)})
            cells.append(row)
        return {"w": W, "h": H, "alive_cells": alive, "total": W * H, "cells": cells}
