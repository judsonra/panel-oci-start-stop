import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { TableModule } from 'primeng/table';
import { AuditAccessLogModel } from '@/app/core/models';
import { ApiService } from '@/app/core/api.service';

@Component({
    selector: 'app-audit-access-page',
    standalone: true,
    imports: [CommonModule, FormsModule, ButtonModule, InputTextModule, TableModule],
    template: `
        <section class="page-header">
            <div>
                <span class="section-kicker">Auditoria</span>
                <h2>Acessos</h2>
                <p>Visualize autenticações, acessos negados e o tempo interno de processamento de cada rota da API.</p>
            </div>
        </section>
        <div class="form-actions">
            <input pInputText [(ngModel)]="query" placeholder="Filtrar por email, rota ou mensagem" />
            <button pButton type="button" label="Filtrar" icon="pi pi-search" (click)="load()"></button>
        </div>
        <div class="table-shell">
            @if (itemCount() > 0) {
                <p-table [value]="tableItems()" responsiveLayout="scroll">
                    <ng-template pTemplate="header">
                        <tr>
                            <th>Início</th>
                            <th>Fim</th>
                            <th>Duração</th>
                            <th>Evento</th>
                            <th>Origem</th>
                            <th>Email</th>
                            <th>Rota</th>
                            <th>Método</th>
                            <th>Status</th>
                            <th>Mensagem</th>
                        </tr>
                    </ng-template>
                    <ng-template pTemplate="body" let-item>
                        <tr>
                            <td>{{ item.started_at ? (item.started_at | date: 'dd/MM/yyyy HH:mm:ss.SSS') : '-' }}</td>
                            <td>{{ item.finished_at ? (item.finished_at | date: 'dd/MM/yyyy HH:mm:ss.SSS') : '-' }}</td>
                            <td>{{ item.duration_ms != null ? item.duration_ms + ' ms' : '-' }}</td>
                            <td>{{ item.event_type }}</td>
                            <td>{{ item.auth_source || '-' }}</td>
                            <td>{{ item.email || '-' }}</td>
                            <td>{{ item.path || '-' }}</td>
                            <td>{{ item.method || '-' }}</td>
                            <td>{{ item.status_code || '-' }}</td>
                            <td>{{ item.message || '-' }}</td>
                        </tr>
                    </ng-template>
                </p-table>
            } @else if (loaded()) {
                <p>Nenhum registro de acesso encontrado.</p>
            }
        </div>
    `
})
export class AuditAccessPage implements OnInit {
    private readonly api = inject(ApiService);
    readonly items = signal<AuditAccessLogModel[]>([]);
    readonly loaded = signal(false);
    readonly tableItems = computed(() => [...this.items()]);
    readonly itemCount = computed(() => this.tableItems().length);
    query = '';

    ngOnInit(): void {
        this.load();
    }

    load(): void {
        this.api.listAuditAccess({ query: this.query || undefined }).subscribe((items) => {
            this.items.set(items ?? []);
            this.loaded.set(true);
        });
    }
}
