"""
Conftest file for UI tests with fixtures for browser setup and configuration.
"""
import os
import pytest
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.edge.service import Service as EdgeService
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager


# Screen size configurations
SCREEN_SIZES = {
    'desktop': (1920, 1080),
    'laptop': (1366, 768),
    'tablet': (768, 1024),
    'mobile': (375, 812),
}


def pytest_addoption(parser):
    """Add command-line options for UI testing."""
    parser.addoption('--browser', action='store', default='chrome',
                     choices=['chrome', 'firefox', 'edge'],
                     help='Browser to use for tests')
    parser.addoption('--screen-size', action='store', default='desktop',
                     choices=['desktop', 'laptop', 'tablet', 'mobile'],
                     help='Screen size for responsive testing')
    parser.addoption('--base-url', action='store', default='http://localhost:8001',
                     help='Base URL for the application')


@pytest.fixture(scope='session')
def base_url(request):
    """Return the base URL for the application."""
    return request.config.getoption('--base-url')


@pytest.fixture(scope='session')
def screen_size(request):
    """Return the screen size configuration."""
    size_name = request.config.getoption('--screen-size')
    return SCREEN_SIZES.get(size_name, SCREEN_SIZES['desktop'])


@pytest.fixture(scope='function')
def browser(request, screen_size):
    """Set up and return a browser instance."""
    browser_name = request.config.getoption('--browser')
    headless = os.environ.get('CI', 'false').lower() == 'true'
    
    # Set up browser based on name
    if browser_name == 'chrome':
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size={}x{}'.format(*screen_size))
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    
    elif browser_name == 'firefox':
        options = webdriver.FirefoxOptions()
        if headless:
            options.add_argument('--headless')
        service = FirefoxService(GeckoDriverManager().install())
        driver = webdriver.Firefox(service=service, options=options)
        driver.set_window_size(*screen_size)
    
    elif browser_name == 'edge':
        options = webdriver.EdgeOptions()
        if headless:
            options.add_argument('--headless')
        service = EdgeService(EdgeChromiumDriverManager().install())
        driver = webdriver.Edge(service=service, options=options)
        driver.set_window_size(*screen_size)
    
    else:
        raise ValueError(f"Unsupported browser: {browser_name}")
    
    # Set implicit wait time
    driver.implicitly_wait(10)
    
    # Return the driver
    yield driver
    
    # Quit the driver after test
    driver.quit()


@pytest.fixture(scope='function')
def login(browser, base_url):
    """Login to the application with default credentials."""
    browser.get(f"{base_url}/login")
    
    # Enter credentials
    username_field = browser.find_element('id', 'username')
    password_field = browser.find_element('id', 'password')
    submit_button = browser.find_element('xpath', '//button[@type="submit"]')
    
    username_field.send_keys('admin')
    password_field.send_keys('admin')
    submit_button.click()
    
    # Wait for dashboard to load
    time.sleep(1)
    
    return browser


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Take screenshot on test failure."""
    outcome = yield
    report = outcome.get_result()
    
    if report.when == 'call' and report.failed:
        # Check if browser fixture is available
        browser = item.funcargs.get('browser')
        if browser:
            # Create screenshots directory if it doesn't exist
            os.makedirs('screenshots', exist_ok=True)
            
            # Create filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            test_name = item.nodeid.replace('/', '_').replace(':', '_').replace('.', '_')
            filename = f"screenshots/failure_{test_name}_{timestamp}.png"
            
            # Save screenshot
            browser.save_screenshot(filename)
            print(f"Screenshot saved to {filename}") 