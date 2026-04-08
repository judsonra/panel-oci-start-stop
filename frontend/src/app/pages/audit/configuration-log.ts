import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { TableModule } from 'primeng/table';
import { ApiService } from '@/app/core/api.service';
import { AuditConfigurationLogModel } from '@/app/core/models';

@Component({
    selector: 'app-audit-configuration-page',
    standalone: true,
    imports: [CommonModule, FormsModule, ButtonModule, InputTextModule, TableModule],
    template: `
        <section class="page-header">
            <div>
                <span class="section-kicker">Auditoria</span>
                <h2>Configurações</h2>
                <p>Rastreie mudanças administrativas e operacionais realizadas na aplicação.</p>
            </div>
        </section>
        <div class="form-actions">
            <input pInputText [(ngModel)]="query" placeholder="Filtrar por ator, entidade ou resumo" />
            <button pButton type="button" label="Filtrar" icon="pi pi-search" (click)="load()"></button>
        </div>
        <div class="table-shell">
            <p-table [value]="items()" responsiveLayout="scroll">
                <ng-template pTemplate="header">
                    <tr>
                        <th>Quando</th>
                        <th>Evento</th>
                        <th>Entidade</th>
                        <th>Ator</th>
                        <th>Resumo</th>
                    </tr>
                </ng-template>
                <ng-template pTemplate="body" let-item>
                    <tr>
                        <td>{{ item.created_at | date: 'dd/MM/yyyy HH:mm' }}</td>
                        <td>{{ item.event_type }}</td>
                        <td>{{ item.entity_type }}</td>
                        <td>{{ item.actor_email || '-' }}</td>
                        <td>{{ item.summary }}</td>
                    </tr>
                </ng-template>
            </p-table>
        </div>
    `
})
export class AuditConfigurationPage implements OnInit {
    private readonly api = inject(ApiService);
    readonly items = signal<AuditConfigurationLogModel[]>([]);
    query = '';

    ngOnInit(): void {
        this.load();
    }

    load(): void {
        this.api.listAuditConfigurations({ query: this.query || undefined }).subscribe((items) => this.items.set(items));
    }
}
