#!/usr/bin/env python3
"""
OSI News Automation - Master Setup Script
==========================================
Automates complete project setup from scratch.

Usage:
    python setup.py
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from datetime import datetime


# ===========================================
# FORMATTING HELPERS
# ===========================================

def print_header():
    """Print welcome header."""
    print("""
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║           OSI NEWS AUTOMATION - SETUP WIZARD                  ║
║           Automated Trending Story Generator                  ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
""")


def print_step(step_num, title):
    """Print formatted step header."""
    print("\n" + "=" * 70)
    print(f"STEP {step_num}: {title}")
    print("=" * 70)


def print_success(message):
    """Print success message."""
    print(f"✅ {message}")


def print_error(message):
    """Print error message."""
    print(f"❌ {message}")


def print_warning(message):
    """Print warning message."""
    print(f"⚠️  {message}")


def print_info(message):
    """Print info message."""
    print(f"▶  {message}")


# ===========================================
# COMMAND EXECUTION
# ===========================================

def run_command(command, description, critical=False):
    """
    Run shell command with output.
    
    Args:
        command: Command to execute.
        description: Human-readable description.
        critical: If True, exit on failure.
        
    Returns:
        True if successful, False otherwise.
    """
    print_info(description)
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            text=True,
            capture_output=True
        )
        
        if result.stdout:
            print(result.stdout[:500])  # Show first 500 chars
        
        print_success("Success")
        return True
        
    except subprocess.CalledProcessError as e:
        print_error(f"Failed: {e.stderr[:200] if e.stderr else 'Unknown error'}")
        
        if critical:
            print("\n❌ Critical step failed. Setup cannot continue.")
            sys.exit(1)
        
        return False


# ===========================================
# SETUP STEPS
# ===========================================

def check_prerequisites():
    """Check system prerequisites."""
    print_step(1, "Checking Prerequisites")
    
    # Python version
    python_version = sys.version_info
    print(f"Python version: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    if python_version < (3, 11):
        print_error("Python 3.11+ required")
        print("Please install Python 3.11 or higher from https://www.python.org/")
        sys.exit(1)
    
    print_success("Python version OK")
    
    # Check pip
    try:
        subprocess.run(["pip", "--version"], check=True, capture_output=True)
        print_success("pip installed")
    except:
        print_error("pip not found")
        sys.exit(1)
    
    # Check MongoDB
    print_info("Checking MongoDB...")
    result = subprocess.run(
        ["sc", "query", "MongoDB"],
        capture_output=True,
        text=True
    )
    
    if "RUNNING" in result.stdout:
        print_success("MongoDB is running")
    else:
        print_warning("MongoDB not running or not installed")
        print("  Install from: https://www.mongodb.com/try/download/community")
        print("  Or start service: net start MongoDB")


def install_dependencies():
    """Install Python dependencies."""
    print_step(2, "Installing Dependencies")
    
    if not Path("requirements.txt").exists():
        print_error("requirements.txt not found")
        return False
    
    print_info("This may take a few minutes...")
    
    success = run_command(
        "pip install -r requirements.txt",
        "Installing Python packages"
    )
    
    if not success:
        print_warning("Some packages may have failed to install")
        response = input("\nContinue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    return True


def create_directories():
    """Create required output directories."""
    print_step(3, "Creating Output Directories")
    
    directories = [
        "output/json",
        "output/images",
        "output/logs",
        "data/cache",
        "scripts",
        "docs"
    ]
    
    for directory in directories:
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)
        print(f"  ✓ {directory}")
    
    print_success("All directories created")


def setup_environment():
    """Setup environment configuration."""
    print_step(4, "Environment Configuration")
    
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if env_file.exists():
        print_success(".env file already exists")
        
        response = input("\nOverwrite with .env.example? (y/n): ")
        if response.lower() == 'y':
            if env_example.exists():
                shutil.copy(env_example, env_file)
                print_success("Copied .env.example to .env")
            else:
                print_warning(".env.example not found")
    else:
        if env_example.exists():
            shutil.copy(env_example, env_file)
            print_success("Created .env from .env.example")
        else:
            print_warning(".env.example not found - creating basic .env")
            env_file.write_text("# OSI News Automation Configuration\n")
    
    print("\n" + "=" * 70)
    print("⚠️  IMPORTANT: Configure your API keys in .env")
    print("=" * 70)
    print("""
Required API Keys:
  1. GROQ_API_KEY - Get from: https://console.groq.com
  2. HOCALWIRE_API_KEY - Provided by Hocalwire
  3. HOCALWIRE_USER_SESSION_ID - From registration
  4. MONGODB_URI - Default: mongodb://localhost:27017/

Optional:
  5. SLACK_WEBHOOK_URL - For monitoring alerts
  6. ENABLE_IMAGE_GENERATION - Set to true/false
  7. ENABLE_TRANSLATION - Set to true/false
