"""
Tests for the mock application using page objects.
"""
import pytest
import time
from tests.ui.pages import LoginPage, DashboardPage


class TestMockApp:
    """Test cases for the mock STB-ReStreamer application."""
    
    def test_login_page_loads(self, browser, base_url):
        """Test that the login page loads correctly."""
        login_page = LoginPage(browser, base_url)
        login_page.navigate()
        
        assert login_page.is_loaded()
        
        # Verify responsive layout based on screen size
        window_size = browser.get_window_size()
        container_width = login_page.get_container_width()
        
        if window_size['width'] <= 768:  # Mobile or tablet
            assert container_width > window_size['width'] * 0.7
        else:  # Desktop or laptop
            assert container_width < window_size['width'] * 0.6
    
    def test_successful_login(self, browser, base_url):
        """Test that users can log in with valid credentials."""
        login_page = LoginPage(browser, base_url)
        login_page.navigate()
        login_page.login('admin', 'admin')
        
        # Verify redirect to dashboard
        dashboard_page = DashboardPage(browser, base_url)
        assert dashboard_page.is_loaded()
        
        # Verify welcome message
        welcome_message = dashboard_page.get_welcome_message()
        assert "Welcome, admin" in welcome_message
    
    def test_failed_login(self, browser, base_url):
        """Test that login fails with invalid credentials."""
        login_page = LoginPage(browser, base_url)
        login_page.navigate()
        login_page.login('invalid', 'wrongpassword')
        
        # Verify error message
        error_message = login_page.get_error_message()
        assert error_message is not None
        assert "Invalid credentials" in error_message
    
    def test_navigation(self, browser, base_url):
        """Test navigation between different sections of the app."""
        # Login first
        login_page = LoginPage(browser, base_url)
        login_page.navigate()
        login_page.login('admin', 'admin')
        
        # Get dashboard page object
        dashboard_page = DashboardPage(browser, base_url)
        
        # Test navigation to portals
        dashboard_page.navigate_to_portals()
        assert browser.current_url.endswith('/portals')
        
        # Return to dashboard
        browser.get(base_url)
        assert dashboard_page.is_loaded()
        
        # Test navigation to channels
        dashboard_page.navigate_to_channels()
        assert browser.current_url.endswith('/channels')
        
        # Return to dashboard
        browser.get(base_url)
        assert dashboard_page.is_loaded()
        
        # Test navigation to categories
        dashboard_page.navigate_to_categories()
        assert browser.current_url.endswith('/categories')
        
        # Return to dashboard
        browser.get(base_url)
        assert dashboard_page.is_loaded()
        
        # Test navigation to EPG
        dashboard_page.navigate_to_epg()
        assert browser.current_url.endswith('/epg')
        
        # Return to dashboard
        browser.get(base_url)
        assert dashboard_page.is_loaded()
        
        # Test navigation to settings
        dashboard_page.navigate_to_settings()
        assert browser.current_url.endswith('/settings')
    
    def test_logout(self, browser, base_url):
        """Test that users can log out successfully."""
        # Login first
        login_page = LoginPage(browser, base_url)
        login_page.navigate()
        login_page.login('admin', 'admin')
        
        # Get dashboard page object
        dashboard_page = DashboardPage(browser, base_url)
        
        # Logout
        dashboard_page.logout()
        
        # Verify redirect to login page
        time.sleep(1)  # Allow time for redirect
        assert login_page.is_loaded() 