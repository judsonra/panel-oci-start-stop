import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { finalize } from 'rxjs';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { MessageModule } from 'primeng/message';
import { TableModule } from 'primeng/table';
import { TextareaModule } from 'primeng/textarea';
import { ApiService } from '@/app/core/api.service';
import { AuthService } from '@/app/core/auth.service';
import { AccessPermissionModel, ApiErrorResponse } from '@/app/core/models';

@Component({
    selector: 'app-admin-direct-permissions-page',
    standalone: true,
    imports: [CommonModule, ReactiveFormsModule, ButtonModule, InputTextModule, MessageModule, TableModule, TextareaModule],
    template: `
        <section class="page-header">
            <div>
                <span class="section-kicker">Administração</span>
                <h2>Permissões Diretas</h2>
                <p>Gerencie o nome amigável e a descrição das permissões sem alterar a chave técnica da ACL.</p>
            </div>
        </section>

        @if (error()) {
            <p-message severity="error" [text]="error() || ''"></p-message>
        }

        @if (feedback()) {
            <p-message severity="success" [text]="feedback() || ''"></p-message>
        }

        <section class="instances-tabs-panel">
            <div class="table-shell">
                <p-table [value]="permissions()" [loading]="loading()">
                    <ng-template pTemplate="header">
                        <tr>
                            <th>Nome real</th>
                            <th>Label</th>
                            <th>Descrição</th>
                            <th class="actions-column">Ações</th>
                        </tr>
                    </ng-template>
                    <ng-template pTemplate="body" let-permission>
                        <tr>
                            <td><code>{{ permission.key }}</code></td>
                            <td>{{ permission.label }}</td>
                            <td>{{ permission.description || '-' }}</td>
                            <td class="actions-column">
                                <button
                                    pButton
                                    type="button"
                                    icon="pi pi-pencil"
                                    severity="secondary"
                                    variant="outlined"
                                    [disabled]="!canManage()"
                                    (click)="edit(permission)"
                                ></button>
                            </td>
                        </tr>
                    </ng-template>
                </p-table>
            </div>

            <form class="form-panel" [formGroup]="form" (ngSubmit)="save()">
                <label>
                    <span>Nome real</span>
                    <input pInputText type="text" formControlName="key" readonly />
                </label>
                <label>
                    <span>Label</span>
                    <input pInputText type="text" formControlName="label" />
                </label>
                <label>
                    <span>Descrição</span>
                    <textarea pTextarea formControlName="description" rows="4"></textarea>
                </label>
                <div class="form-actions">
                    <button pButton type="submit" label="Salvar permissão" icon="pi pi-save" [disabled]="!canManage() || !editingPermissionId()"></button>
                </div>
            </form>
        </section>
    `
})
export class AdminDirectPermissionsPage implements OnInit {
    private readonly api = inject(ApiService);
    private readonly auth = inject(AuthService);
    private readonly formBuilder = inject(FormBuilder);

    readonly permissions = signal<AccessPermissionModel[]>([]);
    readonly loading = signal(false);
    readonly editingPermissionId = signal<string | null>(null);
    readonly error = signal<string | null>(null);
    readonly feedback = signal<string | null>(null);
    readonly canManage = computed(() => this.auth.hasPermission('admin.permissions.manage'));
    readonly form = this.formBuilder.nonNullable.group({
        key: [{ value: '', disabled: true }],
        label: ['', [Validators.required]],
        description: ['']
    });

    ngOnInit(): void {
        this.load();
    }

    load(): void {
        this.loading.set(true);
        this.api
            .listAccessPermissions()
            .pipe(finalize(() => this.loading.set(false)))
            .subscribe({
                next: (permissions) => this.permissions.set(permissions),
                error: () => this.error.set('Não foi possível carregar as permissões.')
            });
    }

    edit(permission: AccessPermissionModel): void {
        this.editingPermissionId.set(permission.id);
        this.error.set(null);
        this.feedback.set(null);
        this.form.setValue({
            key: permission.key,
            label: permission.label,
            description: permission.description || ''
        });
    }

    save(): void {
        if (this.form.invalid || !this.editingPermissionId()) {
            this.form.markAllAsTouched();
            return;
        }
        this.error.set(null);
        this.feedback.set(null);
        const payload = this.form.getRawValue();
        this.api
            .updateAccessPermission(this.editingPermissionId() as string, {
                label: payload.label,
                description: payload.description || null
            })
            .subscribe({
                next: () => {
                    this.feedback.set('Permissão atualizada com sucesso.');
                    this.load();
                },
                error: (response: { error?: ApiErrorResponse }) => {
                    this.error.set(response.error?.detail ?? 'Não foi possível atualizar a permissão.');
                }
            });
    }
}
