"""
Login page object for STB-ReStreamer UI tests.
"""
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class LoginPage:
    """Page object for the login page."""
    
    # URL
    URL_PATH = "/login"
    
    # Locators
    USERNAME_FIELD = (By.ID, "username")
    PASSWORD_FIELD = (By.ID, "password")
    SUBMIT_BUTTON = (By.XPATH, "//button[@type='submit']")
    ERROR_MESSAGE = (By.CLASS_NAME, "error")
    LOGIN_CONTAINER = (By.CLASS_NAME, "login-container")
    
    def __init__(self, browser, base_url):
        """Initialize with browser and base URL."""
        self.browser = browser
        self.base_url = base_url
        self.wait = WebDriverWait(browser, 10)
    
    def navigate(self):
        """Navigate to the login page."""
        self.browser.get(f"{self.base_url}{self.URL_PATH}")
        return self
    
    def is_loaded(self):
        """Check if the login page is loaded."""
        try:
            # Wait for the login container to be visible
            self.wait.until(
                EC.visibility_of_element_located(self.LOGIN_CONTAINER)
            )
            
            # Check for the username and password fields
            username_field = self.browser.find_element(*self.USERNAME_FIELD)
            password_field = self.browser.find_element(*self.PASSWORD_FIELD)
            
            # Check for the submit button
            submit_button = self.browser.find_element(*self.SUBMIT_BUTTON)
            
            return True
        except:
            return False
    
    def enter_username(self, username):
        """Enter username in the username field."""
        username_field = self.wait.until(
            EC.visibility_of_element_located(self.USERNAME_FIELD)
        )
        username_field.clear()
        username_field.send_keys(username)
        return self
    
    def enter_password(self, password):
        """Enter password in the password field."""
        password_field = self.wait.until(
            EC.visibility_of_element_located(self.PASSWORD_FIELD)
        )
        password_field.clear()
        password_field.send_keys(password)
        return self
    
    def click_login(self):
        """Click the login button."""
        submit_button = self.wait.until(
            EC.element_to_be_clickable(self.SUBMIT_BUTTON)
        )
        submit_button.click()
        return self
    
    def login(self, username, password):
        """Perform login with the provided credentials."""
        self.enter_username(username)
        self.enter_password(password)
        self.click_login()
        return self
    
    def get_error_message(self):
        """Get the error message if present."""
        try:
            error = self.browser.find_element(*self.ERROR_MESSAGE)
            return error.text
        except:
            return None
    
    def get_container_width(self):
        """Get the width of the login container."""
        container = self.browser.find_element(*self.LOGIN_CONTAINER)
        return container.size['width'] 