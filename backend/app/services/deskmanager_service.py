from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.deskmanager_category import DeskManagerCategory
from app.models.deskmanager_user import DeskManagerUser
from app.repositories.deskmanager_repository import DeskManagerRepository
from app.schemas.deskmanager import (
    DeskManagerCreateTicketItem,
    DeskManagerCreateTicketResult,
    DeskManagerCreateTicketsResponse,
)


class DeskManagerService:
    def __init__(
        self,
        session: Session,
        settings: Settings | None = None,
        client_factory: Callable[[], httpx.Client] | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = DeskManagerRepository(session)
        self.client_factory = client_factory or (lambda: httpx.Client(timeout=30.0))

    def list_users(self) -> list[DeskManagerUser]:
        return self.repository.list_users()

    def list_categories(self, search: str | None = None) -> list[DeskManagerCategory]:
        return self.repository.list_categories(search)

    def create_tickets(self, items: list[DeskManagerCreateTicketItem]) -> DeskManagerCreateTicketsResponse:
        self._validate_configuration()
        users = {item.id: item for item in self.repository.get_users_by_ids([item.user_id for item in items])}
        categories = {item.id: item for item in self.repository.get_categories_by_ids([item.category_id for item in items])}
        missing_user_ids = sorted({item.user_id for item in items if item.user_id not in users})
        missing_category_ids = sorted({item.category_id for item in items if item.category_id not in categories})

        if missing_user_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"One or more DeskManager users were not found: {', '.join(missing_user_ids)}",
            )
        if missing_category_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"One or more DeskManager categories were not found: {', '.join(missing_category_ids)}",
            )

        with self.client_factory() as client:
            token = self._authenticate(client)
            results = [self._create_ticket(client, item, users[item.user_id], categories[item.category_id], token) for item in items]

        success_count = sum(1 for item in results if item.status == "success")
        failed_count = len(results) - success_count
        return DeskManagerCreateTicketsResponse(
            total=len(results),
            success_count=success_count,
            failed_count=failed_count,
            results=results,
        )

    def _validate_configuration(self) -> None:
        required = {
            "DESKMANAGER_AUTH_URL": self.settings.deskmanager_auth_url,
            "DESKMANAGER_TICKETS_URL": self.settings.deskmanager_tickets_url,
            "DESKMANAGER_APPROVER_TOKEN": self.settings.deskmanager_approver_token,
            "DESKMANAGER_PUBLIC_KEY": self.settings.deskmanager_public_key,
            "DESKMANAGER_SOLICITACAO_ID": self.settings.deskmanager_solicitacao_id,
            "DESKMANAGER_IMPACTO_ID": self.settings.deskmanager_impacto_id,
            "DESKMANAGER_URGENCIA_ID": self.settings.deskmanager_urgencia_id,
            "DESKMANAGER_CATEGORIA_ID": self.settings.deskmanager_categoria_id,
            "DESKMANAGER_CATEGORIA_TIPO_ID": self.settings.deskmanager_categoria_tipo_id,
            "DESKMANAGER_GRUPO_ID": self.settings.deskmanager_grupo_id,
        }
        missing = [name for name, value in required.items() if not value.strip()]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"DeskManager configuration is incomplete: {', '.join(missing)}",
            )

    def _authenticate(self, client: httpx.Client) -> str:
        try:
            response = client.post(
                self.settings.deskmanager_auth_url,
                json={"PublicKey": self.settings.deskmanager_public_key},
                headers={
                    "Authorization": self.settings.deskmanager_approver_token,
                    "Content-Type": "application/json",
                    "JsonPath": "true",
                },
            )
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"DeskManager authentication request failed: {exc.__class__.__name__}",
            ) from exc

        payload = self._parse_response_body(response)
        if response.status_code != status.HTTP_200_OK:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"DeskManager authentication failed: {response.status_code}",
            )

        token = payload.get("access_token") if isinstance(payload, dict) else None
        if not isinstance(token, str) or not token.strip():
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="DeskManager authentication did not return an access token",
            )
        return token

    def _create_ticket(
        self,
        client: httpx.Client,
        item: DeskManagerCreateTicketItem,
        user: DeskManagerUser,
        category: DeskManagerCategory,
        token: str,
    ) -> DeskManagerCreateTicketResult:
        payload = {
            "TChamado": {
                "Solicitante": user.id,
                "AutoCategoria": category.id,
                "Solicitacao": self.settings.deskmanager_solicitacao_id,
                "Impacto": self.settings.deskmanager_impacto_id,
                "Urgencia": self.settings.deskmanager_urgencia_id,
                "Descricao": item.description.strip(),
                "Categoria": self.settings.deskmanager_categoria_id,
                "CategoriaTipo": self.settings.deskmanager_categoria_tipo_id,
                "Grupo": self.settings.deskmanager_grupo_id,
            }
        }

        try:
            response = client.put(
                self.settings.deskmanager_tickets_url,
                json=payload,
                headers={"Authorization": token, "Content-Type": "application/json"},
            )
        except httpx.HTTPError as exc:
            return DeskManagerCreateTicketResult(
                user_id=item.user_id,
                category_id=item.category_id,
                description=item.description,
                status="failed",
                message=f"DeskManager request failed: {exc.__class__.__name__}",
            )

        body = self._parse_response_body(response)
        if response.status_code == status.HTTP_200_OK:
            message = "Chamado criado com sucesso!"
            if isinstance(body, dict):
                message = str(body.get("message") or body.get("Mensagem") or message)
            return DeskManagerCreateTicketResult(
                user_id=item.user_id,
                category_id=item.category_id,
                description=item.description,
                status="success",
                message=message,
                external_response=body,
            )

        return DeskManagerCreateTicketResult(
            user_id=item.user_id,
            category_id=item.category_id,
            description=item.description,
            status="failed",
            message=f"Erro ao criar chamado: {response.status_code}",
            external_response=body,
        )

    def _parse_response_body(self, response: httpx.Response) -> Any:
        try:
            return response.json()
        except ValueError:
            text = response.text.strip()
            return text or None
