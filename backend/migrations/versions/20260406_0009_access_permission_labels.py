"""sync access permission labels and add permission admin scopes

Revision ID: 20260406_0009
Revises: 20260406_0008
Create Date: 2026-04-06 13:30:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260406_0009"
down_revision = "20260406_0008"
branch_labels = None
depends_on = None


OLD_PERMISSION_METADATA = {
    "dashboard.view": ("Dashboard", "Visualizar dashboard"),
    "instances.view": ("Instâncias", "Visualizar instâncias"),
    "instances.manage": ("Instâncias", "Criar, editar e operar instâncias"),
    "groups.view": ("Grupos", "Visualizar grupos de instâncias"),
    "groups.manage": ("Grupos", "Criar, editar e excluir grupos de instâncias"),
    "schedules.view": ("Agendamentos", "Visualizar agendamentos"),
    "schedules.manage": ("Agendamentos", "Criar, editar e excluir agendamentos"),
    "compartments.view": ("Compartimentos", "Visualizar compartimentos"),
    "compartments.manage": ("Compartimentos", "Sincronizar e importar compartimentos"),
    "deskmanager.view": ("DeskManager", "Visualizar DeskManager"),
    "deskmanager.create_ticket": ("DeskManager", "Abrir chamados no DeskManager"),
    "reports.view": ("Relatórios", "Visualizar relatórios"),
    "audit.executions.view": ("Auditoria", "Visualizar execuções"),
    "audit.access.view": ("Auditoria", "Visualizar acessos"),
    "audit.settings.view": ("Auditoria", "Visualizar mudanças de configuração"),
    "admin.view": ("Administração", "Visualizar área administrativa"),
    "admin.users.view": ("Administração", "Visualizar usuários"),
    "admin.users.manage": ("Administração", "Gerenciar usuários"),
    "admin.access_groups.view": ("Administração", "Visualizar grupos de acesso"),
    "admin.access_groups.manage": ("Administração", "Gerenciar grupos de acesso"),
}

NEW_PERMISSION_METADATA = {
    "dashboard.view": ("Visualizar dashboard", "Permite abrir a tela principal de dashboard."),
    "instances.view": ("Visualizar instâncias", "Permite abrir a tela de instâncias."),
    "instances.manage": ("Gerenciar instâncias", "Permite criar, editar e operar instâncias."),
    "groups.view": ("Visualizar grupos de instâncias", "Permite abrir a tela de grupos de instâncias."),
    "groups.manage": ("Gerenciar grupos de instâncias", "Permite criar, editar e excluir grupos de instâncias."),
    "schedules.view": ("Visualizar agendamentos", "Permite abrir a tela de agendamentos."),
    "schedules.manage": ("Gerenciar agendamentos", "Permite criar, editar e excluir agendamentos."),
    "compartments.view": ("Visualizar compartimentos", "Permite abrir a tela de compartimentos."),
    "compartments.manage": ("Gerenciar compartimentos", "Permite sincronizar e importar compartimentos."),
    "deskmanager.view": ("Visualizar DeskManager", "Permite abrir a área do DeskManager."),
    "deskmanager.create_ticket": ("Abrir chamados no DeskManager", "Permite criar chamados no DeskManager."),
    "reports.view": ("Visualizar relatórios", "Permite abrir a tela de relatórios."),
    "audit.executions.view": ("Visualizar auditoria de execuções", "Permite abrir a auditoria de execuções."),
    "audit.access.view": ("Visualizar auditoria de acessos", "Permite abrir a auditoria de acessos."),
    "audit.settings.view": ("Visualizar auditoria de configurações", "Permite abrir a auditoria de configurações."),
    "admin.view": ("Visualizar administração", "Permite visualizar a área administrativa."),
    "admin.users.view": ("Visualizar usuários", "Permite abrir a tela de usuários."),
    "admin.users.manage": ("Gerenciar usuários", "Permite criar e editar usuários."),
    "admin.access_groups.view": ("Visualizar grupos de acesso", "Permite abrir a tela de grupos de acesso."),
    "admin.access_groups.manage": ("Criar/Editar grupos de acesso", "Permite criar e editar grupos de acesso."),
    "admin.permissions.view": ("Visualizar permissões diretas", "Permite visualizar a tabela de permissões diretas."),
    "admin.permissions.manage": ("Gerenciar permissões diretas", "Permite editar label e descrição das permissões."),
}


def upgrade() -> None:
    bind = op.get_bind()

    for permission_key, (new_label, new_description) in NEW_PERMISSION_METADATA.items():
        row = bind.execute(
            sa.text("SELECT id, label, description FROM access_permissions WHERE key = :key"),
            {"key": permission_key},
        ).mappings().first()
        if row is None:
            bind.execute(
                sa.text(
                    """
                    INSERT INTO access_permissions (id, key, label, description, created_at, updated_at)
                    VALUES (:id, :key, :label, :description, now(), now())
                    """
                ),
                {
                    "id": f"perm-{permission_key}",
                    "key": permission_key,
                    "label": new_label,
                    "description": new_description,
                },
            )
            continue

        old_metadata = OLD_PERMISSION_METADATA.get(permission_key)
        if old_metadata is None:
            continue

        if row["label"] == old_metadata[0] and row["description"] == old_metadata[1]:
            bind.execute(
                sa.text(
                    """
                    UPDATE access_permissions
                    SET label = :label, description = :description, updated_at = now()
                    WHERE key = :key
                    """
                ),
                {"key": permission_key, "label": new_label, "description": new_description},
            )


def downgrade() -> None:
    bind = op.get_bind()

    for permission_key, (old_label, old_description) in OLD_PERMISSION_METADATA.items():
        bind.execute(
            sa.text(
                """
                UPDATE access_permissions
                SET label = :label, description = :description, updated_at = now()
                WHERE key = :key
                """
            ),
            {"key": permission_key, "label": old_label, "description": old_description},
        )

    bind.execute(
        sa.text("DELETE FROM access_permissions WHERE key IN ('admin.permissions.view', 'admin.permissions.manage')")
    )
