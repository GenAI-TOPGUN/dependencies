"""
GenBI Streamlit Chatbot (Vega-Lite) - single-file app

Features implemented:
1. Conversational chatbot UI in Streamlit that classifies user questions as either
   - field-level (metadata/schema) questions, or
   - data questions (require analyzing the dataset and producing a visualization/table)
2. If question is field-level -> returns metadata answer (local) or enrich via LLM second call.
3. If data question -> sends question + sanitized JSON sample to LLM to request a Vega-Lite spec + explanation.
4. If LLM suggestion is a Vega-Lite spec it is rendered via Streamlit's `st.vega_lite_chart`.
   If Vega-Lite is not appropriate the app falls back to a table view.
5. UI provides local chart-type overrides (no extra LLM call) so users can instantly switch the chart
   type or view a table of the results. Also provides sampling / aggregation controls.
6. A few-shot prompt engineering block is embedded for the LLM classification and the Vega-Lite generator.
7. Conversation history (last 3 Q/A) is shown in the sidebar and stored in session state.
8. Dummy static fields (schema) and complex nested sales JSON (20 records) are included.

Run instructions:
    pip install streamlit pandas altair openai python-dateutil
    export OPENAI_API_KEY=...   # or set on Windows via setx
    streamlit run GenBI_Streamlit_Chatbot_VegaLite.py

Notes:
- This code uses the OpenAI Chat Completions API interface (you can adapt to your LLM provider by modifying `call_llm`).
- The Vega-Lite spec is expected in the assistant response as a JSON block. The code extracts and validates it.

"""

import streamlit as st
import pandas as pd
import altair as alt
import json
import textwrap
import re
import os
from datetime import datetime, timedelta
from dateutil.parser import parse as dateparse

# Optional: import OpenAI. If you don't want to call an LLM, set USE_LLM = False below.
try:
    import openai
except Exception:
    openai = None

# ----------------------------- Configuration -----------------------------
USE_LLM = True  # flip to False to use only local heuristics and sample answers
LLM_MODEL = "gpt-4o"  # change to your preferred model; keep compatible with your provider
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if openai and OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY

# Maximum rows to pass to LLM (we pass a sampled/aggregated JSON to keep payload small)
MAX_ROWS_TO_SEND = 50

# Supported local chart types for UI override (Vega-Lite mark names)
LOCAL_CHART_TYPES = [
    "auto-infer",
    "bar",
    "line",
    "area",
    "point",
    "scatter",
    "heatmap",
    "boxplot",
    "treemap",
    "table"
]

# ----------------------------- Dummy schema & data -----------------------------
# 1) Schema / fields metadata (static)
FIELDS = [
    {"name":"order_id", "type":"string", "description":"Unique order identifier"},
    {"name":"order_date", "type":"temporal", "description":"Order timestamp (ISO)"},
    {"name":"customer.id", "type":"string", "description":"Customer ID"},
    {"name":"customer.name", "type":"string", "description":"Customer full name"},
    {"name":"customer.region", "type":"string", "description":"Customer region or market"},
    {"name":"items[].product_id", "type":"string", "description":"Product SKU"},
    {"name":"items[].category", "type":"string", "description":"Product category"},
    {"name":"items[].quantity", "type":"integer", "description":"Quantity purchased of the product"},
    {"name":"items[].unit_price", "type":"number", "description":"Unit price in USD"},
    {"name":"items[].revenue", "type":"number", "description":"quantity * unit_price (derived)"},
    {"name":"shipping_method", "type":"string", "description":"Shipping method used"},
    {"name":"status", "type":"string", "description":"Order status (delivered, returned, pending)"}
]

