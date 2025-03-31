"""
Tests for cross-browser compatibility.
"""
import pytest
from tests.ui.pages import LoginPage, DashboardPage


def test_browser_title_and_login(browser, base_url):
    """Test that the basic login functionality works in the current browser."""
    # Get current browser name
    browser_name = browser.capabilities.get('browserName', 'unknown').lower()
    
    # Navigate to login page
    login_page = LoginPage(browser, base_url)
    login_page.navigate()
    
    # Verify browser loads the page
    assert login_page.is_loaded()
    print(f"✅ Login page title verified in {browser_name}")
    
    # Test basic login functionality
    login_page.login('admin', 'admin')
    
    # Verify dashboard loads after login
    dashboard_page = DashboardPage(browser, base_url)
    assert dashboard_page.is_loaded()
    print(f"✅ Login functionality verified in {browser_name}")
    
    # Verify welcome message
    welcome_message = dashboard_page.get_welcome_message()
    assert "Welcome, admin" in welcome_message
    print(f"✅ Dashboard welcome message verified in {browser_name}")


def test_form_interactions(browser, base_url):
    """Test that form interactions work correctly in the current browser."""
    # Get current browser name
    browser_name = browser.capabilities.get('browserName', 'unknown').lower()
    
    # Navigate to login page
    login_page = LoginPage(browser, base_url)
    login_page.navigate()
    
    # Test interactions with form elements
    login_page.enter_username('testuser')
    username_field = browser.find_element('id', 'username')
    assert username_field.get_attribute('value') == 'testuser'
    print(f"✅ Username input verified in {browser_name}")
    
    login_page.enter_password('password123')
    password_field = browser.find_element('id', 'password')
    assert password_field.get_attribute('value') == 'password123'
    print(f"✅ Password input verified in {browser_name}")


def test_navigation_interactions(browser, base_url):
    """Test that navigation interactions work correctly in the current browser."""
    # Get current browser name
    browser_name = browser.capabilities.get('browserName', 'unknown').lower()
    
    # Login first
    login_page = LoginPage(browser, base_url)
    login_page.navigate()
    login_page.login('admin', 'admin')
    
    # Get dashboard page
    dashboard_page = DashboardPage(browser, base_url)
    
    # Test navigation to portals
    dashboard_page.navigate_to_portals()
    assert browser.current_url.endswith('/portals')
    print(f"✅ Portals navigation verified in {browser_name}")
    
    # Return to dashboard
    browser.get(base_url)
    assert dashboard_page.is_loaded()
    
    # Test navigation to channels
    dashboard_page.navigate_to_channels()
    assert browser.current_url.endswith('/channels')
    print(f"✅ Channels navigation verified in {browser_name}")
    
    # Return to dashboard
    browser.get(base_url)
    assert dashboard_page.is_loaded()
    
    # Test navigation to categories
    dashboard_page.navigate_to_categories()
    assert browser.current_url.endswith('/categories')
    print(f"✅ Categories navigation verified in {browser_name}")
    
    # Return to dashboard
    browser.get(base_url)
    assert dashboard_page.is_loaded()
    
    # Test navigation to EPG
    dashboard_page.navigate_to_epg()
    assert browser.current_url.endswith('/epg')
    print(f"✅ EPG navigation verified in {browser_name}")
    
    # Return to dashboard
    browser.get(base_url)
    assert dashboard_page.is_loaded()
    
    # Test navigation to settings
    dashboard_page.navigate_to_settings()
    assert browser.current_url.endswith('/settings')
    print(f"✅ Settings navigation verified in {browser_name}")


def test_logout_functionality(browser, base_url):
    """Test that logout functionality works correctly in the current browser."""
    # Get current browser name
    browser_name = browser.capabilities.get('browserName', 'unknown').lower()
    
    # Login first
    login_page = LoginPage(browser, base_url)
    login_page.navigate()
    login_page.login('admin', 'admin')
    
    # Get dashboard page
    dashboard_page = DashboardPage(browser, base_url)
    
    # Test logout
    dashboard_page.logout()
    assert login_page.is_loaded()
    print(f"✅ Logout functionality verified in {browser_name}") 