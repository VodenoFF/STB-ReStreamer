# STB-ReStreamer Test Plan

This test plan outlines a systematic approach to verify that all critical functionality from the original STB-ReStreamer application has been properly implemented in the refactored version.

## 1. Test Environment Setup

### 1.1. Prerequisites

- Both applications deployed (original and refactored)
- Identical portal configurations
- Test IPTV accounts with:
  - Stalker/Ministra portal
  - Xtream portal
  - M3U playlist

### 1.2. Tools

- Web browser (Chrome, Firefox)
- Stream testing tools (VLC, ffmpeg)
- Network monitoring (Wireshark, browser dev tools)
- API testing (Postman, curl)

### 1.3. Test Data

- Sample portals for each type
- Test MACs and credentials
- Sample channel groups
- Test streams

## 2. Functional Test Cases

### 2.1. Core Functionality

#### 2.1.1. Application Initialization

| Test ID | Test Description | Expected Result | Status |
|---------|-----------------|----------------|--------|
| CORE-001 | Start application with default configuration | App starts and listens on configured port | ❓ |
| CORE-002 | Start application with custom port | App starts and listens on specified port | ❓ |
| CORE-003 | Start application with invalid configuration | App handles error gracefully | ❓ |

#### 2.1.2. Authentication & Security

| Test ID | Test Description | Expected Result | Status |
|---------|-----------------|----------------|--------|
| AUTH-001 | Access protected route without authentication | Redirect to login page | ❓ |
| AUTH-002 | Login with valid credentials | Successful login and access to dashboard | ❓ |
| AUTH-003 | Login with invalid credentials | Error message and remain on login page | ❓ |
| AUTH-004 | Logout functionality | Session terminated and redirect to login | ❓ |
| AUTH-005 | Session persistence | Session remains valid across browser restarts | ❓ |

### 2.2. Portal Management

#### 2.2.1. Portal CRUD Operations

| Test ID | Test Description | Expected Result | Status |
|---------|-----------------|----------------|--------|
| PORTAL-001 | View list of portals | All portals displayed with status | ❓ |
| PORTAL-002 | Add new Stalker portal | Portal added and visible in list | ❓ |
| PORTAL-003 | Add new Ministra portal | Portal added and visible in list | ❓ |
| PORTAL-004 | Add new Xtream portal | Portal added and visible in list | ❓ |
| PORTAL-005 | Add new M3U portal | Portal added and visible in list | ❓ |
| PORTAL-006 | Edit existing portal | Portal details updated | ❓ |
| PORTAL-007 | Delete existing portal | Portal removed from list | ❓ |

#### 2.2.2. Portal Configuration

| Test ID | Test Description | Expected Result | Status |
|---------|-----------------|----------------|--------|
| PORTALCFG-001 | Add MAC address to portal | MAC added to portal | ❓ |
| PORTALCFG-002 | Remove MAC address from portal | MAC removed from portal | ❓ |
| PORTALCFG-003 | Enable/disable portal | Portal status changes | ❓ |
| PORTALCFG-004 | Test portal connectivity | Connection status displayed | ❓ |
| PORTALCFG-005 | Add portal with invalid URL | Validation error displayed | ❓ |
| PORTALCFG-006 | Configure portal with username/password | Credentials saved and used | ❓ |

### 2.3. Channel Management

#### 2.3.1. Channel Loading & Display

| Test ID | Test Description | Expected Result | Status |
|---------|-----------------|----------------|--------|
| CHAN-001 | Load channels from Stalker portal | Channels displayed correctly | ❓ |
| CHAN-002 | Load channels from Xtream portal | Channels displayed correctly | ❓ |
| CHAN-003 | Load channels from M3U playlist | Channels displayed correctly | ❓ |
| CHAN-004 | View channel details | Channel info displayed correctly | ❓ |

#### 2.3.2. Channel Group Management

| Test ID | Test Description | Expected Result | Status |
|---------|-----------------|----------------|--------|
| GROUP-001 | Create new channel group | Group created and visible | ❓ |
| GROUP-002 | Add channels to group | Channels added to group | ❓ |
| GROUP-003 | Remove channel from group | Channel removed from group | ❓ |
| GROUP-004 | Reorder channels within group | Channels display in new order | ❓ |
| GROUP-005 | Reorder groups | Groups display in new order | ❓ |
| GROUP-006 | Delete channel group | Group removed from list | ❓ |
| GROUP-007 | Edit group properties | Group properties updated | ❓ |

### 2.4. Streaming Functionality

#### 2.4.1. Stream Generation

| Test ID | Test Description | Expected Result | Status |
|---------|-----------------|----------------|--------|
| STREAM-001 | Generate direct stream from Stalker portal | Stream plays correctly | ❓ |
| STREAM-002 | Generate direct stream from Xtream portal | Stream plays correctly | ❓ |
| STREAM-003 | Generate direct stream from M3U playlist | Stream plays correctly | ❓ |
| STREAM-004 | Generate stream with FFmpeg transcoding | Stream transcoded and plays correctly | ❓ |
| STREAM-005 | Stream with invalid channel | Appropriate error displayed | ❓ |

#### 2.4.2. Stream Management

| Test ID | Test Description | Expected Result | Status |
|---------|-----------------|----------------|--------|
| STREAMCTL-001 | Use stream caching | Cached stream used on second request | ❓ |
| STREAMCTL-002 | MAC rotation on multiple streams | MACs rotated correctly | ❓ |
| STREAMCTL-003 | Stream with rate limiting | Rate limiting applied correctly | ❓ |
| STREAMCTL-004 | Stream statistics display | Active streams displayed correctly | ❓ |
| STREAMCTL-005 | Concurrent streams handling | Multiple streams handled correctly | ❓ |

