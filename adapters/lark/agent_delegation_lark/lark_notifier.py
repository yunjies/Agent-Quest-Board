"""
Lark / Feishu Notifier — 飞书通知发送器。

职责：
- 接收 LarkTopicBoard 产出的 notification dict（from board_interface.py handle_event / batch_process_events）。
- 通过 lark-cli（shell 命令）发送实际飞书消息。
- 响应"needs_topic_creation"创建飞书话题（thread）。
- 响应"pending_close"清理话题映射。
- 支持 dry-run 模式。
- 异常不抛出，只写 error 日志。
- 不包含硬编码凭证。
"""
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

# ── action 到 lark-cli 调用的映射 ───────────────────────────

NOTIFICATION_TO_LARK_ACTION = {
    "notify_contractor": "task_published",
    "notify_principal": "result_submitted",
    "notify_contractor_revision": "review_rejected",
    "notify_closing": "review_approved",
    "close_topic": "task_closed",
    "notify_incident": "incident_created",
}


class LarkNotifierError(RuntimeError):
    pass


class LarkNotifier:
    """通过 lark-cli 将 board notification 发送到飞书。

    使用方式：:

        notifier = LarkNotifier(topic_group_id="oc_example_group", dry_run=True)
        for notif in board.batch_process_events(events, tasks=tasks):
            notifier.dispatch(notif)

    dry_run=True 时只打印日志，不调用 lark-cli。
    lark_cli_bin 可替换为其他兼容的命令行工具。
    """

    def __init__(
        self,
        topic_group_id=None,
        incident_chat_id=None,
        dry_run=False,
        lark_cli_bin="lark-cli",
        config_path=None,
    ):
        self.topic_group_id = topic_group_id
        self.incident_chat_id = incident_chat_id
        self.dry_run = dry_run
        self.lark_cli_bin = lark_cli_bin
        self.config_path = config_path

    def dispatch(self, notification):
        """发送单条 notification 到飞书。

        Args:
            notification: dict 或 None — LarkTopicBoard.handle_event() 或
                           batch_process_events() 返回的 notification 字典。

        Returns:
            dict — 发送结果，包含成功/失败状态、消息 ID（如有）、错误信息（如有）。
        """
        if notification is None:
            return {"notification_type": None, "success": True}

        result = {"notification_type": notification.get("event_type"), "success": False}

        try:
            topic_id = notification.get("topic_id")
            body = notification.get("body", "")
            title = notification.get("title", "")
            action = notification.get("action", "none")
            needs_topic = notification.get("needs_topic_creation", False)
            pending_close = notification.get("pending_close", False)
            route = notification.get("route", "")
            to = notification.get("to", "unknown")

            # ── 创建话题 ──────────────────────────────
            if needs_topic and self.topic_group_id:
                topic_result = self._create_topic(title, body, notification)
                result["topic_created"] = topic_result.get("success", False)
                result["topic_id"] = topic_result.get("topic_id")

            # ── 发送消息到话题 ──────────────────────────
            if topic_id:
                send_result = self._send_message(
                    chat_id=topic_id if isinstance(topic_id, str) else topic_id.get("topic_id"),
                    body=body,
                )
                result["message_sent"] = send_result.get("success", False)
                result["message_id"] = send_result.get("message_id")

            # ── 话题关闭 ──────────────────────────────
            if pending_close:
                close_result = self._close_topic(notification)
                result["close_initiated"] = close_result.get("success", False)

            # ── 异常通知 ──────────────────────────────
            if route == "notify_incident" and self.incident_chat_id:
                incident_result = self._send_message(
                    chat_id=self.incident_chat_id,
                    body=f"[{title}] {body}",
                )
                result["incident_notified"] = incident_result.get("success", False)

            result["success"] = True

        except Exception as e:
            logger.error("dispatch failed for notification %s: %s", notification.get("event_type"), e)
            result["error"] = str(e)

        return result

    # ── 内部方法 ──────────────────────────────────────────

    def _create_topic(self, title, body, notification):
        """创建飞书话题（thread）。

        dry_run 模式只返回假结果。
        真实调用通过 lark-cli im +messages-send 向话题组发送首条消息。
        """
        if self.dry_run:
            logger.info("[DRY-RUN] would create topic with title=%s", title)
            return {"success": True, "topic_id": "example-dry-run-topic"}

        try:
            # 发送首条消息到话题组，作为话题的开端
            cmd = [
                self.lark_cli_bin,
                "im", "+messages-send",
                "--chat-id", self.topic_group_id,
                "--text", f"[{title}]\n{body}",
            ]
            if self.config_path:
                cmd.extend(["--config", self.config_path])

            proc = subprocess.run(
                cmd,
                capture_output=True, text=True, timeout=30,
            )
            if proc.returncode != 0:
                logger.warning("lark-cli send (topic creation) failed: %s", proc.stderr.strip())
                return {"success": False, "error": proc.stderr.strip()}

            # lark-cli 的消息发送返回中包含 message_id
            # 格式: {"code":0,"data":{"message_id":"om_xxx"}}
            import json
            try:
                parsed = json.loads(proc.stdout)
                msg_id = parsed.get("data", {}).get("message_id", "unknown")
            except (json.JSONDecodeError, KeyError):
                msg_id = "unknown"

            logger.info("topic created via lark-cli; message_id=%s", msg_id)
            return {"success": True, "topic_id": msg_id}

        except subprocess.TimeoutExpired:
            logger.error("lark-cli topic creation timed out")
            return {"success": False, "error": "timeout"}
        except FileNotFoundError:
            logger.error("lark-cli not found at %s", self.lark_cli_bin)
            return {"success": False, "error": f"lark-cli not found: {self.lark_cli_bin}"}

    def _send_message(self, chat_id, body):
        """发送普通飞书消息。

        Args:
            chat_id: str — 目标群聊或话题 ID
            body: str — 消息正文
        """
        if not chat_id:
            return {"success": False, "error": "no chat_id"}

        if self.dry_run:
            logger.info("[DRY-RUN] would send message to chat_id=%s: %s", chat_id, body[:80])
            return {"success": True, "message_id": "example-dry-run-msg"}

        try:
            cmd = [
                self.lark_cli_bin,
                "im", "+messages-send",
                "--chat-id", chat_id,
                "--text", body,
            ]
            if self.config_path:
                cmd.extend(["--config", self.config_path])

            proc = subprocess.run(
                cmd,
                capture_output=True, text=True, timeout=30,
            )
            if proc.returncode != 0:
                logger.warning("lark-cli send failed: %s", proc.stderr.strip())
                return {"success": False, "error": proc.stderr.strip()}

            import json
            try:
                parsed = json.loads(proc.stdout)
                msg_id = parsed.get("data", {}).get("message_id", "unknown")
            except (json.JSONDecodeError, KeyError):
                msg_id = "unknown"

            return {"success": True, "message_id": msg_id}

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "timeout"}
        except FileNotFoundError:
            return {"success": False, "error": f"lark-cli not found: {self.lark_cli_bin}"}

    def _close_topic(self, notification):
        """关闭话题。

        当前实现：向话题发送关闭标记消息。
        后续可扩展为修改群聊名称或归档。
        """
        task_id = notification.get("task_id", "unknown")
        if self.dry_run:
            logger.info("[DRY-RUN] would close topic for task_id=%s", task_id)
            return {"success": True}

        topic_id = notification.get("topic_id")
        if not topic_id:
            return {"success": False, "error": "no topic_id to close"}

        chat_id = topic_id if isinstance(topic_id, str) else topic_id.get("topic_id")
        if not chat_id:
            return {"success": False, "error": "no resolved chat_id"}

        # 发送关闭标记消息
        return self._send_message(
            chat_id=chat_id,
            body=f"[任务已关闭] {task_id} — 此任务已完成，话题即将归档。",
        )

    def dispatch_batch(self, notifications):
        """批量发送通知。

        Args:
            notifications: list[dict] — batch_process_events 返回的通知列表

        Returns:
            list[dict] — 每条通知的发送结果
        """
        return [self.dispatch(n) for n in notifications]
