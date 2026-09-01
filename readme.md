# ⚡ Telegram Auto-Accept Join Request Bot

An asynchronous, high-performance Telegram Bot built with `python-telegram-bot` and `aiosqlite` that **automatically approves join requests** for Telegram channels and supergroups in real-time. It features personalized welcome direct messages, live analytics, an interactive admin dashboard, and broadcast tools.

---

## ✨ Key Features

- ⚡ **Instant Auto-Approval**: Approves incoming channel and group join requests in milliseconds.
- 🔒 **Global Force Subscription**: Require users to join one or multiple official update channels before accessing the bot, with instant in-bot verification buttons.
- 💌 **Customizable Welcome DMs**: Sends a personalized direct message to users upon acceptance with dynamic placeholders.
- 🎛️ **Granular Controls**: Enable or disable auto-approval and welcome messages individually per channel.
- 📊 **Real-Time Analytics**: Track total approvals, daily approvals, connected channels, and registered users.
- 📢 **Broadcast Engine**: Broadcast updates or announcements to all users with live delivery progress and rate-limiting protection.
- 🛠️ **Interactive UI / UX**: Rich inline buttons, paginated channel settings, and guided in-bot setup tutorials.
- 🗄️ **Persistent Storage**: Built-in async SQLite database storing channels, users, settings, and request logs.

---

## 📋 Bot Commands

