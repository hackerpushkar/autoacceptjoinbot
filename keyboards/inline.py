from typing import List, Dict, Any, Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, CopyTextButton
from utils.helpers import get_add_to_channel_url, get_add_to_group_url


def get_start_keyboard(bot_username: str, is_user_admin: bool = False) -> InlineKeyboardMarkup:
    """Main start menu keyboard with colorful actions and share button."""
    buttons = [
        [
            InlineKeyboardButton("➕ Add to Channel", url=get_add_to_channel_url(bot_username)),
            InlineKeyboardButton("➕ Add to Group", url=get_add_to_group_url(bot_username))
        ],
        [
            InlineKeyboardButton("📖 Setup Guide", callback_data="nav_help"),
            InlineKeyboardButton("📊 My Channels", callback_data="nav_channels")
        ],
        [
            InlineKeyboardButton(
                "↗️ Share Bot with Friends",
                switch_inline_query=f"Check out @{bot_username} - Fast Telegram Auto-Accept Join Request Bot!"
            )
        ],
        [
            InlineKeyboardButton("ℹ️ About Bot", callback_data="nav_about")
        ]
    ]

    if is_user_admin:
        buttons.append([
            InlineKeyboardButton("⚙️ Admin Control Panel", callback_data="nav_admin_panel")
        ])

    return InlineKeyboardMarkup(buttons)


def get_help_keyboard() -> InlineKeyboardMarkup:
    """Help tutorial keyboard with step-by-step navigation."""
    buttons = [
        [
            InlineKeyboardButton("🔑 Step 1: Admin Permissions", callback_data="help_step_admin"),
            InlineKeyboardButton("🔗 Step 2: Request Link", callback_data="help_step_link")
        ],
        [
            InlineKeyboardButton("💬 Step 3: Custom DM", callback_data="help_step_dm"),
            InlineKeyboardButton("❓ FAQ & Troubleshooting", callback_data="help_step_faq")
        ],
        [
            InlineKeyboardButton("🏠 Back to Main Menu", callback_data="nav_start")
        ]
    ]
    return InlineKeyboardMarkup(buttons)


def get_back_to_help_keyboard() -> InlineKeyboardMarkup:
    """Keyboard to navigate back to help menu."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Setup Guide", callback_data="nav_help")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="nav_start")]
    ])


def get_back_to_start_keyboard() -> InlineKeyboardMarkup:
    """Simple back to main menu keyboard."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Back to Main Menu", callback_data="nav_start")]
    ])


def get_about_keyboard(bot_username: str) -> InlineKeyboardMarkup:
    """About menu keyboard with copy button and More Info action."""
    buttons = [
        [
            InlineKeyboardButton(
                f"📋 Copy Bot Username (@{bot_username})",
                copy_text=CopyTextButton(text=f"@{bot_username}")
            )
        ],
        [
            InlineKeyboardButton("ℹ️ More Info", callback_data="about_more_info")
        ],
        [
            InlineKeyboardButton("🏠 Back to Main Menu", callback_data="nav_start")
        ]
    ]
    return InlineKeyboardMarkup(buttons)


def get_more_info_keyboard(bot_username: str) -> InlineKeyboardMarkup:
    """More Info menu keyboard with Developer Info, Admin Info, Share Bot, and navigation."""
    buttons = [
        [
            InlineKeyboardButton("👨‍💻 Developer Info", callback_data="info_developer"),
            InlineKeyboardButton("👑 Admin Info", callback_data="info_admin")
        ],
        [
            InlineKeyboardButton(
                "↗️ Share Bot",
                switch_inline_query=f"https://t.me/{bot_username}"
            )
        ],
        [
            InlineKeyboardButton("🔙 Go Back", callback_data="nav_about"),
            InlineKeyboardButton("🏠 Back to Main Menu", callback_data="nav_start")
        ]
    ]
    return InlineKeyboardMarkup(buttons)


