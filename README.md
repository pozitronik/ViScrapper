# VIParser - Product Management & Web Scraping Tool

**📖 Documentation Languages:** [English](README.md) | [Русский](README_RU.md)

VIParser is a comprehensive product management system that helps you scrape product information from websites, manage your product catalog, and automatically post to Telegram channels. It consists of a web-based backend service and a Chrome browser extension for easy product scraping.

## 📋 Table of Contents

- [What VIParser Does](#what-viparser-does)
- [System Requirements](#system-requirements)
- [Installation Guide](#installation-guide)
  - [Step 1: Install Python](#step-1-install-python)
  - [Step 2: Download and Setup VIParser](#step-2-download-and-setup-viparser)
  - [Step 3: Install Chrome Extension](#step-3-install-chrome-extension)
  - [Step 4: Setup Telegram Bot (Optional)](#step-4-setup-telegram-bot-optional)
- [First Time Setup](#first-time-setup)
- [How to Use VIParser](#how-to-use-viparser)
- [Troubleshooting](#troubleshooting)
- [Advanced Configuration](#advanced-configuration)
- [Support](#support)

## 🎯 What VIParser Does

VIParser helps you:

- **📱 Scrape Products**: Extract product information from websites with one click
- **🗂️ Manage Catalog**: Organize your products in a searchable, filterable table
- **📸 Download Images**: Automatically download and store product images
- **📤 Telegram Integration**: Post products to your Telegram channels automatically
- **📊 Export Data**: Export your product data for use in other applications
- **🔍 Search & Filter**: Find products quickly with powerful search and filtering
- **📝 Templates**: Create custom message templates for Telegram posts

## 💻 System Requirements

- **Operating System**: Windows 10/11, macOS 10.14+, or Linux Ubuntu 18.04+
- **Browser**: Google Chrome or Microsoft Edge (for the extension)
- **Internet Connection**: Required for product scraping and Telegram features
- **Disk Space**: At least 1GB free space (more if you scrape many products with images)

## 🚀 Installation Guide

### Step 1: Install Python

VIParser requires Python 3.8 or newer. Follow the instructions for your operating system:

#### Windows Users:

1. **Download Python**:
   - Go to [python.org/downloads](https://www.python.org/downloads/)
   - Click the yellow "Download Python" button (it will show the latest version)
   - Download the file (it will be named something like `python-3.11.x-amd64.exe`)

2. **Install Python**:
   - Double-click the downloaded file
   - **⚠️ IMPORTANT**: Check the box "Add Python to PATH" at the bottom
   - Click "Install Now"
   - Wait for installation to complete
   - Click "Close"

3. **Verify Installation**:
   - Press `Windows + R`, type `cmd`, and press Enter
   - Type `python --version` and press Enter
   - You should see something like "Python 3.11.x"
   - If you see an error, restart your computer and try again

#### macOS Users:

1. **Download Python**:
   - Go to [python.org/downloads](https://www.python.org/downloads/)
   - Click "Download Python" for macOS
   - Download the `.pkg` file

2. **Install Python**:
   - Double-click the downloaded `.pkg` file
   - Follow the installation wizard
   - Enter your password when prompted

3. **Verify Installation**:
   - Open Terminal (press `Cmd + Space`, type "Terminal", press Enter)
   - Type `python3 --version` and press Enter
   - You should see something like "Python 3.11.x"

#### Linux Users:

Most Linux distributions come with Python pre-installed. To check and install if needed:

```bash
# Check if Python 3.8+ is installed
python3 --version

# If not installed or version is too old, install Python:
# Ubuntu/Debian:
sudo apt update
sudo apt install python3 python3-pip python3-venv

# CentOS/RHEL/Fedora:
sudo yum install python3 python3-pip
# or on newer versions:
sudo dnf install python3 python3-pip
```

### Step 2: Download and Setup VIParser

#### Option A: Download from GitHub (Recommended)

1. **Download VIParser**:
   - Go to the VIParser GitHub repository
   - Click the green "Code" button
   - Click "Download ZIP"
   - Save the file to your Desktop or Downloads folder

2. **Extract Files**:
   - Right-click the downloaded ZIP file
   - Select "Extract All" (Windows) or double-click (macOS/Linux)
   - Choose a location like `C:\VIParser` (Windows) or `/home/username/VIParser` (Linux/macOS)
   - Remember this location - you'll need it later!

#### Option B: Clone with Git (Advanced Users)

If you have Git installed:
```bash
git clone <repository-url>
cd viparser
```

#### Setup the Backend Service

1. **Open Command Prompt/Terminal**:
   - **Windows**: Press `Windows + R`, type `cmd`, press Enter
   - **macOS**: Press `Cmd + Space`, type "Terminal", press Enter
   - **Linux**: Press `Ctrl + Alt + T`

2. **Navigate to VIParser folder**:
   ```bash
   # Replace with your actual path
   cd C:\VIParser\backend          # Windows
   cd /path/to/VIParser/backend    # macOS/Linux
   ```

3. **Create Virtual Environment**:
   ```bash
   # Windows:
   python -m venv venv
   
   # macOS/Linux:
   python3 -m venv venv
   ```

4. **Activate Virtual Environment**:
   ```bash
   # Windows:
   venv\Scripts\activate
   
   # macOS/Linux:
   source venv/bin/activate
   ```
   
   You should see `(venv)` at the beginning of your command prompt.

5. **Install Required Packages**:
   ```bash
   pip install -r requirements.txt
   ```
   
   This will take a few minutes. You'll see many packages being installed.

6. **Create Configuration File**:
   - In the `backend` folder, copy the file `.env.example` to `.env`
   - **Windows**: Right-click `.env.example` → Copy, then right-click in folder → Paste, rename to `.env`
   - **macOS/Linux**: `cp .env.example .env`

7. **Start VIParser**:
   ```bash
   python main.py
   ```
   
   You should see:
   ```
   INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
   ```

8. **Test Installation**:
   - Open your web browser
   - Go to `http://localhost:8000`
   - You should see the VIParser interface
   - If it works, press `Ctrl+C` in the command prompt to stop the server

### Step 3: Install Chrome Extension

1. **Prepare Extension Files**:
   - Navigate to the `chrome-extension` folder in your VIParser directory
   - This folder contains the extension files

2. **Open Chrome Extensions Page**:
   - Open Google Chrome
   - Type `chrome://extensions/` in the address bar and press Enter
   - Or go to Menu (⋮) → More Tools → Extensions

3. **Enable Developer Mode**:
   - In the top-right corner, toggle "Developer mode" to ON
   - New buttons will appear

4. **Install Extension**:
   - Click "Load unpacked"
   - Navigate to and select the `chrome-extension` folder from your VIParser directory
   - Click "Select Folder" (Windows) or "Open" (macOS)

5. **Verify Installation**:
   - You should see "VIParser" in your extensions list
   - The VIParser icon should appear in your Chrome toolbar
   - If you don't see the icon, click the puzzle piece (🧩) in the toolbar and pin VIParser

### Step 4: Setup Telegram Bot (Optional)

If you want to post products to Telegram channels, you need to create a Telegram bot:

#### Create a Telegram Bot

1. **Start BotFather**:
   - Open Telegram on your phone or computer
   - Search for `@BotFather` (official Telegram bot)
   - Start a chat with BotFather

2. **Create New Bot**:
   - Send `/newbot` to BotFather
   - Choose a name for your bot (e.g., "My Store Bot")
   - Choose a username for your bot (must end with 'bot', e.g., "mystoreproducts_bot")

3. **Get Bot Token**:
   - BotFather will give you a token that looks like: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`
   - **⚠️ IMPORTANT**: Keep this token secret! Don't share it with anyone.

4. **Configure VIParser**:
   - Open the `.env` file in your `backend` folder with a text editor (Notepad on Windows, TextEdit on macOS)
   - Find the line `TELEGRAM_BOT_TOKEN=`
   - Add your token after the equals sign: `TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`
   - Save the file

#### Setup Telegram Channel

1. **Create Channel** (if you don't have one):
   - In Telegram, tap the pencil icon → "New Channel"
   - Choose "Public Channel" for easier setup
   - Set a username for your channel (e.g., @mystoreproducts)

2. **Add Bot to Channel**:
   - Go to your channel settings
   - Tap "Administrators" → "Add Admin"
   - Search for your bot's username
   - Add the bot and give it permission to "Post Messages"

3. **Get Channel ID**:
   - For public channels, use: `@yourchannelusername`
   - For private channels, you'll need the numeric ID (advanced topic)

## 🎉 First Time Setup

### 1. Start VIParser Backend

Every time you want to use VIParser:

1. **Open Command Prompt/Terminal**
2. **Navigate to backend folder**:
   ```bash
   cd C:\VIParser\backend          # Windows
   cd /path/to/VIParser/backend    # macOS/Linux
   ```
3. **Activate virtual environment**:
   ```bash
   # Windows:
   venv\Scripts\activate
   
   # macOS/Linux:
   source venv/bin/activate
   ```
4. **Start the server**:
   ```bash
   python main.py
   ```
5. **Keep this window open** while using VIParser

### 2. Open VIParser Interface

- Open your web browser
- Go to `http://localhost:8000`
- You should see the VIParser dashboard

### 3. Setup Telegram Channel (Optional)

If you configured Telegram:

1. In VIParser interface, click "📢 Channels"
2. Click "➕ Add Channel"
3. Fill in:
   - **Channel Name**: A friendly name (e.g., "My Store")
   - **Chat ID**: Your channel username (e.g., `@mystoreproducts`)
   - **Description**: Optional description
4. Click "🔧 Test Connection" to verify it works
5. Click "➕ Create Channel"

## 📖 How to Use VIParser

### Scraping Your First Product

1. **Start VIParser Backend** (if not already running)
2. **Visit a Product Page**:
   - Go to any e-commerce website (Amazon, eBay, etc.)
   - Navigate to a specific product page

3. **Use the Extension**:
   - Click the VIParser icon in your Chrome toolbar
   - The extension will automatically detect product information
   - You'll see the product name, SKU, price, etc.
   - Add any comments if needed
   - Click "Scrape Product"

4. **View in Dashboard**:
   - Go to `http://localhost:8000` in your browser
   - Your scraped product will appear in the table
   - Images will be automatically downloaded

### Managing Your Products

- **🔍 Search**: Use the search box to find specific products
- **🔽 Filter**: Click "Filters" to filter by price, availability, etc.
- **📊 Sort**: Click column headers to sort the table
- **⚙️ Columns**: Click "Columns" to customize which columns are visible
- **✏️ Edit**: Click on any cell to edit product information inline
- **🗑️ Delete**: Select products and click "Delete Selected"

### Posting to Telegram

1. **Select Products**: Check the boxes next to products you want to post
2. **Click "📤 Post to Telegram"**
3. **Choose Channel**: Select your Telegram channel
4. **Select Template**: Choose a message template or create custom text
5. **Configure Options**: Choose whether to include photos
6. **Click "📤 Send Posts"**

### Creating Message Templates

1. **Click "📝 Templates"** in the main interface
2. **Click "➕ Add Template"**
3. **Fill in**:
   - **Template Name**: A descriptive name
   - **Template Content**: Your message with placeholders like `{name}`, `{price}`, `{sku}`
4. **Click "📋 Show Placeholders"** to see all available placeholders
5. **Click "👁️ Preview"** to test your template
6. **Click "➕ Create Template"**

Example template:
```
🛍️ New Product Alert!

📦 {name}
💰 Price: {price} {currency}
🔖 SKU: {sku}
🎨 Color: {color}
✅ {availability}

🔗 {product_url}
```

## 🔧 Troubleshooting

### Common Issues

#### "Python is not recognized" Error
- **Solution**: Python is not in your PATH. Reinstall Python and make sure to check "Add Python to PATH" during installation.

#### Extension doesn't detect products
- **Solution**: 
  - Make sure VIParser backend is running (`python main.py`)
  - Check that you're on a product page with structured data
  - Try refreshing the page and clicking the extension icon again

#### "Failed to load products" in dashboard
- **Solution**:
  - Make sure VIParser backend is running
  - Check that you're accessing `http://localhost:8000` (not https)
  - Look for error messages in the command prompt where you started VIParser

#### Telegram bot doesn't work
- **Solution**:
  - Verify your bot token is correct in `.env` file
  - Make sure the bot is added as administrator to your channel
  - Test the connection in VIParser channel settings

#### "ModuleNotFoundError" when starting VIParser
- **Solution**:
  - Make sure you activated the virtual environment: `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (macOS/Linux)
  - Reinstall requirements: `pip install -r requirements.txt`

### Getting Help

If you encounter issues:

1. **Check the command prompt/terminal** where VIParser is running for error messages
2. **Browser Console**: Press F12 in your browser and check the "Console" tab for errors
3. **Extension Console**: Right-click the VIParser extension icon → "Inspect popup" → check Console tab

### Performance Tips

- **Close unused browser tabs** when scraping to improve performance
- **Restart VIParser** if it becomes slow: press Ctrl+C and run `python main.py` again
- **Limit concurrent scraping**: Don't scrape too many products at once

## ⚙️ Advanced Configuration

### Environment Variables

Edit the `.env` file in the `backend` folder to customize VIParser:

```env
# Database settings
DATABASE_URL=sqlite:///./viparser.db

# Image storage
IMAGE_DIR=./images

# Telegram integration
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Price calculation
PRICE_MULTIPLIER=1.0

# Backup settings
BACKUP_ENABLED=true
BACKUP_INTERVAL_HOURS=24
BACKUP_MAX_BACKUPS=10

# Development settings
DEBUG=false
LOG_LEVEL=INFO
```

### Port Configuration

If port 8000 is already in use, you can change it:

1. Edit `main.py` in the backend folder
2. Find the line: `uvicorn.run("main:app", host="0.0.0.0", port=8000)`
3. Change `port=8000` to another port like `port=8080`
4. Access VIParser at `http://localhost:8080`

### Database Backup

VIParser automatically creates database backups every 24 hours. Backup files are stored in the `backups` folder.

To manually create a backup:
- Stop VIParser (Ctrl+C)
- Copy the `viparser.db` file to a safe location
- Restart VIParser

## 🆘 Support

### Documentation
- Check this README for common questions
- Look at the `.env.example` file for configuration options

### Reporting Issues
If you find bugs or need help:
1. Check the [Troubleshooting](#troubleshooting) section first
2. Note the exact error message
3. Include your operating system and Python version
4. Describe what you were doing when the error occurred

### Privacy and Security
- VIParser stores all data locally on your computer
- No product data is sent to external servers (except Telegram if you choose to use it)
- Your Telegram bot token is stored locally and not shared
- Images are downloaded and stored on your local machine

---

## 🎯 Quick Start Summary

1. **Install Python** (with "Add to PATH" checked)
2. **Download VIParser** and extract to a folder
3. **Open command prompt** and navigate to `backend` folder
4. **Run these commands**:
   ```bash
   python -m venv venv
   venv\Scripts\activate          # Windows
   source venv/bin/activate       # macOS/Linux
   pip install -r requirements.txt
   python main.py
   ```
5. **Install Chrome extension** from `chrome-extension` folder
6. **Visit** `http://localhost:8000` to use VIParser
7. **Start scraping** products with the Chrome extension!

**🎉 Congratulations! VIParser is now ready to use.**