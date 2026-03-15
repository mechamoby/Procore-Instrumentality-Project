"""SteelSync ActionResolver — CC-7.1

Resolves contextual actions for any actionable element.
Generators are called in sequence and return ActionButton lists.
Runs at API response time, not at signal/synthesis time.
"""

import logging
import re
from dataclasses import dataclass, field, asdict
from typing import Optional
from urllib.parse import quote

logger = logging.getLogger("steelsync.actions")

PROCORE_BASE = "https://sandbox.procore.com/webclients/host/companies/4281379/projects"


@dataclass
class ActionButton:
    action_type: str       # "procore_link", "email_compose", "external_tool"
    label: str
    icon: str              # "procore", "email", "smartsheet", "onedrive", "excel", "browser"
    url: str
    target: str = "_blank"
    priority: int = 1      # lower = more prominent
    context: dict = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


class ProcoreDeepLinkGenerator:
    """Generates Procore deep links for entities."""

    # URL pattern per entity type
    PATTERNS = {
        "rfi":          "{base}/{ppid}/tools/rfis/{eid}",
        "submittal":    "{base}/{ppid}/tools/submittals/{eid}",
        "daily_log":    "{base}/{ppid}/tools/daily_log",
        "daily_report": "{base}/{ppid}/tools/daily_log",
        "change_order": "{base}/{ppid}/tools/change_orders/{eid}",
        "drawing":      "{base}/{ppid}/tools/drawings",
        "schedule":     "{base}/{ppid}/tools/schedule",
        "budget":       "{base}/{ppid}/tools/budget/detail",
        "document":     "{base}/{ppid}/tools/documents/{eid}",
    }

    LIST_PATTERNS = {
        "rfi":          "{base}/{ppid}/tools/rfis",
        "submittal":    "{base}/{ppid}/tools/submittals",
        "change_order": "{base}/{ppid}/tools/change_orders",
        "drawing":      "{base}/{ppid}/tools/drawings",
        "document":     "{base}/{ppid}/tools/documents",
    }

    def generate(self, entity_type: str, procore_id: Optional[int],
                 procore_project_id: Optional[int], context: dict = None) -> list:
        """Generate Procore deep link actions."""
        if not procore_project_id:
            return []

        ppid = str(procore_project_id)
        eid = str(procore_id) if procore_id else None

        # Try entity-specific deep link
        if eid and entity_type in self.PATTERNS:
            pattern = self.PATTERNS[entity_type]
            url = pattern.format(base=PROCORE_BASE, ppid=ppid, eid=eid)
            label = f"Open in Procore"
            return [ActionButton(
                action_type="procore_link",
                label=label,
                icon="procore",
                url=url,
                priority=1,
            )]

        # Fallback to list page
        if entity_type in self.LIST_PATTERNS:
            url = self.LIST_PATTERNS[entity_type].format(base=PROCORE_BASE, ppid=ppid)
            return [ActionButton(
                action_type="procore_link",
                label=f"View {entity_type.replace('_', ' ').title()}s in Procore",
                icon="procore",
                url=url,
                priority=1,
            )]

        # Fallback to project home
        url = f"{PROCORE_BASE}/{ppid}"
        return [ActionButton(
            action_type="procore_link",
            label="Open Project in Procore",
            icon="procore",
            url=url,
            priority=1,
        )]


