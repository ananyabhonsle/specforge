# SpecForge

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![TLA+](https://img.shields.io/badge/Spec-TLA%2B-purple)
![Model Checker](https://img.shields.io/badge/Model%20Checker-TLC-green)
![License](https://img.shields.io/badge/License-MIT-yellow)
![Cost](https://img.shields.io/badge/Experiment%20Cost-%240.00-brightgreen)

*Can LLMs write machine-checkable formal specifications? A closed-loop pipeline where an LLM writes TLA+ specifications from Raft Go code, and TLC brute-force verifies every reachable state.*

---

## Table of Contents

- [Overview](#overview)
- [Key Findings](#key-findings)
- [The Pipeline](#the-pipeline)
- [Results](#results)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [How It Works](#how-it-works)
- [Cost Audit](#cost-audit)
- [Limitations](#limitations)
- [Credits & Third-Party Tools](#credits--third-party-tools)
- [Related Work](#related-work)
- [Citation](#citation)

---

## Overview

SpecForge is a closed-loop pipeline that tests whether Large Language Models (LLMs) can write formal specifications that a model checker can verify. We feed Raft leader-election Go code to an LLM, it generates a TLA+ specification, and the TLC model checker brute-force verifies every possible state in the configured state space.

If TLC finds an error, the error message is fed back to the LLM for self-correction - up to 4 attempts.

### Research Question

Can LLMs translate distributed-systems code into verifiable TLA+ specifications, and can they fix their own errors using deterministic verifier feedback?

---

## Key Findings

- **GPT-OSS 120B writes verified specifications:** The LLM generated a TLA+ specification that TLC verified across 100 distinct states. Real election contention was explored.

- **A green checkmark can be a lie:** Qwen 3.8-27B also appeared to pass TLC, but the state graph had depth 1 and only 0 transitions. The specification was contradictory. Verification is meaningful only when the state space is inspected.

- **The closed loop fixes syntax, not semantics:** Incorrect TLA+ syntax can be self-corrected using TLC feedback, but semantic errors, such as infinite sets and contradictory constraints, require human intervention.

---

## The Pipeline

```text
Raft Go Code
     |
     v
    [LLM]
     |
     v
  TLA+ Spec
     |
     v
 [TLC Checker]
     |
     v
   Verdict
     |
     +---------------------------+
     |                           |
     | Error feedback            |
     v                           |
    [LLM] -----------------------+
          (max 4 attempts)
```

### Components

- **LLM:** GPT-OSS 120B (120B parameters, open-weight, via Groq free tier)
- **Specification Language:** TLA+, developed by Leslie Lamport, recipient of the 2013 Turing Award
- **Model Checker:** TLC (Java-based model checker from the TLA+ tools ecosystem)
- **Orchestrator:** Python pipeline with subprocess integration

---

## Results

| LLM | TLC Verdict | States Explored | Assessment |
|---|---|---|---|
| GPT-OSS 120B | No error | 321 generated / 100 distinct | Genuine pass |
| Qwen 3.8-27B | No error | 2 generated / 1 distinct | Vacuous pass |
| Gemini 3.8 Flash | HTTP 503 | - | Unavailable |

### Seeded Bug Demo

We removed the majority check from `BecomeLeader`, introducing the classic split-brain bug. TLC caught the violation:

```text
Error: Invariant AtMostOneLeader is violated.

State 4: s1 becomes Leader (term 1)  <- no majority!
State 5: s2 becomes Leader (term 1)  <- TWO LEADERS, SAME TERM
```

The violation demonstrates how model checking can detect a safety property failure that ordinary execution-based tests may not expose.

---

## Quick Start

### Prerequisites

- Python 3.10+
- Java 21+ (for TLC)
- Groq API key (free tier) - [Get an API key](https://console.groq.com/)

### Installation

```bash
git clone https://github.com/ananyabhonsle/specforge.git
cd specforge

# Java is required for TLC
sudo apt install -y default-jre

# Install Python dependencies
pip install streamlit

# Optional: configure the API key for the LLM pipeline
export GROQ_API_KEY="your-key-here"
```

### Run the Demo

**Option 1: Streamlit web app**

```bash
streamlit run app.py --server.port 8501 --server.headless true
```

**Option 2: Run TLC directly on the LLM-generated specification**

```bash
cd raft.tla
java -cp ../tla2tools.jar tlc2.TLC -config raft_llm.cfg raft_llm.tla
```

**Option 3: Run the full LLM pipeline**

```bash
python3 pipeline/extract.py
```

### Run TLC on Different Test Cases

From the `raft.tla/` directory:

```bash
# Case A: Expert reference specification (Ongaro's Raft)
java -cp ../tla2tools.jar tlc2.TLC -config MC.cfg MC.tla

# Case B: AI-generated specification (GPT-OSS 120B)
java -cp ../tla2tools.jar tlc2.TLC -config raft_llm.cfg raft_llm.tla

# Case C: Seeded split-brain bug
java -cp ../tla2tools.jar tlc2.TLC -config raft_llm_buggy.cfg raft_llm_buggy.tla

# Case D: Natural numbers (n + m = m + n)
java -cp ../tla2tools.jar tlc2.TLC -config nat_add.cfg nat_add.tla
```

---

## Project Structure

```text
specforge/
├── app.py                    # Streamlit web app (interactive demo)
├── tla2tools.jar             # TLC model checker (Java, MIT license)
├── pipeline/
│   ├── config.py             # API keys, paths, and model names
│   ├── raft_code.py          # Raft Go code (input to LLM)
│   ├── run_tlc.py            # Python wrapper for TLC subprocess
│   ├── extract.py             # Main pipeline (closed-loop orchestrator)
│   └── extract_qwen.py       # Qwen-specific pipeline runner
├── raft.tla/
│   ├── raft.tla              # Ongaro's reference Raft spec (CC-BY-4.0)
│   ├── MC.tla                # Bounded wrapper for Stage 0
│   ├── MC.cfg
│   ├── raft_llm.tla          # GPT-OSS generated spec (passing)
│   ├── raft_llm.cfg
│   ├── raft_llm_buggy.tla    # Same spec with bug injected
│   ├── raft_llm_buggy.cfg
│   ├── raft_llm_qwen.tla     # Qwen generated spec (vacuous pass)
│   ├── nat_add.tla           # Natural number test
│   ├── nat_add.cfg
│   └── counter.tla           # Counter test
└── results/
    ├── groq_run.json         # GPT-OSS attempt logs
    ├── qwen_run.json         # Qwen attempt logs
    ├── gemini_run.json       # Gemini attempt logs (all 503)
    └── summary.json          # Combined results
```

---

## How It Works

### 1. The Input

Raft Go code implementing simplified leader election is stored in `pipeline/raft_code.py`:

```go
func (s *Server) BecomeLeader(votesReceived int, clusterSize int) {
    if s.state != Candidate {
        return
    }

    if votesReceived > clusterSize/2 { // MAJORITY CHECK
        s.state = Leader
    }
}
```

### 2. The LLM Call

Python sends the source code and a prompt to the GPT-OSS 120B API:

```python
prompt = "You are a formal methods expert. Write a TLA+ spec..."
response = call_groq_api(prompt)
```

The LLM generates a TLA+ specification intended to represent the behavior and safety properties of the supplied code.

### 3. TLC Verification

The generated specification is written to disk, then TLC checks it:

```python
subprocess.run([
    "java",
    "-cp",
    "tla2tools.jar",
    "tlc2.TLC",
    "-config",
    "raft_llm.cfg",
    "raft_llm"
])
```

TLC explores the reachable states within the configured model and checks whether the `AtMostOneLeader` invariant holds.

### 4. The Closed Loop

If TLC reports an error, the error message is appended to the prompt and the LLM is called again, up to a maximum of four attempts:

```python
if not tlc_result.success:
    previous_error = tlc_result.error
    # Retry with error feedback (max 4 attempts)
```

This allows the model to respond to deterministic verification feedback rather than relying solely on its own assessment of the generated specification.

---

## Cost Audit

| Component | Provider | Cost | Card on File |
|---|---|---:|---|
| Compute | GitHub Codespaces (free tier) | $0.00 | No |
| LLM: GPT-OSS 120B | Groq (free tier) | $0.00 | No |
| LLM: Qwen 3.8-27B | Groq (free tier) | $0.00 | No |
| LLM: Gemini 3.8 Flash | Google AI Studio (free tier) | $0.00 | No |
| Model checker: TLC | Local (MIT license) | $0.00 | No |
| Raft reference specification | Diego Ongaro (CC-BY-4.0) | $0.00 | No |
| **Total** | | **$0.00** | **No** |

*Costs reflect the reported experiment and free-tier usage. They do not imply that future runs or usage beyond free-tier limits will remain free.*

---

## Limitations

- **Gemini availability:** Gemini 3.8 Flash was unavailable during testing (HTTP 503). The framework supports adding it.
- **Manual corrections:** Manual fixes were applied to LLM-generated specifications, including an infinite quantifier and duplicate definitions. These interventions are documented honestly.
- **Bounded state space:** The model is bounded to 2 servers and terms 0–3 for tractability.
- **Limited safety coverage:** Only one safety property, `AtMostOneLeader`, was tested. Four other Raft properties remain future work.
- **Vacuous verification:** A successful TLC exit does not by itself establish that a specification meaningfully models the intended system. The state graph and transition coverage must also be inspected.

---

## Credits & Third-Party Tools

- **Raft reference specification:** Diego Ongaro, [ongardie/raft.tla](https://github.com/ongardie/raft.tla), licensed under CC BY 4.0.
- **Model checker:** [TLA+ tools](https://github.com/tlaplus/tlaplus), distributed under the MIT License.
- **Language model:** GPT-OSS 120B by OpenAI, released under Apache 2.0, accessed through [Groq](https://console.groq.com/).
- **Project author:** Ananya Bhonsle.

SpecForge is an independent experiment evaluating LLM-generated formal specifications. LLMs were used as tools in the experiment, not as authors of this report. Third-party names and tools are acknowledged for attribution and do not imply endorsement of SpecForge.

---

## Related Work

- **ReProver (Yang et al., NeurIPS 2023):** Lean tactic suggestion with retrieval.
- **LeanAide (2024):** GPT-4 for informal-to-formal Lean translation.
- **AlphaProof (DeepMind, 2024):** Large-scale mathematical proof generation.
- **Self-Refine (Madaan et al., NeurIPS 2023):** Iterative self-correction, which provides a conceptual basis for the four-attempt feedback loop.

---

## Citation

If you use this work, please cite:

```bibtex
@misc{specforge2026,
  title={SpecForge: A Closed-Loop Pipeline for LLM-Generated Formal Specifications Verified by TLC},
  author={Bhonsle, Ananya},
  year={2026},
  howpublished={\url{https://github.com/ananyabhonsle/specforge}}
}
```

---

## License

MIT License - see the [LICENSE](LICENSE) file for details.
