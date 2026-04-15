export interface InstanceModel {
    id: string;
    name: string;
    ocid: string;
    app_url?: string | null;
    environment?: 'HMG' | 'PRD' | string | null;
    customer_name?: string | null;
    domain?: string | null;
    name_prefix?: string | null;
    compartment_id?: string | null;
    description?: string | null;
    enabled: boolean;
    last_known_state?: string | null;
    vcpu?: number | null;
    memory_gbs?: number | null;
    vnic_id?: string | null;
    public_ip?: string | null;
    private_ip?: string | null;
    oci_created_at?: string | null;
    created_at: string;
    updated_at: string;
}

export interface InstanceImportPreviewModel {
    name: string;
    ocid: string;
    app_url?: string | null;
    environment?: 'HMG' | 'PRD' | string | null;
    customer_name?: string | null;
    domain?: string | null;
    name_prefix?: string | null;
    vcpu?: number | null;
    memory_gbs?: number | null;
    vnic_id?: string | null;
    public_ip?: string | null;
    private_ip?: string | null;
    compartment_ocid: string;
    compartment_name: string;
    oci_created_at?: string | null;
    already_registered: boolean;
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
    target_type: 'instance' | 'group';
    instance_id?: string | null;
    instance_name?: string | null;
    group_id?: string | null;
    group_name?: string | null;
    type: 'one_time' | 'weekly' | 'monthly';
    action: 'start' | 'stop' | 'restart';
    run_at_utc?: string | null;
    days_of_week?: number[] | null;
    days_of_month?: number[] | null;
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

export interface InstanceStatusRefreshCompartmentModel {
    compartment_ocid: string;
    compartment_name: string;
    total_oci_instances: number;
    matched_instances: number;
    updated: number;
    unchanged: number;
    failed: number;
    message?: string | null;
}

export interface InstanceStatusRefreshModel {
    total_compartments: number;
    processed_compartments: number;
    matched_instances: number;
    updated: number;
    unchanged: number;
    failed: number;
    compartments: InstanceStatusRefreshCompartmentModel[];
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

export interface ReportDetailedCostModel {
    date: string;
    compartment_id?: string | null;
    compartment_name?: string | null;
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
    detailed_items: ReportDetailedCostModel[];
}

export interface ApiErrorResponse {
    detail?: string;
}

export interface InstanceVnicModel {
    instance_ocid: string;
    vnic_id?: string | null;
}

export interface VnicDetailsModel {
    vnic_id: string;
    public_ip?: string | null;
    private_ip?: string | null;
}

export interface ImportedInstanceModel {
    ocid: string;
    name: string;
    status: 'created' | 'updated' | 'unchanged' | 'failed';
    message?: string | null;
    vcpu?: number | null;
    memory_gbs?: number | null;
    vnic_id?: string | null;
    public_ip?: string | null;
    private_ip?: string | null;
    oci_created_at?: string | null;
}

export interface ImportedCompartmentModel {
    compartment_ocid: string;
    compartment_name: string;
    total_instances: number;
    created: number;
    updated: number;
    unchanged: number;
    failed: number;
    instances: ImportedInstanceModel[];
}

export interface ImportAllCompartmentsModel {
    total_compartments: number;
    processed_compartments: number;
    total_instances: number;
    created: number;
    updated: number;
    unchanged: number;
    failed: number;
    compartments: ImportedCompartmentModel[];
}

export interface ImportAllCompartmentsJobCreateModel {
    job_id: string;
    status: string;
    started_at: string;
}

export interface ImportAllCompartmentsJobStatusModel {
    job_id: string;
    status: string;
    started_at: string;
    finished_at?: string | null;
    total_compartments: number;
    processed_compartments: number;
    total_instances: number;
    processed_instances: number;
    created: number;
    updated: number;
    unchanged: number;
    failed: number;
    current_compartment_name?: string | null;
    current_instance_name?: string | null;
    result?: ImportAllCompartmentsModel | null;
    error?: string | null;
}

export interface GroupInstanceModel {
    id: string;
    name: string;
    ocid: string;
    compartment_id?: string | null;
}

export interface GroupModel {
    id: string;
    name: string;
    instance_count: number;
    instances: GroupInstanceModel[];
    created_at: string;
    updated_at: string;
}

export interface GroupTreeInstanceModel {
    id: string;
    name: string;
    ocid: string;
}

export interface GroupTreeCompartmentModel {
    id: string;
    name: string;
    instances: GroupTreeInstanceModel[];
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

export interface AuthConfigModel {
    entra_enabled: boolean;
    local_enabled: boolean;
    authority?: string | null;
    client_id?: string | null;
    redirect_uri?: string | null;
    post_logout_redirect_uri?: string | null;
    scopes: string[];
}

export interface AuthTokenModel {
    access_token: string;
    token_type: string;
    expires_in: number;
}

export interface CurrentUserModel {
    subject: string;
    email?: string | null;
    groups: string[];
    permissions: string[];
    auth_source: string;
    is_superadmin: boolean;
    access_user_id?: string | null;
}

export interface AccessPermissionModel {
    id: string;
    key: string;
    label: string;
    description?: string | null;
}

export interface AccessGroupModel {
    id: string;
    name: string;
    description?: string | null;
    is_active: boolean;
    permission_keys: string[];
    member_count: number;
    created_at: string;
    updated_at: string;
}

export interface AccessUserModel {
    id: string;
    email: string;
    display_name?: string | null;
    is_active: boolean;
    is_superadmin: boolean;
    direct_permissions: string[];
    group_ids: string[];
    effective_permissions: string[];
    created_at: string;
    updated_at: string;
}

export interface AuditAccessLogModel {
    id: string;
    event_type: string;
    auth_source?: string | null;
    email?: string | null;
    user_id?: string | null;
    ip_address?: string | null;
    user_agent?: string | null;
    path?: string | null;
    method?: string | null;
    status_code?: number | null;
    message?: string | null;
    started_at?: string | null;
    finished_at?: string | null;
    duration_ms?: number | null;
    created_at: string;
}

export interface AuditConfigurationLogModel {
    id: string;
    event_type: string;
    entity_type: string;
    entity_id?: string | null;
    actor_email?: string | null;
    actor_user_id?: string | null;
    summary: string;
    before_data?: Record<string, unknown> | null;
    after_data?: Record<string, unknown> | null;
    created_at: string;
}

export interface DeskManagerUserModel {
    id: string;
    name: string;
}

export interface DeskManagerCategoryModel {
    id: string;
    name: string;
}

export interface DeskManagerCreateTicketItemModel {
    user_id: string;
    category_id: string;
    description: string;
}

export interface DeskManagerCreateTicketResultModel {
    user_id: string;
    category_id: string;
    description: string;
    status: 'success' | 'failed';
    message: string;
    external_response?: unknown;
}

export interface DeskManagerCreateTicketsResponseModel {
    total: number;
    success_count: number;
    failed_count: number;
    results: DeskManagerCreateTicketResultModel[];
}
