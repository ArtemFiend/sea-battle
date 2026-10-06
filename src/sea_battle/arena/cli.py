import argparse
import asyncio
from collections.abc import Sequence

from sea_battle.arena.match import Arena, Player
from sea_battle.arena.service import HTTPGameService
from sea_battle.arena.tournament import Tournament, format_tournament_result


def _service(value: str) -> tuple[str, str]:
    name, separator, url = value.partition("=")
    if not separator or not name.strip() or not url.strip():
        raise argparse.ArgumentTypeError("expected NAME=URL")
    return name.strip(), url.strip()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a round-robin Sea Battle tournament",
    )
    parser.add_argument(
        "--service",
        action="append",
        required=True,
        type=_service,
        metavar="NAME=URL",
        help="service name and base URL; provide at least twice",
    )
    parser.add_argument("--timeout", type=float, default=1.0)
    parser.add_argument("--max-turns", type=int, default=1000)
    return parser


async def _run(args: argparse.Namespace) -> str:
    if len(args.service) < 2:
        raise ValueError("Provide at least two --service values")

    services = [
        HTTPGameService(url, timeout=args.timeout)
        for _, url in args.service
    ]
    players = [
        Player(name, service)
        for (name, _), service in zip(args.service, services, strict=True)
    ]
    try:
        tournament = Tournament(
            Arena(timeout=args.timeout, max_turns=args.max_turns)
        )
        result = await tournament.run(players)
        return format_tournament_result(result)
    finally:
        await asyncio.gather(*(service.aclose() for service in services))


def main(argv: Sequence[str] | None = None) -> None:
    args = _parser().parse_args(argv)
    try:
        output = asyncio.run(_run(args))
    except ValueError as error:
        raise SystemExit(str(error)) from error
    print(output)
