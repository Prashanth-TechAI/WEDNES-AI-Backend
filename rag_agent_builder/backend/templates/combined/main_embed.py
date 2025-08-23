import os
from uuid import uuid4
import fitz
{% if config.ui.type == "streamlit" %}
import streamlit as st
{% elif config.ui.type == "gradio" %}
import gradio as gr
{% endif %}
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
import requests
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, CountResult, Distance

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
PDF_PATH = "data/data.pdf"
COLLECTION_NAME = "{{ config.vector_store.collection_name }}"
EMBED_DIM = {{ config.embedding.dimensions }}

assert GROQ_API_KEY, "Missing GROQ_API_KEY"

embedder = SentenceTransformer("{{ config.embedding.model_name }}")

qdrant = QdrantClient(url="{{ config.vector_store.url }}")
existing = [c.name for c in qdrant.get_collections().collections]
if COLLECTION_NAME not in existing:
    qdrant.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=EMBED_DIM, distance=Distance.{{ config.vector_store.distance_metric.upper() }})
    )

def load_chunks(chunk_sents=4):
    doc = fitz.open(PDF_PATH)
    text = " ".join(page.get_text().replace("\n", " ") for page in doc)
    sents = [s.strip() + "." for s in text.split(". ") if s]
    chunks, cur = [], []
    for sent in sents:
        cur.append(sent)
        if len(cur) >= chunk_sents:
            chunks.append(" ".join(cur))
            cur = []
    if cur:
        chunks.append(" ".join(cur))
    return chunks

def ensure_ingested():
    cnt: CountResult = qdrant.count(collection_name=COLLECTION_NAME)
    if cnt.count == 0:
        chunks = load_chunks()
        points = [
            {"id": str(uuid4()), "vector": embedder.encode(c).tolist(), "payload": {"text": c}}
            for c in chunks
        ]
        qdrant.upsert(collection_name=COLLECTION_NAME, points=points)

def retrieve(query: str, top_k=5) -> str:
    qv = embedder.encode(query).tolist()
    hits = qdrant.search(
        collection_name=COLLECTION_NAME,
        query_vector=qv,
        limit=top_k,
        with_payload=True,
    )
    return "\n\n".join(hit.payload["text"] for hit in hits)

def ask_groq(context: str, question: str) -> str:
    payload = {
        "model": "{{ config.llm.model_name }}",
        "messages": [{"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}\nAnswer:"}],
    }
    r = requests.post(
        "{{ config.llm.api_url }}",
        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
        json=payload,
        timeout=15,
    )
    data = r.json()
    if r.status_code != 200 or "choices" not in data:
        return f"LLM error: {data.get('error', data)}"
    return data["choices"][0]["message"]["content"].strip()

ensure_ingested()

{% if config.ui.type == "streamlit" %}
st.set_page_config(page_title="RAG Chatbot", layout="centered")
st.title(f"RAG Chatbot - {COLLECTION_NAME}")

question = st.text_input("Ask a question:")
if question:
    with st.spinner("Thinking..."):
        context = retrieve(question)
        answer = ask_groq(context, question)
    st.write(answer)

{% elif config.ui.type == "gradio" %}
def respond(question):
    context = retrieve(question)
    return ask_groq(context, question)

demo = gr.Interface(fn=respond, inputs="text", outputs="text", title="RAG Chatbot")

if __name__ == "__main__":
    demo.launch()
{% endif %}
