import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { finalize } from 'rxjs';
import { ButtonModule } from 'primeng/button';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { ConfirmationService } from 'primeng/api';
import { MessageModule } from 'primeng/message';
import { TableModule } from 'primeng/table';
import { TooltipModule } from 'primeng/tooltip';
import { ApiService } from '@/app/core/api.service';
import { ApiErrorResponse, GroupModel } from '@/app/core/models';

@Component({
    selector: 'app-groups-page',
    standalone: true,
    imports: [CommonModule, ButtonModule, ConfirmDialogModule, MessageModule, TableModule, TooltipModule],
    providers: [ConfirmationService],
    template: `
        <section class="page-header">
            <div>
                <span class="section-kicker">Grupos</span>
                <h2>Grupos de instâncias</h2>
                <p>Organize instâncias por compartimento e mantenha grupos prontos para operações futuras.</p>
            </div>
            <button pButton type="button" label="Novo Grupo" icon="pi pi-plus" (click)="openNewGroup()"></button>
        </section>

        <p-confirmdialog></p-confirmdialog>

        @if (feedback()) {
            <p-message [severity]="feedbackSeverity()" [text]="feedback() || ''"></p-message>
        }

        @if (error()) {
            <p-message severity="error" [text]="error() || ''"></p-message>
        }

        <div class="table-shell">
            <p-table [value]="groups()" [loading]="loading()" dataKey="id" responsiveLayout="scroll">
                <ng-template pTemplate="header">
                    <tr>
                        <th>Grupo</th>
                        <th>Instâncias</th>
                        <th>Atualizado em</th>
                        <th class="actions-column">Ações</th>
                    </tr>
                </ng-template>
                <ng-template pTemplate="body" let-group>
                    <tr>
                        <td>{{ group.name }}</td>
                        <td>{{ group.instance_count }}</td>
                        <td>{{ formatDate(group.updated_at) }}</td>
                        <td class="actions-column">
                            <div class="instance-actions-group" role="group" aria-label="Ações do grupo">
                                <p-button
                                    type="button"
                                    size="small"
                                    severity="secondary"
                                    variant="outlined"
                                    icon="pi pi-pencil"
                                    pTooltip="Editar"
                                    tooltipPosition="top"
                                    ariaLabel="Editar"
                                    (onClick)="editGroup(group.id)"
                                />
                                <p-button
                                    type="button"
                                    size="small"
                                    severity="danger"
                                    variant="outlined"
                                    icon="pi pi-trash"
                                    pTooltip="Excluir"
                                    tooltipPosition="top"
                                    ariaLabel="Excluir"
                                    (onClick)="confirmDelete(group)"
                                />
                            </div>
                        </td>
                    </tr>
                </ng-template>
                <ng-template pTemplate="emptymessage">
                    <tr>
                        <td colspan="4">Nenhum grupo cadastrado.</td>
                    </tr>
                </ng-template>
            </p-table>
        </div>
    `
})
export class GroupsPage implements OnInit {
    private readonly api = inject(ApiService);
    private readonly router = inject(Router);
    private readonly confirmationService = inject(ConfirmationService);

    readonly groups = signal<GroupModel[]>([]);
    readonly loading = signal(false);
    readonly error = signal<string | null>(null);
    readonly feedback = signal<string | null>(null);
    readonly feedbackSeverity = signal<'success' | 'error'>('success');

    ngOnInit(): void {
        const feedback = (window.history.state?.feedback as string | undefined)?.trim();
        if (feedback) {
            this.feedbackSeverity.set('success');
            this.feedback.set(feedback);
        }
        this.loadGroups();
    }

    loadGroups(): void {
        this.loading.set(true);
        this.error.set(null);
        this.api
            .listGroups()
            .pipe(finalize(() => this.loading.set(false)))
            .subscribe({
                next: (groups) => this.groups.set(groups),
                error: () => this.error.set('Não foi possível carregar os grupos.')
            });
    }

    openNewGroup(): void {
        void this.router.navigate(['/groups/new']);
    }

    editGroup(groupId: string): void {
        void this.router.navigate(['/groups', groupId, 'edit']);
    }

    confirmDelete(group: GroupModel): void {
        this.confirmationService.confirm({
            header: 'Excluir grupo',
            message: `Deseja excluir o grupo ${group.name}?`,
            acceptLabel: 'Excluir',
            rejectLabel: 'Cancelar',
            acceptButtonStyleClass: 'p-button-danger',
            accept: () => {
                this.api.deleteGroup(group.id).subscribe({
                    next: () => {
                        this.groups.set(this.groups().filter((item) => item.id !== group.id));
                        this.feedbackSeverity.set('success');
                        this.feedback.set('Grupo excluído com sucesso.');
                    },
                    error: (response: { error?: ApiErrorResponse }) => {
                        this.feedbackSeverity.set('error');
                        this.feedback.set(response.error?.detail ?? 'Não foi possível excluir o grupo.');
                    }
                });
            }
        });
    }

    formatDate(value: string): string {
        return new Date(value).toLocaleString('pt-BR');
    }
}
