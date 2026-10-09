"""The deployed Streamlit app calls the shared RAG functions directly."""
import os
import streamlit as st

from answers import answer_question
from gemini import GeminiError
from retrieval import SetupError

st.set_page_config(page_title='Client Knowledge Assistant', page_icon='📚')
try:
    # Top-level Streamlit secrets also work as environment variables for the shared backend.
    for name in ('GEMINI_API_KEY', 'GEMINI_MODEL', 'CHUNKING_MODEL'):
        if name in st.secrets:
            os.environ[name] = str(st.secrets[name])
except FileNotFoundError:
    pass  # Local runs can use .env instead.
st.title('Client Knowledge Assistant')
st.caption('Answers from Automattic’s Terms of Service, Privacy Policy and Cookie Policy.')

with st.form('question_form'):
    question = st.text_area('Your question', placeholder='How long do deleted WordPress.com posts stay in Trash?', max_chars=1000)
    submitted = st.form_submit_button('Ask', type='primary')

if submitted:
    try:
        with st.spinner('Looking for evidence…'):
            result = answer_question(question)
        st.session_state['result'] = result
    except (ValueError, GeminiError, SetupError) as error:
        st.session_state.pop('result', None)
        st.error(str(error))

if 'result' in st.session_state:
    result = st.session_state['result']
    st.subheader('Answer')
    st.write(result['answer'])
    if result['sources']:
        st.subheader('Sources')
        for index, source in enumerate(result['sources'], start=1):
            st.write(f"{index}. {source['document']} — {source['section']}")
            st.link_button('Open original document', source['url'])
            with st.expander('View supporting passage'):
                st.text(source['excerpt'])
