"""Real artificial-life layer: autopoiesis checklist made executable.

An organism here is not a metaphor: it holds state no other organism holds,
consumes a leased metabolism every tick, reproduces with heritable variation
when it has surplus energy, and dies (state deleted) when starved, old, or
culled by selection. Genome = NCA rule weights; offspring inherit + mutate them.
Fitness = verified heal performance, measured - never self-declared.
"""
import random, time, uuid

class Genome:
    def __init__(self, heal_rate=0.12, harm_rate=0.25, signal_decay=0.85, mutation=0.05):
        self.heal_rate, self.harm_rate = heal_rate, harm_rate
        self.signal_decay, self.mutation = signal_decay, mutation
    def mutate(self, rng):
        m = self.mutation
        return Genome(
            heal_rate=max(0.02, min(0.4, self.heal_rate + rng.uniform(-m, m))),
            harm_rate=max(0.05, min(0.5, self.harm_rate + rng.uniform(-m, m))),
            signal_decay=max(0.5, min(0.98, self.signal_decay + rng.uniform(-m, m))),
            mutation=m)
    def to_dict(self):
        return {"heal_rate": round(self.heal_rate, 3), "harm_rate": round(self.harm_rate, 3),
                "signal_decay": round(self.signal_decay, 3)}

class Organism:
    MAX_AGE = 600  # ticks; old age is a real death cause
    REPRO_COST, REPRO_THRESHOLD = 6.0, 14.0
    def __init__(self, genome=None, generation=0, parent=None, rng=None):
        self.id = uuid.uuid4().hex[:8]
        self.genome = genome or Genome()
        self.generation, self.parent = generation, parent
        self.energy, self.age, self.heals, self.failures = 10.0, 0, 0, 0
        self.born = time.strftime("%H:%M:%S")
        self.rng = rng or random.Random()
    @property
    def fitness(self):
        total = self.heals + self.failures
        return (self.heals / total) if total else 0.5  # unproven = neutral, not trusted
    def tick(self, food=0.0):
        """Metabolize: food in, basal cost out. Returns death cause or None."""
        self.age += 1
        self.energy += food - 1.0  # basal metabolic cost per tick
        if self.energy <= 0:
            return "starved (lease/metabolism exhausted)"
        if self.age > self.MAX_AGE:
            return "old age"
        return None
    def reproduce(self):
        if self.energy < self.REPRO_THRESHOLD:
            return None
        self.energy -= self.REPRO_COST
        child = Organism(self.genome.mutate(self.rng), self.generation + 1, parent=self.id, rng=self.rng)
        child.energy = self.REPRO_COST
        return child
    def record(self, healed):
        if healed:
            self.heals += 1; self.energy += 4.0  # verified heal = food
        else:
            self.failures += 1; self.energy -= 2.0
    def to_dict(self):
        return {"id": self.id, "gen": self.generation, "parent": self.parent,
                "energy": round(self.energy, 1), "age": self.age,
                "fitness": round(self.fitness, 2), "heals": self.heals,
                "genome": self.genome.to_dict(), "born": self.born}

class Population:
    """The tissue. Selection is external (broker/verifier measured fitness), culls weakest."""
    MAX_POP = 24
    def __init__(self, seed=7):
        self.rng = random.Random(seed)
        self.members = [Organism(rng=self.rng) for _ in range(6)]
        self.graveyard, self.births = [], 0
    def leader_genome(self):
        if not self.members:
            return None
        return max(self.members, key=lambda x: x.fitness).genome

    def tick(self, food_per_organism=1.2):
        deaths = []
        for o in list(self.members):
            cause = o.tick(food=self.rng.uniform(0, food_per_organism * 2))
            if cause:
                deaths.append((o, cause)); self.members.remove(o)
                self.graveyard.append({"id": o.id, "gen": o.generation, "cause": cause, "fitness": round(o.fitness, 2)})
        # reproduction from surplus, then selection cull beyond capacity
        for o in list(self.members):
            child = o.reproduce()
            if child:
                self.members.append(child); self.births += 1
        if len(self.members) > self.MAX_POP:
            self.members.sort(key=lambda x: x.fitness, reverse=True)
            for culled in self.members[self.MAX_POP:]:
                self.graveyard.append({"id": culled.id, "gen": culled.generation, "cause": "selected out (lowest fitness)", "fitness": round(culled.fitness, 2)})
            self.members = self.members[:self.MAX_POP]
        return deaths
    def record_outcome(self, healed):
        # fittest organism is credited/blamed - it led the swarm response
        if self.members:
            leader = max(self.members, key=lambda x: x.fitness)
            leader.record(healed)
    def export_state(self):
        return {"members": [{"genome": o.genome.to_dict(), "generation": o.generation, "parent": o.parent,
                             "energy": o.energy, "age": o.age, "heals": o.heals, "failures": o.failures, "id": o.id}
                            for o in self.members],
                "graveyard": self.graveyard, "births": self.births}

    def import_state(self, data):
        if not data or not data.get("members"):
            return
        self.members = []
        for m in data["members"]:
            g = Genome(m["genome"]["heal_rate"], m["genome"]["harm_rate"], m["genome"]["signal_decay"])
            o = Organism(g, m["generation"], m.get("parent"), rng=self.rng)
            o.id, o.energy, o.age, o.heals, o.failures = m["id"], m["energy"], m["age"], m["heals"], m["failures"]
            self.members.append(o)
        self.graveyard, self.births = data.get("graveyard", []), data.get("births", 0)

    def snapshot(self):
        return {"population": len(self.members), "births": self.births,
                "deaths": len(self.graveyard),
                "max_generation": max((o.generation for o in self.members), default=0),
                "organisms": [o.to_dict() for o in self.members],
                "graveyard": self.graveyard[-8:]}
