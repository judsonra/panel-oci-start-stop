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
import { AccessGroupModel, AccessPermissionModel, ApiErrorResponse } from '@/app/core/models';

@Component({
    selector: 'app-admin-access-groups-page',
    standalone: true,
    imports: [CommonModule, ReactiveFormsModule, ButtonModule, CheckboxModule, MessageModule, MultiSelectModule, TableModule],
    template: `
        <section class="page-header">
            <div>
                <span class="section-kicker">Administração</span>
                <h2>Grupos de acesso</h2>
                <p>Defina perfis reutilizáveis e deixe os usuários herdarem permissões por associação.</p>
            </div>
        </section>

        @if (error()) {
            <p-message severity="error" [text]="error() || ''"></p-message>
        }

        @if (feedback()) {
            <p-message severity="success" [text]="feedback() || ''"></p-message>
        }

        <div class="table-shell">
            <p-table [value]="groups()" [loading]="loading()">
                <ng-template pTemplate="header">
                    <tr>
                        <th>Grupo</th>
                        <th>Membros</th>
                        <th>Permissões</th>
                        <th>Ações</th>
                    </tr>
                </ng-template>
                <ng-template pTemplate="body" let-group>
                    <tr>
                        <td>{{ group.name }}</td>
                        <td>{{ group.member_count }}</td>
                        <td>{{ group.permission_keys.length }}</td>
                        <td><button pButton type="button" icon="pi pi-pencil" severity="secondary" variant="outlined" (click)="edit(group)"></button></td>
                    </tr>
                </ng-template>
            </p-table>
        </div>

        <form class="form-panel" [formGroup]="form" (ngSubmit)="save()">
            <label><span>Nome</span><input type="text" formControlName="name" /></label>
            <label><span>Descrição</span><input type="text" formControlName="description" /></label>
            <label>
                <span>Permissões</span>
                <p-multiselect formControlName="permission_keys" [options]="permissionOptions()" optionLabel="label" optionValue="key" appendTo="body">
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
            <label class="checkbox-field"><p-checkbox formControlName="is_active" binary="true"></p-checkbox><span>Ativo</span></label>
            <div class="form-actions">
                <button pButton type="submit" [label]="editingGroupId() ? 'Salvar grupo' : 'Criar grupo'" icon="pi pi-save"></button>
            </div>
        </form>
    `
})
export class AdminAccessGroupsPage implements OnInit {
    private readonly api = inject(ApiService);
    private readonly formBuilder = inject(FormBuilder);

    readonly groups = signal<AccessGroupModel[]>([]);
    readonly permissions = signal<AccessPermissionModel[]>([]);
    readonly loading = signal(false);
    readonly editingGroupId = signal<string | null>(null);
    readonly error = signal<string | null>(null);
    readonly feedback = signal<string | null>(null);
    readonly permissionOptions = computed(() => this.permissions());
    readonly selectedPermissionOptions = computed(() => {
        const selectedKeys = this.form.controls.permission_keys.value;
        return this.permissions().filter((permission) => selectedKeys.includes(permission.key));
    });
    readonly form = this.formBuilder.nonNullable.group({
        name: ['', [Validators.required]],
        description: [''],
        is_active: [true],
        permission_keys: [[] as string[]]
    });

    ngOnInit(): void {
        this.load();
    }

    load(): void {
        this.loading.set(true);
        this.api.listAccessGroups().pipe(finalize(() => this.loading.set(false))).subscribe({
            next: (groups) => this.groups.set(groups),
            error: () => this.error.set('Não foi possível carregar os grupos de acesso.')
        });
        this.api.listAccessPermissions().subscribe({ next: (permissions) => this.permissions.set(permissions) });
    }

    edit(group: AccessGroupModel): void {
        this.editingGroupId.set(group.id);
        this.form.setValue({
            name: group.name,
            description: group.description || '',
            is_active: group.is_active,
            permission_keys: [...group.permission_keys]
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
        const request$ = this.editingGroupId()
            ? this.api.updateAccessGroup(this.editingGroupId() as string, payload)
            : this.api.createAccessGroup(payload);
        request$.subscribe({
            next: () => {
                this.feedback.set(this.editingGroupId() ? 'Grupo atualizado com sucesso.' : 'Grupo criado com sucesso.');
                this.editingGroupId.set(null);
                this.form.reset({ name: '', description: '', is_active: true, permission_keys: [] });
                this.load();
            },
            error: (response: { error?: ApiErrorResponse }) => this.error.set(response.error?.detail ?? 'Não foi possível salvar o grupo.')
        });
    }
}
