"""
Tests for streaming functionality in STB-ReStreamer.
These tests verify that streams are properly authenticated and validated.
"""
import unittest
from unittest.mock import MagicMock, patch
import logging
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the modules to test
from src.services.stb_api import StbApi

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test")

class TestStreamValidation(unittest.TestCase):
    """Test the streaming validation functionality."""
    
    def setUp(self):
        """Set up the test environment."""
        # Create mock config manager
        self.config_manager = MagicMock()
        
        # Create StbApi instance with the mock config manager
        self.stb_api = StbApi(self.config_manager)
        
    @patch('src.services.stb_api.StbApi._get_portal')
    def test_stream_url_with_missing_portal(self, mock_get_portal):
        """Test get_stream_url with missing portal."""
        # Set up the mock to return None (portal not found)
        mock_get_portal.return_value = None
        
        # Call the method
        result = self.stb_api.get_stream_url('invalid_portal', '00:11:22:33:44:55', 'channel_123')
        
        # Verify the result
        self.assertIsNone(result)
        mock_get_portal.assert_called_once_with('invalid_portal')
        
    @patch('src.services.stb_api.StbApi._get_portal')
    @patch('src.services.stb_api.StbApi.get_token')
    def test_stream_url_with_missing_token(self, mock_get_token, mock_get_portal):
        """Test get_stream_url with missing token."""
        # Set up the mocks
        mock_get_portal.return_value = {'name': 'Test Portal', 'type': 'stalker'}
        mock_get_token.return_value = None
        
        # Call the method
        result = self.stb_api.get_stream_url('test_portal', '00:11:22:33:44:55', 'channel_123')
        
        # Verify the result
        self.assertIsNone(result)
        mock_get_portal.assert_called_once_with('test_portal')
        mock_get_token.assert_called_once_with('test_portal', '00:11:22:33:44:55')
        
    @patch('src.services.stb_api.StbApi._get_portal')
    @patch('src.services.stb_api.StbApi.get_token')
    @patch('src.services.stb_api.StbApi.get_profile')
    def test_stream_url_with_missing_profile(self, mock_get_profile, mock_get_token, mock_get_portal):
        """Test get_stream_url with missing profile."""
        # Set up the mocks
        mock_get_portal.return_value = {'name': 'Test Portal', 'type': 'stalker'}
        mock_get_token.return_value = 'valid_token'
        mock_get_profile.return_value = None
        
        # Call the method
        result = self.stb_api.get_stream_url('test_portal', '00:11:22:33:44:55', 'channel_123')
        
        # Verify the result
        self.assertIsNone(result)
        mock_get_portal.assert_called_once_with('test_portal')
        mock_get_token.assert_called_once_with('test_portal', '00:11:22:33:44:55')
        mock_get_profile.assert_called_once_with('test_portal', '00:11:22:33:44:55')
        
    @patch('src.services.stb_api.StbApi._get_portal')
    @patch('src.services.stb_api.StbApi.get_token')
    @patch('src.services.stb_api.StbApi.get_profile')
    @patch('src.services.stb_api.StbApi._get_provider')
    def test_stream_url_with_valid_data(self, mock_get_provider, mock_get_profile, mock_get_token, mock_get_portal):
        """Test get_stream_url with valid data."""
        # Set up the mocks
        mock_get_portal.return_value = {'name': 'Test Portal', 'type': 'stalker'}
        mock_get_token.return_value = 'valid_token'
        mock_get_profile.return_value = {'status': 'active'}
        
        # Mock provider
        mock_provider = MagicMock()
        mock_provider.get_stream_url.return_value = 'http://example.com/stream/123'
        mock_get_provider.return_value = mock_provider
        
        # Call the method
        result = self.stb_api.get_stream_url('test_portal', '00:11:22:33:44:55', 'channel_123')
        
        # Verify the result
        self.assertEqual(result, 'http://example.com/stream/123')
        mock_get_portal.assert_called_once_with('test_portal')
        mock_get_token.assert_called_once_with('test_portal', '00:11:22:33:44:55')
        mock_get_profile.assert_called_once_with('test_portal', '00:11:22:33:44:55')
        mock_get_provider.assert_called_once_with({'name': 'Test Portal', 'type': 'stalker'})
        mock_provider.get_stream_url.assert_called_once_with(
            {'name': 'Test Portal', 'type': 'stalker'}, 
            '00:11:22:33:44:55', 
            'channel_123', 
            'valid_token'
        )

if __name__ == '__main__':
    unittest.main() 