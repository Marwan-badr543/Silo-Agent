from fastapi import APIRouter, Depends

from agent.silo_agent import SiloAgent
from api.core.objects_factory import ObjectsFactory
from api.routers.chat_schema import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    agent: SiloAgent = Depends(ObjectsFactory.get_agent),
):
    return ChatResponse(answer=await agent.ask(body.question, body.session_id))
