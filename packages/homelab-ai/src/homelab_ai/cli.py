"""``homelab-ai`` developer CLI: inspect the model chain and smoke-test providers."""

import argparse
import sys
import time

from pydantic import BaseModel, Field

from .exceptions import HomelabAIError
from .providers import build_model, get_provider
from .settings import AISettings, ModelSpec
from .task import AITask


class Probe(BaseModel):
    answer: str = Field(description="The single word 'pong'")


def _models(settings: AISettings) -> int:
    for role, spec in [("primary", settings.model)] + [
        ("fallback", s) for s in settings.fallback_models
    ]:
        try:
            status = "ready" if get_provider(spec).is_configured(settings) else "no credentials"
        except HomelabAIError as exc:
            status = str(exc)
        print(f"{role:<9} {spec!s:<45} {status}")
    return 0


def _ping(settings: AISettings, specs: list[ModelSpec]) -> int:
    failures = 0
    for spec in specs or settings.chain:
        start = time.perf_counter()
        try:
            model = build_model(spec, settings)
            task = AITask(
                name="ping",
                output_type=Probe,
                instructions="Reply with the word pong.",
                settings=settings.model_copy(update={"attempts": 1}),
                models=[model],
            )
            answer = task.run_sync("ping").answer
            print(f"ok    {spec!s:<45} {time.perf_counter() - start:6.2f}s  {answer!r}")
        except HomelabAIError as exc:
            failures += 1
            print(f"FAIL  {spec!s:<45} {time.perf_counter() - start:6.2f}s  {exc}")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="homelab-ai", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("models", help="Show the configured model chain and credential status")
    ping = sub.add_parser("ping", help="Call each model directly with a tiny structured prompt")
    ping.add_argument(
        "-m",
        "--model",
        action="append",
        default=[],
        help="Model spec to test, e.g. anthropic:claude-haiku-5-5 (repeatable; default: chain)",
    )
    args = parser.parse_args(argv)
    settings = AISettings()
    if args.command == "models":
        return _models(settings)
    return _ping(settings, [ModelSpec.parse(m) for m in args.model])


if __name__ == "__main__":
    sys.exit(main())
