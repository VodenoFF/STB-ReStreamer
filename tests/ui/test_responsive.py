"""
Tests for responsive design across different screen sizes.
"""
import pytest
from tests.ui.pages import LoginPage, DashboardPage


@pytest.mark.parametrize('screen_type', ['mobile', 'tablet', 'laptop', 'desktop'])
def test_login_responsive(browser, base_url, screen_type, request):
    """Test that the login page is responsive across different screen sizes."""
    # Override the screen size for this specific test
    screen_size_param = request.config.getoption('--screen-size')
    original_size = browser.get_window_size()
    
    # Set screen size based on parameter
    if screen_type == 'mobile':
        browser.set_window_size(375, 812)  # iPhone X
    elif screen_type == 'tablet':
        browser.set_window_size(768, 1024)  # iPad
    elif screen_type == 'laptop':
        browser.set_window_size(1366, 768)  # Laptop
    elif screen_type == 'desktop':
        browser.set_window_size(1920, 1080)  # Desktop
    
    try:
        # Navigate to login page
        login_page = LoginPage(browser, base_url)
        login_page.navigate()
        
        # Verify login page loads
        assert login_page.is_loaded()
        
        # Get current window size
        size = browser.get_window_size()
        
        # Get container width
        container_width = login_page.get_container_width()
        
        # Print debug info
        print(f"Testing {screen_type} layout at {size['width']}x{size['height']}")
        print(f"Container width: {container_width}")
        
        # Verify responsive behavior
        if screen_type == 'mobile':
            # On mobile, container should take up most of the width
            assert container_width > size['width'] * 0.6, f"Container width ({container_width}) should be greater than {size['width'] * 0.6}"
        elif screen_type == 'tablet':
            # On tablet, container is a bit narrower but still takes significant space
            assert container_width > size['width'] * 0.4, f"Container width ({container_width}) should be greater than {size['width'] * 0.4}"
        else:
            # On larger screens, container should be more compact
            assert container_width < size['width'] * 0.7, f"Container width ({container_width}) should be less than {size['width'] * 0.7}"
    
    finally:
        # Restore original window size
        browser.set_window_size(original_size['width'], original_size['height'])


@pytest.mark.parametrize('screen_type', ['mobile', 'tablet', 'laptop', 'desktop'])
def test_dashboard_responsive(browser, base_url, screen_type, request):
    """Test that the dashboard is responsive across different screen sizes."""
    # Set screen size based on parameter
    original_size = browser.get_window_size()
    
    if screen_type == 'mobile':
        browser.set_window_size(375, 812)  # iPhone X
    elif screen_type == 'tablet':
        browser.set_window_size(768, 1024)  # iPad
    elif screen_type == 'laptop':
        browser.set_window_size(1366, 768)  # Laptop
    elif screen_type == 'desktop':
        browser.set_window_size(1920, 1080)  # Desktop
    
    try:
        # Login first
        login_page = LoginPage(browser, base_url)
        login_page.navigate()
        login_page.login('admin', 'admin')
        
        # Verify dashboard loads
        dashboard_page = DashboardPage(browser, base_url)
        assert dashboard_page.is_loaded()
        
        # Get actual window size after browser resizing
        actual_size = browser.get_window_size()
        print(f"Testing {screen_type} layout at {actual_size['width']}x{actual_size['height']}")
        
        # Verify dashboard elements are visible
        sidebar = browser.find_element('class name', 'sidebar')
        content = browser.find_element('class name', 'content')
        
        # Basic assertions that should pass on all screen sizes
        assert sidebar.is_displayed(), "Sidebar should be visible"
        assert content.is_displayed(), "Content should be visible"
        
        # Get element dimensions
        sidebar_width = sidebar.size['width']
        content_width = content.size['width']
        sidebar_height = sidebar.size['height']
        
        # Debug information
        print(f"Sidebar dimensions: {sidebar_width}x{sidebar_height}")
        print(f"Content width: {content_width}")
        print(f"Sidebar location: x={sidebar.location['x']}, y={sidebar.location['y']}")
        print(f"Content location: x={content.location['x']}, y={content.location['y']}")
        
        # Check layout based on screen size
        if screen_type == 'mobile':
            # On mobile, verify layout is stacked vertically
            # Either the sidebar is above the content
            if sidebar.location['y'] < content.location['y']:
                assert sidebar.location['y'] < content.location['y'], "Sidebar should be above content on mobile"
            # Or sidebar takes full width
            else:
                assert sidebar_width >= actual_size['width'] * 0.9, "Sidebar should take nearly full width on mobile"
        elif screen_type == 'tablet':
            # On tablet, the layout could be either stacked or side-by-side
            # Just verify that elements are visible and appropriately sized
            assert sidebar_width <= actual_size['width'], "Sidebar should not exceed screen width"
            assert content_width <= actual_size['width'], "Content should not exceed screen width" 
        else:
            # On larger screens, sidebar should be narrower than content
            assert sidebar_width < content_width, "Sidebar should be narrower than content on larger screens"
        
        # Check welcome text is visible
        welcome_text = browser.find_element('class name', 'welcome')
        assert welcome_text.is_displayed(), "Welcome text should be visible"
        assert "Welcome" in welcome_text.text, "Welcome text should be present"
    
    finally:
        # Restore original window size
        browser.set_window_size(original_size['width'], original_size['height']) 