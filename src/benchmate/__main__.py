"""Lazy command entry point: verification needs the Python standard library only."""
import sys


def main():
    if sys.argv[1:2] == ["verify"]:
        from .verify import main as verify_main
        return verify_main(sys.argv[2:])
    from .cli import main as legacy_main
    return legacy_main()


if __name__ == "__main__":
    sys.exit(main())