| Command | Description | Access |
|---|---|---|
| `/start` | Welcome screen & main interactive menu | Everyone |
| `/help` | Guided tutorial on bot setup and permissions | Everyone |
| `/channels` | View connected channels and configure settings | Everyone / Admins |
| `/about` | Information about bot version and engine | Everyone |
| `/stats` | Live performance analytics & metrics | Admin / Everyone |
| `/admin` | Admin dashboard & control center | Admin Only |
| `/broadcast` | Broadcast message to all registered users | Admin Only |
| `/cancel` | Cancel current conversation/action | Everyone |

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python **3.10+** (Python 3.10, 3.11, 3.12, 3.13, or 3.14)
- A Telegram Bot Token from [@BotFather](https://t.me/BotFather)

### 2. Installation

1. Clone or open the repository folder:
   ```bash
   cd "Telegram Auto Accept Bot"
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create your `.env` configuration file from the template:
   ```bash
   # On Windows (cmd/PowerShell)
   copy .env.example .env

   # On Linux/macOS
   cp .env.example .env
   ```

4. Open `.env` and fill in your details:
   ```env
   BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
   ADMIN_IDS=123456789

   # Optional: MongoDB URI (if unset, SQLite will be used automatically)
   MONGO_URI=mongodb+srv://<user>:<password>@cluster0.mongodb.net/?retryWrites=true&w=majority
   DATABASE_NAME=telegram_auto_accept_bot
   ```
   > 💡 **Tip:** You can find your Telegram User ID using [@userinfobot](https://t.me/userinfobot) or [@raw_data_bot](https://t.me/raw_data_bot).

### 3. Run the Bot

**Production Mode:**
```bash
python main.py
```

**Development Mode (Auto-Restart / Hot Reload on code changes):**
```bash
# Using watchfiles (Python equivalent of npm run dev / nodemon)
python -m watchfiles --filter python "python main.py" .

# Or using nodemon (if you have Node.js installed)
npx nodemon --exec python main.py -e py,env
```

---

## 📖 Channel & Group Setup Guide

To enable the bot to automatically accept requests in your channel or group:

### Step 1: Add the Bot as an Administrator
1. Open your Channel or Group info page in Telegram.
2. Go to **Settings** ➔ **Administrators** ➔ **Add Administrator**.
3. Search for your bot's username and add it.
4. Ensure the following permissions are enabled:
   - ✅ **Invite Users via Link** (or *Add Members*)
   - ✅ **Manage Join Requests**

### Step 2: Create a Join Request Invite Link
1. Go to your Channel/Group **Settings** ➔ **Invite Links**.
2. Tap **Create a New Link**.
3. Turn **ON** the option: **"Request Admin Approval"** (or *"Approve New Members"*).
4. Copy and share this invite link.

Whenever anyone opens this link and requests to join, the bot will approve them immediately and send them a welcome DM!

---

## 💬 Welcome Message Customization

You can customize the direct message sent to new members using placeholders, images/media, and interactive inline buttons.

### 1. Supported Placeholders

| Placeholder | Replaced With | Example |
|---|---|---|
| `{name}` | User's full name | `Alex Smith` |
| `{first_name}` | User's first name | `Alex` |
| `{username}` | User's `@username` (or first name) | `@alexsmith` |
| `{mention}` | Clickable Telegram mention link | [Alex](tg://user?id=12345) |
| `{chat_title}` | Name of the channel/group | `Crypto VIP Club` |
| `{user_id}` | Telegram user ID | `123456789` |

---

### 2. Attaching Images / GIFs / Videos

To attach a welcome image:
1. Go to `/channels` and select your channel.
2. Click **"✏️ Set Custom Welcome DM"**.
3. **Send a Photo, GIF, or Video** directly to the bot in Telegram.
4. Put your welcome text and buttons in the **Caption**!

---

### 3. Adding Custom Inline Buttons

You can attach clickable URL buttons by adding button syntax anywhere in your message or photo caption:

#### Single Button (1 per row):
```text
[👉 Join VIP Channel - https://t.me/yourvipchannel]
[🌐 Official Website - https://example.com]
```

#### Multiple Buttons (in the same row):
```text
[🌐 Website - https://mysite.com | 💬 Support - https://t.me/support]
```
or
```text
[🌐 Website - https://mysite.com][💬 Support - https://t.me/support]
```

#### Complete Welcome Message Example with Image & Buttons:
```text
👋 Welcome {name} to *{chat_title}*!

🎉 Your request has been approved. Make sure to check our official resources below:

[🚀 VIP Access - https://t.me/yourvipchannel]
[🌐 Website - https://example.com | 💬 Support - https://t.me/support]
```

---

## ⚡ Approving Past / Backlog Join Requests

The bot has a built-in hybrid engine to approve **past/pending requests** that accumulated before the bot was added or while the bot was offline.

### How to Use Backlog Approval:
1. In Telegram, go to `/channels` and select your channel.
2. Click **`[ ⚡ Approve All Pending Requests ]`**.
3. Confirm by clicking **`[ ⚡ Yes, Approve All Requests ]`**.
4. The bot will approve all backlog members with real-time live progress updates!

### (Optional) 2-Minute MTProto Setup for Backlog Engine:
1. Get your free `API_ID` & `API_HASH` from [my.telegram.org](https://my.telegram.org).
2. Generate your string session by running:
   ```bash
   python services/session_generator.py
   ```
3. Copy the generated `SESSION_STRING` into your `.env` file:
   ```env
   TELEGRAM_API_ID=12345678
   TELEGRAM_API_HASH=your_api_hash_here
   SESSION_STRING=your_generated_session_string_here
   ```
4. Restart the bot (`python main.py`).

---

## 📁 Project Structure

```text
Telegram Auto Accept Bot/
├── .env.example              # Environment variables template
├── requirements.txt          # Python dependencies
├── main.py                   # Main bot entry point & handler registry
├── config.py                 # Environment parser and logging setup
├── test_bot.py               # Unit tests
├── database/
│   ├── __init__.py
│   └── db.py                 # Dual database engine (MongoDB + SQLite fallback)
├── handlers/
│   ├── __init__.py
│   ├── join_request.py       # Live ChatJoinRequest approval & welcome DM logic
│   ├── user.py               # /start, /help, /about & user callbacks
│   └── admin.py              # /admin, /stats, /channels, /broadcast, backlog approvals
├── keyboards/
│   ├── __init__.py
│   └── inline.py             # Inline keyboard menus & layout builders
├── services/
│   ├── __init__.py
│   ├── backlog_cleaner.py    # MTProto batch & backlog request approvals
│   └── session_generator.py  # Interactive string session helper
└── utils/
    ├── __init__.py
    ├── force_sub.py          # Force subscription verification & join keyboard builder
    └── helpers.py            # String template formatters & button parser

```

---

## 🛡️ Running as a 24/7 Background Service (Linux / VPS)

To keep the bot running permanently on a Linux VPS, you can use `systemd`:

1. Create a service file:
   ```bash
   sudo nano /etc/systemd/system/telegram-autoaccept.service
   ```

2. Paste the following configuration (adjust paths and user):
   ```ini
   [Unit]
   Description=Telegram Auto Accept Bot
   After=network.target

   [Service]
   Type=simple
   User=ubuntu
   WorkingDirectory=/home/ubuntu/Telegram-Auto-Accept-Bot
   ExecStart=/usr/bin/python3 /home/ubuntu/Telegram-Auto-Accept-Bot/main.py
   Restart=always
   RestartSec=5

   [Install]
   WantedBy=multi-user.target
   ```

3. Enable and start the service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable telegram-autoaccept
   sudo systemctl start telegram-autoaccept
   ```

4. Check status:
   ```bash
   sudo systemctl status telegram-autoaccept
   ```