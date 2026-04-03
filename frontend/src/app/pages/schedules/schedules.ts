import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { finalize } from 'rxjs';
import { MenuItem } from 'primeng/api';
import { AutoCompleteCompleteEvent, AutoCompleteModule } from 'primeng/autocomplete';
import { ButtonModule } from 'primeng/button';
import { CheckboxModule } from 'primeng/checkbox';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { ConfirmationService } from 'primeng/api';
import { DatePickerModule } from 'primeng/datepicker';
import { MessageModule } from 'primeng/message';
import { MultiSelectModule } from 'primeng/multiselect';
import { SplitButtonModule } from 'primeng/splitbutton';
import { TableModule } from 'primeng/table';
import { TabsModule } from 'primeng/tabs';
import { TagModule } from 'primeng/tag';
import { ApiService } from '@/app/core/api.service';
import { InstanceModel, ScheduleModel } from '@/app/core/models';

type ScheduleTypeValue = 'one_time' | 'recurring';
type ScheduleActionValue = 'start' | 'stop' | 'restart';

interface DayOption {
    label: string;
    value: number;
}

@Component({
    selector: 'app-schedules-page',
    standalone: true,
    imports: [
        CommonModule,
        ReactiveFormsModule,
        AutoCompleteModule,
        ButtonModule,
        CheckboxModule,
        ConfirmDialogModule,
        DatePickerModule,
        MessageModule,
        MultiSelectModule,
        SplitButtonModule,
        TableModule,
        TabsModule,
        TagModule
    ],
    providers: [ConfirmationService],
    template: `
        <section class="page-header">
            <div>
                <span class="section-kicker">Agendamentos</span>
                <h2>Automação recorrente e pontual</h2>
                <p>Defina a instância, tipo de execução e ação desejada para o agendamento em UTC.</p>
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
                                        <th>Instância</th>
                                        <th>Tipo</th>
                                        <th>Ação</th>
                                        <th>Execução UTC</th>
                                        <th>Status</th>
                                    </tr>
                                </ng-template>
                                <ng-template pTemplate="body" let-schedule>
                                    <tr>
                                        <td>{{ schedule.instance_name || schedule.instance_id }}</td>
                                        <td>{{ schedule.type === 'one_time' ? 'Execução única' : 'Recorrente' }}</td>
                                        <td>{{ schedule.action | uppercase }}</td>
                                        <td>{{ executionLabel(schedule) }}</td>
                                        <td class="schedule-status-cell">
                                            <p-tag [severity]="schedule.enabled ? 'success' : 'contrast'" [value]="schedule.enabled ? 'ativo' : 'inativo'"></p-tag>
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

                            <label>
                                <span>Tipo</span>
                                <select formControlName="type" (change)="onTypeChange()">
                                    <option value="one_time">Execução única</option>
                                    <option value="recurring">Recorrente</option>
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
                                    <p-datepicker formControlName="run_at_utc" [showIcon]="true" appendTo="body" dateFormat="dd/mm/yy" />
                                </label>
                            }

                            @if (isOneTime()) {
                                <label>
                                    <span>Hora</span>
                                    <p-datepicker formControlName="run_time_utc" [timeOnly]="true" hourFormat="24" appendTo="body" />
                                </label>
                            }

                            @if (isRecurring()) {
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

                            @if (isRecurring()) {
                                <label>
                                    <span>Horário UTC</span>
                                    <p-datepicker formControlName="time_utc" [timeOnly]="true" hourFormat="24" appendTo="body" />
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

    readonly schedules = signal<ScheduleModel[]>([]);
    readonly instances = signal<InstanceModel[]>([]);
    readonly instanceSuggestions = signal<InstanceModel[]>([]);
    readonly loading = signal(false);
    readonly saving = signal(false);
    readonly feedback = signal<string | null>(null);
    readonly feedbackSeverity = signal<'success' | 'error'>('success');
    readonly editingScheduleId = signal<string | null>(null);
    readonly rowBusyIds = signal<Set<string>>(new Set());
    readonly activeTab = signal(0);
    readonly currentUtcDate = signal(new Date());
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

    readonly form = this.formBuilder.group({
        instance: this.formBuilder.control<InstanceModel | string | null>(null, Validators.required),
        instance_id: this.formBuilder.control('', { nonNullable: true }),
        type: this.formBuilder.control<ScheduleTypeValue>('one_time', Validators.required),
        action: this.formBuilder.control<ScheduleActionValue>('start', Validators.required),
        run_at_utc: this.formBuilder.control<Date | null>(null),
        run_time_utc: this.formBuilder.control<Date | null>(null),
        days_of_week: this.formBuilder.control<number[]>([], { nonNullable: true }),
        time_utc: this.formBuilder.control<Date | null>(null),
        enabled: this.formBuilder.control(true, { nonNullable: true })
    });

    ngOnInit(): void {
        this.form.controls.instance.valueChanges.subscribe((value) => {
            this.form.controls.instance_id.setValue(typeof value === 'object' && value ? value.id : '', { emitEvent: false });
        });
        this.loadSchedules();
        this.loadInstances();
        this.startUtcClock();
    }

    ngOnDestroy(): void {
        if (this.clockTimer !== null) {
            window.clearInterval(this.clockTimer);
        }
    }

    isOneTime(): boolean {
        return this.form.controls.type.value === 'one_time';
    }

    isRecurring(): boolean {
        return this.form.controls.type.value === 'recurring';
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

    filterInstances(event: AutoCompleteCompleteEvent): void {
        const query = (event.query ?? '').trim().toLowerCase();
        if (!query) {
            this.instanceSuggestions.set(this.instances());
            return;
        }

        this.instanceSuggestions.set(this.instances().filter((instance) => instance.name.toLowerCase().includes(query)));
    }

    onTypeChange(): void {
        if (this.isOneTime()) {
            this.form.patchValue({ days_of_week: [], time_utc: null });
        } else {
            this.form.patchValue({ run_at_utc: null, run_time_utc: null });
        }
    }

    save(): void {
        this.clearFeedback();

        if (!this.validateFormByType() || this.form.invalid) {
            this.form.markAllAsTouched();
            return;
        }

        const raw = this.form.getRawValue();
        const payload: Partial<ScheduleModel> = {
            instance_id: raw.instance_id,
            type: raw.type ?? 'one_time',
            action: raw.action ?? 'start',
            enabled: raw.enabled ?? true,
            run_at_utc: raw.type === 'one_time' && raw.run_at_utc && raw.run_time_utc ? this.toUtcDateTimeIso(raw.run_at_utc, raw.run_time_utc) : null,
            days_of_week: raw.type === 'recurring' ? raw.days_of_week : null,
            time_utc: raw.type === 'recurring' && raw.time_utc ? this.toHourMinute(raw.time_utc) : null
        };

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

        const days = (schedule.days_of_week ?? [])
            .map((day) => this.dayOptions.find((option) => option.value === day)?.label.slice(0, 3))
            .filter(Boolean)
            .join(', ');
        return [days, schedule.time_utc].filter(Boolean).join(' - ') || '-';
    }

    isRowBusy(scheduleId: string): boolean {
        return this.rowBusyIds().has(scheduleId);
    }

    editSchedule(schedule: ScheduleModel): void {
        const instance = this.instances().find((item) => item.id === schedule.instance_id) ?? null;
        this.editingScheduleId.set(schedule.id);
        const runAtUtc = schedule.run_at_utc ? new Date(schedule.run_at_utc) : null;
        this.form.reset({
            instance,
            instance_id: schedule.instance_id,
            type: schedule.type,
            action: schedule.action,
            run_at_utc: runAtUtc,
            run_time_utc: runAtUtc,
            days_of_week: schedule.days_of_week ?? [],
            time_utc: schedule.time_utc ? this.fromHourMinute(schedule.time_utc) : null,
            enabled: schedule.enabled
        });
        this.instanceSuggestions.set(this.instances());
        this.clearFeedback();
        this.activeTab.set(1);
    }

    resetForm(): void {
        this.editingScheduleId.set(null);
        this.form.reset({
            instance: null,
            instance_id: '',
            type: 'one_time',
            action: 'start',
            run_at_utc: null,
            run_time_utc: null,
            days_of_week: [],
            time_utc: null,
            enabled: true
        });
        this.instanceSuggestions.set(this.instances());
        this.activeTab.set(0);
    }

    setActiveTab(value: number | string | undefined): void {
        const nextValue = typeof value === 'number' ? value : Number(value ?? 0);
        this.activeTab.set(Number.isNaN(nextValue) ? 0 : nextValue);
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
            message: `Deseja excluir o agendamento da instância ${schedule.instance_name || schedule.instance_id}?`,
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
        if (!this.form.controls.instance_id.value) {
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

        if ((this.form.controls.days_of_week.value ?? []).length === 0) {
            this.feedbackSeverity.set('error');
            this.feedback.set('Selecione ao menos um dia da semana.');
            return false;
        }
        if (!this.form.controls.time_utc.value) {
            this.feedbackSeverity.set('error');
            this.feedback.set('Informe o horário UTC do agendamento recorrente.');
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

    private toUtcDateTimeIso(date: Date, time: Date): string {
        return new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate(), time.getHours(), time.getMinutes(), 0, 0)).toISOString();
    }

    private toHourMinute(value: Date): string {
        const hours = String(value.getHours()).padStart(2, '0');
        const minutes = String(value.getMinutes()).padStart(2, '0');
        return `${hours}:${minutes}`;
    }

    private fromHourMinute(value: string): Date {
        const [hours, minutes] = value.split(':').map(Number);
        const date = new Date();
        date.setHours(hours, minutes, 0, 0);
        return date;
    }
}