# 2) Complex nested sales data (20 records). Each order has nested customer dict and items list.
def generate_sample_sales(n=20, seed=42):
    import random
    random.seed(seed)
    customers = [
        {"id": f"C{100+i}", "name": name, "region": reg}
        for i, (name, reg) in enumerate([
            ("Alice Wong","APAC"),("Bob Smith","EMEA"),("Carla Ruiz","LATAM"),("David Lee","APAC"),("Emma Chen","APAC"),
            ("Frank Jones","NA"),("Gina Rossi","EMEA"),("Hiro Tanaka","APAC"),("Ibrahim Khan","ME"),("Jana Novak","EU"),
            ("Karl O'Neil","NA"),("Liu Wei","APAC"),("Maria Garcia","LATAM"),("Noah Brown","NA"),("Olga Petrova","EE"),
            ("Paul Miller","NA"),("Quinn Park","APAC"),("Ravi Patel","APAC"),("Sara Ahmed","ME"),("Tomoko Sato","APAC")
        ])
    ]

    products = [
        {"product_id": f"P{100+i}", "category": cat, "name": pname, "unit_price": price}
        for i, (pname, cat, price) in enumerate([
            ("Widget A","Gadgets",12.5),("Widget B","Gadgets",15.0),("Gizmo X","Widgets",25.5),("Gizmo Y","Widgets",22.0),
            ("Thing 1","Accessories",5.5),("Thing 2","Accessories",7.0),("Deluxe","Premium",99.0),("Basic","Premium",49.5)
        ])
    ]

    statuses = ["delivered","pending","returned"]
    shipping = ["standard","express","pickup"]

    start_date = datetime.utcnow() - timedelta(days=120)
    data = []
    for i in range(n):
        cust = customers[i % len(customers)]
        order_date = (start_date + timedelta(days=random.randint(0, 120))).isoformat()
        num_items = random.randint(1,3)
        items = []
        for j in range(num_items):
            p = random.choice(products)
            qty = random.randint(1,10)
            items.append({
                "product_id": p["product_id"],
                "product_name": p["name"],
                "category": p["category"],
                "quantity": qty,
                "unit_price": p["unit_price"],
                "revenue": round(qty * p["unit_price"],2)
            })
        order = {
            "order_id": f"O{1000+i}",
            "order_date": order_date,
            "customer": cust,
            "items": items,
            "shipping_method": random.choice(shipping),
            "status": random.choice(statuses)
        }
        data.append(order)
    return data

SAMPLE_DATA = generate_sample_sales(20)

# ----------------------------- Utilities -----------------------------

