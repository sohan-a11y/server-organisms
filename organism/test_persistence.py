import sys
sys.path.insert(0, ".")
from brain import Brain
from life import Population

b = Brain("leader")
b.learn("timing side channel token compare leaks secret", "use constant time compare", source="experience")
state_b = b.export_state()
b2 = Brain("leader-restarted")
b2.import_state(state_b)
assert b2.ask("timing side channel token fix?")["known"], b2.snapshot()
print("brain survives restart (neurons/instincts restored): OK", b2.snapshot()["neurons"])

p = Population(seed=9)
for o in p.members:
    o.energy = 22.0
p.tick(food_per_organism=1.0)
state_p = p.export_state()
p2 = Population(seed=99)
p2.import_state(state_p)
assert p2.snapshot()["population"] == p.snapshot()["population"]
assert p2.snapshot()["max_generation"] == p.snapshot()["max_generation"]
print("population survives restart (members/generations restored): OK", p2.snapshot()["population"])
print("PERSISTENCE TEST PASS")
