from typing import List, Optional, Any, Dict
from langchain_core.schema import BaseMessage, AIMessage, ChatResult, ChatGeneration
from langchain.chat_models.base import BaseChatModel
# Remove _call if you used: you can keep it or use _generate; both need to align.

class CustomLlamaEndpointChat(BaseChatModel):
    # existing __init__, properties etc...

    @property
    def _llm_type(self) -> str:
        return "custom_llama"

    @property
    def _identifying_params(self) -> Dict[str, Any]:
        return {
            "endpoint_url": self.endpoint_url,
            "model_name": self.model_name,
            "temperature": self.temperature,
            "auth_group": self.auth_group
        }

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any
    ) -> ChatResult:
        """
        Required abstract method: generate a response from the given messages.
        We'll call the endpoint with custom headers, get the content, 
        wrap into AIMessage, return ChatResult.
        """
        # Prepare payload
        payload = {
            "model": self.model_name,
            "messages": [ {"role": m.role, "content": m.content} for m in messages ],
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

        import requests
        resp = requests.post(self.endpoint_url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        j = resp.json()

        # Extract content (adapt if your API uses different fields)
        try:
            content = j["choices"][0]["message"]["content"]
        except Exception:
            content = j.get("response") or j.get("output") or str(j)

        ai_msg = AIMessage(content=content)
        generation = ChatGeneration(message=ai_msg)
        return ChatResult(generations=[generation], llm_output=j)



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
