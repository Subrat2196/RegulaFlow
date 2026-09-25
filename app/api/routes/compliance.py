from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.dependencies import get_model_provider
from app.models.api import APIResponse
from app.providers.base import ModelProvider

router = APIRouter(prefix="/compliance", tags=["compliance"])


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=10, max_length=4000)
    system_prompt: str | None = Field(default=None, max_length=2000)
    temperature: float = Field(default=0.0, ge=0.0, le=1.0)


class GenerateResult(BaseModel):
    content: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: float


@router.post("/generate", response_model=APIResponse[GenerateResult])
async def generate_text(
    request: GenerateRequest,
    provider: ModelProvider = Depends(get_model_provider),
) -> APIResponse[GenerateResult]:
    """
    Send a prompt to the configured model provider and return the response.

    This is the first endpoint that uses the provider abstraction:
    - In development: MockProvider answers without any API key
    - In production: OpenAIProvider calls the real API (Session 10)

    The endpoint code is identical regardless of which provider is active.
    """
    response = await provider.generate(
        request.prompt,
        system_prompt=request.system_prompt,
        temperature=request.temperature,
    )
    return APIResponse(
        data=GenerateResult(
            content=response.content,
            model=response.model,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            latency_ms=response.latency_ms,
        )
    )
