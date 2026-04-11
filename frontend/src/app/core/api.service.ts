import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import {
    AccessGroupModel,
    AccessPermissionModel,
    AccessUserModel,
    AuditAccessLogModel,
    AuditConfigurationLogModel,
    AuthConfigModel,
    AuthTokenModel,
    BackendHealthResponse,
    CompartmentModel,
    CostByCompartmentReportModel,
    DeskManagerCategoryModel,
    DeskManagerCreateTicketItemModel,
    DeskManagerCreateTicketsResponseModel,
    DeskManagerUserModel,
    ExecutionModel,
    GroupModel,
    GroupTreeCompartmentModel,
    ImportAllCompartmentsModel,
    ImportAllCompartmentsJobCreateModel,
    ImportAllCompartmentsJobStatusModel,
    InstanceImportPreviewModel,
    InstanceModel,
    InstanceStatusRefreshModel,
    InstanceVnicModel,
    ReportsHealthResponse,
    ScheduleModel,
    CurrentUserModel,
    VnicDetailsModel
} from './models';

declare global {
    interface Window {
        __APP_CONFIG__?: {
            apiBaseUrl?: string;
            reportsApiBaseUrl?: string;
            authEntraEnabled?: boolean;
            authLocalEnabled?: boolean;
            entraAuthority?: string;
            entraClientId?: string;
            entraRedirectUri?: string;
            entraPostLogoutRedirectUri?: string;
            entraScopes?: string;
        };
    }
}

@Injectable({ providedIn: 'root' })
export class ApiService {
    private readonly http = inject(HttpClient);
    private readonly baseUrl = this.resolveBaseUrl();
    private readonly reportsBaseUrl = this.resolveReportsBaseUrl();
    private readonly reportsServiceBaseUrl = this.resolveReportsServiceBaseUrl();

    private resolveBaseUrl(): string {
        const configuredBaseUrl = window.__APP_CONFIG__?.apiBaseUrl?.trim();
        return configuredBaseUrl && configuredBaseUrl.length > 0 ? configuredBaseUrl : 'http://localhost:8000/api';
    }

    private resolveReportsBaseUrl(): string {
        const configuredBaseUrl = window.__APP_CONFIG__?.reportsApiBaseUrl?.trim();
        return configuredBaseUrl && configuredBaseUrl.length > 0 ? configuredBaseUrl : 'http://localhost:8010/api';
    }

    private resolveReportsServiceBaseUrl(): string {
        return this.reportsBaseUrl.replace(/\/api\/?$/, '');
    }

    private resolveDocsUrl(baseUrl: string): string {
        return baseUrl.replace(/\/api\/?$/, '/docs#');
    }

    private buildQueryParams(params?: Record<string, string | number | boolean | null | undefined>): HttpParams {
        let httpParams = new HttpParams();
        for (const [key, value] of Object.entries(params ?? {})) {
            if (value === undefined || value === null || value === '') {
                continue;
            }
            httpParams = httpParams.set(key, String(value));
        }
        return httpParams;
    }

    getBackendHealth(): Observable<BackendHealthResponse> {
        return this.http.get<BackendHealthResponse>(`${this.baseUrl}/health`);
    }

    getReportsHealth(): Observable<ReportsHealthResponse> {
        return this.http.get<ReportsHealthResponse>(`${this.reportsServiceBaseUrl}/health`);
    }

    getBackendDocsUrl(): string {
        return this.resolveDocsUrl(this.baseUrl);
    }

    getReportsDocsUrl(): string {
        return this.resolveDocsUrl(this.reportsBaseUrl);
    }

    getAuthConfig(): Observable<AuthConfigModel> {
        return this.http.get<AuthConfigModel>(`${this.baseUrl}/auth/config`);
    }

    loginLocal(payload: { email: string; password: string }): Observable<AuthTokenModel> {
        return this.http.post<AuthTokenModel>(`${this.baseUrl}/auth/local/login`, payload);
    }

    exchangeEntraCode(payload: { code: string; code_verifier: string; redirect_uri: string }): Observable<AuthTokenModel> {
        return this.http.post<AuthTokenModel>(`${this.baseUrl}/auth/entra/exchange`, payload);
    }

    getCurrentUser(): Observable<CurrentUserModel> {
        return this.http.get<CurrentUserModel>(`${this.baseUrl}/auth/me`);
    }

    logout(): Observable<void> {
        return this.http.post<void>(`${this.baseUrl}/auth/logout`, {});
    }

    registerPageAccess(path: string): Observable<void> {
        return this.http.post<void>(`${this.baseUrl}/auth/page-access`, { path });
    }

    // Backend microservice: instance control and operational entities.
    listInstances(): Observable<InstanceModel[]> {
        return this.http.get<InstanceModel[]>(`${this.baseUrl}/instances`);
    }

