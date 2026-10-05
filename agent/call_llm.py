import os

from langchain_openai import ChatOpenAI

NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"

nemotron_llm = ChatOpenAI(
    base_url=NVIDIA_BASE_URL,
    api_key=os.environ["NVIDIA_API_KEY"],
    model="nvidia/nemotron-3.5-lightning-30b-a3b",
    max_tokens=2000,
)

gpt_oss_llm = ChatOpenAI(
    base_url=NVIDIA_BASE_URL,
    api_key=os.environ["NVIDIA_API_KEY"],
    model="openai/gpt-oss-20b",
    max_tokens=1024,
)
