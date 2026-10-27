"""Growable brain: neurons = concepts + atomic instincts (continuous-learning model).

- A neuron fires for a concept (English word or code token). Novel concept = new neuron grows.
- An instinct is one trigger->action memory with confidence 0.3..0.9, evidence-backed.
  Confidence rises on verified success, falls on failure - knowledge AND reasoning grow.
- Unknown question: brain asks the LLM (Muse) once, learns the answer as new neurons +
  instinct, remembers it, and can teach it to swarm peers. Peers grow the same neurons.
This is a symbolic growable memory, honestly not a transformer - the LLM is the teacher.
"""
import re, time

SEED = [
    ("sql injection dumps all users when input is interpolated into query",
     "parameterize query; bind user input as parameter, never interpolate"),
    ("broken authorization lets user read another user record by changing id",
     "check ownership on server for every record access"),
    ("health endpoint returns ok when service is running normally",
     "treat health ok as alive; replay normal traffic after any patch"),
]

def concepts(text):
    return sorted(set(re.findall(r"[a-z_][a-z0-9_]{2,}", text.lower())))

class Brain:
    def __init__(self, owner="org", llm_ask=None):
        self.owner = owner
        self.llm_ask = llm_ask  # callable(question)->answer or None (Muse when key set)
        self.neurons = {}       # concept -> activation count
        self.edges = {}         # (a,b) -> weight: co-occurrence = reasoning links
        self.instincts = []     # {trigger, action, confidence, evidence, source}
        self.pending_unknown = []
        for trig, act in SEED:
            self.learn(trig, act, source="seed", confidence=0.7)

    # --- growth ---
    def _grow(self, words):
        new = 0
        for w in words:
            if w not in self.neurons:
                self.neurons[w] = 0; new += 1
            self.neurons[w] += 1
        for a, b in zip(words, words[1:]):
            self.edges[(a, b)] = self.edges.get((a, b), 0) + 1
        return new

    def learn(self, trigger, action, source="experience", confidence=0.5):
        new_neurons = self._grow(concepts(trigger + " " + action))
        for inst in self.instincts:
            if inst["trigger"] == trigger:
                inst["confidence"] = min(0.9, inst["confidence"] + 0.1)
                inst["evidence"] += 1
                return {"learned": "reinforced", "new_neurons": new_neurons,
                        "confidence": inst["confidence"]}
        self.instincts.append({"trigger": trigger, "action": action,
                               "confidence": confidence, "evidence": 1, "source": source})
        return {"learned": "new-instinct", "new_neurons": new_neurons, "confidence": confidence}

    # --- reasoning: recall by concept overlap, weighted by confidence ---
    def recall(self, question):
        qw = set(concepts(question))
        best, best_score = None, 0.0
        for inst in self.instincts:
            tw = set(concepts(inst["trigger"]))
            overlap = len(qw & tw) / max(1, len(qw))
            score = overlap * inst["confidence"]
            if score > best_score:
                best, best_score = inst, score
        # Require at least 2 shared concepts and 40% query coverage, so a
        # one-word query cannot recall (and then teach) a wrong instinct.
        shared = len(qw & set(concepts(best["trigger"]))) if best else 0
        if best and best_score > 0.08 and shared >= 2 and (shared / max(1, len(qw))) >= 0.4:
            return {"known": True, "answer": best["action"], "confidence": best["confidence"],
                    "score": round(best_score, 3), "neurons": len(self.neurons)}
        return {"known": False, "answer": None, "neurons": len(self.neurons)}

    def ask(self, question):
        """Understands if it can; otherwise learns from LLM, remembers, grows."""
        hit = self.recall(question)
        if hit["known"]:
            return {**hit, "via": "memory (neurons recalled)"}
        # does not know -> ask teacher (LLM). Without key, queue honestly as unknown.
        if self.llm_ask:
            taught = self.llm_ask(question)
            if taught:
                grew = self.learn(question, taught, source="LLM-teacher", confidence=0.5)
                return {"known": True, "answer": taught, "via": "LLM taught -> learned",
                        "grew": grew, "neurons": len(self.neurons)}
        if question not in self.pending_unknown:
            self.pending_unknown.append(question)
        return {"known": False, "answer": None, "via": "unknown - queued for LLM (set META_API_KEY)",
                "neurons": len(self.neurons)}

    def reward(self, trigger, success):
        for inst in self.instincts:
            if trigger in inst["trigger"] or inst["trigger"] in trigger:
                inst["confidence"] = max(0.3, min(0.9, inst["confidence"] + (0.1 if success else -0.15)))
                inst["evidence"] += 1
                return inst["confidence"]
        return None

    # --- swarm communication: teach peers ---
    def teach_packet(self):
        # Only verified instincts are taught swarm-wide: evidence >= 2
        # (seeded or rewarded by a verified heal), never a fresh LLM guess.
        verified = [i for i in self.instincts if i["evidence"] >= 2 or i["source"] in ("seed", "experience")]
        return {"from": self.owner, "instincts": verified, "concepts": list(self.neurons)}

    def receive_teaching(self, packet):
        if packet.get("from") == self.owner:
            return {"absorbed": 0}
        absorbed = 0
        known = {i["trigger"] for i in self.instincts}
        for inst in packet.get("instincts", []):
            if inst["trigger"] not in known:
                self.learn(inst["trigger"], inst["action"], source=f"peer:{packet['from']}",
                           confidence=max(0.3, inst["confidence"] - 0.1))
                absorbed += 1
        return {"absorbed": absorbed, "neurons": len(self.neurons)}

    def export_state(self):
        return {"neurons": self.neurons, "edges": {f"{a}|{b}": v for (a, b), v in self.edges.items()},
                "instincts": self.instincts, "pending_unknown": self.pending_unknown}

    def import_state(self, data):
        if not data:
            return
        self.neurons = data.get("neurons", self.neurons)
        self.edges = {}
        for k, v in data.get("edges", {}).items():
            a, _, b = k.partition("|")
            self.edges[(a, b)] = v
        saved = {i["trigger"]: i for i in data.get("instincts", [])}
        for trig, inst in saved.items():
            if trig not in {i["trigger"] for i in self.instincts}:
                self.instincts.append(inst)
            else:
                cur = next(i for i in self.instincts if i["trigger"] == trig)
                cur["confidence"] = max(cur["confidence"], inst["confidence"]); cur["evidence"] = max(cur["evidence"], inst["evidence"])
        self.pending_unknown = data.get("pending_unknown", [])

    def snapshot(self):
        return {"owner": self.owner, "neurons": len(self.neurons), "edges": len(self.edges),
                "instincts": len(self.instincts), "pending_unknown": self.pending_unknown[-5:],
                "top_neurons": sorted(self.neurons, key=self.neurons.get, reverse=True)[:8],
                "instinct_list": [{"trigger": i["trigger"][:60], "confidence": i["confidence"],
                                   "source": i["source"]} for i in self.instincts]}
