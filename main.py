import os
import streamlit as st 
from typing import Any, List, Dict

from doc_helper_backend.core import run_llm
import doc_helper_backend
def _format_sources(context_docs : List[Any]) -> List[str]:
    return [
        str((meta.get("source") or "Unknown"))
        for doc in (context_docs or [])
        if (meta := (getattr(doc, "metadata",None) or {})) is not None

    ]

st.set_page_config(page_title="LangChain Documentation Helper",layout="centered")
st.title("Welcome to LangChain Document Helper ")

with st.sidebar:
    st.subheader("Session")
    if st.button("Clear chat", use_container_width=True):
        st.session_state.pop("messages",None)
        st.rerun()

if "messages" not in st.session_state:
    st.session_state.messages =[
        {
            "role":"assistant",
            "content": "Ask me anything about langchain documentation.",
            "sources":["www.langchain.com","www.anthropic.com"]
        }
    ]

for msg in st.session_state.messages:
    with st.chat_message(msg['role']):
        st.markdown(msg["content"] or [])
        if msg.get("sources"):
            with st.expander("Sources"):
                for s in msg["sources"]:
                    st.markdown(f"-{s}")

prompt = st.chat_input("Ask a question about langchain...")

if prompt:
    st.session_state.messages.append({"role":"user","content":prompt , "sources":[]})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Retrieving docs and generating"):
                result: Dict[str,Any] = run_llm(prompt)
                # answer =  doc_helper_backend.core.ollama_model + "\n" + str(result.get("answer","")).strip() or "(No answer returned)"
                answer =  str(result.get("answer","")).strip() or "(No answer returned)"
                sources = set(_format_sources(result.get("context",[])))


            st.markdown(answer)
            if sources:
                with st.expander("Sources"):
                    for s in sources:
                        st.markdown(f"-{s}")

            st.session_state.messages.append({"role":"assistant", "content":answer,"sources":sources})
        except Exception as e:
            st.error("Failed to generate response.")
            st.exception(e)


if __name__ == "__main__":
    print("\n\n\n\n\n\n\n\n\nRun the below command to start\n streamlit run main.py")