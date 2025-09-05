"""
Desktop notifications module for NexTalk client.

This module provides functions to display system notifications
using the notify-send command on Linux.
"""

import logging
import shutil
import subprocess

# 设置日志记录器
logger = logging.getLogger(__name__)


def check_notify_send() -> bool:
    """
    Check if notify-send command is available on the system.

    Returns:
        bool: True if notify-send is available, False otherwise.
    """
    return shutil.which("notify-send") is not None


def show_notification(title: str, message: str, urgency: str = "normal") -> bool:
    """
    Show a desktop notification using notify-send.

    Args:
        title: The notification title
        message: The notification message body
        urgency: Urgency level ('low', 'normal', or 'critical')

    Returns:
        bool: True if the notification was sent successfully, False otherwise
    """
    # 验证参数
    if not title or not message:
        logger.error("Cannot show notification: Title or message is empty")
        return False

    # 验证urgency参数
    valid_urgencies = ["low", "normal", "critical"]
    if urgency not in valid_urgencies:
        logger.warning(f"Invalid urgency level '{urgency}', defaulting to 'normal'")
        urgency = "normal"

    # 检查notify-send是否可用
    if not check_notify_send():
        logger.error("notify-send command not found. Please install libnotify-bin package.")
        return False

    try:
        # 执行notify-send命令
        result = subprocess.run(
            ["notify-send", f"--urgency={urgency}", title, message],
            check=True,
            capture_output=True,
            text=True,
        )
        logger.debug(f"Notification sent: {title} - {message}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to send notification: {e}")
        logger.debug(f"Command output: {e.stdout}, Error: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error when sending notification: {e}")
        return False
