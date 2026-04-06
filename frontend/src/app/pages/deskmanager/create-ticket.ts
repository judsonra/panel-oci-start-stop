import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { finalize } from 'rxjs';
import { AutoCompleteCompleteEvent, AutoCompleteModule } from 'primeng/autocomplete';
import { ButtonModule } from 'primeng/button';
import { MessageModule } from 'primeng/message';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { TextareaModule } from 'primeng/textarea';
import { ApiService } from '@/app/core/api.service';
import {
    ApiErrorResponse,
    DeskManagerCategoryModel,
    DeskManagerCreateTicketResultModel,
    DeskManagerUserModel,
} from '@/app/core/models';

interface PendingDeskManagerTicket {
    local_id: string;
    user_id: string;
    user_name: string;
    category_id: string;
    category_name: string;
    description: string;
    status: 'pending' | 'success' | 'failed';
    message?: string | null;
}

@Component({
    selector: 'app-deskmanager-create-ticket-page',
    standalone: true,
    imports: [CommonModule, ReactiveFormsModule, AutoCompleteModule, ButtonModule, MessageModule, TableModule, TagModule, TextareaModule],
    template: `
        <section class="page-header">
            <div>
                <span class="section-kicker">DeskManager</span>
                <h2>Criar chamado</h2>
                <p>Monte a fila local de chamados, revise no grid e envie o lote para o DeskManager.</p>
            </div>
        </section>

        @if (feedback()) {
            <p-message [severity]="feedbackSeverity()" [text]="feedback() || ''"></p-message>
        }

        @if (error()) {
            <p-message severity="error" [text]="error() || ''"></p-message>
        }

        <form class="form-panel" [formGroup]="form">
            <label>
                <span>Solicitante</span>
                <p-autocomplete
                    formControlName="user"
                    [suggestions]="userSuggestions()"
                    optionLabel="name"
                    [dropdown]="true"
                    dropdownMode="blank"
                    [completeOnFocus]="true"
                    [showClear]="true"
                    [forceSelection]="true"
                    placeholder="Selecione o solicitante"
                    (completeMethod)="filterUsers($event)"
                />
            </label>

            <label>
                <span>Auto-categoria</span>
                <p-autocomplete
                    formControlName="category"
                    [suggestions]="categorySuggestions()"
                    optionLabel="name"
                    [dropdown]="true"
                    dropdownMode="blank"
                    [completeOnFocus]="true"
                    [showClear]="true"
                    [forceSelection]="true"
                    placeholder="Pesquise e selecione a categoria"
                    (completeMethod)="filterCategories($event)"
                />
            </label>

            <label>
                <span>Descrição</span>
                <textarea pTextarea formControlName="description" rows="4" placeholder="Descreva o problema aqui..."></textarea>
            </label>

            <div class="form-actions">
                <button pButton type="button" label="Abrir chamado" icon="pi pi-send" (click)="submitTickets()" [disabled]="submitting() || pendingCount() === 0"></button>
                <button pButton type="button" label="Adicionar" icon="pi pi-plus" (click)="addPendingTicket()" [disabled]="loadingCatalogs()"></button>
            </div>
        </form>

        <div class="table-shell">
            <p-table [value]="tickets()" responsiveLayout="scroll">
                <ng-template pTemplate="header">
                    <tr>
                        <th>Solicitante</th>
                        <th>Descrição</th>
                        <th>Auto-categoria</th>
                        <th>Status</th>
                        <th>Mensagem</th>
                        <th class="actions-column">Ações</th>
                    </tr>
                </ng-template>
                <ng-template pTemplate="body" let-ticket>
                    <tr>
                        <td>{{ ticket.user_name }}</td>
                        <td>{{ ticket.description }}</td>
                        <td>{{ ticket.category_name }}</td>
                        <td>
                            <p-tag
                                [severity]="ticket.status === 'success' ? 'success' : ticket.status === 'failed' ? 'danger' : 'warn'"
                                [value]="ticket.status"
                            ></p-tag>
                        </td>
                        <td>{{ ticket.message || '-' }}</td>
                        <td class="actions-column">
                            <p-button
                                type="button"
                                size="small"
                                severity="danger"
                                variant="outlined"
                                icon="pi pi-trash"
                                ariaLabel="Remover"
                                (onClick)="removeTicket(ticket.local_id)"
                            />
                        </td>
                    </tr>
                </ng-template>
                <ng-template pTemplate="emptymessage">
                    <tr>
                        <td colspan="6">Nenhum chamado adicionado ao grid.</td>
                    </tr>
                </ng-template>
            </p-table>
        </div>
    `
})
export class DeskManagerCreateTicketPage implements OnInit {
    private readonly api = inject(ApiService);
    private readonly formBuilder = inject(FormBuilder);

