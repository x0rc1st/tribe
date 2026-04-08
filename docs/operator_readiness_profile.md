# Operator Readiness Profile

## A neuroscience-grounded framework for assessing cognitive readiness in high-stakes operator training

---

## 1. Foundation

### 1.1 What This Is

A measurement framework that maps brain engagement predictions from TRIBE v2 to the cognitive dimensions required for high-stakes operator mastery. For each piece of training content, TRIBE produces 17 data points (10 cortical group z-scores + 7 subcortical structure z-scores). This framework translates those data points into 6 operator readiness dimensions, each grounded in established neuroscience and each with a unique, distinguishable neural signature.

### 1.2 The Problem It Solves

Training programs label content by format (lecture, lab, simulation) or topic (forensics, incident response). But format and topic don't tell you which cognitive circuits the content actually engages. A module labeled "hands-on lab" might be a guided walkthrough that barely activates procedural circuits. A "threat simulation" might be a passive video that doesn't engage decision-making under pressure.

TRIBE measures what the content does to the brain. This framework maps those measurements to what the operator needs.

### 1.3 Scientific Lineage

This framework builds on four established research traditions:

**Dreyfus Model of Skill Acquisition (1980)** — Developed for the US Air Force to explain why expert pilots violated the very rules they were trained to follow. Five stages: Novice (rule-following, prefrontal-dependent) through Expert (intuitive, pattern-based, subcortical-automatic). The neural correlate of this progression is the cortico-striatal shift — skills migrate from conscious prefrontal processing to automatic basal ganglia execution.
Source: [Dreyfus & Dreyfus 1980](https://apps.dtic.mil/sti/tr/pdf/ADA084551.pdf), commissioned by US Air Force Office of Scientific Research

**Endsley's Situational Awareness Model (1995)** — Three hierarchical levels: perception, comprehension, projection. Loss of SA is the #1 cause of operator error in aviation. Validated across military, aviation, surgical, and nuclear domains.
Source: [Endsley 1995](https://journals.sagepub.com/doi/10.1518/001872095779049543)

**Klein's Naturalistic Decision Making (1993/2008)** — Recognition-Primed Decision model: experts don't analyze options, they recognize situations and act. Developed from studying fireground commanders, military officers, intensive care nurses. The brain basis: hippocampal pattern matching + prefrontal evaluation, not deliberate option comparison.
Source: [Klein 2008](https://journals.sagepub.com/doi/10.1518/001872008X288385)

**Cognitive Task Analysis (CTA)** — Military-developed technique for extracting expert cognitive processes through structured interviews. TRIBE automates a portion of this: instead of asking experts which cognitive skills a task requires, we measure which brain circuits the training content engages.
Source: [CTA-based surgical training meta-analysis](https://academic.oup.com/bjsopen/article/5/6/zrab122/6460901)

### 1.4 Applicable Domains

This framework applies to any domain where operators must perform under pressure with high consequences for failure:

| Domain | Operator | Critical failure modes |
|:---|:---|:---|
| Cybersecurity | SOC analyst, incident responder, penetration tester | Missed IOCs, frozen during incident, wrong triage priority |
| Military | Combat controller, intelligence analyst, drone operator | Loss of SA, failure to act under fire, misidentified threat |
| Aviation | Pilot, air traffic controller | Loss of SA, procedural error under stress, wrong decision with incomplete data |
| Surgery | Surgeon, anesthesiologist | Procedural error, missed complication, tunnel vision during crisis |
| Emergency services | Paramedic, firefighter | Wrong triage, frozen under pressure, missed hazard |

---

## 2. The 6 Dimensions

### 2.1 Why 6

We began with 8 candidate dimensions derived from the operator training literature. Two were dropped after auditing which dimensions produce unique, distinguishable signatures in TRIBE's 17 data points:

- **Metacognition & Error Monitoring** — dropped as standalone. TRIBE measures what content engages, not what the learner does internally. Self-monitoring requires the learner to turn attention inward, which is invisible to content-level prediction. The reflective processing signal (Group 10) is folded into Dimension 4 as the best available proxy. True metacognitive assessment requires behavioral measurement (confidence-calibrated quizzes, think-aloud protocols). Source: [Metacognitive monitoring & neural activity, Nature 2024](https://www.nature.com/articles/s41539-024-00231-z)

- **Adaptive Expertise** — merged into Dimension 5 (Analytical Synthesis). From TRIBE's data, the difference between "matching known patterns" (pattern recognition) and "inventing new approaches" (adaptive expertise) is whether Group 1 is also elevated alongside Groups 7+8. This is captured as a sub-signal within Analytical Synthesis rather than a separate dimension, because the two share anchor groups and would be weakly discriminated. Source: [Adaptive Expertise](https://en.wikipedia.org/wiki/Adaptive_expertise)

The remaining 6 dimensions each have at least one brain group or subcortical structure that serves as a **unique anchor** — no other dimension uses it as a primary signal.

### 2.2 Unique Anchor Summary

| # | Dimension | Unique Anchor | Why It's Unique |
|:---:|:---|:---|:---|
| 1 | Procedural Automaticity | Group 2, Putamen, Pallidum | Only dimension using motor/habit circuits |
| 2 | Threat Detection & Calibration | Group 9, Amygdala | Only dimension anchored on threat/emotional circuits |
| 3 | Situational Awareness | Group 5 | Only dimension anchored on attentional gating |
| 4 | Strategic Decision-Making & Reflection | Group 1 + Group 10 | Only dimension combining executive function with reflection |
| 5 | Analytical Synthesis & Pattern Matching | Group 8 + Group 7 + Hippocampus | Only dimension combining synthesis with memory binding |
| 6 | Stress Resilience | Co-activation pattern | Only dimension requiring cognitive + threat simultaneous activation |

---

### Dimension 1: Procedural Automaticity

**What it is.** Executing known procedures without conscious effort so they survive stress-induced prefrontal degradation. When cortisol floods the prefrontal cortex during a crisis, only skills that have migrated to automatic basal ganglia execution remain intact.

**The neural mechanism.** The cortico-striatal shift is one of the most replicated findings in motor learning neuroscience. Early in learning, the caudate nucleus (dorsomedial striatum) mediates conscious, goal-directed behavior — the learner thinks through each step. With practice, control transfers to the putamen (dorsolateral striatum), which drives automatic, habitual execution. The pallidum gates motor output, selecting which learned routine to execute. This transfer is observable in fMRI: caudate activation decreases while putamen activation increases as a skill becomes automatic.

**Why it matters for operators.** This is the single biggest predictor of operator failure under stress. If a procedure hasn't migrated from caudate to putamen, the operator will freeze when prefrontal function degrades under pressure. The military trains procedures to automaticity precisely because conscious processing fails under fire. A cybersecurity operator who has to "think about" running volatility analysis during a live incident is already behind.

**What failure looks like.** The operator can explain the procedure perfectly (high Group 3) but fumbles execution under time pressure. They know the steps but can't execute them fluidly. In cybersecurity: knows the incident response checklist but can't execute it under a live attack.

**The expert progression (Dreyfus mapping).**
- Novice: follows rules consciously (Group 1 + Caudate dominant)
- Competent: procedures becoming smoother (Groups 1 and 2 co-active)
- Expert: execution is fluid and unconscious (Group 2 + Putamen/Pallidum dominant, Group 1 quiet)

**Unique anchor:** Group 2 + Putamen + Pallidum — no other dimension uses these.
**Detection rule:** Group 2 >= Moderate AND (Putamen OR Pallidum) engaged
**Content that triggers it:** Timed CTF labs, repetitive tool drills, speed runs, muscle-memory command exercises, drills under simulated time pressure.

**Cross-domain parallels:**
- Aviation: simulator hours (distinct from ground school)
- Surgery: knot-tying drills, laparoscopic trainer repetitions
- Military: weapons handling drills, room-clearing rehearsals

**Evidence level:** Very strong
**Key sources:**
- Packard & Knowlton 2002 — Learning and memory functions of the basal ganglia
- Yin & Knowlton 2006 — Role of the basal ganglia in habit formation
- [fMRI meta-analysis of striatal habits, 2022](https://pubmed.ncbi.nlm.nih.gov/35963543/) — confirmed dorsolateral putamen in habit expression
- [PNAS 2020: spatiotemporal dissociation in caudate](https://www.pnas.org/doi/10.1073/pnas.2003963117) — head-to-tail caudate transition during skill learning

---

### Dimension 2: Threat Detection & Calibration

**What it is.** Developing appropriate threat reactivity — not maximum sensitivity, but calibrated sensitivity. Expert operators show lower amygdala response to routine threats (habituation) but maintained sensitivity to novel threats. The training goal is not to maximize amygdala activation but to calibrate it.

**The neural mechanism.** The amygdala tags experiences with emotional significance, which enhances memory consolidation through modulation of hippocampal encoding. The relationship between arousal and performance follows the Yerkes-Dodson inverted-U curve, now confirmed by modern neuroscience: performance peaks at moderate arousal, facilitated by optimal catecholamine (norepinephrine/dopamine) levels. Too little arousal and threats are missed; too much and the operator develops tunnel vision. The nucleus accumbens (Group 6) sustains motivational drive during long monitoring periods between threat events.

**Why it matters for operators.** An uncalibrated operator either misses real threats (under-arousal) or generates excessive false positives and burns out (over-arousal). SOC analysts who alert on everything are as dangerous as those who alert on nothing. The training challenge is exposure to enough threats that the amygdala learns to discriminate.

**What failure looks like.** Two modes: (1) Alert fatigue — operator has habituated to ALL signals, misses real threats. (2) Hypervigilance — operator treats every anomaly as critical, wastes resources, burns out. Both indicate miscalibrated threat circuits.

**Unique anchor:** Group 9 + Amygdala — fairly exclusive to this dimension.
**Detection rule:** Group 9 >= Moderate AND Amygdala engaged
**Content that triggers it:** Escalating threat scenarios, red team simulations, false positive discrimination exercises, mixed benign/malicious traffic analysis.

**Caveat:** TRIBE can't distinguish "well-calibrated threat training" from "merely alarming content." Both light up the same circuits. But if these circuits aren't engaged at all, the content is definitely not building threat detection capability. The measurement tells you whether the content creates the conditions for calibration; the actual calibration requires exposure over time.

**Cross-domain parallels:**
- Aviation: upset recovery training, engine failure simulation
- Surgery: recognizing hemorrhage vs. normal bleeding
- Military: IED recognition training, rules of engagement exercises

**Evidence level:** Strong
**Key sources:**
- McGaugh 2004 — The amygdala modulates the consolidation of memories of emotionally arousing experiences
- LaBar & Cabeza 2006 — Cognitive neuroscience of emotional memory
- [Yerkes-Dodson revisited, Trends in Cognitive Sciences 2024](https://www.cell.com/trends/cognitive-sciences/fulltext/S1364-6613(24)00078-0) — modern neuroscience confirms inverted-U
- [PNAS 2025: catecholaminergic arousal shifts the Yerkes-Dodson curve](https://www.pnas.org/doi/10.1073/pnas.2419733122)
- [Lupien et al 2007](https://pmc.ncbi.nlm.nih.gov/articles/PMC2657838/) — glucocorticoid inverted-U for memory performance

---

### Dimension 3: Situational Awareness

**What it is.** Endsley's three-level model: (1) perception of elements in the environment, (2) comprehension of their meaning, (3) projection of their future state. Loss of SA is the #1 documented cause of operator error in aviation and is consistently cited across military, surgical, and nuclear safety domains.

**The neural mechanism.** Level 1 (perception) engages the thalamic reticular nucleus, which gates sensory information — filtering what reaches cortical processing. Level 2 (comprehension) engages the perisylvian language network (Group 3) and the dorsal parietal attention network (Group 5) for integrating perceived elements into meaning. Level 3 (projection) engages the inferior parietal lobule and angular gyrus (Group 8) for constructing mental models of future states, supported by hippocampal relational memory for maintaining context.

**Why it matters for operators.** An operator without SA is flying blind. They may be technically skilled (high Dimension 1) and detect individual threats (high Dimension 2) but fail to maintain the overall picture. In cybersecurity: an analyst who focuses entirely on one suspicious process while missing that five other hosts are beaconing to the same C2. In aviation: a pilot fixated on one failing instrument while losing altitude.

**What failure looks like.** Tunnel vision. The operator narrows focus to one element and loses track of the broader operational picture. Also: failure to project — the operator understands what IS happening but can't anticipate what WILL happen next.

**Unique anchor:** Group 5 (literally named "Situational Awareness & Focus")
**Supporting:** Groups 3, 8 + Thalamus + Hippocampus
**Detection rule:** Group 5 >= Moderate AND Group 3 >= Baseline AND Group 8 >= Baseline
**Content that triggers it:** Multi-host incident scenarios, SOC dashboard exercises, expanding-scope simulations, scenarios requiring tracking multiple concurrent threads.

**Cross-domain parallels:**
- Aviation: scan pattern training, multi-instrument monitoring
- Surgery: maintaining awareness of patient vitals during complex procedure
- Military: battlefield management, tracking multiple units and threats simultaneously

**Evidence level:** Very strong (aviation — the most studied domain for SA)
**Key sources:**
- [Endsley 1995 — Toward a Theory of Situation Awareness](https://journals.sagepub.com/doi/10.1518/001872095779049543)
- [Saalmann et al 2012, Science](https://www.science.org/) — pulvinar thalamus in attentional modulation
- [USAARL 2025 — Holistic Situational Awareness and Decision Making](https://usaarl.health.mil/assets/docs/techReports/2025-10.pdf) — US Army Research Lab technical report

---

### Dimension 4: Strategic Decision-Making & Reflection

**What it is.** Acting with incomplete information under time pressure with irreversible consequences, then reflecting on outcomes to extract lessons. Combines Klein's Recognition-Primed Decision framework (experts don't compare options — they evaluate a single recognized course of action) with the reflective processing necessary to convert experience into expertise.

**The neural mechanism.** The prefrontal cortex (Group 1) mediates executive function: working memory, planning, cognitive flexibility, abstract reasoning, and value-based decisions. The caudate nucleus provides feedback-based learning signals — each outcome refines the next decision through reward prediction error. The default mode network, centered on posterior cingulate cortex (Group 10), activates during reflective processing — the neural basis of "thinking about thinking," reviewing past decisions, and extracting generalizable lessons.

**Why it matters for operators.** Two failure modes: (1) The operator who can't decide — paralyzed by ambiguity, waiting for more data that won't come. (2) The operator who decides but never reflects — makes the same mistakes repeatedly because experience isn't being consolidated into improved mental models. The reflection component (Group 10) is why after-action reviews are mandatory in military and surgical training — the decision alone is insufficient; the learning from the decision completes the cycle.

**What failure looks like.** Analysis paralysis during incidents. Or: the operator who has handled 50 incidents but hasn't improved because they never reflected on what worked and why.

**Note on metacognition:** This dimension absorbs the metacognitive component (self-evaluation, error monitoring) that was dropped as a standalone dimension. TRIBE detects whether content engages reflective circuits — but the actual self-monitoring behavior (calibrating confidence, catching own errors) requires behavioral measurement beyond TRIBE's scope.

**Unique anchor:** Group 1 + Group 10 combination
**Supporting:** Caudate (feedback-based learning)
**Detection rule:** Group 1 >= Moderate AND Group 10 >= Baseline
**Content that triggers it:** Tabletop exercises, incident command simulations, ambiguous evidence exercises, post-incident reviews, after-action reports, case studies with no single correct answer.

**Cross-domain parallels:**
- Aviation: crew decision-making exercises, accident case study analysis
- Surgery: morbidity and mortality conferences, complication reviews
- Military: tactical decision games, sand table exercises, after-action reviews

**Evidence level:** Strong
**Key sources:**
- [Klein 2008 — Naturalistic Decision Making](https://journals.sagepub.com/doi/10.1518/001872008X288385)
- [Caudate causal role in reward-evidence integration, PMC 2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC7308093/)
- [Metacognitive monitoring & neural activity, Nature 2024](https://www.nature.com/articles/s41539-024-00231-z) — DLPFC linked to metacognitive calibration accuracy

---

### Dimension 5: Analytical Synthesis & Pattern Matching

**What it is.** Integrating disparate data into coherent understanding and matching situations to known or novel patterns. Encompasses both recognition-primed assessment (Klein's RPD: expert matches current situation to stored patterns) and adaptive expertise (inventing new approaches when the playbook doesn't apply).

**The neural mechanism.** The inferior parietal lobule and angular gyrus (Group 8) are the brain's integration hub — where information from different modalities and domains converges into unified understanding. The hippocampus binds contextual elements (timestamps, IP addresses, behavioral sequences) into coherent episodic representations and enables relational memory — finding structural similarities between the current situation and past experience even when surface features differ. The medial temporal cortex (Group 7) supports the encoding of these integrated representations.

When Group 1 (prefrontal) is ALSO elevated alongside Groups 7+8, the content requires creative problem-solving — the operator must generate novel approaches rather than match to known patterns. This is flagged as the "adaptive" sub-signal.

**Why it matters for operators.** This is the "connect the dots" capability. An operator may perceive all the individual elements (Dimension 3, SA Level 1) but fail to synthesize them into a coherent picture. In cybersecurity: seeing the DNS anomaly, the firewall alert, and the failed SMB authentication as three separate events rather than one attack chain. Pattern matching is what makes the difference between an analyst who processes alerts and one who catches campaigns.

**What failure looks like.** The operator reports individual IOCs but can't construct the attack narrative. They see trees but not the forest. Or: they match every situation to the most recent pattern they learned (availability bias) rather than the most relevant one.

**Unique anchor:** Group 8 + Group 7 + Hippocampus combination
**Sub-signal:** If Group 1 is ALSO elevated, flag as "adaptive" — content requires novel problem-solving, not just pattern matching.
**Detection rule:** Group 8 >= Moderate AND Group 7 >= Baseline AND Hippocampus engaged
**Content that triggers it:**
- Pattern matching: Log analysis, anomaly detection, "spot the IOC" challenges, attack reconstruction exercises
- Adaptive variant: Novel scenarios with deliberately broken assumptions, zero-day simulations, exercises with no single correct answer

**Cross-domain parallels:**
- Aviation: weather pattern recognition, failure cascade analysis
- Surgery: diagnostic pattern recognition, complication anticipation
- Military: intelligence fusion, threat pattern analysis across multiple sources

**Evidence level:** Strong
**Key sources:**
- [Klein 1993/2008 — Recognition-Primed Decision model](https://journals.sagepub.com/doi/10.1518/001872008X288385)
- [Kim 2011 — Meta-analysis of 74 fMRI subsequent memory studies](https://pubmed.ncbi.nlm.nih.gov/20869446/) — hippocampal encoding predicts later recall
- [Cognitive flexibility transfers to novel task sets, PMC 2023](https://pmc.ncbi.nlm.nih.gov/articles/PMC10236430/)
- [Cognitive flexibility training for real-world impact, 2024](https://www.sciencedirect.com/science/article/pii/S2352154624000640)

---

### Dimension 6: Stress Resilience

**What it is.** Maintaining cognitive performance when cortisol spikes. Acute uncontrollable stress causes rapid and dramatic loss of prefrontal cognitive function through norepinephrine and dopamine flooding of alpha-1 adrenergic and D1 dopamine receptors, which open potassium channels that weaken prefrontal network connectivity. Stress inoculation training — used by military special operations, surgeons, and pilots — deliberately exposes trainees to controlled stress to build tolerance to this neurochemical degradation.

**The neural mechanism.** This dimension is unique because it is not about a single brain circuit but about the INTERACTION between circuits under pressure. Under moderate stress, prefrontal function is maintained and performance is optimized (Yerkes-Dodson peak). Under acute uncontrollable stress, prefrontal dendrites lose connectivity, working memory degrades, and the amygdala takes over — driving reactive, emotion-based responses rather than strategic ones. The training goal is to push the Yerkes-Dodson peak rightward: the operator can maintain cognitive function at stress levels that would degrade an untrained person.

**Why it matters for operators.** Every other dimension assumes the operator's brain is functioning normally. Stress Resilience determines whether those capabilities survive contact with reality. An operator with perfect procedural knowledge (Dimension 1) and excellent pattern matching (Dimension 5) will still fail if their prefrontal cortex goes offline during a real incident. This is why military training includes stress exposure phases, why surgical training includes simulated emergencies, and why pilot training includes upset recovery.

**What failure looks like.** The operator who performs flawlessly in training but freezes, panics, or makes catastrophic errors during a real incident. The gap between training performance and operational performance IS the stress resilience gap.

**The detection logic.** This is a co-activation pattern: content must engage cognitive circuits AND threat/emotional circuits simultaneously. If content only engages cognitive groups (no threat), it's classroom learning — valuable but not stress training. If content only engages threat circuits (no cognition), it's just alarming — not training. The specific combination is the training stimulus for stress inoculation.

**Caveat:** TRIBE measures the content's engagement signature, not the learner's actual stress response. But this is the same limitation every training program accepts — the military designs stress-inducing training stimuli and trusts that repeated exposure builds tolerance. They don't measure cortisol during every exercise. We measure whether the content creates the right conditions.

**Unique anchor:** Co-activation pattern — no other dimension requires cognitive + threat simultaneous activation.
**Detection rule:** (Group 1 OR Group 5 OR Group 8 >= Moderate) AND (Group 9 >= Moderate)
**Strength score:** Limited by the weaker of cognitive vs threat activation — both must be present.
**Content that triggers it:** Time-pressured CTFs with real consequences, inject-based exercises, chaos engineering scenarios, expanding-scope incidents under ambiguity.

**Cross-domain parallels:**
- Aviation: upset recovery in full-motion simulator, engine failure on takeoff
- Surgery: simulated hemorrhage during laparoscopic procedure, unexpected anatomy
- Military: stress inoculation training, combat simulation with live fire effects
- Source: [RAND — Stress Inoculation for Battlefield Airmen](https://www.rand.org/content/dam/rand/pubs/research_reports/RR700/RR750/RAND_RR750.pdf)

**Evidence level:** Strong
**Key sources:**
- [Arnsten 2009 — Stress signalling pathways that impair PFC](https://pmc.ncbi.nlm.nih.gov/articles/PMC2907136/) — the molecular mechanism
- [Arnsten 2015 — PFC executive processes affected by stress](https://pmc.ncbi.nlm.nih.gov/articles/PMC5756532/)
- [McEwen 2012 — Brain on Stress, Neuron](https://pmc.ncbi.nlm.nih.gov/articles/PMC3753223/) — stress effects on hippocampus, amygdala, PFC
- [Lyons 2009 — Stress inoculation enhances prefrontal cognitive control](https://med.stanford.edu/content/dam/sm/parkerlab/documents/Lyons_Frontiers_2009.pdf)
- [Yerkes-Dodson revisited, Trends in Cognitive Sciences 2024](https://www.cell.com/trends/cognitive-sciences/fulltext/S1364-6613(24)00078-0)

---

## 3. Inter-Dimension Dependencies

The 6 dimensions are not independent. They form a progression:

```
                    Stress Resilience (6)
                    "Can all of this survive pressure?"
                           |
              depends on ALL dimensions below
                           |
        +---------+---------+---------+
        |         |         |         |
  Procedural  Situational  Strategic  Analytical
  Automaticity Awareness   Decision   Synthesis
     (1)        (3)         (4)        (5)
        |         |         |         |
        +---------+---------+---------+
                           |
                  Threat Detection (2)
                  "Can I recognize what matters?"
```

**Key dependencies:**
- **Stress Resilience depends on Procedural Automaticity.** If procedures haven't migrated to putamen, they WILL fail under stress. Train Dimension 1 before testing Dimension 6.
- **Analytical Synthesis depends on Situational Awareness.** You can't synthesize what you haven't perceived. SA (Dimension 3) feeds the raw material that Synthesis (Dimension 5) integrates.
- **Strategic Decision depends on Analytical Synthesis.** Decisions are only as good as the mental model they're based on. A weak Dimension 5 means Dimension 4 operates on incomplete understanding.
- **Stress Resilience is the capstone.** It tests whether Dimensions 1-5 hold up under pressure. It should be trained LAST, after the component skills are in place.

**Implication for gap recommendations:** Don't recommend stress resilience training if procedural automaticity is low. The operator needs to automate procedures FIRST, then test them under stress. Recommending a time-pressured CTF to someone who can't yet execute the basic procedure is setting them up to fail.

---

## 4. Expert Progression Model

Mapped to the [Dreyfus Model of Skill Acquisition](https://apps.dtic.mil/sti/tr/pdf/ADA084551.pdf), developed for US Air Force pilot training:

| Dreyfus Stage | Dimension Profile | What It Looks Like |
|:---|:---|:---|
| **Novice** | Low across all. Dim 1 driven by Group 1 (conscious rule-following), not Group 2. | Follows checklists. Asks "what do I do next?" Needs explicit guidance. |
| **Advanced Beginner** | Dim 3 (SA) and Dim 5 (Synthesis) emerging. Dim 1 still Group 1-dominant. | Starts recognizing patterns but can't yet prioritize. Sees elements but not the picture. |
| **Competent** | Dim 4 (Decision) emerging. Dim 1 transitioning from Group 1 to Group 2. Dim 2 (Threat) developing. | Can plan and prioritize. Procedures becoming smoother. Starting to feel responsibility for outcomes. |
| **Proficient** | Dim 5 strong. Dim 1 now Group 2-dominant. Dim 6 (Stress) emerging. | Sees situations holistically. Procedures are automatic. Can perform under moderate pressure. Knows what's important immediately. |
| **Expert** | All 6 dimensions high. Dim 1 is pure Group 2 + Putamen. Dim 6 proven under real stress. | Acts intuitively. Doesn't follow rules — follows understanding. Maintains performance under maximum stress. Can improvise (Dim 5 adaptive sub-signal active). |

---

## 5. Known Limitations

### 5.1 What TRIBE Measures vs. What It Doesn't

TRIBE measures the brain engagement profile of **content** — it predicts which neural circuits a piece of training material would activate in an average brain. It does NOT measure:

- **Individual learner differences.** Two learners consuming the same content will have different actual brain responses based on their prior knowledge, motivation, attention, and neural architecture. TRIBE predicts the population-average response.
- **Actual learning outcomes.** High engagement is necessary but not sufficient for learning. A distracted learner won't encode content regardless of its engagement profile.
- **Learner's internal state.** Whether the learner is actually stressed, actually self-monitoring, actually motivated — these are invisible to content-level prediction.

### 5.2 Dimensions We Cannot Measure

**Metacognition & Error Monitoring** — Self-monitoring, confidence calibration, catching your own mistakes. Requires the learner to turn attention inward. Partially proxied by Group 10 within Dimension 4, but true metacognitive assessment requires behavioral measurement.
Source: [Nature 2024](https://www.nature.com/articles/s41539-024-00231-z)

**Team Coordination & Communication** — Crew Resource Management, shared mental models, coordinated action. Involves social cognition (theory of mind, temporoparietal junction) which doesn't map to our 10 brain groups. Requires behavioral assessment in team settings.
Source: [CRM](https://en.wikipedia.org/wiki/Crew_resource_management)

### 5.3 Model Quality Constraints

The subcortical model (r=0.12, single subject, video-trained) is substantially weaker than the cortical model (r~0.5+, Meta pretrained). This is reflected in conservative subcortical blending weights (effective beta 0.025-0.113). Dimensions that rely heavily on subcortical anchors (Dimensions 1 and 2 especially) will improve in detection accuracy as the subcortical model improves.

### 5.4 Validation Required

The dimension detection rules use thresholds derived from neuroscience literature and z-score distributions, not from empirical validation against actual operator performance. The critical next step is:
- Predict brain engagement for content with KNOWN training outcomes
- Correlate dimension coverage with actual operator performance metrics
- Tune detection thresholds based on empirical data

This is Priority #3 in the project roadmap: validate against HTB learning outcomes.

---

## 6. Detection Rules (Implementation Spec)

### 6.1 Thresholds

Score thresholds derived from z-score distribution:
- **Strong:** z-score > 1.0
- **Moderate:** z-score > 0.3
- **Baseline:** z-score > -0.3
- **Low:** z-score <= -0.3

Subcortical "engaged" = structure z-score >= 75th percentile threshold (from subcortical aggregator, config: threshold_percentile = 75.0)

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
            "details": dict  # dimension-specific sub-signals
        }}
    """
    g = group_scores
    sc = subcortical

    MODERATE = 0.3
    BASELINE = -0.3

    dimensions = {}

    # 1. Procedural Automaticity
    g2_ok = g.get(2, -1) >= MODERATE
    putamen_engaged = sc.get("Putamen", {}).get("engaged", False)
    pallidum_engaged = sc.get("Pallidum", {}).get("engaged", False)
    dimensions["procedural_automaticity"] = {
        "covered": g2_ok and (putamen_engaged or pallidum_engaged),
        "strength": g.get(2, 0),
        "details": {
            "cortical_motor": g.get(2, 0),
            "putamen": sc.get("Putamen", {}).get("z_score", 0),
            "pallidum": sc.get("Pallidum", {}).get("z_score", 0),
        },
    }

    # 2. Threat Detection & Calibration
    g9_ok = g.get(9, -1) >= MODERATE
    amygdala_engaged = sc.get("Amygdala", {}).get("engaged", False)
    dimensions["threat_detection"] = {
        "covered": g9_ok and amygdala_engaged,
        "strength": g.get(9, 0),
        "details": {
            "cortical_threat": g.get(9, 0),
            "amygdala": sc.get("Amygdala", {}).get("z_score", 0),
            "motivation": g.get(6, 0),  # sustained drive
        },
    }

    # 3. Situational Awareness
    g5_ok = g.get(5, -1) >= MODERATE
    g3_ok = g.get(3, -1) >= BASELINE
    g8_baseline = g.get(8, -1) >= BASELINE
    dimensions["situational_awareness"] = {
        "covered": g5_ok and g3_ok and g8_baseline,
        "strength": g.get(5, 0),
        "details": {
            "attention_focus": g.get(5, 0),
            "comprehension": g.get(3, 0),
            "integration": g.get(8, 0),
            "thalamus": sc.get("Thalamus", {}).get("z_score", 0),
        },
    }

    # 4. Strategic Decision-Making & Reflection
    g1_ok = g.get(1, -1) >= MODERATE
    g10_ok = g.get(10, -1) >= BASELINE
    dimensions["strategic_decision"] = {
        "covered": g1_ok and g10_ok,
        "strength": g.get(1, 0),
        "details": {
            "executive_function": g.get(1, 0),
            "reflection": g.get(10, 0),
            "caudate_feedback": sc.get("Caudate", {}).get("z_score", 0),
        },
    }

    # 5. Analytical Synthesis & Pattern Matching
    g8_ok = g.get(8, -1) >= MODERATE
    g7_ok = g.get(7, -1) >= BASELINE
    hippo_engaged = sc.get("Hippocampus", {}).get("engaged", False)
    is_adaptive = g8_ok and g.get(1, -1) >= MODERATE
    dimensions["analytical_synthesis"] = {
        "covered": g8_ok and g7_ok and hippo_engaged,
        "strength": g.get(8, 0),
        "details": {
            "synthesis": g.get(8, 0),
            "memory_encoding": g.get(7, 0),
            "hippocampus": sc.get("Hippocampus", {}).get("z_score", 0),
            "adaptive": is_adaptive,
        },
    }

    # 6. Stress Resilience (co-activation pattern)
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
    learning_path: string       // e.g., "SOC Analyst L2", "Penetration Tester"

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
    coverage: float         // 0.0-1.0, fraction of modules that hit this dimension
    mean_strength: float    // average strength across modules that hit it
    module_count: int       // how many modules contributed
    last_engaged: date      // recency matters — skills decay without reinforcement
}

ModuleEngagement {
    module_id: string
    module_name: string
    predicted_at: datetime
    group_scores: {group_id: float}
    subcortical_scores: {structure: float}
    dimensions: {dimension_key: {covered, strength, details}}
}

DimensionGap {
    dimension: string
    current_coverage: float
    severity: string            // "critical", "moderate", "minor"
    blocked_by: [string]        // dimensions that should be trained first
    recommended_content: [string]
    message: string
}
```

---

## 8. Gap Detection & Recommendations

### 8.1 Gap Messages

| Gap | Severity | Message |
|:---|:---:|:---|
| Low Procedural Automaticity | Critical | "This operator can explain procedures but hasn't automated them to muscle memory. Add timed hands-on labs and repetitive drills. Do NOT advance to stress testing until this dimension is covered." |
| Low Threat Detection | Critical | "Training content doesn't engage threat detection circuits. Add escalating threat scenarios, red team simulations, and false positive discrimination exercises." |
| Low Situational Awareness | Moderate | "The operator hasn't practiced maintaining the big picture under complexity. Add multi-host incident scenarios and expanding-scope simulations." |
| Low Strategic Decision | Moderate | "Training lacks decision-making under uncertainty. Add tabletop exercises, incident command simulations, and post-incident reviews." |
| Low Analytical Synthesis | Moderate | "The operator hasn't practiced integrating disparate data into coherent analysis. Add log analysis exercises, attack reconstruction challenges, and anomaly detection drills." |
| Low Stress Resilience | Critical | "Current content doesn't engage cognitive and threat circuits simultaneously. Add time-pressured CTFs with real consequences. NOTE: verify Procedural Automaticity is covered first." |

### 8.2 Dependency-Aware Recommendations

The gap engine must respect inter-dimension dependencies:

```python
DEPENDENCY_ORDER = {
    "stress_resilience": ["procedural_automaticity", "threat_detection"],
    "analytical_synthesis": ["situational_awareness"],
    "strategic_decision": ["analytical_synthesis"],
}
```

If Stress Resilience is a gap but Procedural Automaticity is also a gap, recommend Procedural Automaticity FIRST and flag Stress Resilience as blocked.

---

## 9. Cortical-Subcortical Blending (Current Config)

Per-group evidence weights from subcortical_cognitive_map.json, scaled by subcortical_reliability (0.25):

| Group | Structure | Evidence Weight | Effective Beta | Key Evidence |
|:---|:---|:---:|:---:|:---|
| 7 | Hippocampus | 0.45 | 0.113 | [Meta-analysis of 74 fMRI studies](https://pubmed.ncbi.nlm.nih.gov/20869446/) |
| 2 | Putamen+Pallidum | 0.30 | 0.075 | [fMRI meta-analysis of striatal habits](https://pubmed.ncbi.nlm.nih.gov/35963543/) |
| 6 | Accumbens | 0.30 | 0.075 | [Meta-analysis of 49 MID studies](https://pmc.ncbi.nlm.nih.gov/articles/PMC6327084/) |
| 9 | Amygdala | 0.25 | 0.062 | [Amygdala fMRI critical appraisal](https://pmc.ncbi.nlm.nih.gov/articles/PMC11325331/) |
| 1 | Caudate | 0.25 | 0.062 | [PNAS 2020 caudate dissociation](https://www.pnas.org/doi/10.1073/pnas.2003963117) |
| 3 | Thalamus | 0.10 | 0.025 | [Nature Reviews Neuroscience 2024](https://www.nature.com/articles/s41583-024-00867-1) |
| 5 | Thalamus | 0.10 | 0.025 | Same — cannot resolve nuclei at standard resolution |

---

## 10. Implementation Phases

### Phase 1: Dimension Scoring Engine
- Implement `detect_dimensions()` function
- Add `dimensions` field to `/api/v1/predict` response
- No new endpoints — enrich existing prediction response

### Phase 2: Operator Profile Accumulation
- POST /api/v1/profile/{operator_id}/modules — record a module's dimension scores
- GET /api/v1/profile/{operator_id} — return readiness profile with coverage across all 6 dimensions

### Phase 3: Gap Detection & Recommendations
- GET /api/v1/profile/{operator_id}/gaps — return gaps with dependency-aware recommendations
- Respect DEPENDENCY_ORDER when recommending

### Phase 4: UI Integration
- 6-dimension radar chart (Operator Readiness view)
- Per-operator dashboard with dimension coverage over time
- Gap visualization with recommended next modules
- Module-level dimension badges ("This module covers: Procedural Automaticity, Threat Detection")
