import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit, computed, inject, signal } from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { Subscription, concat, finalize, of, switchMap, timer } from 'rxjs';
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
import { ApiErrorResponse, ImportAllCompartmentsJobStatusModel, ImportAllCompartmentsModel, InstanceImportPreviewModel, InstanceModel, InstanceStatusRefreshModel } from '@/app/core/models';

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
            <button
                pButton
                type="button"
                label="Atualizar status"
                icon="pi pi-refresh"
                [severity]="refreshButtonSeverity()"
                styleClass="instances-refresh-button"
                [loading]="refreshButtonLoading()"
                [disabled]="refreshButtonDisabled()"
                (click)="openRefreshConfirmation()"
            ></button>
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
            [visible]="refreshProgressVisible()"
            [modal]="true"
            [closable]="false"
            [closeOnEscape]="true"
            [draggable]="false"
            [dismissableMask]="false"
            [resizable]="false"
            [style]="{ width: '34rem', maxWidth: 'calc(100vw - 2rem)' }"
            (onHide)="handleRefreshProgressHide()"
        >
            <ng-template pTemplate="header">
                <div class="dialog-header-with-action">
                    <span>Consultando status das instâncias</span>
                    <button
                        pButton
                        type="button"
                        icon="pi pi-times"
                        rounded
                        text
                        severity="secondary"
                        pTooltip="Cancelar e Fechar"
                        tooltipPosition="top"
                        aria-label="Cancelar e Fechar"
                        (click)="requestRefreshCancellation()"
                    ></button>
                </div>
            </ng-template>
            <div class="refresh-progress-copy">
                <span>{{ refreshProgressMessage() }}</span>
                @if (refreshCurrentInstanceName()) {
                    <small>Consultando: {{ refreshCurrentInstanceName() }}</small>
                }
            </div>
            <p-progressbar mode="indeterminate"></p-progressbar>
        </p-dialog>

        <p-dialog
            header="Registro Automático"
            [visible]="autoRegisterConfirmationVisible()"
            [modal]="true"
            [closable]="true"
            [draggable]="false"
            [resizable]="false"
            [style]="{ width: '34rem', maxWidth: 'calc(100vw - 2rem)' }"
            (visibleChange)="handleAutoRegisterConfirmationVisibility($event)"
        >
            <div class="auto-register-dialog-copy">
                <p>
                    Esta ação <span class="auto-register-warning-emphasis">NÃO PODE</span> ser
                    <span class="auto-register-warning-emphasis">CANCELADA</span>, é
                    <span class="auto-register-warning-emphasis">DEMORADA</span>, e pode gerar
                    <span class="auto-register-warning-emphasis">LENTIDÃO</span>. Deseja prosseguir.
                </p>
                <label>
                    <span>Digite <strong>Estou ciente</strong> para habilitar o botão Sim</span>
                    <input
                        pInputText
                        [ngModel]="autoRegisterConfirmationText()"
                        [ngModelOptions]="{ standalone: true }"
                        placeholder="Estou ciente"
                        (ngModelChange)="autoRegisterConfirmationText.set($event)"
                    />
                </label>
            </div>
            <ng-template pTemplate="footer">
                <button pButton type="button" label="Não" severity="secondary" [outlined]="true" (click)="cancelAutoRegisterConfirmation()"></button>
                <button pButton type="button" label="Sim" severity="danger" [disabled]="!autoRegisterCanConfirm()" (click)="confirmAutomaticRegistration()"></button>
            </ng-template>
        </p-dialog>

        <p-dialog
            [header]="autoRegisterCompleted() ? 'Registro Automático concluído' : 'Registro Automático em andamento'"
            [visible]="autoRegisterProgressVisible()"
            [modal]="true"
            [closable]="autoRegisterCompleted()"
            [closeOnEscape]="autoRegisterCompleted()"
            [draggable]="false"
            [dismissableMask]="false"
            [resizable]="false"
            [style]="{ width: '44rem', maxWidth: 'calc(100vw - 2rem)' }"
            (visibleChange)="handleAutoRegisterProgressVisibility($event)"
        >
            <div class="refresh-progress-copy">
                <strong>{{ autoRegisterProgressTitle() }}</strong>
                <span>{{ autoRegisterProgressMessage() }}</span>
                @if (autoRegisterCurrentCompartmentName()) {
                    <small>Compartimento atual: {{ autoRegisterCurrentCompartmentName() }}</small>
                }
                @if (autoRegisterCurrentInstanceName()) {
                    <small>Instância atual: {{ autoRegisterCurrentInstanceName() }}</small>
                }
                @if (autoRegisterLoading()) {
                    @if (autoRegisterHasDeterminateProgress()) {
                        <p-progressbar [value]="autoRegisterProgressPercent()"></p-progressbar>
                    } @else {
                        <p-progressbar mode="indeterminate"></p-progressbar>
                    }
                }
            </div>

            @if (autoRegisterResult(); as result) {
                <div class="auto-register-summary-grid">
                    <article class="auto-register-summary-card">
                        <span>Compartimentos</span>
                        <strong>{{ result.processed_compartments }} / {{ result.total_compartments }}</strong>
                    </article>
                    <article class="auto-register-summary-card">
                        <span>Instâncias</span>
                        <strong>{{ result.total_instances }}</strong>
                    </article>
                    <article class="auto-register-summary-card">
                        <span>Criadas</span>
                        <strong>{{ result.created }}</strong>
                    </article>
                    <article class="auto-register-summary-card">
                        <span>Atualizadas</span>
                        <strong>{{ result.updated }}</strong>
                    </article>
                    <article class="auto-register-summary-card">
                        <span>Sem alteração</span>
                        <strong>{{ result.unchanged }}</strong>
                    </article>
                    <article class="auto-register-summary-card">
                        <span>Falhas</span>
                        <strong>{{ result.failed }}</strong>
                    </article>
                </div>

                <div class="auto-register-compartments">
                    @for (compartment of result.compartments; track compartment.compartment_ocid) {
                        <article class="auto-register-compartment-card">
                            <header>
                                <strong>{{ compartment.compartment_name }}</strong>
                                <small>{{ compartment.total_instances }} instância(s)</small>
                            </header>
                            <p>
                                Criadas: {{ compartment.created }} | Atualizadas: {{ compartment.updated }} | Sem alteração:
                                {{ compartment.unchanged }} | Falhas: {{ compartment.failed }}
                            </p>
                        </article>
                    }
                </div>
            }

            <ng-template pTemplate="footer">
                @if (autoRegisterCompleted()) {
                    <button pButton type="button" label="Fechar" (click)="closeAutomaticRegistrationProgress()"></button>
                }
            </ng-template>
        </p-dialog>

        <section class="instances-tabs-panel">
            <p-tabs [value]="activeTab()" (valueChange)="setActiveTab($event)">
                <p-tablist>
                    <p-tab [value]="0">Instâncias cadastradas</p-tab>
                    <p-tab [value]="1">Importação de instâncias</p-tab>
                </p-tablist>
                <p-tabpanels>
                    <p-tabpanel [value]="0">
                        @if (actionFeedback()) {
                            <p-message [severity]="actionFeedbackSeverity()" [text]="actionFeedback() || ''"></p-message>
                        }
                        @if (error()) {
                            <p-message severity="error" [text]="error() || ''"></p-message>
                        }
                        @if (startStatusAlert()) {
                            <aside class="instances-slide-alert" role="alert" aria-live="assertive">
                                <div class="instances-slide-alert-copy">
                                    <i class="pi pi-exclamation-triangle" aria-hidden="true"></i>
                                    <span>{{ startStatusAlert() }}</span>
                                </div>
                                <button
                                    pButton
                                    type="button"
                                    icon="pi pi-times"
                                    text
                                    rounded
                                    severity="secondary"
                                    ariaLabel="Fechar alerta"
                                    (click)="dismissStartStatusAlert()"
                                >
                                </button>
                            </aside>
                        }
                        @if (stopStatusAlert()) {
                            <aside class="instances-slide-alert" role="alert" aria-live="assertive">
                                <div class="instances-slide-alert-copy">
                                    <i class="pi pi-exclamation-triangle" aria-hidden="true"></i>
                                    <span>{{ stopStatusAlert() }}</span>
                                </div>
                                <button
                                    pButton
                                    type="button"
                                    icon="pi pi-times"
                                    text
                                    rounded
                                    severity="secondary"
                                    ariaLabel="Fechar alerta"
                                    (click)="dismissStopStatusAlert()"
                                >
                                </button>
                            </aside>
                        }

                        <section class="table-filter-row instances-filter-row">
                            <input
                                pInputText
                                [ngModel]="instanceSearchTerm()"
                                [ngModelOptions]="{ standalone: true }"
                                placeholder="Filtrar por nome, OCID, IP público ou IP privado"
                                (ngModelChange)="instanceSearchTerm.set($event)"
                            />
                        </section>

                        @if (showInitialLoadingHint()) {
                            <p class="instances-loading-hint" aria-live="polite">Carregando instâncias...</p>
                        }

                        <div class="table-shell">
                            <p-table [value]="filteredInstances()" [loading]="tableLoading()" dataKey="id" responsiveLayout="scroll">
                                <ng-template pTemplate="header">
                                    <tr>
                                        <th>Nome</th>
                                        <th>URL</th>
                                        <th>OCID</th>
                                        <th>IP Privado</th>
                                        <th>Status</th>
                                        <th>Habilitada</th>
                                        <th class="actions-column">Ações</th>
                                    </tr>
                                </ng-template>
                                <ng-template pTemplate="body" let-instance>
                                    <tr>
                                        <td>{{ instance.name }}</td>
                                        <td>{{ instance.app_url || '-' }}</td>
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
                                        <td>{{ instance.private_ip || '-' }}</td>
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
                                            <div class="instance-actions-group" role="group" aria-label="Ações da instância">
                                                <p-button
                                                    type="button"
                                                    size="small"
                                                    severity="success"
                                                    variant="outlined"
                                                    icon="pi pi-check"
                                                    pTooltip="Ligar"
                                                    tooltipPosition="top"
                                                    ariaLabel="Ligar"
                                                    [loading]="isStarting(instance.id)"
                                                    (onClick)="start(instance.id)"
                                                    [disabled]="!canStartInstance(instance)"
                                                />
                                                <p-button
                                                    type="button"
                                                    size="small"
                                                    severity="danger"
                                                    variant="outlined"
                                                    icon="pi pi-times"
                                                    pTooltip="Desligar"
                                                    tooltipPosition="top"
                                                    ariaLabel="Desligar"
                                                    [loading]="isStopping(instance.id)"
                                                    (onClick)="stop(instance.id)"
                                                    [disabled]="!canStopInstance(instance)"
                                                />
                                                <p-button
                                                    type="button"
                                                    size="small"
                                                    severity="secondary"
                                                    variant="outlined"
                                                    icon="pi pi-refresh"
                                                    pTooltip="Atualizar status"
                                                    tooltipPosition="top"
                                                    ariaLabel="Atualizar status"
                                                    [loading]="isRefreshingRow(instance.id)"
                                                    (onClick)="refreshInstanceStatus(instance)"
                                                    [disabled]="!instance.enabled || isRefreshingRow(instance.id) || isStarting(instance.id) || isStopping(instance.id)"
                                                />
                                            </div>
                                        </td>
                                    </tr>
                                </ng-template>
                                <ng-template pTemplate="emptymessage">
                                    <tr>
                                        <td colspan="7">{{ showInitialLoadingHint() ? '' : 'Nenhuma instância cadastrada.' }}</td>
                                    </tr>
                                </ng-template>
                            </p-table>
                        </div>
                    </p-tabpanel>
                    <p-tabpanel [value]="1">
                        <form class="form-panel" [formGroup]="form" (ngSubmit)="save()">
                            @if (error()) {
                                <p-message severity="error" [text]="error() || ''"></p-message>
                            }

                            <label>
                                <span>OCID da instância</span>
                                <div class="instance-import-search-row">
                                    <input pInputText type="search" formControlName="ocid" placeholder="Cole o OCID da instância na OCI" />
                                    <button
                                        pButton
                                        type="button"
                                        label="Buscar"
                                        icon="pi pi-search"
                                        [loading]="importPreviewLoading()"
                                        [disabled]="importPreviewLoading() || saving()"
                                        (click)="lookupInstancePreview()"
                                    ></button>
                                </div>
                            </label>

                            @if (importPreview(); as preview) {
                                @if (preview.already_registered) {
                                    <p-message severity="warn" text="A instância informada já está cadastrada no banco local. O salvamento de um novo cadastro foi bloqueado."></p-message>
                                }

                                <section class="instance-import-preview-list" aria-label="Dados da instância">
                                    <p class="instance-import-preview-item">
                                        <span class="instance-import-preview-label">Nome:</span>
                                        <span class="instance-import-preview-value">{{ preview.name }}</span>
                                    </p>
                                    <p class="instance-import-preview-item">
                                        <span class="instance-import-preview-label">OCID:</span>
                                        <span class="instance-import-preview-value">{{ preview.ocid }}</span>
                                    </p>
                                    <p class="instance-import-preview-item">
                                        <span class="instance-import-preview-label">vCPU:</span>
                                        <span class="instance-import-preview-value">{{ formatNumber(preview.vcpu) }}</span>
                                    </p>
                                    <p class="instance-import-preview-item">
                                        <span class="instance-import-preview-label">Memória:</span>
                                        <span class="instance-import-preview-value">{{ formatMemory(preview.memory_gbs) }}</span>
                                    </p>
                                    <p class="instance-import-preview-item">
                                        <span class="instance-import-preview-label">IP Público:</span>
                                        <span class="instance-import-preview-value">{{ preview.public_ip || '-' }}</span>
                                    </p>
                                    <p class="instance-import-preview-item">
                                        <span class="instance-import-preview-label">IP Privado:</span>
                                        <span class="instance-import-preview-value">{{ preview.private_ip || '-' }}</span>
                                    </p>
                                    <p class="instance-import-preview-item">
                                        <span class="instance-import-preview-label">Compartimento:</span>
                                        <span class="instance-import-preview-value">{{ preview.compartment_name }}</span>
                                    </p>
                                </section>
                            }

                            <label>
                                <span>Descrição</span>
                                <textarea pTextarea formControlName="description" rows="4" placeholder="Contexto operacional ou observações"></textarea>
                            </label>

                            <label class="checkbox-row">
                                <input type="checkbox" formControlName="enabled" />
                                <span>Instância habilitada para comandos</span>
                            </label>

                            <div class="form-actions">
                                <button pButton type="submit" label="Salvar instância" icon="pi pi-save" [disabled]="!canSaveImportedInstance()"></button>
                                <button
                                    pButton
                                    type="button"
                                    label="Registro Automático"
                                    icon="pi pi-bolt"
                                    severity="danger"
                                    [disabled]="saving() || autoRegisterLoading()"
                                    (click)="openAutomaticRegistrationConfirmation()"
                                ></button>
                            </div>
                        </form>
                    </p-tabpanel>
                </p-tabpanels>
            </p-tabs>
        </section>
    `
})
export class InstancesPage implements OnInit, OnDestroy {
    private readonly api = inject(ApiService);
    private readonly formBuilder = inject(FormBuilder);
    private autoRegisterPollingSubscription: Subscription | null = null;
    private readonly startStatusPollingSubscriptions = new Map<string, Subscription>();
    private readonly stopStatusPollingSubscriptions = new Map<string, Subscription>();
    private readonly startStatusPollIntervalMs = 15000;
    private readonly maxStartStatusChecks = 4;

    readonly instances = signal<InstanceModel[]>([]);
    readonly importPreview = signal<InstanceImportPreviewModel | null>(null);
    readonly importPreviewLoading = signal(false);
    readonly loading = signal(false);
    readonly saving = signal(false);
    readonly error = signal<string | null>(null);
    readonly actionFeedback = signal<string | null>(null);
    readonly actionFeedbackSeverity = signal<'success' | 'error'>('success');
    readonly activeTab = signal(0);
    readonly togglingIds = signal<Set<string>>(new Set());
    readonly refreshingRowIds = signal<Set<string>>(new Set());
    readonly startingIds = signal<Set<string>>(new Set());
    readonly stoppingIds = signal<Set<string>>(new Set());
    readonly refreshConfirmationVisible = signal(false);
    readonly refreshProgressVisible = signal(false);
    readonly refreshingStatuses = signal(false);
    readonly instanceSearchTerm = signal('');
    readonly refreshCurrentInstanceName = signal<string | null>(null);
    readonly refreshProgressMessage = signal('Preparando consulta...');
    readonly refreshCancellationRequested = signal(false);
    readonly autoRegisterConfirmationVisible = signal(false);
    readonly autoRegisterLoading = signal(false);
    readonly autoRegisterProgressVisible = signal(false);
    readonly autoRegisterProgressMessage = signal('Preparando sincronização das instâncias...');
    readonly autoRegisterResult = signal<ImportAllCompartmentsModel | null>(null);
    readonly autoRegisterJobStatus = signal<ImportAllCompartmentsJobStatusModel | null>(null);
    readonly autoRegisterCompleted = signal(false);
    readonly autoRegisterConfirmationText = signal('');
    readonly startStatusAlert = signal<string | null>(null);
    readonly stopStatusAlert = signal<string | null>(null);
    readonly isInitialLoadPending = computed(() => this.loading() && this.instances().length === 0);
    readonly showInitialLoadingHint = computed(() => this.isInitialLoadPending());
    readonly tableLoading = computed(() => this.loading() && this.instances().length > 0);
    readonly refreshButtonDisabled = computed(() => this.isInitialLoadPending() || this.refreshingStatuses());
    readonly refreshButtonLoading = computed(() => this.refreshingStatuses());
    readonly refreshButtonSeverity = computed<'secondary' | 'success'>(() => (this.isInitialLoadPending() ? 'secondary' : 'success'));
    readonly canSaveImportedInstance = computed(() => {
        const preview = this.importPreview();
        return !!preview
            && !preview.already_registered
            && !this.saving()
            && !this.importPreviewLoading()
            && this.form.controls.ocid.valid
            && this.form.controls.ocid.value.trim() === preview.ocid;
    });
    readonly filteredInstances = computed(() => {
        const query = this.instanceSearchTerm().trim().toLowerCase();
        const items = this.instances();
        if (!query) {
            return items;
        }

        return items.filter((instance) =>
            [instance.name, instance.ocid, instance.app_url ?? '', instance.public_ip ?? '', instance.private_ip ?? '']
                .some((value) => value.toLowerCase().includes(query))
        );
    });
    readonly autoRegisterCanConfirm = computed(() => this.autoRegisterConfirmationText().trim() === 'Estou ciente');
    readonly autoRegisterProgressTitle = computed(() => {
        const job = this.autoRegisterJobStatus();
        const result = this.autoRegisterResult();
        if (job) {
            return `Compartimentos processados: ${job.processed_compartments} / ${job.total_compartments}`;
        }
        if (result) {
            return `Compartimentos processados: ${result.processed_compartments} / ${result.total_compartments}`;
        }
        return this.autoRegisterLoading() ? 'Consultando todos os compartimentos ativos...' : 'Sincronização pendente.';
    });
    readonly autoRegisterProgressPercent = computed(() => {
        const job = this.autoRegisterJobStatus();
        if (!job || job.total_instances <= 0) {
            return 0;
        }
        return Math.round((job.processed_instances / job.total_instances) * 100);
    });
    readonly autoRegisterHasDeterminateProgress = computed(() => (this.autoRegisterJobStatus()?.total_instances ?? 0) > 0);
    readonly autoRegisterCurrentCompartmentName = computed(() => this.autoRegisterJobStatus()?.current_compartment_name ?? null);
    readonly autoRegisterCurrentInstanceName = computed(() => this.autoRegisterJobStatus()?.current_instance_name ?? null);

    readonly form = this.formBuilder.nonNullable.group({
        ocid: ['', [Validators.required, Validators.pattern(/^ocid1\.instance\..+/)]],
        description: [''],
        enabled: [true]
    });

    ngOnInit(): void {
        this.form.controls.ocid.valueChanges.subscribe((value) => this.clearPreviewIfOcidChanged(value));
        this.loadInstances();
    }

    ngOnDestroy(): void {
        this.stopAutomaticRegistrationPolling();
        this.cancelAllStartStatusPolling();
        this.cancelAllStopStatusPolling();
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

    lookupInstancePreview(): void {
        if (this.form.controls.ocid.invalid) {
            this.form.controls.ocid.markAsTouched();
            return;
        }

        this.importPreviewLoading.set(true);
        this.importPreview.set(null);
        this.error.set(null);
        this.actionFeedback.set(null);

        this.api
            .importUpsertInstance({ ocid: this.form.controls.ocid.value.trim() })
            .pipe(finalize(() => this.importPreviewLoading.set(false)))
            .subscribe({
                next: (result) => {
                    if (result.mode === 'updated' && result.instance) {
                        const updatedInstance = result.instance;
                        const current = this.instances();
                        const next = current.some((item) => item.id === updatedInstance.id)
                            ? current.map((item) => (item.id === updatedInstance.id ? updatedInstance : item))
                            : [updatedInstance, ...current];
                        this.instances.set(next);
                        this.actionFeedbackSeverity.set('success');
                        this.actionFeedback.set(`Instância ${updatedInstance.name} atualizada automaticamente.`);
                        this.importPreview.set(null);
                        this.activeTab.set(0);
                        return;
                    }

                    this.importPreview.set(result.preview ?? null);
                },
                error: (response: { error?: ApiErrorResponse }) => {
                    this.error.set(response.error?.detail ?? 'Não foi possível consultar a instância na OCI.');
                }
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

    requestRefreshCancellation(): void {
        this.refreshCancellationRequested.set(true);
        this.refreshProgressVisible.set(false);
        this.refreshProgressMessage.set('Cancelamento solicitado. Finalizando a consulta em andamento...');
    }

    handleRefreshProgressHide(): void {
        if (this.refreshingStatuses()) {
            this.requestRefreshCancellation();
        }
    }

    openAutomaticRegistrationConfirmation(): void {
        this.actionFeedback.set(null);
        this.error.set(null);
        this.autoRegisterConfirmationText.set('');
        this.autoRegisterConfirmationVisible.set(true);
    }

    cancelAutoRegisterConfirmation(): void {
        this.autoRegisterConfirmationVisible.set(false);
        this.autoRegisterConfirmationText.set('');
    }

    handleAutoRegisterConfirmationVisibility(visible: boolean): void {
        if (!visible) {
            this.cancelAutoRegisterConfirmation();
        }
    }

    handleAutoRegisterProgressVisibility(visible: boolean): void {
        if (!visible && this.autoRegisterCompleted()) {
            this.closeAutomaticRegistrationProgress();
        }
    }

    closeAutomaticRegistrationProgress(): void {
        this.stopAutomaticRegistrationPolling();
        this.autoRegisterProgressVisible.set(false);
        this.autoRegisterCompleted.set(false);
        this.autoRegisterResult.set(null);
        this.autoRegisterJobStatus.set(null);
        this.autoRegisterProgressMessage.set('Preparando sincronização das instâncias...');
    }

    confirmRefreshStatuses(): void {
        this.refreshConfirmationVisible.set(false);

        if (this.instances().length === 0) {
            this.actionFeedbackSeverity.set('error');
            this.actionFeedback.set('Não há instâncias cadastradas para atualizar o status.');
            return;
        }

        this.refreshingStatuses.set(true);
        this.refreshProgressVisible.set(true);
        this.refreshCancellationRequested.set(false);
        this.refreshProgressMessage.set('Consultando os compartimentos e atualizando os status...');
        this.refreshCurrentInstanceName.set(null);
        this.error.set(null);
        this.actionFeedback.set(null);

        this.api.refreshInstanceStatuses().subscribe({
            next: (summary) => this.handleRefreshSummary(summary),
            error: (response: { error?: ApiErrorResponse }) => {
                this.refreshCurrentInstanceName.set(null);
                this.refreshProgressVisible.set(false);
                this.refreshingStatuses.set(false);
                this.actionFeedbackSeverity.set('error');
                this.actionFeedback.set(response.error?.detail ?? 'Não foi possível atualizar os status das instâncias.');
            }
        });
    }

    confirmAutomaticRegistration(): void {
        if (!this.autoRegisterCanConfirm()) {
            return;
        }

        this.autoRegisterConfirmationVisible.set(false);
        this.autoRegisterLoading.set(true);
        this.autoRegisterProgressVisible.set(true);
        this.autoRegisterCompleted.set(false);
        this.autoRegisterResult.set(null);
        this.autoRegisterJobStatus.set(null);
        this.autoRegisterProgressMessage.set('Iniciando o registro automático...');

        this.api
            .startImportAllCompartmentsInstancesJob()
            .subscribe({
                next: (job) => {
                    this.autoRegisterProgressMessage.set('Consultando os compartimentos ativos e importando as instâncias...');
                    this.startAutomaticRegistrationPolling(job.job_id);
                },
                error: (response: { error?: ApiErrorResponse }) => {
                    this.autoRegisterLoading.set(false);
                    this.autoRegisterCompleted.set(true);
                    this.autoRegisterProgressMessage.set('A sincronização foi interrompida por erro.');
                    this.actionFeedbackSeverity.set('error');
                    this.actionFeedback.set(response.error?.detail ?? 'Não foi possível executar o registro automático.');
                }
            });
    }

    save(): void {
        if (!this.canSaveImportedInstance()) {
            this.form.markAllAsTouched();
            return;
        }

        this.saving.set(true);
        this.error.set(null);
        this.actionFeedback.set(null);

        const payload = this.form.getRawValue();
        const request$ = this.api.importInstance({
            ocid: payload.ocid,
            description: payload.description,
            enabled: payload.enabled,
        });

        request$.pipe(finalize(() => this.saving.set(false))).subscribe({
                next: () => {
                    this.resetForm();
                    this.actionFeedbackSeverity.set('success');
                    this.actionFeedback.set('Instância importada com sucesso.');
                    this.activeTab.set(0);
                    this.loadInstances();
                },
                error: (response: { error?: ApiErrorResponse }) => {
                    this.error.set(response.error?.detail ?? 'Não foi possível salvar a instância.');
                }
            });
    }

    start(instanceId: string): void {
        const instance = this.instances().find((item) => item.id === instanceId);
        if (!instance || !this.canStartInstance(instance)) {
            return;
        }

        this.startStatusAlert.set(null);
        this.actionFeedback.set(null);
        this.error.set(null);
        this.markStarting(instance.id, true);
        this.cancelStartStatusPolling(instance.id);

        this.api.startInstance(instance.id).subscribe({
            next: (execution) => {
                const nextState = execution.instance_state ?? instance.last_known_state ?? null;
                this.updateInstanceState(instance.id, nextState);
                this.actionFeedbackSeverity.set(execution.status === 'failed' ? 'error' : 'success');
                this.actionFeedback.set(
                    execution.status === 'failed'
                        ? execution.stderr_summary || 'A operação retornou falha no backend.'
                        : `Comando de inicialização enviado com sucesso para ${instance.name}.`
                );

                if (execution.status === 'failed' || nextState === 'RUNNING') {
                    this.markStarting(instance.id, false);
                    return;
                }

                this.scheduleStartStatusCheck(instance.id, instance.name, 1);
            },
            error: (response: { error?: ApiErrorResponse }) => {
                this.actionFeedbackSeverity.set('error');
                this.actionFeedback.set(response.error?.detail ?? 'Falha ao executar a ação na instância.');
                this.markStarting(instance.id, false);
            }
        });
    }

    stop(instanceId: string): void {
        const instance = this.instances().find((item) => item.id === instanceId);
        if (!instance || !this.canStopInstance(instance)) {
            return;
        }

        this.stopStatusAlert.set(null);
        this.startStatusAlert.set(null);
        this.actionFeedback.set(null);
        this.error.set(null);
        this.markStopping(instance.id, true);
        this.cancelStopStatusPolling(instance.id);

        this.api.stopInstance(instance.id).subscribe({
            next: (execution) => {
                const fallbackState = execution.status === 'failed' ? (instance.last_known_state ?? null) : 'STOPPING';
                const nextState = execution.instance_state ?? fallbackState;
                this.updateInstanceState(instance.id, nextState);
                this.actionFeedbackSeverity.set(execution.status === 'failed' ? 'error' : 'success');
                this.actionFeedback.set(
                    execution.status === 'failed'
                        ? execution.stderr_summary || 'A operação retornou falha no backend.'
                        : `Comando de desligamento enviado com sucesso para ${instance.name}.`
                );

                if (execution.status === 'failed' || nextState === 'STOPPED') {
                    this.markStopping(instance.id, false);
                    return;
                }

                this.scheduleStopStatusCheck(instance.id, instance.name, 1);
            },
            error: (response: { error?: ApiErrorResponse }) => {
                this.actionFeedbackSeverity.set('error');
                this.actionFeedback.set(response.error?.detail ?? 'Falha ao executar a ação na instância.');
                this.markStopping(instance.id, false);
            }
        });
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

    isStarting(instanceId: string): boolean {
        return this.startingIds().has(instanceId);
    }

    isStopping(instanceId: string): boolean {
        return this.stoppingIds().has(instanceId);
    }

    canStartInstance(instance: InstanceModel): boolean {
        return instance.enabled && instance.last_known_state === 'STOPPED' && !this.isStarting(instance.id) && !this.isStopping(instance.id);
    }

    canStopInstance(instance: InstanceModel): boolean {
        return instance.enabled
            && instance.last_known_state !== 'STOPPED'
            && instance.last_known_state !== 'STOPPING'
            && !this.isStarting(instance.id)
            && !this.isStopping(instance.id);
    }

    dismissStartStatusAlert(): void {
        this.startStatusAlert.set(null);
    }

    dismissStopStatusAlert(): void {
        this.stopStatusAlert.set(null);
    }

    setActiveTab(value: string | number | undefined): void {
        this.activeTab.set(typeof value === 'number' ? value : Number(value ?? 0));
    }

    private startAutomaticRegistrationPolling(jobId: string): void {
        this.stopAutomaticRegistrationPolling();
        this.autoRegisterPollingSubscription = concat(of(0), timer(1500, 1500))
            .pipe(switchMap(() => this.api.getImportAllCompartmentsInstancesJob(jobId)))
            .subscribe({
                next: (status) => this.handleAutomaticRegistrationStatus(status),
                error: (response: { error?: ApiErrorResponse }) => {
                    this.stopAutomaticRegistrationPolling();
                    this.autoRegisterLoading.set(false);
                    this.autoRegisterCompleted.set(true);
                    this.autoRegisterProgressMessage.set('A sincronização foi interrompida por erro.');
                    this.actionFeedbackSeverity.set('error');
                    this.actionFeedback.set(response.error?.detail ?? 'Não foi possível acompanhar o registro automático.');
                }
            });
    }

    private stopAutomaticRegistrationPolling(): void {
        this.autoRegisterPollingSubscription?.unsubscribe();
        this.autoRegisterPollingSubscription = null;
    }

    private handleAutomaticRegistrationStatus(status: ImportAllCompartmentsJobStatusModel): void {
        this.autoRegisterJobStatus.set(status);

        if (status.status === 'completed' && status.result) {
            this.stopAutomaticRegistrationPolling();
            this.autoRegisterLoading.set(false);
            this.autoRegisterResult.set(status.result);
            this.autoRegisterCompleted.set(true);
            this.autoRegisterProgressMessage.set('Sincronização concluída. Revise o resumo abaixo.');
            this.actionFeedbackSeverity.set(status.result.failed > 0 ? 'error' : 'success');
            this.actionFeedback.set(
                status.result.failed > 0
                    ? `Registro automático concluído com ${status.result.created} criada(s), ${status.result.updated} atualizada(s), ${status.result.unchanged} sem alteração e ${status.result.failed} falha(s).`
                    : `Registro automático concluído com ${status.result.created} criada(s), ${status.result.updated} atualizada(s) e ${status.result.unchanged} sem alteração.`
            );
            this.activeTab.set(0);
            this.loadInstances();
            return;
        }

        if (status.status === 'failed') {
            this.stopAutomaticRegistrationPolling();
            this.autoRegisterLoading.set(false);
            this.autoRegisterCompleted.set(true);
            this.autoRegisterProgressMessage.set('A sincronização foi interrompida por erro.');
            this.actionFeedbackSeverity.set('error');
            this.actionFeedback.set(status.error ?? 'Não foi possível executar o registro automático.');
            return;
        }

        this.autoRegisterProgressMessage.set(
            status.total_instances > 0
                ? `Instâncias processadas: ${status.processed_instances} / ${status.total_instances}`
                : 'Consultando os compartimentos ativos e importando as instâncias...'
        );
    }

    formatNumber(value?: number | null): string {
        if (value == null) {
            return '-';
        }
        return Number.isInteger(value) ? `${value}` : value.toFixed(1);
    }

    formatMemory(value?: number | null): string {
        if (value == null) {
            return '-';
        }
        return `${this.formatNumber(value)} GB`;
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

    private handleRefreshSummary(summary: InstanceStatusRefreshModel): void {
        const failedCompartment = summary.compartments.find((item) => item.failed > 0);
        const lastProcessedCompartment = summary.compartments.length > 0 ? summary.compartments[summary.compartments.length - 1] : null;
        this.refreshCurrentInstanceName.set(failedCompartment?.compartment_name ?? lastProcessedCompartment?.compartment_name ?? null);
        this.refreshProgressMessage.set('Atualizando a listagem das instâncias...');
        this.refreshProgressVisible.set(false);
        this.refreshingStatuses.set(false);
        this.loadInstances();

        this.actionFeedbackSeverity.set(summary.failed > 0 ? 'error' : 'success');
        if (summary.failed > 0) {
            this.actionFeedback.set(
                `Atualização concluída: ${summary.updated} alterada(s), ${summary.unchanged} sem alteração e ${summary.failed} compartimento(s) com falha.`
            );
            return;
        }

        this.actionFeedback.set(
            `Atualização concluída: ${summary.updated} alterada(s), ${summary.unchanged} sem alteração em ${summary.processed_compartments} compartimento(s).`
        );
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

    private markStarting(instanceId: string, starting: boolean): void {
        const next = new Set(this.startingIds());
        if (starting) {
            next.add(instanceId);
        } else {
            next.delete(instanceId);
        }
        this.startingIds.set(next);
    }

    private markStopping(instanceId: string, stopping: boolean): void {
        const next = new Set(this.stoppingIds());
        if (stopping) {
            next.add(instanceId);
        } else {
            next.delete(instanceId);
        }
        this.stoppingIds.set(next);
    }

    private updateInstanceState(instanceId: string, nextState: string | null): void {
        this.instances.set(this.instances().map((item) => (item.id === instanceId ? { ...item, last_known_state: nextState } : item)));
    }

    private scheduleStartStatusCheck(instanceId: string, instanceName: string, attempt: number): void {
        this.cancelStartStatusPolling(instanceId);

        const subscription = timer(this.startStatusPollIntervalMs)
            .pipe(switchMap(() => this.api.getInstanceStatus(instanceId)))
            .subscribe({
                next: (execution) => {
                    const nextState = execution.instance_state ?? null;
                    this.updateInstanceState(instanceId, nextState);

                    if (nextState === 'RUNNING') {
                        this.markStarting(instanceId, false);
                        this.cancelStartStatusPolling(instanceId);
                        return;
                    }

                    if (attempt >= this.maxStartStatusChecks) {
                        this.markStarting(instanceId, false);
                        this.cancelStartStatusPolling(instanceId);
                        this.startStatusAlert.set(`Atualizar manualmente o status da ${instanceName}`);
                        return;
                    }

                    this.scheduleStartStatusCheck(instanceId, instanceName, attempt + 1);
                },
                error: (response: { error?: ApiErrorResponse }) => {
                    this.cancelStartStatusPolling(instanceId);
                    this.markStarting(instanceId, false);
                    this.actionFeedbackSeverity.set('error');
                    this.actionFeedback.set(response.error?.detail ?? 'Não foi possível atualizar o status da instância.');
                }
            });

        this.startStatusPollingSubscriptions.set(instanceId, subscription);
    }

    private cancelStartStatusPolling(instanceId: string): void {
        const current = this.startStatusPollingSubscriptions.get(instanceId);
        current?.unsubscribe();
        this.startStatusPollingSubscriptions.delete(instanceId);
    }

    private cancelAllStartStatusPolling(): void {
        for (const subscription of this.startStatusPollingSubscriptions.values()) {
            subscription.unsubscribe();
        }
        this.startStatusPollingSubscriptions.clear();
    }

    private scheduleStopStatusCheck(instanceId: string, instanceName: string, attempt: number): void {
        this.cancelStopStatusPolling(instanceId);

        const subscription = timer(this.startStatusPollIntervalMs)
            .pipe(switchMap(() => this.api.getInstanceStatus(instanceId)))
            .subscribe({
                next: (execution) => {
                    const nextState = execution.instance_state ?? null;
                    this.updateInstanceState(instanceId, nextState);

                    if (nextState === 'STOPPED') {
                        this.markStopping(instanceId, false);
                        this.cancelStopStatusPolling(instanceId);
                        return;
                    }

                    if (attempt >= this.maxStartStatusChecks) {
                        this.markStopping(instanceId, false);
                        this.cancelStopStatusPolling(instanceId);
                        this.stopStatusAlert.set(`Atualizar manualmente o status da ${instanceName}`);
                        return;
                    }

                    this.scheduleStopStatusCheck(instanceId, instanceName, attempt + 1);
                },
                error: (response: { error?: ApiErrorResponse }) => {
                    this.cancelStopStatusPolling(instanceId);
                    this.markStopping(instanceId, false);
                    this.actionFeedbackSeverity.set('error');
                    this.actionFeedback.set(response.error?.detail ?? 'Não foi possível atualizar o status da instância.');
                }
            });

        this.stopStatusPollingSubscriptions.set(instanceId, subscription);
    }

    private cancelStopStatusPolling(instanceId: string): void {
        const current = this.stopStatusPollingSubscriptions.get(instanceId);
        current?.unsubscribe();
        this.stopStatusPollingSubscriptions.delete(instanceId);
    }

    private cancelAllStopStatusPolling(): void {
        for (const subscription of this.stopStatusPollingSubscriptions.values()) {
            subscription.unsubscribe();
        }
        this.stopStatusPollingSubscriptions.clear();
    }

    private resetForm(): void {
        this.importPreview.set(null);
        this.form.reset({
            ocid: '',
            description: '',
            enabled: true
        });
    }

    private clearPreviewIfOcidChanged(value: string): void {
        const preview = this.importPreview();
        if (preview && preview.ocid !== value.trim()) {
            this.importPreview.set(null);
        }
    }
}