    listGroups(): Observable<GroupModel[]> {
        return this.http.get<GroupModel[]>(`${this.baseUrl}/groups`);
    }

    getGroup(groupId: string): Observable<GroupModel> {
        return this.http.get<GroupModel>(`${this.baseUrl}/groups/${groupId}`);
    }

    getGroupTree(): Observable<GroupTreeCompartmentModel[]> {
        return this.http.get<GroupTreeCompartmentModel[]>(`${this.baseUrl}/groups/tree`);
    }

    createGroup(payload: { name: string; instance_ids: string[] }): Observable<GroupModel> {
        return this.http.post<GroupModel>(`${this.baseUrl}/groups`, payload);
    }

    updateGroup(groupId: string, payload: { name: string; instance_ids: string[] }): Observable<GroupModel> {
        return this.http.put<GroupModel>(`${this.baseUrl}/groups/${groupId}`, payload);
    }

    deleteGroup(groupId: string): Observable<void> {
        return this.http.delete<void>(`${this.baseUrl}/groups/${groupId}`);
    }

    listCompartments(): Observable<CompartmentModel[]> {
        return this.http.get<CompartmentModel[]>(`${this.baseUrl}/compartiments/list`);
    }

    listAndUpdateCompartments(): Observable<CompartmentModel[]> {
        return this.http.get<CompartmentModel[]>(`${this.baseUrl}/compartiments/listandupdate`);
    }

    importAllCompartmentsInstances(): Observable<ImportAllCompartmentsModel> {
        return this.http.get<ImportAllCompartmentsModel>(`${this.baseUrl}/compartiments/instancesall`);
    }

    startImportAllCompartmentsInstancesJob(): Observable<ImportAllCompartmentsJobCreateModel> {
        return this.http.post<ImportAllCompartmentsJobCreateModel>(`${this.baseUrl}/compartiments/instancesall/jobs`, {});
    }

    getImportAllCompartmentsInstancesJob(jobId: string): Observable<ImportAllCompartmentsJobStatusModel> {
        return this.http.get<ImportAllCompartmentsJobStatusModel>(`${this.baseUrl}/compartiments/instancesall/jobs/${encodeURIComponent(jobId)}`);
    }

    getInstanceVnic(instanceOcid: string): Observable<InstanceVnicModel> {
        return this.http.get<InstanceVnicModel>(`${this.baseUrl}/compartiments/instances/${encodeURIComponent(instanceOcid)}/vnic`);
    }

    getVnicDetails(vnicId: string): Observable<VnicDetailsModel> {
        return this.http.get<VnicDetailsModel>(`${this.baseUrl}/compartiments/vnics/${encodeURIComponent(vnicId)}`);
    }

    createInstance(payload: Partial<InstanceModel>): Observable<InstanceModel> {
        return this.http.post<InstanceModel>(`${this.baseUrl}/instances`, payload);
    }

    getInstanceImportPreview(instanceOcid: string): Observable<InstanceImportPreviewModel> {
        return this.http.get<InstanceImportPreviewModel>(`${this.baseUrl}/instances/import-preview/${encodeURIComponent(instanceOcid)}`);
    }

    importInstance(payload: { ocid: string; description?: string | null; enabled: boolean }): Observable<InstanceModel> {
        return this.http.post<InstanceModel>(`${this.baseUrl}/instances/import`, payload);
    }

    updateInstance(instanceId: string, payload: Partial<InstanceModel>): Observable<InstanceModel> {
        return this.http.put<InstanceModel>(`${this.baseUrl}/instances/${instanceId}`, payload);
    }

    startInstance(instanceId: string): Observable<ExecutionModel> {
        return this.http.post<ExecutionModel>(`${this.baseUrl}/instances/${instanceId}/start`, {});
    }

    stopInstance(instanceId: string): Observable<ExecutionModel> {
        return this.http.post<ExecutionModel>(`${this.baseUrl}/instances/${instanceId}/stop`, {});
    }

    getInstanceStatus(instanceId: string): Observable<ExecutionModel> {
        return this.http.get<ExecutionModel>(`${this.baseUrl}/instances/${instanceId}/status`);
    }

    refreshInstanceStatuses(): Observable<InstanceStatusRefreshModel> {
        return this.http.post<InstanceStatusRefreshModel>(`${this.baseUrl}/instances/status-refresh`, {});
    }

    listSchedules(): Observable<ScheduleModel[]> {
        return this.http.get<ScheduleModel[]>(`${this.baseUrl}/schedules`);
    }

    createSchedule(payload: Partial<ScheduleModel>): Observable<ScheduleModel> {
        return this.http.post<ScheduleModel>(`${this.baseUrl}/schedules`, payload);
    }

    updateSchedule(scheduleId: string, payload: Partial<ScheduleModel>): Observable<ScheduleModel> {
        return this.http.put<ScheduleModel>(`${this.baseUrl}/schedules/${scheduleId}`, payload);
    }

