import streamlit as st
import json
import pandas as pd

# -------------------------------
# Sample JSON dataset (dummy sales)
# -------------------------------
sample_data = {
    "orders": [
        {"order_id": 1, "customer": "Alice", "region": "North", "month": "Jan", "sales": 120, "shipping": "Air"},
        {"order_id": 2, "customer": "Bob", "region": "South", "month": "Jan", "sales": 90, "shipping": "Sea"},
        {"order_id": 3, "customer": "Charlie", "region": "East", "month": "Feb", "sales": 150, "shipping": "Air"},
        {"order_id": 4, "customer": "David", "region": "West", "month": "Feb", "sales": 110, "shipping": "Road"},
        {"order_id": 5, "customer": "Eve", "region": "North", "month": "Mar", "sales": 200, "shipping": "Air"},
        {"order_id": 6, "customer": "Frank", "region": "South", "month": "Mar", "sales": 95, "shipping": "Sea"},
    ]
}

# -------------------------------
# Prompt Builder with Few-shot Examples
# -------------------------------
def build_prompt(user_question: str, json_data: str) -> str:
    return f"""
    You are a data visualization assistant.
    Task:
    - Return only valid JSON.
    - If chart possible: return {{
        "explanation": "...",
        "spec": {{ Vega-Lite spec }}
      }}
    - If not: {{
        "explanation": "...",
        "table": [...]
      }}

    ### Dataset
    {json_data}

    ### Example 1 (Bar Chart)
    User: Show me total sales by region.
    Assistant:
    {{
      "explanation": "This bar chart shows total sales grouped by region.",
      "spec": {{
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "mark": "bar",
        "encoding": {{
          "x": {{"field": "region", "type": "ordinal"}},
          "y": {{"aggregate": "sum", "field": "sales", "type": "quantitative"}}
        }},
        "data": {{"values": {json_data["orders"]} }}
      }}
    }}

    ### Example 2 (Line Chart)
    User: Show me sales trend by month.
    Assistant:
    {{
      "explanation": "This line chart shows monthly sales trend.",
      "spec": {{
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "mark": "line",
        "encoding": {{
          "x": {{"field": "month", "type": "ordinal"}},
          "y": {{"aggregate": "sum", "field": "sales", "type": "quantitative"}}
        }},
        "data": {{"values": {json_data["orders"]} }}
      }}
    }}

    ### Example 3 (Table Fallback)
    User: Show me all customer names and regions.
    Assistant:
    {{
      "explanation": "A chart is not appropriate. Showing tabular data instead.",
      "table": [
        {{"customer": "Alice", "region": "North"}},
        {{"customer": "Bob", "region": "South"}}
      ]
    }}

    ### Now answer this:
    User: {user_question}
    Assistant:
    """

# -------------------------------
# Mock LLM (replace with OpenAI call in real app)
# -------------------------------
def call_llm(prompt: str) -> str:
    # 🚨 Replace this with real OpenAI call (stubbing for demo)
    # Example: openai.ChatCompletion.create(...)
    return json.dumps({
        "explanation": "This bar chart shows sales by shipping method.",
        "spec": {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "mark": "bar",
            "encoding": {
                "x": {"field": "shipping", "type": "ordinal"},
                "y": {"aggregate": "sum", "field": "sales", "type": "quantitative"}
            },
            "data": {"values": sample_data["orders"]}
        }
    })

# -------------------------------
# Streamlit App UI
# -------------------------------
st.set_page_config(page_title="GenBI Assistant", layout="wide")

st.title("📊 Gen Business Intelligence Assistant")

# Sidebar extras
st.sidebar.header("Features")
st.sidebar.write("- Conversational chatbot")
st.sidebar.write("- Vega-Lite charts")
st.sidebar.write("- Table fallback")
st.sidebar.write("- Last 3 questions memory")

# Session state for chat history
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Chat input sticky at bottom
user_question = st.chat_input("Ask me about the sales data...")

if user_question:
    # Build prompt
    prompt = build_prompt(user_question, json.dumps(sample_data))
    # Call LLM
    llm_response = call_llm(prompt)
    
    try:
        response = json.loads(llm_response)
    except:
        response = {"explanation": "Error parsing response.", "table": []}

    # Save conversation
    st.session_state.chat_history.append((user_question, response))

# Display chat history (last 3 Q&A)
for q, r in st.session_state.chat_history[-3:]:
    st.markdown(f"**You:** {q}")
    st.markdown(f"**Assistant:** {r['explanation']}")
    if "spec" in r:
        st.vega_lite_chart(pd.DataFrame(sample_data["orders"]), r["spec"])
    elif "table" in r:
        st.dataframe(pd.DataFrame(r["table"]))
