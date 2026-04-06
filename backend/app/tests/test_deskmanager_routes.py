from app.api.routes import create_deskmanager_tickets, list_deskmanager_categories, list_deskmanager_users
from app.core.config import Settings
from app.core.security import CurrentUser
from app.schemas.deskmanager import DeskManagerCreateTicketItem, DeskManagerCreateTicketsRequest
from app.services.deskmanager_service import DeskManagerService


class RouteClientFactory:
    def __init__(self) -> None:
        self.client = type(
            "DeskClient",
            (),
            {
                "__enter__": lambda self: self,
                "__exit__": lambda self, exc_type, exc, tb: False,
                "post": lambda self, *_args, **_kwargs: __import__("httpx").Response(200, json={"access_token": "route-token"}),
                "put": lambda self, *_args, **_kwargs: __import__("httpx").Response(200, json={"message": "Route ok"}),
            },
        )()

    def __call__(self):
        return self.client


def build_route_service(override_session) -> DeskManagerService:
    settings = Settings(
        deskmanager_auth_url="https://api.desk.ms/Login/autenticar",
        deskmanager_tickets_url="https://api.desk.ms/Chamados",
        deskmanager_approver_token="approver-token",
        deskmanager_public_key="public-key",
        deskmanager_solicitacao_id="000004",
        deskmanager_impacto_id="000002",
        deskmanager_urgencia_id="000002",
        deskmanager_categoria_id="47859",
        deskmanager_categoria_tipo_id="47859",
        deskmanager_grupo_id="000019",
    )
    return DeskManagerService(override_session, settings=settings, client_factory=RouteClientFactory())


def test_deskmanager_routes_list_users_and_categories(override_session):
    service = build_route_service(override_session)
    current_user = CurrentUser(subject="local", email=None, groups=[])

    users = list_deskmanager_users(current_user, service)
    categories = list_deskmanager_categories("VPN", current_user, service)

    assert any(item.name == "Eduardo" for item in users)
    assert any("VPN" in item.name for item in categories)


def test_deskmanager_create_route_returns_batch_response(override_session):
    service = build_route_service(override_session)
    current_user = CurrentUser(subject="local", email=None, groups=[])

    response = create_deskmanager_tickets(
        DeskManagerCreateTicketsRequest(
            items=[
                DeskManagerCreateTicketItem(
                    user_id="2572",
                    category_id="9679",
                    description="Abrir chamado via rota",
                )
            ]
        ),
        current_user,
        service,
    )

    assert response.total == 1
    assert response.success_count == 1
    assert response.results[0].message == "Route ok"
