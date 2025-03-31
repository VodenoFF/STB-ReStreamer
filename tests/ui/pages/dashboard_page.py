"""
Dashboard page object for STB-ReStreamer UI tests.
"""
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class DashboardPage:
    """Page object for the dashboard page."""
    
    # URL
    URL_PATH = "/"
    
    # Locators
    CONTAINER = (By.CLASS_NAME, "container")
    SIDEBAR = (By.CLASS_NAME, "sidebar")
    CONTENT = (By.CLASS_NAME, "content")
    WELCOME_TEXT = (By.CLASS_NAME, "welcome")
    NAV_DASHBOARD = (By.XPATH, "//a[contains(text(), 'Dashboard')]")
    NAV_PORTALS = (By.XPATH, "//a[contains(text(), 'Portals')]")
    NAV_CHANNELS = (By.XPATH, "//a[contains(text(), 'Channels')]")
    NAV_CATEGORIES = (By.XPATH, "//a[contains(text(), 'Categories')]")
    NAV_EPG = (By.XPATH, "//a[contains(text(), 'EPG')]")
    NAV_SETTINGS = (By.XPATH, "//a[contains(text(), 'Settings')]")
    NAV_LOGOUT = (By.XPATH, "//a[contains(text(), 'Logout')]")
    
    def __init__(self, browser, base_url):
        """Initialize with browser and base URL."""
        self.browser = browser
        self.base_url = base_url
        self.wait = WebDriverWait(browser, 10)
    
    def navigate(self):
        """Navigate to the dashboard page."""
        self.browser.get(f"{self.base_url}{self.URL_PATH}")
        return self
    
    def is_loaded(self):
        """Check if the dashboard page is loaded."""
        try:
            # Wait for the dashboard container to be visible
            self.wait.until(
                EC.visibility_of_element_located(self.CONTAINER)
            )
            
            # Check for the sidebar and content sections
            sidebar = self.browser.find_element(*self.SIDEBAR)
            content = self.browser.find_element(*self.CONTENT)
            
            return sidebar.is_displayed() and content.is_displayed()
        except:
            return False
    
    def get_welcome_message(self):
        """Get the welcome message text."""
        welcome_message = self.wait.until(
            EC.visibility_of_element_located(self.WELCOME_TEXT)
        )
        return welcome_message.text
    
    def navigate_to_portals(self):
        """Navigate to the portals page."""
        self.wait.until(
            EC.element_to_be_clickable(self.NAV_PORTALS)
        ).click()
        return self
    
    def navigate_to_channels(self):
        """Navigate to the channels page."""
        self.wait.until(
            EC.element_to_be_clickable(self.NAV_CHANNELS)
        ).click()
        return self
    
    def navigate_to_categories(self):
        """Navigate to the categories page."""
        self.wait.until(
            EC.element_to_be_clickable(self.NAV_CATEGORIES)
        ).click()
        return self
    
    def navigate_to_epg(self):
        """Navigate to the EPG page."""
        self.wait.until(
            EC.element_to_be_clickable(self.NAV_EPG)
        ).click()
        return self
    
    def navigate_to_settings(self):
        """Navigate to the settings page."""
        self.wait.until(
            EC.element_to_be_clickable(self.NAV_SETTINGS)
        ).click()
        return self
    
    def logout(self):
        """Log out of the application."""
        self.wait.until(
            EC.element_to_be_clickable(self.NAV_LOGOUT)
        ).click()
        return self 