import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ExecutionModel, InstanceModel, ScheduleModel } from './models';

declare global {
    interface Window {
        __APP_CONFIG__?: {
            apiBaseUrl?: string;
        };
    }
}

@Injectable({ providedIn: 'root' })
export class ApiService {
    private readonly http = inject(HttpClient);
    private readonly baseUrl = this.resolveBaseUrl();

    private resolveBaseUrl(): string {
        const configuredBaseUrl = window.__APP_CONFIG__?.apiBaseUrl?.trim();
        return configuredBaseUrl && configuredBaseUrl.length > 0 ? configuredBaseUrl : 'http://localhost:8000/api';
    }

    listInstances(): Observable<InstanceModel[]> {
        return this.http.get<InstanceModel[]>(`${this.baseUrl}/instances`);
    }

    createInstance(payload: Partial<InstanceModel>): Observable<InstanceModel> {
        return this.http.post<InstanceModel>(`${this.baseUrl}/instances`, payload);
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
}
