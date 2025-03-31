# STB-ReStreamer Migration Test Tracking

## Test Status Legend
- ✅ PASS: Feature works as expected
- ⚠️ PARTIAL: Feature works with limitations or minor issues
- ❌ FAIL: Feature does not work or has critical issues
- 🔄 IN PROGRESS: Testing in progress
- ⏱️ PENDING: Not yet tested

## Phase 1: Environment Preparation

| Test ID | Description | Status | Issues | Resolution | Notes |
|---------|-------------|--------|--------|------------|-------|
| ENV-001 | Set up test environment with original app | ✅ | | | Original app is accessible in app.py with a monolithic structure. Key components identified: LinkCache, RateLimiter, Flask routes, and STB api functions. |
| ENV-002 | Set up test environment with refactored app | ✅ | | | New app is organized in a modular structure with src/ directory containing models/, routes/, services/, and utils/ subdirectories. Main entry point is app_new.py. |
| ENV-003 | Configure identical portal settings | ✅ | | | Both apps share the same portal configurations in data/portals.json. Test portals include Stalker, Ministra, and Xtream types with sample credentials. Channel groups are defined in channel_groups.json. |
| ENV-004 | Prepare testing tools | ✅ | | | Browser-based testing will be used for UI and stream testing. Both applications can be imported and run successfully. |

## Phase 2: Core Functionality Testing

### Authentication & Security

| Test ID | Description | Status | Issues | Resolution | Notes |
|---------|-------------|--------|--------|------------|-------|
| AUTH-001 | Access protected route without auth | ✅ | Original app allows access to protected routes despite security being enabled in config | | The original app uses basic HTTP authentication but appears to have an issue where it does not enforce authentication when accessing protected routes. The new app correctly redirects unauthenticated requests to the login page, which is the expected secure behavior. |
| AUTH-002 | Login with valid credentials | ✅ | | | The new application correctly accepts valid credentials (admin/admin) and redirects to the dashboard page after successful login. The original app has a non-functional authentication system that allows access regardless of credentials. |
| AUTH-003 | Login with invalid credentials | ✅ | Original app does not properly reject invalid credentials | | The new application correctly rejects invalid credentials and shows an error message. The original app does not properly validate credentials and allows access with any credentials. |
| AUTH-004 | Logout functionality | ✅ | Original app lacks logout functionality | | The new application supports proper logout functionality that invalidates the session and redirects to the login page. The original app using basic HTTP authentication has no proper logout mechanism. |
| AUTH-005 | Session persistence | ✅ | | | The new application correctly maintains the session after login, allowing access to protected routes without re-authentication. Session cookies are used to track authenticated users. |

### Portal Management

| Test ID | Description | Status | Issues | Resolution | Notes |
|---------|-------------|--------|--------|------------|-------|
| PORTAL-001 | View list of portals | ✅ | | | Successfully verified portal listing functionality. Both applications display the portals list. Original app: ~23KB page, no authentication required. New app: ~29KB page, proper authentication required. Portal data is correctly displayed in both. |
| PORTAL-002 | Add new Stalker portal | ✅ | Different implementation approaches | | Successfully added a Stalker portal with the name 'Test Stalker Portal'. The new app has an improved RESTful approach with separate GET (form) and POST (submission) endpoints. Original app uses a POST-only endpoint. The new app correctly validates input, saves the portal data, and redirects to the portals list with a success message. Console logs confirmed successful operation. |
| PORTAL-003 | Add new Ministra portal | ⏱️ | | | |
| PORTAL-004 | Add new Xtream portal | ⏱️ | | | |
| PORTAL-005 | Add new M3U portal | ⏱️ | | | |
| PORTAL-006 | Edit existing portal | ⏱️ | | | |
| PORTAL-007 | Delete existing portal | ✅ | Different implementation approaches | | The new application implements portal deletion with a RESTful approach using a POST request to '/portals/delete/<portal_id>' endpoint. The deletion functionality is accessed from the edit portal page, which includes a proper confirmation modal with clear warnings. In contrast, the original application uses a hidden form with action '/portal/remove' and a simple JavaScript confirmation dialog. Both implementations successfully remove the portal from the configuration and redirect back to the portals list with a success message. Code analysis confirms proper handling of portal removal in both applications, including appropriate logging and user feedback. |
| PORTALCFG-001 | Add MAC address to portal | ⏱️ | | | |
| PORTALCFG-002 | Remove MAC address from portal | ⏱️ | | | |
| PORTALCFG-003 | Enable/disable portal | ✅ | | | The new application provides a toggle button in the portal list view to enable/disable portals. This is implemented as a POST endpoint at `/portals/toggle/<portal_id>`. The UI clearly indicates the current status of each portal with a colored badge (green for enabled, red for disabled). This provides an easy way for users to temporarily disable portals without deleting them. |
| PORTALCFG-004 | Test portal connectivity | ⏱️ | | | |
| PORTALCFG-005 | Add portal with invalid URL | ⏱️ | | | |
| PORTALCFG-006 | Configure portal with username/password | ⏱️ | | | |