    deleteSchedule(scheduleId: string): Observable<void> {
        return this.http.delete<void>(`${this.baseUrl}/schedules/${scheduleId}`);
    }

    listExecutions(): Observable<ExecutionModel[]> {
        return this.http.get<ExecutionModel[]>(`${this.baseUrl}/executions`);
    }

    listDeskManagerUsers(): Observable<DeskManagerUserModel[]> {
        return this.http.get<DeskManagerUserModel[]>(`${this.baseUrl}/deskmanager/users`);
    }

    listDeskManagerCategories(search?: string): Observable<DeskManagerCategoryModel[]> {
        return this.http.get<DeskManagerCategoryModel[]>(`${this.baseUrl}/deskmanager/categories`, {
            params: search ? { search } : {}
        });
    }

    createDeskManagerTickets(payload: { items: DeskManagerCreateTicketItemModel[] }): Observable<DeskManagerCreateTicketsResponseModel> {
        return this.http.post<DeskManagerCreateTicketsResponseModel>(`${this.baseUrl}/deskmanager/criarchamado`, payload);
    }

    listAccessUsers(): Observable<AccessUserModel[]> {
        return this.http.get<AccessUserModel[]>(`${this.baseUrl}/admin/users`);
    }

    createAccessUser(payload: {
        email: string;
        display_name?: string | null;
        is_active: boolean;
        is_superadmin: boolean;
        direct_permissions: string[];
        group_ids: string[];
    }): Observable<AccessUserModel> {
        return this.http.post<AccessUserModel>(`${this.baseUrl}/admin/users`, payload);
    }

    updateAccessUser(
        userId: string,
        payload: Partial<{
            email: string;
            display_name?: string | null;
            is_active: boolean;
            is_superadmin: boolean;
            direct_permissions: string[];
            group_ids: string[];
        }>
    ): Observable<AccessUserModel> {
        return this.http.put<AccessUserModel>(`${this.baseUrl}/admin/users/${userId}`, payload);
    }

    listAccessGroups(): Observable<AccessGroupModel[]> {
        return this.http.get<AccessGroupModel[]>(`${this.baseUrl}/admin/groups`);
    }

    createAccessGroup(payload: { name: string; description?: string | null; is_active: boolean; permission_keys: string[] }): Observable<AccessGroupModel> {
        return this.http.post<AccessGroupModel>(`${this.baseUrl}/admin/groups`, payload);
    }

    updateAccessGroup(
        groupId: string,
        payload: Partial<{ name: string; description?: string | null; is_active: boolean; permission_keys: string[] }>
    ): Observable<AccessGroupModel> {
        return this.http.put<AccessGroupModel>(`${this.baseUrl}/admin/groups/${groupId}`, payload);
    }

    listAccessPermissions(): Observable<AccessPermissionModel[]> {
        return this.http.get<AccessPermissionModel[]>(`${this.baseUrl}/admin/permissions`);
    }

    updateAccessPermission(permissionId: string, payload: { label: string; description?: string | null }): Observable<AccessPermissionModel> {
        return this.http.put<AccessPermissionModel>(`${this.baseUrl}/admin/permissions/${permissionId}`, payload);
    }

    listAuditAccess(params?: { email?: string; event_type?: string; auth_source?: string; query?: string }): Observable<AuditAccessLogModel[]> {
        return this.http.get<AuditAccessLogModel[]>(`${this.baseUrl}/audit/access`, { params: this.buildQueryParams(params) });
    }

    listAuditConfigurations(params?: {
        actor_email?: string;
        event_type?: string;
        entity_type?: string;
        query?: string;
    }): Observable<AuditConfigurationLogModel[]> {
        return this.http.get<AuditConfigurationLogModel[]>(`${this.baseUrl}/audit/configurations`, { params: this.buildQueryParams(params) });
    }

    listAuditExecutions(): Observable<ExecutionModel[]> {
        return this.http.get<ExecutionModel[]>(`${this.baseUrl}/audit/executions`);
    }

    // Reports microservice: all report data, cache refresh and exports.
    getCostByCompartment(year: number, month: number): Observable<CostByCompartmentReportModel> {
        return this.http.get<CostByCompartmentReportModel>(`${this.reportsBaseUrl}/reports/cost-by-compartment`, {
            params: { year, month }
        });
    }

    refreshCostByCompartment(payload: { year: number; month: number }): Observable<CostByCompartmentReportModel> {
        return this.http.post<CostByCompartmentReportModel>(`${this.reportsBaseUrl}/reports/cost-by-compartment/refresh`, payload);
    }

    getCostByCompartmentCsvUrl(year: number, month: number): string {
        return `${this.reportsBaseUrl}/reports/cost-by-compartment.csv?year=${year}&month=${month}`;
    }
}
