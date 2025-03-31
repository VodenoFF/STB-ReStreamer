/**
 * STB-ReStreamer Portal Management JavaScript
 * Manages IPTV portal interactions, real-time updates, and form handling
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize Portal WebSocket connection
    initPortalWebSocket();
    
    // Initialize portal type selector behavior
    initPortalTypeSelector();
    
    // Add portal testing functionality
    initPortalTesting();
    
    // Add form validation for portal forms
    initPortalFormValidation();
});

/**
 * Initialize WebSocket connection for real-time portal updates
 */
function initPortalWebSocket() {
    // Check if socket.io is available
    if (typeof io === 'undefined') {
        console.warn('Socket.IO not loaded, real-time updates unavailable');
        return;
    }
    
    // Connect to socket.io server
    const socket = io();
    
    // Handle connection
    socket.on('connect', function() {
        console.log('Connected to server for real-time portal updates');
    });
    
    // Handle portal status updates
    socket.on('portal_status_update', function(data) {
        updatePortalStatus(data);
    });
    
    // Handle portal connection count updates
    socket.on('portal_connection_update', function(data) {
        updatePortalConnections(data);
    });
    
    // Handle disconnection
    socket.on('disconnect', function() {
        console.log('Disconnected from server');
    });
}

/**
 * Update the status indicator for a portal
 * @param {Object} data - Portal status data
 */
function updatePortalStatus(data) {
    const portalId = data.portal_id;
    const statusIndicator = document.querySelector(`#portal-status-${portalId}`);
    
    if (!statusIndicator) return;
    
    // Update the status indicator
    statusIndicator.innerHTML = '';
    
    if (data.status === 'up') {
        statusIndicator.innerHTML = '<span class="badge bg-success">UP</span>';
    } else if (data.status === 'down') {
        statusIndicator.innerHTML = '<span class="badge bg-danger">DOWN</span>';
    } else if (data.status === 'disabled') {
        statusIndicator.innerHTML = '<span class="badge bg-secondary">DISABLED</span>';
    } else {
        statusIndicator.innerHTML = '<span class="badge bg-warning">UNKNOWN</span>';
    }
    
    // Show a toast notification
    showToast(`Portal "${data.name}" is now ${data.status.toUpperCase()}`, 
              data.status === 'up' ? 'success' : data.status === 'down' ? 'danger' : 'warning');
}

/**
 * Update the connection count for a portal
 * @param {Object} data - Portal connection data
 */
function updatePortalConnections(data) {
    const portalId = data.portal_id;
    const connectionCounter = document.querySelector(`#portal-connections-${portalId}`);
    
    if (!connectionCounter) return;
    
    // Update the connection counter
    connectionCounter.textContent = data.connections;
    
    // Update class based on connection limit
    const maxConnections = parseInt(connectionCounter.getAttribute('data-max') || '1');
    
    if (data.connections >= maxConnections) {
        connectionCounter.classList.add('text-danger');
        connectionCounter.classList.remove('text-success', 'text-warning');
    } else if (data.connections > 0) {
        connectionCounter.classList.add('text-success');
        connectionCounter.classList.remove('text-danger', 'text-warning');
    } else {
        connectionCounter.classList.add('text-warning');
        connectionCounter.classList.remove('text-success', 'text-danger');
    }
}

/**
 * Initialize the portal type selector to show/hide relevant fields
 */
function initPortalTypeSelector() {
    const typeSelector = document.querySelector('#portal-type');
    if (!typeSelector) return;
    
    const updateVisibleFields = function() {
        const selectedType = typeSelector.value;
        
        // Hide all type-specific fields first
        document.querySelectorAll('.field-stalker, .field-xtream, .field-m3u, .field-ministra, .field-xcupdates')
            .forEach(field => field.classList.add('d-none'));
        
        // Show fields for the selected type
        document.querySelectorAll(`.field-${selectedType}`)
            .forEach(field => field.classList.remove('d-none'));
            
        // Handle special cases
        if (selectedType === 'm3u') {
            // Make URL field accept file:// URLs and HTTP URLs
            document.querySelector('#url').placeholder = 'http://example.com/playlist.m3u or file:///path/to/playlist.m3u';
        } else {
            // Reset URL placeholder for other types
            document.querySelector('#url').placeholder = 'http://example.com';
        }
    };
    
    // Run once on init
    updateVisibleFields();
    
    // Update when type changes
    typeSelector.addEventListener('change', updateVisibleFields);
}

/**
 * Initialize portal testing functionality
 */
function initPortalTesting() {
    // Handle test button click
    document.querySelectorAll('.btn-test-portal').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const portalId = this.getAttribute('data-portal-id');
            testPortalConnection(portalId);
        });
    });
    
    // Handle test all button
    const testAllBtn = document.querySelector('#test-all-portals');
    if (testAllBtn) {
        testAllBtn.addEventListener('click', function(e) {
            e.preventDefault();
            testAllPortals();
        });
    }
}

/**
 * Test connection to a specific portal
 * @param {string} portalId - Portal ID to test
 */
