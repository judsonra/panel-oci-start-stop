import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit, computed, inject, signal } from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { finalize } from 'rxjs';
import { MenuItem } from 'primeng/api';
import { AutoCompleteCompleteEvent, AutoCompleteModule } from 'primeng/autocomplete';
import { ButtonModule } from 'primeng/button';
import { CheckboxModule } from 'primeng/checkbox';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { ConfirmationService } from 'primeng/api';
import { DatePickerModule } from 'primeng/datepicker';
import { InputMaskModule } from 'primeng/inputmask';
import { MessageModule } from 'primeng/message';
import { MultiSelectModule } from 'primeng/multiselect';
import { SplitButtonModule } from 'primeng/splitbutton';
import { TableModule } from 'primeng/table';
import { TabsModule } from 'primeng/tabs';
import { TagModule } from 'primeng/tag';
import { TooltipModule } from 'primeng/tooltip';
import { ApiService } from '@/app/core/api.service';
import { GroupModel, InstanceModel, ScheduleModel } from '@/app/core/models';

type ScheduleTypeValue = 'one_time' | 'weekly' | 'monthly';
type ScheduleActionValue = 'start' | 'stop' | 'restart';

interface DayOption {
    label: string;
    value: number;
}

type ScheduleTargetTabValue = 0 | 1;

interface ScheduleFormValue {
    target_type: 'instance' | 'group' | null;
    instance: InstanceModel | string | null;
    instance_id: string;
    group: GroupModel | string | null;
    group_id: string;
    type: ScheduleTypeValue | null;
    action: ScheduleActionValue | null;
    run_at_utc: Date | null;
    run_time_utc: Date | null;
    days_of_week: number[] | null;
    days_of_month: number[] | null;
    time_utc: Date | null;
    enabled: boolean | null;
}

interface NormalizedScheduleFormValue {
    target_type: 'instance' | 'group';
    instance: InstanceModel | string | null;
    instance_id: string;
    group: GroupModel | string | null;
    group_id: string;
    type: ScheduleTypeValue;
    action: ScheduleActionValue;
    run_at_utc: Date | null;
    run_time_utc: Date | null;
    days_of_week: number[];
    days_of_month: number[];
    time_utc: Date | null;
    enabled: boolean;
}

