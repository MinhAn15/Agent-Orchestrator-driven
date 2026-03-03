"""Generate Antigravity architecture diagram using the diagrams library.

Run: python docs/architecture.py
Output: docs/architecture.png (auto-committed by CI workflow)
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.client import User
from diagrams.onprem.network import Nginx
from diagrams.programming.language import Python
from diagrams.onprem.database import Redis
from diagrams.onprem.monitoring import Grafana
from diagrams.onprem.queue import Kafka

graph_attr = {
    "fontsize": "14",
    "bgcolor": "white",
    "pad": "0.5",
    "splines": "ortho",
}

with Diagram(
    "Antigravity — Agent Orchestration Architecture",
    filename="docs/architecture",
    outformat="png",
    show=False,
    graph_attr=graph_attr,
    direction="LR",
):
    client = User("Client")

    with Cluster("Antigravity Orchestrator"):
        gateway = Nginx("API Gateway")
        planner = Python("Planner")
        policy = Python("Policy Engine")
        executor = Python("Executor")

    with Cluster("Connectors & Tools"):
        tools = Python("Tool Layer")
        event_bus = Kafka("Event Bus")

    with Cluster("State & Memory"):
        memory = Redis("Memory Store")

    observability = Grafana("Observability\n(latency · cost · quality)")

    # Main flow
    client >> gateway >> planner >> policy
    policy >> Edge(label="approved") >> executor
    executor >> tools >> event_bus
    executor >> Edge(label="reads/writes") >> memory
    memory >> Edge(label="context") >> planner
    executor >> observability
