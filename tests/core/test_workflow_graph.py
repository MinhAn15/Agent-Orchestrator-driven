"""Test skeleton for workflow graph behaviors."""

from antigravity.workflow import WorkflowGraph


def test_workflow_graph_can_be_created_with_no_nodes() -> None:
    graph = WorkflowGraph()

    assert graph.nodes == ()
