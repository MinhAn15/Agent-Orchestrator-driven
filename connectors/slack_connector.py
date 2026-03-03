"""Slack connector for Antigravity (v0.3).

Sends messages to Slack channels/users via the Slack Incoming Webhook API
or the Slack Web API (chat.postMessage).

No external SDK required — uses only urllib from the standard library for
the webhook path, keeping the dependency footprint minimal.
"""

from __future__ import annotations

import json
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SlackMessage:
    """Represents a Slack message payload."""

    text: str
    channel: str | None = None          # Required for Web API, ignored for webhooks
    username: str = "Antigravity Bot"
    icon_emoji: str = ":robot_face:"
    attachments: list[dict[str, Any]] = field(default_factory=list)
    blocks: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "text": self.text,
            "username": self.username,
            "icon_emoji": self.icon_emoji,
        }
        if self.channel:
            payload["channel"] = self.channel
        if self.attachments:
            payload["attachments"] = self.attachments
        if self.blocks:
            payload["blocks"] = self.blocks
        return payload


@dataclass
class SlackConnector:
    """Sends messages to Slack via Incoming Webhooks or the Web API.

    Args:
        webhook_url:  Incoming Webhook URL (for simple webhook-based sends).
        bot_token:    Slack Bot OAuth token (for Web API calls).
        default_channel: Default channel used when no channel is specified.
        timeout:      HTTP request timeout in seconds.
    """

    webhook_url: str | None = None
    bot_token: str | None = None
    default_channel: str | None = None
    timeout: int = 10

    def __post_init__(self) -> None:
        if not self.webhook_url and not self.bot_token:
            raise ValueError(
                "SlackConnector requires either webhook_url or bot_token."
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def send(self, text: str, channel: str | None = None, **kwargs: Any) -> dict[str, Any]:
        """Send a plain-text message.

        Args:
            text:    Message text.
            channel: Target channel (overrides default_channel).
            **kwargs: Extra fields forwarded to SlackMessage.

        Returns:
            Response dict with keys 'ok', 'status', and optional 'error'.
        """
        msg = SlackMessage(
            text=text,
            channel=channel or self.default_channel,
            **kwargs,
        )
        return self._dispatch(msg)

    def send_alert(self, title: str, body: str, level: str = "info", channel: str | None = None) -> dict[str, Any]:
        """Send a structured alert with colour-coded attachment.

        Args:
            title:   Alert title.
            body:    Alert body text.
            level:   One of 'info', 'warning', 'error'.
            channel: Optional channel override.
        """
        color_map = {"info": "#36a64f", "warning": "#f0ad4e", "error": "#d9534f"}
        attachment = {
            "color": color_map.get(level, "#cccccc"),
            "title": title,
            "text": body,
            "footer": "Antigravity",
        }
        return self.send(text=title, channel=channel, attachments=[attachment])

    # ------------------------------------------------------------------
    # Internal dispatch
    # ------------------------------------------------------------------

    def _dispatch(self, msg: SlackMessage) -> dict[str, Any]:
        if self.webhook_url:
            return self._send_webhook(msg)
        return self._send_web_api(msg)

    def _send_webhook(self, msg: SlackMessage) -> dict[str, Any]:
        payload = json.dumps(msg.to_dict()).encode("utf-8")
        req = urllib.request.Request(
            self.webhook_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode()
                return {"ok": body == "ok", "status": resp.status, "body": body}
        except urllib.error.HTTPError as exc:
            return {"ok": False, "status": exc.code, "error": str(exc)}
        except OSError as exc:
            return {"ok": False, "status": None, "error": str(exc)}

    def _send_web_api(self, msg: SlackMessage) -> dict[str, Any]:
        payload = json.dumps(msg.to_dict()).encode("utf-8")
        req = urllib.request.Request(
            "https://slack.com/api/chat.postMessage",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.bot_token}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode())
                return {"ok": data.get("ok", False), "status": resp.status, "data": data}
        except urllib.error.HTTPError as exc:
            return {"ok": False, "status": exc.code, "error": str(exc)}
        except OSError as exc:
            return {"ok": False, "status": None, "error": str(exc)}