### 2.5. HDHR Emulation

| Test ID | Test Description | Expected Result | Status |
|---------|-----------------|----------------|--------|
| HDHR-001 | Device discovery endpoint | Returns valid discovery data | ❓ |
| HDHR-002 | Channel lineup endpoint | Returns valid lineup data | ❓ |
| HDHR-003 | Status information endpoint | Returns valid status data | ❓ |
| HDHR-004 | Stream using HDHR URL format | Stream plays correctly | ❓ |

### 2.6. Additional Features

#### 2.6.1. Settings Management

| Test ID | Test Description | Expected Result | Status |
|---------|-----------------|----------------|--------|
| SETTINGS-001 | View settings page | Settings displayed correctly | ❓ |
| SETTINGS-002 | Modify application settings | Settings saved and applied | ❓ |
| SETTINGS-003 | Reset settings to default | Settings reset to defaults | ❓ |

#### 2.6.2. Playlist Export

| Test ID | Test Description | Expected Result | Status |
|---------|-----------------|----------------|--------|
| PLAYLIST-001 | Export M3U playlist all channels | Valid M3U playlist generated | ❓ |
| PLAYLIST-002 | Export M3U playlist for specific group | Valid group playlist generated | ❓ |
| PLAYLIST-003 | Export with custom parameters | Playlist reflects custom settings | ❓ |

#### 2.6.3. EPG Functionality

| Test ID | Test Description | Expected Result | Status |
|---------|-----------------|----------------|--------|
| EPG-001 | View EPG data | EPG displayed correctly | ❓ |
| EPG-002 | Channel mapping for EPG | Mappings work correctly | ❓ |
| EPG-003 | EPG data update | EPG updates properly | ❓ |

#### 2.6.4. Alert System

| Test ID | Test Description | Expected Result | Status |
|---------|-----------------|----------------|--------|
| ALERT-001 | View system alerts | Alerts displayed correctly | ❓ |
| ALERT-002 | Generate new alert | Alert appears in list | ❓ |
| ALERT-003 | Resolve an alert | Alert marked as resolved | ❓ |

## 3. Performance Testing

| Test ID | Test Description | Expected Result | Status |
|---------|-----------------|----------------|--------|
| PERF-001 | Load testing: 10 concurrent streams | All streams function correctly | ❓ |
| PERF-002 | Memory usage over time | Memory usage remains stable | ❓ |
| PERF-003 | CPU usage during streaming | CPU usage reasonable | ❓ |
| PERF-004 | Response time for UI operations | UI remains responsive | ❓ |

## 4. Security Testing

| Test ID | Test Description | Expected Result | Status |
|---------|-----------------|----------------|--------|
| SEC-001 | Credential storage security | Credentials stored securely | ❓ |
| SEC-002 | Session handling | Sessions managed securely | ❓ |
| SEC-003 | Token management | Tokens managed securely | ❓ |
| SEC-004 | Input validation | Invalid inputs rejected | ❓ |

## 5. Compatibility Testing

| Test ID | Test Description | Expected Result | Status |
|---------|-----------------|----------------|--------|
| COMPAT-001 | Browser compatibility: Chrome | Application functions correctly | ❓ |
| COMPAT-002 | Browser compatibility: Firefox | Application functions correctly | ❓ |
| COMPAT-003 | Browser compatibility: Safari | Application functions correctly | ❓ |
| COMPAT-004 | Browser compatibility: Edge | Application functions correctly | ❓ |
| COMPAT-005 | Mobile compatibility | Functions on mobile devices | ❓ |
| COMPAT-006 | Player compatibility: VLC | Streams play correctly | ❓ |
| COMPAT-007 | Player compatibility: KODI | Streams play correctly | ❓ |
| COMPAT-008 | Player compatibility: Built-in player | Streams play correctly | ❓ |

## 6. Test Execution

### 6.1. Test Environment Preparation

1. Deploy both applications in identical environments
2. Configure identical test portals in both apps
3. Prepare test data for channels and groups

### 6.2. Test Execution Process

1. Execute tests in order of dependency
2. Document results for each test case
3. For failed tests, document:
   - Steps to reproduce
   - Expected vs. actual result
   - Error messages
   - Screenshots/logs
4. Update status in tracking sheet

### 6.3. Test Reporting

After all tests are completed:

1. Calculate pass/fail percentages
2. Identify critical issues
3. Document workarounds for any issues
4. Prepare summary report with recommendations

## 7. Issue Tracking and Resolution

For any discovered issues:

1. Create detailed issue report with:
   - Issue description
   - Steps to reproduce
   - Severity assessment
   - Affected functionality

2. Track issue resolution:
   - Assigned developer
   - Status (Open, In Progress, Fixed, Verified)
   - Resolution notes
   - Verification results

## 8. Regression Test Plan

After any fixes or changes:

1. Re-test directly affected functionality
2. Re-test any dependent functionality
3. Verify no new issues introduced
4. Update test results documentation

## 9. Final Acceptance Criteria

The refactored application will be considered functional equivalent to the original when:

1. All critical functionality tests pass
2. No high-severity issues remain
3. Performance metrics meet or exceed original
4. All identified original bugs have been addressed

## 10. Test Tools & Procedures

### 10.1. Manual Testing Procedure

1. Login to application
2. Navigate to functionality being tested
3. Execute test steps according to test case
4. Document results and observations
5. Capture screenshots of any issues

### 10.2. Automated Testing (if applicable)

1. API endpoint testing with Postman/curl
2. Load testing with appropriate tools
3. Browser automation for UI testing

### 10.3. Tools

- Browser developer tools for debugging
- Wireshark for network analysis
- VLC for stream verification
- FFMPEG for stream testing/analysis 