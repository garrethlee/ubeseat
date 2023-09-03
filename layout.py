import streamlit as st
from config import cfg
from helpers import cookie_manager
from datetime import datetime


def make_tracking_container(
    get_course_url,
    check_availability,
    track_delete_course,
    update_latest_refresh_time,
    cookie_manager,
):
    """
    Creates a tracking container for the user's tracked courses.

    Parameters:
        check_availability (function): A function that checks the availability of courses.
        track_delete_course (function): A function that tracks or deletes a course.
        update_latest_refresh_time (function): A function that updates the latest refresh time.
        cookie_manager (CookieManager): An instance of the CookieManager class.

    Returns:
        threading.Thread: A thread object that checks the availability of courses and updates the UI accordingly.
    """
    st.subheader("My Tracked Courses")
    has_been_refreshed = cookie_manager.get(cfg.LAST_REFRESH_KEY)
    if has_been_refreshed:
        has_been_refreshed = datetime.strptime(has_been_refreshed, cfg.DATETIME_FORMAT)
        last_update_time = (datetime.now() - has_been_refreshed).seconds
        last_update_time_in_minutes = last_update_time // 60
        status = f"{last_update_time_in_minutes} minutes ago"
    else:
        status = "Never"
    st.info(f"Last update: {status}")
    col1, col2, col3 = st.columns((1, 4, 0.8))
    with col1:
        st.caption("Course")
    with col2:
        st.caption("Availability")
    with col3:
        st.caption("Action")

    placeholders = []

    for course in st.session_state[cfg.TRACKED_COURSES_KEY]:
        with st.container():
            col1, col2, col3 = st.columns((1, 4, 0.8))
            with col1:
                st.text("")
                st.write(
                    f"<a href='{get_course_url(course)}'>{course}</a>",
                    unsafe_allow_html=True,
                )
            with col2:
                placeholder = st.empty()
                course_availability_data = st.session_state[
                    cfg.TRACKED_COURSES_KEY
                ].get(course, False)
                if course_availability_data:
                    if course_availability_data["General Seats Remaining"] > 0:
                        expander_text = "✅ Some general seat(s) remaning!"
                    else:
                        expander_text = "⚠️ No general seats remaining"
                else:
                    expander_text = "❌ No data collected"
                    course_availability_data = {}
                with st.expander(expander_text):
                    placeholder = st.dataframe(course_availability_data)
                    placeholders.append(placeholder)
            with col3:
                st.button(
                    "x",
                    key=f"Remove {course}",
                    on_click=track_delete_course,
                    args=(course, cookie_manager),
                    type="secondary",
                )

    check = st.button("Refresh")
    if check:
        with st.status(label="Refreshing data...", expanded=True) as status:
            st.write("Checking availability of courses...")
            check_availability(
                placeholders, st.session_state[cfg.TRACKED_COURSES_KEY], cookie_manager
            )
            update_latest_refresh_time(cookie_manager)
            status.update(label="Data Refreshed!", state="complete", expanded=True)

    return


def make_input_container(track_and_reset, course_dropdown_data):
    """
    Generates a container for user input with dropdown menus for department, course, and section.

    Parameters:
    - track_and_reset (function): A callback function to track and reset the input values.
    - course_dropdown_data (dict): A dictionary containing the dropdown data for courses.

    Returns:
    None
    """
    col1, col2, col3 = st.columns((1, 1, 1))
    with col1:
        department_options = [""] + sorted(course_dropdown_data.keys())
        department = st.selectbox(
            label="Department", options=department_options, key="department"
        )
    with col2:
        course_options = [""] + sorted(course_dropdown_data.get(department, {}).keys())
        course = st.selectbox(
            label="Course",
            options=course_options,
            disabled=department == "",
            key="course",
        )
    with col3:
        section_options = course_dropdown_data.get(department, {}).get(course, [""])
        section = st.selectbox(
            label="Section",
            options=section_options,
            disabled=course == "",
            key="section",
        )

    st.button(
        "Add",
        disabled=any((not department, not course, not section)),
        on_click=track_and_reset,
        args=(f"{department} {course} {section}", cookie_manager),
    )


def make_email_container(enable_edit, save_email, client):
    """
    Creates an email container that allows the user to input and save an email address.

    Parameters:
        enable_edit (function): A function that enables or disables the editing of the email address.
        save_email (function): A function that saves the email address.

    Returns:
        save_email_button (bool): A boolean value indicating whether the save button was clicked.
    """
    user_email = st.text_input(
        label="Notify me via",
        value=st.session_state.user_email,
        on_change=enable_edit,
        placeholder="name@email.com",
    )
    st.caption("***NOTE***: *Remember to click on **save** after entering your email*")

    st.markdown("---")

    save_email_button = st.button(
        "Save All Settings",
        disabled=not st.session_state.edit,
    )
    return user_email, save_email_button
