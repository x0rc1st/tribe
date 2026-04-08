# Operator Readiness Profile

## A neuroscience-grounded framework for assessing cognitive readiness in high-stakes operator training

---

## 1. Foundation

### 1.1 What This Is

A measurement framework that maps brain engagement predictions from TRIBE v2 to the cognitive dimensions required for high-stakes operator mastery. For each piece of training content, TRIBE produces 17 data points (10 cortical group z-scores + 7 subcortical structure z-scores). This framework translates those data points into 6 operator readiness dimensions, each grounded in established neuroscience and each with a unique, distinguishable neural signature.

### 1.2 The Problem It Solves

Training programs label content by format (lecture, lab, simulation) or topic (forensics, incident response). But format and topic don't tell you which cognitive circuits the content actually engages. A module labeled "hands-on lab" might be a guided walkthrough that barely activates procedural circuits. A "threat simulation" might be a passive video that doesn't engage decision-making under pressure.

TRIBE measures what the content does to the brain. This framework maps those measurements to what the operator needs.

### 1.3 Composite Scientific Framework

No single model of expertise adequately covers cognition, motor skills, decision-making, stress, and threat detection — because those are fundamentally different neural systems. Rather than force everything into one philosophical model, this framework uses the strongest empirically-validated model for each aspect of operator performance. Each component can be challenged independently without the whole framework collapsing.

