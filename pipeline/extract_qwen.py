"""Run pipeline with Qwen 3.8-27B as the LLM."""
import json, re, time, urllib.request, urllib.error, sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from config import GROQ_API_KEY, QWEN_MODEL, MAX_ATTEMPTS, RAFT_DIR, RESULTS_DIR
from raft_code import RAFT_GO_CODE, TARGET_INVARIANT
from run_tlc import run_tlc

def call_qwen(prompt):
    url = "https://api.groq.com/openai/v1/chat/completions"
    payload = {"model": QWEN_MODEL, "messages": [{"role": "user", "content": prompt}], "temperature": 0.2, "max_tokens": 3000}
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "User-Agent": "specforge/1.0"
    })
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read())
        return data["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:300]
        raise Exception(f"HTTP {e.code}: {body}")

def build_prompt(previous_error=None):
    parts = [
        "You are a formal methods expert. Below is a simplified Go implementation",
        "of Raft leader election. Your task: write a TLA+ specification that",
        "models this code, plus an invariant AtMostOneLeader that no two servers",
        "can both be Leader in the same term.",
        "",
        "Output rules (CRITICAL):",
        "1. Output ONLY the TLA+ module, starting with ---- MODULE raft_llm ----",
        "2. Do NOT wrap output in markdown code fences",
        "3. Use CONSTANTS for Server, Follower, Candidate, Leader, Nil",
        "4. Use [x EXCEPT ![s] = v] for state updates",
        "5. The module MUST end with ====",
        "6. Include: Init, Next, Spec, and AtMostOneLeader definitions",
        "7. Use EXTENDS Naturals at the top",
        "8. Bound all quantifiers — never use \\E x \\in Nat, always \\E x \\in 0..3",
        "",
        "Go code:",
        RAFT_GO_CODE,
        "",
        "Target invariant:",
        TARGET_INVARIANT,
    ]
    if previous_error:
        parts.extend(["", "=== PREVIOUS ATTEMPT FAILED ===",
            "Your previous TLA+ spec failed TLC with this error:",
            previous_error[:1500], "",
            "Fix the issue and output the COMPLETE corrected spec."])
    return "\n".join(parts)

def extract_tla_module(llm_output):
    text = re.sub(r"```(?:tla)?\s*", "", llm_output)
    text = text.replace("```", "")
    match = re.search(r"----+\s*MODULE\s+(\w+)\s*----+(.*?)====+", text, re.DOTALL)
    if match:
        return f"---- MODULE raft_llm ----\n{match.group(2)}\n====\n"
    return f"---- MODULE raft_llm ----\n{text.strip()}\n====\n"

def write_spec_files(tla_content):
    spec_path = RAFT_DIR / "raft_llm_qwen.tla"
    cfg_path = RAFT_DIR / "raft_llm_qwen.cfg"
    spec_path.write_text(tla_content)
    cfg_content = """SPECIFICATION Spec
CHECK_DEADLOCK FALSE
INVARIANT AtMostOneLeader

CONSTANTS
Server = {s1, s2}
Follower = Follower
Candidate = Candidate
Leader = Leader
Nil = Nil
"""
    cfg_path.write_text(cfg_content)
    return spec_path

print(f"\n{'='*60}\n  Running pipeline: Qwen 3.8-27B\n{'='*60}")
result = {"vendor": "Qwen", "model": QWEN_MODEL, "timestamp": datetime.now().isoformat(),
          "attempts": [], "final_success": False, "rounds_needed": None, "tier_reached": 0}
previous_error = None

for attempt_num in range(1, MAX_ATTEMPTS + 1):
    print(f"\n--- Attempt {attempt_num}/{MAX_ATTEMPTS} ---")
    prompt = build_prompt(previous_error)
    print(f"  -> Calling Qwen API...")
    t0 = time.time()
    try:
        raw_response = call_qwen(prompt)
    except Exception as e:
        err_msg = str(e)[:500]
        print(f"  x API call failed: {err_msg}")
        result["attempts"].append({"attempt": attempt_num, "api_error": err_msg})
        previous_error = f"API error: {e}"
        time.sleep(3)
        continue
    api_time = time.time() - t0
    print(f"  v API responded in {api_time:.1f}s ({len(raw_response)} chars)")

    tla_content = extract_tla_module(raw_response)
    write_spec_files(tla_content)

    tlc_result = run_tlc("raft_llm_qwen.tla")

    tier = 0
    if tlc_result["success"]:
        tier = 4
    elif tlc_result["error"]:
        err = tlc_result["error"]
        if any(w in err for w in ["Encountered", "Unknown", "expected", "syntax"]):
            tier = 0
        elif any(w in err for w in ["Invariant", "Property", "violated"]):
            tier = 2
        else:
            tier = 1

    attempt_record = {"attempt": attempt_num, "api_time_s": round(api_time, 2),
                      "tier_reached": tier, "tlc_success": tlc_result["success"],
                      "tlc_error": tlc_result["error"][:500] if tlc_result["error"] else None}

    if tlc_result["success"]:
        print(f"  vvv TLC PASSED on attempt {attempt_num}!")
        print(f"     States: {tlc_result['states_generated']}")
        result["final_success"] = True
        result["rounds_needed"] = attempt_num
        result["tier_reached"] = 4
        result["attempts"].append(attempt_record)
        break
    else:
        err_snippet = tlc_result["error"][-400:] if tlc_result["error"] else "unknown"
        print(f"  x TLC failed (tier {tier}). Error tail:")
        for line in err_snippet.strip().split("\n")[-5:]:
            print(f"     {line}")
        previous_error = tlc_result["error"]
        result["tier_reached"] = max(result["tier_reached"], tier)
        result["attempts"].append(attempt_record)

RESULTS_DIR.mkdir(exist_ok=True)
with open(RESULTS_DIR / "qwen_run.json", "w") as f:
    json.dump(result, f, indent=2)
print(f"\nResults saved to {RESULTS_DIR / 'qwen_run.json'}")
print(f"\nFinal: success={result['final_success']}, tier={result['tier_reached']}, rounds={result['rounds_needed']}")