def get_developer_info_keyboard() -> InlineKeyboardMarkup:
    """Keyboard inside Developer Info screen featuring the Gift button."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎁 Gift for You Guys", callback_data="info_gift")
        ],
        [
            InlineKeyboardButton("🔙 Go Back", callback_data="about_more_info"),
            InlineKeyboardButton("🏠 Back to Main Menu", callback_data="nav_start")
        ]
    ])


def get_gift_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for Gift for You Guys template redirection."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ Yes",
                url="https://app.qufork.com/templates?template=tpl_1787813858505_refer_and_earn_teleg"
            ),
            InlineKeyboardButton("❌ No", callback_data="info_developer")
        ],
        [
            InlineKeyboardButton("🏠 Back to Main Menu", callback_data="nav_start")
        ]
    ])


def get_info_subpage_keyboard() -> InlineKeyboardMarkup:
    """Subpage back navigation for Admin Info."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔙 Go Back", callback_data="about_more_info"),
            InlineKeyboardButton("🏠 Back to Main Menu", callback_data="nav_start")
        ]
    ])


def get_admin_main_keyboard() -> InlineKeyboardMarkup:
    """Admin dashboard keyboard."""
    buttons = [
        [
            InlineKeyboardButton("📊 Live Analytics", callback_data="admin_stats"),
            InlineKeyboardButton("📢 Broadcast Message", callback_data="admin_broadcast_prompt")
        ],
        [
            InlineKeyboardButton("📋 Monitored Channels & Groups", callback_data="nav_channels")
        ],
        [
            InlineKeyboardButton("🏠 Back to Main Menu", callback_data="nav_start")
        ]
    ]
    return InlineKeyboardMarkup(buttons)


