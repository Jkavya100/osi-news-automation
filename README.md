# OSI News Automation System

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)](https://github.com/Jkavya100/osi-news-automation)

An intelligent, fully automated news aggregation and publishing system that scrapes global news sources, detects trending topics, generates comprehensive articles using LLMs, creates AI-generated images, translates content into multiple languages, and automatically publishes to Hocalwire CMS.

---

## 🚀 Features

### Core Capabilities
- **🌐 Multi-Source Web Scraping**: Automatically scrapes news from 20+ global sources
- **📊 Trend Detection**: AI-powered trend analysis to identify breaking stories
- **✍️ AI Article Generation**: Uses Groq LLM (Llama 3.3 70B) to create comprehensive news articles
- **🎨 AI Image Generation**: Creates contextual images using Stable Diffusion
- **🌍 Multi-Language Translation**: Translates articles to Hindi, Spanish, French, and Arabic
- **📤 Automatic Publishing**: Direct upload to Hocalwire CMS (democracynewslive.com)
- **🔄 Failed Upload Retry Queue**: Automatically retries failed uploads when network returns
- **⏰ Scheduled Automation**: Run hourly, daily, or on custom schedules
- **💾 MongoDB Integration**: Persistent storage with duplicate detection
- **📊 Beautiful Web Dashboard**: View and manage generated articles

### Advanced Features
- Smart location extraction and categorization
- Exponential backoff retry mechanism
- Semantic duplicate detection using embeddings
- Session-based scraping with comprehensive logging
- Social media post generation (Twitter, LinkedIn, Instagram, Facebook)

---

## 📋 Prerequisites

### Required Software
- **Python 3.11 or higher** ([Download](https://www.python.org/downloads/))
- **MongoDB** (Local or Atlas) ([Download](https://www.mongodb.com/try/download/community))
- **Git** ([Download](https://git-scm.com/downloads))

### API Keys (Required)
- **Groq API Key** (Free): [Get from Groq Console](https://console.groq.com/)
- **Hocalwire API Key**: Provided by Hocalwire platform
- **Cloudinary Account** (Optional, for image hosting): [Sign up](https://cloudinary.com/)

### Optional (for full features)
- Social media API keys (Twitter, LinkedIn, Instagram, Facebook)

---

## 🛠️ Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/Jkavya100/osi-news-automation.git
cd osi-news-automation
```

### Step 2: Set Up Python Environment

#### On Windows:
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate

# Upgrade pip
python -m pip install --upgrade pip
```

#### On macOS/Linux:
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

### Step 3: Install Dependencies

```bash
# Install all required packages
pip install -r requirements.txt
```

**Note for Mac users with Apple Silicon (M1/M2/M3):**
```bash
# If you encounter issues with torch, use:
pip install torch torchvision torchaudio

# For accelerate issues:
pip install --upgrade accelerate
```

### Step 4: Install MongoDB

#### On Windows:
1. Download MongoDB Community Server from [mongodb.com](https://www.mongodb.com/try/download/community)
2. Run the installer (default settings work fine)
3. MongoDB will run as a Windows Service automatically

#### On macOS:
```bash
# Using Homebrew
brew tap mongodb/brew
brew install mongodb-community

# Start MongoDB
brew services start mongodb-community
```

#### On Linux (Ubuntu/Debian):
```bash
# Import MongoDB GPG key
wget -qO - https://www.mongodb.org/static/pgp/server-6.0.asc | sudo apt-key add -

# Add MongoDB repository
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/6.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-6.0.list

# Install MongoDB
sudo apt-get update
sudo apt-get install -y mongodb-org

# Start MongoDB
sudo systemctl start mongod
sudo systemctl enable mongod
```

### Step 5: Configure Environment Variables

1. **Copy the example environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` file with your credentials:**
   ```bash
   # On Windows
   notepad .env
   
   # On macOS
   open -e .env
   
   # On Linux
   nano .env
   ```

3. **Required Variables (minimum for basic operation):**
   ```bash
   # Groq API (Required - Get from https://console.groq.com/)
   GROQ_API_KEY=your_actual_groq_key_here
   
   # Hocalwire CMS
   HOCALWIRE_API_KEY=your_hocalwire_api_key
   HOCALWIRE_API_URL=https://democracynewslive.com/dev/h-api/createFeedV2
   
   # MongoDB (Local)
   MONGODB_LOCAL_URI=mongodb://localhost:27017/
   MONGODB_DATABASE=osi_news_automation
   
   # Scheduling
   SCRAPING_INTERVAL_HOURS=1
   TOP_TRENDS_COUNT=5
   
   # Retry Queue
   RETRY_FAILED_UPLOADS_ENABLED=true
   RETRY_INTERVAL_MINUTES=30
   MAX_GLOBAL_UPLOAD_RETRIES=10
   ```

4. **Optional but Recommended:**
   ```bash
   # Cloudinary (for image hosting)
   CLOUDINARY_CLOUD_NAME=your_cloud_name
   CLOUDINARY_API_KEY=your_api_key
   CLOUDINARY_API_SECRET=your_api_secret
   
   # Enable Advanced Features
   ENABLE_IMAGE_GENERATION=true
   ENABLE_TRANSLATION=true
   ENABLE_SOCIAL_POSTING=false
   ```

### Step 6: Initialize the Database

The database will be automatically created on first run, but you can verify the connection:

```bash
python -c "from src.database.mongo_client import get_client; db = get_client(); print('✅ Database connected successfully!')"
```

---

## 🎯 Usage

### Option 1: Run Once (Manual Mode)

Generate and publish articles immediately:

```bash
python run_automation.py --mode once
```

### Option 2: Scheduled Mode (Recommended)

Run automatically every hour:

```bash
python run_automation.py --mode scheduled
```

This will:
- Run the main pipeline every hour (configurable via `SCRAPING_INTERVAL_HOURS`)
- Run the retry queue every 30 minutes to retry failed uploads
- Continue running until you press `Ctrl+C`

### Option 3: Dry Run (Testing)

Test the pipeline without actually uploading:

```bash
python run_automation.py --mode dry-run
```

### View Generated Articles Dashboard

Start the web dashboard to view your generated articles:

```bash
# Navigate to frontend directory
cd src/frontend

# Start the Flask server
python app.py
```

Then open your browser to: `http://localhost:5000`

---

## 🔧 Additional Tools

### Retry Failed Uploads

If articles failed to upload (e.g., network issue), you can manually retry:

```bash
# View retry queue status
python retry_uploads.py --status

# Retry all failed uploads
python retry_uploads.py

# Retry specific article by ID
python retry_uploads.py --article-id <mongodb-id>

# Test mode
python retry_uploads.py --dry-run
```

### Health Check

Monitor system status:

```bash
python scripts/health_check.py
```

---

## 📁 Project Structure

```
osi-news-automation/
├── src/
│   ├── api_integrations/       # Hocalwire, social media APIs
│   │   ├── hocalwire_uploader.py
│   │   ├── retry_failed_uploads.py
│   │   └── social_media_poster.py
│   ├── content_generation/     # AI article generation
│   │   └── article_generator.py
│   ├── database/               # MongoDB integration
│   │   └── mongo_client.py
│   ├── frontend/               # Web dashboard
│   │   ├── app.py
│   │   ├── templates/
│   │   └── static/
│   ├── image_generation/       # AI image creation
│   │   └── image_creator.py
│   ├── scrapers/               # Web scraping modules
│   │   └── batch_scraper.py
│   ├── translation/            # Multi-language support
│   │   └── translator.py
│   └── trend_detection/        # Trend analysis
│       └── trend_analyzer.py
├── config/
│   └── production.env          # Production config template
├── scripts/
│   └── health_check.py         # System health monitoring
├── output/
│   ├── images/                 # Generated images
│   ├── logs/                   # System logs
│   └── json/                   # Pipeline statistics
├── run_automation.py           # Main pipeline orchestrator
├── retry_uploads.py            # Failed upload retry tool
├── requirements.txt            # Python dependencies
├── .env.example                # Environment template
└── README.md                   # This file
```

---

## ⚙️ Configuration Reference

### Main Pipeline Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `SCRAPING_INTERVAL_HOURS` | `3` | How often to run the scraper |
| `TOP_TRENDS_COUNT` | `5` | Number of articles to generate per run |
| `MAX_ARTICLES_PER_RUN` | `50` | Maximum articles to scrape |
| `ARTICLE_MIN_WORDS` | `800` | Minimum words per generated article |
| `ARTICLE_MAX_WORDS` | `1200` | Maximum words per generated article |

### Retry Queue Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `RETRY_FAILED_UPLOADS_ENABLED` | `true` | Enable automatic retry |
| `RETRY_INTERVAL_MINUTES` | `30` | Retry check interval |
| `MAX_GLOBAL_UPLOAD_RETRIES` | `10` | Max retry attempts |
| `RETRY_BATCH_SIZE` | `20` | Articles per retry run |

### Feature Flags

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_TREND_DETECTION` | `true` | Enable trend analysis |
| `ENABLE_ARTICLE_GENERATION` | `true` | Enable AI article generation |
| `ENABLE_IMAGE_GENERATION` | `false` | Enable AI image creation |
| `ENABLE_TRANSLATION` | `false` | Enable multi-language translation |
| `ENABLE_HOCALWIRE_UPLOAD` | `true` | Enable Hocalwire publishing |

---

## 🐛 Troubleshooting

### Issue: MongoDB Connection Failed

**Solution:**
```bash
# Check if MongoDB is running
# Windows:
sc query MongoDB

# macOS:
brew services list | grep mongodb

# Linux:
sudo systemctl status mongod

# If not running, start it:
# Windows: Start the "MongoDB" service in Services
# macOS: brew services start mongodb-community
# Linux: sudo systemctl start mongod
```

### Issue: Groq API Rate Limit

**Solution:**
- Groq free tier has limits. Wait a few minutes or upgrade your plan
- Check your usage at: https://console.groq.com/

### Issue: Image Generation Fails or Too Slow

**Solution:**
```bash
# Disable image generation in .env
ENABLE_IMAGE_GENERATION=false

# Or use faster settings
IMAGE_INFERENCE_STEPS=20  # Default is 30
```

### Issue: Module Import Errors

**Solution:**
```bash
# Ensure you're in the virtual environment
# You should see (venv) in your terminal prompt

# Reinstall dependencies
pip install --upgrade -r requirements.txt
```

### Issue: Permission Denied (Mac/Linux)

**Solution:**
```bash
# Make scripts executable
chmod +x run_automation.py
chmod +x retry_uploads.py

# Or run with python explicitly
python run_automation.py --mode once
```

---

## 📊 Monitoring & Logs

### View Logs

```bash
# Latest log file
tail -f output/logs/automation_2026-01-27.log

# On Windows (PowerShell)
Get-Content output/logs/automation_2026-01-27.log -Wait
```

### Check Pipeline Stats

```bash
# View latest pipeline statistics
cat output/json/pipeline_stats_*.json | tail -n 50
```

### Monitor Database

```python
from src.database.mongo_client import get_client

db = get_client()
stats = db.get_statistics()
print(stats)
```

---

## 🚀 Production Deployment

### Running as a Background Service

#### On Windows (Task Scheduler):
1. Open Task Scheduler
2. Create Basic Task
3. Trigger: At startup
4. Action: Start a program
5. Program: `C:\path\to\venv\Scripts\python.exe`
6. Arguments: `C:\path\to\run_automation.py --mode scheduled`

#### On macOS (launchd):
```bash
# Create a plist file
nano ~/Library/LaunchAgents/com.osi.newsautomation.plist
```

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.osi.newsautomation</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/venv/bin/python</string>
        <string>/path/to/run_automation.py</string>
        <string>--mode</string>
        <string>scheduled</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

```bash
# Load the service
launchctl load ~/Library/LaunchAgents/com.osi.newsautomation.plist
```

#### On Linux (systemd):
```bash
# Create service file
sudo nano /etc/systemd/system/osi-news.service
```

```ini
[Unit]
Description=OSI News Automation System
After=network.target mongod.service

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/osi-news-automation
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/python run_automation.py --mode scheduled
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
sudo systemctl enable osi-news
sudo systemctl start osi-news

# Check status
sudo systemctl status osi-news
```

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 🙏 Acknowledgments

- **Groq** for providing free LLM API access
- **Hocalwire** for the CMS platform
- **Stability AI** for Stable Diffusion models
- **MongoDB** for the database solution

---

## 📞 Support

For issues, questions, or suggestions:
- Create an issue on [GitHub](https://github.com/Jkavya100/osi-news-automation/issues)
- Check the [Troubleshooting](#-troubleshooting) section
- Review logs in `output/logs/`

---

## 🔄 Version History

- **v1.0.0** (2026-01-27)
  - Initial release
  - Core pipeline with scraping, generation, and publishing
  - Failed upload retry queue
  - Multi-language translation
  - AI image generation
  - Web dashboard

---

**Made with ❤️ for automated news generation**
