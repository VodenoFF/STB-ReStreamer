#!/usr/bin/env python3
"""
UI Test Runner for STB-ReStreamer

This script starts the mock application and runs UI tests.
"""
import os
import sys
import time
import argparse
import subprocess
import signal
from threading import Thread


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Run UI tests for STB-ReStreamer')
    
    parser.add_argument(
        '--browser', 
        choices=['chrome', 'firefox', 'edge'],
        default='chrome',
        help='Browser to use for testing (default: chrome)'
    )
    
    parser.add_argument(
        '--screen-size',
        choices=['desktop', 'laptop', 'tablet', 'mobile'],
        default='desktop',
        help='Screen size for responsive testing (default: desktop)'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=8001,
        help='Port to run the application on (default: 8001)'
    )
    
    parser.add_argument(
        '--app',
        default='mock_app.py',
        help='Application file to run (default: mock_app.py)'
    )
    
    parser.add_argument(
        '--report',
        action='store_true',
        help='Generate HTML test report'
    )
    
    parser.add_argument(
        '--tests',
        default='tests/ui/',
        help='Test file or directory to run (default: tests/ui/)'
    )
    
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Run tests in headless mode'
    )
    
    return parser.parse_args()


def run_app(args):
    """Run the application in a separate process."""
    # Set environment variable to indicate test mode
    env = os.environ.copy()
    env['TEST_MODE'] = 'true'
    
    # Start the application
    app_process = subprocess.Popen(
        [sys.executable, args.app, '--port', str(args.port)],
        env=env
    )
    
    # Allow time for the app to start
    time.sleep(3)
    
    return app_process


def run_tests(args):
    """Run UI tests with pytest."""
    # Prepare command
    cmd = [
        sys.executable, 
        '-m', 
        'pytest',
        args.tests,
        '-v'
    ]
    
    # Add browser option if specified
    if args.browser != 'chrome':
        cmd.append(f'--browser={args.browser}')
    
    # Add HTML report option if requested
    if args.report:
        report_file = f'report-{args.browser}-{args.screen_size}.html'
        cmd.append(f'--html={report_file}')
    
    # Set environment variables
    env = os.environ.copy()
    if args.headless:
        env['CI'] = 'true'
    
    # Add base_url parameter
    cmd.append(f'--base-url=http://localhost:{args.port}')
    
    # Run tests
    return subprocess.run(cmd, env=env)


def main():
    """Main function to run UI tests."""
    args = parse_arguments()
    
    print(f"Starting UI tests with {args.browser} browser in {args.screen_size} mode")
    
    # Create screenshots directory if it doesn't exist
    os.makedirs('screenshots', exist_ok=True)
    
    # Start the application
    print(f"Starting application on port {args.port}...")
    app_process = run_app(args)
    
    try:
        # Run the tests
        print(f"Running UI tests...")
        result = run_tests(args)
        
        # Report results
        if result.returncode == 0:
            print("UI tests completed successfully!")
        else:
            print(f"UI tests failed with exit code {result.returncode}")
        
        if args.report:
            report_file = f'report-{args.browser}-{args.screen_size}.html'
            print(f"Test report saved to {report_file}")
        
        sys.exit(result.returncode)
        
    finally:
        # Terminate the application
        print("Stopping application...")
        if sys.platform == 'win32':
            app_process.terminate()
        else:
            app_process.send_signal(signal.SIGTERM)
        app_process.wait()


if __name__ == '__main__':
    main() 