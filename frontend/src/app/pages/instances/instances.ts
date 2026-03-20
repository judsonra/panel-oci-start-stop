import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { finalize, firstValueFrom } from 'rxjs';
import { ButtonModule } from 'primeng/button';
import { DialogModule } from 'primeng/dialog';
import { InputTextModule } from 'primeng/inputtext';
import { MessageModule } from 'primeng/message';
import { ProgressBarModule } from 'primeng/progressbar';
import { TableModule } from 'primeng/table';
import { TabsModule } from 'primeng/tabs';
import { TagModule } from 'primeng/tag';
import { TextareaModule } from 'primeng/textarea';
import { ToggleSwitchModule } from 'primeng/toggleswitch';
import { TooltipModule } from 'primeng/tooltip';
import { ApiService } from '@/app/core/api.service';
import { ApiErrorResponse, InstanceModel } from '@/app/core/models';

@Component({
    selector: 'app-instances-page',
    standalone: true,
    imports: [CommonModule, FormsModule, ReactiveFormsModule, ButtonModule, DialogModule, InputTextModule, TextareaModule, MessageModule, ProgressBarModule, TableModule, TabsModule, TagModule, ToggleSwitchModule, TooltipModule],
    template: `
        <section class="page-header">
            <div>
                <span class="section-kicker">Instâncias OCI</span>
                <h2>Painel Operacional OCI</h2>
                <p>Cadastre o OCID das instâncias e acione operações de inicialização e desligamento diretamente pela API.</p>
            </div>
            <button pButton type="button" label="Atualizar" icon="pi pi-refresh" [outlined]="true" (click)="openRefreshConfirmation()" [loading]="loading() || refreshingStatuses()" [disabled]="refreshingStatuses()"></button>
        </section>

        <p-dialog
            header="Atualizar status"
            [visible]="refreshConfirmationVisible()"
            [modal]="true"
            [closable]="false"
            [draggable]="false"
            [resizable]="false"
            [style]="{ width: '30rem', maxWidth: 'calc(100vw - 2rem)' }"
        >
            <p>Essa operação pode demorar.</p>
            <ng-template pTemplate="footer">
                <button pButton type="button" label="Não" severity="secondary" [outlined]="true" (click)="cancelRefreshConfirmation()"></button>
                <button pButton type="button" label="Sim" (click)="confirmRefreshStatuses()"></button>
            </ng-template>
        </p-dialog>

        <p-dialog
            header="Consultando status das instâncias"
            [visible]="refreshProgressVisible()"
            [modal]="true"
            [closable]="false"
            [closeOnEscape]="false"
            [draggable]="false"
            [dismissableMask]="false"
            [resizable]="false"
            [style]="{ width: '34rem', maxWidth: 'calc(100vw - 2rem)' }"
        >
            <div class="refresh-progress-copy">
                <strong>{{ refreshProgressCount() }} / {{ refreshProgressTotal() }}</strong>
                <span>{{ refreshProgressMessage() }}</span>
                @if (refreshCurrentInstanceName()) {
                    <small>Consultando: {{ refreshCurrentInstanceName() }}</small>
                }
            </div>
            <p-progressbar [value]="refreshProgressPercent()"></p-progressbar>
        </p-dialog>

        <section class="instances-tabs-panel">
            <p-tabs [value]="activeTab()" (valueChange)="setActiveTab($event)">
                <p-tablist>
                    <p-tab [value]="0">Instâncias cadastradas</p-tab>
                    <p-tab [value]="1">Cadastro de instância</p-tab>
                </p-tablist>
                <p-tabpanels>
                    <p-tabpanel [value]="0">
                        @if (actionFeedback()) {
                            <p-message [severity]="actionFeedbackSeverity()" [text]="actionFeedback() || ''"></p-message>
                        }
                        @if (error()) {
                            <p-message severity="error" [text]="error() || ''"></p-message>
                        }

                        <div class="table-shell">
                            <p-table [value]="instances()" [loading]="loading()" dataKey="id" responsiveLayout="scroll">
                                <ng-template pTemplate="header">
                                    <tr>
                                        <th>Nome</th>
                                        <th>OCID</th>
                                        <th>Status</th>
                                        <th>Habilitada</th>
                                        <th class="actions-column">Ações</th>
                                    </tr>
                                </ng-template>
                                <ng-template pTemplate="body" let-instance>
                                    <tr>
                                        <td>{{ instance.name }}</td>
                                        <td class="ocid-cell">
                                            <div class="ocid-inline-actions">
                                                <span>{{ formatOcid(instance.ocid) }}</span>
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
                                                    [disabled]="!instance.ocid"
                                                    (click)="copyOcid(instance.ocid)"
                                                ></button>
                                            </div>
                                        </td>
                                        <td>
                                            <p-tag [severity]="tagSeverity(instance.last_known_state)" [value]="instance.last_known_state || 'UNKNOWN'"></p-tag>
                                        </td>
                                        <td>
                                            <p-toggleswitch
                                                [ngModel]="instance.enabled"
                                                [disabled]="isToggling(instance.id)"
                                                [styleClass]="instance.enabled ? 'enabled-switch' : 'disabled-switch'"
                                                (ngModelChange)="toggleEnabled(instance, $event)"
                                            />
                                        </td>
                                        <td class="actions-column">
                                            <button
                                                pButton
                                                type="button"
                                                size="small"
                                                icon="pi pi-power-off"
                                                rounded
                                                outlined
                                                pTooltip="Ligar"
                                                tooltipPosition="top"
                                                aria-label="Ligar"
                                                (click)="start(instance.id)"
                                                [disabled]="!instance.enabled"
                                            ></button>
                                            <button
                                                pButton
                                                type="button"
                                                size="small"
                                                severity="secondary"
                                                icon="pi pi-stop-circle"
                                                rounded
                                                outlined
                                                pTooltip="Desligar"
                                                tooltipPosition="top"
                                                aria-label="Desligar"
                                                (click)="stop(instance.id)"
                                                [disabled]="!instance.enabled"
                                            ></button>
                                            <button
                                                pButton
                                                type="button"
                                                size="small"
                                                severity="secondary"
                                                icon="pi pi-refresh"
                                                rounded
                                                outlined
                                                pTooltip="Atualizar status"
                                                tooltipPosition="top"
                                                aria-label="Atualizar status"
                                                [loading]="isRefreshingRow(instance.id)"
                                                (click)="refreshInstanceStatus(instance)"
                                                [disabled]="!instance.enabled || isRefreshingRow(instance.id)"
                                            ></button>
                                        </td>
                                    </tr>
                                </ng-template>
                                <ng-template pTemplate="emptymessage">
                                    <tr>
                                        <td colspan="5">Nenhuma instância cadastrada.</td>
                                    </tr>
                                </ng-template>
                            </p-table>
                        </div>
                    </p-tabpanel>
                    <p-tabpanel [value]="1">
                        <form class="form-panel" [formGroup]="form" (ngSubmit)="save()">
                            <label>
                                <span>Nome</span>
                                <input pInputText formControlName="name" placeholder="Ex.: Aplicação Financeira" />
                            </label>

                            <label>
                                <span>OCID da instância</span>
                                <input pInputText formControlName="ocid" placeholder="ocid1.instance.oc1..." />
                            </label>

                            <label>
                                <span>Descrição</span>
                                <textarea pTextarea formControlName="description" rows="4" placeholder="Contexto operacional ou observações"></textarea>
                            </label>

                            <label class="checkbox-row">
                                <input type="checkbox" formControlName="enabled" />
                                <span>Instância habilitada para comandos</span>
                            </label>

                            <div class="form-actions">
                                <button pButton type="submit" label="Salvar instância" icon="pi pi-save" [disabled]="form.invalid || saving()"></button>
                            </div>
                        </form>
                    </p-tabpanel>
                </p-tabpanels>
            </p-tabs>
        </section>
    `
})
export class InstancesPage implements OnInit {
    private readonly api = inject(ApiService);
    private readonly formBuilder = inject(FormBuilder);

