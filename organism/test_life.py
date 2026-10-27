import sys
sys.path.insert(0, ".")
from life import Population, Organism

p = Population(seed=3)
assert len(p.members) == 6
# Starvation kills: zero food, basal cost drains energy
for _ in range(30):
    p.tick(food_per_organism=0.0)
assert len(p.members) < 6 or len(p.graveyard) > 0, p.snapshot()
print("starvation/death: OK", len(p.graveyard), "dead")

# Fed population reproduces with heredity + variation and generations advance
p2 = Population(seed=5)
for o in p2.members:
    o.energy = 20.0
p2.tick(food_per_organism=1.0)
snap = p2.snapshot()
assert snap["births"] > 0 and snap["max_generation"] >= 1, snap
child = [o for o in p2.members if o.generation == 1][0]
parent = [o for o in p2.members if o.id == child.parent][0]
assert child.genome.heal_rate != parent.genome.heal_rate or child.genome.harm_rate != parent.genome.harm_rate
print("reproduction with mutated heredity: OK, births", snap["births"])

# Fitness is measured by outcomes; selection culls weakest beyond capacity
o = Organism()
o.record(True); o.record(True); o.record(False)
assert abs(o.fitness - 2/3) < 0.01
print("measured fitness: OK", round(o.fitness, 2))
print("LIFE TEST PASS")
