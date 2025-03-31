"""
Tests for basic accessibility features in the STB-ReStreamer UI.
"""
import pytest
from tests.ui.pages import LoginPage, DashboardPage


def test_login_page_accessibility(browser, base_url):
    """Test basic accessibility features on the login page."""
    # Navigate to login page
    login_page = LoginPage(browser, base_url)
    login_page.navigate()
    
    # Check that form elements have labels
    username_field = browser.find_element('id', 'username')
    password_field = browser.find_element('id', 'password')
    
    # Find label elements
    username_label = browser.find_element('xpath', "//label[@for='username']")
    password_label = browser.find_element('xpath', "//label[@for='password']")
    
    # Verify labels exist and have text
    assert username_label.text.strip() != ""
    assert password_label.text.strip() != ""
    
    # Check that form fields have appropriate attributes
    assert username_field.get_attribute('required') is not None
    assert password_field.get_attribute('required') is not None
    assert password_field.get_attribute('type') == 'password'
    
    # Check for meaningful button text
    submit_button = browser.find_element('xpath', '//button[@type="submit"]')
    assert submit_button.text.strip() != ""
    
    # Check for color contrast (basic check)
    # In a real application, you would use a specialized accessibility testing library
    background_color = browser.execute_script(
        'return window.getComputedStyle(document.body).backgroundColor'
    )
    text_color = browser.execute_script(
        'return window.getComputedStyle(document.querySelector("label")).color'
    )
    
    # Just make sure we can retrieve these values - proper contrast analysis would require more tools
    assert background_color is not None
    assert text_color is not None
    print(f"Background color: {background_color}, Text color: {text_color}")


def test_keyboard_navigation(browser, base_url):
    """Test keyboard navigation through the login form."""
    # Navigate to login page
    login_page = LoginPage(browser, base_url)
    login_page.navigate()
    
    # Focus on username field
    username_field = browser.find_element('id', 'username')
    username_field.click()
    
    # Enter username
    username_field.send_keys('admin')
    
    # Tab to password field
    browser.execute_script("arguments[0].focus(); arguments[0].select();", username_field)
    username_field.send_keys('\t')  # Tab key
    
    # Verify focus moved to password field
    active_element = browser.switch_to.active_element
    assert active_element.get_attribute('id') == 'password'
    
    # Enter password
    active_element.send_keys('admin')
    
    # Tab to submit button
    active_element.send_keys('\t')  # Tab key
    
    # Verify focus moved to submit button
    active_element = browser.switch_to.active_element
    assert active_element.get_attribute('type') == 'submit'
    
    # Hit Enter to submit the form
    active_element.send_keys('\n')  # Enter key
    
    # Verify we're redirected to dashboard after login
    dashboard_page = DashboardPage(browser, base_url)
    assert dashboard_page.is_loaded()


def test_dashboard_accessibility(browser, base_url):
    """Test basic accessibility features on the dashboard."""
    # Login first
    login_page = LoginPage(browser, base_url)
    login_page.navigate()
    login_page.login('admin', 'admin')
    
    # Get dashboard page
    dashboard_page = DashboardPage(browser, base_url)
    
    # Check navigation elements have accessible text
    nav_items = browser.find_elements('class name', 'nav-item')
    expected_texts = ['Dashboard', 'Portals', 'Channels', 'Categories', 'EPG', 'Settings']
    
    # Verify we have the expected number of navigation items
    assert len(nav_items) >= len(expected_texts), f"Expected at least {len(expected_texts)} nav items, found {len(nav_items)}"
    
    # Check that each expected navigation item exists with proper text
    found_texts = []
    for nav_item in nav_items:
        link = nav_item.find_element('tag name', 'a')
        found_texts.append(link.text)
        
        # Check that the links are clickable
        assert link.is_enabled()
        assert link.is_displayed()
    
    # Verify all expected nav texts are present
    for expected_text in expected_texts:
        assert any(expected_text in text for text in found_texts), f"Navigation item '{expected_text}' not found"
    
    # Check for logout link
    logout_element = browser.find_element('class name', 'logout')
    logout_link = logout_element.find_element('tag name', 'a')
    assert 'Logout' in logout_link.text
    assert logout_link.is_enabled()
    assert logout_link.is_displayed()
    
    # Check for heading structure (h1, h2, etc.)
    headings = browser.find_elements('xpath', '//h1 | //h2 | //h3')
    assert len(headings) > 0
    
    # Verify welcome message is visible
    welcome_message = browser.find_element(*dashboard_page.WELCOME_TEXT)
    assert welcome_message.is_displayed()
    assert welcome_message.text.strip() != "" 