from fastapi import HTTPException
import httpx

from app.core.config import Settings
from app.schemas.deskmanager import DeskManagerCreateTicketItem
from app.services.deskmanager_catalog import DESKMANAGER_CATEGORIES, DESKMANAGER_USERS
from app.services.deskmanager_service import DeskManagerService


class FakeDeskManagerClient:
    def __init__(self, auth_response: httpx.Response, ticket_responses: list[httpx.Response] | None = None, fail_put: bool = False) -> None:
        self.auth_response = auth_response
        self.ticket_responses = ticket_responses or []
        self.fail_put = fail_put
        self.post_calls: list[dict] = []
        self.put_calls: list[dict] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def post(self, url: str, **kwargs):
        self.post_calls.append({"url": url, **kwargs})
        return self.auth_response

    def put(self, url: str, **kwargs):
        self.put_calls.append({"url": url, **kwargs})
        if self.fail_put:
            raise httpx.ConnectError("boom")
        return self.ticket_responses.pop(0)


def build_settings(**overrides) -> Settings:
    return Settings(
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
        **overrides,
    )


def test_deskmanager_service_lists_seeded_catalogs(override_session):
    service = DeskManagerService(override_session, settings=build_settings())

    users = service.list_users()
    categories = service.list_categories("VPN")

    assert len(users) == len(DESKMANAGER_USERS)
    assert len(categories) > 0
    assert any(item.name == "PAS - VPN" for item in categories)


def test_deskmanager_service_creates_tickets_with_configured_payload(override_session):
    auth_response = httpx.Response(200, json={"access_token": "desk-token"})
    ticket_response = httpx.Response(200, json={"message": "Criado"})
    client = FakeDeskManagerClient(auth_response=auth_response, ticket_responses=[ticket_response])
    service = DeskManagerService(override_session, settings=build_settings(), client_factory=lambda: client)
    user_id = DESKMANAGER_USERS[0][0]
    category_id = DESKMANAGER_CATEGORIES[0][0]

    response = service.create_tickets(
        [DeskManagerCreateTicketItem(user_id=user_id, category_id=category_id, description="Erro no ambiente")]
    )

    assert response.success_count == 1
    assert response.failed_count == 0
    assert response.results[0].status == "success"
    assert response.results[0].message == "Criado"
    assert client.post_calls[0]["url"] == "https://api.desk.ms/Login/autenticar"
    assert client.put_calls[0]["url"] == "https://api.desk.ms/Chamados"
    assert client.put_calls[0]["json"]["TChamado"]["Solicitante"] == user_id
    assert client.put_calls[0]["json"]["TChamado"]["AutoCategoria"] == category_id
    assert client.put_calls[0]["json"]["TChamado"]["Categoria"] == "47859"


def test_deskmanager_service_marks_ticket_failures_without_aborting_batch(override_session):
    auth_response = httpx.Response(200, json={"access_token": "desk-token"})
    ticket_response = httpx.Response(500, json={"error": "upstream"})
    client = FakeDeskManagerClient(auth_response=auth_response, ticket_responses=[ticket_response], fail_put=False)
    service = DeskManagerService(override_session, settings=build_settings(), client_factory=lambda: client)

    response = service.create_tickets(
        [
            DeskManagerCreateTicketItem(
                user_id=DESKMANAGER_USERS[0][0],
                category_id=DESKMANAGER_CATEGORIES[0][0],
                description="Falha externa",
            )
        ]
    )

    assert response.success_count == 0
    assert response.failed_count == 1
    assert response.results[0].status == "failed"
    assert response.results[0].message == "Erro ao criar chamado: 500"


def test_deskmanager_service_rejects_missing_configuration(override_session):
    service = DeskManagerService(override_session, settings=build_settings(deskmanager_grupo_id=""))

    try:
        service.create_tickets(
            [
                DeskManagerCreateTicketItem(
                    user_id=DESKMANAGER_USERS[0][0],
                    category_id=DESKMANAGER_CATEGORIES[0][0],
                    description="Config missing",
                )
            ]
        )
    except HTTPException as exc:
        assert exc.status_code == 500
        assert "DESKMANAGER_GRUPO_ID" in exc.detail
    else:
        raise AssertionError("Expected missing DeskManager configuration to raise HTTPException")
