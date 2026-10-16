import streamlit as st
import subprocess
import os

st.set_page_config(page_title="SpecForge", page_icon="🔍", layout="wide")
st.title("SpecForge 🔍")
st.subheader("Can LLMs write formal specifications that a machine can verify?")
st.caption("Research question: How reliably can LLMs translate distributed-systems code "
           "into verifiable TLA+ specs — and can they fix their own errors?")

st.header("The Pipeline")
c1, a1, c2, a2, c3, a3, c4, a4, c5 = st.columns([3, 0.6, 3, 0.6, 3, 0.6, 3, 0.6, 3])
c1.markdown("**1. Raft code**\n\nGo implementation")
c2.markdown("**2. LLM**\n\nwrites TLA+ spec")
c3.markdown("**3. TLA+ spec**\n\nformal math model")
c4.markdown("**4. TLC**\n\nexplores every state")
c5.markdown("**5. Verdict**\n\npass / violation trace")
for a in (a1, a2, a3, a4):
    a.markdown("### →")
st.info("↺ Closed loop: TLC's error is fed back to the LLM (max 4 self-correction attempts)")

PROJECT_ROOT = "/workspaces/specforge"
RAFT_DIR = os.path.join(PROJECT_ROOT, "raft.tla")
TLC_JAR = os.path.join(PROJECT_ROOT, "tla2tools.jar")

CASES = {
    "📘 Case A — Expert spec (Ongaro's Raft, bounded)": ("MC.cfg", "MC.tla"),
    "🤖 Case B — AI-generated spec (GPT-OSS 120B)": ("raft_llm.cfg", "raft_llm.tla"),
    "🐛 Case C — Same AI spec, majority check deleted (split-brain)": ("raft_llm_buggy.cfg", "raft_llm_buggy.tla"),
}

def show_where(tla_filename, keyword="BecomeLeader", ctx=9):
    path = os.path.join(RAFT_DIR, tla_filename)
    try:
        lines = open(path).read().splitlines()
        for i, l in enumerate(lines):
            if l.startswith(keyword):
                st.code("\n".join(lines[i:i+ctx]), language="text")
                return
        st.code("\n".join(lines[:15]), language="text")
    except FileNotFoundError:
        st.error(f"file not found: {path}")

st.header("Interactive Verification — pick a case, run the checker")
choice = st.selectbox("Case", list(CASES.keys()))
cfg_file, tla_file = CASES[choice]

st.markdown("**The critical part of the spec being checked:**")
show_where(tla_file)
st.markdown("**The invariant TLC tests at every reachable state:**")
st.code("\\A i, j \\in Server : (state[i] = Leader /\\ state[j] = Leader /\\ currentTerm[i] = currentTerm[j]) => i = j",
        language="text")

if st.button("▶ Run TLC model checker", type="primary"):
    with st.spinner("TLC exploring all reachable states…"):
        try:
            r = subprocess.run(
                ["java", "-cp", TLC_JAR, "tlc2.TLC",
                 "-config", cfg_file, tla_file.replace(".tla", "")],
                cwd=RAFT_DIR,
                capture_output=True, text=True, timeout=180
            )
            out = r.stdout + r.stderr
        except subprocess.TimeoutExpired:
            out = "TLC timed out after 180 seconds"
        except Exception as e:
            out = f"Error: {e}"

    if "is violated" in out:
        i = out.find("Error")
        st.error("❌ VIOLATION — the invariant can be broken. TLC's counterexample:")
        st.code(out[i:i+800], language="text")
    elif "No error has been found" in out:
        states = [l for l in out.splitlines() if "distinct states" in l]
        st.success("✅ PASS — no reachable state violates the invariant.")
        if states:
            st.caption(states[0])
    else:
        st.warning("TLC output (unexpected):")
        st.code("\n".join(out.splitlines()[-15:]), language="text")

st.header("Benchmark Summary")
st.table({
    "LLM": ["GPT-OSS 120B (Groq)", "Qwen 3.8-27B (Groq)", "Gemini 3.8 Flash (Google)"],
    "Verdict": ["✅ genuine pass", "⚠️ vacuous pass", "— HTTP 503"],
    "State space": ["321 / 100 distinct", "2 / 1 distinct (depth 1!)", "—"],
    "Lesson": ["AI spec survives all scenarios", "green check ≠ real verification",
               "infra limits documented honestly"],
})

st.header("Findings")
st.warning("**1.** The self-correction loop fixes syntax, not semantics (infinite sets, contradictory constraints).")
st.warning("**2.** A green checkmark can be vacuous — Qwen's spec passed with zero transitions enabled. "
           "Real verification means inspecting the state space, not just the verdict.")
st.caption("LLMs were the subject of this experiment, not the authors of this report. · "
           "Raft spec: Diego Ongaro (CC-BY-4.0) · TLC: MIT · GitHub Codespaces · $0.00")
