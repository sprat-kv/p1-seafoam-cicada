"""
Complete Project Validation Script

Runs all tests and validates the complete project implementation.
"""

import subprocess
import sys


def run_command(cmd, description):
    """Run a command and report results"""
    print(f"\n{'='*60}")
    print(f"{description}")
    print(f"{'='*60}")
    print(f"Command: {cmd}")
    print()
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    if result.returncode == 0:
        print(f"[PASS] {description}")
        return True
    else:
        print(f"[FAIL] {description}")
        return False


def main():
    print("\n" + "="*60)
    print("PROJECT VALIDATION SUITE".center(60))
    print("="*60)
    
    tests = [
        (
            ".venv\\Scripts\\python test_stage2.py",
            "Stage 2: Core Logic Tests"
        ),
        (
            ".venv\\Scripts\\python test_stage3.py",
            "Stage 3: HITL Workflow Tests"
        ),
        (
            ".venv\\Scripts\\python -c \"from app.main import app; print('FastAPI app loads successfully')\"",
            "FastAPI Application Load Test"
        ),
        (
            ".venv\\Scripts\\python -c \"from app.graph.workflow import compile_graph; from langgraph.checkpoint.memory import MemorySaver; g = compile_graph(MemorySaver(), ['admin_review']); print('Graph compilation successful')\"",
            "Graph Compilation Test"
        ),
    ]
    
    results = []
    for cmd, desc in tests:
        results.append(run_command(cmd, desc))
    
    print("\n" + "="*60)
    print("VALIDATION SUMMARY".center(60))
    print("="*60)
    
    for i, (cmd, desc) in enumerate(tests):
        status = "[PASS]" if results[i] else "[FAIL]"
        print(f"{status} {desc}")
    
    total = len(results)
    passed = sum(results)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n" + "="*60)
        print("ALL VALIDATIONS PASSED!".center(60))
        print("Project is ready for deployment".center(60))
        print("="*60 + "\n")
        return 0
    else:
        print("\n" + "="*60)
        print("SOME VALIDATIONS FAILED".center(60))
        print("="*60 + "\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
