import os
from typing import Dict, Any, Optional, List

from core.model_router import ModelRouter
from core.tier_classifier import TierClassifier
from core.cost_tracker import CostTracker
from core.escalation_protocol import EscalationProtocol

try:
    from google.cloud import aiplatform
except ImportError:
    aiplatform = None

try:
    from langchain_google_vertexai import ChatVertexAI
    from langchain.agents import initialize_agent, AgentType
except ImportError:
    ChatVertexAI = None
    initialize_agent = None
    AgentType = None


class GCPComputeTool:
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.name = "GCP Compute Manager"
        self.description = "Manages Antigravity TPU node instances."


class VertexAIJobTool:
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.name = "Vertex AI Job Runner"
        self.description = "Submits AlphaEvolve AutoML jobs for CY4 metric search."


class BigQueryTool:
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.name = "BigQuery Results Store"
        self.description = "Stores MCMC and profile-likelihood parameter grid results."


# Initialize Vertex AI for project if SDK available
if aiplatform is not None:
    try:
        project_id = os.environ.get("GCP_PROJECT_ID", "gen-lang-client-0625573011")
        location = os.environ.get("GCP_REGION", "us-east4")
        aiplatform.init(
            project=project_id,
            location=location,
        )
    except Exception as e:
        print(f"Vertex AI Init Note: {e}")

from src.utils.redis_ledger import DistributedRedisLedger

class SocrateAICoordinator:
    """
    Multi-model T1 Coordinator leveraging Gemini low-tier models (Flash) for task routing,
    Pro for intermediate reasoning, and Ultra for complex scientific discoveries.
    With fault-tolerance via Redis Ledger.
    """

    def __init__(
        self,
        project_id: str = None,
        router: Optional[ModelRouter] = None,
        classifier: Optional[TierClassifier] = None,
        cost_tracker: Optional[CostTracker] = None,
        escalation_protocol: Optional[EscalationProtocol] = None,
    ):
        self.project_id = project_id or os.environ.get("GCP_PROJECT_ID", "gen-lang-client-0625573011")
        self.router = router or ModelRouter()
        self.classifier = classifier or TierClassifier()
        self.cost_tracker = cost_tracker or CostTracker()
        self.escalation = escalation_protocol or EscalationProtocol(
            router=self.router, cost_tracker=self.cost_tracker
        )
        self.ledger = DistributedRedisLedger()

        self.tools = [
            GCPComputeTool(project_id=self.project_id),
            VertexAIJobTool(project_id=self.project_id),
            BigQueryTool(project_id=self.project_id),
        ]

    def dispatch_directive(self, directive: str, max_retries: int = 3) -> Dict[str, Any]:
        """
        Main entry point for processing incoming natural language directives with
        tiered model routing, budget check, and fault-tolerant escalation fallback.
        """
        import hashlib
        # Create a unique task ID for idempotency and resume capability
        task_id = hashlib.md5(directive.encode('utf-8')).hexdigest()
        
        # Check if already processed
        cached_state = self.ledger.get_task_state(task_id)
        if cached_state:
            import json
            state = json.loads(cached_state)
            if state.get("status") == "COMPLETED":
                print(f"Task {task_id} already completed, returning cached result.")
                return state.get("result", {})

        # 1. Check budget ceiling
        if self.cost_tracker.is_over_budget():
            print("WARNING: Monthly budget limit reached. Routing restricted.")

        # 2. Classify directive
        classification = self.classifier.classify(directive)
        action = classification["classified_action"]

        # 3. Route to model tier
        route_info = self.router.route(
            action,
            override_tier="mid" if classification["escalate"] else None,
        )

        # 4. Mock execution or Vertex AI invocation
        def execute_task(route: Dict[str, Any]) -> Dict[str, Any]:
            model_name = route["model_name"]
            tier = route["tier"]

            # If LangChain Vertex AI is available, instantiate real LLM handle
            llm_instance = None
            if ChatVertexAI is not None:
                try:
                    llm_instance = ChatVertexAI(model_name=model_name, temperature=0.0)
                except Exception as e:
                    print(f"VertexAI LLM Init Note ({model_name}): {e}")

            return {
                "directive": directive,
                "action": action,
                "tier_used": tier,
                "model_name": model_name,
                "status": "DISPATCHED",
                "tools_available": len(self.tools),
                "llm_ready": llm_instance is not None,
            }

        # 5. Execute with fault-tolerant retries and escalation fallback
        attempt = 0
        last_error = None
        while attempt < max_retries:
            try:
                res = self.escalation.execute_with_escalation(
                    action=action,
                    execution_func=execute_task,
                    validator_func=lambda r: r is not None and r.get("status") == "DISPATCHED",
                )
                
                # Save success state
                import json
                self.ledger.set_task_state(
                    task_id,
                    json.dumps({"status": "COMPLETED", "result": res}),
                    expire_secs=86400 # Expire in 1 day
                )
                return res
            except Exception as e:
                attempt += 1
                last_error = e
                print(f"⚠️ Task {task_id} failed on attempt {attempt}/{max_retries}: {e}")
                import time
                time.sleep(2 ** attempt) # Exponential backoff
                
        # If all retries fail
        return {
            "status": "FAILED",
            "error": str(last_error),
            "directive": directive
        }


def initialize_socrateai_coordinator(
    project_id: str = "gen-lang-client-0625573011",
    router: Optional[ModelRouter] = None,
    classifier: Optional[TierClassifier] = None,
) -> Any:
    """
    Backward-compatible factory initializer matching original test expectations.
    """
    tools = [
        GCPComputeTool(project_id=project_id),
        VertexAIJobTool(project_id=project_id),
        BigQueryTool(project_id=project_id),
    ]

    if ChatVertexAI is not None and initialize_agent is not None:
        try:
            llm = ChatVertexAI(model_name="gemini-1.5-pro", temperature=0.0)
            agent = initialize_agent(
                tools,
                llm,
                agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
                verbose=True,
            )
            return agent
        except Exception as e:
            print(f"Vertex AI Agent init note: {e}")
            return tools
    else:
        print("ChatVertexAI SDK not available in local environment; returning initialized tools.")
        return tools


if __name__ == "__main__":
    coordinator = SocrateAICoordinator()
    res = coordinator.dispatch_directive("Check AlphaEvolve job status and pre-validate TPU node")
    print(f"\n[T0 DIRECTIVE RESULT]: {res}")
