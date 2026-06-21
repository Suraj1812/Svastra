from dataclasses import dataclass

from app.postoffice.validators import CEPEvent, CEPValidationError


@dataclass(frozen=True)
class EventRoute:
    handler: str
    target_app: str


ROUTES = {
    "consent.request": EventRoute("consent_handler", "rogi_mitra"),
    "consent.grant": EventRoute("consent_handler", "mantrana_mitra"),
    "consent.reject": EventRoute("consent_handler", "mantrana_mitra"),
    "consent.revoke": EventRoute("consent_handler", "mantrana_mitra"),
    "relationship.created": EventRoute("relationship_handler", "svastra_backend"),
    "relationship.deactivated": EventRoute("relationship_handler", "svastra_backend"),
    "schedule.generate": EventRoute("schedule_handler", "schedule_engine"),
    "advisory.publish": EventRoute("advisory_handler", "rogi_mitra"),
    "task.generate": EventRoute("task_handler", "rogi_mitra"),
    "response.log": EventRoute("response_handler", "mantrana_mitra"),
    "alert.trigger": EventRoute("alert_handler", "mantrana_mitra"),
    "message.send": EventRoute("message_handler", "rogi_mitra"),
}


def route_event(event: CEPEvent):
    route = ROUTES.get(event.event_type)
    if route is None:
        raise CEPValidationError(f"No route exists for {event.event_type}")
    return route
