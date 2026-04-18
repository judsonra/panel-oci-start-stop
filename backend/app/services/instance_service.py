import logging
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.compartment import Compartment
from app.models.execution_log import ExecutionLog, ExecutionSource, ExecutionStatus
from app.models.instance import Instance
from app.repositories.compartment_repository import CompartmentRepository
from app.repositories.execution_repository import ExecutionRepository
from app.repositories.instance_repository import InstanceRepository
from app.schemas.instance import InstanceCreate, InstanceUpdate
from app.services.audit_service import AuditService
from app.services.oci_cli import OCIVnicDetails, OCIService

logger = logging.getLogger(__name__)


@dataclass
class ImportInstanceResult:
    ocid: str
    name: str
    status: str
    message: str | None
    vcpu: float | None
    memory_gbs: float | None
    vnic_id: str | None
    public_ip: str | None
    private_ip: str | None
    oci_created_at: datetime | None


@dataclass
class ImportCompartmentResult:
    compartment_ocid: str
    compartment_name: str
    total_instances: int
    created: int
    updated: int
    unchanged: int
    failed: int
    instances: list[ImportInstanceResult]


@dataclass
class ImportAllCompartmentsResult:
    total_compartments: int
    processed_compartments: int
    total_instances: int
    created: int
    updated: int
    unchanged: int
    failed: int
    compartments: list[ImportCompartmentResult]


@dataclass
class ImportProgressSnapshot:
    total_compartments: int
    processed_compartments: int
    total_instances: int
    processed_instances: int
    created: int
    updated: int
    unchanged: int
    failed: int
    current_compartment_name: str | None
    current_instance_name: str | None


@dataclass
class StatusRefreshCompartmentResult:
    compartment_ocid: str
    compartment_name: str
    total_oci_instances: int
    matched_instances: int
    updated: int
    unchanged: int
    failed: int
    message: str | None = None


@dataclass
class StatusRefreshResult:
    total_compartments: int
    processed_compartments: int
    matched_instances: int
    updated: int
    unchanged: int
    failed: int
    compartments: list[StatusRefreshCompartmentResult]


@dataclass
class InstanceImportPreview:
    name: str
    ocid: str
    app_url: str | None
    environment: str | None
    customer_name: str | None
    domain: str | None
    name_prefix: str | None
    vcpu: float | None
    memory_gbs: float | None
    vnic_id: str | None
    public_ip: str | None
    private_ip: str | None
    compartment_ocid: str
    compartment_name: str
    oci_created_at: datetime | None
    already_registered: bool


@dataclass
class InstanceImportUpsertResult:
    mode: str
    instance: Instance | None = None
    preview: InstanceImportPreview | None = None


@dataclass
class InstanceRoutingData:
    app_url: str | None
    environment: str | None
    customer_name: str | None
    domain: str | None
    name_prefix: str | None


@dataclass
class ProxyResolveResult:
    decision: str
    instance_id: str | None
    ocid: str | None
    state: str | None
    message: str | None
    retry_after_seconds: int | None = None


@dataclass
class AppUrlBackfillItemResult:
    instance_id: str
    ocid: str
    name: str
    derived_app_url: str | None
    outcome: str
    message: str | None


@dataclass
class AppUrlBackfillResult:
    total: int
    processed: int
    updated: int
    skipped_existing: int
    unresolved: int
    failed: int
    items: list[AppUrlBackfillItemResult]


@dataclass
class AppUrlBackfillProgressSnapshot:
    total: int
    processed: int
    updated: int
    skipped_existing: int
    unresolved: int
    failed: int
    current_instance_name: str | None