def get_stats_keyboard() -> InlineKeyboardMarkup:
    """Stats view keyboard with refresh and quick actions."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔄 Refresh Statistics", callback_data="admin_stats"),
            InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast_prompt")
        ],
        [
            InlineKeyboardButton("⚙️ Admin Dashboard", callback_data="nav_admin_panel"),
            InlineKeyboardButton("🏠 Main Menu", callback_data="nav_start")
        ]
    ])


def get_channels_keyboard(channels: List[Dict[str, Any]], page: int = 0, per_page: int = 5) -> InlineKeyboardMarkup:
    """List registered channels/groups with status badges and pagination."""
    buttons = []
    total = len(channels)
    start_idx = page * per_page
    end_idx = start_idx + per_page
    page_channels = channels[start_idx:end_idx]

    for ch in page_channels:
        title = ch.get("title") or f"Chat {ch['chat_id']}"
        auto = "🟢" if ch.get("auto_accept", 1) == 1 else "🔴"
        buttons.append([
            InlineKeyboardButton(f"{auto} {title}", callback_data=f"chat_detail:{ch['chat_id']}")
        ])

    # Pagination controls
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"channels_page:{page - 1}"))
    if end_idx < total:
        nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"channels_page:{page + 1}"))

    if nav_row:
        buttons.append(nav_row)

    buttons.append([
        InlineKeyboardButton("🔄 Refresh List", callback_data=f"channels_page:{page}"),
        InlineKeyboardButton("🏠 Main Menu", callback_data="nav_start")
    ])

    return InlineKeyboardMarkup(buttons)


def get_chat_settings_keyboard(chat_id: int, auto_accept: bool) -> InlineKeyboardMarkup:
    """Main Chat settings keyboard with quick Copy ID and status indicators."""
    auto_label = "🟢 Auto-Accept: ACTIVE" if auto_accept else "🔴 Auto-Accept: DISABLED"

    buttons = [
        [
            InlineKeyboardButton(auto_label, callback_data=f"chat_toggle_auto:{chat_id}")
        ],
        [
            InlineKeyboardButton(
                f"📋 Copy Chat ID ({chat_id})",
                copy_text=CopyTextButton(text=str(chat_id))
            )
        ],
        [
            InlineKeyboardButton("⚡ Approve Past / Pending Requests", callback_data=f"chat_prompt_pending:{chat_id}")
        ],
        [
            InlineKeyboardButton("💌 Manage Welcome DM & Media", callback_data=f"chat_welcome_menu:{chat_id}")
        ],
        [
            InlineKeyboardButton("🔒 Setup Force Join Another Channel", callback_data=f"chat_forcesub_menu:{chat_id}")
        ],
        [
            InlineKeyboardButton("🔙 Back to Channels", callback_data="nav_channels")
        ]
    ]
    return InlineKeyboardMarkup(buttons)


def format_delay_time(seconds: int) -> str:
    """Format seconds into readable human time."""
    if not seconds or seconds <= 0:
        return "Instant"
    if seconds % 86400 == 0:
        days = seconds // 86400
        return f"{days} Day" if days == 1 else f"{days} Days"
    if seconds % 3600 == 0:
        hours = seconds // 3600
        return f"{hours} Hour" if hours == 1 else f"{hours} Hours"
    if seconds % 60 == 0:
        mins = seconds // 60
        return f"{mins} Min" if mins == 1 else f"{mins} Mins"
    return f"{seconds}s"


def get_chat_forcesub_menu_keyboard(
    chat_id: int,
    force_sub_enabled: bool,
    has_channels: bool,
    send_only_enabled: bool = False,
    send_only_delay: int = 86400
) -> InlineKeyboardMarkup:
    """Force join management keyboard for a specific channel."""
    status_label = "🟢 Force Join: ACTIVE" if force_sub_enabled else "🔴 Force Join: DISABLED"
    send_only_label = f"⏱️ Send Only: {'🟢 ' + format_delay_time(send_only_delay) if send_only_enabled else '🔴 Disabled'}"

    buttons = [
        [
            InlineKeyboardButton(status_label, callback_data=f"chat_toggle_forcesub:{chat_id}")
        ],
        [
            InlineKeyboardButton(send_only_label, callback_data=f"chat_sendonly_menu:{chat_id}")
        ],
        [
            InlineKeyboardButton("✏️ Set / Change Force Join Channels", callback_data=f"chat_edit_forcesub:{chat_id}")
        ]
    ]
    if has_channels:
        buttons.append([
            InlineKeyboardButton("🗑️ Clear Force Join Channels", callback_data=f"chat_reset_forcesub:{chat_id}")
        ])
    buttons.append([
        InlineKeyboardButton("🔙 Back to Chat Settings", callback_data=f"chat_detail:{chat_id}")
    ])
    return InlineKeyboardMarkup(buttons)


def get_chat_sendonly_menu_keyboard(chat_id: int, send_only_enabled: bool, current_delay: int) -> InlineKeyboardMarkup:
    """Send Only mode timer configuration keyboard."""
    status_label = "🟢 Send Only Mode: ACTIVE" if send_only_enabled else "🔴 Send Only Mode: DISABLED"
    
    def _active_mark(sec: int, label: str) -> str:
        return f"✅ {label}" if current_delay == sec else label

    buttons = [
        [
            InlineKeyboardButton(status_label, callback_data=f"chat_toggle_sendonly:{chat_id}")
        ],
        [
            InlineKeyboardButton(_active_mark(3600, "1 Hour"), callback_data=f"chat_set_sendonly_delay:{chat_id}:3600"),
            InlineKeyboardButton(_active_mark(21600, "6 Hours"), callback_data=f"chat_set_sendonly_delay:{chat_id}:21600"),
            InlineKeyboardButton(_active_mark(43200, "12 Hours"), callback_data=f"chat_set_sendonly_delay:{chat_id}:43200"),
        ],
        [
            InlineKeyboardButton(_active_mark(86400, "1 Day (24h)"), callback_data=f"chat_set_sendonly_delay:{chat_id}:86400"),
            InlineKeyboardButton(_active_mark(172800, "2 Days (48h)"), callback_data=f"chat_set_sendonly_delay:{chat_id}:172800"),
            InlineKeyboardButton(_active_mark(259200, "3 Days (72h)"), callback_data=f"chat_set_sendonly_delay:{chat_id}:259200"),
        ],
        [
            InlineKeyboardButton("🔙 Back to Force Join Menu", callback_data=f"chat_forcesub_menu:{chat_id}")
        ]
    ]
    return InlineKeyboardMarkup(buttons)


def get_channel_force_join_request_keyboard(
    chat_id: int,
    channels: List[Dict[str, Any]],
    bot_username: Optional[str] = None
) -> InlineKeyboardMarkup:
    """Build keyboard for force join prompt during ChatJoinRequest with channel links, verify button, and test autostart button."""
    buttons = []
    for idx, ch in enumerate(channels, 1):
        title = ch.get("title") or f"Channel {idx}"
        url = ch.get("url") or "https://t.me/"
        btn_label = f"Join {title}"
        if len(btn_label) > 40:
            btn_label = btn_label[:37] + "..."
        buttons.append([
            InlineKeyboardButton(btn_label, url=url)
        ])

    buttons.append([
        InlineKeyboardButton("🔄 Verify & Join", callback_data=f"verify_chat_join:{chat_id}")
    ])
    return InlineKeyboardMarkup(buttons)


def get_approve_pending_confirm_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    """Confirmation keyboard for batch approving all pending requests."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚡ Yes, Approve All Backlog Requests", callback_data=f"chat_exec_pending:{chat_id}")
        ],
        [
            InlineKeyboardButton("❌ Cancel & Go Back", callback_data=f"chat_detail:{chat_id}")
        ]
    ])