@Component({
    selector: 'app-schedules-page',
    standalone: true,
    imports: [
        CommonModule,
        FormsModule,
        ReactiveFormsModule,
        AutoCompleteModule,
        ButtonModule,
        CheckboxModule,
        ConfirmDialogModule,
        DatePickerModule,
        InputMaskModule,
        MessageModule,
        MultiSelectModule,
        SplitButtonModule,
        TableModule,
        TabsModule,
        TagModule,
        TooltipModule
    ],
    providers: [ConfirmationService],
    styles: [
        `
            .month-days-panel {
                display: grid;
                gap: 0.75rem;
            }

            .month-days-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(3.25rem, 1fr));
                gap: 0.5rem;
            }

            .month-day-button {
                min-width: 0;
            }

            .month-day-actions {
                display: flex;
                justify-content: flex-end;
            }
        `
    ],
    template: `
        <section class="page-header">
            <div>
                <span class="section-kicker">Agendamentos</span>
                <h2>Automação recorrente e pontual</h2>
                <p>Defina a instância ou grupo, tipo de execução e ação desejada para o agendamento em UTC.</p>
            </div>
        </section>

        <p-confirmdialog></p-confirmdialog>

        @if (feedback()) {
            <p-message [severity]="feedbackSeverity()" [text]="feedback() || ''"></p-message>
        }

        <section class="instances-tabs-panel">
            <p-tabs [value]="activeTab()" (valueChange)="setActiveTab($event)">
                <p-tablist>
                    <p-tab [value]="0">Agendamentos</p-tab>
                    <p-tab [value]="1">Novo agendamento</p-tab>
                </p-tablist>
                <p-tabpanels>
                    <p-tabpanel [value]="0">
                        <div class="table-shell">
                            <p-table [value]="schedules()" [loading]="loading()" responsiveLayout="scroll">
                                <ng-template pTemplate="header">
                                    <tr>
                                        <th>Instâncias/Grupos</th>
                                        <th class="schedule-target-column">Alvo</th>
                                        <th>Tipo</th>
                                        <th class="schedule-action-column">Ação</th>
                                        <th class="schedule-execution-column">Execução UTC</th>
                                        <th class="schedule-status-column">Status</th>
                                    </tr>
                                </ng-template>
                                <ng-template pTemplate="body" let-schedule>
                                    <tr>
                                        <td>{{ scheduleDisplayName(schedule) }}</td>
                                        <td class="schedule-target-column">
                                            <i
                                                [class]="schedule.target_type === 'group' ? 'pi pi-sitemap' : 'pi pi-desktop'"
                                                [pTooltip]="schedule.target_type === 'group' ? 'Grupo de instância' : 'Instância'"
                                                tooltipPosition="top"
                                            ></i>
                                        </td>
                                        <td>{{ typeLabel(schedule.type) }}</td>
                                        <td class="schedule-action-column">{{ schedule.action | uppercase }}</td>
                                        <td class="schedule-execution-column">{{ executionLabel(schedule) }}</td>
                                        <td class="schedule-status-cell schedule-status-column">
                                            <p-tag [value]="schedule.enabled ? 'ON' : 'OFF'" [severity]="schedule.enabled ? 'success' : 'warn'"></p-tag>
                                            <p-splitbutton
                                                [label]="schedule.enabled ? 'Off' : 'On'"
                                                [icon]="schedule.enabled ? 'pi pi-pause' : 'pi pi-play'"
                                                size="small"
                                                [model]="rowMenuActions(schedule)"
                                                appendTo="body"
                                                [disabled]="isRowBusy(schedule.id)"
                                                (onClick)="toggleSchedule(schedule)"
                                            ></p-splitbutton>
                                        </td>
                                    </tr>
                                </ng-template>
                            </p-table>
                        </div>
                    </p-tabpanel>
                    <p-tabpanel [value]="1">
                        <form class="form-panel" [formGroup]="form" (ngSubmit)="save()">
                            @if (editingScheduleId()) {
                                <p-message severity="info" text="Editando agendamento selecionado."></p-message>
                            }

                            <p-tabs [value]="createTargetTab()" (valueChange)="setCreateTargetTab($event)">
                                <p-tablist>
                                    <p-tab [value]="0">Instância</p-tab>
                                    <p-tab [value]="1">Grupo de instância</p-tab>
                                </p-tablist>
                                <p-tabpanels>
                                    <p-tabpanel [value]="0">
                                        <label>
                                            <span>Instância</span>
                                            <p-autocomplete
                                                formControlName="instance"
                                                [suggestions]="instanceSuggestions()"
                                                optionLabel="name"
                                                [dropdown]="true"
                                                dropdownMode="blank"
                                                [completeOnFocus]="true"
                                                [showClear]="true"
                                                [forceSelection]="true"
                                                placeholder="Selecione pelo nome da instância"
                                                (completeMethod)="filterInstances($event)"
                                            />
                                        </label>
                                    </p-tabpanel>
                                    <p-tabpanel [value]="1">
                                        <label>
                                            <span>Grupo de instância</span>
                                            <p-autocomplete
                                                formControlName="group"
                                                [suggestions]="groupSuggestions()"
                                                optionLabel="name"
                                                [dropdown]="true"
                                                dropdownMode="blank"
                                                [completeOnFocus]="true"
                                                [showClear]="true"
                                                [forceSelection]="true"
                                                placeholder="Selecione pelo nome do grupo"
                                                (completeMethod)="filterGroups($event)"
                                            />
                                        </label>
                                    </p-tabpanel>
                                </p-tabpanels>
                            </p-tabs>

                            <label>
                                <span>Tipo</span>
                                <select formControlName="type" (change)="onTypeChange()">
                                    <option value="one_time">Execução única</option>
                                    <option value="weekly">Semanal</option>
                                    <option value="monthly">Mensal</option>
                                </select>
                            </label>

                            <label>
                                <span>Ação</span>
                                <select formControlName="action">
                                    <option value="start">Start</option>
                                    <option value="stop">Stop</option>
                                    <option value="restart">Restart</option>
                                </select>
                            </label>

                            @if (isOneTime()) {
                                <label>
                                    <span>Data</span>
                                    <p-datepicker
                                        formControlName="run_at_utc"
                                        inputId="schedule-run-at-input"
                                        [showIcon]="true"
                                        [showButtonBar]="true"
                                        appendTo="body"
                                        dateFormat="dd/mm/yy"
                                    />
                                </label>
                            }

                            @if (isOneTime()) {
                                <label>
                                    <span>Hora</span>
                                    <p-inputmask
                                        [ngModel]="runTimeInput()"
                                        (ngModelChange)="onRunTimeInputChange($event)"
                                        [ngModelOptions]="{ standalone: true }"
                                        mask="99:99"
                                        slotChar="hh:mm"
                                        placeholder="hh:mm"
                                        [autoClear]="false"
                                    />
                                </label>
                            }

                            @if (isWeekly()) {
                                <label>
                                    <span>Dias da semana</span>
                                    <p-multiselect
                                        formControlName="days_of_week"
                                        [options]="dayOptions"
                                        optionLabel="label"
                                        optionValue="value"
                                        placeholder="Selecione os dias"
                                        appendTo="body"
                                    />
                                </label>
                            }

                            @if (isMonthly()) {
                                <div class="month-days-panel">
                                    <span>Dias do mês</span>
                                    <div class="month-days-grid">
                                        @for (day of monthDayOptions; track day) {
                                            <button
                                                pButton
                                                type="button"
                                                class="month-day-button"
                                                [label]="day.toString()"
                                                [severity]="isMonthDaySelected(day) ? 'primary' : 'secondary'"
                                                [outlined]="!isMonthDaySelected(day)"
                                                (click)="toggleMonthDay(day)"
                                            ></button>
                                        }
                                    </div>
                                    <div class="month-day-actions">
                                        <button pButton type="button" label="Limpar" severity="secondary" [text]="true" (click)="clearMonthDays()"></button>
                                    </div>
                                </div>
                            }

                            @if (isWeekly() || isMonthly()) {
                                <label>
                                    <span>Horário UTC</span>
                                    <p-inputmask
                                        [ngModel]="scheduledTimeInput()"
                                        (ngModelChange)="onScheduledTimeInputChange($event)"
                                        [ngModelOptions]="{ standalone: true }"
                                        mask="99:99"
                                        slotChar="hh:mm"
                                        placeholder="hh:mm"
                                        [autoClear]="false"
                                    />
                                </label>
                            }

                            <div class="utc-clock-panel">
                                <span class="utc-clock-kicker">Hora UTC</span>
                                <strong>{{ utcClockDisplay() }}</strong>
                            </div>

                            <label class="checkbox-row">
                                <p-checkbox formControlName="enabled" [binary]="true" inputId="schedule-enabled"></p-checkbox>
                                <span>Agendamento habilitado</span>
                            </label>

                            <div class="form-actions">
                                <button pButton type="submit" label="Salvar agendamento" icon="pi pi-calendar-plus" [disabled]="saving()"></button>
                                @if (editingScheduleId()) {
                                    <button pButton type="button" label="Cancelar edição" severity="secondary" [outlined]="true" (click)="resetForm()"></button>
                                }
                            </div>
                        </form>
                    </p-tabpanel>
                </p-tabpanels>
            </p-tabs>
        </section>
    `
})
export class SchedulesPage implements OnInit, OnDestroy {
    private readonly api = inject(ApiService);
    private readonly formBuilder = inject(FormBuilder);
    private readonly confirmationService = inject(ConfirmationService);
    private clockTimer: number | null = null;
    private dateInputCleanup: (() => void) | null = null;