    readonly users = signal<DeskManagerUserModel[]>([]);
    readonly userSuggestions = signal<DeskManagerUserModel[]>([]);
    readonly categorySuggestions = signal<DeskManagerCategoryModel[]>([]);
    readonly tickets = signal<PendingDeskManagerTicket[]>([]);
    readonly loadingCatalogs = signal(false);
    readonly submitting = signal(false);
    readonly error = signal<string | null>(null);
    readonly feedback = signal<string | null>(null);
    readonly feedbackSeverity = signal<'success' | 'error'>('success');
    readonly pendingCount = computed(() => this.tickets().filter((item) => item.status === 'pending').length);

    readonly form = this.formBuilder.group({
        user: this.formBuilder.control<DeskManagerUserModel | null>(null, Validators.required),
        category: this.formBuilder.control<DeskManagerCategoryModel | null>(null, Validators.required),
        description: this.formBuilder.nonNullable.control('', [Validators.required, Validators.maxLength(4000)])
    });

    ngOnInit(): void {
        this.loadCatalogs();
    }

    loadCatalogs(): void {
        this.loadingCatalogs.set(true);
        this.error.set(null);
        this.api
            .listDeskManagerUsers()
            .pipe(finalize(() => this.loadingCatalogs.set(false)))
            .subscribe({
                next: (users) => {
                    this.users.set(users);
                    this.userSuggestions.set(users);
                    this.loadCategories();
                },
                error: () => this.error.set('Não foi possível carregar os solicitantes do DeskManager.')
            });
    }

    loadCategories(search?: string): void {
        this.api.listDeskManagerCategories(search).subscribe({
            next: (categories) => this.categorySuggestions.set(categories),
            error: () => this.error.set('Não foi possível carregar as categorias do DeskManager.')
        });
    }

    filterUsers(event: AutoCompleteCompleteEvent): void {
        const query = (event.query ?? '').trim().toLowerCase();
        this.userSuggestions.set(this.users().filter((item) => item.name.toLowerCase().includes(query)));
    }

    filterCategories(event: AutoCompleteCompleteEvent): void {
        this.loadCategories(event.query);
    }

    addPendingTicket(): void {
        if (this.form.invalid) {
            this.form.markAllAsTouched();
            return;
        }

        const user = this.form.controls.user.value;
        const category = this.form.controls.category.value;
        const description = this.form.controls.description.value.trim();
        if (!user || !category || !description) {
            this.form.markAllAsTouched();
            return;
        }

        this.tickets.update((items) => [
            ...items,
            {
                local_id: `${Date.now()}-${items.length}`,
                user_id: user.id,
                user_name: user.name,
                category_id: category.id,
                category_name: category.name,
                description,
                status: 'pending',
                message: null
            }
        ]);
        this.feedbackSeverity.set('success');
        this.feedback.set('Chamado adicionado ao grid local.');
        this.form.reset({ user: null, category: null, description: '' });
        this.userSuggestions.set(this.users());
    }

    removeTicket(localId: string): void {
        this.tickets.update((items) => items.filter((item) => item.local_id !== localId));
    }

    submitTickets(): void {
        const pending = this.tickets().filter((item) => item.status === 'pending');
        if (pending.length === 0) {
            this.feedbackSeverity.set('error');
            this.feedback.set('Não há chamados pendentes para envio.');
            return;
        }

        this.submitting.set(true);
        this.error.set(null);
        this.api
            .createDeskManagerTickets({
                items: pending.map((item) => ({
                    user_id: item.user_id,
                    category_id: item.category_id,
                    description: item.description
                }))
            })
            .pipe(finalize(() => this.submitting.set(false)))
            .subscribe({
                next: (response) => {
                    this.applySubmissionResults(pending.map((item) => item.local_id), response.results);
                    this.feedbackSeverity.set(response.failed_count > 0 ? 'error' : 'success');
                    this.feedback.set(
                        `Envio finalizado. Sucesso: ${response.success_count} | Falhas: ${response.failed_count} | Pendentes: ${this.pendingCount()}`
                    );
                },
                error: (response: { error?: ApiErrorResponse }) => {
                    this.error.set(response.error?.detail ?? 'Não foi possível abrir os chamados no DeskManager.');
                }
            });
    }

    private applySubmissionResults(localIds: string[], results: DeskManagerCreateTicketResultModel[]): void {
        const mapped = new Map(localIds.map((localId, index) => [localId, results[index]]));
        this.tickets.update((items) =>
            items.map((item) => {
                const result = mapped.get(item.local_id);
                if (!result) {
                    return item;
                }
                return {
                    ...item,
                    status: result.status,
                    message: result.message
                };
            })
        );
    }
}
