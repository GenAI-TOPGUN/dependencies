from typing import List, Dict
from langchain.schema import HumanMessage, SystemMessage, AIMessage
from langchain.chat_models.base import BaseChatModel
from langchain.core.schema import ChatResult, ChatGeneration
import requests
import os

class CustomLlamaEndpointChat(BaseChatModel):
    """A custom chat model to call a LLaMA API endpoint with custom headers."""

    def __init__(self, endpoint_url: str, api_key: str, auth_group: str = None, model_name: str = None, temperature: float = 0.7):
        self.endpoint_url = endpoint_url
        self.api_key = api_key
        self.auth_group = auth_group
        self.model_name = model_name
        self.temperature = temperature

    @property
    def _llm_type(self) -> str:
        return "custom_llama"

    @property
    def _identifying_params(self) -> Dict[str, any]:
        return {
            "endpoint_url": self.endpoint_url,
            "model_name": self.model_name,
            "temperature": self.temperature,
            "auth_group": self.auth_group
        }

    def _call(self, messages: List[Dict], **kwargs) -> ChatResult:
        """
        messages: list of dicts with 'role' and 'content'
        """

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": self.temperature,
            **kwargs
        }
        headers = {
            "Content-Type": "application/json",
            "X-API-KEY": self.api_key
        }
        if self.auth_group:
            headers["X-AUTH-GROUP"] = self.auth_group

        resp = requests.post(self.endpoint_url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        j = resp.json()
        # You will need to adapt depending on the API's response schema
        # Suppose it returns {"choices": [...]} similar to OpenAI
        content = j["choices"][0]["message"]["content"]
        # wrap
        message = AIMessage(content=content)
        generation = ChatGeneration(message=message)
        return ChatResult(generations=[[generation]], llm_output=j)



#-----
# in models.py

from your_custom_module import CustomLlamaEndpointChat  # from above class

def select_model(provider: str = "openai", model_name: str = None, temperature: float = 0.2):
    provider = provider.lower()
    if provider == "llama_custom":
        return CustomLlamaEndpointChat(
            endpoint_url=os.environ["LLAMA_CUSTOM_ENDPOINT"],
            api_key=os.environ["LLAMA_CUSTOM_KEY"],
            auth_group=os.environ.get("LLAMA_CUSTOM_AUTH_GROUP"),
            model_name=model_name or os.environ.get("LLAMA_CUSTOM_MODEL"),
            temperature=temperature
        )
    # other branches (openai, azure, llama_local, llama_api) ...




#----
