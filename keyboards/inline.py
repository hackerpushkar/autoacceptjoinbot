from typing import List, Dict, Any
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
    """About menu keyboard with copy button and share action."""
    buttons = [
        [
            InlineKeyboardButton(
                f"📋 Copy Bot Username (@{bot_username})",
                copy_text=CopyTextButton(text=f"@{bot_username}")
            )
        ],
        [
            InlineKeyboardButton(
                "↗️ Share Bot",
                switch_inline_query=f"https://t.me/{bot_username}"
            )
        ],
        [
            InlineKeyboardButton("🏠 Back to Main Menu", callback_data="nav_start")
        ]
    ]
    return InlineKeyboardMarkup(buttons)


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
            InlineKeyboardButton("🔙 Back to Channels", callback_data="nav_channels")
        ]
    ]
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
        # Clean title for button display
        btn_label = f"📢 Join {title}"
        if len(btn_label) > 35:
            btn_label = btn_label[:32] + "..."
        buttons.append([
            InlineKeyboardButton(btn_label, url=url)
        ])

    # Verification button as the last row
    buttons.append([
        InlineKeyboardButton("🔄 Verify / I Joined", callback_data="verify_force_sub")
    ])

    return InlineKeyboardMarkup(buttons)

