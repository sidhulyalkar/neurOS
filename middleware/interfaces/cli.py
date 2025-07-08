# interfaces/cli.py
import click
from core.orchestrator.main import main

@click.command()
@click.option("--workflow", default="workflows/sample_pipeline.yaml", help="Path to workflow YAML")
def cli(workflow):
    """CLI for neurOS orchestrator."""
    main(workflow)

if __name__ == "__main__":
    cli()