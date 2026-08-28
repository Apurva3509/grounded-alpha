import argparse
import sys
from pathlib import Path
from typing import NoReturn

from grounded_alpha.audit import audit_packet
from grounded_alpha.parser import PacketValidationError, load_packet
from grounded_alpha.policy import load_policy
from grounded_alpha.renderers import render_json, render_markdown

FORMATTERS = {"json": render_json, "markdown": render_markdown}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="grounded-alpha",
        description="Audit financial research packets for evidence quality.",
    )
    parser.add_argument("packet", type=Path, help="Path to a research packet JSON file")
    parser.add_argument("--policy", type=Path, help="Optional TOML policy file")
    parser.add_argument(
        "--format", choices=FORMATTERS, default="markdown", help="Output format"
    )
    parser.add_argument("--output", type=Path, help="Write output to a file")
    return parser


def fail(message: str, exit_code: int = 2) -> NoReturn:
    sys.stderr.write(f"grounded-alpha: {message}\n")
    raise SystemExit(exit_code)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        raw, _ = load_packet(args.packet)
        policy = load_policy(args.policy)
        report = audit_packet(raw, policy)
    except (PacketValidationError, ValueError) as error:
        fail(str(error))

    output = FORMATTERS[args.format](report)
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    else:
        sys.stdout.write(output)
    return 0 if report.passed else 1
