# DASH — Deep Additive State History

> Internal notes on the cognitive science model powering the adaptive question engine.

## What DASH Is

DASH (Deep Additive State History) is a psychologically-grounded student modeling approach that treats learning as a **memory problem**, not a completion problem.

Rather than tracking a binary "learned / not learned" state per skill, DASH models a continuous **memory strength** value for each skill per student. This value grows with practice and decays with time — mimicking how human memory actually works.

## Core Concepts Used in This System

### Memory Strength (M)
A continuous real-valued score representing how strongly a student has internalized a skill. Updated after every answer:
- **Correct answer** → strength increases (with diminishing returns as mastery grows)
- **Incorrect answer** → strength decreases; prerequisite skills are also penalized
- **Time without practice** → strength decays exponentially

### Forgetting Rate (λ)
Each skill has its own forgetting rate. Skills practiced less frequently decay faster. Mastered skills (P ≥ 0.7) do not decay — this prevents regression on already-secured knowledge.

### Probability of Correct Response
The expected probability of a student answering a question correctly is computed via a sigmoid function:

```
P(correct) = 1 / (1 + exp(-(M - difficulty)))
```

Where `M` is the current (decayed) memory strength and `difficulty` is the skill's difficulty offset.

### Prerequisite Graph
Skills are organized in a dependency graph. A student cannot unlock a harder skill until all prerequisites have a P(correct) ≥ 0.7. Wrong answers on a skill also penalize its prerequisites (with a smaller impact).

## How We Use It

The DASH model drives the `DASHSystem` class in `services/DashSystem/dash_system.py`. At question selection time:

1. All skills are scored by predicted correctness at the current timestamp
2. Skills below 0.7 threshold with met prerequisites are recommended
3. Questions are pulled from the recommended skill's exercise pool
4. Recent performance (last 5 answers) determines a difficulty adjustment (−0.30 to +0.30)
5. The student state is updated after each answer and persisted to MongoDB

## Why DASH Over Simpler Models

| Aspect | Binary "Learned/Not Learned" | DASH |
|--------|------------------------------|------|
| Forgetting | Not modeled | Explicitly modeled (exponential decay) |
| Mastery | On/Off | Continuous 0–5 scale |
| Prerequisites | Manual rules | Dynamic probability gates |
| Difficulty adaptation | Static | Per-student, per-session |
| Repeat recommendations | Random | Timed — resurfaces when memory decays |

---

*Author: Yash Gondaliya*