class InstanceService:
    _start_attempt_lock = Lock()
    _last_start_attempt_by_instance_id: dict[str, float] = {}

    def __init__(self, session: Session, oci_service: OCIService) -> None:
        self.session = session
        self.instances = InstanceRepository(session)
        self.compartments = CompartmentRepository(session)
        self.executions = ExecutionRepository(session)
        self.oci_service = oci_service
        self.audit = AuditService(session)

    def list_instances(self) -> list[Instance]:
        return self.instances.list()

    def get_instance(self, instance_id: str) -> Instance:
        instance = self.instances.get(instance_id)
        if instance is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instance not found")
        return instance

    def create_instance(self, payload: InstanceCreate) -> Instance:
        if self.instances.get_by_ocid(payload.ocid):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Instance OCID already registered")
        if payload.compartment_id and self.session.get(Compartment, payload.compartment_id) is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Compartment not found")
        prepared_payload = self._prepare_instance_create_payload(payload)
        self._ensure_app_url_unique(prepared_payload.app_url)
        try:
            return self.instances.create(prepared_payload)
        except IntegrityError as exc:
            self.session.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Instance app_url already registered") from exc

    def get_import_preview(self, instance_ocid: str) -> InstanceImportPreview:
        existing = self.instances.get_by_ocid(instance_ocid)
        if existing is not None:
            compartment = existing.compartment or (self.session.get(Compartment, existing.compartment_id) if existing.compartment_id else None)
            return InstanceImportPreview(
                name=existing.name,
                ocid=existing.ocid,
                app_url=existing.app_url,
                environment=existing.environment,
                customer_name=existing.customer_name,
                domain=existing.domain,
                name_prefix=existing.name_prefix,
                vcpu=existing.vcpu,
                memory_gbs=existing.memory_gbs,
                vnic_id=existing.vnic_id,
                public_ip=existing.public_ip,
                private_ip=existing.private_ip,
                compartment_ocid=compartment.ocid if compartment is not None else existing.compartment_id or "",
                compartment_name=compartment.name if compartment is not None else "Compartimento não identificado",
                oci_created_at=existing.oci_created_at,
                already_registered=True,
            )

        return self._fetch_import_preview_from_oci(instance_ocid)

    def import_instance(self, ocid: str, description: str | None, enabled: bool, app_url: str | None = None) -> Instance:
        if self.instances.get_by_ocid(ocid):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Instance OCID already registered")

        preview = self.get_import_preview(ocid)
        compartment = self._ensure_compartment_cached(preview.compartment_ocid, preview.compartment_name)
        routing = self._resolve_routing_fields(
            preview.name,
            app_url=app_url,
            environment=preview.environment,
            customer_name=preview.customer_name,
            domain=preview.domain,
            name_prefix=preview.name_prefix,
        )
        self._ensure_app_url_unique(routing.app_url)
        created = self.instances.create(
            InstanceCreate(
                name=preview.name,
                ocid=preview.ocid,
                compartment_id=compartment.id,
                description=description,
                enabled=enabled,
                app_url=routing.app_url,
                environment=routing.environment,
                customer_name=routing.customer_name,
                domain=routing.domain,
                name_prefix=routing.name_prefix,
            )
        )
        created, _ = self.instances.apply_updates(
            created,
            {
                "vcpu": preview.vcpu,
                "memory_gbs": preview.memory_gbs,
                "vnic_id": preview.vnic_id,
                "public_ip": preview.public_ip,
                "private_ip": preview.private_ip,
                "oci_created_at": preview.oci_created_at,
            },
        )
        return created

    def import_instance_upsert(self, ocid: str) -> InstanceImportUpsertResult:
        preview = self._fetch_import_preview_from_oci(ocid)
        existing = self.instances.get_by_ocid(ocid)
        if existing is None:
            return InstanceImportUpsertResult(mode="not_registered", preview=preview)

        compartment = self._ensure_compartment_cached(preview.compartment_ocid, preview.compartment_name)
        routing = self._resolve_routing_fields(
            preview.name,
            app_url=preview.app_url,
            environment=preview.environment,
            customer_name=preview.customer_name,
            domain=preview.domain,
            name_prefix=preview.name_prefix,
        )
        self._ensure_app_url_unique(routing.app_url, excluding_instance_id=existing.id)
        updated, _ = self.instances.apply_updates(
            existing,
            {
                "name": preview.name,
                "compartment_id": compartment.id,
                "vcpu": preview.vcpu,
                "memory_gbs": preview.memory_gbs,
                "vnic_id": preview.vnic_id,
                "public_ip": preview.public_ip,
                "private_ip": preview.private_ip,
                "oci_created_at": preview.oci_created_at,
                "app_url": routing.app_url,
                "environment": routing.environment,
                "customer_name": routing.customer_name,
                "domain": routing.domain,
                "name_prefix": routing.name_prefix,
            },
        )
        return InstanceImportUpsertResult(mode="updated", instance=updated)

    def update_instance(self, instance_id: str, payload: InstanceUpdate) -> Instance:
        instance = self.get_instance(instance_id)
        if payload.compartment_id and self.session.get(Compartment, payload.compartment_id) is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Compartment not found")
        update_data = payload.model_dump(exclude_none=True)
        next_name = update_data.get("name", instance.name)
        routing = self._resolve_routing_fields(
            next_name,
            app_url=update_data.get("app_url", instance.app_url),
            environment=update_data.get("environment", instance.environment),
            customer_name=update_data.get("customer_name", instance.customer_name),
            domain=update_data.get("domain", instance.domain),
            name_prefix=update_data.get("name_prefix", instance.name_prefix),
        )
        update_data["app_url"] = routing.app_url
        update_data["environment"] = routing.environment
        update_data["customer_name"] = routing.customer_name
        update_data["domain"] = routing.domain
        update_data["name_prefix"] = routing.name_prefix
        self._ensure_app_url_unique(routing.app_url, excluding_instance_id=instance.id)
        try:
            return self.instances.update(instance, InstanceUpdate(**update_data))
        except IntegrityError as exc:
            self.session.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Instance app_url already registered") from exc

    def resolve_for_proxy(self, host: str, cooldown_seconds: int = 60) -> ProxyResolveResult:
        normalized_host = self._normalize_app_url(host)
        if not normalized_host:
            return ProxyResolveResult(
                decision="error",
                instance_id=None,
                ocid=None,
                state=None,
                message="Invalid host",
                retry_after_seconds=30,
            )
        instance = self.instances.get_by_app_url(normalized_host)
        if instance is None:
            return ProxyResolveResult(
                decision="not_found",
                instance_id=None,
                ocid=None,
                state=None,
                message="No mapped instance for host",
                retry_after_seconds=60,
            )
        if not instance.enabled:
            return ProxyResolveResult(
                decision="error",
                instance_id=instance.id,
                ocid=instance.ocid,
                state=instance.last_known_state,
                message="Instance is disabled",
                retry_after_seconds=60,
            )
        status_result = self.oci_service.get_status(instance.ocid)
        if not status_result.success:
            logger.warning(
                "proxy_resolve_status_failed host=%s instance_id=%s ocid=%s error=%s",
                normalized_host,
                instance.id,
                instance.ocid,
                status_result.parsed_error or status_result.stderr,
            )
            return ProxyResolveResult(
                decision="error",
                instance_id=instance.id,
                ocid=instance.ocid,
                state=instance.last_known_state,
                message=status_result.parsed_error or status_result.stderr or "status_check_failed",
                retry_after_seconds=30,
            )
        next_state = status_result.state or instance.last_known_state
        self._update_last_known_state(instance, next_state)
        if next_state == "RUNNING":
            logger.info("proxy_resolve_pass host=%s instance_id=%s ocid=%s", normalized_host, instance.id, instance.ocid)
            return ProxyResolveResult(
                decision="pass",
                instance_id=instance.id,
                ocid=instance.ocid,
                state=next_state,
                message="Instance is running",
            )
        if next_state in {"STARTING", "PROVISIONING"}:
            return ProxyResolveResult(
                decision="wait",
                instance_id=instance.id,
                ocid=instance.ocid,
                state=next_state,
                message="Instance is starting",
                retry_after_seconds=30,
            )
        if next_state == "STOPPED":
            if not self._can_trigger_start(instance.id, cooldown_seconds=max(cooldown_seconds, 0)):
                return ProxyResolveResult(
                    decision="wait",
                    instance_id=instance.id,
                    ocid=instance.ocid,
                    state="STARTING",
                    message="Start already requested recently",
                    retry_after_seconds=max(cooldown_seconds, 1),
                )
            start_result = self.oci_service.start_instance(instance.ocid)
            if not start_result.success:
                logger.warning(
                    "proxy_resolve_start_failed host=%s instance_id=%s ocid=%s error=%s",
                    normalized_host,
                    instance.id,
                    instance.ocid,
                    start_result.parsed_error or start_result.stderr,
                )
                return ProxyResolveResult(
                    decision="error",
                    instance_id=instance.id,
                    ocid=instance.ocid,
                    state=next_state,
                    message=start_result.parsed_error or start_result.stderr or "start_failed",
                    retry_after_seconds=30,
                )
            start_state = start_result.state or "STARTING"
            self._update_last_known_state(instance, start_state)
            logger.info(
                "proxy_resolve_wait_start_requested host=%s instance_id=%s ocid=%s state=%s",
                normalized_host,
                instance.id,
                instance.ocid,
                start_state,
            )
            return ProxyResolveResult(
                decision="wait",
                instance_id=instance.id,
                ocid=instance.ocid,
                state=start_state,
                message="Start command requested",
                retry_after_seconds=30,
            )
        return ProxyResolveResult(
            decision="wait",
            instance_id=instance.id,
            ocid=instance.ocid,
            state=next_state,
            message="Instance not ready",
            retry_after_seconds=30,
        )

    def backfill_missing_app_urls(
        self,
        progress_callback: Callable[[AppUrlBackfillProgressSnapshot], None] | None = None,
        job_id: str | None = None,
    ) -> AppUrlBackfillResult:
        # Target only legacy rows with missing host mapping.
        missing = [item for item in self.instances.list() if not item.app_url or not item.app_url.strip()]
        total = len(missing)
        processed = 0
        updated = 0
        skipped_existing = 0
        unresolved = 0
        failed = 0
        current_instance_name: str | None = None
        items: list[AppUrlBackfillItemResult] = []

        def emit_progress() -> None:
            if progress_callback is None:
                return
            progress_callback(
                AppUrlBackfillProgressSnapshot(
                    total=total,
                    processed=processed,
                    updated=updated,
                    skipped_existing=skipped_existing,
                    unresolved=unresolved,
                    failed=failed,
                    current_instance_name=current_instance_name,
                )
            )

        logger.info("app_url_backfill_started job_id=%s total_missing=%s", job_id or "sync", total)
        emit_progress()

        for instance in missing:
            current_instance_name = instance.name
            derived = self.derive_routing_fields(instance.name)
            try:
                latest = self.instances.get(instance.id)
                if latest is None:
                    failed += 1
                    items.append(
                        AppUrlBackfillItemResult(
                            instance_id=instance.id,
                            ocid=instance.ocid,
                            name=instance.name,
                            derived_app_url=derived.app_url,
                            outcome="failed",
                            message="instance_not_found_during_backfill",
                        )
                    )
                    continue

                if latest.app_url and latest.app_url.strip():
                    skipped_existing += 1
                    items.append(
                        AppUrlBackfillItemResult(
                            instance_id=latest.id,
                            ocid=latest.ocid,
                            name=latest.name,
                            derived_app_url=derived.app_url,
                            outcome="skipped_existing",
                            message="app_url_already_set",
                        )
                    )
                    continue

                if not derived.app_url:
                    unresolved += 1
                    items.append(
                        AppUrlBackfillItemResult(
                            instance_id=latest.id,
                            ocid=latest.ocid,
                            name=latest.name,
                            derived_app_url=None,
                            outcome="unresolved",
                            message="could_not_derive_app_url_from_instance_name",
                        )
                    )
                    continue

                mapped = self.instances.get_by_app_url(derived.app_url)
                if mapped is not None and mapped.id != latest.id:
                    unresolved += 1
                    items.append(
                        AppUrlBackfillItemResult(
                            instance_id=latest.id,
                            ocid=latest.ocid,
                            name=latest.name,
                            derived_app_url=derived.app_url,
                            outcome="unresolved",
                            message=f"app_url_conflict_with_instance_id:{mapped.id}",
                        )
                    )
                    continue

                _, changed = self.instances.apply_updates(
                    latest,
                    {
                        "app_url": derived.app_url,
                        "environment": latest.environment or derived.environment,
                        "customer_name": latest.customer_name or derived.customer_name,
                        "domain": latest.domain or derived.domain,
                        "name_prefix": latest.name_prefix or derived.name_prefix,
                    },
                )
                if changed:
                    updated += 1
                    items.append(
                        AppUrlBackfillItemResult(
                            instance_id=latest.id,
                            ocid=latest.ocid,
                            name=latest.name,
                            derived_app_url=derived.app_url,
                            outcome="updated",
                            message=None,
                        )
                    )
                else:
                    skipped_existing += 1
                    items.append(
                        AppUrlBackfillItemResult(
                            instance_id=latest.id,
                            ocid=latest.ocid,
                            name=latest.name,
                            derived_app_url=derived.app_url,
                            outcome="skipped_existing",
                            message="no_changes_required",
                        )
                    )
            except Exception as exc:
                self.session.rollback()
                failed += 1
                logger.exception(
                    "app_url_backfill_item_failed job_id=%s instance_id=%s ocid=%s error=%s",
                    job_id or "sync",
                    instance.id,
                    instance.ocid,
                    str(exc),
                )
                items.append(
                    AppUrlBackfillItemResult(
                        instance_id=instance.id,
                        ocid=instance.ocid,
                        name=instance.name,
                        derived_app_url=derived.app_url,
                        outcome="failed",
                        message=str(exc),
                    )
                )
            finally:
                processed += 1
                emit_progress()

        current_instance_name = None
        result = AppUrlBackfillResult(
            total=total,
            processed=processed,
            updated=updated,
            skipped_existing=skipped_existing,
            unresolved=unresolved,
            failed=failed,
            items=items,
        )
        logger.info(
            "app_url_backfill_finished job_id=%s total=%s processed=%s updated=%s skipped_existing=%s unresolved=%s failed=%s",
            job_id or "sync",
            result.total,
            result.processed,
            result.updated,
            result.skipped_existing,
            result.unresolved,
            result.failed,
        )
        return result

    def delete_instance(self, instance_id: str, *, actor_email: str | None = None, actor_user_id: str | None = None) -> None:
        instance = self.get_instance(instance_id)
        before_data = {
            "id": instance.id,
            "name": instance.name,
            "ocid": instance.ocid,
            "compartment_id": instance.compartment_id,
        }
        self.instances.delete(instance)
        self.audit.log_configuration_event(
            event_type="instance_deleted",
            entity_type="instance",
            entity_id=before_data["id"],
            actor_email=actor_email,
            actor_user_id=actor_user_id,
            summary=f"Instance {before_data['name']} deleted",
            before_data=before_data,
        )

    def get_status(self, instance_id: str) -> ExecutionLog:
        instance = self.get_instance(instance_id)
        return self._execute_action(instance, "status", ExecutionSource.manual)

    def start(self, instance_id: str, source: ExecutionSource = ExecutionSource.manual) -> ExecutionLog:
        instance = self.get_instance(instance_id)
        self._ensure_start_allowed(instance)
        return self._execute_action(instance, "start", source)

    def stop(self, instance_id: str, source: ExecutionSource = ExecutionSource.manual) -> ExecutionLog:
        instance = self.get_instance(instance_id)
        return self._execute_action(instance, "stop", source)

    def restart(self, instance_id: str, source: ExecutionSource = ExecutionSource.manual) -> ExecutionLog:
        instance = self.get_instance(instance_id)
        return self._execute_action(instance, "restart", source)

    def get_instance_vnic(self, instance_ocid: str) -> str | None:
        return self.oci_service.get_instance_vnic_id(instance_ocid)

    def get_vnic_details(self, vnic_id: str) -> OCIVnicDetails:
        return self.oci_service.get_vnic_details(vnic_id)

    def import_all_compartment_instances(
        self,
        progress_callback: Callable[[ImportProgressSnapshot], None] | None = None,
        job_id: str | None = None,
    ) -> ImportAllCompartmentsResult:
        compartments = [item for item in self.compartments.list() if item.active]
        results: list[ImportCompartmentResult] = []
        processed_compartments = 0
        processed_instances = 0
        created = 0
        updated = 0
        unchanged = 0
        failed = 0
        total_instances = 0
        current_compartment_name: str | None = None
        current_instance_name: str | None = None

        def emit_progress() -> None:
            if progress_callback is None:
                return
            progress_callback(
                ImportProgressSnapshot(
                    total_compartments=len(compartments),
                    processed_compartments=processed_compartments,
                    total_instances=total_instances,
                    processed_instances=processed_instances,
                    created=created,
                    updated=updated,
                    unchanged=unchanged,
                    failed=failed,
                    current_compartment_name=current_compartment_name,
                    current_instance_name=current_instance_name,
                )
            )

        logger.info(
            "Automatic registration job started [job_id=%s total_compartments=%s]",
            job_id or "sync",
            len(compartments),
        )
        emit_progress()

        for compartment in compartments:
            current_compartment_name = compartment.name
            current_instance_name = None
            logger.info(
                "Automatic registration job processing compartment [job_id=%s compartment_ocid=%s compartment_name=%s]",
                job_id or "sync",
                compartment.ocid,
                compartment.name,
            )

            try:
                oci_instances = self.oci_service.list_instances_by_compartment(compartment.ocid)
                total_instances += len(oci_instances)
                logger.info(
                    "Automatic registration job listed compartment instances [job_id=%s compartment_ocid=%s compartment_name=%s total_instances=%s]",
                    job_id or "sync",
                    compartment.ocid,
                    compartment.name,
                    len(oci_instances),
                )
                emit_progress()
            except RuntimeError as exc:
                failed += 1
                processed_compartments += 1
                logger.info(
                    "Automatic registration job failed to list compartment instances [job_id=%s compartment_ocid=%s compartment_name=%s error=%s]",
                    job_id or "sync",
                    compartment.ocid,
                    compartment.name,
                    str(exc),
                )
                results.append(
                    ImportCompartmentResult(
                        compartment_ocid=compartment.ocid,
                        compartment_name=compartment.name,
                        total_instances=0,
                        created=0,
                        updated=0,
                        unchanged=0,
                        failed=1,
                        instances=[
                            ImportInstanceResult(
                                ocid="",
                                name=compartment.name,
                                status="failed",
                                message=str(exc),
                                vcpu=None,
                                memory_gbs=None,
                                vnic_id=None,
                                public_ip=None,
                                private_ip=None,
                                oci_created_at=None,
                            )
                        ],
                    )
                )
                emit_progress()
                continue

            compartment_results: list[ImportInstanceResult] = []
            compartment_created = 0
            compartment_updated = 0
            compartment_unchanged = 0
            compartment_failed = 0

            for remote in oci_instances:
                current_instance_name = remote.name
                logger.info(
                    "Automatic registration job processing instance [job_id=%s compartment_ocid=%s compartment_name=%s instance_ocid=%s instance_name=%s]",
                    job_id or "sync",
                    compartment.ocid,
                    compartment.name,
                    remote.ocid,
                    remote.name,
                )
                try:
                    vnic_id = self.oci_service.get_instance_vnic_id(remote.ocid)
                    vnic_details = self.oci_service.get_vnic_details(vnic_id) if vnic_id else OCIVnicDetails(vnic_id="", public_ip=None, private_ip=None)
                    status_name = self._upsert_imported_instance(
                        compartment.id,
                        remote.name,
                        remote.ocid,
                        remote.vcpu,
                        remote.memory_gbs,
                        vnic_id,
                        vnic_details.public_ip,
                        vnic_details.private_ip,
                        remote.oci_created_at,
                    )
                    if status_name == "created":
                        created += 1
                        compartment_created += 1
                    elif status_name == "updated":
                        updated += 1
                        compartment_updated += 1
                    else:
                        unchanged += 1
                        compartment_unchanged += 1
                    logger.info(
                        "Automatic registration job processed instance [job_id=%s compartment_ocid=%s compartment_name=%s instance_ocid=%s instance_name=%s status=%s created=%s updated=%s unchanged=%s failed=%s]",
                        job_id or "sync",
                        compartment.ocid,
                        compartment.name,
                        remote.ocid,
                        remote.name,
                        status_name,
                        created,
                        updated,
                        unchanged,
                        failed,
                    )
                    compartment_results.append(
                        ImportInstanceResult(
                            ocid=remote.ocid,
                            name=remote.name,
                            status=status_name,
                            message=None,
                            vcpu=remote.vcpu,
                            memory_gbs=remote.memory_gbs,
                            vnic_id=vnic_id,
                            public_ip=vnic_details.public_ip,
                            private_ip=vnic_details.private_ip,
                            oci_created_at=remote.oci_created_at,
                        )
                    )
                except RuntimeError as exc:
                    failed += 1
                    compartment_failed += 1
                    logger.info(
                        "Automatic registration job failed instance [job_id=%s compartment_ocid=%s compartment_name=%s instance_ocid=%s instance_name=%s error=%s]",
                        job_id or "sync",
                        compartment.ocid,
                        compartment.name,
                        remote.ocid,
                        remote.name,
                        str(exc),
                    )
                    compartment_results.append(
                        ImportInstanceResult(
                            ocid=remote.ocid,
                            name=remote.name,
                            status="failed",
                            message=str(exc),
                            vcpu=remote.vcpu,
                            memory_gbs=remote.memory_gbs,
                            vnic_id=None,
                            public_ip=None,
                            private_ip=None,
                            oci_created_at=remote.oci_created_at,
                        )
                    )
                finally:
                    processed_instances += 1
                    emit_progress()

            current_instance_name = None
            processed_compartments += 1
            compartment_result = ImportCompartmentResult(
                compartment_ocid=compartment.ocid,
                compartment_name=compartment.name,
                total_instances=len(oci_instances),
                created=compartment_created,
                updated=compartment_updated,
                unchanged=compartment_unchanged,
                failed=compartment_failed,
                instances=compartment_results,
            )
            results.append(compartment_result)
            logger.info(
                "Automatic registration job finished compartment [job_id=%s compartment_ocid=%s compartment_name=%s total_instances=%s created=%s updated=%s unchanged=%s failed=%s]",
                job_id or "sync",
                compartment.ocid,
                compartment.name,
                compartment_result.total_instances,
                compartment_result.created,
                compartment_result.updated,
                compartment_result.unchanged,
                compartment_result.failed,
            )
            emit_progress()

        result = ImportAllCompartmentsResult(
            total_compartments=len(compartments),
            processed_compartments=processed_compartments,
            total_instances=total_instances,
            created=created,
            updated=updated,
            unchanged=unchanged,
            failed=failed,
            compartments=results,
        )
        logger.info(
            "Automatic registration job finished [job_id=%s processed_compartments=%s total_compartments=%s processed_instances=%s total_instances=%s created=%s updated=%s unchanged=%s failed=%s]",
            job_id or "sync",
            result.processed_compartments,
            result.total_compartments,
            processed_instances,
            result.total_instances,
            result.created,
            result.updated,
            result.unchanged,
            result.failed,
        )
        return result

    def refresh_statuses_by_compartment(self) -> StatusRefreshResult:
        compartments = [item for item in self.compartments.list() if item.active]
        compartment_ids = {item.id for item in compartments}
        local_instances = [item for item in self.instances.list() if item.compartment_id in compartment_ids]
        instances_by_compartment_id: dict[str, list[Instance]] = {}
        for instance in local_instances:
            if instance.compartment_id is None:
                continue
            instances_by_compartment_id.setdefault(instance.compartment_id, []).append(instance)

        results: list[StatusRefreshCompartmentResult] = []
        processed_compartments = 0
        matched_instances = 0
        updated = 0
        unchanged = 0
        failed = 0

        for compartment in compartments:
            try:
                oci_instances = self.oci_service.list_instances_by_compartment(compartment.ocid)
            except RuntimeError as exc:
                processed_compartments += 1
                failed += 1
                results.append(
                    StatusRefreshCompartmentResult(
                        compartment_ocid=compartment.ocid,
                        compartment_name=compartment.name,
                        total_oci_instances=0,
                        matched_instances=0,
                        updated=0,
                        unchanged=0,
                        failed=1,
                        message=str(exc),
                    )
                )
                continue

            state_by_ocid = {
                item.ocid: item.lifecycle_state
                for item in oci_instances
                if item.lifecycle_state is not None
            }
            local_compartment_instances = instances_by_compartment_id.get(compartment.id, [])
            compartment_matched = 0
            compartment_updated = 0
            compartment_unchanged = 0

            for instance in local_compartment_instances:
                if instance.ocid not in state_by_ocid:
                    continue
                compartment_matched += 1
                next_state = state_by_ocid[instance.ocid]
                if instance.last_known_state != next_state:
                    instance.last_known_state = next_state
                    self.session.add(instance)
                    compartment_updated += 1
                else:
                    compartment_unchanged += 1

            if compartment_updated > 0:
                self.session.commit()

            processed_compartments += 1
            matched_instances += compartment_matched
            updated += compartment_updated
            unchanged += compartment_unchanged
            results.append(
                StatusRefreshCompartmentResult(
                    compartment_ocid=compartment.ocid,
                    compartment_name=compartment.name,
                    total_oci_instances=len(oci_instances),
                    matched_instances=compartment_matched,
                    updated=compartment_updated,
                    unchanged=compartment_unchanged,
                    failed=0,
                )
            )

        return StatusRefreshResult(
            total_compartments=len(compartments),
            processed_compartments=processed_compartments,
            matched_instances=matched_instances,
            updated=updated,
            unchanged=unchanged,
            failed=failed,
            compartments=results,
        )

    def _upsert_imported_instance(
        self,
        compartment_id: str,
        name: str,
        ocid: str,
        vcpu: float | None,
        memory_gbs: float | None,
        vnic_id: str | None,
        public_ip: str | None,
        private_ip: str | None,
        oci_created_at: datetime | None,
    ) -> str:
        routing = self.derive_routing_fields(name)
        existing = self.instances.get_by_ocid(ocid)
        excluding_instance_id = existing.id if existing is not None else None
        self._ensure_app_url_unique(routing.app_url, excluding_instance_id=excluding_instance_id)
        if existing is None:
            self.instances.create(
                InstanceCreate(
                    name=name,
                    ocid=ocid,
                    app_url=routing.app_url,
                    environment=routing.environment,
                    customer_name=routing.customer_name,
                    domain=routing.domain,
                    name_prefix=routing.name_prefix,
                    compartment_id=compartment_id,
                    description=None,
                    enabled=True,
                )
            )
            created_instance = self.instances.get_by_ocid(ocid)
            if created_instance is not None:
                self.instances.apply_updates(
                    created_instance,
                    {
                        "vcpu": vcpu,
                        "memory_gbs": memory_gbs,
                        "compartment_id": compartment_id,
                        "vnic_id": vnic_id,
                        "public_ip": public_ip,
                        "private_ip": private_ip,
                        "oci_created_at": oci_created_at,
                    },
                )
            return "created"

        _, changed = self.instances.apply_updates(
            existing,
            {
                "name": name,
                "compartment_id": compartment_id,
                "vcpu": vcpu,
                "memory_gbs": memory_gbs,
                "vnic_id": vnic_id,
                "public_ip": public_ip,
                "private_ip": private_ip,
                "oci_created_at": oci_created_at,
                "environment": routing.environment,
                "customer_name": routing.customer_name,
                "domain": routing.domain,
                "name_prefix": routing.name_prefix,
                "app_url": routing.app_url,
            },
        )
        return "updated" if changed else "unchanged"

    def _fetch_import_preview_from_oci(self, instance_ocid: str) -> InstanceImportPreview:
        try:
            details = self.oci_service.get_instance_details(instance_ocid)
            vnic_id = self.oci_service.get_instance_vnic_id(instance_ocid)
            vnic_details = self.oci_service.get_vnic_details(vnic_id) if vnic_id else OCIVnicDetails(vnic_id="", public_ip=None, private_ip=None)
        except RuntimeError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

        compartment = self._ensure_compartment_cached(details.compartment_ocid)
        routing = self.derive_routing_fields(details.name)
        return InstanceImportPreview(
            name=details.name,
            ocid=details.ocid,
            app_url=routing.app_url,
            environment=routing.environment,
            customer_name=routing.customer_name,
            domain=routing.domain,
            name_prefix=routing.name_prefix,
            vcpu=details.vcpu,
            memory_gbs=details.memory_gbs,
            vnic_id=vnic_id,
            public_ip=vnic_details.public_ip,
            private_ip=vnic_details.private_ip,
            compartment_ocid=details.compartment_ocid,
            compartment_name=compartment.name,
            oci_created_at=details.oci_created_at,
            already_registered=False,
        )

    def _prepare_instance_create_payload(self, payload: InstanceCreate) -> InstanceCreate:
        routing = self._resolve_routing_fields(
            payload.name,
            app_url=payload.app_url,
            environment=payload.environment,
            customer_name=payload.customer_name,
            domain=payload.domain,
            name_prefix=payload.name_prefix,
        )
        return payload.model_copy(
            update={
                "app_url": routing.app_url,
                "environment": routing.environment,
                "customer_name": routing.customer_name,
                "domain": routing.domain,
                "name_prefix": routing.name_prefix,
            }
        )

    def _resolve_routing_fields(
        self,
        name: str,
        *,
        app_url: str | None,
        environment: str | None,
        customer_name: str | None,
        domain: str | None,
        name_prefix: str | None,
    ) -> InstanceRoutingData:
        derived = self.derive_routing_fields(name)
        return InstanceRoutingData(
            app_url=self._normalize_app_url(app_url) or derived.app_url,
            environment=self._normalize_environment(environment) or derived.environment,
            customer_name=self._normalize_customer_name(customer_name) or derived.customer_name,
            domain=self._normalize_domain(domain) or derived.domain,
            name_prefix=self._normalize_name_prefix(name_prefix) or derived.name_prefix,
        )

    @classmethod
    def derive_routing_fields(cls, instance_name: str) -> InstanceRoutingData:
        normalized_name = instance_name.strip()
        upper = normalized_name.upper()
        environment: str | None = None
        marker_index = -1
        marker_size = 0
        if "HMG-" in upper:
            environment = "HMG"
            marker_index = upper.index("HMG-")
            marker_size = 4
        elif "PRD-" in upper:
            environment = "PRD"
            marker_index = upper.index("PRD-")
            marker_size = 4

        customer_name: str | None = None
        if marker_index >= 0:
            raw_customer = normalized_name[marker_index + marker_size :].strip()
            customer_name = cls._normalize_customer_name(raw_customer)

        domain: str | None = None
        name_prefix: str | None = None
        if upper.startswith("OCIXDOC"):
            name_prefix = "OCIXDOC"
            domain = "docnix.com.br"
        elif upper.startswith("OCIXPM"):
            name_prefix = "OCIXPM"
            domain = "pmrun.com.br"
        elif "-" in normalized_name:
            name_prefix = normalized_name.split("-", 1)[0].strip().upper() or None

        app_url: str | None = None
        if customer_name and domain:
            app_host = f"{customer_name}hmg.{domain}" if environment == "HMG" else f"{customer_name}.{domain}"
            app_url = cls._normalize_app_url(app_host)

        return InstanceRoutingData(
            app_url=app_url,
            environment=environment,
            customer_name=customer_name,
            domain=domain,
            name_prefix=name_prefix,
        )

    def _ensure_app_url_unique(self, app_url: str | None, excluding_instance_id: str | None = None) -> None:
        if not app_url:
            return
        existing = self.instances.get_by_app_url(app_url)
        if existing is None:
            return
        if excluding_instance_id and existing.id == excluding_instance_id:
            return
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Instance app_url already registered")

    def _update_last_known_state(self, instance: Instance, next_state: str | None) -> None:
        if next_state is None or instance.last_known_state == next_state:
            return
        instance.last_known_state = next_state
        self.session.add(instance)
        self.session.commit()

    @classmethod
    def _can_trigger_start(cls, instance_id: str, cooldown_seconds: int) -> bool:
        if cooldown_seconds <= 0:
            return True
        now = time.monotonic()
        with cls._start_attempt_lock:
            last = cls._last_start_attempt_by_instance_id.get(instance_id)
            if last is not None and (now - last) < cooldown_seconds:
                return False
            cls._last_start_attempt_by_instance_id[instance_id] = now
            # Drop stale keys to avoid unbounded growth.
            stale_limit = now - max(cooldown_seconds * 5, 300)
            stale_keys = [key for key, value in cls._last_start_attempt_by_instance_id.items() if value < stale_limit]
            for key in stale_keys:
                del cls._last_start_attempt_by_instance_id[key]
            return True

    @staticmethod
    def _normalize_customer_name(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if not normalized:
            return None
        normalized = re.sub(r"[^a-z0-9-]+", "-", normalized)
        normalized = re.sub(r"-{2,}", "-", normalized).strip("-")
        return normalized or None

    @staticmethod
    def _normalize_environment(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        return normalized if normalized in {"HMG", "PRD"} else None

    @staticmethod
    def _normalize_domain(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower().rstrip(".")
        if not normalized:
            return None
        if not re.fullmatch(r"[a-z0-9.-]+\.[a-z]{2,63}", normalized):
            return None
        return normalized

    @staticmethod
    def _normalize_name_prefix(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        return normalized or None

    @staticmethod
    def _normalize_app_url(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if not normalized:
            return None
        normalized = re.sub(r"^https?://", "", normalized)
        normalized = normalized.split("/", 1)[0].strip().rstrip(".")
        if ":" in normalized:
            normalized = normalized.split(":", 1)[0]
        if not re.fullmatch(r"[a-z0-9.-]+\.[a-z]{2,63}", normalized):
            return None
        return normalized

    def _execute_action(self, instance: Instance, action: str, source: ExecutionSource) -> ExecutionLog:
        if not instance.enabled:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Instance is disabled")
        started_at = datetime.now(timezone.utc)
        execution = ExecutionLog(
            instance_id=instance.id,
            action=action,
            source=source,
            status=ExecutionStatus.pending,
            started_at=started_at,
        )
        execution = self.executions.create(execution)
        if action == "start":
            command_result = self.oci_service.start_instance(instance.ocid)
        elif action == "stop":
            command_result = self.oci_service.stop_instance(instance.ocid)
        elif action == "restart":
            command_result = self.oci_service.restart_instance(instance.ocid)
        else:
            command_result = self.oci_service.get_status(instance.ocid)
        execution.status = ExecutionStatus.success if command_result.success else ExecutionStatus.failed
        execution.stdout_summary = command_result.stdout
        execution.stderr_summary = command_result.parsed_error or command_result.stderr
        execution.finished_at = datetime.now(timezone.utc)
        self.executions.update(execution)
        instance.last_known_state = command_result.state or instance.last_known_state
        self.session.add(instance)
        self.session.commit()
        return execution

    def _ensure_start_allowed(self, instance: Instance) -> None:
        if not instance.enabled:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Instance is disabled")
        if instance.last_known_state != "STOPPED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Instance can only be started when enabled and with status STOPPED",
            )

    def _ensure_compartment_cached(self, compartment_ocid: str, known_name: str | None = None) -> Compartment:
        compartment = self.compartments.get_by_ocid(compartment_ocid)
        resolved_name = known_name or (compartment.name if compartment is not None else None)

        if resolved_name is None or (compartment is not None and compartment.active is False):
            resolved_name = self._lookup_compartment_name(compartment_ocid) or resolved_name

        if resolved_name is None:
            resolved_name = compartment_ocid

        if compartment is None:
            return self.compartments.create(name=resolved_name, ocid=compartment_ocid, active=True)

        if compartment.name != resolved_name or compartment.active is False:
            return self.compartments.update(compartment, name=resolved_name, active=True)

        return compartment

    def _lookup_compartment_name(self, compartment_ocid: str) -> str | None:
        try:
            compartments = self.oci_service.list_compartments()
        except RuntimeError:
            return None

        for item in compartments:
            if item.ocid == compartment_ocid:
                return item.name
        return None