    readonly schedules = signal<ScheduleModel[]>([]);
    readonly instances = signal<InstanceModel[]>([]);
    readonly groups = signal<GroupModel[]>([]);
    readonly instanceSuggestions = signal<InstanceModel[]>([]);
    readonly groupSuggestions = signal<GroupModel[]>([]);
    readonly loading = signal(false);
    readonly saving = signal(false);
    readonly feedback = signal<string | null>(null);
    readonly feedbackSeverity = signal<'success' | 'error'>('success');
    readonly editingScheduleId = signal<string | null>(null);
    readonly rowBusyIds = signal<Set<string>>(new Set());
    readonly activeTab = signal(0);
    readonly createTargetTab = signal<ScheduleTargetTabValue>(0);
    readonly currentUtcDate = signal(new Date());
    readonly runTimeInput = signal('');
    readonly scheduledTimeInput = signal('');
    readonly utcClockDisplay = computed(() =>
        this.currentUtcDate().toLocaleTimeString('pt-BR', {
            timeZone: 'UTC',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
        })
    );

    readonly dayOptions: DayOption[] = [
        { label: 'Domingo', value: 6 },
        { label: 'Segunda-feira', value: 0 },
        { label: 'Terça-feira', value: 1 },
        { label: 'Quarta-feira', value: 2 },
        { label: 'Quinta-feira', value: 3 },
        { label: 'Sexta-feira', value: 4 },
        { label: 'Sábado', value: 5 }
    ];

