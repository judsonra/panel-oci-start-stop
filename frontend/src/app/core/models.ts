export interface InstanceModel {
    id: string;
    name: string;
    ocid: string;
    description?: string | null;
    enabled: boolean;
    last_known_state?: string | null;
    created_at: string;
    updated_at: string;
}

export interface CompartmentModel {
    id: string;
    name: string;
    ocid: string;
    active: boolean;
    created_at: string;
    updated_at: string;
}

export interface ScheduleModel {
    id: string;
    instance_id: string;
    instance_name?: string | null;
    type: 'one_time' | 'recurring';
    action: 'start' | 'stop' | 'restart';
    run_at_utc?: string | null;
    days_of_week?: number[] | null;
    time_utc?: string | null;
    enabled: boolean;
    last_triggered_at?: string | null;
}

export interface ExecutionModel {
    id: string;
    instance_id: string;
    instance_name?: string | null;
    instance_state?: string | null;
    action: string;
    source: 'manual' | 'schedule';
    status: 'pending' | 'success' | 'failed';
    stdout_summary?: string | null;
    stderr_summary?: string | null;
    started_at: string;
    finished_at?: string | null;
}

export interface ReportDailyCostModel {
    date: string;
    amount: number;
}

export interface ReportResourceCostModel {
    service?: string | null;
    sku_name?: string | null;
    resource_id?: string | null;
    resource_name?: string | null;
    total_amount: number;
}

export interface ReportCompartmentCostModel {
    compartment_id?: string | null;
    compartment_name?: string | null;
    total_amount: number;
    daily_costs: ReportDailyCostModel[];
    resources: ReportResourceCostModel[];
}

export interface CostByCompartmentReportModel {
    year: number;
    month: number;
    currency?: string | null;
    source: 'cache' | 'oci';
    sync_status: string;
    available: boolean;
    last_refreshed_at?: string | null;
    total_amount: number;
    daily_totals: ReportDailyCostModel[];
    compartments: ReportCompartmentCostModel[];
}

export interface ApiErrorResponse {
    detail?: string;
}

export interface BackendHealthResponse {
    status: string;
    timestamp: string;
    database: string;
    oci_cli: string;
    oci_config: string;
    details: Record<string, string | null>;
}

export interface ReportsHealthResponse {
    status: string;
}

export type TopbarServiceStatusState = 'online' | 'degraded' | 'offline';

export interface TopbarServiceStatusModel {
    label: string;
    status: TopbarServiceStatusState;
    online: boolean;
    docsUrl: string;
}
