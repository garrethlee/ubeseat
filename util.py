import streamlit as st


def join_live_threads(threads, loading_data_spinner):
    for thread in threads:
        if thread.is_alive():
            # loading_data_spinner.text("Loading data...")
            thread.join()


def enable_edit():
    """
    Enable editing by setting the session state variable "edit" to True.
    """
    st.session_state["edit"] = True
