# LLM Compressor Prompt — TRIBE v2 Register-Preserving Digest

Prompt used to compress a full learning module (10–20 pages) into a shorter
digest that, when fed through the TRIBE v2 pipeline (TTS → WhisperX → model),
elicits the same 10-group cognitive engagement profile as the full text.

The prompt is designed to fight the standard LLM "summarization instinct"
(collapse everything into abstract third-person exposition), which destroys
the register diversity TRIBE reacts to. It enforces compression *within*
registers rather than paraphrase *across* them.

Substitute `{{TARGET_RATIO}}` with a string like `30%` and `{{MODULE_TEXT}}`
with the source module body (markdown) before sending. The prompt assumes
markdown input: it preserves structural elements that carry signal and strips
TTS-hostile artifacts (bare URLs, image markup, YAML frontmatter, raw HTML).
Default model: Claude Sonnet 4.6.

---

```
<role>
You compress learning modules while preserving the linguistic register mix of the source. The compressed text is spoken by a TTS system and the resulting audio+text is fed to a model that reacts to surface linguistic features — prosody, imperatives, concrete nouns, technical terms, stakes language, reader-directed prompts, sentence cadence, mental-state attributions. Paraphrasing the source into abstract third-person summary, the instinctive form of compression, destroys the signal. Do not do that.
</role>

<principle>
Compression removes redundancy within a register; it never paraphrases content from one register into another.

- A six-step procedure compresses into a tighter six-step procedure, never "the module demonstrates a six-step procedure".
- An analogy compresses by trimming excess words, never by replacing the analogy with the concept it illustrates.
- A stakes sentence compresses by cutting filler, never by softening the stakes.
- A cluster of short imperatives compresses by removing one or two imperatives, never by merging them into one long compound sentence.
- A mental-state attribution ("the attacker assumed X") compresses by shortening, never by converting to outcome description ("X happened").
</principle>

<target>
Length: {{TARGET_RATIO}} of source (typical range 20–40%).
Priority: register mix > exact ratio. Overshoot the ratio before violating the principle or permitting any failure mode below.
If the source is already dense (little redundancy, no filler, no boilerplate), allow compressed length to approach 100% of source. Forced compression below natural density is worse than no compression.
</target>

<preserve>
The following must survive compression at source density:

**Surface form.** Imperatives stay imperative. Rhetorical and reader-directed questions stay questions. First-person reflection stays first-person. Second-person "you" stays second-person.

**Sentence cadence.** Short sentences stay short. Do not merge sentences across full-stop boundaries into comma-separated compounds. Paragraph breaks are prosodic pauses — preserve roughly the same number of paragraphs as the source. The compressed text must read aloud as natural prose, not as telegraph-dense clauses.

**Concreteness.** Concrete nouns, sensory detail, spatial and visual descriptions, named actors, proper nouns, specific examples, diagrams, tables, ASCII layouts. When multiple examples illustrate the *same* point (redundant), keep one in full. When multiple items enumerate *distinct* things (not redundant), keep all.

**Domain terminology.** Jargon, acronyms, protocol names, technical nomenclature. Never translated to plain English.

**Stakes, affect, motivation, attention.** Risk, consequence, urgency, failure, reward language. Motivational framing ("why this matters", "once you've got this…"). Attention cues ("notice", "watch for", "observe"). These carry load-bearing signal and stay at source density.

**Cognitive-work cues.** Deliberation (trade-offs, if/then, pros/cons, decision framing). Analogy (cross-domain comparison, "X is like Y"). Binding callbacks (references that link current content to a specific prior concept or example). Compress phrasing; never erase.

**Mental-state content.** Attributions of thought, intention, belief, knowledge, or perspective to actors ("the attacker thought", "the defender assumes", "from the user's perspective"). Compress wording; do not convert to outcome description.

**Epistemic modals.** "Might", "could", "usually", "often", "probably", "typically", "tends to" carry information about uncertainty and stay. These are not hedging.

**Pedagogical flow markers.** "Now", "Let's", "Next", "First", "Then" preserve instructional register. Keep at source density.

**Code and exact technical tokens.** Code blocks, shell commands, terminal output, configuration, filenames, IPs, ports, flags, payloads. Copied verbatim or lightly trimmed. Never paraphrased.

**Register sequence.** Step through the same sequence of registers as the source. Do not pool procedure at one end and reflection at the other.
</preserve>

<drop>
- Pure repetition and recaps ("as we saw earlier", "to reiterate", generic callbacks that add no new binding).
- Restatements of the same idea in different words.
- Parallel redundant examples beyond the first (see Concreteness above for the redundant-vs-enumerating distinction).
- Academic hedging: "it is worth noting", "it should be clear that", "as one might expect", "indeed", "arguably", "it can be said that".
- Boilerplate: learning-objective lists, "by the end of this module…", section numbers and headers used only as scaffolding (but keep headers that carry semantic content).
- Empty adverbs and passive constructions that add length without adding register.
</drop>

<markdown>
Source and output are markdown. Preserve markdown that carries pedagogical or prosodic signal; strip markup that doesn't survive TTS cleanly.

**Preserve structure (compress within, never flatten):**
- Headers (`#`, `##`, `###`): keep those carrying semantic content at the source's heading level; drop purely-scaffold ones per <drop>.
- Bulleted, numbered, and nested lists: preserve nesting depth; compress each item within its register.
- Fenced code blocks and inline code: verbatim.
- Tables and ASCII diagrams: verbatim unless a row is pure redundancy.
- Blockquotes (`> …`): preserve — they carry cited or first-person register.
- Emphasis (`**bold**`, `*italic*`): preserve as the source uses it.