def get_chat_welcome_menu_keyboard(chat_id: int, welcome_enabled: bool) -> InlineKeyboardMarkup:
    """Dedicated Welcome Message management keyboard with active badges."""
    welcome_label = "🟢 Welcome DM: ACTIVE" if welcome_enabled else "🔴 Welcome DM: DISABLED"

    buttons = [
        [
            InlineKeyboardButton(welcome_label, callback_data=f"chat_toggle_welcome:{chat_id}")
        ],
        [
            InlineKeyboardButton("✏️ Edit Welcome Message & Media", callback_data=f"chat_edit_welcome:{chat_id}")
        ],
        [
            InlineKeyboardButton("👁️ Live Preview DM", callback_data=f"chat_preview_welcome:{chat_id}"),
            InlineKeyboardButton("🔄 Reset to Default", callback_data=f"chat_reset_welcome:{chat_id}")
        ],
        [
            InlineKeyboardButton("🔙 Back to Chat Settings", callback_data=f"chat_detail:{chat_id}")
        ]
    ]
    return InlineKeyboardMarkup(buttons)


def get_broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    """Confirmation keyboard for broadcast."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🚀 Confirm & Send Broadcast", callback_data="broadcast_confirm"),
            InlineKeyboardButton("❌ Cancel", callback_data="broadcast_cancel")
        ]
    ])


def get_force_sub_keyboard(channels: List[Dict[str, str]]) -> InlineKeyboardMarkup:
    """Generate keyboard for force sub channels with join links and Verify button."""
    buttons = []
    
    for idx, ch in enumerate(channels, 1):
        title = ch.get("title") or f"Channel {idx}"
        url = ch.get("url") or "https://t.me/"
        # Button label: Join {title}
        btn_label = f"Join {title}"
        if len(btn_label) > 40:
            btn_label = btn_label[:37] + "..."
        buttons.append([
            InlineKeyboardButton(btn_label, url=url)
        ])

    # Verification button as the last row
    buttons.append([
        InlineKeyboardButton("🔄 I Have Joined (Verify)", callback_data="verify_force_sub")
    ])

    return InlineKeyboardMarkup(buttons)


