# customlocalmodel.py

# customlocalmodel.py

import requests
from typing import List, Optional, Any, Dict

from langchain_core.messages.human import HumanMessage
from langchain_core.messages.ai import AIMessage
from langchain_core.messages.base import BaseMessage
from langchain.chat_models.base import BaseChatModel
from langchain.schema import ChatResult, ChatGeneration

class CustomLlamaEndpointChat(BaseChatModel):
    """Custom chat model using a LLaMA endpoint with custom headers, with hardcoded settings."""

    # Hardcoded values
    endpoint_url: str = "https://your-llama-endpoint.example.com/v1/chat/completions"
    api_key: str = "YOUR_API_KEY_HERE"
    auth_group: Optional[str] = "YOUR_AUTH_GROUP_IF_ANY"
    model_name: str = "llama-custom-model-name"
    temperature: float = 0.7

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
        Fixed‐parameter version. Build payload from messages (using type to identify role),
        send request with hardcoded endpoint & headers.
        """

        def message_to_role_content(m: BaseMessage) -> Dict[str, str]:
            # LangChain messages have .type instead of .role
            # .type is one of: "human", "ai", "system", etc.
            msg_type = getattr(m, "type", None)
            if msg_type == "human":
                role = "user"
            elif msg_type == "ai":
                role = "assistant"
            else:
                # fallback: m.type or default to "user"
                role = msg_type or "user"
            return {"role": role, "content": m.content}

        payload = {
            "model": self.model_name,
            "messages": [message_to_role_content(m) for m in messages],
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

        # Extract content; adapt if your endpoint schema differs
        try:
            content = j["choices"][0]["message"]["content"]
        except Exception:
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
