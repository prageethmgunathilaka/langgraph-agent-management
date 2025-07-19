"""
LLM Service Layer for Hybrid Intelligence Architecture
Provides unified interface for different LLM providers with planning and dynamic inference capabilities
"""

import json
import logging
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from enum import Enum
import asyncio
from datetime import datetime

# LLM Provider imports
try:
    import openai

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import anthropic

    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    import google.generativeai as genai

    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

# Caching
try:
    import diskcache as dc

    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False

logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"


class InferenceType(Enum):
    PLANNING = "planning"
    DYNAMIC = "dynamic"
    ERROR_RECOVERY = "error_recovery"
    DECISION_MAKING = "decision_making"


@dataclass
class LLMConfig:
    provider: LLMProvider
    model: str
    api_key: str
    temperature: float = 0.7
    max_tokens: int = 4000
    enable_caching: bool = True
    cache_ttl: int = 3600  # 1 hour


@dataclass
class LLMRequest:
    prompt: str
    inference_type: InferenceType
    context: Optional[Dict[str, Any]] = None
    system_prompt: Optional[str] = None
    response_format: Optional[str] = "json"  # json, text, structured


@dataclass
class LLMResponse:
    content: str
    provider: LLMProvider
    model: str
    tokens_used: int
    cost_estimate: float
    inference_type: InferenceType
    timestamp: datetime
    cached: bool = False


