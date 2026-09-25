"""Convenience entry point for Version 2."""

try:
    from Version2.app import main
except ModuleNotFoundError:
    # The deployment script places the runtime modules in one flat directory.
    from app import main


if __name__ == "__main__":
    raise SystemExit(main())