    readonly instances = signal<InstanceModel[]>([]);
    readonly loading = signal(false);
    readonly saving = signal(false);
    readonly error = signal<string | null>(null);
    readonly actionFeedback = signal<string | null>(null);
    readonly actionFeedbackSeverity = signal<'success' | 'error'>('success');
    readonly activeTab = signal(0);
    readonly togglingIds = signal<Set<string>>(new Set());
    readonly refreshingRowIds = signal<Set<string>>(new Set());
    readonly refreshConfirmationVisible = signal(false);
    readonly refreshProgressVisible = signal(false);
    readonly refreshingStatuses = signal(false);
    readonly refreshProgressCount = signal(0);
    readonly refreshProgressTotal = signal(0);
    readonly refreshCurrentInstanceName = signal<string | null>(null);
    readonly refreshProgressMessage = signal('Preparando consulta...');
    readonly refreshProgressPercent = computed(() => {
        const total = this.refreshProgressTotal();
        return total === 0 ? 0 : Math.round((this.refreshProgressCount() / total) * 100);
    });

    readonly form = this.formBuilder.nonNullable.group({
        name: ['', [Validators.required, Validators.maxLength(120)]],
        ocid: ['', [Validators.required, Validators.pattern(/^ocid1\.instance\..+/)]],
        description: [''],
        enabled: [true]
    });

