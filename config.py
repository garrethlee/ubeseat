class Config:
    # In-app content
    ABOUT = """# About Ubeseat 💺

Welcome to **Ubeseat**, the app that helps you track and get notified about course availability in real-time. Whether you're a student trying to secure a spot in a popular course or someone who wants to stay updated on class openings, Ubeseat has got you covered!

## Features

- **Course Tracking**: Select the courses you're interested in, and Ubeseat will keep an eye on their availability for you.
- **Real-time Notifications**: Receive instant email notifications as soon as a tracked course becomes available.
- **User-friendly Interface**: Ubeseat's intuitive interface makes it easy to add, manage, and delete tracked courses.
- **Customization**: Personalize your experience by choosing the courses you want to track and setting up your notification preferences.

## How It Works

1. Select Courses: Use the dropdown menu to choose the courses you want to track.
2. Stay Updated: Ubeseat will monitor the availability of the selected courses and notify you when a spot opens up.
3. Receive Notifications: You'll receive an email notification with all information on courses that have availabilities

## Contact

Feel free to reach out to garreth.edderick@gmail.com for any inquiries, suggestions, or feedback

"""
    # In-app parameters
    MINUTES = 60
    DATETIME_FORMAT = "%m/%d/%Y, %H:%M:%S"
    EMAIL_REGEX_PATTERN = """(?:[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*|"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])*")@(?:(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?|\[(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?|[a-z0-9-]*[a-z0-9]:(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])+)\])"""

    # Session States and Cookies
    LAST_REFRESH_KEY = "last_refresh_timestamp"
    TRACKED_COURSES_KEY = "tracked_courses"
    EMAIL_KEY = "user_email"

    # NoSQL database params
    USER_DB = "users"
    USER_TABLE = "profiles"


cfg = Config()
