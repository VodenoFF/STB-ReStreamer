"""
Basic UI tests for the STB-ReStreamer application.
"""
import pytest
from tests.ui.pages import LoginPage, DashboardPage


def test_browser_works(browser, base_url):
    """Verify that the browser can load the application."""
    login_page = LoginPage(browser, base_url)
    login_page.navigate()
    
    assert login_page.is_loaded()
    
    # Verify form fields are accessible
    username_field = browser.find_element('id', 'username')
    password_field = browser.find_element('id', 'password')
    submit_button = browser.find_element('xpath', '//button[@type="submit"]')
    
    assert username_field.is_displayed()
    assert password_field.is_displayed()
    assert submit_button.is_displayed()


def test_responsive_viewport(browser, base_url, screen_size):
    """Test that the viewport adjusts correctly for different screen sizes."""
    login_page = LoginPage(browser, base_url)
    login_page.navigate()
    
    # Check that window size is set, but don't check exact dimensions
    # as browser may adjust this based on available space
    window_size = browser.get_window_size()
    print(f"Actual window size: {window_size['width']}x{window_size['height']}")
    print(f"Expected screen size: {screen_size[0]}x{screen_size[1]}")
    
    # Verify login container width (don't compare exact window dimensions)
    container_width = login_page.get_container_width()
    
    # On mobile, container should be nearly full width
    # On desktop, container should be more compact
    if screen_size[0] <= 768:  # Mobile or tablet
        assert container_width > window_size['width'] * 0.7, "Container should be nearly full width on mobile"
    else:  # Desktop or laptop
        assert container_width < window_size['width'] * 0.6, "Container should be compact on desktop"


def test_successful_login(browser, base_url):
    """Test successful login with valid credentials."""
    login_page = LoginPage(browser, base_url)
    login_page.navigate()
    login_page.login('admin', 'admin')
    
    # Verify redirect to dashboard
    dashboard_page = DashboardPage(browser, base_url)
    assert dashboard_page.is_loaded()
    
    # Verify welcome message
    welcome_message = dashboard_page.get_welcome_message()
    assert "Welcome, admin" in welcome_message


def test_navigation_after_login(browser, base_url):
    """Test navigation between pages after login."""
    # Login first
    login_page = LoginPage(browser, base_url)
    login_page.navigate()
    login_page.login('admin', 'admin')
    
    # Get dashboard page object
    dashboard_page = DashboardPage(browser, base_url)
    assert dashboard_page.is_loaded()
    
    # Test navigation to portals
    dashboard_page.navigate_to_portals()
    assert browser.current_url.endswith('/portals')
    
    # Go back to dashboard
    browser.get(base_url)
    assert dashboard_page.is_loaded()
    
    # Test navigation to channels
    dashboard_page.navigate_to_channels()
    assert browser.current_url.endswith('/channels')
    
    # Go back to dashboard
    browser.get(base_url)
    assert dashboard_page.is_loaded()
    
    # Test navigation to categories
    dashboard_page.navigate_to_categories()
    assert browser.current_url.endswith('/categories')
    
    # Go back to dashboard
    browser.get(base_url)
    assert dashboard_page.is_loaded()
    
    # Test navigation to EPG
    dashboard_page.navigate_to_epg()
    assert browser.current_url.endswith('/epg')
    
    # Go back to dashboard
    browser.get(base_url)
    assert dashboard_page.is_loaded()
    
    # Test navigation to settings
    dashboard_page.navigate_to_settings()
    assert browser.current_url.endswith('/settings') 