import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { finalize } from 'rxjs';
import { ButtonModule } from 'primeng/button';
import { MessageModule } from 'primeng/message';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { TooltipModule } from 'primeng/tooltip';
import { ApiService } from '@/app/core/api.service';
import { ApiErrorResponse, CompartmentModel } from '@/app/core/models';

type StatusFilterValue = 'all' | 'active' | 'inactive';

@Component({
    selector: 'app-compartments-page',
    standalone: true,
    imports: [CommonModule, ButtonModule, MessageModule, TableModule, TagModule, TooltipModule],
    template: `
        <section class="page-header">
            <div>
                <span class="section-kicker">Compartimentos OCI</span>
                <h2>Compartimentos cadastrados</h2>
                <p>Consulte os compartimentos armazenados localmente e sincronize a lista com a OCI quando precisar atualizar o banco.</p>
            </div>
            <button pButton type="button" label="Atualizar" icon="pi pi-refresh" [outlined]="true" [loading]="refreshing()" [disabled]="refreshing()" (click)="refreshCompartments()"></button>
        </section>

        @if (feedback()) {
            <p-message [severity]="feedbackSeverity()" [text]="feedback() || ''"></p-message>
        }

        @if (error()) {
            <p-message severity="error" [text]="error() || ''"></p-message>
        }

        <section class="table-filter-row">
            <label>
                <span>Status</span>
                <select [value]="statusFilter()" (change)="setStatusFilter($any($event.target).value)">
                    <option value="all">Todos</option>
                    <option value="active">Ativos</option>
                    <option value="inactive">Inativos</option>
                </select>
            </label>
        </section>

        <div class="table-shell">
            <p-table [value]="filteredCompartments()" [loading]="loading()" dataKey="id" responsiveLayout="scroll">
                <ng-template pTemplate="header">
                    <tr>
                        <th>Nome</th>
                        <th>OCID</th>
                        <th>Status</th>
                    </tr>
                </ng-template>
                <ng-template pTemplate="body" let-compartment>
                    <tr>
                        <td>{{ compartment.name }}</td>
                        <td class="ocid-cell">
                            <div class="ocid-inline-actions">
                                <span>{{ formatOcid(compartment.ocid) }}</span>
                                <button
                                    pButton
                                    type="button"
                                    size="small"
                                    icon="pi pi-clipboard"
                                    rounded
                                    outlined
                                    styleClass="ocid-copy-button"
                                    pTooltip="Copiar"
                                    tooltipPosition="top"
                                    aria-label="Copiar OCID"
                                    [disabled]="!compartment.ocid"
                                    (click)="copyOcid(compartment.ocid)"
                                ></button>
                            </div>
                        </td>
                        <td>
                            <p-tag [severity]="compartment.active ? 'success' : 'contrast'" [value]="compartment.active ? 'ativo' : 'inativo'"></p-tag>
                        </td>
                    </tr>
                </ng-template>
                <ng-template pTemplate="emptymessage">
                    <tr>
                        <td colspan="3">Nenhum compartimento encontrado.</td>
                    </tr>
                </ng-template>
            </p-table>
        </div>
    `
})
export class CompartmentsPage implements OnInit {
    private readonly api = inject(ApiService);

    readonly compartments = signal<CompartmentModel[]>([]);
    readonly loading = signal(false);
    readonly refreshing = signal(false);
    readonly error = signal<string | null>(null);
    readonly feedback = signal<string | null>(null);
    readonly feedbackSeverity = signal<'success' | 'error'>('success');
    readonly statusFilter = signal<StatusFilterValue>('all');
    readonly filteredCompartments = computed(() => {
        const filter = this.statusFilter();
        const items = this.compartments();
        if (filter === 'active') {
            return items.filter((item) => item.active);
        }
        if (filter === 'inactive') {
            return items.filter((item) => !item.active);
        }
        return items;
    });

    ngOnInit(): void {
        this.loadCompartments();
    }

    loadCompartments(): void {
        this.loading.set(true);
        this.error.set(null);
        this.api
            .listCompartments()
            .pipe(finalize(() => this.loading.set(false)))
            .subscribe({
                next: (items) => this.compartments.set(items),
                error: () => this.error.set('Não foi possível carregar os compartimentos.')
            });
    }

    refreshCompartments(): void {
        this.refreshing.set(true);
        this.error.set(null);
        this.feedback.set(null);
        this.api
            .listAndUpdateCompartments()
            .pipe(finalize(() => this.refreshing.set(false)))
            .subscribe({
                next: (items) => {
                    this.compartments.set(items);
                    this.feedbackSeverity.set('success');
                    this.feedback.set('Compartimentos atualizados com sucesso.');
                },
                error: (response: { error?: ApiErrorResponse }) => {
                    this.feedbackSeverity.set('error');
                    this.feedback.set(response.error?.detail ?? 'Não foi possível atualizar os compartimentos.');
                }
            });
    }

    setStatusFilter(value: string): void {
        if (value === 'active' || value === 'inactive') {
            this.statusFilter.set(value);
            return;
        }
        this.statusFilter.set('all');
    }

    async copyOcid(ocid?: string | null): Promise<void> {
        if (!ocid) {
            this.feedbackSeverity.set('error');
            this.feedback.set('Não foi possível copiar o OCID.');
            return;
        }

        try {
            await navigator.clipboard.writeText(ocid);
            this.feedbackSeverity.set('success');
            this.feedback.set('OCID copiado com sucesso.');
        } catch {
            this.feedbackSeverity.set('error');
            this.feedback.set('Não foi possível copiar o OCID.');
        }
    }

    formatOcid(ocid?: string | null): string {
        if (!ocid) {
            return '-';
        }

        return ocid.length <= 10 ? ocid : `...${ocid.slice(-10)}`;
    }
}
