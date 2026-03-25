import configparser
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from app.core.config import Settings, get_settings


@dataclass
class UsageCostEntry:
    usage_date: date
    compartment_id: str | None
    compartment_name: str | None
    service: str | None
    sku_name: str | None
    resource_id: str | None
    resource_name: str | None
    currency: str | None
    amount: Decimal


@dataclass
class UsageCostDataset:
    currency: str | None
    entries: list[UsageCostEntry]

    @property
    def total_amount(self) -> Decimal:
        return sum((entry.amount for entry in self.entries), Decimal("0"))


class OCIUsageService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    @property
    def config_file(self) -> str:
        return f"{self.settings.oci_config_dir}/config"

    def resolve_tenant_id(self) -> str:
        if self.settings.oci_tenant_id:
            return self.settings.oci_tenant_id
        config_path = Path(self.config_file)
        if not config_path.is_file():
            raise RuntimeError(f"OCI config file not found at '{self.config_file}'")
        parser = configparser.ConfigParser()
        parser.read(config_path)
        if self.settings.oci_cli_profile not in parser:
            raise RuntimeError(f"OCI profile '{self.settings.oci_cli_profile}' not found in '{self.config_file}'")
        tenant_id = parser[self.settings.oci_cli_profile].get("tenancy")
        if not tenant_id:
            raise RuntimeError("OCI tenancy not configured. Set OCI_TENANT_ID or configure tenancy in OCI config.")
        return tenant_id

    def fetch_cost_by_compartment(self, year: int, month: int) -> UsageCostDataset:
        period_start = date(year, month, 1)
        period_end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
        summary_group_by = json.dumps(["compartmentId", "compartmentName", "service", "skuName"])
        resource_group_by = json.dumps(["compartmentId", "compartmentName", "service", "resourceId"])

        summary_payload = self._run(
            [
                "usage-api",
                "usage-summary",
                "request-summarized-usages",
                "--tenant-id",
                self.resolve_tenant_id(),
                "--time-usage-started",
                f"{period_start.isoformat()}T00:00:00Z",
                "--time-usage-ended",
                f"{period_end.isoformat()}T00:00:00Z",
                "--granularity",
                "DAILY",
                "--compartment-depth",
                "6",
                "--query-type",
                "COST",
                "--group-by",
                summary_group_by,
                "--profile",
                self.settings.oci_cli_profile,
                "--output",
                "json",
            ]
        )
        summary_dataset = self._parse_usage_summary(summary_payload)

        try:
            resource_payload = self._run(
                [
                    "usage-api",
                    "usage-summary",
                    "request-summarized-usages",
                    "--tenant-id",
                    self.resolve_tenant_id(),
                    "--time-usage-started",
                    f"{period_start.isoformat()}T00:00:00Z",
                    "--time-usage-ended",
                    f"{period_end.isoformat()}T00:00:00Z",
                    "--granularity",
                    "DAILY",
                    "--compartment-depth",
                    "6",
                    "--query-type",
                    "COST",
                    "--group-by",
                    resource_group_by,
                    "--profile",
                    self.settings.oci_cli_profile,
                    "--output",
                    "json",
                ]
            )
        except RuntimeError:
            return summary_dataset

        return self._merge_usage_datasets(summary_dataset, self._parse_usage_summary(resource_payload))

    def _run(self, args: list[str]) -> dict:
        command = [self.settings.oci_cli_path, *args]
        if shutil.which(self.settings.oci_cli_path) is None:
            raise RuntimeError(f"OCI CLI not found in PATH for '{self.settings.oci_cli_path}'")
        if not Path(self.config_file).is_file():
            raise RuntimeError(f"OCI config file not found at '{self.config_file}'")
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    "OCI_CLI_CONFIG_FILE": self.config_file,
                    "SUPPRESS_LABEL_WARNING": "True" if self.settings.suppress_oci_label_warning else "False",
                },
                check=False,
                cwd=self.settings.oci_config_dir,
            )
        except OSError as exc:
            raise RuntimeError(str(exc)) from exc
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or "OCI usage summary command failed")
        try:
            return json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError("OCI usage summary did not return valid JSON") from exc

    def _parse_usage_summary(self, payload: dict) -> UsageCostDataset:
        data = payload.get("data") or payload
        raw_items = data.get("items") or []
        entries: list[UsageCostEntry] = []
        detected_currency = self._string_value(data, "currency", "currencyCode")
        for item in raw_items:
            amount = self._decimal_value(
                item,
                "computed-amount",
                "computedAmount",
                "cost",
                "myCost",
                "netCost",
                "attributed-cost",
                "attributedCost",
            )
            if amount is None:
                continue
            usage_date = self._date_value(item, "time-usage-started", "timeUsageStarted", "usageDate")
            if usage_date is None:
                continue
            currency = self._string_value(item, "currency", "currencyCode") or detected_currency
            detected_currency = detected_currency or currency
            entries.append(
                UsageCostEntry(
                    usage_date=usage_date,
                    compartment_id=self._string_value(item, "compartmentId", "compartment-id"),
                    compartment_name=self._string_value(item, "compartmentName", "compartment-name") or "Compartimento não informado",
                    service=self._string_value(item, "service", "serviceName"),
                    sku_name=self._string_value(item, "skuName", "sku-name", "skuPartNumber"),
                    resource_id=self._string_value(item, "resourceId", "resource-id"),
                    resource_name=self._string_value(item, "resourceName", "resource-name"),
                    currency=currency,
                    amount=amount,
                )
            )
        return UsageCostDataset(currency=detected_currency, entries=entries)

    @staticmethod
    def _merge_usage_datasets(summary_dataset: UsageCostDataset, resource_dataset: UsageCostDataset) -> UsageCostDataset:
        if not resource_dataset.entries:
            return summary_dataset

        resource_lookup: dict[tuple[date, str | None, str | None, str | None], UsageCostEntry] = {}
        for entry in resource_dataset.entries:
            key = (entry.usage_date, entry.compartment_id, entry.compartment_name, entry.service)
            existing = resource_lookup.get(key)
            if existing is None or entry.amount >= existing.amount:
                resource_lookup[key] = entry

        merged_entries: list[UsageCostEntry] = []
        for entry in summary_dataset.entries:
            resource_match = resource_lookup.get((entry.usage_date, entry.compartment_id, entry.compartment_name, entry.service))
            merged_entries.append(
                UsageCostEntry(
                    usage_date=entry.usage_date,
                    compartment_id=entry.compartment_id,
                    compartment_name=entry.compartment_name,
                    service=entry.service,
                    sku_name=entry.sku_name,
                    resource_id=resource_match.resource_id if resource_match else None,
                    resource_name=resource_match.resource_name if resource_match else None,
                    currency=entry.currency,
                    amount=entry.amount,
                )
            )

        return UsageCostDataset(currency=summary_dataset.currency or resource_dataset.currency, entries=merged_entries)

    @staticmethod
    def _string_value(item: dict, *keys: str) -> str | None:
        for key in keys:
            if key in item and item[key] not in (None, ""):
                return str(item[key])
        dimensions = item.get("dimensions") if isinstance(item.get("dimensions"), dict) else None
        if dimensions:
            for key in keys:
                if key in dimensions and dimensions[key] not in (None, ""):
                    return str(dimensions[key])
        return None

    @classmethod
    def _decimal_value(cls, item: dict, *keys: str) -> Decimal | None:
        for key in keys:
            value = item.get(key)
            decimal_value = cls._to_decimal(value)
            if decimal_value is not None:
                return decimal_value
        dimensions = item.get("dimensions") if isinstance(item.get("dimensions"), dict) else None
        if dimensions:
            for key in keys:
                decimal_value = cls._to_decimal(dimensions.get(key))
                if decimal_value is not None:
                    return decimal_value
        return None

    @staticmethod
    def _to_decimal(value: object) -> Decimal | None:
        if value in (None, ""):
            return None
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            return None

    @staticmethod
    def _date_value(item: dict, *keys: str) -> date | None:
        for key in keys:
            value = item.get(key)
            if not value:
                continue
            try:
                normalized = str(value).replace("Z", "+00:00")
                return datetime.fromisoformat(normalized).astimezone(UTC).date()
            except ValueError:
                continue
        return None
