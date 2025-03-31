"""
Performance tests for the STB-ReStreamer application.

These tests measure load times, memory usage, and response times for various pages.
"""
import time
import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import psutil


@pytest.fixture
def login(browser, base_url):
    """Fixture to login to the application before running tests."""
    browser.get(f"{base_url}/login")
    username_field = browser.find_element(By.ID, "username")
    password_field = browser.find_element(By.ID, "password")
    submit_button = browser.find_element(By.XPATH, "//button[@type='submit']")
    
    username_field.send_keys("admin")
    password_field.send_keys("admin")
    submit_button.click()
    
    # Wait for dashboard to load - using the container with id="dashboard"
    WebDriverWait(browser, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "container"))
    )


def measure_load_time(browser, url):
    """Measure the time it takes to load a page."""
    start_time = time.time()
    browser.get(url)
    # Wait for the page to be fully loaded
    WebDriverWait(browser, 10).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )
    end_time = time.time()
    return (end_time - start_time) * 1000  # Convert to ms


def test_initial_load_time(browser, base_url):
    """Test the initial load time of the login page."""
    load_time = measure_load_time(browser, f"{base_url}/login")
    print(f"Login page load time: {load_time:.2f} ms")
    
    # Acceptable threshold for initial load time (adjust as needed)
    assert load_time < 3000, f"Initial load time was {load_time:.2f} ms, which exceeds threshold of 3000 ms"


def test_dashboard_load_time(browser, base_url, login):
    """Test the load time of the dashboard after login."""
    # Login is handled by the fixture
    
    # Measure time to reload the dashboard
    load_time = measure_load_time(browser, base_url)
    print(f"Dashboard load time: {load_time:.2f} ms")
    
    # Acceptable threshold for dashboard load time (adjust as needed)
    assert load_time < 2000, f"Dashboard load time was {load_time:.2f} ms, which exceeds threshold of 2000 ms"


def test_navigation_response_time(browser, base_url, login):
    """Test response time when navigating between different pages."""
    # Login is handled by the fixture
    
    # Define pages to navigate to
    pages = {
        "Dashboard": "",
        "Portals": "/portals",
        "Channels": "/channels",
        "Categories": "/categories",
        "EPG": "/epg",
        "Settings": "/settings"
    }
    
    for page_name, page_url in pages.items():
        # Navigate to the page
        start_time = time.time()
        full_url = f"{base_url}{page_url}"
        browser.get(full_url)
        
        # Wait for the page to load
        WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Ensure we're on the correct page by checking URL
        if page_url:
            assert page_url in browser.current_url
        else:
            assert browser.current_url.rstrip('/') == base_url.rstrip('/') or browser.current_url == f"{base_url}/"
        
        end_time = time.time()
        response_time = (end_time - start_time) * 1000  # Convert to ms
        
        print(f"{page_name} navigation response time: {response_time:.2f} ms")
        
        # Threshold for navigation (adjust based on application expectations)
        assert response_time < 2000, f"{page_name} navigation time was {response_time:.2f} ms, which exceeds threshold of 2000 ms"
        
        # Return to dashboard before next navigation
        if page_url:
            browser.get(base_url)
            # Wait for dashboard to load
            WebDriverWait(browser, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "container"))
            )


def test_memory_usage(browser, base_url, login):
    """Test memory usage while navigating the application."""
    # Login is handled by the fixture
    
    # Get baseline memory usage
    process = psutil.Process()
    baseline_memory = process.memory_info().rss / 1024 / 1024  # Convert to MB
    
    # Define pages to navigate to
    pages = {
        "Dashboard": "",
        "Portals": "/portals",
        "Channels": "/channels",
        "Categories": "/categories",
        "EPG": "/epg",
        "Settings": "/settings"
    }
    
    max_memory_increase = 0
    
    for page_name, page_url in pages.items():
        # Navigate to the page
        full_url = f"{base_url}{page_url}"
        browser.get(full_url)
        
        # Wait for the page to load
        WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Measure memory usage
        current_memory = process.memory_info().rss / 1024 / 1024  # Convert to MB
        memory_increase = current_memory - baseline_memory
        
        print(f"{page_name} memory usage: {current_memory:.2f} MB (increase: {memory_increase:.2f} MB)")
        
        if memory_increase > max_memory_increase:
            max_memory_increase = memory_increase
            
        # Return to dashboard before next navigation
        if page_url:
            browser.get(base_url)
            # Wait for dashboard to load
            WebDriverWait(browser, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "container"))
            )
    
    # Threshold for acceptable memory increase (adjust based on application expectations)
    print(f"Maximum memory increase: {max_memory_increase:.2f} MB")
    assert max_memory_increase < 100, f"Maximum memory increase was {max_memory_increase:.2f} MB, which exceeds threshold of 100 MB" 