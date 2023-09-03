import extra_streamlit_components as stx
import streamlit as st
from config import cfg
from crawler import SSC_Scraper
from datetime import datetime
import time


def get_course_url(course_string):
    dept, course, section = course_string.split()
    return SSC_Scraper().make_url(dept=dept, course=course, section=section)


def track_reset_session_state(course, cookie_manager):
    """
    Reset the session state for the specified course by clearing the values of the "department", "course", and "section" keys.
    If the specified course is already added to the session state, display an info message.
    Otherwise, append the specified course to the "courses" list in the session state.

    Parameters:
    - course (str): The course to track and reset.

    Returns:
    - None
    """
    for obj in ("department", "course", "section"):
        st.session_state[obj] = ""
    if course in st.session_state[cfg.TRACKED_COURSES_KEY]:
        st.info(f"{course} is already added")
    else:
        st.session_state[cfg.TRACKED_COURSES_KEY][course] = ""
        cookie_manager.set(
            cfg.TRACKED_COURSES_KEY,
            st.session_state[cfg.TRACKED_COURSES_KEY],
            expires_at=None,
        )
        st.session_state["edit"] = True


def track_refresh_courses(placeholder_elements, courses, cookie_manager):
    """
    Track the refresh of courses.

    Args:
        placeholder_elements (List[Placeholder]): The list of placeholder elements.
        courses (Dict[str, Any]): The dictionary of courses.
        cookie_manager (CookieManager): The cookie manager.

    Returns:
        None
    """
    import asyncio

    scraper = SSC_Scraper()
    results_by_course = asyncio.run(
        scraper.async_get_user_availabilities(list(courses.keys()))
    )
    # Get current state of tracked courses in cookie
    tracked_courses = cookie_manager.get(cfg.TRACKED_COURSES_KEY)

    # Update cookies and streamlit elements
    for (course, results), placeholder_element in zip(
        results_by_course.items(), placeholder_elements
    ):
        # update cookie state, session state
        tracked_courses[course] = results
        st.session_state[cfg.TRACKED_COURSES_KEY][course] = results
        # Update view in streamit
        placeholder_element.table(results)

    # RE-set cookies
    cookie_manager.set(cfg.TRACKED_COURSES_KEY, tracked_courses, expires_at=None)
    st.toast("Course info refreshed!")


def track_delete_course(course, cookie_manager):
    """
    Delete a course from the session state and update the tracked courses cookie.

    Parameters:
        course (str): The name of the course to be deleted.

    Returns:
        None
    """
    st.toast(f"{course} deleted")
    st.session_state[cfg.TRACKED_COURSES_KEY].pop(course)
    cookie_manager.set(
        cfg.TRACKED_COURSES_KEY,
        st.session_state[cfg.TRACKED_COURSES_KEY],
        expires_at=None,
    )
    st.session_state["edit"] = True


def simulate_delay(seconds):
    """
    Simulates a delay for a specified number of seconds.

    Args:
        seconds (int): The number of seconds to delay.

    Returns:
        None
    """
    start_time = time.time()
    while time.time() - start_time < seconds:
        pass


def save_email_to_session_and_cookie(orig_email, new_email, client, save_user_info_db):
    """
    Saves the given email to the session state and cookie.

    Parameters:
        email (str): The email to be saved.

    Returns:
        None
    """
    response = save_user_info_db(
        client,
        st.session_state[cfg.EMAIL_KEY],
        new_email,
        list(st.session_state[cfg.TRACKED_COURSES_KEY]),
    )
    st.session_state.user_email = new_email
    cookie_manager.set(cfg.EMAIL_KEY, st.session_state[cfg.EMAIL_KEY], expires_at=None)
    st.session_state["edit"] = False
    simulate_delay(0.5)
    return response


def init_session_state(cookie_manager):
    """
    Initializes the session state by retrieving and setting the necessary values.

    Args:
        cookie_manager (CookieManager): The cookie manager object used to retrieve the cookies.

    Returns:
        bool: True if the session state is successfully initialized, False otherwise.
    """

    cookies = cookie_manager.get_all()

    # Keep track of added courses
    tracked_courses = cookies.get(cfg.TRACKED_COURSES_KEY, {})
    st.session_state[cfg.TRACKED_COURSES_KEY] = tracked_courses

    # Disable save button by default
    if "edit" not in st.session_state:
        st.session_state.edit = False

    if "scrape_job_running" not in st.session_state:
        st.session_state.scrape_job_running = False

    # Keep track of saved email
    user_email = cookies.get(cfg.EMAIL_KEY, "")
    st.session_state[cfg.EMAIL_KEY] = user_email

    return True


def update_latest_refresh_time(cookie_manager):
    """
    Update the latest refresh time.

    Parameters:
        cookie_manager (CookieManager): The cookie manager object.

    Returns:
        None
    """
    datetime_str = datetime.now().strftime(cfg.DATETIME_FORMAT)
    st.session_state[cfg.LAST_REFRESH_KEY] = datetime_str
    cookie_manager.set(
        cfg.LAST_REFRESH_KEY,
        st.session_state[cfg.LAST_REFRESH_KEY],
        expires_at=None,
        key="set_datetime",
    )


cookie_manager = stx.CookieManager()
