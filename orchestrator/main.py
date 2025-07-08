# orchestrator/main.py
import yaml
from core.agents.spec_agent import SpecAgent
from core.agents.run_agent import RunAgent
from core.agents.eval_agent import EvalAgent

def load_workflow(path):
    with open(path, 'r') as f:
        return yaml.safe_load(f)

def main(workflow_path: str):
    config = load_workflow(workflow_path)
    spec_agent = SpecAgent()
    detailed_config = spec_agent.load_spec(config)
    run_agent = RunAgent()
    output = run_agent.run(detailed_config)
    eval_agent = EvalAgent()
    metrics = eval_agent.evaluate(output)
    print("Run metrics:", metrics)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="neurOS orchestrator")
    parser.add_argument("--workflow", type=str, default="workflows/sample_pipeline.yaml")
    args = parser.parse_args()
    main(args.workflow)
