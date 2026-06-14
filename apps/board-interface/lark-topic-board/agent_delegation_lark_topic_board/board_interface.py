"""Lark Topic Board — 飞书话题公告板前端 Interface。

职责：
- 每个 task_id 对应一个飞书话题。
- 发布任务时通知乙方。
- result_submitted 时通知甲方验收。
- reject 时通知原 contractor 返工。
- approved + closed 后标记话题关闭。
- Lark sync failed 时写 incident，但不影响核心 task 状态。
- 飞书只做前端，不是事实源。
- 不调用 LLM。
- 不理解任务内容。
- 不替甲方验收。
- 不替乙方执行。

公告板事件的完整流转（由适配器根据事件日志驱动）：
  task_published      → notify_contractor (创建话题)
  result_submitted    → notify_principal (通知验收)
  review_rejected     → notify_contractor (通知返工)
  review_approved     → notify_closing (标记待关闭)
  task_closed         → close_topic (关闭话题)
  incident_created    → notify_incident (通知异常)
"""
import json
from datetime import datetime, timezone
from pathlib import Path


# ── 通知类型 ──────────────────────────────────────────────

NOTIFICATION_TYPES = {
    "task_published": "notify_contractor",
    "result_submitted": "notify_principal",
    "review_rejected": "notify_contractor_revision",
    "review_approved": "notify_closing",
    "task_closed": "close_topic",
    "incident_created": "notify_incident",
}


# ── 通知消息模板（不调用 LLM，不猜任务内容） ────────────

EVENT_MESSAGES = {
    "task_published": {
        "to": "contractor",
        "title": "新任务待领取",
        "body": "任务 {task_id}「{title}」已发布。请领取后开始执行。",
        "action": "claim_task",
    },
    "result_submitted": {
        "to": "principal",
        "title": "任务结果已提交",
        "body": "乙方已提交任务 {task_id}「{title}」的执行结果。请验收。",
        "action": "review_task",
    },
    "review_rejected": {
        "to": "contractor",
        "title": "验收未通过，需要返工",
        "body": "任务 {task_id}「{title}」验收未通过。修改意见：{revision_request}。请返工后重新提交。",
        "action": "revise_task",
    },
    "review_approved": {
        "to": "both",
        "title": "任务已通过验收",
        "body": "任务 {task_id}「{title}」已通过验收。公告板即将关闭任务。",
        "action": "none",
    },
    "task_closed": {
        "to": "both",
        "title": "任务已关闭",
        "body": "任务 {task_id}「{title}」已完成并关闭。",
        "action": "none",
    },
    "incident_created": {
        "to": "operator",
        "title": "异常事件",
        "body": "任务 {task_id} 发生异常：{incident_description}",
        "action": "investigate",
    },
}


class LarkTopicBoardError(ValueError):
    pass


class LarkTopicBoard:
    """飞书话题公告板前端。

    这是一个 zero-agent 适配器：
    - 不调用 LLM。
    - 不理解任务内容。
    - 不替甲方验收。
    - 不替乙方执行。
    - 只处理通知路由和话题状态。
    - 不直接修改 board 状态机（通过 lifecycle.py 操作 board 事实源）。
    """

    def __init__(self, mapping_store=None, frontend_id="lark-topic-board"):
        self.mapping_store = mapping_store or ".local/frontends/lark-topic-map.json"
        self.frontend_id = frontend_id
        self._topic_map = self._load_map()

    # ── 话题映射管理 ──────────────────────────────────────

    def get_topic_for_task(self, task_id):
        """获取 task_id 对应的飞书话题 ID。"""
        return self._topic_map.get(task_id)

    def assign_topic(self, task_id, topic_id):
        """为 task_id 分配飞书话题 ID。"""
        self._topic_map[task_id] = {"topic_id": topic_id, "status": "active"}
        self._save_map()

    def close_topic(self, task_id):
        """标记话题为已关闭。"""
        if task_id in self._topic_map:
            self._topic_map[task_id]["status"] = "closed"
            self._topic_map[task_id]["closed_at"] = _now()
            self._save_map()

    def is_topic_active(self, task_id):
        """话题是否仍处于活跃状态。"""
        entry = self._topic_map.get(task_id)
        return entry is not None and entry.get("status") == "active"

    # ── 事件处理 ──────────────────────────────────────────

    def handle_event(self, event, task=None):
        """处理单个 board 事件，产出前端通知。

        参数：
            event:      事件字典（必须包含 type, task_id, actor_identity_id, payload）
            task:       可选的 task 字典（提供额外上下文如 title）

        返回：
            dict 或 None — 前端通知描述。None 表示该事件不需要前端动作。

        不调用 LLM。
        不理解事件内容。
        不修改 board 事实源。
        """
        event_type = event.get("type")
        if event_type not in NOTIFICATION_TYPES:
            return None  # 未知事件，跳过

        task_id = event.get("task_id", "unknown")
        payload = event.get("payload", {})
        title = task.get("title", "") if task else payload.get("title", "")

        route = NOTIFICATION_TYPES[event_type]
        template = EVENT_MESSAGES.get(event_type, {})
        body = template.get("body", "").format(
            task_id=task_id,
            title=title,
            revision_request=payload.get("revision_request", "无"),
            incident_description=payload.get("error", "未知异常"),
        )

        notification = {
            "task_id": task_id,
            "event_type": event_type,
            "route": route,
            "to": template.get("to", "unknown"),
            "title": template.get("title", ""),
            "body": body,
            "action": template.get("action", "none"),
            "topic_id": self.get_topic_for_task(task_id),
        }

        # 特殊处理：task_published → 需要创建话题
        if event_type == "task_published":
            notification["needs_topic_creation"] = True

        # 特殊处理：review_approved → 准备关闭话题
        if event_type == "review_approved":
            notification["pending_close"] = True

        return notification

    def batch_process_events(self, events, tasks=None):
        """批量处理事件，返回通知列表。"""
        task_lookup = {t["task_id"]: t for t in (tasks or [])}
        notifications = []
        for event in events:
            task = task_lookup.get(event.get("task_id", ""))
            notif = self.handle_event(event, task=task)
            if notif:
                notifications.append(notif)
        return notifications

    # ── 内部持久化 ──────────────────────────────────────

    def _load_map(self):
        path = Path(self.mapping_store) if isinstance(self.mapping_store, str) else self.mapping_store
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {}

    def _save_map(self):
        path = Path(self.mapping_store) if isinstance(self.mapping_store, str) else self.mapping_store
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self._topic_map, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def _now():
    return datetime.now(timezone.utc).isoformat()