function testPortalConnection(portalId) {
    // Show testing indicator
    const statusIndicator = document.querySelector(`#portal-status-${portalId}`);
    if (statusIndicator) {
        statusIndicator.innerHTML = '<span class="spinner-border spinner-border-sm text-info" role="status"></span>';
    }
    
    // Test button
    const testButton = document.querySelector(`.btn-test-portal[data-portal-id="${portalId}"]`);
    if (testButton) {
        const originalText = testButton.innerHTML;
        testButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span> Testing...';
        testButton.disabled = true;
    }
    
    // Make the AJAX request
    fetch(`/portals/test/${portalId}`, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Show success
            showToast(`Portal test successful: ${data.message}`, 'success');
            
            if (statusIndicator) {
                statusIndicator.innerHTML = '<span class="badge bg-success">UP</span>';
            }
        } else {
            // Show error
            showToast(`Portal test failed: ${data.error}`, 'danger');
            
            if (statusIndicator) {
                statusIndicator.innerHTML = '<span class="badge bg-danger">DOWN</span>';
            }
        }
        
        // Reset test button
        if (testButton) {
            testButton.innerHTML = originalText;
            testButton.disabled = false;
        }
    })
    .catch(error => {
        console.error('Error testing portal:', error);
        showToast('Error testing portal: Network error', 'danger');
        
        // Reset status indicator
        if (statusIndicator) {
            statusIndicator.innerHTML = '<span class="badge bg-warning">UNKNOWN</span>';
        }
        
        // Reset test button
        if (testButton) {
            testButton.innerHTML = originalText;
            testButton.disabled = false;
        }
    });
}

/**
 * Test all portal connections
 */
function testAllPortals() {
    // Get all portal IDs
    const portalButtons = document.querySelectorAll('.btn-test-portal');
    const portalIds = Array.from(portalButtons).map(btn => btn.getAttribute('data-portal-id'));
    
    // Test each portal with a slight delay between them
    portalIds.forEach((portalId, index) => {
        setTimeout(() => {
            testPortalConnection(portalId);
        }, index * 500); // 500ms delay between tests to avoid overwhelming the server
    });
}

/**
 * Initialize portal form validation
 */
function initPortalFormValidation() {
    const portalForm = document.querySelector('#portal-form');
    if (!portalForm) return;
    
    portalForm.addEventListener('submit', function(e) {
        // Validate based on portal type
        const portalType = document.querySelector('#portal-type')?.value || 'stalker';
        
        const nameField = document.querySelector('#name');
        const urlField = document.querySelector('#url');
        
        // Basic validation
        let isValid = true;
        
        if (!nameField?.value.trim()) {
            showFieldError(nameField, 'Portal name is required');
            isValid = false;
        }
        
        if (!urlField?.value.trim()) {
            showFieldError(urlField, 'Portal URL is required');
            isValid = false;
        }
        
        // Type-specific validation
        if (portalType === 'm3u') {
            // Check if URL is a valid M3U URL or file path
            const urlValue = urlField?.value.trim() || '';
            if (!urlValue.endsWith('.m3u') && !urlValue.endsWith('.m3u8')) {
                showFieldError(urlField, 'URL must point to an M3U or M3U8 file');
                isValid = false;
            }
        }
        
        // MAC address validation if provided
        const macField = document.querySelector('#mac');
        if (macField && macField.value.trim()) {
            const macRegex = /^([0-9A-F]{2}[:-]){5}([0-9A-F]{2})$/i;
            if (!macRegex.test(macField.value.trim())) {
                showFieldError(macField, 'Invalid MAC address format (XX:XX:XX:XX:XX:XX)');
                isValid = false;
            }
        }
        
        if (!isValid) {
            e.preventDefault();
        }
    });
}

/**
 * Show an error for a form field
 * @param {HTMLElement} field - The form field with an error
 * @param {string} message - Error message to display
 */
function showFieldError(field, message) {
    // Add error class
    field.classList.add('is-invalid');
    
    // Create error message
    let feedbackDiv = field.nextElementSibling;
    if (!feedbackDiv || !feedbackDiv.classList.contains('invalid-feedback')) {
        feedbackDiv = document.createElement('div');
        feedbackDiv.className = 'invalid-feedback';
        field.parentNode.insertBefore(feedbackDiv, field.nextSibling);
    }
    
    feedbackDiv.textContent = message;
    
    // Remove error when field is changed
    field.addEventListener('input', function() {
        field.classList.remove('is-invalid');
    }, { once: true });
}

/**
 * Format a MAC address as it is typed
 * @param {HTMLInputElement} input - MAC address input field
 */
function formatMacAddress(input) {
    // Remove non-hex characters
    let value = input.value.replace(/[^0-9A-F]/gi, '');
    
    // Insert colons
    let formattedValue = '';
    for (let i = 0; i < value.length && i < 12; i++) {
        if (i > 0 && i % 2 === 0) {
            formattedValue += ':';
        }
        formattedValue += value[i];
    }
    
    // Update the input value
    input.value = formattedValue.toUpperCase();
} 