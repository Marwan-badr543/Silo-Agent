import os

from langchain_openai import ChatOpenAI

# This plugin picks its own model, so it can change without touching the main agent or other plugins.
llm = ChatOpenAI(
    model="openai/gpt-oss-20b",
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.environ["NVIDIA_API_KEY"],
    max_tokens=1024,
)
