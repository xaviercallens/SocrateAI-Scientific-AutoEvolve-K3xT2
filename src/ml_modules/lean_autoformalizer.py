"""
Lean 4 Autoformalization Agent
==============================
Implements Process-Driven Autoformalization (PDA) using a
Mistral LLM endpoint to dynamically write and verify mathlib4 proofs.
Utilizes Human-AI collaborative patterns from YuanheZ/lean-stat-learning-theory.
"""

import json
import logging
import requests
import os
from typing import Dict, Any, List

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

from integration.lean_client import LeanInteractiveREPL

logger = logging.getLogger(__name__)

class CostMonitor:
    """Tracks token usage and estimates API costs for the LLM Autoformalizer."""
    def __init__(self):
        self.input_tokens = 0
        self.output_tokens = 0
        # Gemini 1.5 Pro estimated standard pricing (USD per 1M tokens)
        self.cost_per_1m_input = 3.50
        self.cost_per_1m_output = 10.50

    def add_usage(self, input_toks: int, output_toks: int):
        self.input_tokens += input_toks
        self.output_tokens += output_toks
        
    def estimate_cost(self) -> float:
        in_cost = (self.input_tokens / 1_000_000.0) * self.cost_per_1m_input
        out_cost = (self.output_tokens / 1_000_000.0) * self.cost_per_1m_output
        return in_cost + out_cost
        
    def get_summary(self) -> dict:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "estimated_cost_usd": round(self.estimate_cost(), 6)
        }

global_cost_monitor = CostMonitor()

class AgoraRAGRetriever:
    """
    Retrieval-Augmented Generation (RAG) module to fetch
    existing K3 and F-Theory lemmas from SocrateAI-Scientific-Agora.
    """
    def __init__(self):
        # Mock database connection to the local FAISS index of mathlib4
        self.knowledge_base = ["lemma k3_picard_bound (P : ℕ) : P ≤ 20", 
                               "theorem swampland_distance (tau : ℝ) : tau > 0"]

    def retrieve_premises(self, query: str, top_k: int = 3) -> List[str]:
        logger.info(f"Retrieving top {top_k} premises for query: {query}")
        return self.knowledge_base[:top_k]


class MistralLeanAgent:
    """
    The main agent that formulates and repairs Lean 4 tactics using Mistral AI.
    Used when LLM_PROVIDER=mistral.
    """
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("MISTRAL_API_KEY", "mock-mistral-key")
        self.model = "mistral-large-latest"
        self.endpoint = "https://api.mistral.ai/v1/chat/completions"

    def draft_proof(self, theorem_statement: str, premises: List[str]) -> str:
        """Drafts the initial Chain-of-Thought proof."""
        prompt = f"Using premises: {premises}, prove: {theorem_statement}\nOutput ONLY valid Lean 4 tactics line-by-line."
        logger.info(f"Mistral drafting proof for: {theorem_statement}")
        # Mock LLM Call
        return "intro h\napply swampland_distance\nexact h\n"

    def repair_proof(self, tactic: str, error_msg: str, proof_state: str) -> str:
        """Acts as the Critic Agent, repairing failed tactics."""
        logger.info(f"Mistral repairing tactic '{tactic}' due to error.")
        # Mock LLM Call
        return "simp [h]"


class GeminiLeanAgent:
    """
    The main agent that formulates and repairs Lean 4 tactics using Google Gemini.
    Optimized for cost efficiency using the user's existing GCP/Gemini subscription.
    """
    def __init__(self, model_name: str = "gemini-1.5-pro-latest"):
        self.model_name = model_name
        if GEMINI_AVAILABLE:
            # Assumes GOOGLE_API_KEY is natively provided by the environment
            genai.configure()
            self.model = genai.GenerativeModel(model_name)
        else:
            self.model = None

    def draft_proof(self, theorem_statement: str, premises: List[str]) -> str:
        """Drafts the initial Chain-of-Thought proof."""
        prompt = f"Using premises: {premises}, prove the following Lean 4 theorem: {theorem_statement}\nOutput ONLY valid Lean 4 tactics line-by-line."
        logger.info(f"Gemini ({self.model_name}) drafting proof for: {theorem_statement}")
        
        if self.model:
            try:
                response = self.model.generate_content(prompt)
                
                if hasattr(response, 'usage_metadata'):
                    in_toks = getattr(response.usage_metadata, 'prompt_token_count', 0)
                    out_toks = getattr(response.usage_metadata, 'candidates_token_count', 0)
                    global_cost_monitor.add_usage(in_toks, out_toks)

                return response.text
            except Exception as e:
                logger.error(f"Gemini API error: {e}")

        # Fallback Mock
        return "intro h\napply swampland_distance\nexact h\n"

    def repair_proof(self, tactic: str, error_msg: str, proof_state: str) -> str:
        """Acts as the Critic Agent, repairing failed tactics."""
        prompt = f"The tactic '{tactic}' failed with error: {error_msg}.\nCurrent state: {proof_state}.\nProvide the corrected Lean 4 tactic."
        logger.info(f"Gemini repairing tactic '{tactic}' due to error.")
        
        if self.model:
            try:
                response = self.model.generate_content(prompt)
                
                if hasattr(response, 'usage_metadata'):
                    in_toks = getattr(response.usage_metadata, 'prompt_token_count', 0)
                    out_toks = getattr(response.usage_metadata, 'candidates_token_count', 0)
                    global_cost_monitor.add_usage(in_toks, out_toks)
                    
                return response.text
            except Exception as e:
                logger.error(f"Gemini API error: {e}")

        # Fallback Mock
        return "simp [h]"