#### Rasmussen's Skill-Rule-Knowledge Framework (SRK)
**Role in our framework:** Cognitive mode classification and failure analysis
**Origin:** Developed by Jens Rasmussen for high-stakes operator domains, directly inspired by the 1979 Three Mile Island nuclear incident where operators applied rules without sufficient knowledge of the underlying system.
**What it provides:** Three cognitive modes (Skill, Rule, Knowledge) with distinct error types and reliability levels. Each mode maps to specific neural circuits.
**Empirical basis:** Applied in nuclear safety, process control, aviation. Recent brain imaging studies have characterized cortical activity for each SRK level.
**Sources:**
- [Rasmussen SRK quantification under time pressure, PMC 2023](https://pmc.ncbi.nlm.nih.gov/articles/PMC10112018/)
- [Brain cortical characterization of SRK levels, PMC 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC12467830/)
- [SRK in nuclear control rooms](https://www.sciencedirect.com/science/article/abs/pii/S0029549314000235)

#### Fitts & Posner's Three-Stage Motor Learning Model
**Role in our framework:** Procedural skill progression (Dimension 1)
**What it provides:** Three stages — Cognitive (conscious, slow), Associative (refining, faster), Autonomous (automatic, effortless). Maps directly to the cortico-striatal shift observed in fMRI.
**Empirical basis:** Strong fMRI evidence showing frontal/parietal activation in early learning shifting to basal ganglia and cerebellum in late learning.
**Source:** [Motor learning unfolds in distinct neural systems, PLOS Biology 2015](https://pmc.ncbi.nlm.nih.gov/articles/PMC4672876/)

#### Klein's Naturalistic Decision Making / Recognition-Primed Decision Model
**Role in our framework:** Decision-making and pattern matching (Dimensions 4, 5)
**Origin:** Commissioned by US Army Research Institute. Developed from field studies of fireground commanders, military officers, ICU nurses.
**What it provides:** Experts don't compare options — they recognize situations and evaluate a single course of action. Klein describes this at the cognitive level; our neural mapping (hippocampal pattern matching + prefrontal evaluation) is our interpretation based on the neuroscience of recognition and executive function.
**Source:** [Klein 2008 — Naturalistic Decision Making](https://journals.sagepub.com/doi/10.1518/001872008X288385)

#### Endsley's Situational Awareness Model
**Role in our framework:** Awareness and mental model maintenance (Dimension 3)
**What it provides:** Three hierarchical levels: perception of elements, comprehension of meaning, projection of future state. SA problems documented in 88% of human-error commercial aviation accidents (Jones & Endsley 1996).
**Source:** [Endsley 1995 — Situation Awareness Theory](https://journals.sagepub.com/doi/10.1518/001872095779049543)

#### Yerkes-Dodson / Arnsten Stress-Performance Model
**Role in our framework:** Stress resilience and threat calibration (Dimensions 2, 6)
**What it provides:** The inverted-U relationship between arousal and performance, with the molecular mechanism: catecholamine (norepinephrine/dopamine) flooding of alpha-1 and D1 receptors weakens prefrontal connectivity under acute stress.
**Empirical basis:** Confirmed by 2024 pupillometry studies and 2025 pharmacological manipulation (atomoxetine shifts the Yerkes-Dodson curve).
**Sources:**
- [Yerkes-Dodson revisited, Trends in Cognitive Sciences 2024](https://www.cell.com/trends/cognitive-sciences/fulltext/S1364-6613(24)00078-0)
- [PNAS 2025 — catecholaminergic arousal shifts the curve](https://www.pnas.org/doi/10.1073/pnas.2419733122)
- [Arnsten 2009 — Stress signalling impairs PFC](https://pmc.ncbi.nlm.nih.gov/articles/PMC2907136/)

#### Cognitive Task Analysis (CTA)
**Role in our framework:** Methodological foundation — TRIBE automates a portion of CTA
**What it provides:** Structured extraction of expert cognitive processes. TRIBE measures which brain circuits content engages, complementing CTA's interview-based approach.
**Source:** [CTA-based surgical training meta-analysis](https://academic.oup.com/bjsopen/article/5/6/zrab122/6460901)

### 1.4 How the Components Integrate

```
                    RASMUSSEN SRK
              (cognitive mode & failure analysis)
                         |
         +---------------+---------------+
         |               |               |
    SKILL-BASED      RULE-BASED     KNOWLEDGE-BASED
    (automatic)      (IF-THEN)      (analytical)
         |               |               |
    FITTS & POSNER   ENDSLEY SA     KLEIN NDM/RPD
    (motor learning  (awareness     (decision-making
     progression)     levels)        under uncertainty)
         |               |               |
    Dimension 1      Dimension 3    Dimensions 4, 5
         |               |               |
         +-------+-------+-------+-------+
                 |                 |
          YERKES-DODSON / ARNSTEN
          (stress-performance, arousal calibration)
                 |                 |
            Dimension 2       Dimension 6
```

Each dimension maps to a Rasmussen cognitive mode AND uses a domain-specific model for its internal mechanics:

| Dimension | Rasmussen Mode | Domain-Specific Model | What It Measures |
|:---|:---|:---|:---|
| 1. Procedural Automaticity | Skill-based | Fitts & Posner | Has the skill reached autonomous execution? |
| 2. Threat Detection | Transitions across all modes | Yerkes-Dodson / Arnsten | Is threat reactivity calibrated? |
| 3. Situational Awareness | Rule-based + Knowledge-based | Endsley SA | Can the operator maintain the big picture? |
| 4. Strategic Decision & Reflection | Knowledge-based | Klein NDM | Can the operator decide under uncertainty? |
| 5. Analytical Synthesis | Knowledge-based + Rule-based | Klein RPD | Can the operator connect the dots? |
| 6. Stress Resilience | All modes under degradation | Arnsten/Yerkes-Dodson | Do capabilities survive cortisol? |

### 1.5 Rasmussen SRK Failure Mode Analysis

Each cognitive mode has a specific error type. This is what makes SRK uniquely valuable — it doesn't just describe performance, it predicts HOW operators fail.

**Rasmussen's original error taxonomy (1983):**

| SRK Mode | Error Type | Example | Dimension Gap |
|:---|:---|:---|:---|
| **Skill-based** | **Slips** — correct intention, wrong action. Attentional or perceptual failure during automated execution. | Operator types wrong IP in firewall rule, runs command in wrong terminal | Low Dim 1 (execution not error-proof) |
| **Skill-based** | **Lapses** — correct intention, forgotten step. Memory failure during automated sequence. | Operator skips a step in the forensic preservation chain, forgets to document a finding | Low Dim 1 (sequence not fully automated) |
| **Rule-based** | **Rule-based mistakes** — wrong rule selected for the situation. The operator matches to the wrong pattern or applies the wrong procedure. | Operator applies the phishing playbook to a supply chain compromise | Low Dim 3 + 5 (poor SA, poor synthesis) |
| **Knowledge-based** | **Knowledge-based mistakes** — wrong mental model. Reasoning from incorrect first principles under novel conditions. | Operator assumes attacker left because C2 traffic stopped, missing persistence mechanism | Low Dim 4 + 5 (weak reasoning, incomplete model) |

**Our extensions (synthesized from Rasmussen + Arnsten):**

| Pattern | Error Type | Example | Dimension Gap |
|:---|:---|:---|:---|
| **Mode transition failure** | Operator stays in rule-based when the situation requires knowledge-based reasoning (novel, unprecedented scenario). Not in Rasmussen's original taxonomy but a natural consequence of his framework. | Operator keeps applying standard IR playbook to a zero-day with no matching signatures | Low Dim 5 adaptive sub-signal |
| **Stress-induced regression** | Under acute stress, the operator regresses from a higher to lower SRK mode (Arnsten's prefrontal degradation mechanism applied to Rasmussen's framework). The operator THINKS they're still reasoning but has actually regressed to pattern-matching or automatic responses. | Operator reverts to memorized checklist during a crisis that requires creative response | Low Dim 6 (not stress-tested) |

The error type maps directly to gap recommendations: the error tells you which dimension to train.

### 1.6 Applicable Domains

| Domain | Operator | SRK Failure Examples |
|:---|:---|:---|
| Cybersecurity | SOC analyst, incident responder, pen tester | Slip: wrong command. Rule mistake: wrong playbook. Knowledge mistake: wrong threat model. |
| Military | Combat controller, intel analyst, drone operator | Slip: wrong radio frequency. Rule mistake: wrong ROE applied. Knowledge mistake: wrong enemy intent model. |
| Aviation | Pilot, ATC | Slip: wrong altitude setting. Rule mistake: wrong checklist for the failure. Knowledge mistake: misunderstanding weather dynamics. |
| Surgery | Surgeon, anesthesiologist | Slip: wrong instrument. Rule mistake: wrong protocol for the complication. Knowledge mistake: misunderstanding the anatomy variant. |

---

## 2. The 6 Dimensions

### 2.1 Why 6

Started with 8 candidate dimensions. Dropped 2 after auditing which produce unique, distinguishable signatures in TRIBE's 17 data points (10 cortical groups + 7 subcortical structures):

- **Metacognition & Error Monitoring** — dropped as standalone. TRIBE measures content engagement, not learner self-reflection. Group 10 signal folded into Dimension 4. True metacognitive assessment requires behavioral measurement.
  Source: [Nature 2024](https://www.nature.com/articles/s41539-024-00231-z)

- **Adaptive Expertise** — merged into Dimension 5 as sub-signal. The difference between pattern matching and improvisation (whether Group 1 is also elevated) is captured within Analytical Synthesis rather than as a separate dimension.
  Source: [Adaptive Expertise](https://en.wikipedia.org/wiki/Adaptive_expertise)

### 2.2 Unique Anchor Summary

| # | Dimension | Unique Anchor | Why It's Unique |
|:---:|:---|:---|:---|
| 1 | Procedural Automaticity | Group 2, Putamen, Pallidum | Only dimension using motor/habit circuits |
| 2 | Threat Detection & Calibration | Group 9, Amygdala | Only dimension anchored on threat/emotional circuits |
| 3 | Situational Awareness | Group 5 | Only dimension anchored on attentional gating |
| 4 | Strategic Decision & Reflection | Group 1 + Group 10 | Only dimension combining executive function with reflection |
| 5 | Analytical Synthesis & Pattern Matching | Group 8 + Group 7 + Hippocampus | Only dimension combining synthesis with memory binding |
| 6 | Stress Resilience | Co-activation pattern | Only dimension requiring cognitive + threat simultaneous activation |

---

### Dimension 1: Procedural Automaticity

**Rasmussen mode:** Skill-based
**Domain model:** Fitts & Posner — Cognitive → Associative → Autonomous

**What it is.** Executing known procedures without conscious effort so they survive stress-induced prefrontal degradation. When cortisol floods the prefrontal cortex during a crisis, only skills that have migrated to automatic basal ganglia execution remain intact.

**The neural mechanism.** The cortico-striatal shift: early learning uses the caudate nucleus (conscious, goal-directed), with practice control transfers to the putamen (automatic, habitual). The pallidum gates motor output. This transfer is observable in fMRI: frontal/parietal activation decreases while basal ganglia and cerebellar activation increases as a skill becomes automatic.

**Fitts & Posner progression:**
- Cognitive stage: slow, conscious, error-prone (Group 1 + Caudate dominant, high prefrontal load)
- Associative stage: refining, fewer errors (Groups 1 and 2 co-active, transitioning)
- Autonomous stage: fast, automatic, resistant to interference (Group 2 + Putamen/Pallidum dominant, prefrontal quiet)

**SRK error type:** Slips — correct procedure, wrong execution. Operator knows what to do but mis-executes under pressure.

**Why it matters.** The single biggest predictor of operator failure under stress. If a procedure hasn't migrated from caudate to putamen, the operator freezes when prefrontal function degrades.

**Unique anchor:** Group 2 + Putamen + Pallidum
**Detection rule:** Group 2 >= Moderate AND (Putamen OR Pallidum) engaged
**Cortical-only fallback:** Group 2 >= Strong (when subcortical data unavailable or unreliable)
**Content that triggers it:** Timed CTF labs, repetitive tool drills, speed runs, muscle-memory exercises

**Text input nuance:** TRIBE converts text to speech and predicts brain engagement for LISTENING to that text. Different text types produce different Dim 1 signals:
- **Conceptual/declarative text** ("nmap is a network scanner that..."): Very low Dim 1. Engages comprehension, not motor circuits. Expected and correct.
- **Procedural/instructional text** ("run `nmap -sV 10.10.10.5`, then check for..."): Low-Moderate Dim 1. Sequential action descriptions partially activate motor planning (premotor cortex) and mental rehearsal circuits — the brain simulates the action sequence while reading. This is the Fitts & Posner cognitive stage: acquiring procedural knowledge before it can be automated.
- **Video of procedure execution**: Moderate Dim 1. Motor observation circuits (mirror neuron system) activate when watching someone perform actions.
- **Actually performing the procedure**: High Dim 1 (cannot be measured by TRIBE — outside content prediction scope).

A lab writeup is a necessary precursor to procedural automaticity (you need procedural knowledge before you can automate it), but it's not sufficient. TRIBE correctly assigns lab writeups a lower Dim 1 score than hands-on execution would produce. HTB should interpret low Dim 1 on text modules as "this content teaches procedural knowledge but doesn't build muscle memory — pair with hands-on practice."

**Cross-domain:** Aviation simulator hours. Surgical knot-tying drills. Military weapons handling drills.

**Evidence level:** Very strong
**Sources:**
- Packard & Knowlton 2002 — Learning and memory functions of the basal ganglia
- [fMRI meta-analysis of striatal habits, 2022](https://pubmed.ncbi.nlm.nih.gov/35963543/)
- [PNAS 2020: caudate dissociation in skill learning](https://www.pnas.org/doi/10.1073/pnas.2003963117)
- [Motor learning in distinct neural systems, PLOS Biology 2015](https://pmc.ncbi.nlm.nih.gov/articles/PMC4672876/)

---

### Dimension 2: Threat Detection & Calibration

**Rasmussen mode:** Transitions across all three modes — recognizing threats involves skill-based pattern detection, rule-based classification, and knowledge-based assessment
**Domain model:** Yerkes-Dodson / Arnsten

**What it is.** Developing calibrated threat reactivity. Expert operators show lower amygdala response to routine threats (habituation) but maintained sensitivity to novel ones. The training goal is optimal arousal, not maximum arousal.

**The neural mechanism.** The amygdala tags experiences with emotional significance, enhancing hippocampal memory consolidation. Performance follows the Yerkes-Dodson inverted-U: moderate arousal (optimal catecholamine levels) maximizes performance. Under-arousal: threats missed. Over-arousal: tunnel vision, false positives, burnout. The nucleus accumbens (Group 6) sustains motivational drive during long monitoring periods between events.

**SRK error type:** Misclassification — either failing to detect a real threat (skill-based: habituated too much) or over-classifying benign signals as threats (rule-based: wrong discrimination rule).

**Unique anchor:** Group 9 + Amygdala
**Detection rule:** Group 9 >= Moderate AND Amygdala engaged
**Cortical-only fallback:** Group 9 >= Strong (when subcortical data unavailable or unreliable)
**Content that triggers it:** Escalating scenarios, red team simulations, false positive discrimination, mixed benign/malicious analysis

**Caveat:** TRIBE can't distinguish calibrated threat training from merely alarming content. Both light up the same circuits. The measurement tells you whether the content creates the conditions for calibration; actual calibration requires exposure over time.

**Cross-domain:** Aviation upset recovery. Surgical hemorrhage recognition. Military IED detection training.

**Evidence level:** Strong
**Sources:**
- McGaugh 2004 — Amygdala modulates memory consolidation
- [Yerkes-Dodson revisited, Trends in Cognitive Sciences 2024](https://www.cell.com/trends/cognitive-sciences/fulltext/S1364-6613(24)00078-0)
- [PNAS 2025: catecholaminergic mechanism](https://www.pnas.org/doi/10.1073/pnas.2419733122)
- [Lupien et al 2007: glucocorticoid inverted-U](https://pmc.ncbi.nlm.nih.gov/articles/PMC2657838/)

---

### Dimension 3: Situational Awareness

**Rasmussen mode:** Rule-based + Knowledge-based (SA Level 1 can be skill-based, but Levels 2-3 require higher cognitive modes)
**Domain model:** Endsley SA

**What it is.** Endsley's three levels: (1) perception of elements, (2) comprehension of meaning, (3) projection of future state. Loss of SA is documented in 88% of human-error commercial aviation accidents (Jones & Endsley 1996) and is consistently cited across military, surgical, and nuclear safety domains.

**The neural mechanism.** Level 1 (perception): thalamic reticular nucleus gates sensory information. Level 2 (comprehension): perisylvian language network (Group 3) and dorsal parietal attention network (Group 5) integrate perceived elements. Level 3 (projection): inferior parietal lobule and angular gyrus (Group 8) construct mental models of future states, supported by hippocampal relational memory.

**SRK error type:** Rule-based mistake — operator applies the wrong interpretive frame because they lost track of the situation. Also: knowledge-based mistake from failed projection (can't anticipate what happens next).

**Unique anchor:** Group 5 (literally named "Situational Awareness & Focus")
**Supporting:** Groups 3, 8 + Thalamus + Hippocampus
**Detection rule:** Group 5 >= Moderate AND Group 3 >= Baseline AND Group 8 >= Baseline
**Content that triggers it:** Multi-host incident scenarios, SOC dashboard exercises, expanding-scope simulations

**Cross-domain:** Aviation scan pattern training. Surgical vital sign monitoring. Military battlefield management.

**Evidence level:** Very strong
**Sources:**
- [Endsley 1995 — SA Theory](https://journals.sagepub.com/doi/10.1518/001872095779049543)
- [Jones & Endsley 1996 — SA errors in aviation](https://pubmed.ncbi.nlm.nih.gov/8827130/) — 88% of human-error accidents involved SA problems; 76% were Level 1 (perception) failures
- [USAARL 2025 — Holistic SA and Decision Making](https://usaarl.health.mil/assets/docs/techReports/2025-10.pdf)

---

### Dimension 4: Strategic Decision-Making & Reflection

**Rasmussen mode:** Knowledge-based (novel or high-stakes decisions require analytical reasoning, not rule application)
**Domain model:** Klein NDM / Recognition-Primed Decision

**What it is.** Acting with incomplete information under time pressure with irreversible consequences, then reflecting to extract lessons. Klein's RPD model: experts evaluate a single recognized course of action rather than comparing multiple options.

**The neural mechanism.** Prefrontal cortex (Group 1): executive function, working memory, planning, value-based decisions. Caudate: feedback-based learning through reward prediction error. Default mode network / posterior cingulate (Group 10): reflective processing — reviewing past decisions, extracting generalizable lessons.

**SRK error type:** Knowledge-based mistake — wrong mental model, reasoning from incorrect first principles. Also: failure to reflect (Rasmussen's "mode transition failure" — the operator doesn't step back from rule-based to knowledge-based when the situation demands it).

**Note on metacognition:** Absorbs the reflective/metacognitive component. TRIBE detects whether content engages reflective circuits (Group 10). Actual self-monitoring behavior requires behavioral measurement.

**Unique anchor:** Group 1 + Group 10 combination
**Supporting:** Caudate
**Detection rule:** Group 1 >= Moderate AND Group 10 >= Baseline
**Content that triggers it:** Tabletops, incident command sims, ambiguous evidence exercises, post-incident reviews, after-action reports

**Cross-domain:** Aviation crew decision exercises. Surgical M&M conferences. Military tactical decision games.

**Evidence level:** Strong
**Sources:**
- [Klein 2008 — NDM](https://journals.sagepub.com/doi/10.1518/001872008X288385)
- [Caudate in reward-evidence integration, PMC 2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC7308093/)
- [Metacognitive monitoring & neural activity, Nature 2024](https://www.nature.com/articles/s41539-024-00231-z)

---

### Dimension 5: Analytical Synthesis & Pattern Matching

**Rasmussen mode:** Knowledge-based (novel synthesis) + Rule-based (pattern matching to known signatures)
**Domain model:** Klein RPD (pattern recognition) + Adaptive Expertise (novel synthesis)

**What it is.** Integrating disparate data into coherent understanding and matching situations to known or novel patterns. This is the "connect the dots" capability — seeing the DNS anomaly, firewall alert, and failed SMB auth as one attack chain rather than three separate events.

**The neural mechanism.** Inferior parietal lobule and angular gyrus (Group 8): integration hub where information from different domains converges. Hippocampus: binds contextual elements into coherent episodic representations and enables relational memory — finding structural similarities between current and past situations. Medial temporal cortex (Group 7): encoding of integrated representations.

**Sub-signal for adaptive expertise:** When Group 1 is ALSO elevated alongside Groups 7+8, the content requires creative problem-solving — the operator must generate novel approaches rather than match to stored patterns. This is Rasmussen's knowledge-based mode operating without applicable rules. Flagged as "adaptive" variant.

**SRK error type:** Rule-based mistake — matching to the wrong pattern (availability bias). Knowledge-based mistake — constructing an incorrect integrated model.

**Unique anchor:** Group 8 + Group 7 + Hippocampus combination
**Detection rule:** Group 8 >= Moderate AND Group 7 >= Baseline AND Hippocampus engaged
**Cortical-only fallback:** Group 8 >= Moderate AND Group 7 >= Moderate (when subcortical data unavailable or unreliable — stricter cortical threshold compensates for missing hippocampal confirmation)
**Sub-signal:** If Group 1 >= Moderate, flag as "adaptive" variant
**Content that triggers it:** Log analysis, anomaly detection, attack reconstruction. Adaptive: novel scenarios, zero-day sims, broken assumptions.

**Cross-domain:** Aviation failure cascade analysis. Surgical diagnostic synthesis. Military intelligence fusion.

**Evidence level:** Strong
**Sources:**
- [Klein 1993/2008 — RPD model](https://journals.sagepub.com/doi/10.1518/001872008X288385)
- [Meta-analysis of 74 fMRI subsequent memory studies](https://pubmed.ncbi.nlm.nih.gov/20869446/)
- [Cognitive flexibility transfers to novel tasks, PMC 2023](https://pmc.ncbi.nlm.nih.gov/articles/PMC10236430/)

---

### Dimension 6: Stress Resilience

**Rasmussen mode:** All modes under degradation — stress causes regression (knowledge→rule→skill) and increases error rates across all modes
**Domain model:** Arnsten / Yerkes-Dodson

**What it is.** Maintaining cognitive performance when cortisol spikes. Acute uncontrollable stress causes rapid loss of prefrontal function through norepinephrine/dopamine flooding. Stress inoculation training — used by military special operations, surgeons, pilots — deliberately exposes trainees to controlled stress to build tolerance.

**The neural mechanism.** Under acute stress, high levels of norepinephrine and dopamine engage alpha-1 adrenergic and D1 dopamine receptors, opening potassium channels that weaken prefrontal network connectivity. Working memory, planning, and flexible thinking degrade. The amygdala takes over, driving reactive responses. Glucocorticoids (cortisol) exacerbate this effect. Stress inoculation training pushes the Yerkes-Dodson peak rightward — the operator maintains cognitive function at stress levels that would degrade an untrained person.

**SRK error type:** Stress-induced regression — the operator drops from knowledge-based to rule-based, or from rule-based to skill-based, applying simpler but less appropriate cognitive strategies. This is Rasmussen's most dangerous failure: the operator THINKS they're still reasoning but has actually regressed to pattern-matching or automatic responses.

**Why co-activation matters.** Content must engage cognitive circuits AND threat circuits simultaneously. Cognitive-only = classroom (not stress training). Threat-only = just alarming (not training). The combination is the training stimulus for stress inoculation.

**Caveat:** Measures the content's engagement signature, not the learner's actual stress response. Same limitation every training program accepts — the military designs stress-inducing stimuli and trusts that repeated exposure builds tolerance.

**Unique anchor:** Co-activation pattern — cognitive + threat simultaneous activation
**Detection rule:** (Group 1 OR Group 5 OR Group 8 >= Moderate) AND (Group 9 >= Moderate)
**Strength:** Limited by the weaker of cognitive vs threat — both must be present.
**Content that triggers it:** Time-pressured CTFs with consequences, inject-based exercises, chaos engineering, expanding-scope incidents under ambiguity

**Cross-domain:** Aviation upset recovery in full-motion sim. Surgical simulated emergency. Military stress inoculation. Source: [RAND — Stress Inoculation for Battlefield Airmen](https://www.rand.org/content/dam/rand/pubs/research_reports/RR700/RR750/RAND_RR750.pdf)

**Evidence level:** Strong
**Sources:**
- [Arnsten 2009 — Stress signalling impairs PFC](https://pmc.ncbi.nlm.nih.gov/articles/PMC2907136/)
- [McEwen 2012 — Brain on Stress, Neuron](https://pmc.ncbi.nlm.nih.gov/articles/PMC3753223/)
- [Lyons 2009 — Stress inoculation enhances PFC control](https://med.stanford.edu/content/dam/sm/parkerlab/documents/Lyons_Frontiers_2009.pdf)
- [Rasmussen SRK under time pressure, 2023](https://pmc.ncbi.nlm.nih.gov/articles/PMC10112018/) — quantified mode switching under stress

---

## 3. Inter-Dimension Dependencies

The 6 dimensions form a dependency structure rooted in Rasmussen's SRK hierarchy:

```
                    Stress Resilience (6)
              "Do ALL capabilities survive pressure?"
              Rasmussen: all modes under degradation
                    |                 |
                    |         depends on (1) and (2)
                    |                 |
              Procedural        Threat Detection
              Automaticity           (2)
                 (1)
                SKILL

              Strategic Decision (4)
              "Can the operator decide?"
                    |
              depends on (5)
                    |
              Analytical Synthesis (5)
              "Can the operator connect dots?"
                    |
              depends on (3)
                    |
              Situational Awareness (3)
              "Can the operator see the picture?"
```

**Enforced dependencies (from DEPENDENCY_ORDER):**
- **Stress Resilience (6) depends on Procedural Automaticity (1) + Threat Detection (2).** If procedures haven't reached Fitts & Posner's autonomous stage, they WILL fail when Arnsten's stress pathway kicks in. Train Dimensions 1 and 2 before testing Dimension 6.
- **Analytical Synthesis (5) depends on Situational Awareness (3).** You can't synthesize what you haven't perceived (Endsley: comprehension depends on perception).
- **Strategic Decision (4) depends on Analytical Synthesis (5).** Decisions are only as good as the mental model they're based on (Klein: RPD requires accurate situation assessment).
- **Stress Resilience (6) is the capstone.** It tests whether capabilities survive Arnsten's stress-induced prefrontal degradation.
- **Dimensions 1, 2, 3 have no prerequisites.** They can be trained in parallel from the start.

**Implication for gap recommendations:** Don't recommend stress resilience training if procedural automaticity is low. The operator needs to automate procedures FIRST (Fitts & Posner autonomous stage), then test them under stress (Yerkes-Dodson). Recommending a time-pressured CTF to someone who can't execute the basic procedure is setting them up for Rasmussen's most dangerous failure mode: stress-induced regression.

---

## 4. Operator Progression Model

Rather than Dreyfus's empirically unsupported 5 stages, this framework uses Rasmussen's SRK modes to describe operator development. The progression is characterized by which cognitive mode the operator primarily relies on, and which dimensions are covered:

| Development Phase | Primary SRK Mode | Dimension Profile | Observable Behavior |
|:---|:---|:---|:---|
| **Foundational** | Knowledge-based dominant | Dim 3 (SA) and Dim 5 (Synthesis) emerging. Dim 1 still conscious (Fitts cognitive stage). | Follows procedures consciously. Asks "what do I do next?" Can explain concepts but execution is slow. Makes knowledge-based errors: wrong mental models. |
| **Competent** | Rule-based dominant | Dim 4 (Decision) developing. Dim 1 transitioning (Fitts associative stage). Dim 2 (Threat) emerging. | Applies standard playbooks. Procedures becoming fluid. Starting to recognize patterns. Makes rule-based errors: applies wrong playbook to situation. |
| **Proficient** | Skill-based for routine, Rule-based for novel | Dim 1 autonomous (Fitts autonomous stage). Dim 5 strong. Dim 6 (Stress) emerging. | Routine tasks are automatic. Sees situations holistically. Can perform under moderate pressure. Makes slips occasionally but catches them. |
| **Expert** | Fluid mode-switching: Skill for execution, Knowledge for novelty | All 6 dimensions covered. Dim 1 fully automatic. Dim 6 proven under real stress. Dim 5 adaptive sub-signal active. | Acts intuitively for known situations (Klein RPD). Switches to analytical mode for novel situations. Maintains all capabilities under maximum stress. Mode transitions are smooth and appropriate. |

**What makes this better than Dreyfus:** Each phase is defined by observable, measurable criteria (which SRK mode dominates, which dimensions are covered) rather than subjective assessment. TRIBE can measure the dimension profile; the SRK mode is inferred from the pattern.

---

## 5. Known Limitations

### 5.1 What TRIBE Measures vs. What It Doesn't

TRIBE measures the brain engagement profile of **content** — it predicts which neural circuits training material would activate in an average brain. It does NOT measure:

- **Individual learner differences.** Two learners consuming the same content will have different actual brain responses.
- **Actual learning outcomes.** High engagement is necessary but not sufficient.
- **Learner's internal state.** Stress, motivation, attention — invisible to content-level prediction.

### 5.2 Dimensions We Cannot Measure

**Metacognition & Error Monitoring** — Self-monitoring requires inward attention, invisible to content prediction. Partially proxied by Group 10 in Dimension 4. True assessment requires behavioral measurement.
Source: [Nature 2024](https://www.nature.com/articles/s41539-024-00231-z)

**Team Coordination & Communication** — CRM involves social cognition (theory of mind, temporoparietal junction) outside our 10 brain groups. Requires behavioral assessment in team settings.
Source: [Crew Resource Management](https://en.wikipedia.org/wiki/Crew_resource_management)

### 5.3 Model Quality Constraints

Subcortical model (r=0.12, single subject, video-trained) is substantially weaker than cortical (r~0.5+, Meta pretrained). Conservative blending weights (effective beta 0.025-0.113) reflect this. Dimensions relying on subcortical anchors (especially 1 and 2) improve as the subcortical model improves.

### 5.4 Validation Required

Detection thresholds are derived from neuroscience literature and z-score distributions, not empirical correlation with operator performance. The critical validation step: predict brain engagement for content with KNOWN training outcomes, correlate dimension coverage with actual performance metrics.

---

## 6. Detection Rules (Implementation Spec)

### 6.1 Thresholds

- **Strong:** z-score > 1.0
- **Moderate:** z-score > 0.3
- **Baseline:** z-score > -0.3
- **Low:** z-score <= -0.3

Subcortical "engaged" = structure z-score >= 75th percentile threshold (config: threshold_percentile = 75.0)

### 6.2 Detection Function

```python
def detect_dimensions(group_scores: dict, subcortical: dict) -> dict:
    """Detect which operator readiness dimensions a piece of content covers.

    Args:
        group_scores: {group_id: z_score} for groups 1-10
        subcortical: {structure_name: {"z_score": float, "engaged": bool}}

    Returns:
        {dimension_key: {
            "covered": bool,
            "strength": float,
            "srk_mode": str,
            "details": dict
        }}
    """
    g = group_scores
    sc = subcortical

    MODERATE = 0.3
    BASELINE = -0.3

    dimensions = {}

    STRONG = 1.0

    # 1. Procedural Automaticity (Skill-based)
    g2_ok = g.get(2, -1) >= MODERATE
    putamen_engaged = sc.get("Putamen", {}).get("engaged", False)
    pallidum_engaged = sc.get("Pallidum", {}).get("engaged", False)
    sc_ok = putamen_engaged or pallidum_engaged
    cortical_fallback = g.get(2, -1) >= STRONG  # fallback when subcortical unreliable
    dimensions["procedural_automaticity"] = {
        "covered": g2_ok and (sc_ok or cortical_fallback),
        "strength": g.get(2, 0),
        "srk_mode": "skill-based",
        "details": {
            "cortical_motor": g.get(2, 0),
            "putamen": sc.get("Putamen", {}).get("z_score", 0),
            "pallidum": sc.get("Pallidum", {}).get("z_score", 0),
        },
    }

    # 2. Threat Detection & Calibration (Cross-mode)
    g9_ok = g.get(9, -1) >= MODERATE
    amygdala_engaged = sc.get("Amygdala", {}).get("engaged", False)
    g9_strong = g.get(9, -1) >= STRONG  # cortical-only fallback
    dimensions["threat_detection"] = {
        "covered": g9_ok and (amygdala_engaged or g9_strong),
        "strength": g.get(9, 0),
        "srk_mode": "cross-mode",
        "details": {
            "cortical_threat": g.get(9, 0),
            "amygdala": sc.get("Amygdala", {}).get("z_score", 0),
            "motivation": g.get(6, 0),
        },
    }

    # 3. Situational Awareness (Rule + Knowledge)
    g5_ok = g.get(5, -1) >= MODERATE
    g3_ok = g.get(3, -1) >= BASELINE
    g8_baseline = g.get(8, -1) >= BASELINE
    dimensions["situational_awareness"] = {
        "covered": g5_ok and g3_ok and g8_baseline,
        "strength": g.get(5, 0),
        "srk_mode": "rule-based",
        "details": {
            "attention_focus": g.get(5, 0),
            "comprehension": g.get(3, 0),
            "integration": g.get(8, 0),
            "thalamus": sc.get("Thalamus", {}).get("z_score", 0),
        },
    }

    # 4. Strategic Decision-Making & Reflection (Knowledge-based)
    g1_ok = g.get(1, -1) >= MODERATE
    g10_ok = g.get(10, -1) >= BASELINE
    dimensions["strategic_decision"] = {
        "covered": g1_ok and g10_ok,
        "strength": g.get(1, 0),
        "srk_mode": "knowledge-based",
        "details": {
            "executive_function": g.get(1, 0),
            "reflection": g.get(10, 0),
            "caudate_feedback": sc.get("Caudate", {}).get("z_score", 0),
        },
    }

    # 5. Analytical Synthesis & Pattern Matching (Knowledge + Rule)
    g8_ok = g.get(8, -1) >= MODERATE
    g7_ok = g.get(7, -1) >= BASELINE
    g7_mod = g.get(7, -1) >= MODERATE  # stricter cortical-only fallback
    hippo_engaged = sc.get("Hippocampus", {}).get("engaged", False)
    is_adaptive = g8_ok and g.get(1, -1) >= MODERATE
    dimensions["analytical_synthesis"] = {
        "covered": g8_ok and (g7_ok and hippo_engaged or g7_mod),
        "strength": g.get(8, 0),
        "srk_mode": "knowledge-based" if is_adaptive else "rule-based",
        "details": {
            "synthesis": g.get(8, 0),
            "memory_encoding": g.get(7, 0),
            "hippocampus": sc.get("Hippocampus", {}).get("z_score", 0),
            "adaptive": is_adaptive,
        },
    }

    # 6. Stress Resilience (All modes under degradation)
    cognitive_ok = (
        g.get(1, -1) >= MODERATE
        or g.get(5, -1) >= MODERATE
        or g.get(8, -1) >= MODERATE
    )
    threat_ok = g.get(9, -1) >= MODERATE
    cognitive_peak = max(g.get(1, -1), g.get(5, -1), g.get(8, -1))
    dimensions["stress_resilience"] = {
        "covered": cognitive_ok and threat_ok,
        "strength": min(cognitive_peak, g.get(9, -1)),
        "srk_mode": "all-modes-degraded",
        "details": {
            "cognitive_peak": cognitive_peak,
            "threat_activation": g.get(9, 0),
            "co_activation": cognitive_ok and threat_ok,
        },
    }

    return dimensions
```

---

## 7. Data Model

```
OperatorProfile {
    operator_id: string
    learning_path: string

    dimensions: {
        procedural_automaticity: DimensionScore
        threat_detection: DimensionScore
        situational_awareness: DimensionScore
        strategic_decision: DimensionScore
        analytical_synthesis: DimensionScore
        stress_resilience: DimensionScore
    }

    completed_modules: [ModuleEngagement]
    gaps: [DimensionGap]
}

DimensionScore {
    coverage: float         // 0.0-1.0
    mean_strength: float
    module_count: int
    last_engaged: date
}

ModuleEngagement {
    module_id: string
    module_name: string
    predicted_at: datetime
    group_scores: {group_id: float}
    subcortical_scores: {structure: float}
    dimensions: {dimension_key: {covered, strength, srk_mode, details}}
}

DimensionGap {
    dimension: string
    current_coverage: float
    severity: string            // "critical", "moderate", "minor"
    srk_error_risk: string      // what Rasmussen error type this gap enables
    blocked_by: [string]        // dimensions that should be trained first
    recommended_content: [string]
    message: string
}
```

---

## 8. Gap Detection & Recommendations

### 8.1 Gap Messages with SRK Error Risk

| Gap | Severity | SRK Error Risk | Message |
|:---|:---:|:---|:---|
| Low Procedural Automaticity | Critical | Slips under pressure | "This operator can explain procedures but hasn't automated them. Add timed hands-on labs and repetitive drills. Do NOT advance to stress testing until this is covered." |
| Low Threat Detection | Critical | Missed threats or alert fatigue | "Training doesn't engage threat detection circuits. Add escalating threat scenarios and false positive discrimination exercises." |
| Low Situational Awareness | Moderate | Rule-based mistake from lost SA | "The operator hasn't practiced maintaining the big picture. Add multi-host incident scenarios and expanding-scope simulations." |
| Low Strategic Decision | Moderate | Knowledge-based mistake from poor reasoning | "Training lacks decision-making under uncertainty. Add tabletops, incident command sims, and post-incident reviews." |
| Low Analytical Synthesis | Moderate | Wrong pattern match or failed integration | "The operator hasn't practiced connecting disparate data. Add log analysis exercises and attack reconstruction challenges." |
| Low Stress Resilience | Critical | Stress-induced SRK regression | "Content doesn't engage cognitive and threat circuits simultaneously. Add time-pressured CTFs. NOTE: verify Procedural Automaticity first." |

### 8.2 Dependency-Aware Recommendation Logic

```python
DEPENDENCY_ORDER = {
    "stress_resilience": ["procedural_automaticity", "threat_detection"],
    "analytical_synthesis": ["situational_awareness"],
    "strategic_decision": ["analytical_synthesis"],
}
```

If Stress Resilience is a gap but Procedural Automaticity is also a gap, recommend Procedural Automaticity FIRST and flag Stress Resilience as blocked. This prevents Rasmussen's stress-induced regression failure — you can't test stress resilience on skills that aren't automated yet.

---

## 9. Cortical-Subcortical Blending (Current Config)

| Group | Structure | Evidence Weight | Effective Beta | Key Evidence |
|:---|:---|:---:|:---:|:---|
| 7 | Hippocampus | 0.45 | 0.113 | [Meta-analysis of 74 fMRI studies](https://pubmed.ncbi.nlm.nih.gov/20869446/) |
| 2 | Putamen+Pallidum | 0.30 | 0.075 | [fMRI meta-analysis of striatal habits](https://pubmed.ncbi.nlm.nih.gov/35963543/) |
| 6 | Accumbens | 0.30 | 0.075 | [Meta-analysis of 49 MID studies](https://pmc.ncbi.nlm.nih.gov/articles/PMC6327084/) |
| 9 | Amygdala | 0.25 | 0.062 | [Amygdala fMRI critical appraisal](https://pmc.ncbi.nlm.nih.gov/articles/PMC11325331/) |
| 1 | Caudate | 0.25 | 0.062 | [PNAS 2020 caudate dissociation](https://www.pnas.org/doi/10.1073/pnas.2003963117) |
| 3 | Thalamus | 0.10 | 0.025 | [Nature Reviews Neuroscience 2024](https://www.nature.com/articles/s41583-024-00867-1) |
| 5 | Thalamus | 0.10 | 0.025 | Cannot resolve nuclei at standard fMRI resolution |

---

## 10. Operational Workflow

The intended use is **batch preprocessing of the HTB content library**, not real-time per-learner prediction:

1. **Batch predict all modules** — run every module (text, video, lab writeup) through TRIBE once (~5 min per module)
2. **Tag each module** — store its 6-dimension profile alongside existing metadata
3. **Define per-role requirements** — "SOC Analyst L2 needs all 6 dimensions. Pen Tester needs heavy Dims 1+4+5"
4. **For each learner on a path, compute gaps** — compare completed modules' dimension profiles against role requirements
5. **Serve recommendations instantly** — dimension profiles are precomputed properties of content, not per-learner predictions

Predictions happen on the CONTENT, not the learner. The brain engagement profile is a property of the training material. Process the library once (or on content updates), store dimension profiles, and recommendations become instant lookups.

**Estimated batch processing:** 500 modules × ~5 min/module ≈ 42 hours one-time compute. After that, recommendations are database queries.

---

## 11. Implementation Phases

### Phase 1: Dimension Scoring Engine
- Implement `detect_dimensions()` function
- Add `dimensions` field to `/api/v1/predict` response
- Include `srk_mode` and `details` for each dimension

### Phase 2: Operator Profile Accumulation
- POST /api/v1/profile/{operator_id}/modules — record module dimension scores
- GET /api/v1/profile/{operator_id} — return readiness profile

### Phase 3: Gap Detection & Recommendations
- GET /api/v1/profile/{operator_id}/gaps — dependency-aware gap analysis with SRK error risk
- Respect DEPENDENCY_ORDER

### Phase 4: UI Integration
- 6-dimension radar chart (Operator Readiness view)
- SRK mode indicator per dimension
- Gap visualization with dependency arrows
- Module-level dimension badges
