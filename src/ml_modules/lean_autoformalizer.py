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


def run_autoformalization(theorem_statement: str, max_retries: int = 5) -> Dict[str, Any]:
    """
    The main execution loop for Process-Driven Autoformalization.
    """
    rag = AgoraRAGRetriever()
    llm = get_llm_agent()
    repl = LeanInteractiveREPL()
    
    # 1. Retrieve Knowledge
    premises = rag.retrieve_premises(theorem_statement)
    
    # 2. Draft Initial Proof
    draft_tactics = llm.draft_proof(theorem_statement, premises).strip().split('\n')
    
    # 3. Interactive Execution Loop
    repl.initialize_env(imports=["Mathlib.Topology.MetricSpace.Basic"])
    
    final_script = []
    
    for tactic in draft_tactics:
        attempts = 0
        success = False
        current_tactic = tactic
        
        while attempts < max_retries and not success:
            result = repl.execute_tactic(current_tactic)
            
            if result.get("error"):
                # 4. Repair loop via Mistral
                current_tactic = llm.repair_proof(current_tactic, result["error"], result["state"])
                attempts += 1
            else:
                success = True
                final_script.append(current_tactic)
                if result.get("state") == "no goals":
                    repl.close()
                    return {"status": "success", "verified_proof": "\n".join(final_script)}
                
        if not success:
            repl.close()
            return {"status": "failed", "reason": "Max retries exceeded on tactic repair."}
            
    repl.close()
    return {"status": "incomplete", "reason": "Proof ended but goals remain open."}

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    res = run_autoformalization("theorem k3_vacuum_stable (tau : ℝ) (h : tau = 0.5) : stable tau")
    print(json.dumps(res, indent=2))