    ngOnInit(): void {
        this.loadInstances();
    }

    loadInstances(): void {
        this.loading.set(true);
        this.error.set(null);
        this.api
            .listInstances()
            .pipe(finalize(() => this.loading.set(false)))
            .subscribe({
                next: (instances) => this.instances.set(instances),
                error: () => this.error.set('Não foi possível carregar as instâncias.')
            });
    }

    openRefreshConfirmation(): void {
        this.actionFeedback.set(null);
        this.error.set(null);
        this.refreshConfirmationVisible.set(true);
    }

    cancelRefreshConfirmation(): void {
        this.refreshConfirmationVisible.set(false);
    }

    async confirmRefreshStatuses(): Promise<void> {
        this.refreshConfirmationVisible.set(false);
        const enabledInstances = this.instances().filter((instance) => instance.enabled);

        if (enabledInstances.length === 0) {
            this.actionFeedbackSeverity.set('error');
            this.actionFeedback.set('Não há instâncias habilitadas para consultar o status.');
            return;
        }

        this.refreshingStatuses.set(true);
        this.refreshProgressVisible.set(true);
        this.refreshProgressCount.set(0);
        this.refreshProgressTotal.set(enabledInstances.length);
        this.refreshProgressMessage.set('Iniciando consulta dos status...');
        this.refreshCurrentInstanceName.set(null);
        this.error.set(null);
        this.actionFeedback.set(null);

        let successCount = 0;
        let failedCount = 0;

        for (const instance of enabledInstances) {
            this.refreshCurrentInstanceName.set(instance.name);
            this.refreshProgressMessage.set(`Consultando o status de ${instance.name}...`);

            try {
                const execution = await firstValueFrom(this.api.getInstanceStatus(instance.id));
                if (execution.status === 'failed') {
                    failedCount += 1;
                } else {
                    successCount += 1;
                }
            } catch {
                failedCount += 1;
            } finally {
                this.refreshProgressCount.set(this.refreshProgressCount() + 1);
            }
        }

        this.refreshCurrentInstanceName.set(null);
        this.refreshProgressMessage.set('Atualizando a listagem das instâncias...');
        this.refreshProgressVisible.set(false);
        this.refreshingStatuses.set(false);
        this.loadInstances();

        this.actionFeedbackSeverity.set(failedCount > 0 ? 'error' : 'success');
        if (failedCount > 0) {
            this.actionFeedback.set(`Consulta concluída: ${successCount} com sucesso e ${failedCount} com falha.`);
        } else {
            this.actionFeedback.set(`Consulta concluída com sucesso para ${successCount} instância(s).`);
        }
    }

    save(): void {
        if (this.form.invalid) {
            this.form.markAllAsTouched();
            return;
        }

        this.saving.set(true);
        this.error.set(null);
        this.actionFeedback.set(null);

        this.api
            .createInstance(this.form.getRawValue())
            .pipe(finalize(() => this.saving.set(false)))
            .subscribe({
                next: () => {
                    this.form.reset({
                        name: '',
                        ocid: '',
                        description: '',
                        enabled: true
                    });
                    this.actionFeedbackSeverity.set('success');
                    this.actionFeedback.set('Instância cadastrada com sucesso.');
                    this.activeTab.set(0);
                    this.loadInstances();
                },
                error: (response: { error?: ApiErrorResponse }) => {
                    this.error.set(response.error?.detail ?? 'Não foi possível salvar a instância.');
                }
            });
    }

    start(instanceId: string): void {
        this.handleInstanceAction(instanceId, 'start');
    }

    stop(instanceId: string): void {
        this.handleInstanceAction(instanceId, 'stop');
    }

    async copyOcid(ocid?: string | null): Promise<void> {
        if (!ocid) {
            this.actionFeedbackSeverity.set('error');
            this.actionFeedback.set('Não foi possível copiar o OCID.');
            return;
        }

        try {
            await navigator.clipboard.writeText(ocid);
            this.actionFeedbackSeverity.set('success');
            this.actionFeedback.set('OCID copiado com sucesso.');
        } catch {
            this.actionFeedbackSeverity.set('error');
            this.actionFeedback.set('Não foi possível copiar o OCID.');
        }
    }

    isToggling(instanceId: string): boolean {
        return this.togglingIds().has(instanceId);
    }

    isRefreshingRow(instanceId: string): boolean {
        return this.refreshingRowIds().has(instanceId);
    }

