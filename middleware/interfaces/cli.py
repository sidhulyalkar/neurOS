# middleware/interfaces/cli.py
import click
import asyncio
from orchestrator.main import main_async

@click.command()
@click.option(
    '--workflow',
    default='workflows/sample_workflow.yaml',
    help='Path to workflow YAML'
)
def cli(workflow):
    """CLI for neurOS orchestrator."""
    asyncio.run(main_async(workflow))

if __name__ == '__main__':
    cli()
