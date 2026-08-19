import json
import sys
from pathlib import Path

from .config import RESULTS_DIR


def load_results():
    """Load all result files into a dictionary."""
    results = {}
    
    for model_dir in RESULTS_DIR.iterdir():
        if not model_dir.is_dir() or model_dir.name == "__pycache__":
            continue
        model = model_dir.name
        
        for approach_dir in model_dir.iterdir():
            if not approach_dir.is_dir():
                continue
            approach = approach_dir.name
            
            for result_file in approach_dir.glob("*.json"):
                try:
                    data = json.loads(result_file.read_text())
                    key = (model, approach, data.get("task_id"), data.get("repetition"))
                    results[key] = data
                except Exception as e:
                    print(f"Error loading {result_file}: {e}")
    
    return results


def check_required_fields(results):
    """Check that all results have required fields."""
    # Core fields required for benchmark analysis
    required_fields = [
        "run_id", "timestamp", "model", "approach", "task_id", "repetition",
        "score", "checks", "final_answer", "trace", "tokens", "latency_ms",
        "steps", "wall_ms"
    ]
    
    missing_fields = []
    for key, data in results.items():
        for field in required_fields:
            if field not in data:
                missing_fields.append({
                    "file": f"{data.get('model')}/{data.get('approach')}/{data.get('task_id')}__r{data.get('repetition')}.json",
                    "field": field
                })
    
    if missing_fields:
        print(f"Found {len(missing_fields)} missing fields:")
        for item in missing_fields[:10]:
            print(f"  {item['file']}: missing '{item['field']}'")
        return False
    return True


def check_score_range(results):
    """Check that all scores are between 0 and 1."""
    invalid_scores = []
    
    for key, data in results.items():
        score = data.get("score")
        if score is None or not (0 <= score <= 1):
            invalid_scores.append({
                "file": f"{data.get('model')}/{data.get('approach')}/{data.get('task_id')}__r{data.get('repetition')}.json",
                "score": score
            })
    
    if invalid_scores:
        print(f"Found {len(invalid_scores)} invalid scores:")
        for item in invalid_scores[:10]:
            print(f"  {item['file']}: score={item['score']}")
        return False
    return True


def check_token_counts(results):
    """Check that token counts are reasonable."""
    issues = []
    
    for key, data in results.items():
        tokens = data.get("tokens", {})
        prompt_tokens = tokens.get("prompt", 0)
        completion_tokens = tokens.get("completion", 0)
        total_tokens = tokens.get("total", 0)
        
        # Basic sanity checks
        if prompt_tokens < 0 or completion_tokens < 0 or total_tokens < 0:
            issues.append({
                "file": f"{data.get('model')}/{data.get('approach')}/{data.get('task_id')}__r{data.get('repetition')}.json",
                "issue": "negative token count",
                "tokens": tokens
            })
        elif total_tokens != prompt_tokens + completion_tokens:
            issues.append({
                "file": f"{data.get('model')}/{data.get('approach')}/{data.get('task_id')}__r{data.get('repetition')}.json",
                "issue": "token count mismatch",
                "tokens": tokens
            })
        elif total_tokens > 100000:  # Unreasonably high
            issues.append({
                "file": f"{data.get('model')}/{data.get('approach')}/{data.get('task_id')}__r{data.get('repetition')}.json",
                "issue": "unusually high token count",
                "tokens": tokens
            })
    
    if issues:
        print(f"Found {len(issues)} token count issues:")
        for item in issues[:10]:
            print(f"  {item['file']}: {item['issue']}")
        return False
    return True


def check_latency_measurements(results):
    """Check that latency measurements are reasonable."""
    issues = []
    
    for key, data in results.items():
        latency_ms = data.get("latency_ms")
        wall_ms = data.get("wall_ms")
        
        if latency_ms is not None and (latency_ms < 0 or latency_ms > 300000):  # > 5 minutes
            issues.append({
                "file": f"{data.get('model')}/{data.get('approach')}/{data.get('task_id')}__r{data.get('repetition')}.json",
                "issue": "unreasonable latency",
                "latency_ms": latency_ms
            })
        
        if wall_ms is not None and (wall_ms < 0 or wall_ms > 300000):  # > 5 minutes
            issues.append({
                "file": f"{data.get('model')}/{data.get('approach')}/{data.get('task_id')}__r{data.get('repetition')}.json",
                "issue": "unreasonable wall time",
                "wall_ms": wall_ms
            })
    
    if issues:
        print(f"Found {len(issues)} latency issues:")
        for item in issues[:10]:
            print(f"  {item['file']}: {item['issue']}")
        return False
    return True


