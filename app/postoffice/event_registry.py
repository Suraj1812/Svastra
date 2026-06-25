from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EventRegistryEntry:
    internal_type: str
    canonical_type: str
    label: str
    description: str
    category: str


MVP_EVENT_REGISTRY: dict[str, EventRegistryEntry] = {
    "advisory.publish": EventRegistryEntry(
        internal_type="advisory.publish",
        canonical_type="event.advisory.publish",
        label="Advisory Published",
        description="Provider published a care advisory for the patient.",
        category="care_plan",
    ),
    "schedule.generate": EventRegistryEntry(
        internal_type="schedule.generate",
        canonical_type="event.schedule.generate",
        label="Schedule Generated",
        description="Backend generated due times and grace windows for advisory tasks.",
        category="schedule",
    ),
    "task.generate": EventRegistryEntry(
        internal_type="task.generate",
        canonical_type="event.task.generate",
        label="Care Plan Delivered",
        description="Patient-facing care tasks were created and delivered.",
        category="task",
    ),
    "response.log": EventRegistryEntry(
        internal_type="response.log",
        canonical_type="event.response.log",
        label="Response Logged",
        description="Patient submitted a task response or uploaded an investigation report.",
        category="response",
    ),
    "attachment.upload": EventRegistryEntry(
        internal_type="attachment.upload",
        canonical_type="event.attachment.upload",
        label="Attachment Uploaded",
        description="Patient uploaded an investigation report attachment.",
        category="attachment",
    ),
    "alert.trigger": EventRegistryEntry(
        internal_type="alert.trigger",
        canonical_type="event.alert.trigger",
        label="Alert Triggered",
        description="Clinical rule evaluation created an alert for provider review.",
        category="alert",
    ),
    "alert.acknowledge": EventRegistryEntry(
        internal_type="alert.acknowledge",
        canonical_type="event.alert.acknowledge",
        label="Alert Acknowledged",
        description="Provider acknowledged a clinical alert without deleting history.",
        category="alert",
    ),
    "alert.resolve": EventRegistryEntry(
        internal_type="alert.resolve",
        canonical_type="event.alert.resolve",
        label="Alert Resolved",
        description="Provider resolved a clinical alert while keeping it visible historically.",
        category="alert",
    ),
    "consent.request": EventRegistryEntry(
        internal_type="consent.request",
        canonical_type="event.consent.request",
        label="Consent Requested",
        description="Provider or caregiver requested patient-controlled access.",
        category="consent",
    ),
    "consent.grant": EventRegistryEntry(
        internal_type="consent.grant",
        canonical_type="event.consent.grant",
        label="Consent Granted",
        description="Patient granted access consent.",
        category="consent",
    ),
    "consent.reject": EventRegistryEntry(
        internal_type="consent.reject",
        canonical_type="event.consent.reject",
        label="Consent Rejected",
        description="Patient rejected an access request.",
        category="consent",
    ),
    "consent.revoke": EventRegistryEntry(
        internal_type="consent.revoke",
        canonical_type="event.consent.revoke",
        label="Consent Revoked",
        description="Patient revoked active access consent.",
        category="consent",
    ),
    "relationship.created": EventRegistryEntry(
        internal_type="relationship.created",
        canonical_type="event.relationship.created",
        label="Relationship Created",
        description="Consent-backed operational healthcare relationship became active.",
        category="relationship",
    ),
    "relationship.deactivated": EventRegistryEntry(
        internal_type="relationship.deactivated",
        canonical_type="event.relationship.deactivated",
        label="Relationship Deactivated",
        description="Operational healthcare relationship was deactivated.",
        category="relationship",
    ),
    "message.send": EventRegistryEntry(
        internal_type="message.send",
        canonical_type="event.message.send",
        label="Message Sent",
        description="A message event was sent through PostOffice.",
        category="message",
    ),
}

DOCUMENTED_MVP_EVENT_TYPES = tuple(
    MVP_EVENT_REGISTRY[event_type].canonical_type
    for event_type in (
        "advisory.publish",
        "schedule.generate",
        "response.log",
        "attachment.upload",
        "alert.trigger",
        "alert.acknowledge",
        "alert.resolve",
    )
) + ("event.attachment.upload",)


def registry_entry(event_type: str) -> EventRegistryEntry:
    return MVP_EVENT_REGISTRY.get(
        event_type,
        EventRegistryEntry(
            internal_type=event_type,
            canonical_type=f"event.{event_type}",
            label=event_type.replace(".", " ").replace("_", " ").title(),
            description="Registered operational event.",
            category="other",
        ),
    )


def canonical_event_type(event_type: str) -> str:
    return registry_entry(event_type).canonical_type
