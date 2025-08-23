import os
import pandas as pd
from dotenv import load_dotenv  # this import is necessary for loading environment variables

# === Load environment variables ===
load_dotenv()

# === Embedded Source ===
{{ parts.source }}

# === Embedded LLM ===
{{ parts.llm }}

# === Embedded Prompt ===
from prompt import SYSTEM_PROMPT  # Assumes prompt.py is generated separately

# === Embedded Framework ===
{{ parts.framework }}

# === UI Configuration ===
UI_FRAMEWORK = "{{ parts.ui }}"

def load_data():
    # This function is dynamically replaced by the source-specific implementation
    pass

def run_agent(df, question):
    # This function is dynamically replaced by the framework-specific implementation
    pass

# === UI Logic ===
if UI_FRAMEWORK == "streamlit":
    import streamlit as st

    st.set_page_config(page_title="AI Data Agent", layout="wide")
    st.title("Chat with Your Data")

    data_file = "data.csv" if "{{ parts.source }}" == "csv" else "data.xlsx"

    if os.path.exists(os.path.join(os.path.dirname(__file__), data_file)):
        df = load_data()
        st.subheader("Preview of Data")
        st.dataframe(df.head())

        st.subheader("Ask a question about your data")
        question = st.text_input("Enter your question:")

        if question:
            with st.spinner("Generating response..."):
                try:
                    answer = run_agent(df, question)
                    st.success("Response:")
                    st.write(answer)
                except Exception as e:
                    st.error(f"An error occurred: {e}")
    else:
        st.error(f"{data_file} file not found.")

elif UI_FRAMEWORK == "gradio":

    import gradio as gr # This import is necessary for Gradio UI
    def ask_question(q):
        df = load_data()
        return run_agent(df, q)
    iface = gr.Interface(fn=ask_question, inputs="text", outputs="text", title="AI Data Agent")
    iface.launch()