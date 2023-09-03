import streamlit as st
from layout import make_email_container, make_input_container, make_tracking_container
from db import init_db_connection, get_course_dropdown_data, save_user_info_db
from helpers import *
from util import *
import re

threads = []

st.set_page_config(
    page_title="Ubeseat",
    page_icon="💺",
    menu_items={
        "About": cfg.ABOUT,
    },
)

st.title("Ubeseat 💺")
st.write("Real-time alerts and tracking for UBC course availability")

# Initialize app settings and data
status = init_session_state(cookie_manager=cookie_manager)
client = init_db_connection()
course_dropdown_data = get_course_dropdown_data(client)

# Input Container
# Contains dropdown menu to select courses to be added to user dashboard
make_input_container(track_reset_session_state, course_dropdown_data)

st.markdown("---")

# Tracking Container
# Contains dashboard with user-selected courses, with the option to delete or refresh course availability status
make_tracking_container(
    get_course_url,
    track_refresh_courses,
    track_delete_course,
    update_latest_refresh_time,
    cookie_manager,
)


st.markdown("---")

# Email Container
# Contains textbox to specify email to notify when courses are available
user_email, save_email_button = make_email_container(
    enable_edit, save_email_to_session_and_cookie, client
)

if save_email_button:
    if user_email == "":
        st.error("Email can't be empty!")
    elif re.match(cfg.EMAIL_REGEX_PATTERN, user_email) is None:
        st.error("Email is invalid!")
    else:
        response = save_email_to_session_and_cookie(
            st.session_state[cfg.EMAIL_KEY], user_email, client, save_user_info_db
        )
        if response.acknowledged:
            st.success("Email and tracked courses saved!")

# Join any live threads
# Allows "refresh" to run in a separate thread from app execution, avoiding any pauses
# join_live_threads(threads, loading_data_spinner)
