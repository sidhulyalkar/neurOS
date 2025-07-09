# orchestrator/main.py
import asyncio
import yaml
from core.signals.pipeline import ProcessingGraph
from agents.device_agent import DeviceAgent
from agents.run_agent import RunAgent
from agents.eval_agent import EvalAgent



def load_workflow(path: str) -> dict:
    """Load YAML workflow spec from file."""
    with open(path, 'r') as f:
        return yaml.safe_load(f)

async def main_async(workflow_path: str):
    """
    Main asynchronous entry point.

    Loads a workflow spec from a YAML file, builds a ProcessingGraph from it,
    starts a device, sets up Run and Eval agents, and processes each incoming
    sample. On each sample, runs the processing graph, evaluates the output
    with the Eval agent, and prints metrics.

    Keeps alive until termination with Ctrl+C.
    """
    # 1. Load workflow spec
    spec = load_workflow(workflow_path)
    # 2. Build processing graph from spec
    graph = ProcessingGraph()
    # Expect spec format:
    # spec: { nodes: [ {name, processor, params}, ... ], edges: [ [from, to], ... ] }
    for node in spec.get('nodes', []):
        module_path, class_name = node['processor'].rsplit('.', 1)
        module = __import__(module_path, fromlist=[class_name])
        proc_cls = getattr(module, class_name)
        processor = proc_cls(**node.get('params', {}))
        graph.add_node(node['name'], processor)
    for edge in spec.get('edges', []):
        src, dst = edge
        graph.add_edge(src, dst)

    # 3. Start device
    device_agent = DeviceAgent()
    device, info = await device_agent.create_and_start(spec.get('device_key', 'mock'), **spec.get('device_params', {}))
    print(f"Device started: {info}")

    # 4. Setup Run and Eval agents
    run_agent = RunAgent()
    eval_agent = EvalAgent()

    # 5. On each incoming sample, process
    async def on_data(sample: dict):
        """
        On each incoming sample, process it through the graph, run the output
        through the RunAgent, evaluate the output with the EvalAgent, and
        print the evaluation metrics.
        """
        
        results = await graph.execute(sample, context=None)
        output = run_agent.run(results)
        metrics = eval_agent.evaluate(output)
        print("Metrics:", metrics)

    device.on('data', on_data)

    # 6. Keep alive until termination
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down device...")
        await device.stop_acquisition()

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='neurOS orchestrator')
    parser.add_argument('--workflow', type=str, default='workflows/sample_pipeline.yaml', help='Path to workflow YAML')
    args = parser.parse_args()
    asyncio.run(main_async(args.workflow))