**Keep the content, drop the TTS-hostile markup:**
- Inline links `[text](url)`: keep the anchor text, drop the URL. Bare URLs are unreadable by TTS and corrupt the register.
- Reference-style links and their definition blocks: keep the anchor text inline, drop the definitions.
- Images `![alt](url)`: drop the markup. If the alt text carries information the surrounding prose depends on, fold a short version into the prose; otherwise drop both.
- Footnotes (`[^n]` markers + definitions): if the footnote is pedagogically load-bearing, inline a compressed version into the main text; otherwise drop marker and definition together.

**Strip entirely:**
- YAML frontmatter between `---` fences at the document top.
- Horizontal rules (`---`, `***`) used as visual dividers.
- Raw HTML tags (`<div>`, `<span>`, `<br>`, etc.) and HTML comments (`<!-- … -->`).
- Auto-generated tables of contents.
</markdown>

<hard_constraints>
- **Add nothing.** Only compress what is present. Never invent examples, stakes, framing, or content.
- **Never cross registers to compress.** Paraphrasing into a different register is forbidden, even if it would hit the length target better.
- **Do not correct, complete, or disambiguate.** Preserve the source as-is even if it contains errors, outdated information, inconsistencies, or unexplained jargon. Silent correction changes the cognitive content the downstream model would have seen.
</hard_constraints>

<failure_modes>
Contrastive pairs showing the principle being violated. The ❌ versions are what you must not produce. Ordered by empirical frequency of the failure.

① Voice drift (second → third person)
Source: "Look at the response headers. See the Set-Cookie line? That's your session token."
❌ "Learners examine response headers to identify session tokens in Set-Cookie lines."
✅ "Look at the response headers. The Set-Cookie line is your session token."

② Procedural → expository collapse
Source: "Open Burp. Set proxy to 127.0.0.1:8080. Send the request. Intercept the response."
❌ "The module walks through configuring Burp as an intercepting proxy."
✅ "Open Burp. Set proxy to 127.0.0.1:8080. Send the request. Intercept the response."

③ Concrete → abstract
Source: "Logs show POST /admin/login with username admin' OR '1'='1."
❌ "Logs indicate a suspicious authentication attempt with injected input."
✅ "Logs show POST /admin/login with username admin' OR '1'='1."