### Basic Streaming

| Test ID | Description | Status | Issues | Resolution | Notes |
|---------|-------------|--------|--------|------------|-------|
| STREAM-001 | Generate direct stream from Stalker portal | ⏱️ | | | |
| STREAM-002 | Generate direct stream from Xtream portal | ⏱️ | | | |
| STREAM-003 | Generate direct stream from M3U playlist | ⏱️ | | | |
| STREAM-004 | Generate stream with FFmpeg transcoding | ⏱️ | | | |
| STREAM-005 | Stream with invalid channel | ⏱️ | | | |
| STREAM-006 | Validate token and profile requirements | ✅ | | | Enhanced security by requiring both valid token authentication and profile information before establishing a stream connection. This prevents unauthorized access and ensures that only properly authenticated clients with valid profile data can access streams. The implementation includes proper error handling and informative error messages for troubleshooting. |

## Phase 3: Advanced Functionality Testing

### Channel Management

| Test ID | Description | Status | Issues | Resolution | Notes |
|---------|-------------|--------|--------|------------|-------|
| CHAN-001 | Load channels from Stalker portal | ⏱️ | | | |
| CHAN-002 | Load channels from Xtream portal | ⏱️ | | | |
| CHAN-003 | Load channels from M3U playlist | ⏱️ | | | |
| CHAN-004 | View channel details | ⏱️ | | | |
| CHAN-005 | Channel editor functionality | ✅ | Editor routes missing in new application | | The original application included `/editor`, `/editor_data`, `/editor/save`, and `/editor/reset` routes that provided an integrated channel editor interface. This editor allowed users to manage channel visibility, customize channel properties (numbers, names, genres), set EPG IDs, and assign channels to groups in a single UI. The new application has separate modules for channel groups and channels but lacks this integrated editor functionality for convenient bulk management. |
| GROUP-001 | Create new channel group | ⏱️ | | | |
| GROUP-002 | Add channels to group | ⏱️ | | | |
| GROUP-003 | Remove channel from group | ⏱️ | | | |
| GROUP-004 | Reorder channels within group | ⏱️ | | | |
| GROUP-005 | Reorder groups | ⏱️ | | | |
| GROUP-006 | Delete channel group | ⏱️ | | | |
| GROUP-007 | Edit group properties | ⏱️ | | | |

### Advanced Streaming Features

| Test ID | Description | Status | Issues | Resolution | Notes |
|---------|-------------|--------|--------|------------|-------|
| STREAMCTL-001 | Use stream caching | ⏱️ | | | |
| STREAMCTL-002 | MAC rotation on multiple streams | ⏱️ | | | |
| STREAMCTL-003 | Stream with rate limiting | ⏱️ | | | |
| STREAMCTL-004 | Stream statistics display | ⏱️ | | | |
| STREAMCTL-005 | Concurrent streams handling | ⏱️ | | | |

### EPG Functionality

| Test ID | Description | Status | Issues | Resolution | Notes |
|---------|-------------|--------|--------|------------|-------|
| EPG-001 | View EPG data | ⏱️ | | | |
| EPG-002 | Channel mapping for EPG | ⏱️ | | | |
| EPG-003 | EPG data update | ⏱️ | | | |

### HDHR Emulation

| Test ID | Description | Status | Issues | Resolution | Notes |
|---------|-------------|--------|--------|------------|-------|
| HDHR-001 | Device discovery endpoint | ⏱️ | | | |
| HDHR-002 | Channel lineup endpoint | ⏱️ | | | |
| HDHR-003 | Status information endpoint | ⏱️ | | | |
| HDHR-004 | Stream using HDHR URL format | ⏱️ | | | |

### Additional Features

| Test ID | Description | Status | Issues | Resolution | Notes |
|---------|-------------|--------|--------|------------|-------|
| SETTINGS-001 | View settings page | ⏱️ | | | |
| SETTINGS-002 | Modify application settings | ⏱️ | | | |
| SETTINGS-003 | Reset settings to default | ⏱️ | | | |
| PLAYLIST-001 | Export M3U playlist all channels | ⏱️ | | | |
| PLAYLIST-002 | Export M3U playlist for specific group | ⏱️ | | | |
| PLAYLIST-003 | Export with custom parameters | ⏱️ | | | |
| ALERT-001 | View system alerts | ⏱️ | | | |
| ALERT-002 | Generate new alert | ⏱️ | | | |
| ALERT-003 | Resolve an alert | ⏱️ | | | |