class LLMService:
    """Unified LLM service supporting multiple providers with caching and cost tracking"""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.provider = config.provider
        self.client = self._initialize_client()
        self.cache = self._initialize_cache() if config.enable_caching else None
        self.cost_tracker = CostTracker()

    def _initialize_client(self):
        """Initialize the appropriate LLM client"""
        if self.provider == LLMProvider.OPENAI:
            if not OPENAI_AVAILABLE:
                raise ImportError("OpenAI package not installed")
            return openai.OpenAI(api_key=self.config.api_key)

        elif self.provider == LLMProvider.ANTHROPIC:
            if not ANTHROPIC_AVAILABLE:
                raise ImportError("Anthropic package not installed")
            return anthropic.Anthropic(api_key=self.config.api_key)

        elif self.provider == LLMProvider.GOOGLE:
            if not GOOGLE_AVAILABLE:
                raise ImportError("Google GenerativeAI package not installed")
            genai.configure(api_key=self.config.api_key)
            return genai.GenerativeModel(self.config.model)

        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def _initialize_cache(self):
        """Initialize disk cache for LLM responses"""
        if not CACHE_AVAILABLE:
            logger.warning("Diskcache not available, caching disabled")
            return None
        return dc.Cache(".llm_cache", size_limit=1e9)  # 1GB cache

    async def generate_planning_workflow(self, request: str, context: Dict[str, Any] = None) -> LLMResponse:
        """Generate structured workflow plan from complex request"""
        system_prompt = """You are a workflow planning expert. Convert complex requests into structured, executable workflow plans.

Return a JSON response with this structure:
{
  "workflow_id": "unique_workflow_id",
  "title": "Workflow Title",
  "description": "Brief description",
  "steps": [
    {
      "step_id": "step_1",
      "title": "Step Title",
      "description": "What this step does",
      "agent_type": "api_agent|data_agent|file_agent|notification_agent",
      "action": "specific_action_to_perform",
      "inputs": {"key": "value"},
      "outputs": ["expected_output_1", "expected_output_2"],
      "dependencies": ["step_id_1", "step_id_2"],
      "error_handling": "how_to_handle_errors",
      "timeout": 300
    }
  ],
  "success_criteria": "How to determine success",
  "failure_handling": "What to do if workflow fails"
}"""

        llm_request = LLMRequest(
            prompt=request,
            inference_type=InferenceType.PLANNING,
            context=context,
            system_prompt=system_prompt,
            response_format="json",
        )

        return await self._execute_request(llm_request)

    async def dynamic_inference(self, situation: str, context: Dict[str, Any], inference_type: InferenceType) -> LLMResponse:
        """Handle dynamic inference during execution"""

        system_prompts = {
            InferenceType.ERROR_RECOVERY: """You are an error recovery expert. Analyze the error situation and provide recovery strategies.
            
Return JSON with:
{
  "error_analysis": "What went wrong",
  "recovery_strategies": [
    {
      "strategy": "retry_with_backoff",
      "description": "Retry with exponential backoff",
      "parameters": {"max_retries": 3, "backoff_factor": 2}
    }
  ],
  "recommended_action": "immediate_action_to_take"
}""",
            InferenceType.DECISION_MAKING: """You are a decision-making expert. Analyze the situation and provide the best course of action.
            
Return JSON with:
{
  "situation_analysis": "Analysis of current situation",
  "options": [
    {
      "option": "option_name",
      "description": "What this option does",
      "pros": ["advantage_1", "advantage_2"],
      "cons": ["disadvantage_1", "disadvantage_2"],
      "confidence": 0.85
    }
  ],
  "recommendation": "recommended_option",
  "reasoning": "Why this is the best choice"
}""",
            InferenceType.DYNAMIC: """You are a dynamic adaptation expert. Analyze the situation and provide adaptive responses.
            
Return JSON with:
{
  "adaptation_needed": true,
  "changes_required": [
    {
      "type": "modify_step",
      "step_id": "step_1",
      "modifications": {"timeout": 600, "retry_count": 5}
    }
  ],
  "reasoning": "Why these changes are needed"
}""",
        }

        llm_request = LLMRequest(
            prompt=situation,
            inference_type=inference_type,
            context=context,
            system_prompt=system_prompts[inference_type],
            response_format="json",
        )

        return await self._execute_request(llm_request)

    async def _execute_request(self, request: LLMRequest) -> LLMResponse:
        """Execute LLM request with caching and error handling"""

        # Log the request details
        logger.debug(f"🚀 LLM REQUEST - Provider: {self.provider.value}, Model: {self.config.model}")
        logger.debug(f"📝 PROMPT: {request.prompt[:200]}{'...' if len(request.prompt) > 200 else ''}")
        if request.system_prompt:
            logger.debug(f"🎯 SYSTEM: {request.system_prompt[:100]}{'...' if len(request.system_prompt) > 100 else ''}")
        if request.context:
            logger.debug(f"📋 CONTEXT: {str(request.context)[:200]}{'...' if len(str(request.context)) > 200 else ''}")

        # Check cache first
        if self.cache:
            cache_key = self._generate_cache_key(request)
            cached_response = self.cache.get(cache_key)
            if cached_response:
                logger.info(f"💾 Cache hit for {request.inference_type}")
                cached_response.cached = True
                return cached_response

        # Execute request based on provider
        try:
            logger.debug(f"🌐 Sending request to {self.provider.value}...")
            if self.provider == LLMProvider.OPENAI:
                response = await self._execute_openai_request(request)
            elif self.provider == LLMProvider.ANTHROPIC:
                response = await self._execute_anthropic_request(request)
            elif self.provider == LLMProvider.GOOGLE:
                response = await self._execute_google_request(request)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")

            # Log the response
            logger.debug(f"✅ LLM RESPONSE: {response.content[:300]}{'...' if len(response.content) > 300 else ''}")
            logger.debug(
                f"📊 TOKENS: Input={response.input_tokens}, Output={response.output_tokens}, Cost=${response.cost:.4f}"
            )

            # Cache the response
            if self.cache:
                self.cache.set(cache_key, response, expire=self.config.cache_ttl)
                logger.debug(f"💾 Response cached with key: {cache_key[:50]}...")

            # Track costs
            self.cost_tracker.add_usage(response)
            logger.info(f"💰 Total session cost: ${self.cost_tracker.total_cost:.4f}")

            return response

        except Exception as e:
            logger.error(f"❌ LLM request failed: {str(e)}")
            raise

    async def _execute_openai_request(self, request: LLMRequest) -> LLMResponse:
        """Execute OpenAI request"""
        messages = []

        # o1 models don't support system messages, so we merge system prompt with user prompt
        if self.config.model.startswith("o1"):
            user_content = ""
            if request.system_prompt:
                user_content += f"Instructions: {request.system_prompt}\n\n"
            if request.context:
                user_content += f"Context: {json.dumps(request.context, indent=2)}\n\n"
            user_content += request.prompt
            messages.append({"role": "user", "content": user_content})
        else:
            # Standard models support system messages
            if request.system_prompt:
                messages.append({"role": "system", "content": request.system_prompt})

            if request.context:
                context_str = f"Context: {json.dumps(request.context, indent=2)}\n\n"
                messages.append({"role": "user", "content": context_str + request.prompt})
            else:
                messages.append({"role": "user", "content": request.prompt})

        # o1 models use different parameter names and don't support temperature
        if self.config.model.startswith("o1"):
            response = self.client.chat.completions.create(
                model=self.config.model, messages=messages, max_completion_tokens=self.config.max_tokens
            )
        else:
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )

        return LLMResponse(
            content=response.choices[0].message.content,
            provider=self.provider,
            model=self.config.model,
            tokens_used=response.usage.total_tokens,
            cost_estimate=self._calculate_cost(response.usage.total_tokens),
            inference_type=request.inference_type,
            timestamp=datetime.now(),
        )

    async def _execute_anthropic_request(self, request: LLMRequest) -> LLMResponse:
        """Execute Anthropic request"""
        prompt = request.prompt
        if request.context:
            prompt = f"Context: {json.dumps(request.context, indent=2)}\n\n{prompt}"

        response = await self.client.messages.create(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            system=request.system_prompt or "",
            messages=[{"role": "user", "content": prompt}],
        )

        return LLMResponse(
            content=response.content[0].text,
            provider=self.provider,
            model=self.config.model,
            tokens_used=response.usage.input_tokens + response.usage.output_tokens,
            cost_estimate=self._calculate_cost(response.usage.input_tokens + response.usage.output_tokens),
            inference_type=request.inference_type,
            timestamp=datetime.now(),
        )

    async def _execute_google_request(self, request: LLMRequest) -> LLMResponse:
        """Execute Google request"""
        prompt = request.prompt
        if request.context:
            prompt = f"Context: {json.dumps(request.context, indent=2)}\n\n{prompt}"

        if request.system_prompt:
            prompt = f"{request.system_prompt}\n\n{prompt}"

        response = await self.client.generate_content_async(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=self.config.temperature,
                max_output_tokens=self.config.max_tokens,
            ),
        )

        # Google doesn't provide token usage in the same way
        estimated_tokens = len(prompt.split()) + len(response.text.split())

        return LLMResponse(
            content=response.text,
            provider=self.provider,
            model=self.config.model,
            tokens_used=estimated_tokens,
            cost_estimate=self._calculate_cost(estimated_tokens),
            inference_type=request.inference_type,
            timestamp=datetime.now(),
        )

    def _generate_cache_key(self, request: LLMRequest) -> str:
        """Generate cache key for request"""
        key_data = {
            "provider": self.provider.value,
            "model": self.config.model,
            "prompt": request.prompt,
            "system_prompt": request.system_prompt,
            "context": request.context,
            "temperature": self.config.temperature,
        }
        return f"llm_cache:{hash(json.dumps(key_data, sort_keys=True))}"

    def _calculate_cost(self, tokens: int) -> float:
        """Calculate estimated cost based on tokens and provider"""
        # Simplified cost calculation - should be updated with actual pricing
        cost_per_1k_tokens = {
            LLMProvider.OPENAI: 0.002,  # GPT-4 pricing
            LLMProvider.ANTHROPIC: 0.008,  # Claude pricing
            LLMProvider.GOOGLE: 0.001,  # Gemini pricing
        }

        return (tokens / 1000) * cost_per_1k_tokens.get(self.provider, 0.002)

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics"""
        return self.cost_tracker.get_stats()


class CostTracker:
    """Track LLM usage and costs"""

    def __init__(self):
        self.usage_log = []
        self.total_cost = 0.0
        self.total_tokens = 0

    def add_usage(self, response: LLMResponse):
        """Add usage record"""
        self.usage_log.append(
            {
                "timestamp": response.timestamp,
                "provider": response.provider.value,
                "model": response.model,
                "tokens": response.tokens_used,
                "cost": response.cost_estimate,
                "inference_type": response.inference_type.value,
                "cached": response.cached,
            }
        )

        if not response.cached:
            self.total_cost += response.cost_estimate
            self.total_tokens += response.tokens_used

    def get_stats(self) -> Dict[str, Any]:
        """Get usage statistics"""
        return {
            "total_requests": len(self.usage_log),
            "total_cost": self.total_cost,
            "total_tokens": self.total_tokens,
            "cache_hit_rate": len([r for r in self.usage_log if r["cached"]]) / len(self.usage_log) if self.usage_log else 0,
            "requests_by_type": self._group_by_inference_type(),
            "cost_by_provider": self._group_by_provider(),
        }

    def _group_by_inference_type(self) -> Dict[str, int]:
        """Group usage by inference type"""
        groups = {}
        for record in self.usage_log:
            inference_type = record["inference_type"]
            groups[inference_type] = groups.get(inference_type, 0) + 1
        return groups

    def _group_by_provider(self) -> Dict[str, float]:
        """Group cost by provider"""
        groups = {}
        for record in self.usage_log:
            if not record["cached"]:
                provider = record["provider"]
                groups[provider] = groups.get(provider, 0.0) + record["cost"]
        return groups


class LLMServiceFactory:
    """Factory for creating LLM services"""

    @staticmethod
    def create_service(provider: str, model: str, api_key: str, **kwargs) -> LLMService:
        """Create LLM service instance"""
        config = LLMConfig(provider=LLMProvider(provider), model=model, api_key=api_key, **kwargs)
        return LLMService(config)

    @staticmethod
    def create_from_env() -> LLMService:
        """Create LLM service from environment variables"""
        import os

        # Try OpenAI first
        if os.getenv("OPENAI_API_KEY"):
            return LLMServiceFactory.create_service(
                provider="openai", model=os.getenv("OPENAI_MODEL", "gpt-4"), api_key=os.getenv("OPENAI_API_KEY")
            )

        # Try Anthropic
        elif os.getenv("ANTHROPIC_API_KEY"):
            return LLMServiceFactory.create_service(
                provider="anthropic",
                model=os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229"),
                api_key=os.getenv("ANTHROPIC_API_KEY"),
            )

        # Try Google
        elif os.getenv("GOOGLE_API_KEY"):
            return LLMServiceFactory.create_service(
                provider="google", model=os.getenv("GOOGLE_MODEL", "gemini-pro"), api_key=os.getenv("GOOGLE_API_KEY")
            )

        else:
            raise ValueError("No LLM API key found in environment variables")