class EmailComposeGenerator:
    """Generates mailto: links for intelligence items and signals."""

    TEMPLATES = {
        "rfi_became_overdue": {
            "subject": "RE: {project_name} – RFI #{entity_value} Response Needed",
            "body": "This is a follow-up regarding RFI #{entity_value} on {project_name}.\n\nThis item is now {days_overdue} days past due. Please provide a response at your earliest convenience so we can keep the project on schedule.\n\nThank you.",
        },
        "submittal_rejected": {
            "subject": "RE: {project_name} – Submittal #{entity_value} Resubmission Required",
            "body": "The submittal referenced above has been returned and requires resubmission.\n\nPlease review the comments and resubmit as soon as possible.\n\nThank you.",
        },
        "response_turnaround_slipping": {
            "subject": "{project_name} – Outstanding Items Follow-Up",
            "body": "I wanted to follow up on several outstanding items for {project_name}.\n\nWe're seeing response times trending longer than expected. Please review your open items and prioritize responses.\n\nThank you.",
        },
        "promised_date_passed": {
            "subject": "RE: {project_name} – {entity_description} Status Update",
            "body": "The committed date for the item referenced above has passed.\n\nPlease provide a status update and revised completion date.\n\nThank you.",
        },
        "schedule_milestone_approaching": {
            "subject": "{project_name} – {milestone_name} in {days_until} Days",
            "body": "This is a reminder that {milestone_name} is approaching in {days_until} days on {project_name}.\n\nPlease confirm all prerequisites are on track.\n\nThank you.",
        },
    }

    DEFAULT_TEMPLATE = {
        "subject": "{project_name} – {title}",
        "body": "Regarding: {title}\n\n{summary}\n\nPlease advise.\n\nThank you.",
    }

    def generate(self, signal_category: str, entity_type: str,
                 supporting_context: dict, project_name: str,
                 title: str = "", summary: str = "",
                 recipient_email: str = "", cc_email: str = "") -> list:
        """Generate email compose action."""
        template = self.TEMPLATES.get(signal_category, self.DEFAULT_TEMPLATE)

        # Build substitution context
        ctx = {
            "project_name": project_name or "[Unknown Project]",
            "entity_value": supporting_context.get("entity_value", "[Unknown]"),
            "entity_description": supporting_context.get("entity_description", title or "[Unknown]"),
            "days_overdue": supporting_context.get("days_overdue", "[Unknown]"),
            "milestone_name": supporting_context.get("milestone_name", "[Unknown]"),
            "days_until": supporting_context.get("days_until", "[Unknown]"),
            "title": title or "[Unknown]",
            "summary": summary or "",
        }

        subject = self._substitute(template["subject"], ctx)
        body = self._substitute(template["body"], ctx)

        # Build mailto URL
        mailto = f"mailto:{quote(recipient_email, safe='@.')}"
        params = [f"subject={quote(subject)}"]
        if cc_email:
            params.append(f"cc={quote(cc_email, safe='@.')}")
        body_encoded = quote(body).replace('%0A', '%0D%0A')
        params.append(f"body={body_encoded}")
        mailto += "?" + "&".join(params)

        # Enforce 2000 char limit
        if len(mailto) > 2000:
            truncated_body = body[:300] + "\n\n[See SteelSync for full context]"
            body_encoded = quote(truncated_body).replace('%0A', '%0D%0A')
            params[-1] = f"body={body_encoded}"
            mailto = f"mailto:{quote(recipient_email, safe='@.')}?" + "&".join(params)

        label = "Email Responsible Party" if recipient_email else "Compose Email"
        return [ActionButton(
            action_type="email_compose",
            label=label,
            icon="email",
            url=mailto,
            priority=2,
        )]

    def _substitute(self, template: str, ctx: dict) -> str:
        """Substitute template variables, using [Unknown] for missing values."""
        def replacer(match):
            key = match.group(1)
            return str(ctx.get(key, "[Unknown]"))
        return re.sub(r'\{(\w+)\}', replacer, template)


class ExternalToolLinkGenerator:
    """Generates links to external tools configured for a project."""

    ENTITY_TOOL_MAP = {
        "submittal": ["smartsheet"],
        "document": ["onedrive", "sharepoint"],
        "drawing": ["onedrive", "sharepoint"],
    }

    def generate(self, entity_type: str, tools: list) -> list:
        """Generate external tool actions based on entity type and configured tools."""
        if not tools:
            return []

        relevant_tool_names = self.ENTITY_TOOL_MAP.get(entity_type, [])
        actions = []
        for tool in tools:
            tool_name_lower = (tool.get("tool_name") or "").lower()
            if any(t in tool_name_lower for t in relevant_tool_names):
                actions.append(ActionButton(
                    action_type="external_tool",
                    label=f"Open in {tool['tool_name']}",
                    icon=tool.get("tool_icon", "browser"),
                    url=tool["base_url"],
                    priority=3,
                ))
        return actions


class ActionResolver:
    """Main resolver — calls generators in sequence and merges results."""

    def __init__(self):
        self.procore_gen = ProcoreDeepLinkGenerator()
        self.email_gen = EmailComposeGenerator()
        self.external_gen = ExternalToolLinkGenerator()

    def resolve(self, entity_type: str, procore_id: Optional[int] = None,
                procore_project_id: Optional[int] = None,
                signal_category: str = "", supporting_context: dict = None,
                project_name: str = "", title: str = "", summary: str = "",
                recipient_email: str = "", cc_email: str = "",
                external_tools: list = None) -> list:
        """Resolve all applicable actions for an entity."""
        supporting_context = supporting_context or {}
        external_tools = external_tools or []
        actions = []

        # 1. Procore deep links
        actions.extend(self.procore_gen.generate(
            entity_type, procore_id, procore_project_id
        ))

        # 2. Email compose (only for intelligence/radar items with signal context)
        if signal_category or title:
            actions.extend(self.email_gen.generate(
                signal_category, entity_type, supporting_context,
                project_name, title, summary, recipient_email, cc_email
            ))

        # 3. External tool links
        actions.extend(self.external_gen.generate(entity_type, external_tools))

        # Sort by priority
        actions.sort(key=lambda a: a.priority)
        return actions

    def resolve_for_entity_row(self, entity_type: str, procore_id: Optional[int],
                                procore_project_id: Optional[int]) -> list:
        """Simplified resolve for direct entity rows (RFI/submittal tables)."""
        return self.procore_gen.generate(entity_type, procore_id, procore_project_id)


# Singleton instance
resolver = ActionResolver()
