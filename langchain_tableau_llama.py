# customlocalmodel.py

import os
import requests
from typing import List, Optional, Any, Dict

from langchain_core.messages import BaseMessage
from langchain.chat_models.base import BaseChatModel
from langchain.schema import AIMessage
from langchain.schema import ChatResult, ChatGeneration

class CustomLlamaEndpointChat(BaseChatModel):
    """Custom chat model using a LLaMA endpoint with custom headers"""

    def __init__(
        self,
        endpoint_url: str,
        api_key: str,
        auth_group: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: float = 0.7,
    ):
        self.endpoint_url = endpoint_url
        self.api_key = api_key
        self.auth_group = auth_group
        self.model_name = model_name
        self.temperature = temperature

    @property
    def _llm_type(self) -> str:
        return "custom_llama"

    @property
    def _identifying_params(self) -> Dict[str, Any]:
        return {
            "endpoint_url": self.endpoint_url,
            "model_name": self.model_name,
            "temperature": self.temperature,
            "auth_group": self.auth_group,
        }

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any
    ) -> ChatResult:
        """
        Sends request to LLaMA endpoint. Builds payload from messages.
        Returns a ChatResult as required by BaseChatModel.
        """

        # Build payload
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": m.role, "content": m.content} for m in messages
            ],
            "temperature": self.temperature,
        }
        if stop:
            payload["stop"] = stop
        payload.update(kwargs)

        headers = {
            "Content-Type": "application/json",
            "X-API-KEY": self.api_key,
        }
        if self.auth_group:
            headers["X-AUTH-GROUP"] = self.auth_group

        resp = requests.post(self.endpoint_url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        j = resp.json()

        # Extract content -- customize depending on what your LLaMA API returns
        # Example assumption: {"choices": [{"message": {"content": ...}}]}
        try:
            content = j["choices"][0]["message"]["content"]
        except Exception:
            # fallback options
            content = j.get("response") or j.get("output") or str(j)

        ai_msg = AIMessage(content=content)

        gen = ChatGeneration(message=ai_msg)
        return ChatResult(generations=[gen], llm_output=j)


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
