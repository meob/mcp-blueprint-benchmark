import json
import sys
from pathlib import Path

from .config import MODELS, RESULTS_DIR


def load_manifest():
    manifest_path = RESULTS_DIR / "manifest.json"
    if not manifest_path.exists():
        print("No manifest.json found in results/")
        return None
    return json.loads(manifest_path.read_text())


def check_model_coverage(manifest):
    """Check if all expected models are present in results."""
    if not manifest:
        return False
    
    expected_models = {m["name"] for m in MODELS}
    actual_models = set(manifest.get("models", []))
    
    missing = expected_models - actual_models
    extra = actual_models - expected_models
    
    print(f"Expected models: {sorted(expected_models)}")
    print(f"Actual models: {sorted(actual_models)}")
    
    if missing:
        print(f"Missing models: {sorted(missing)}")
        return False
    if extra:
        print(f"Extra models: {sorted(extra)}")
    return True


def check_cell_count(manifest):
    """Verify we have the expected number of cells."""
    if not manifest:
        return False
    
    models = len(manifest.get("models", []))
    approaches = len(manifest.get("approaches", []))
    tasks = len(manifest.get("tasks", []))
    runs = manifest.get("runs_per_cell", 0)
    
    expected = models * approaches * tasks * runs
    print(f"Expected cells: {models} × {approaches} × {tasks} × {runs} = {expected}")
    
    # Count actual result files and tasks per model
    actual_count = 0
    actual_models = set()
    actual_tasks_per_model = {}
    for model_dir in RESULTS_DIR.iterdir():
        if model_dir.is_dir() and model_dir.name != "__pycache__":
            actual_models.add(model_dir.name)
            model_tasks = set()
            for approach_dir in model_dir.iterdir():
                if approach_dir.is_dir():
                    for f in approach_dir.glob("*.json"):
                        actual_count += 1
                        # Extract task_id from filename
                        task_id = f.stem.rsplit("_r", 1)[0]
                        model_tasks.add(task_id)
            actual_tasks_per_model[model_dir.name] = model_tasks
    
    print(f"Actual result files: {actual_count}")
    print(f"Models with results: {sorted(actual_models)}")
    
    # Check if we have results for all expected models
    expected_models = set(manifest.get("models", []))
    missing_models = expected_models - actual_models
    if missing_models:
        print(f"Models pending: {sorted(missing_models)}")
        # Calculate expected for models that have results, using actual task counts
        expected_partial = 0
        for model, model_tasks in actual_tasks_per_model.items():
            expected_partial += len(model_tasks) * approaches * runs
        if actual_count == expected_partial:
            print(f"All cells complete for {len(actual_models)} models ({actual_count} cells)")
            return True
        else:
            print(f"Partial results: {actual_count}/{expected_partial} cells for available models")
            return False
    
    if expected != actual_count:
        print(f"Cell count mismatch: expected {expected}, got {actual_count}")
        return False
    return True


def check_score_distribution():
    """Check for excessive complete failures (score=0) that might indicate issues."""
    issues = []
    total_files = 0
    
    for model_dir in RESULTS_DIR.iterdir():
        if not model_dir.is_dir() or model_dir.name == "__pycache__":
            continue
        model = model_dir.name
        
        for approach_dir in model_dir.iterdir():
            if not approach_dir.is_dir():
                continue
            approach = approach_dir.name
            
            for result_file in approach_dir.glob("*.json"):
                total_files += 1
                try:
                    data = json.loads(result_file.read_text())
                    score = data.get("score", 0)
                    # Flag only complete failures (score=0) as potentially problematic
                    if score == 0:
                        issues.append({
                            "file": result_file.name,
                            "model": model,
                            "approach": approach,
                            "score": score,
                            "task": data.get("task_id"),
                            "checks": data.get("checks", [])
                        })
                except Exception as e:
                    issues.append({
                        "file": result_file.name,
                        "model": model,
                        "approach": approach,
                        "error": str(e)
                    })
    
    # Allow up to 5% complete failures (expected in benchmarking)
    failure_rate = len(issues) / total_files if total_files > 0 else 0
    threshold = 0.05  # 5%
    
    if failure_rate > threshold:
        print(f"\nFound {len(issues)} complete failures (out of {total_files} total, {failure_rate:.1%}):")
        for issue in issues[:10]:  # Show first 10
            print(f"  {issue['model']}/{issue['approach']}/{issue['file']}: score={issue.get('score')}")
        if len(issues) > 10:
            print(f"  ... and {len(issues) - 10} more")
        return False
    else:
        print(f"\nFound {len(issues)} complete failures (out of {total_files} total, {failure_rate:.1%}) - within acceptable threshold")
        return True


def check_token_consistency():
    """Check for large token count variations across runs of the same task."""
    # Group results by (model, approach, task)
    groups = {}
    
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
                    task = data.get("task_id")
                    key = (model, approach, task)
                    
                    if key not in groups:
                        groups[key] = []
                    groups[key].append({
                        "file": result_file.name,
                        "tokens": data.get("tokens", {}).get("total", 0),
                        "score": data.get("score", 0)
                    })
                except Exception:
                    pass
    
    # Check consistency within groups (allow moderate variations)
    inconsistencies = []
    for key, results in groups.items():
        if len(results) < 2:
            continue
        
        token_values = [r["tokens"] for r in results]
        if len(set(token_values)) > 1:
            # Only flag very large variations (more than 50% difference from mean)
            # LLM token counts can vary significantly between runs due to different reasoning paths
            mean_tokens = sum(token_values) / len(token_values)
            max_deviation = max(abs(t - mean_tokens) for t in token_values)
            if max_deviation > mean_tokens * 0.5:  # More than 50% variation
                inconsistencies.append({
                    "key": key,
                    "token_values": token_values,
                    "files": [r["file"] for r in results],
                    "mean": mean_tokens,
                    "max_deviation": max_deviation
                })
    
    if inconsistencies:
        print(f"\nFound {len(inconsistencies)} extreme token inconsistencies:")
        for inc in inconsistencies[:5]:
            print(f"  {inc['key']}: {inc['token_values']} (mean={inc['mean']:.0f}, max_dev={inc['max_deviation']:.0f})")
        return False
    return True


def main():
    """Run all verification checks."""
    print("=" * 60)
    print("MCP Blueprint Benchmark Verification")
    print("=" * 60)
    
    manifest = load_manifest()
    
    checks = [
        ("Manifest exists", lambda: manifest is not None),
        ("Model coverage", lambda: check_model_coverage(manifest)),
        ("Cell count", lambda: check_cell_count(manifest)),
        ("Score distribution", check_score_distribution),
        ("Token consistency", check_token_consistency),
    ]
    
    results = []
    for name, check_fn in checks:
        print(f"\n--- {name} ---")
        try:
            passed = check_fn()
            results.append((name, passed))
            print(f"Result: {'PASS' if passed else 'FAIL'}")
        except Exception as e:
            print(f"Error: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("Verification Summary")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"{name}: {status}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\nAll verification checks passed!")
        return 0
    else:
        print("\nSome verification checks failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())