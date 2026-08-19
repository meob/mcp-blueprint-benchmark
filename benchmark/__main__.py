import sys
import importlib


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ["--help", "-h"]:
        print("Usage: python -m benchmark <command> [args]")
        print("Commands:")
        print("  run       Run the benchmark")
        print("  verify    Run verification checklist")
        print("  validate  Validate results consistency")
        sys.exit(0)
    
    command = sys.argv[1]
    
    if command == "run":
        from .run import main as run_main, parse_args
        args = parse_args()
        import asyncio
        asyncio.run(run_main(args))
    elif command == "verify":
        from .verify import main as verify_main
        sys.exit(verify_main())
    elif command == "validate":
        from .validate import main as validate_main
        sys.exit(validate_main())
    else:
        print(f"Unknown command: {command}")
        print("Commands: run, verify, validate")
        sys.exit(1)


if __name__ == "__main__":
    main()