    readonly monthDayOptions = Array.from({ length: 31 }, (_, index) => index + 1);

    readonly form = this.formBuilder.group({
        target_type: this.formBuilder.control<'instance' | 'group'>('instance', Validators.required),
        instance: this.formBuilder.control<InstanceModel | string | null>(null),
        instance_id: this.formBuilder.control('', { nonNullable: true }),
        group: this.formBuilder.control<GroupModel | string | null>(null),
        group_id: this.formBuilder.control('', { nonNullable: true }),
        type: this.formBuilder.control<ScheduleTypeValue>('one_time', Validators.required),
        action: this.formBuilder.control<ScheduleActionValue>('start', Validators.required),
        run_at_utc: this.formBuilder.control<Date | null>(null),
        run_time_utc: this.formBuilder.control<Date | null>(null),
        days_of_week: this.formBuilder.control<number[]>([], { nonNullable: true }),
        days_of_month: this.formBuilder.control<number[]>([], { nonNullable: true }),
        time_utc: this.formBuilder.control<Date | null>(null),
        enabled: this.formBuilder.control(true, { nonNullable: true })
    });

    ngOnInit(): void {
        this.form.controls.instance.valueChanges.subscribe((value) => {
            this.form.controls.instance_id.setValue(typeof value === 'object' && value ? value.id : '', { emitEvent: false });
        });
        this.form.controls.group.valueChanges.subscribe((value) => {
            this.form.controls.group_id.setValue(typeof value === 'object' && value ? value.id : '', { emitEvent: false });
        });
        this.form.controls.run_at_utc.valueChanges.subscribe((value) => {
            this.syncDateInputValue(value);
        });
        this.loadSchedules();
        this.loadInstances();
        this.loadGroups();
        this.startUtcClock();
        this.scheduleDateInputBinding();
    }

    ngOnDestroy(): void {
        if (this.clockTimer !== null) {
            window.clearInterval(this.clockTimer);
        }
        this.dateInputCleanup?.();
    }

    isOneTime(): boolean {
        return this.form.controls.type.value === 'one_time';
    }

    isWeekly(): boolean {
        return this.form.controls.type.value === 'weekly';
    }

    isMonthly(): boolean {
        return this.form.controls.type.value === 'monthly';
    }

    loadSchedules(): void {
        this.loading.set(true);
        this.api
            .listSchedules()
            .pipe(finalize(() => this.loading.set(false)))
            .subscribe((items) => this.schedules.set(items));
    }

    loadInstances(): void {
        this.api.listInstances().subscribe((items) => {
            this.instances.set(items);
            this.instanceSuggestions.set(items);
            this.syncSelectedInstanceFromId();
        });
    }

    loadGroups(): void {
        this.api.listGroups().subscribe((items) => {
            this.groups.set(items);
            this.groupSuggestions.set(items);
            this.syncSelectedGroupFromId();
        });
    }

    filterInstances(event: AutoCompleteCompleteEvent): void {
        const query = (event.query ?? '').trim().toLowerCase();
        if (!query) {
            this.instanceSuggestions.set(this.instances());
            return;
        }

        this.instanceSuggestions.set(this.instances().filter((instance) => instance.name.toLowerCase().includes(query)));
    }

    filterGroups(event: AutoCompleteCompleteEvent): void {
        const query = (event.query ?? '').trim().toLowerCase();
        if (!query) {
            this.groupSuggestions.set(this.groups());
            return;
        }

        this.groupSuggestions.set(this.groups().filter((group) => group.name.toLowerCase().includes(query)));
    }

    onTypeChange(): void {
        if (this.isOneTime()) {
            this.form.patchValue({ days_of_week: [], days_of_month: [], time_utc: null });
            this.scheduledTimeInput.set('');
        } else if (this.isWeekly()) {
            this.form.patchValue({ run_at_utc: null, run_time_utc: null });
            this.runTimeInput.set('');
            this.form.patchValue({ days_of_month: [] });
        } else {
            this.form.patchValue({ run_at_utc: null, run_time_utc: null, days_of_week: [] });
            this.runTimeInput.set('');
        }
        this.scheduleDateInputBinding();
    }

