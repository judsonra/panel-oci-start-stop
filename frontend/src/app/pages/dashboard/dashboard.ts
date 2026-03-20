import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { CardModule } from 'primeng/card';
import { TagModule } from 'primeng/tag';
import { ApiService } from '@/app/core/api.service';
import { ExecutionModel, InstanceModel, ScheduleModel } from '@/app/core/models';

@Component({
    selector: 'app-dashboard-page',
    standalone: true,
    imports: [CommonModule, CardModule, TagModule],
    template: `
        <section class="page-header">
            <div>
                <span class="section-kicker">Painel operacional OCI</span>
                <h2>Visão geral do ambiente</h2>
                <p>Resumo rápido das instâncias cadastradas, dos agendamentos ativos e das execuções recentes.</p>
            </div>
        </section>

        <section class="stats-grid">
            <p-card>
                <div class="stat-card">
                    <span class="stat-label">Instâncias cadastradas</span>
                    <strong>{{ instances().length }}</strong>
                    <small>{{ enabledInstances() }} habilitadas para operação</small>
                </div>
            </p-card>
            <p-card>
                <div class="stat-card">
                    <span class="stat-label">Agendamentos</span>
                    <strong>{{ schedules().length }}</strong>
                    <small>{{ activeSchedules() }} ativos em UTC</small>
                </div>
            </p-card>
            <p-card>
                <div class="stat-card">
                    <span class="stat-label">Execuções recentes</span>
                    <strong>{{ executions().length }}</strong>
                    <small>{{ failedExecutions() }} falharam nas últimas consultas</small>
                </div>
            </p-card>
        </section>

        <section class="dashboard-grid">
            <p-card header="Saúde operacional">
                <div class="summary-list">
                    <div class="summary-row">
                        <span>Instâncias ligadas conhecidas</span>
                        <p-tag severity="success" [value]="runningInstances().toString()" />
                    </div>
                    <div class="summary-row">
                        <span>Instâncias desligadas conhecidas</span>
                        <p-tag severity="contrast" [value]="stoppedInstances().toString()" />
                    </div>
                    <div class="summary-row">
                        <span>Execuções com falha</span>
                        <p-tag severity="danger" [value]="failedExecutions().toString()" />
                    </div>
                </div>
            </p-card>

            <p-card header="Últimas execuções">
                @if (executions().length) {
                    <div class="summary-list">
                        @for (execution of executions(); track execution.id) {
                            <div class="execution-row">
                                <div>
                                    <strong>{{ execution.action | uppercase }}</strong>
                                    <small>{{ execution.started_at | date: 'dd/MM/yyyy HH:mm' }}</small>
                                </div>
                                <p-tag [severity]="execution.status === 'success' ? 'success' : 'danger'" [value]="execution.status" />
                            </div>
                        }
                    </div>
                } @else {
                    <p class="empty-state-copy">Nenhuma execução encontrada.</p>
                }
            </p-card>
        </section>
    `
})
export class Dashboard implements OnInit {
    private readonly api = inject(ApiService);

    readonly instances = signal<InstanceModel[]>([]);
    readonly schedules = signal<ScheduleModel[]>([]);
    readonly executions = signal<ExecutionModel[]>([]);

    readonly enabledInstances = computed(() => this.instances().filter((item) => item.enabled).length);
    readonly activeSchedules = computed(() => this.schedules().filter((item) => item.enabled).length);
    readonly runningInstances = computed(() => this.instances().filter((item) => item.last_known_state === 'RUNNING').length);
    readonly stoppedInstances = computed(() => this.instances().filter((item) => item.last_known_state === 'STOPPED').length);
    readonly failedExecutions = computed(() => this.executions().filter((item) => item.status === 'failed').length);

    ngOnInit(): void {
        this.api.listInstances().subscribe((items) => this.instances.set(items));
        this.api.listSchedules().subscribe((items) => this.schedules.set(items));
        this.api.listExecutions().subscribe((items) => this.executions.set(items.slice(0, 5)));
    }
}
