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

export interface ApiErrorResponse {
    detail?: string;
}