    save(): void {
        this.clearFeedback();

        if (!this.validateFormByType() || this.form.invalid) {
            this.form.markAllAsTouched();
            return;
        }

        const raw = this.normalizeScheduleFormValue(this.form.getRawValue());
        const payload = this.editingScheduleId() ? this.buildUpdatePayload(raw) : this.buildCreatePayload(raw);

        this.saving.set(true);

        const request$ = this.editingScheduleId()
            ? this.api.updateSchedule(this.editingScheduleId()!, payload)
            : this.api.createSchedule(payload);

        request$.pipe(finalize(() => this.saving.set(false))).subscribe({
            next: (schedule) => {
                this.feedbackSeverity.set('success');
                this.feedback.set(this.editingScheduleId() ? 'Agendamento atualizado com sucesso.' : 'Agendamento salvo com sucesso.');
                if (this.editingScheduleId()) {
                    this.schedules.set(this.schedules().map((item) => (item.id === schedule.id ? schedule : item)));
                } else {
                    this.schedules.set([schedule, ...this.schedules()]);
                }
                this.resetForm();
                this.activeTab.set(0);
            },
            error: (response: { error?: { detail?: string } }) => {
                this.feedbackSeverity.set('error');
                this.feedback.set(response.error?.detail ?? 'Não foi possível salvar o agendamento.');
            }
        });
    }

    rowMenuActions(schedule: ScheduleModel): MenuItem[] {
        return [
            {
                label: 'Editar',
                icon: 'pi pi-pencil',
                command: (event) => {
                    event?.originalEvent?.preventDefault?.();
                    event?.originalEvent?.stopPropagation?.();
                    this.editSchedule(schedule);
                }
            },
            {
                label: 'Excluir',
                icon: 'pi pi-times',
                command: (event) => {
                    event?.originalEvent?.preventDefault?.();
                    event?.originalEvent?.stopPropagation?.();
                    this.confirmDelete(schedule);
                }
            }
        ];
    }

    executionLabel(schedule: ScheduleModel): string {
        if (schedule.type === 'one_time') {
            return schedule.run_at_utc
                ? new Date(schedule.run_at_utc).toLocaleString('pt-BR', {
                      timeZone: 'UTC',
                      day: '2-digit',
                      month: '2-digit',
                      year: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                      hour12: false
                  })
                : '-';
        }
        if (schedule.type === 'weekly') {
            const days = (schedule.days_of_week ?? [])
                .map((day) => this.dayOptions.find((option) => option.value === day)?.label.slice(0, 3))
                .filter(Boolean)
                .join(', ');
            return [days, schedule.time_utc].filter(Boolean).join(' - ') || '-';
        }
        const days = (schedule.days_of_month ?? []).join(', ');
        return [days ? `Dias ${days}` : '', schedule.time_utc].filter(Boolean).join(' - ') || '-';
    }

    typeLabel(type: ScheduleTypeValue): string {
        if (type === 'one_time') {
            return 'Execução única';
        }
        if (type === 'weekly') {
            return 'Semanal';
        }
        return 'Mensal';
    }

    scheduleDisplayName(schedule: ScheduleModel): string {
        return schedule.target_type === 'group'
            ? schedule.group_name || schedule.group_id || '-'
            : schedule.instance_name || schedule.instance_id || '-';
    }

    isRowBusy(scheduleId: string): boolean {
        return this.rowBusyIds().has(scheduleId);
    }

    editSchedule(schedule: ScheduleModel): void {
        const instance = schedule.instance_id ? this.instances().find((item) => item.id === schedule.instance_id) ?? null : null;
        const group = schedule.group_id ? this.groups().find((item) => item.id === schedule.group_id) ?? null : null;
        this.editingScheduleId.set(schedule.id);
        const runAtUtc = schedule.run_at_utc ? new Date(schedule.run_at_utc) : null;
        this.form.reset({
            target_type: schedule.target_type,
            instance,
            instance_id: schedule.instance_id ?? '',
            group,
            group_id: schedule.group_id ?? '',
            type: schedule.type,
            action: schedule.action,
            run_at_utc: runAtUtc,
            run_time_utc: runAtUtc,
            days_of_week: schedule.days_of_week ?? [],
            days_of_month: schedule.days_of_month ?? [],
            time_utc: schedule.time_utc ? this.fromHourMinute(schedule.time_utc) : null,
            enabled: schedule.enabled
        });
        this.runTimeInput.set(runAtUtc ? this.toHourMinute(runAtUtc) : '');
        this.scheduledTimeInput.set(schedule.time_utc ?? '');
        this.instanceSuggestions.set(this.instances());
        this.groupSuggestions.set(this.groups());
        this.createTargetTab.set(schedule.target_type === 'group' ? 1 : 0);
        this.clearFeedback();
        this.activeTab.set(1);
        this.scheduleDateInputBinding();
    }

