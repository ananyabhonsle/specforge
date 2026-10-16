"""Run TLC programmatically and return (success, error_message)."""
import subprocess
import shutil
from pathlib import Path
from config import TLC_JAR, RAFT_DIR, TLC_TIMEOUT_SECONDS

def run_tlc(spec_filename: str, work_dir: Path = RAFT_DIR) -> dict:
    """
    Run TLC on a spec file. Returns dict with:
      - success: bool
      - error: str or None (last ~2000 chars of TLC output if failed)
      - states_generated: int or None
      - wall_clock_s: float
    """
    spec_path = work_dir / spec_filename
    if not spec_path.exists():
        return {
            "success": False,
            "error": f"Spec file not found: {spec_path}",
            "states_generated": None,
            "wall_clock_s": 0.0,
        }

    # Also need a .cfg file with the same basename
    cfg_path = work_dir / spec_filename.replace(".tla", ".cfg")
    if not cfg_path.exists():
        return {
            "success": False,
            "error": f"Config file not found: {cfg_path}",
            "states_generated": None,
            "wall_clock_s": 0.0,
        }

    cmd = [
        "java", "-cp", str(TLC_JAR),
        "tlc2.TLC",
        "-config", cfg_path.name,
        spec_filename.replace(".tla", ""),
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=str(work_dir),
            capture_output=True,
            text=True,
            timeout=TLC_TIMEOUT_SECONDS,
        )
        output = result.stdout + "\n" + result.stderr

        if "No error has been found" in output:
            # Extract state count
            states = None
            for line in output.split("\n"):
                if "states generated" in line and "distinct" in line:
                    states = line.strip()
                    break
            return {
                "success": True,
                "error": None,
                "states_generated": states,
                "wall_clock_s": 0.0,
            }
        else:
            # Extract the last 2000 chars as the error
            return {
                "success": False,
                "error": output[-2000:],
                "states_generated": None,
                "wall_clock_s": 0.0,
            }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": f"TLC timed out after {TLC_TIMEOUT_SECONDS}s",
            "states_generated": None,
            "wall_clock_s": float(TLC_TIMEOUT_SECONDS),
        }

if __name__ == "__main__":
    # Smoke test with the existing MC.tla (known-good)
    print("Smoke testing run_tlc on MC.tla...")
    result = run_tlc("MC.tla")
    print(f"  success: {result['success']}")
    print(f"  states:  {result['states_generated']}")
    if result['error']:
        print(f"  error:   {result['error'][:500]}")