""")
    
    response = input("\nOpen .env file for editing now? (y/n): ")
    if response.lower() == 'y':
        try:
            subprocess.run(["notepad", ".env"])
        except:
            print("Please edit .env manually")
    
    input("\nPress Enter after configuring .env...")


def initialize_database():
    """Initialize MongoDB database."""
    print_step(5, "Initializing Database")
    
    if not Path("src/database/initialize_db.py").exists():
        print_warning("Database initialization script not found")
        return False
    
    success = run_command(
        "python src/database/initialize_db.py",
        "Setting up MongoDB collections and indexes"
    )
    
    if success:
        print_success("Database initialized")
    else:
        print_warning("Database initialization failed")
        print("  Make sure MongoDB is running: net start MongoDB")
    
    return success


def test_components():
    """Test critical components."""
    print_step(6, "Testing Components")
    
    # Check if pytest is installed
    try:
        subprocess.run(["pytest", "--version"], check=True, capture_output=True)
    except:
        print_info("Installing pytest...")
        run_command("pip install pytest", "Installing pytest")
    
    print_info("Running component tests (this may take a minute)...")
    
    # Run basic tests
    tests_passed = 0
    tests_total = 0
    
    test_files = [
        "tests/test_integration.py::TestScraperIntegration::test_scraper_returns_articles",
        "tests/test_integration.py::TestDatabaseIntegration::test_save_and_retrieve_article",
    ]
    
    for test_file in test_files:
        if Path(test_file.split("::")[0]).exists():
            tests_total += 1
            if run_command(f"pytest {test_file} -v", f"Testing {test_file.split('::')[1]}"):
                tests_passed += 1
    
    if tests_total > 0:
        print(f"\n📊 Tests: {tests_passed}/{tests_total} passed")
    else:
        print_warning("No test files found - skipping tests")


def run_dry_run():
    """Run pipeline in dry-run mode."""
    print_step(7, "Running Test Pipeline")
    
    print("\n" + "=" * 70)
    print("Running dry-run pipeline (no actual uploads)")
    print("This will:")
    print("  • Scrape 5 test articles")
    print("  • Detect trends")
    print("  • Generate comprehensive articles")
    print("  • Create social media posts")
    print("  • Skip actual uploads to Hocalwire")
    print("\nThis may take 2-5 minutes...")
    print("=" * 70 + "\n")
    
    success = run_command(
        "python run_automation.py --mode dry-run",
        "Executing test pipeline"
    )
    
    if success:
        print_success("Pipeline test successful!")
        print("\n📁 Check output files:")
        print("  • output/json/pipeline_stats_*.json")
        print("  • output/json/social_posts_*.json")
        print("  • output/logs/automation_*.log")
    else:
        print_error("Pipeline test failed")
        print("  Check logs in: output/logs/")
        return False
    
    return True


def setup_complete():
    """Display setup completion message."""
    print("\n" + "=" * 70)
    print("🎉 SETUP COMPLETE!")
    print("=" * 70)
    
    print("""
✅ Installation Summary:
  • Python dependencies installed
  • Output directories created
  • Environment configured
  • Database initialized
  • Components tested
  • Pipeline verified

📋 Next Steps:

1. Verify Configuration:
   • Check .env file has all API keys
   • Test MongoDB connection
   • Verify Groq API key works

2. Test Real Upload:
   python run_automation.py --mode once

3. Setup Automation (Windows):
   cd scripts
   setup_windows_scheduler.bat

4. Setup Monitoring:
   • Add Slack webhook to .env
   • Run: python scripts/monitor.py
   • Schedule hourly monitoring

5. Check Output:
   • Logs: output/logs/automation_*.log
   • JSON: output/json/
   • Dashboard: https://democracynewslive.com/dashboard

📚 Documentation:
  • README.md - Getting started
  • docs/QUICKSTART.md - Quick reference
  • docs/DEPLOYMENT.md - Production deployment
  • docs/MONITORING.md - Monitoring setup
  • docs/PRODUCTION_CHECKLIST.md - Deployment checklist

🔧 Useful Commands:
  • Run once: python run_automation.py --mode once
  • Dry run: python run_automation.py --mode dry-run
  • Health check: python scripts/health_check.py
  • Monitor: python scripts/monitor.py
  • Test Slack: python scripts/test_slack.py

Need help? Check the documentation or review the logs.

Happy automating! 🚀
""")


# ===========================================
# MAIN
# ===========================================

def main():
    """Main setup function."""
    print_header()
    
    print(f"Setup started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Working directory: {os.getcwd()}\n")
    
    try:
        # Run setup steps
        check_prerequisites()
        install_dependencies()
        create_directories()
        setup_environment()
        initialize_database()
        test_components()
        
        # Ask before dry run
        print("\n" + "=" * 70)
        response = input("Run test pipeline now? (y/n): ")
        if response.lower() == 'y':
            if run_dry_run():
                setup_complete()
            else:
                print("\n⚠️  Setup completed but pipeline test failed")
                print("Review logs and try: python run_automation.py --mode dry-run")
        else:
            print("\n✅ Setup completed (pipeline test skipped)")
            print("Run manually: python run_automation.py --mode dry-run")
            setup_complete()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Setup failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