    resetForm(): void {
        this.editingScheduleId.set(null);
        this.form.reset({
            target_type: 'instance',
            instance: null,
            instance_id: '',
            group: null,
            group_id: '',
            type: 'one_time',
            action: 'start',
            run_at_utc: null,
            run_time_utc: null,
            days_of_week: [],
            days_of_month: [],
            time_utc: null,
            enabled: true
        });
        this.runTimeInput.set('');
        this.scheduledTimeInput.set('');
        this.instanceSuggestions.set(this.instances());
        this.groupSuggestions.set(this.groups());
        this.createTargetTab.set(0);
        this.activeTab.set(0);
        this.scheduleDateInputBinding();
    }

    setActiveTab(value: number | string | undefined): void {
        const nextValue = typeof value === 'number' ? value : Number(value ?? 0);
        this.activeTab.set(Number.isNaN(nextValue) ? 0 : nextValue);
    }

    setCreateTargetTab(value: number | string | undefined): void {
        const nextValue = typeof value === 'number' ? value : Number(value ?? 0);
        const normalized = nextValue === 1 ? 1 : 0;
        this.createTargetTab.set(normalized);
        this.form.controls.target_type.setValue(normalized === 1 ? 'group' : 'instance');
        if (normalized === 1) {
            this.form.patchValue({ instance: null, instance_id: '' });
        } else {
            this.form.patchValue({ group: null, group_id: '' });
        }
        this.scheduleDateInputBinding();
    }

    toggleSchedule(schedule: ScheduleModel): void {
        this.clearFeedback();
        this.markRowBusy(schedule.id, true);
        this.api.updateSchedule(schedule.id, { enabled: !schedule.enabled }).subscribe({
            next: (updated) => {
                this.schedules.set(this.schedules().map((item) => (item.id === updated.id ? updated : item)));
                this.feedbackSeverity.set('success');
                this.feedback.set(`Agendamento ${updated.enabled ? 'ativado' : 'desativado'} com sucesso.`);
                this.markRowBusy(schedule.id, false);
            },
            error: (response: { error?: { detail?: string } }) => {
                this.feedbackSeverity.set('error');
                this.feedback.set(response.error?.detail ?? 'Não foi possível atualizar o agendamento.');
                this.markRowBusy(schedule.id, false);
            }
        });
    }

    private confirmDelete(schedule: ScheduleModel): void {
        this.clearFeedback();
        this.confirmationService.confirm({
            message: `Deseja excluir o agendamento de ${this.scheduleDisplayName(schedule)}?`,
            header: 'Confirmar exclusão',
            icon: 'pi pi-exclamation-triangle',
            acceptLabel: 'Excluir',
            rejectLabel: 'Cancelar',
            acceptButtonStyleClass: 'p-button-danger',
            accept: () => this.deleteSchedule(schedule)
        });
    }

    private deleteSchedule(schedule: ScheduleModel): void {
        this.markRowBusy(schedule.id, true);
        this.api.deleteSchedule(schedule.id).subscribe({
            next: () => {
                this.schedules.set(this.schedules().filter((item) => item.id !== schedule.id));
                if (this.editingScheduleId() === schedule.id) {
                    this.resetForm();
                }
                this.feedbackSeverity.set('success');
                this.feedback.set('Agendamento excluído com sucesso.');
                this.markRowBusy(schedule.id, false);
            },
            error: (response: { error?: { detail?: string } }) => {
                this.feedbackSeverity.set('error');
                this.feedback.set(response.error?.detail ?? 'Não foi possível excluir o agendamento.');
                this.markRowBusy(schedule.id, false);
            }
        });
    }

    private validateFormByType(): boolean {
        if (this.form.controls.target_type.value === 'group') {
            if (!this.form.controls.group_id.value) {
                this.feedbackSeverity.set('error');
                this.feedback.set('Selecione um grupo cadastrado.');
                return false;
            }
        } else if (!this.form.controls.instance_id.value) {
            this.feedbackSeverity.set('error');
            this.feedback.set('Selecione uma instância cadastrada.');
            return false;
        }

        if (this.isOneTime()) {
            if (!this.form.controls.run_at_utc.value) {
                this.feedbackSeverity.set('error');
                this.feedback.set('Informe a data da execução única.');
                return false;
            }
            if (!this.form.controls.run_time_utc.value) {
                this.feedbackSeverity.set('error');
                this.feedback.set('Informe a hora da execução única.');
                return false;
            }
            return true;
        }

        if (this.isWeekly()) {
            if ((this.form.controls.days_of_week.value ?? []).length === 0) {
                this.feedbackSeverity.set('error');
                this.feedback.set('Selecione ao menos um dia da semana.');
                return false;
            }
            if (!this.form.controls.time_utc.value) {
                this.feedbackSeverity.set('error');
                this.feedback.set('Informe o horário UTC do agendamento semanal.');
                return false;
            }
            return true;
        }

        if ((this.form.controls.days_of_month.value ?? []).length === 0) {
            this.feedbackSeverity.set('error');
            this.feedback.set('Selecione ao menos um dia do mês.');
            return false;
        }
        if (!this.form.controls.time_utc.value) {
            this.feedbackSeverity.set('error');
            this.feedback.set('Informe o horário UTC do agendamento mensal.');
            return false;
        }
        return true;
    }