def extract_json_from_text(text: str):
    # Find first JSON object or array in text; be tolerant to code fences and single quotes
    m = re.search(r"```json(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if not m:
        m = re.search(r"```(.*?)```", text, re.DOTALL)
    if m:
        candidate = m.group(1).strip()
    else:
        m2 = re.search(r"(\{(?:.|\n)*\}|\[(?:.|\n)*\])", text)
        if not m2:
            raise ValueError("No JSON-like block found in text.")
        candidate = m2.group(1)
    # remove trailing commas before } or ]
    candidate = re.sub(r",\s*([\]\}])", r"\1", candidate)
    # try parse
    try:
        return json.loads(candidate)
    except Exception:
        repaired = candidate.replace("'", '"')
        return json.loads(repaired)


def flatten_orders_to_rows(data):
    # Normalize nested orders to row-per-item (useful for many chart types)
    df = pd.json_normalize(data, record_path=['items'], meta=['order_id','order_date','shipping_method','status', ['customer','id'], ['customer','name'], ['customer','region'] )
    # canonical column names
    df = df.rename(columns={
        'customer.id':'customer.id', 'customer.name':'customer.name', 'customer.region':'customer.region'
    })
    # ensure correct dtypes
    try:
        df['order_date'] = pd.to_datetime(df['order_date'])
    except Exception:
        pass
    df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce')
    df['unit_price'] = pd.to_numeric(df['unit_price'], errors='coerce')
    df['revenue'] = pd.to_numeric(df['revenue'], errors='coerce')
    return df


def sample_data_for_llm(df: pd.DataFrame, max_rows=MAX_ROWS_TO_SEND):
    # sample and aggregate to keep payload small while preserving distribution
    if df.shape[0] <= max_rows:
        return df.to_dict(orient='records')
    # stratified sample by category if present
    if 'category' in df.columns:
        sample = df.groupby('category', group_keys=False).apply(lambda x: x.sample(min(len(x), max(1, max_rows // max(1, df['category'].nunique()))))).reset_index(drop=True)
        return sample.to_dict(orient='records')
    else:
        return df.sample(max_rows).to_dict(orient='records')


# Heuristic local chart inference (fallback when LLM disabled or user selects override)

def infer_chart_from_df(df: pd.DataFrame):
    # very simple heuristics: if temporal + numeric -> line; if cat + num -> bar; two numeric -> scatter; else table
    cols = df.columns.tolist()
    datetime_cols = [c for c in cols if pd.api.types.is_datetime64_any_dtype(df[c])]
    numeric_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
    nominal_cols = [c for c in cols if pd.api.types.is_object_dtype(df[c]) or pd.api.types.is_categorical_dtype(df[c])]

    if datetime_cols and numeric_cols:
        return 'line', {'x': datetime_cols[0], 'y': numeric_cols[0]}
    if nominal_cols and numeric_cols:
        return 'bar', {'x': nominal_cols[0], 'y': numeric_cols[0]}
    if len(numeric_cols) >= 2:
        return 'scatter', {'x': numeric_cols[0], 'y': numeric_cols[1]}
    return 'table', {}


# ----------------------------- Prompt engineering (few-shot) -----------------------------
CLASSIFIER_PROMPT_PREFIX = textwrap.dedent("""
You are an assistant that classifies whether a user's question is asking about the dataset schema/field-level metadata
or asking about the data values/analytics that require querying the dataset.
Return a single JSON object with keys: {"category": "schema" | "data" | "other", "explanation": "..."}

Examples (few-shot):

Q: "What does items[].revenue mean?"
A: {"category":"schema","explanation":"Asks for the meaning of a field 'items[].revenue'"}

Q: "Show me monthly revenue trend for APAC"
A: {"category":"data","explanation":"Requests aggregated analytics from data (time series)"}

Q: "How to contact customer C101?"
A: {"category":"other","explanation":"This is an external or operational question not directly answered by dataset fields or analytics"}

Now classify the following question:
"""
)

VEGALITE_GENERATOR_PROMPT = textwrap.dedent("""
You are an assistant that receives two inputs:
1) A user question
2) A compact JSON array of data records (already normalized to row-per-item)

Your job: produce a valid Vega-Lite (v5) JSON spec that answers the user's question visually if a visualization is appropriate. If a table is more appropriate, return a JSON object with {"render":"table", "explanation":"...", "data": <compact-sample-data> }.

Rules:
- Output exactly one JSON block (no extra commentary outside the JSON). Place the JSON in a code fence or plain JSON.
- The JSON for a chart should contain keys: {"spec": <vega-lite-spec-object>, "explanation": "one-sentence explanation"}
- Ensure date fields are left as ISO strings and label the type using Vega-Lite types (temporal, quantitative, nominal, ordinal) in the spec.
- Aim to keep transforms in the spec (bin, aggregate, timeUnit) rather than pre-aggregating too much.

Few examples:

Example 1:
Q: "Show monthly revenue trend for APAC"
Data: rows with 'order_date','region','revenue'
A: (returns spec with a transform to filter region==APAC, timeUnit: 'yearmonth' on order_date, aggregate sum revenue)

Example 2:
Q: "Top 5 categories by revenue"
Data: rows with 'category','revenue'
A: (returns a bar chart spec sorted desc, using aggregate sum on revenue and limit 5)

Now produce the JSON response for the question and data provided.
""")

# ----------------------------- LLM wrappers -----------------------------

def call_llm_chat(prompt, system=None, temperature=0.0, max_tokens=800):
    # Simple wrapper for OpenAI ChatCompletion. Adapt as needed to your LLM provider.
    if not USE_LLM:
        return None
    if openai is None:
        raise RuntimeError("OpenAI package not installed. Install openai or set USE_LLM=False.")
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY not set in environment. Set it or toggle USE_LLM=False.")

    messages = []
    if system:
        messages.append({"role":"system","content":system})
    messages.append({"role":"user","content":prompt})

    resp = openai.ChatCompletion.create(
        model=LLM_MODEL,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens
    )
    return resp['choices'][0]['message']['content']


# ----------------------------- Streamlit UI -----------------------------

st.set_page_config(page_title="GenBI Chatbot (Vega-Lite)", layout='wide')

# session state setup
if 'history' not in st.session_state:
    st.session_state['history'] = []  # each item: (user, assistant)
if 'messages' not in st.session_state:
    st.session_state['messages'] = []
if 'last_spec' not in st.session_state:
    st.session_state['last_spec'] = None
if 'last_explanation' not in st.session_state:
    st.session_state['last_explanation'] = ''

# Sidebar: configuration, schema, conversation
with st.sidebar:
    st.header('GenBI Controls')
    st.write('Sample schema (fields):')
    for f in FIELDS:
        st.markdown(f"**{f['name']}** — *{f['type']}* — {f['description']}")

    st.markdown('---')
    st.write('Conversation history (last 3):')
    for q,a in st.session_state['history'][-3:][::-1]:
        st.info(f"Q: {q}\nA: {a}")

    st.markdown('---')
    st.write('Settings')
    use_llm_checkbox = st.checkbox('Use LLM for classification & spec generation', value=USE_LLM)
    if use_llm_checkbox != USE_LLM:
        USE_LLM = use_llm_checkbox
    chart_override = st.selectbox('UI: override chart type (no LLM call)', LOCAL_CHART_TYPES, index=0)
    max_points = st.number_input('Max points to render (local)', min_value=100, max_value=10000, value=2000, step=100)
    show_table_checkbox = st.checkbox('Always show table view', value=False)
    st.markdown('---')
    st.write('Run instructions')
    st.caption('Set OPENAI_API_KEY in your environment to enable LLM. Toggle off to run locally.')

# Main area: conversation + dataset preview
st.markdown("<h1 style='text-align:center;margin-bottom:0.25rem'>GenBI — Conversational BI Assistant (Vega-Lite)</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center;color:var(--secondaryTextColor);margin-top:0;'>Ask questions and get visual answers — pick charts, switch to table, or refine queries.</p>", unsafe_allow_html=True)

# layout: chat and preview
col1, col2 = st.columns([2,1])
with col1:
    # Conversational starters (centered) — visually prominent buttons
    st.markdown("<div style='display:flex;justify-content:center;gap:8px;margin:12px 0;'>"
                "<button class='starter'>Show monthly revenue trend for APAC</button>"
                "<button class='starter'>Top 5 categories by revenue</button>"
                "<button class='starter'>Show revenue distribution (histogram)</button>"
                "</div>", unsafe_allow_html=True)
    st.markdown("<style>.starter{background-color:#0b5fff;color:white;border-radius:6px;padding:8px 12px;border:none;cursor:pointer;font-weight:600}.starter:hover{opacity:0.92}</style>", unsafe_allow_html=True)

    # Chat messages container (scrollable)
    chat_container = st.container()
    chat_box = chat_container.empty()

    def render_messages(messages):
        html = "<div style='max-height:54vh;overflow:auto;padding:12px;border-radius:8px;border:1px solid rgba(0,0,0,0.06);background:var(--ifm-pre-background-color);'>"
        for q,a in messages:
            html += "<div style='margin-bottom:12px;padding:8px;'>"
            html += f"<div style='font-weight:600;color:#0b5fff'>You</div><div style='margin-left:6px'>{q}</div>"
            html += f"<div style='margin-top:8px;font-weight:600;color:#0c9a47'>Assistant</div><div style='margin-left:6px'>{a}</div>"
            html += "</div>"
        html += "</div>"
        chat_box.markdown(html, unsafe_allow_html=True)

    render_messages(st.session_state['messages'])

    # Sticky input CSS (fixed to bottom, sits above Streamlit footer)
    st.markdown("""
    <style>
    .chat-input-wrapper {position: fixed; left: 260px; right: 24px; bottom: 18px; background: rgba(255,255,255,0.98); padding:10px; border-radius:10px; box-shadow:0 8px 24px rgba(0,0,0,0.08); display:flex; align-items:center; z-index:9999}
    .chat-text {flex:1; margin-right:8px; padding:8px;border:1px solid rgba(0,0,0,0.08); border-radius:6px}
    .chat-send {background-color:#0b5fff;color:white;border:none;padding:8px 14px;border-radius:8px;cursor:pointer}
    @media (max-width: 900px){ .chat-input-wrapper {left:12px; right:12px;} }
    </style>
    """, unsafe_allow_html=True)

    # Reserve vertical space so the fixed input doesn't overlap content
    st.markdown("<div style='height:84px'></div>", unsafe_allow_html=True)

with col2:
    st.subheader('Data preview')
    st.write('Normalized row-per-item view (used for charts)')
    df_rows = flatten_orders_to_rows(SAMPLE_DATA)
    st.dataframe(df_rows.head(10))
    st.markdown('Download sample JSON')
    st.download_button('Download JSON', data=json.dumps(SAMPLE_DATA, indent=2), file_name='sample_sales.json', mime='application/json')

# Fallback conversational starters implemented as real Streamlit buttons (safe & accessible)
starter_col1, starter_col2, starter_col3 = st.columns([1,1,1])
with starter_col1:
    if st.button('Starter: Monthly revenue (APAC)'):
        st.session_state['input_q'] = 'Show monthly revenue trend for APAC region'
with starter_col2:
    if st.button('Starter: Top 5 categories'):
        st.session_state['input_q'] = 'Top 5 categories by revenue'
with starter_col3:
    if st.button('Starter: Revenue distribution'):
        st.session_state['input_q'] = 'Show revenue distribution (histogram)'

# Sticky input row (Streamlit native inputs; visually matches fixed bar above)
input_col1, input_col2 = st.columns([18,2])
with input_col1:
    user_question = st.text_input('Your question', key='input_q', placeholder='Type your question or pick a starter...')
with input_col2:
    send = st.button('Send', key='send')

# Interaction handling

if send and user_question:
    st.session_state['messages'].append((user_question, '...working...'))

    # 1) classify question: schema / data / other
    classification = {'category':'data','explanation':'Default to data'}
    try:
        if USE_LLM:
            prompt = CLASSIFIER_PROMPT_PREFIX + f"\nQuestion: \"{user_question}\"\n"
            resp = call_llm_chat(prompt, system=None, temperature=0.0, max_tokens=200)
            try:
                classification = extract_json_from_text(resp)
            except Exception:
                # fallback: try to parse inline JSON
                m = re.search(r"(\{.*\})", resp)
                if m:
                    classification = json.loads(m.group(1))
        else:
            # local heuristic: if the question mentions a field name from FIELDS -> schema
            lowered = user_question.lower()
            found = [f for f in FIELDS if f['name'].split('.')[0] in lowered or f['name'] in lowered]
            if found and any(word in lowered for word in ['what','meaning','describe','definition','how to','explain']):
                classification = {'category':'schema','explanation':'Mentioned a field name and asked for meaning (heuristic)'}
            else:
                classification = {'category':'data','explanation':'Heuristic default to data question'}
    except Exception as e:
        classification = {'category':'data','explanation':f'Classifier error fallback: {e}'}

    # 2) respond based on classification
    assistant_text = ''
    if classification['category'] == 'schema':
        # find the field and return description
        q_lower = user_question.lower()
        matched = None
        for f in FIELDS:
            if f['name'].lower() in q_lower or f['name'].split('.')[0].lower() in q_lower:
                matched = f
                break
        if matched:
            assistant_text = f"Field: {matched['name']} (type={matched['type']}) — {matched['description']}"
            st.session_state['last_spec'] = None
            st.session_state['last_explanation'] = assistant_text
        else:
            # If not matched, optionally consult LLM for schema explanation
            if USE_LLM:
                prompt = "You are given a question about the following fields: " + json.dumps(FIELDS) + f"\nQuestion: {user_question}\nExplain which field and provide an answer." 
                resp = call_llm_chat(prompt, temperature=0.0, max_tokens=200)
                assistant_text = resp
            else:
                assistant_text = "Could not find a matching field in schema."

        # update UI
        st.session_state['messages'][-1] = (user_question, assistant_text)
        st.experimental_rerun()

    elif classification['category'] == 'data':
        # Prepare normalized rows and a compact JSON to send to LLM
        df = df_rows.copy()
        compact = sample_data_for_llm(df, max_rows=200)
        if USE_LLM:
            # build prompt for Vega-Lite generation
            generator_prompt = VEGALITE_GENERATOR_PROMPT + "\nQuestion: \"" + user_question + "\"\nData: " + json.dumps(compact, default=str) + "\n"
            try:
                gen_resp = call_llm_chat(generator_prompt, temperature=0.0, max_tokens=1000)
                # parse LLM output for JSON
                try:
                    parsed = extract_json_from_text(gen_resp)
                except Exception:
                    parsed = None
                if parsed and 'spec' in parsed:
                    spec = parsed['spec']
                    explanation = parsed.get('explanation','')
                    st.session_state['last_spec'] = spec
                    st.session_state['last_explanation'] = explanation
                    assistant_text = explanation
                elif parsed and parsed.get('render') == 'table':
                    st.session_state['last_spec'] = None
                    assistant_text = parsed.get('explanation','Showing table')
                    st.session_state['last_explanation'] = assistant_text
                else:
                    # fallback: LLM did not return a good vega-lite; show table
                    st.session_state['last_spec'] = None
                    assistant_text = 'Could not parse vega-lite spec from LLM. Showing fallback table.'
                    st.session_state['last_explanation'] = assistant_text
            except Exception as e:
                st.session_state['last_spec'] = None
                assistant_text = f'LLM error: {e} — falling back to local heuristic chart.'
                st.session_state['last_explanation'] = assistant_text
                # fallthrough to local heuristic
        else:
            # local heuristic chart selection
            chart_type, cols = infer_chart_from_df(df)
            if chart_type == 'table':
                assistant_text = 'I think a table is the best view for this question. Showing table.'
                st.session_state['last_spec'] = None
                st.session_state['last_explanation'] = assistant_text
            else:
                # build a small vega-lite spec locally
                spec = {
                    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
                    "data": {"values": compact},
                    "mark": chart_type if chart_type!='scatter' else 'point',
                    "encoding": {
                        "x": {"field": cols.get('x'), "type": 'temporal' if 'date' in cols.get('x','') else 'nominal'},
                        "y": {"field": cols.get('y'), "type": 'quantitative'}
                    }
                }
                st.session_state['last_spec'] = spec
                assistant_text = f'Local heuristic produced a {chart_type} chart.'
                st.session_state['last_explanation'] = assistant_text

        # update conversation history and show results
        st.session_state['messages'][-1] = (user_question, assistant_text)
        st.session_state['history'].append((user_question, assistant_text))

        # render panel
        if st.session_state['last_spec'] is not None:
            st.subheader('Suggested visualization (Vega-Lite)')
            st.markdown(st.session_state['last_explanation'])
            # allow user to override chart type locally (no LLM call)
            override = chart_override
            if override != 'auto-infer' and override != 'table':
                # mutate mark
                spec = dict(st.session_state['last_spec'])
                spec['mark'] = override if override!='scatter' else 'point'
            else:
                spec = st.session_state['last_spec']

            # optionally limit rows shown/sent; we rely on vega-lite transforms if present
            try:
                st.vega_lite_chart(spec, use_container_width=True)
            except Exception as e:
                st.error(f"Error rendering Vega-Lite spec: {e}")
                st.markdown('Showing fallback table:')
                st.dataframe(df.head(200))

            if show_table_checkbox:
                st.markdown('Data (table)')
                st.dataframe(df.head(500))

        else:
            st.subheader('Fallback table view')
            st.markdown(st.session_state['last_explanation'])
            st.dataframe(df.head(500))

        st.experimental_rerun()

    else:
        # category == other
        assistant_text = "This question appears to be outside the dataset or operational — here's guidance: "
        if USE_LLM:
            resp = call_llm_chat("Answer the following operational question briefly: " + user_question, temperature=0.2, max_tokens=250)
            assistant_text = resp
        st.session_state['messages'][-1] = (user_question, assistant_text)
        st.session_state['history'].append((user_question, assistant_text))
        st.experimental_rerun()

# Footer: small help and samples
st.markdown('---')
st.write('Sample prompts to try:')
st.markdown('- `Show monthly revenue trend for APAC region`')
st.markdown('- `Top 5 categories by revenue`')
st.markdown('- `What does items[].revenue mean?`')
st.markdown('- `Show revenue distribution (histogram)`')

# End of file
