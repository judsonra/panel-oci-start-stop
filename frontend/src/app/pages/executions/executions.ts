import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { ApiService } from '@/app/core/api.service';
import { ExecutionModel } from '@/app/core/models';

@Component({
    selector: 'app-executions-page',
    standalone: true,
    imports: [CommonModule, TableModule, TagModule],
    template: `
        <section class="page-header">
            <div>
                <span class="section-kicker">Execuções</span>
                <h2>Histórico de comandos OCI</h2>
                <p>Visualize sucesso, falhas e origem das chamadas realizadas pelo backend.</p>
            </div>
        </section>

        <div class="table-shell">
            <p-table [value]="executions()" responsiveLayout="scroll">
                <ng-template pTemplate="header">
                    <tr>
                        <th>Instância</th>
                        <th>Ação</th>
                        <th>Origem</th>
                        <th>Status</th>
                        <th>Início</th>
                        <th>Fim</th>
                        <th>Retorno</th>
                    </tr>
                </ng-template>
                <ng-template pTemplate="body" let-execution>
                    <tr>
                        <td>{{ execution.instance_name || execution.instance_id || '-' }}</td>
                        <td>{{ execution.action }}</td>
                        <td>{{ execution.source }}</td>
                        <td>
                            <p-tag [severity]="execution.status === 'success' ? 'success' : execution.status === 'pending' ? 'warn' : 'danger'" [value]="execution.status"></p-tag>
                        </td>
                        <td>{{ execution.started_at | date: 'dd/MM/yyyy HH:mm' }}</td>
                        <td>{{ execution.finished_at ? (execution.finished_at | date: 'dd/MM/yyyy HH:mm') : '-' }}</td>
                        <td>{{ execution.stderr_summary || execution.stdout_summary || '-' }}</td>
                    </tr>
                </ng-template>
            </p-table>
        </div>
    `
})
export class ExecutionsPage implements OnInit {
    private readonly api = inject(ApiService);
    readonly executions = signal<ExecutionModel[]>([]);

    ngOnInit(): void {
        this.api.listAuditExecutions().subscribe((items) => this.executions.set(items));
    }
}
