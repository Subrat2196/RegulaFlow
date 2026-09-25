from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass

from pydantic import BaseModel

"""
dataclass vs Pydantic BaseModel for internal model responses.
The difference between them in 5 points is :
1. Dataclasses are simpler and lighter for pure Python objects.
2. Pydantic BaseModel provides data validation and parsing.
3. Dataclasses do not require JSON serialization.
4. BaseModel is better for API boundaries and external data exchange.
5. Dataclasses are ideal for internal model responses where performance and simplicity matter.
"""
@dataclass
class ModelResponse: 
    """
    Standardized return value from every model provider.

    Every provider — OpenAI, Anthropic, Mock — returns this same shape.
    The rest of the codebase only ever sees ModelResponse, never provider-
    specific objects like openai.ChatCompletion or anthropic.Message.

    Using a dataclass (not Pydantic BaseModel) because this is an internal
    value object — it never crosses an API boundary and never needs
    JSON serialization. Dataclasses are simpler for pure Python objects.
    """

    content: str          # the text or JSON string the model produced
    model: str            # which model was used, e.g. "gpt-4o" or "mock"
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0

"""
This concept of Abstract class is that it is a blueprint for other classes. 
It cannot be instantiated directly. Subclasses must implement all abstract methods.
Here we inherited ABC to create an abstract base class for all model providers. 
We use this pattern to enforce a consistent interface across all model providers.

If we dont use an abstract base class, each model provider could have a different interface, 
making it harder to switch providers or maintain a consistent codebase.

I am not able to undersdtand why OpenAI SDK calls are scattered across the codebase 
without an abstract base class.

The OpenAI SDK calls are scattered because there is no single, consistent interface 
that all parts of the codebase could rely on.
"""
class ModelProvider(ABC):
    """
    Abstract interface that every LLM provider must implement.

    ABC = Abstract Base Class. A class that cannot be instantiated directly.
    It defines a contract — a set of methods every subclass must provide.
    If a subclass fails to implement any @abstractmethod, Python raises
    TypeError when you try to instantiate it.

    Why this matters:
        Without this, OpenAI SDK calls would be scattered across agents,
        services, and route handlers. Switching from OpenAI to Anthropic
        would mean hunting down and changing dozens of files.
        With this, you change one file (openai_provider.py → anthropic_provider.py)
        and nothing else in the codebase needs to know.

    The three methods cover the three ways agents use LLMs:
        generate          → free-text response (summaries, analysis)
        structured_generate → JSON response conforming to a Pydantic schema (agent outputs)
        stream            → token-by-token response (live UI updates)
    """

    # here async because generate and structured_generate are asynchronous methods.
    # by asynchronous we mean that these methods return coroutines and must be awaited.
    # a coroutine is a special function that can pause and resume its execution, 
    # allowing asynchronous operations and await is used to pause until the coroutine completes.
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> ModelResponse:
        """
        Generate a free-text response.

        temperature=0.0 is the default because compliance analysis must be
        deterministic and consistent. Higher temperatures introduce randomness
        — useful for creative tasks, dangerous for regulatory interpretation.
        """

    @abstractmethod
    async def structured_generate(
        self,
        prompt: str,
        response_schema: type[BaseModel],
        *,
        system_prompt: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> ModelResponse:
        """
        Generate a response that conforms to a Pydantic schema.

        The returned ModelResponse.content is a JSON string. The caller
        parses it using response_schema.model_validate_json(response.content).

        Keeping parsing in the caller (not here) means validation failures
        are visible and handleable at the agent level — exactly where the
        retry logic lives.
        """

    # Streaming is synchronous in the sense that the method itself is not async,
    # but it returns an AsyncIterator which must be iterated asynchronously.
    @abstractmethod
    def stream(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> AsyncIterator[str]:
        """
        Stream the response token by token.

        Returns an AsyncIterator — the caller uses `async for token in provider.stream(...)`.
        Used in Session 49 for the Gradio demo UI to show the model "thinking" live.
        """