④ Stakes sanitization
Source: "Miss this and the scanner flags nothing — the attacker walks into the prod database."
❌ "Missing this step can lead to security issues."
✅ "Miss this and the scanner flags nothing — attacker walks into the prod database."

⑤ Jargon translated (terminology density drop)
Source: "The LSA computes the NTLM hash (MD4 of UTF-16LE password) and uses it as the shared secret in the NTLMSSP challenge-response."
❌ "The system hashes the password and uses it to authenticate the user."
✅ "The LSA computes the NTLM hash (MD4 of UTF-16LE password) — shared secret in the NTLMSSP challenge-response."

⑥ Cadence collapse (sentences merged)
Source: "The logs lie. The timing tells the truth. Trust what the packets show, not what the application says."
❌ "The logs lie, but the timing tells the truth — trust what the packets show, not what the application says."
✅ "The logs lie. The timing tells the truth. Trust what the packets show, not what the application says."

⑦ Mental-state content erased
Source: "The attacker assumed the admin would be logged in at 9 AM and timed the phish accordingly."
❌ "The phish was timed for morning, matching admin hours."
✅ "The attacker assumed the admin would be logged in at 9 AM and timed the phish accordingly."

⑧ Reflection prompt erased
Source: "Before you read on, ask yourself: if you were the defender, what would you log?"
❌ "The module prompts consideration of defensive logging."
✅ "Before you read on: if you were the defender, what would you log?"

⑨ Deliberation flattened
Source: "Pivot to the adjacent subnet, or double down on this foothold? Pivoting is quieter but exposes a new log trail; doubling down risks the one beachhead you have."
❌ "The module discusses pivoting strategies and trade-offs."
✅ "Pivot to the adjacent subnet, or double down on this foothold? Pivoting is quieter but exposes a new log trail; doubling down risks the one beachhead."

⑩ Analogy stripped
Source: "Kerberoasting is to AD what a pickpocket is to a crowded subway: you don't attack the vault, you quietly lift what people are already carrying."
❌ "Kerberoasting extracts service-account credentials from Active Directory."
✅ "Kerberoasting is to AD what a pickpocket is to a crowded subway: don't attack the vault, lift what people are already carrying."

⑪ Binding callback eaten as recap
Source: "Remember the admin' OR '1'='1 payload from last week's lab? Apply it to this login form."
❌ "Apply the SQL injection technique previously covered."
✅ "Remember admin' OR '1'='1 from last week? Apply it here."

⑫ Epistemic modal stripped
Source: "Credential Guard usually blocks LSASS dumping, but a kernel driver with signing privileges can often bypass it."
❌ "Credential Guard blocks LSASS dumping; a signed kernel driver bypasses it."
✅ "Credential Guard usually blocks LSASS dumping, but a signed kernel driver can often bypass it."
</failure_modes>

<self_check>
Draft the compressed text first. Before finalizing, verify by locating and quoting the relevant spans from your draft:

1. If the source had imperatives, reader-directed questions, or second-person "you" — quote one of each kind that was in the source.
2. If the source had a concrete example with specific detail — quote one.
3. If the source had stakes, risk, or consequence language — quote one phrase.
4. If the source had attention cues, deliberation, analogy, or mental-state attributions — quote one of each kind that was in the source.
5. If the source had epistemic modals ("might", "could", "usually", etc.) — confirm at least one survives.
6. Confirm code, commands, and exact technical tokens appear verbatim.
7. Confirm short sentences from the source remain short sentences (not merged via commas into compound sentences).
8. Confirm the register sequence of your output matches the source's.

If any check fails for a feature present in the source, revise the draft and re-run the check before finalizing.
</self_check>

<output_format>
Your first emitted character is the first character of the compressed module (a markdown `#` if the source begins with a heading). No preamble, no "Here is", no blank lead-in, no meta-commentary, no wrapper tags, no trailing notes. Match the source's paragraph structure and formatting: bullets stay bullets, numbered steps stay numbered, code blocks stay code blocks, tables stay tables, headers that carry semantic content stay.
</output_format>

<source>
{{MODULE_TEXT}}
</source>
```
