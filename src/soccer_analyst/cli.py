"""Command line interface: `sap`."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Annotated

import typer

from soccer_analyst import __version__
from soccer_analyst.registry import load_registry

app = typer.Typer(help="SoccerAnalystPro", no_args_is_help=True)
registry_app = typer.Typer(help="Registro di fonti e variabili", no_args_is_help=True)
app.add_typer(registry_app, name="registry")

DEFAULT_REGISTRY = Path("registry")


@app.command()
def version() -> None:
    """Stampa la versione."""
    typer.echo(__version__)


@registry_app.command("validate")
def registry_validate(
    registry_dir: Annotated[Path, typer.Option(help="Cartella del registro")] = DEFAULT_REGISTRY,
) -> None:
    """Valida registry/sources.yaml e registry/variables.yaml senza toccare il database."""
    reg = load_registry(registry_dir)
    by_level = Counter(v.level for v in reg.variables)
    by_feasibility = Counter(v.feasibility for v in reg.variables)
    typer.echo(f"Fonti: {len(reg.sources)}  Variabili: {len(reg.variables)}")
    typer.echo("Per livello: " + ", ".join(f"{k}={n}" for k, n in sorted(by_level.items())))
    typer.echo("Per fattibilità: " + ", ".join(f"{k}={n}" for k, n in sorted(by_feasibility.items())))


if __name__ == "__main__":
    app()
