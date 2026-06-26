import logging
from langgraph.graph import StateGraph, END
from backend.app.agents.state import AgentState
from backend.app.agents.supervisor import supervisor_agent
from backend.app.agents.monitoring import monitoring_agent
from backend.app.agents.diagnosis import diagnosis_agent
from backend.app.agents.decision import decision_agent
from backend.app.agents.reporting import reporting_agent

logger = logging.getLogger("agents.graph")

# Initialize StateGraph
workflow = StateGraph(AgentState)

# Add all agents as graph nodes
workflow.add_node("supervisor", supervisor_agent)
workflow.add_node("monitoring", monitoring_agent)
workflow.add_node("diagnosis", diagnosis_agent)
workflow.add_node("decision", decision_agent)
workflow.add_node("reporting", reporting_agent)

# Entry point is always the supervisor
workflow.set_entry_point("supervisor")

# Routing condition function
def router_condition(state: AgentState):
    next_node = state.get("next_agent", "monitoring")
    if next_node == "end":
        return END
    return next_node

# Add dynamic edges from supervisor based on the router
workflow.add_conditional_edges(
    "supervisor",
    router_condition,
    {
        "monitoring": "monitoring",
        "diagnosis": "diagnosis",
        "decision": "decision",
        "reporting": "reporting",
        END: END
    }
)

# Non-supervisor nodes always cycle back to the supervisor
workflow.add_edge("monitoring", "supervisor")
workflow.add_edge("diagnosis", "supervisor")
workflow.add_edge("decision", "supervisor")
workflow.add_edge("reporting", "supervisor")

# Compile graph workflow
app_graph = workflow.compile()
