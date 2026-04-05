import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import {
    BackendHealthResponse,
    CompartmentModel,
    CostByCompartmentReportModel,
    ExecutionModel,
    GroupModel,
    GroupTreeCompartmentModel,
    ImportAllCompartmentsModel,
    ImportAllCompartmentsJobCreateModel,
    ImportAllCompartmentsJobStatusModel,
    InstanceImportPreviewModel,
    InstanceModel,
    InstanceVnicModel,
    ReportsHealthResponse,
    ScheduleModel,
    VnicDetailsModel
} from './models';

declare global {
    interface Window {
        __APP_CONFIG__?: {
            apiBaseUrl?: string;
            reportsApiBaseUrl?: string;
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