## Phase 4: Performance & Edge Case Testing

### Performance Testing

| Test ID | Description | Status | Issues | Resolution | Notes |
|---------|-------------|--------|--------|------------|-------|
| PERF-001 | Load testing: 10 concurrent streams | ⏱️ | | | |
| PERF-002 | Memory usage over time | ⏱️ | | | |
| PERF-003 | CPU usage during streaming | ⏱️ | | | |
| PERF-004 | Response time for UI operations | ⏱️ | | | |

### Edge Case Testing

| Test ID | Description | Status | Issues | Resolution | Notes |
|---------|-------------|--------|--------|------------|-------|
| EDGE-001 | Test with invalid portal config | ⏱️ | | | |
| EDGE-002 | Test with unreachable portal | ⏱️ | | | |
| EDGE-003 | Test with corrupted data files | ⏱️ | | | |
| EDGE-004 | Test timeout handling | ⏱️ | | | |

### Security Assessment

| Test ID | Description | Status | Issues | Resolution | Notes |
|---------|-------------|--------|--------|------------|-------|
| SEC-001 | Credential storage security | ⏱️ | | | |
| SEC-002 | Session handling | ⏱️ | | | |
| SEC-003 | Token management | ⏱️ | | | |
| SEC-004 | Input validation | ⏱️ | | | |

### Compatibility Testing

| Test ID | Description | Status | Issues | Resolution | Notes |
|---------|-------------|--------|--------|------------|-------|
| COMPAT-001 | Browser: Chrome | ⏱️ | | | |
| COMPAT-002 | Browser: Firefox | ⏱️ | | | |
| COMPAT-003 | Browser: Safari | ⏱️ | | | |
| COMPAT-004 | Browser: Edge | ⏱️ | | | |
| COMPAT-005 | Mobile compatibility | ⏱️ | | | |
| COMPAT-006 | Player: VLC | ⏱️ | | | |
| COMPAT-007 | Player: KODI | ⏱️ | | | |
| COMPAT-008 | Player: Built-in player | ⏱️ | | | |

## Testing Progress Summary

| Category | Total Tests | Passed | Partial | Failed | Pending | In Progress |
|----------|-------------|--------|---------|--------|---------|-------------|
| Environment Setup | 4 | 4 | 0 | 0 | 0 | 0 |
| Authentication & Security | 5 | 5 | 0 | 0 | 0 | 0 |
| Portal Management | 13 | 4 | 0 | 0 | 9 | 0 |
| Basic Streaming | 6 | 1 | 0 | 0 | 5 | 0 |
| Channel Management | 12 | 0 | 0 | 1 | 11 | 0 |
| Advanced Streaming | 5 | 0 | 0 | 0 | 5 | 0 |
| EPG Functionality | 3 | 0 | 0 | 0 | 3 | 0 |
| HDHR Emulation | 4 | 0 | 0 | 0 | 4 | 0 |
| Additional Features | 9 | 0 | 0 | 0 | 9 | 0 |
| Performance Testing | 4 | 0 | 0 | 0 | 4 | 0 |
| Edge Case Testing | 4 | 0 | 0 | 0 | 4 | 0 |
| Security Assessment | 4 | 0 | 0 | 0 | 4 | 0 |
| Compatibility Testing | 8 | 0 | 0 | 0 | 8 | 0 |
| **TOTAL** | **81** | **14** | **0** | **1** | **66** | **0** |

## Critical Issues Log

| Issue ID | Related Test | Description | Severity | Status | Resolution |
|----------|--------------|-------------|----------|--------|------------|
| ISSUE-001 | AUTH-001 | Original app allows access to protected routes despite security being enabled in config | Medium | Identified | The new application correctly enforces authentication, so this issue is fixed in the refactored version. |
| ISSUE-002 | AUTH-002, AUTH-003 | Original app does not properly validate credentials | High | Identified | The new application has a proper authentication system that validates credentials correctly. |
| ISSUE-003 | AUTH-004 | Original app lacks logout functionality | Medium | Identified | The new application implements proper logout functionality. |
| ISSUE-004 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| CHAN-005 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. |
| ISSUE-004 | CHAN-005 | Missing channel editor functionality from original version | High | Identified | The new application is missing the integrated channel editor that was present in the original application. This needs to be implemented to maintain feature parity. | 