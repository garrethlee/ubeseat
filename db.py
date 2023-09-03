import streamlit as st
import pymongo
from config import cfg


@st.cache_resource
def init_db_connection():
    try:
        return pymongo.MongoClient(st.secrets["mongo"]["uri"])
    except KeyError:
        raise Exception("Database connection failed. URI might be invalid!")


@st.cache_data(ttl=10 * cfg.MINUTES)
def get_course_dropdown_data(_client):
    """
    Retrieves the course dropdown data from the database.

    Parameters:
        _client (object): The MongoDB client object.

    Returns:
        dict: A dictionary containing the course dropdown data.

    """
    course_db = _client["courses"]
    course_tree = course_db["course_tree"]
    return course_tree.find_one({}, {"_id": False})


def save_user_info_db(_client, orig_email, new_email, tracked_courses):
    """
    Save user information.

    Args:
        _client: The client object.
        orig_email (str): The original email of the user.
        new_email (str): The new email to update.
        tracked_courses (list): A list of courses being tracked.

    Returns:
        None
    """
    # 1. Obtain the users table
    user_profile_table = _client[cfg.USER_DB][cfg.USER_TABLE]
    # 2. if exists, update email and tracked courses.
    #    Otherwise, create new user with new email and tracked courses (upsert document)
    result = user_profile_table.update_one(
        {"email": orig_email},
        {"$set": {"email": new_email, "tracked_courses": tracked_courses}},
        upsert=True,  # insert if not present
    )
    return result