def get_llm_agent():
    """Factory to select the LLM provider based on environment config."""
    provider = os.environ.get("LLM_PROVIDER", "gemini").lower()
    if provider == "mistral":
        return MistralLeanAgent()
    return GeminiLeanAgent()


class IncrementalLeanAgent:
    """
    Stateful Agent for Process-Driven Autoformalization (PDA).
    Maintains the proof history and queries the LLM incrementally based on the live Lean 4 proof state.
    """
    def __init__(self, model_name: str = "gemini-1.5-pro-latest"):
        self.model_name = model_name
        self.history = []
        if GEMINI_AVAILABLE:
            genai.configure()
            self.model = genai.GenerativeModel(model_name)
        else:
            self.model = None

    def get_next_tactic(self, theorem_statement: str, premises: List[str], current_state: str, last_error: str = None) -> str:
        """Prompts the LLM for the next tactic given the full history and current state."""
        prompt = f"Theorem to prove: {theorem_statement}\n"
        if premises:
            prompt += f"Available Premises: {premises}\n"
        
        prompt += "\nProof History:\n"
        for step in self.history:
            prompt += f"Tactic: {step['tactic']}\nState after: {step['state']}\n---\n"
            
        prompt += f"\nCurrent Proof State:\n{current_state}\n"
        if last_error:
            prompt += f"\nERROR on last attempt: {last_error}\nPlease provide a corrected tactic.\n"
            
        prompt += "\nProvide ONLY the next Lean 4 tactic to advance the proof."
        
        logger.info(f"Prompting LLM for next tactic. Current state goals: {current_state.count('⊢')}")
        
        if self.model:
            try:
                # In production, we would use a chat session. For now, generate_content.
                response = self.model.generate_content(prompt)
                
                # Track tokens and costs
                if hasattr(response, 'usage_metadata'):
                    in_toks = getattr(response.usage_metadata, 'prompt_token_count', 0)
                    out_toks = getattr(response.usage_metadata, 'candidates_token_count', 0)
                    global_cost_monitor.add_usage(in_toks, out_toks)
                    logger.info(f"Token Usage -> In: {in_toks}, Out: {out_toks} | Total Session Cost: ${global_cost_monitor.estimate_cost():.6f}")

                return response.text.strip().split('\n')[0]  # Take first line as tactic
            except Exception as e:
                logger.error(f"LLM API error: {e}")
                
        # Mock responses based on state
        if last_error:
            return "simp [h]"
        if len(self.history) == 0:
            return "intro h"
        elif len(self.history) == 1:
            return "apply swampland_distance"
        return "exact h"


def run_pda_autoformalization(theorem_statement: str, max_steps: int = 15) -> Dict[str, Any]:
    """
    Executes the true Process-Driven Autoformalization (PDA) feedback loop.
    The agent dynamically explores the proof tree by reacting to the Lean 4 REPL's live state.
    """
    rag = AgoraRAGRetriever()
    agent = IncrementalLeanAgent()
    repl = LeanInteractiveREPL()
    
    premises = rag.retrieve_premises(theorem_statement)
    repl_env = repl.initialize_env(imports=["Mathlib.Topology.MetricSpace.Basic"])
    
    # In a real REPL, initializing with a theorem returns the initial state with goals.
    # We mock the initial state here.
    current_state = "1 goal\ntau : ℝ\nh : tau = 0.5\n⊢ stable tau"
    last_error = None
    
    logger.info("Starting Process-Driven Autoformalization (PDA) Loop...")
    
    for step_num in range(max_steps):
        # 1. LLM predicts next tactic based on live state
        tactic = agent.get_next_tactic(theorem_statement, premises, current_state, last_error)
        logger.info(f"Step {step_num+1} | LLM proposes tactic: {tactic}")
        
        # 2. Execute against Lean 4 REPL
        result = repl.execute_tactic(tactic)
        
        # 3. Process Feedback Loop
        if result.get("error"):
            logger.warning(f"Tactic failed: {result['error']}")
            last_error = result["error"]
        else:
            logger.info("Tactic succeeded.")
            last_error = None
            current_state = result.get("state", "no goals")
            agent.history.append({"tactic": tactic, "state": current_state})
            
            if "no goals" in current_state.lower():
                logger.info("Proof complete! No goals remaining.")
                repl.close()
                verified_script = "\n".join([step["tactic"] for step in agent.history])
                return {
                    "status": "success", 
                    "verified_proof": verified_script, 
                    "steps": len(agent.history),
                    "cost_metrics": global_cost_monitor.get_summary()
                }
                
    repl.close()
    return {
        "status": "failed", 
        "reason": "Max steps exceeded without completing proof.", 
        "history": agent.history,
        "cost_metrics": global_cost_monitor.get_summary()
    }

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    res = run_pda_autoformalization("theorem k3_vacuum_stable (tau : ℝ) (h : tau = 0.5) : stable tau")
    print("\nFINAL RESULT:")
    print(json.dumps(res, indent=2))