    private syncSelectedInstanceFromId(): void {
        const selectedInstanceId = this.form.controls.instance_id.value;
        if (!selectedInstanceId) {
            return;
        }

        const selectedInstance = this.instances().find((item) => item.id === selectedInstanceId) ?? null;
        this.form.controls.instance.setValue(selectedInstance, { emitEvent: false });
    }

    private syncSelectedGroupFromId(): void {
        const selectedGroupId = this.form.controls.group_id.value;
        if (!selectedGroupId) {
            return;
        }

        const selectedGroup = this.groups().find((item) => item.id === selectedGroupId) ?? null;
        this.form.controls.group.setValue(selectedGroup, { emitEvent: false });
    }

    private clearFeedback(): void {
        this.feedback.set(null);
    }

    private markRowBusy(scheduleId: string, busy: boolean): void {
        const next = new Set(this.rowBusyIds());
        if (busy) {
            next.add(scheduleId);
        } else {
            next.delete(scheduleId);
        }
        this.rowBusyIds.set(next);
    }

    private startUtcClock(): void {
        this.currentUtcDate.set(new Date());
        this.clockTimer = window.setInterval(() => {
            this.currentUtcDate.set(new Date());
        }, 1000);
    }

    onRunTimeInputChange(value: string | null): void {
        const normalized = value ?? '';
        this.runTimeInput.set(normalized);
        this.form.controls.run_time_utc.setValue(this.parseHourMinute(normalized), { emitEvent: false });
    }

    onScheduledTimeInputChange(value: string | null): void {
        const normalized = value ?? '';
        this.scheduledTimeInput.set(normalized);
        this.form.controls.time_utc.setValue(this.parseHourMinute(normalized), { emitEvent: false });
    }

    toggleMonthDay(day: number): void {
        const current = this.form.controls.days_of_month.value ?? [];
        const next = current.includes(day) ? current.filter((item) => item !== day) : [...current, day].sort((a, b) => a - b);
        this.form.controls.days_of_month.setValue(next);
    }

    clearMonthDays(): void {
        this.form.controls.days_of_month.setValue([]);
    }

    isMonthDaySelected(day: number): boolean {
        return (this.form.controls.days_of_month.value ?? []).includes(day);
    }