    setActiveTab(value: string | number | undefined): void {
        this.activeTab.set(typeof value === 'number' ? value : Number(value ?? 0));
    }

    formatOcid(ocid?: string | null): string {
        if (!ocid) {
            return '-';
        }

        return ocid.length <= 10 ? ocid : `...${ocid.slice(-10)}`;
    }

    toggleEnabled(instance: InstanceModel, enabled: boolean): void {
        const previousEnabled = instance.enabled;

        this.instances.set(this.instances().map((item) => (item.id === instance.id ? { ...item, enabled } : item)));
        this.markToggling(instance.id, true);
        this.error.set(null);
        this.actionFeedback.set(null);

        this.api.updateInstance(instance.id, { enabled }).subscribe({
            next: (updatedInstance) => {
                this.instances.set(this.instances().map((item) => (item.id === updatedInstance.id ? updatedInstance : item)));
                this.actionFeedbackSeverity.set('success');
                this.actionFeedback.set(`Instância ${updatedInstance.enabled ? 'habilitada' : 'desabilitada'} com sucesso.`);
                this.markToggling(instance.id, false);
            },
            error: (response: { error?: ApiErrorResponse }) => {
                this.instances.set(this.instances().map((item) => (item.id === instance.id ? { ...item, enabled: previousEnabled } : item)));
                this.actionFeedbackSeverity.set('error');
                this.actionFeedback.set(response.error?.detail ?? 'Não foi possível atualizar o status da instância.');
                this.markToggling(instance.id, false);
            }
        });
    }

    tagSeverity(state?: string | null): 'success' | 'danger' | 'contrast' | 'warn' {
        if (state === 'RUNNING') {
            return 'success';
        }
        if (state === 'STOPPED') {
            return 'contrast';
        }
        if (state === 'STOPPING' || state === 'STARTING') {
            return 'warn';
        }
        return 'danger';
    }

    refreshInstanceStatus(instance: InstanceModel): void {
        const previousState = instance.last_known_state ?? null;
        this.actionFeedback.set(null);
        this.error.set(null);
        this.markRefreshingRow(instance.id, true);

        this.api.getInstanceStatus(instance.id).subscribe({
            next: (execution) => {
                const nextState = execution.instance_state ?? previousState;
                this.instances.set(this.instances().map((item) => (item.id === instance.id ? { ...item, last_known_state: nextState } : item)));
                this.actionFeedbackSeverity.set(execution.status === 'failed' ? 'error' : 'success');
                this.actionFeedback.set(
                    execution.status === 'failed'
                        ? execution.stderr_summary || 'Não foi possível atualizar o status da instância.'
                        : `Status da instância ${instance.name} atualizado com sucesso.`
                );
                this.markRefreshingRow(instance.id, false);
            },
            error: (response: { error?: ApiErrorResponse }) => {
                this.instances.set(this.instances().map((item) => (item.id === instance.id ? { ...item, last_known_state: previousState } : item)));
                this.actionFeedbackSeverity.set('error');
                this.actionFeedback.set(response.error?.detail ?? 'Não foi possível atualizar o status da instância.');
                this.markRefreshingRow(instance.id, false);
            }
        });
    }

    private handleInstanceAction(instanceId: string, action: 'start' | 'stop'): void {
        this.actionFeedback.set(null);
        this.error.set(null);

        const request$ = action === 'start' ? this.api.startInstance(instanceId) : this.api.stopInstance(instanceId);
        request$.subscribe({
            next: (execution) => {
                this.actionFeedbackSeverity.set(execution.status === 'failed' ? 'error' : 'success');
                this.actionFeedback.set(
                    execution.status === 'failed'
                        ? execution.stderr_summary || 'A operação retornou falha no backend.'
                        : `Comando ${action === 'start' ? 'de inicialização' : 'de desligamento'} enviado com sucesso.`
                );
                this.loadInstances();
            },
            error: (response: { error?: ApiErrorResponse }) => {
                this.actionFeedbackSeverity.set('error');
                this.actionFeedback.set(response.error?.detail ?? 'Falha ao executar a ação na instância.');
                this.loadInstances();
            }
        });
    }

    private markToggling(instanceId: string, toggling: boolean): void {
        const next = new Set(this.togglingIds());
        if (toggling) {
            next.add(instanceId);
        } else {
            next.delete(instanceId);
        }
        this.togglingIds.set(next);
    }

    private markRefreshingRow(instanceId: string, refreshing: boolean): void {
        const next = new Set(this.refreshingRowIds());
        if (refreshing) {
            next.add(instanceId);
        } else {
            next.delete(instanceId);
        }
        this.refreshingRowIds.set(next);
    }
}
