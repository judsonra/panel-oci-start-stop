import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { finalize } from 'rxjs';
import { ButtonModule } from 'primeng/button';
import { CheckboxModule } from 'primeng/checkbox';
import { MessageModule } from 'primeng/message';
import { MultiSelectModule } from 'primeng/multiselect';
import { TableModule } from 'primeng/table';
import { ApiService } from '@/app/core/api.service';
import { AccessGroupModel, AccessPermissionModel, AccessUserModel, ApiErrorResponse } from '@/app/core/models';

@Component({
    selector: 'app-admin-users-page',
    standalone: true,
    imports: [CommonModule, ReactiveFormsModule, ButtonModule, CheckboxModule, MessageModule, MultiSelectModule, TableModule],
    template: `
        <section class="page-header">
            <div>
                <span class="section-kicker">Administração</span>
                <h2>Usuários</h2>
                <p>Cadastre usuários por email e associe permissões diretas e grupos de acesso.</p>
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
                <p-table [value]="users()" [loading]="loading()">
                    <ng-template pTemplate="header">
                        <tr>
                            <th>Email</th>
                            <th>Nome</th>
                            <th>Ativo</th>
                            <th>Superadmin</th>
                            <th>Permissões</th>
                            <th class="actions-column">Ações</th>
                        </tr>
                    </ng-template>
                    <ng-template pTemplate="body" let-user>
                        <tr>
                            <td>{{ user.email }}</td>
                            <td>{{ user.display_name || '-' }}</td>
                            <td>{{ user.is_active ? 'Sim' : 'Não' }}</td>
                            <td>{{ user.is_superadmin ? 'Sim' : 'Não' }}</td>
                            <td>{{ user.effective_permissions.length }}</td>
                            <td class="actions-column">
                                <button pButton type="button" icon="pi pi-pencil" severity="secondary" variant="outlined" (click)="editUser(user)"></button>
                            </td>
                        </tr>
                    </ng-template>
                </p-table>
            </div>

            <form class="form-panel" [formGroup]="form" (ngSubmit)="save()">
                <label>
                    <span>Email</span>
                    <input type="email" formControlName="email" />
                </label>
                <label>
                    <span>Nome</span>
                    <input type="text" formControlName="display_name" />
                </label>
                <label>
                    <span>Permissões diretas</span>
                    <p-multiselect formControlName="direct_permissions" [options]="permissionOptions()" optionLabel="label" optionValue="key" appendTo="body">
                        <ng-template let-permission pTemplate="item">
                            <div class="permission-option">
                                <strong>{{ permission.label }}</strong>
                                <small>{{ permission.key }}</small>
                                <small>{{ permission.description || 'Sem descrição' }}</small>
                            </div>
                        </ng-template>
                    </p-multiselect>
                    @if (selectedPermissionOptions().length > 0) {
                        <div class="permission-summary-list">
                            @for (permission of selectedPermissionOptions(); track permission.key) {
                                <div class="permission-summary-item">
                                    <strong>{{ permission.label }}</strong>
                                    <small>{{ permission.key }}</small>
                                </div>
                            }
                        </div>
                    }
                </label>
                <label>
                    <span>Grupos de acesso</span>
                    <p-multiselect formControlName="group_ids" [options]="groupOptions()" optionLabel="name" optionValue="id" appendTo="body"></p-multiselect>
                </label>
                <label class="checkbox-field"><p-checkbox formControlName="is_active" binary="true"></p-checkbox><span>Ativo</span></label>
                <label class="checkbox-field"><p-checkbox formControlName="is_superadmin" binary="true"></p-checkbox><span>Superadmin</span></label>
                <div class="form-actions">
                    <button pButton type="submit" [label]="editingUserId() ? 'Salvar usuário' : 'Criar usuário'" icon="pi pi-save"></button>
                </div>
            </form>
        </section>
    `
})
export class AdminUsersPage implements OnInit {
    private readonly api = inject(ApiService);
    private readonly formBuilder = inject(FormBuilder);

    readonly users = signal<AccessUserModel[]>([]);
    readonly permissions = signal<AccessPermissionModel[]>([]);
    readonly groups = signal<AccessGroupModel[]>([]);
    readonly loading = signal(false);
    readonly editingUserId = signal<string | null>(null);
    readonly error = signal<string | null>(null);
    readonly feedback = signal<string | null>(null);
    readonly permissionOptions = computed(() => this.permissions());
    readonly groupOptions = computed(() => this.groups());
    readonly selectedPermissionOptions = computed(() => {
        const selectedKeys = this.form.controls.direct_permissions.value;
        return this.permissions().filter((permission) => selectedKeys.includes(permission.key));
    });
    readonly form = this.formBuilder.nonNullable.group({
        email: ['', [Validators.required, Validators.email]],
        display_name: [''],
        is_active: [true],
        is_superadmin: [false],
        direct_permissions: [[] as string[]],
        group_ids: [[] as string[]]
    });

    ngOnInit(): void {
        this.load();
    }

    load(): void {
        this.loading.set(true);
        this.api.listAccessUsers().pipe(finalize(() => this.loading.set(false))).subscribe({
            next: (users) => this.users.set(users),
            error: () => this.error.set('Não foi possível carregar os usuários.')
        });
        this.api.listAccessPermissions().subscribe({ next: (permissions) => this.permissions.set(permissions) });
        this.api.listAccessGroups().subscribe({ next: (groups) => this.groups.set(groups) });
    }

    editUser(user: AccessUserModel): void {
        this.editingUserId.set(user.id);
        this.form.setValue({
            email: user.email,
            display_name: user.display_name || '',
            is_active: user.is_active,
            is_superadmin: user.is_superadmin,
            direct_permissions: [...user.direct_permissions],
            group_ids: [...user.group_ids]
        });
    }

    save(): void {
        if (this.form.invalid) {
            this.form.markAllAsTouched();
            return;
        }
        this.error.set(null);
        this.feedback.set(null);
        const payload = this.form.getRawValue();
        const request$ = this.editingUserId()
            ? this.api.updateAccessUser(this.editingUserId() as string, payload)
            : this.api.createAccessUser(payload);
        request$.subscribe({
            next: () => {
                this.feedback.set(this.editingUserId() ? 'Usuário atualizado com sucesso.' : 'Usuário criado com sucesso.');
                this.editingUserId.set(null);
                this.form.reset({ email: '', display_name: '', is_active: true, is_superadmin: false, direct_permissions: [], group_ids: [] });
                this.load();
            },
            error: (response: { error?: ApiErrorResponse }) => {
                this.error.set(response.error?.detail ?? 'Não foi possível salvar o usuário.');
            }
        });
    }
}