    private toUtcDateTimeIso(date: Date, time: Date): string {
        return new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate(), time.getHours(), time.getMinutes(), 0, 0)).toISOString();
    }

    private scheduleDateInputBinding(): void {
        window.setTimeout(() => this.bindDateInputMask(), 0);
    }

    private bindDateInputMask(): void {
        this.dateInputCleanup?.();

        const input = document.getElementById('schedule-run-at-input') as HTMLInputElement | null;
        if (!input) {
            this.dateInputCleanup = null;
            return;
        }

        input.maxLength = 10;
        input.placeholder = 'dd/mm/yyyy';
        this.syncDateInputValue(this.form.controls.run_at_utc.value);

        const handleInput = () => {
            const formatted = this.formatDateInput(input.value);
            if (input.value !== formatted) {
                input.value = formatted;
            }
            this.form.controls.run_at_utc.setValue(formatted.length === 10 ? this.parseDateInput(formatted) : null, { emitEvent: false });
        };

        const handleBlur = () => {
            const formatted = this.formatDateInput(input.value);
            const parsed = this.parseDateInput(formatted);
            input.value = parsed ? this.formatDateValue(parsed) : formatted;
            this.form.controls.run_at_utc.setValue(parsed, { emitEvent: false });
        };

        input.addEventListener('input', handleInput);
        input.addEventListener('blur', handleBlur);
        this.dateInputCleanup = () => {
            input.removeEventListener('input', handleInput);
            input.removeEventListener('blur', handleBlur);
        };
    }

    private syncDateInputValue(value: Date | null): void {
        const input = document.getElementById('schedule-run-at-input') as HTMLInputElement | null;
        if (!input) {
            return;
        }
        input.value = value ? this.formatDateValue(value) : '';
    }

    private formatDateInput(value: string): string {
        const digits = value.replace(/\D/g, '').slice(0, 8);
        if (digits.length <= 2) {
            return digits;
        }
        if (digits.length <= 4) {
            return `${digits.slice(0, 2)}/${digits.slice(2)}`;
        }
        return `${digits.slice(0, 2)}/${digits.slice(2, 4)}/${digits.slice(4)}`;
    }

    private parseDateInput(value: string): Date | null {
        const match = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(value);
        if (!match) {
            return null;
        }

        const day = Number(match[1]);
        const month = Number(match[2]);
        const year = Number(match[3]);
        const parsed = new Date(year, month - 1, day);
        if (
            Number.isNaN(parsed.getTime()) ||
            parsed.getFullYear() !== year ||
            parsed.getMonth() !== month - 1 ||
            parsed.getDate() !== day
        ) {
            return null;
        }
        return parsed;
    }

    private formatDateValue(value: Date): string {
        const day = String(value.getDate()).padStart(2, '0');
        const month = String(value.getMonth() + 1).padStart(2, '0');
        const year = value.getFullYear();
        return `${day}/${month}/${year}`;
    }

    private normalizeScheduleFormValue(raw: ScheduleFormValue): NormalizedScheduleFormValue {
        return {
            ...raw,
            target_type: raw.target_type ?? 'instance',
            type: raw.type ?? 'one_time',
            action: raw.action ?? 'start',
            days_of_week: raw.days_of_week ?? [],
            days_of_month: raw.days_of_month ?? [],
            enabled: raw.enabled ?? true
        };
    }

    private buildCreatePayload(raw: NormalizedScheduleFormValue): Partial<ScheduleModel> {
        const payload = this.buildCommonSchedulePayload(raw);
        if (payload.target_type === 'group') {
            return { ...payload, group_id: raw.group_id };
        }
        return { ...payload, instance_id: raw.instance_id };
    }

    private buildUpdatePayload(raw: NormalizedScheduleFormValue): Partial<ScheduleModel> {
        const payload = this.buildCommonSchedulePayload(raw);
        const currentSchedule = this.editingScheduleId() ? this.schedules().find((item) => item.id === this.editingScheduleId()) : null;
        if (payload.target_type === 'group') {
            return {
                ...payload,
                group_id: raw.group_id,
                ...(currentSchedule?.target_type === 'instance' ? { instance_id: null } : {})
            };
        }
        return {
            ...payload,
            instance_id: raw.instance_id,
            ...(currentSchedule?.target_type === 'group' ? { group_id: null } : {})
        };
    }

    private buildCommonSchedulePayload(raw: NormalizedScheduleFormValue): Partial<ScheduleModel> {
        return {
            target_type: raw.target_type,
            type: raw.type ?? 'one_time',
            action: raw.action ?? 'start',
            enabled: raw.enabled ?? true,
            run_at_utc: raw.type === 'one_time' && raw.run_at_utc && raw.run_time_utc ? this.toUtcDateTimeIso(raw.run_at_utc, raw.run_time_utc) : null,
            days_of_week: raw.type === 'weekly' ? raw.days_of_week : null,
            days_of_month: raw.type === 'monthly' ? raw.days_of_month : null,
            time_utc: raw.type !== 'one_time' && raw.time_utc ? this.toHourMinute(raw.time_utc) : null
        };
    }

    private toHourMinute(value: Date): string {
        const hours = String(value.getHours()).padStart(2, '0');
        const minutes = String(value.getMinutes()).padStart(2, '0');
        return `${hours}:${minutes}`;
    }

    private parseHourMinute(value: string): Date | null {
        const match = /^(\d{2}):(\d{2})$/.exec(value);
        if (!match) {
            return null;
        }

        const hours = Number(match[1]);
        const minutes = Number(match[2]);
        if (hours > 23 || minutes > 59) {
            return null;
        }

        const date = new Date();
        date.setHours(hours, minutes, 0, 0);
        return date;
    }

    private fromHourMinute(value: string): Date {
        const [hours, minutes] = value.split(':').map(Number);
        const date = new Date();
        date.setHours(hours, minutes, 0, 0);
        return date;
    }
}