def compare_with_shipped(results):
    """Compare current results with results_as_shipped/."""
    shipped_dir = RESULTS_DIR.parent / "results_as_shipped"
    if not shipped_dir.exists():
        print("No results_as_shipped/ directory found")
        return True
    
    # Load shipped manifest
    shipped_manifest_path = shipped_dir / "manifest.json"
    if not shipped_manifest_path.exists():
        print("No manifest.json in results_as_shipped/")
        return True
    
    shipped_manifest = json.loads(shipped_manifest_path.read_text())
    
    # Check if configurations are compatible
    current_manifest_path = RESULTS_DIR / "manifest.json"
    if current_manifest_path.exists():
        current_manifest = json.loads(current_manifest_path.read_text())
        
        # Skip comparison if configurations are significantly different
        if (set(current_manifest.get("tasks", [])) != set(shipped_manifest.get("tasks", [])) or
            set(current_manifest.get("approaches", [])) != set(shipped_manifest.get("approaches", [])) or
            current_manifest.get("num_ctx") != shipped_manifest.get("num_ctx")):
            print("Skipping comparison: configurations differ significantly")
            print(f"  Current: tasks={len(current_manifest.get('tasks', []))}, approaches={current_manifest.get('approaches', [])}, num_ctx={current_manifest.get('num_ctx')}")
            print(f"  Shipped: tasks={len(shipped_manifest.get('tasks', []))}, approaches={shipped_manifest.get('approaches', [])}, num_ctx={shipped_manifest.get('num_ctx')}")
            return True
    
    current_results = results
    
    # Load shipped results
    shipped_results = {}
    for model_dir in shipped_dir.iterdir():
        if not model_dir.is_dir() or model_dir.name == "__pycache__":
            continue
        model = model_dir.name
        
        for approach_dir in model_dir.iterdir():
            if not approach_dir.is_dir():
                continue
            approach = approach_dir.name
            
            for result_file in approach_dir.glob("*.json"):
                try:
                    data = json.loads(result_file.read_text())
                    key = (model, approach, data.get("task_id"), data.get("repetition"))
                    shipped_results[key] = data
                except Exception:
                    pass
    
    # Compare scores only for common keys
    common_keys = set(current_results.keys()) & set(shipped_results.keys())
    discrepancies = []
    
    for key in common_keys:
        current_score = current_results[key].get("score", 0)
        shipped_score = shipped_results[key].get("score", 0)
        
        # Only flag significant discrepancies (difference > 0.3)
        if abs(current_score - shipped_score) > 0.3:
            discrepancies.append({
                "key": key,
                "current_score": current_score,
                "shipped_score": shipped_score
            })
    
    if discrepancies:
        print(f"Found {len(discrepancies)} significant score discrepancies with results_as_shipped/:")
        for disc in discrepancies[:10]:
            print(f"  {disc['key']}: current={disc['current_score']}, shipped={disc['shipped_score']}")
        return False
    return True


def main():
    """Run all validation checks."""
    print("=" * 60)
    print("MCP Blueprint Benchmark Validation")
    print("=" * 60)
    
    results = load_results()
    print(f"Loaded {len(results)} result files")
    
    checks = [
        ("Required fields", check_required_fields),
        ("Score range", check_score_range),
        ("Token counts", check_token_counts),
        ("Latency measurements", check_latency_measurements),
        ("Comparison with shipped", compare_with_shipped),
    ]
    
    validation_results = []
    for name, check_fn in checks:
        print(f"\n--- {name} ---")
        try:
            passed = check_fn(results)
            validation_results.append((name, passed))
            print(f"Result: {'PASS' if passed else 'FAIL'}")
        except Exception as e:
            print(f"Error: {e}")
            validation_results.append((name, False))
    
    print("\n" + "=" * 60)
    print("Validation Summary")
    print("=" * 60)
    
    all_passed = True
    for name, passed in validation_results:
        status = "PASS" if passed else "FAIL"
        print(f"{name}: {status}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\nAll validation checks passed!")
        return 0
    else:
        print("\nSome validation checks failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())