import asyncio
import inspect
import random
import re
import time
import urllib
from datetime import datetime
from pprint import pprint as print

import logging

import aiohttp
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs

logging.getLogger("asyncio").setLevel(logging.INFO)


class SSC_Scraper:
    def __init__(self, max_concurrent_tasks=60, retries_per_session=10):
        self.max_concurrent_tasks = max_concurrent_tasks
        self.max_retries_per_session = retries_per_session
        self.url_regex_base = "/cs/courseschedule\?pname=subjarea"

        self.results = {}

    def get_regex_pattern(self, **kwargs):
        url_params = [f"{k}={v}" for k, v in kwargs.items()]
        return ".*".join([self.url_regex_base] + url_params) + ".*"

    @staticmethod
    def _generate_headers():
        """
        Generate the headers for the API request.

        Returns:
            dict: The headers for the API request.
        """
        return {"User-Agent": f"Mozilla {random.randint(1,6)}.0"}

    @staticmethod
    def _format_urls_to_text(urls):
        """
        Formats a list of URLs to text by removing HTML tags.

        Parameters:
        - urls (list): A list of URLs to be formatted.

        Returns:
        - list: A list of URLs formatted as plain text.
        """
        return list(
            map(lambda url: re.sub('<.*"?>', "", re.sub('<.*">', "", str(url))), urls)
        )

    @staticmethod
    def get_sleep_duration(consecutive_retries):
        """
        Calculates the sleep duration for retrying an operation based on the number of current retries.

        Args:
            consecutive_retries (int): The number of current retries.

        Returns:
            float: The calculated sleep duration.
        """
        return 3 * (float(consecutive_retries) / 2) + 2

    @staticmethod
    def make_url(
        sesscd="W",
        sessyr=str(datetime.now().year),
        campuscd="UBC",
        dept="",
        course="",
        section="",
    ):
        """
        Generate the URL for the UBC course page based on the provided parameters.

        Args:
            sesscd (str, optional): The session code. Defaults to "W".
            sessyr (str, optional): The session year. Defaults to the current year.
            campuscd (str, optional): The campus code. Defaults to "UBC".
            dept (str, optional): The department code. Defaults to "".
            course (str, optional): The course code. Defaults to "".
            section (str, optional): The section code. Defaults to "".

        Returns:
            str: The generated URL for the UBC course schedule.
        """
        if section != "":
            tname = "subj-section"
        elif course != "":
            tname = "subj-course"
        elif dept != "":
            tname = "subj-department"
        else:
            tname = "subj-all-departments"

        base_url = f"https://courses.students.ubc.ca/cs/courseschedule?"
        url_params = dict(pname="subjarea", tname=tname)

        frame = inspect.currentframe()
        url_params.update(
            {
                k: v
                for k, v in inspect.getargvalues(frame).locals.items()
                if k
                in (
                    "dept",
                    "course",
                    "section",
                    "campuscd",
                    "campuscd",
                    "sesscd",
                    "sessyr",
                )
            }
        )
        return base_url + urllib.parse.urlencode(url_params)

    def reset_results(self):
        """
        Resets the results list.

        Parameters:
            self (object): The instance of the class.

        Returns:
            None
        """
        self.results = {}

    async def _async_get_urls_from_itemlist(self, item_list):
        """
        Populate the queue with URLs based on the given item list.

        Parameters:
            queue (Queue): The queue to populate with URLs.
            item_list (List[str]): The list of items to process.

        Returns:
            List[str]: The list of objects added to the queue.

        Raises:
            Exception: If an unknown or invalid URL is passed into the function.
        """

        tasks = []

        for item in item_list:
            item_split = item.split()

            # Base Case - scrape a specific section of a specific course (ex: PHIL 220 99A)
            if len(item_split) == 3:
                dept, course, section = item_split
                url = SSC_Scraper.make_url(dept=dept, course=course, section=section)
                future_object = asyncio.Future()
                future_object.set_result(url)
                tasks += [future_object]

            # Recursive Case #1 - scrape all courses and sections (ex: BIOL)
            elif len(item_split) == 1:
                dept = item_split[0]
                course = section = ""
                courses = self.get_courses(dept=dept, course=course, section=section)
                tasks += [
                    asyncio.create_task(self._async_get_urls_from_itemlist(courses))
                ]

            # Recursive Case #2 - scrape all sections of a course (ex: CPSC 110)
            elif len(item_split) == 2:
                dept, course = item_split
                section = ""
                sections = self.get_sections(dept=dept, course=course, section=section)
                tasks += [
                    asyncio.create_task(self._async_get_urls_from_itemlist(sections))
                ]

            # Raise error - invalid URL
            else:
                raise Exception(f"Unknown / Invalid URL passed into function: {url}")
        results = await asyncio.gather(*tasks)
        return results

    def _get_urls_from_itemlist(self, item_list, mode="default"):
        """
        Populates the queue with URLs based on the given item list.

        Parameters:
            item_list (list): A list of items to generate URLs for.

        Returns:
            list: A list of URLs generated based on the item list.
        """
        objects = []

        # Mode "All" scrapes through all lists
        if mode == "all":
            all_courses = {}

        for item in item_list:
            item_split = item.split()

            # Base Case - scrape a specific section of a specific course (ex: PHIL 220 99A)
            if len(item_split) == 3:
                dept, course, section = item_split
                url = SSC_Scraper.make_url(dept=dept, course=course, section=section)
                objects.append(url)

            # Recursive Case #1 - scrape all courses and sections (ex: BIOL)
            elif len(item_split) == 1:
                dept = item_split[0]
                course = section = ""
                courses = self.get_courses(dept=dept, course=course, section=section)
                objects += self._get_urls_from_itemlist(courses)

            # Recursive Case #2 - scrape all sections of a course (ex: CPSC 110)
            elif len(item_split) == 2:
                dept, course = item_split
                section = ""
                sections = self.get_sections(dept=dept, course=course, section=section)
                objects += self._get_urls_from_itemlist(sections)

            # Raise error -
            else:
                raise Exception(f"Unknown / Invalid URL passed into function: {url}")

        if mode == "all":
            return (all_courses, objects)
        return objects

    def _get_urls_from_page(self, url, pattern, start=0, end=None):
        """
        Retrieves URLs from a web page based on a given pattern.

        Args:
            url (str): The URL of the web page.
            pattern (str): The regular expression pattern to match the URLs.
            start (int, optional): The index of the first URL to retrieve (default is 0).
            end (int, optional): The index of the last URL to retrieve (default is None).

        Raises:
            Exception: If the web page indicates that the course is no longer offered.
            Exception: If no URLs matching the pattern are found.

        Returns:
            list: A list of BeautifulSoup objects representing the URLs.
        """
        page = self._get_html(url)
        soup = BeautifulSoup(page, "html.parser")
        objs = soup.find_all("a", href=re.compile(pattern))

        if (
            "The requested course is either no longer offered" in soup.get_text()
            or len(objs) == 0
        ):
            print(f"Course / Department not offered this term: {url}")
            return []

        return objs

    async def _async_get_urls_from_page(self, url, pattern, start=0, end=None):
        """
        Asynchronously retrieves the URLs from a given web page that match a specified pattern.

        Args:
            url (str): The URL of the web page to retrieve.
            pattern (str): The regular expression pattern to match against the href attributes of the <a> tags.
            start (int, optional): The starting index of the objects to retrieve. Defaults to 0.
            end (int, optional): The ending index of the objects to retrieve. Defaults to None.

        Raises:
            Exception: If the web page indicates that the course is no longer offered this term.
            Exception: If no objects are found that match the specified pattern.

        Returns:
            list: A list of objects that match the specified pattern.
        """
        page = await self._async_get_html(url)
        soup = BeautifulSoup(page, "html.parser")
        objs = soup.find_all("a", href=re.compile(pattern))

        if (
            "The requested course is either no longer offered" in soup.get_text()
            or len(objs) == 0
        ):
            print(f"Course / Department is not offered this term: {url}")
            return []

        return objs

    def _get_html(self, url):
        """
        Retrieves the HTML content of a given URL.

        Args:
            url (str): The URL to retrieve the HTML content from.

        Returns:
            bytes: The HTML content of the URL as bytes.
        """
        # Add retry logic
        consecutive_retries = 0
        curr_sleep = self.get_sleep_duration(consecutive_retries)
        while consecutive_retries < self.max_retries_per_session:
            time.sleep(curr_sleep)
            try:
                response = requests.get(url, headers=self._generate_headers())
                consecutive_retries = 0
                return response.content
            except requests.exceptions.ConnectionError:
                consecutive_retries += 1
        raise Exception(f"Maximum retries exceeded in {url}.")

    async def _async_get_html(self, url, show_print=False):
        """
        Asynchronously retrieves the HTML content from the specified URL.

        Args:
            url (str): The URL to retrieve the HTML content from.
            show_print (bool, optional): Whether to print debug information. Defaults to False.

        Returns:
            str: The retrieved HTML content.

        Raises:
            Exception: If the maximum number of retries is reached.
        """
        # Add retry logic
        consecutive_retries = 0
        # Sleep duration increases after each retry
        curr_sleep = self.get_sleep_duration(consecutive_retries)
        while consecutive_retries < self.max_retries_per_session:
            await asyncio.sleep(curr_sleep)
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        url, headers=self._generate_headers()
                    ) as response:
                        html = await response.text()
                        return html
            except aiohttp.ClientError as client_error:
                consecutive_retries += 1
                if show_print:
                    logging.warning(
                        f"Client Error! Trying to use retry {consecutive_retries} out of {self.max_retries_per_session}"
                    )
        raise Exception(f"Maximum retries exceeded in {url}")

    def _extract_availability(self, url):
        html = self._get_html(url)

        # Get Course Name
        query = urlparse(url).query
        parsed_query = parse_qs(query)
        course_name = f"{parsed_query['dept'][0]} {parsed_query['course'][0]} {parsed_query['section'][0]}"

        soup = BeautifulSoup(html, "html.parser")
        nums = []
        labels = [
            "Total Seats Remaining",
            "Currently Registered",
            "General Seats Remaining",
            "Restricted Seats Remaining",
        ]
        for item in soup.find_all("strong"):
            try:
                nums.append(int(item.text))
            except ValueError as e:
                continue
        seats = {label: num for label, num in zip(labels, nums)}

        return (course_name, seats)

    def get_departments(self, **kwargs):
        """
        Retrieves a list of departments from the course schedule website.

        :return: A list of department names.
        """
        url = SSC_Scraper.make_url()
        course_urls = self._get_urls_from_page(url, self.get_regex_pattern(**kwargs))
        depts = SSC_Scraper._format_urls_to_text(course_urls)

        if len(depts) == 0:
            raise Exception("Request rejected by SSC")

        return depts

    def get_courses(self, **kwargs):
        """
        Retrieves a list of courses from the given URL.

        Parameters:
            url (str): The URL of the webpage containing the course information.

        Returns:
            list: A list of course names.
        """

        if kwargs.get("dept") is None:
            raise KeyError("Course department not provided!")

        url = SSC_Scraper.make_url(**kwargs)
        course_urls = self._get_urls_from_page(url, self.get_regex_pattern(**kwargs))
        courses = SSC_Scraper._format_urls_to_text(course_urls)

        return courses

    async def async_get_courses(self, **kwargs):
        """
        Retrieves a list of courses from the given URL asynchronously

        Parameters:
            url (str): The URL of the webpage containing the course information.

        Returns:
            list: A list of course names.
        """

        if kwargs.get("dept") is None:
            raise KeyError("Course department not provided!")

        url = SSC_Scraper.make_url(**kwargs)
        course_urls = await self._async_get_urls_from_page(
            url, self.get_regex_pattern(**kwargs)
        )
        courses = SSC_Scraper._format_urls_to_text(course_urls)

        return courses

    def get_sections(self, **kwargs):
        """
        Retrieves the sections from a given URL.

        Parameters:
            url (str): The URL to retrieve the sections from.

        Returns:
            list: A list of sections retrieved from the URL.
        """

        if kwargs.get("dept") is None:
            raise KeyError("Course department not provided!")
        if kwargs.get("course") is None:
            raise KeyError("Course number not provided!")

        url = SSC_Scraper.make_url(**kwargs)
        section_urls = self._get_urls_from_page(url, self.get_regex_pattern(**kwargs))
        sections = SSC_Scraper._format_urls_to_text(section_urls)

        return sections

    async def async_get_sections(self, **kwargs):
        """
        Retrieves the sections from a given URL.

        Parameters:
            url (str): The URL to retrieve the sections from.

        Returns:
            list: A list of sections retrieved from the URL.
        """

        if kwargs.get("dept") is None:
            raise KeyError("Course department not provided!")
        if kwargs.get("course") is None:
            raise KeyError("Course number not provided!")

        url = SSC_Scraper.make_url(**kwargs)
        section_urls = await self._async_get_urls_from_page(
            url, self.get_regex_pattern(**kwargs)
        )
        sections = SSC_Scraper._format_urls_to_text(section_urls)

        return sections

    def update_results(self, result):
        if isinstance(self.results, dict) and isinstance(result, tuple):
            key, value = result
            if isinstance(key, tuple):
                key1, key2 = key
                self.results[key1][key2] = value
            else:
                self.results[key] = value
        else:
            raise ValueError("Invalid argument and results initialization")

    async def worker(self, queue, semaphore, task):
        while True:
            async with semaphore:
                try:
                    await asyncio.sleep(random.random())
                    result = await task(queue)
                    self.update_results(result)
                    # Get new task from queue
                    queue.task_done()
                except Exception as error:
                    print(error)
                    print("Exiting worker...")
                    break

    async def async_queue_tasks(self, queue_items, task):
        queue = asyncio.Queue()
        sem = asyncio.Semaphore(self.max_concurrent_tasks)

        try:
            # Create MAX_CONCURRENT_TASKS number of workers
            tasks = [
                asyncio.create_task(self.worker(queue=queue, semaphore=sem, task=task))
                for _ in range(self.max_concurrent_tasks)
            ]

            for item in queue_items:
                await queue.put(item)

            # Wait for queue to finish all jobs
            await queue.join()

            # Cancel all workers
            for task in tasks:
                task.cancel()

            # Wait for all tasks to be cancelled
            s = await asyncio.gather(*tasks, return_exceptions=True)
            return self.results

        except Exception as e:
            print(f"Stopping workers due to exception: {e}")

    async def _async_save_all_courses(self, queue):
        url = await queue.get()

        query = urlparse(url).query
        parsed_query = parse_qs(query)
        dept = parsed_query["dept"][0]

        course = parsed_query.get("course", [""])[0]

        if course == "":
            courses = await self.async_get_courses(dept=dept)
            # Get only the course number
            courses = {course.split()[-1]: [] for course in courses}
            # Update queue with new courses
            for course in courses:
                course_url = self.make_url(dept=dept, course=course)
                queue.put_nowait(course_url)

            return (dept, courses)

        else:
            sections = await self.async_get_sections(dept=dept, course=course)
            sections = [section.split()[-1] for section in sections]
            return ((dept, course), sections)

    async def async_extract_available_seats(self, queue):
        url = await queue.get()
        html = await self._async_get_html(url)

        # Get Course Name
        query = urlparse(url).query
        parsed_query = parse_qs(query)
        course_name = f"{parsed_query['dept'][0]} {parsed_query['course'][0]} {parsed_query['section'][0]}"

        soup = BeautifulSoup(html, "html.parser")
        nums = []
        labels = [
            "Total Seats Remaining",
            "Currently Registered",
            "General Seats Remaining",
            "Restricted Seats Remaining",
        ]
        for item in soup.find_all("strong"):
            try:
                nums.append(int(item.text))
            except ValueError as e:
                continue
        seats = {label: num for label, num in zip(labels, nums)}

        return (course_name, seats)

    async def async_get_all_courses(self):
        departments = self.get_departments()
        department_urls = [self.make_url(dept=dept) for dept in departments]
        results = await self.async_queue_tasks(
            department_urls, self._async_save_all_courses
        )
        return results

    async def async_get_user_availabilities(self, queue_items, show_unavailable=True):
        urls = self._get_urls_from_itemlist(queue_items)
        results = await self.async_queue_tasks(urls, self.async_extract_available_seats)
        if show_unavailable:
            return results
        # Only show sections with availabilities
        return {k: v for k, v in results.items() if v["General Seats Remaining"] > 0}

    def get_user_availabilities(self, item_list, show_unavailable=True):
        urls = self._get_urls_from_itemlist(item_list)
        for url in urls:
            result = self._extract_availability(url)
            self.update_results(result)
        if show_unavailable:
            return self.results
        # Only show sections with availabilities
        return {
            k: v for k, v in self.results.items() if v["General Seats Remaining"] > 0
        }


if __name__ == "__main__":
    scraper = SSC_Scraper()

    results = {}

    # # Scrape all courses - synchronously
    start = time.perf_counter()

    # departments = scraper.get_departments()
    # for department in departments:
    #     results[department] = {}
    #     courses = scraper.get_courses(dept=department)
    #     for course in courses:
    #         course = course.split()[-1]
    #         sections = scraper.get_sections(dept=department, course=course)
    #         results[department][course] = sections

    results = scraper._get_urls_from_itemlist(
        ["PHIL 220 99A"] * 50 + ["CPSC 103 101"] * 50
    )

    print(results)
    print(f"Time taken: {time.perf_counter() - start: .02f} seconds")

    import json

    with open("course_info.json", "w") as outfile:
        json.dump(results, outfile)
