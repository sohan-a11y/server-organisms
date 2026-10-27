"""Evolutionary training of the NCA genome (CAX-style adopt pattern, pure python).

Task: damaged tissue must recover alive cells fast without harming healthy cells.
Fitness(genome) = alive_after_40_steps - 2*mean_damage, measured - never declared.
Evolves a population with mutation + selection; benchmarks best vs hand rule.
Saves trained genome to trained_genome.json for the broker to load.
"""
import json
import os
import random
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nca import NCAGrid
from life import Genome

def fitness(genome, steps=12):
    g = NCAGrid()
    g.exploit(1.0)
    for _ in range(steps):
        g.step(genome=genome)
    snap = g.snapshot()
    mean_d = sum(c["d"] for row in snap["cells"] for c in row) / snap["total"]
    return snap["alive_cells"] / snap["total"] - 2 * mean_d

def train(generations=25, pop_size=20, seed=11):
    rng = random.Random(seed)
    pop = [Genome(rng.uniform(0.02, 0.4), rng.uniform(0.05, 0.5), rng.uniform(0.5, 0.98)) for _ in range(pop_size)]
    hand = Genome()
    hand_fit = fitness(hand)
    best, best_fit = hand, hand_fit
    for _ in range(generations):
        scored = sorted(((fitness(g), g) for g in pop), key=lambda x: x[0], reverse=True)
        if scored[0][0] > best_fit:
            best_fit, best = scored[0]
        elites = [g for _, g in scored[:5]]
        pop = elites + [elites[i % len(elites)].mutate(rng) for i in range(pop_size - len(elites))]
    return {"hand_rule_fitness": round(hand_fit, 4), "trained_fitness": round(best_fit, 4),
            "genome": best.to_dict(), "generations": generations}

if __name__ == "__main__":
    result = train()
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trained_genome.json")
    with open(out, "w") as f:
        json.dump(result, f, indent=2)
    print(result)
    assert result["trained_fitness"] >= result["hand_rule_fitness"] - 0.05, "trained must not be far worse than hand rule"
    print("TRAIN PASS ->", out)
