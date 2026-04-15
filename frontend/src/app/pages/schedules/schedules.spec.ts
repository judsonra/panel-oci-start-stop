import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { ConfirmationService } from 'primeng/api';
import { ApiService } from '@/app/core/api.service';
import { AuthService } from '@/app/core/auth.service';
import { GroupModel, InstanceModel, ScheduleModel } from '@/app/core/models';
import { SchedulesPage } from './schedules';

describe('SchedulesPage', () => {
    let fixture: ComponentFixture<SchedulesPage>;
    let component: SchedulesPage;
    let apiService: jasmine.SpyObj<ApiService>;
    let authService: MockAuthService;
    let confirmationService: ConfirmationService;

    class MockAuthService {
        readonly canManage = signal(true);

        hasPermission(permission: string): boolean {
            if (permission === 'schedules.manage') {
                return this.canManage();
            }
            return true;
        }
    }

    const instances: InstanceModel[] = [
        {
            id: 'instance-1',
            name: 'VM Principal',
            ocid: 'ocid1.instance.oc1..example',
            enabled: true,
            created_at: '2026-03-12T00:00:00Z',
            updated_at: '2026-03-12T00:00:00Z'
        },
        {
            id: 'instance-2',
            name: 'Banco UTC',
            ocid: 'ocid1.instance.oc1..database',
            enabled: true,
            created_at: '2026-03-12T00:00:00Z',
            updated_at: '2026-03-12T00:00:00Z'
        }
    ];

    const groups: GroupModel[] = [
        {
            id: 'group-1',
            name: 'Grupo Banco',
            instance_count: 2,
            instances: [
                { id: 'instance-1', name: 'VM Principal', ocid: 'ocid1.instance.oc1..example' },
                { id: 'instance-2', name: 'Banco UTC', ocid: 'ocid1.instance.oc1..database' }
            ],
            created_at: '2026-03-12T00:00:00Z',
            updated_at: '2026-03-12T00:00:00Z'
        }
    ];

    const weeklySchedule: ScheduleModel = {
        id: 'schedule-1',
        target_type: 'instance',
        instance_id: 'instance-1',
        instance_name: 'VM Principal',
        type: 'weekly',
        action: 'restart',
        days_of_week: [0, 1, 2],
        days_of_month: null,
        time_utc: '14:30',
        enabled: true
    };

    beforeEach(async () => {
        apiService = jasmine.createSpyObj<ApiService>('ApiService', ['listSchedules', 'listInstances', 'listGroups', 'createSchedule', 'updateSchedule', 'deleteSchedule']);
        authService = new MockAuthService();
        apiService.listSchedules.and.returnValue(of([weeklySchedule]));
        apiService.listInstances.and.returnValue(of(instances));
        apiService.listGroups.and.returnValue(of(groups));
        apiService.createSchedule.and.returnValue(
            of({ ...weeklySchedule, id: 'schedule-2', type: 'one_time', action: 'start', run_at_utc: '2026-03-15T13:45:00.000Z', days_of_week: null, days_of_month: null, time_utc: null })
        );
        apiService.updateSchedule.and.returnValue(of({ ...weeklySchedule, enabled: false }));
        apiService.deleteSchedule.and.returnValue(of(void 0));

        await TestBed.configureTestingModule({
            imports: [SchedulesPage],
            providers: [
                { provide: ApiService, useValue: apiService },
                { provide: AuthService, useValue: authService }
            ]
        }).compileComponents();

        fixture = TestBed.createComponent(SchedulesPage);
        component = fixture.componentInstance;
        confirmationService = fixture.componentRef.injector.get(ConfirmationService);
        fixture.detectChanges();
    });

    it('opens with the schedules tab selected', () => {
        expect(component.activeTab()).toBe(0);
    });

    it('falls back to the schedules tab when p-tabs emits undefined', () => {
        component.activeTab.set(1);

        component.setActiveTab(undefined);

        expect(component.activeTab()).toBe(0);
    });

    it('keeps schedule list tab selected when user without manage permission tries to open form tab', () => {
        authService.canManage.set(false);

        component.setActiveTab(1);

        expect(component.activeTab()).toBe(0);
    });

    it('loads instances and schedules on init', () => {
        expect(apiService.listInstances).toHaveBeenCalled();
        expect(apiService.listGroups).toHaveBeenCalled();
        expect(apiService.listSchedules).toHaveBeenCalled();
        expect(component.schedules()[0].instance_name).toBe('VM Principal');
    });

    it('filters instances by name for autocomplete', () => {
        component.filterInstances({ query: 'banco', originalEvent: new Event('input') });

        expect(component.instanceSuggestions().length).toBe(1);
        expect(component.instanceSuggestions()[0].name).toBe('Banco UTC');
    });

    it('shows all instances in the autocomplete when query is empty', () => {
        component.filterInstances({ query: '', originalEvent: new Event('input') });

        expect(component.instanceSuggestions()).toEqual(instances);
    });

    it('shows the one-time date field only for one_time type', () => {
        component.form.controls.type.setValue('one_time');

        expect(component.isOneTime()).toBeTrue();
        expect(component.isWeekly()).toBeFalse();
        expect(component.isMonthly()).toBeFalse();
    });

    it('shows weekly fields only for weekly type', () => {
        component.form.controls.type.setValue('weekly');

        expect(component.isWeekly()).toBeTrue();
        expect(component.isOneTime()).toBeFalse();
        expect(component.isMonthly()).toBeFalse();
    });

    it('shows monthly fields only for monthly type', () => {
        component.form.controls.type.setValue('monthly');

        expect(component.isMonthly()).toBeTrue();
        expect(component.isOneTime()).toBeFalse();
        expect(component.isWeekly()).toBeFalse();
    });

    it('formats typed date digits as dd/mm/yyyy', () => {
        expect(component['formatDateInput']('05042026')).toBe('05/04/2026');
    });

    it('accepts valid 24h time input and converts it to Date', () => {
        component.onRunTimeInputChange('21:45');

        expect(component.runTimeInput()).toBe('21:45');
        expect(component.form.controls.run_time_utc.value?.getHours()).toBe(21);
        expect(component.form.controls.run_time_utc.value?.getMinutes()).toBe(45);
    });

    it('rejects invalid 24h time input', () => {
        component.onScheduledTimeInputChange('29:88');

        expect(component.scheduledTimeInput()).toBe('29:88');
        expect(component.form.controls.time_utc.value).toBeNull();
    });

    it('creates a one-time schedule with combined UTC date and time and returns to list tab', () => {
        component.activeTab.set(1);
        component.form.setValue({
            target_type: 'instance',
            instance: instances[0],
            instance_id: 'instance-1',
            group: null,
            group_id: '',
            type: 'one_time',
            action: 'start',
            run_at_utc: new Date('2026-03-15T00:00:00Z'),
            run_time_utc: new Date('2026-03-15T13:45:00Z'),
            days_of_week: [],
            days_of_month: [],
            time_utc: null,
            enabled: true
        });

        component.save();

        expect(apiService.createSchedule).toHaveBeenCalledWith({
            target_type: 'instance',
            instance_id: 'instance-1',
            type: 'one_time',
            action: 'start',
            enabled: true,
            run_at_utc: '2026-03-15T13:45:00.000Z',
            days_of_week: null,
            days_of_month: null,
            time_utc: null
        });
        expect(component.activeTab()).toBe(0);
    });

    it('creates a weekly schedule with selected weekdays and 24h time', () => {
        const time = new Date();
        time.setHours(21, 45, 0, 0);

        component.form.setValue({
            target_type: 'instance',
            instance: instances[1],
            instance_id: 'instance-2',
            group: null,
            group_id: '',
            type: 'weekly',
            action: 'restart',
            run_at_utc: null,
            run_time_utc: null,
            days_of_week: [6, 0, 2],
            days_of_month: [],
            time_utc: time,
            enabled: true
        });

        component.save();

        expect(apiService.createSchedule).toHaveBeenCalledWith({
            target_type: 'instance',
            instance_id: 'instance-2',
            type: 'weekly',
            action: 'restart',
            enabled: true,
            run_at_utc: null,
            days_of_week: [6, 0, 2],
            days_of_month: null,
            time_utc: '21:45'
        });
    });

    it('creates a monthly schedule with selected month days and time', () => {
        const time = new Date();
        time.setHours(7, 30, 0, 0);

        component.form.setValue({
            target_type: 'instance',
            instance: instances[0],
            instance_id: 'instance-1',
            group: null,
            group_id: '',
            type: 'monthly',
            action: 'stop',
            run_at_utc: null,
            run_time_utc: null,
            days_of_week: [],
            days_of_month: [1, 15, 31],
            time_utc: time,
            enabled: true
        });

        component.save();

        expect(apiService.createSchedule).toHaveBeenCalledWith({
            target_type: 'instance',
            instance_id: 'instance-1',
            type: 'monthly',
            action: 'stop',
            enabled: true,
            run_at_utc: null,
            days_of_week: null,
            days_of_month: [1, 15, 31],
            time_utc: '07:30'
        });
    });

    it('loads a schedule into the form for editing and navigates to the form tab', () => {
        component.editSchedule(weeklySchedule);

        expect(component.editingScheduleId()).toBe('schedule-1');
        expect((component.form.controls.instance.value as InstanceModel | null)?.id).toBe('instance-1');
        expect(component.form.controls.instance_id.value).toBe('instance-1');
        expect(component.form.controls.action.value).toBe('restart');
        expect(component.form.controls.days_of_week.value).toEqual([0, 1, 2]);
        expect(component.editDialogVisible()).toBeTrue();
        expect(component.activeTab()).toBe(0);
    });

    it('loads a monthly schedule into the form for editing', () => {
        const monthlySchedule: ScheduleModel = {
            id: 'schedule-3',
            target_type: 'instance',
            instance_id: 'instance-1',
            instance_name: 'VM Principal',
            type: 'monthly',
            action: 'stop',
            days_of_week: null,
            days_of_month: [5, 20, 31],
            time_utc: '08:15',
            enabled: true
        };

        component.editSchedule(monthlySchedule);

        expect(component.form.controls.type.value).toBe('monthly');
        expect(component.form.controls.days_of_month.value).toEqual([5, 20, 31]);
        expect(component.scheduledTimeInput()).toBe('08:15');
    });

    it('filters groups by name for autocomplete', () => {
        component.filterGroups({ query: 'banco', originalEvent: new Event('input') });

        expect(component.groupSuggestions().length).toBe(1);
        expect(component.groupSuggestions()[0].name).toBe('Grupo Banco');
    });

    it('creates a group weekly schedule with target_type group', () => {
        component.activeTab.set(1);
        component.setCreateTargetTab(1);
        component.form.setValue({
            target_type: 'group',
            instance: null,
            instance_id: '',
            group: groups[0],
            group_id: 'group-1',
            type: 'weekly',
            action: 'stop',
            run_at_utc: null,
            run_time_utc: null,
            days_of_week: [0, 2],
            days_of_month: [],
            time_utc: new Date('2026-03-15T21:30:00Z'),
            enabled: true
        });

        component.save();

        expect(apiService.createSchedule).toHaveBeenCalledWith({
            target_type: 'group',
            group_id: 'group-1',
            type: 'weekly',
            action: 'stop',
            enabled: true,
            run_at_utc: null,
            days_of_week: [0, 2],
            days_of_month: null,
            time_utc: '21:30'
        });
    });

    it('loads one-time schedule date and time into the form for editing', () => {
        const oneTimeSchedule: ScheduleModel = {
            id: 'schedule-2',
            target_type: 'instance',
            instance_id: 'instance-1',
            instance_name: 'VM Principal',
            type: 'one_time',
            action: 'start',
            run_at_utc: '2026-03-15T13:45:00.000Z',
            enabled: true
        };

        component.editSchedule(oneTimeSchedule);

        expect(component.form.controls.run_at_utc.value?.toISOString()).toBe('2026-03-15T13:45:00.000Z');
        expect(component.form.controls.run_time_utc.value?.getUTCHours()).toBe(13);
        expect(component.form.controls.run_time_utc.value?.getUTCMinutes()).toBe(45);
    });

    it('runs the edit command from the splitbutton menu', () => {
        const actions = component.rowMenuActions(weeklySchedule);

        actions[0].command?.({ originalEvent: new MouseEvent('click'), item: actions[0] });

        expect(component.editingScheduleId()).toBe('schedule-1');
        expect(component.editDialogVisible()).toBeTrue();
        expect(component.activeTab()).toBe(0);
    });

    it('updates the edited weekly schedule and returns to the schedules tab', () => {
        component.editSchedule(weeklySchedule);
        component.form.patchValue({
            action: 'stop',
            enabled: false
        });

        component.save();

        expect(apiService.updateSchedule).toHaveBeenCalledWith('schedule-1', {
            target_type: 'instance',
            instance_id: 'instance-1',
            group_id: null,
            type: 'weekly',
            action: 'stop',
            enabled: false,
            run_at_utc: null,
            days_of_week: [0, 1, 2],
            days_of_month: null,
            time_utc: '14:30'
        });
        expect(component.editDialogVisible()).toBeFalse();
        expect(component.activeTab()).toBe(0);
        expect(component.schedules()[0].enabled).toBeFalse();
    });

    it('clears instance_id when editing and switching the target from instance to group', () => {
        component.editSchedule(weeklySchedule);
        component.setCreateTargetTab(1);
        component.form.patchValue({
            target_type: 'group',
            group: groups[0],
            group_id: 'group-1'
        });

        component.save();

        expect(apiService.updateSchedule).toHaveBeenCalledWith('schedule-1', {
            target_type: 'group',
            group_id: 'group-1',
            instance_id: null,
            type: 'weekly',
            action: 'restart',
            enabled: true,
            run_at_utc: null,
            days_of_week: [0, 1, 2],
            days_of_month: null,
            time_utc: '14:30'
        });
    });

    it('closes edit dialog when cancelling an edit', () => {
        component.editSchedule(weeklySchedule);

        component.closeEditDialog();

        expect(component.editingScheduleId()).toBeNull();
        expect(component.editDialogVisible()).toBeFalse();
        expect(component.activeTab()).toBe(0);
    });

    it('restores create form draft after closing the edit dialog', () => {
        component.activeTab.set(1);
        component.form.patchValue({
            target_type: 'instance',
            instance: instances[1],
            instance_id: 'instance-2',
            type: 'weekly',
            action: 'stop',
            days_of_week: [1, 3],
            enabled: true
        });
        component.scheduledTimeInput.set('08:30');
        component.onScheduledTimeInputChange('08:30');

        component.editSchedule(weeklySchedule);
        component.closeEditDialog();

        expect(component.form.controls.instance_id.value).toBe('instance-2');
        expect(component.form.controls.action.value).toBe('stop');
        expect(component.form.controls.days_of_week.value).toEqual([1, 3]);
        expect(component.scheduledTimeInput()).toBe('08:30');
    });

    it('toggles a schedule on or off from the splitbutton primary action', () => {
        component.toggleSchedule(weeklySchedule);

        expect(apiService.updateSchedule).toHaveBeenCalledWith('schedule-1', { enabled: false });
        expect(component.schedules()[0].enabled).toBeFalse();
    });

    it('shows permission feedback when update returns 403', () => {
        apiService.updateSchedule.and.returnValue(throwError(() => ({ status: 403 })));

        component.toggleSchedule(weeklySchedule);

        expect(component.feedback()).toBe('Você não tem permissão para gerenciar agendamentos.');
    });

    it('keeps edit and delete options in the splitbutton menu', () => {
        const actions = component.rowMenuActions(weeklySchedule);

        expect(actions.map((item) => item.label)).toEqual(['Editar', 'Excluir']);
    });

    it('returns no row actions when user has no schedules.manage permission', () => {
        authService.canManage.set(false);

        expect(component.rowMenuActions(weeklySchedule)).toEqual([]);
    });

    it('requests confirmation before deleting a schedule', () => {
        const confirmSpy = spyOn(confirmationService, 'confirm');

        component['confirmDelete'](weeklySchedule);

        expect(confirmSpy).toHaveBeenCalled();
    });

    it('runs the delete command from the splitbutton menu', () => {
        const confirmSpy = spyOn(confirmationService, 'confirm');
        const actions = component.rowMenuActions(weeklySchedule);

        actions[1].command?.({ originalEvent: new MouseEvent('click'), item: actions[1] });

        expect(confirmSpy).toHaveBeenCalled();
    });

    it('deletes a schedule after confirmation', () => {
        component['deleteSchedule'](weeklySchedule);

        expect(apiService.deleteSchedule).toHaveBeenCalledWith('schedule-1');
        expect(component.schedules().length).toBe(0);
    });

    it('shows a utc clock display', () => {
        expect(component.utcClockDisplay()).toMatch(/^\d{2}:\d{2}:\d{2}$/);
    });

    it('shows schedules as read-only when user has no schedules.manage permission', () => {
        authService.canManage.set(false);
        fixture.detectChanges();

        const host: HTMLElement = fixture.nativeElement;
        expect(host.textContent).not.toContain('Novo agendamento');
        expect(host.querySelector('p-splitbutton')).toBeNull();
    });

    it('renders ON/OFF status tags instead of a toggle switch', () => {
        const host: HTMLElement = fixture.nativeElement;
        const tag = host.querySelector('.schedule-status-cell .p-tag');
        const statusCell = host.querySelector('.schedule-status-cell');

        expect(tag).not.toBeNull();
        expect(statusCell?.textContent).toContain('ON');
        expect(host.querySelector('.schedule-status-switch')).toBeNull();
    });

    it('renders the tabs and form labels in the template', () => {
        let text = fixture.nativeElement.textContent;
        expect(text).toContain('Agendamentos');
        expect(text).toContain('Novo agendamento');

        component.activeTab.set(1);
        component.form.controls.type.setValue('one_time');
        fixture.detectChanges();
        text = fixture.nativeElement.textContent;
        expect(text).toContain('Instância');
        expect(text).toContain('Grupo de instância');
        expect(text).toContain('Data');
        expect(text).toContain('Hora');
        expect(text).toContain('Hora UTC');

        component.form.controls.type.setValue('weekly');
        fixture.detectChanges();
        text = fixture.nativeElement.textContent;
        expect(text).toContain('Semanal');
        expect(text).toContain('Horário UTC');

        component.form.controls.type.setValue('monthly');
        fixture.detectChanges();
        text = fixture.nativeElement.textContent;
        expect(text).toContain('Mensal');
        expect(text).toContain('Dias do mês');
    });

    it('shows validation feedback when weekly schedule is missing time', () => {
        component.form.setValue({
            target_type: 'instance',
            instance: instances[0],
            instance_id: 'instance-1',
            group: null,
            group_id: '',
            type: 'weekly',
            action: 'start',
            run_at_utc: null,
            run_time_utc: null,
            days_of_week: [0],
            days_of_month: [],
            time_utc: null,
            enabled: true
        });

        component.save();

        expect(component.feedback()).toBe('Informe o horário UTC do agendamento semanal.');
        expect(apiService.createSchedule).not.toHaveBeenCalled();
    });

    it('shows validation feedback when monthly schedule is missing selected days', () => {
        component.form.setValue({
            target_type: 'instance',
            instance: instances[0],
            instance_id: 'instance-1',
            group: null,
            group_id: '',
            type: 'monthly',
            action: 'start',
            run_at_utc: null,
            run_time_utc: null,
            days_of_week: [],
            days_of_month: [],
            time_utc: new Date('2026-03-15T13:15:00Z'),
            enabled: true
        });

        component.save();

        expect(component.feedback()).toBe('Selecione ao menos um dia do mês.');
        expect(apiService.createSchedule).not.toHaveBeenCalled();
    });

    it('shows validation feedback when one-time schedule is missing time', () => {
        component.form.setValue({
            target_type: 'instance',
            instance: instances[0],
            instance_id: 'instance-1',
            group: null,
            group_id: '',
            type: 'one_time',
            action: 'start',
            run_at_utc: new Date('2026-03-15T00:00:00Z'),
            run_time_utc: null,
            days_of_week: [],
            days_of_month: [],
            time_utc: null,
            enabled: true
        });

        component.save();

        expect(component.feedback()).toBe('Informe a hora da execução única.');
        expect(apiService.createSchedule).not.toHaveBeenCalled();
    });

    it('surfaces save errors from the api', () => {
        apiService.createSchedule.and.returnValue(throwError(() => ({ error: { detail: 'Erro ao salvar' } })));
        component.form.setValue({
            target_type: 'instance',
            instance: instances[0],
            instance_id: 'instance-1',
            group: null,
            group_id: '',
            type: 'one_time',
            action: 'start',
            run_at_utc: new Date('2026-03-15T13:00:00'),
            run_time_utc: new Date('2026-03-15T13:15:00'),
            days_of_week: [],
            days_of_month: [],
            time_utc: null,
            enabled: true
        });

        component.save();

        expect(component.feedback()).toBe('Erro ao salvar');
    });

    it('shows validation feedback when no instance is selected', () => {
        component.form.setValue({
            target_type: 'instance',
            instance: null,
            instance_id: '',
            group: null,
            group_id: '',
            type: 'one_time',
            action: 'start',
            run_at_utc: new Date('2026-03-15T13:00:00'),
            run_time_utc: new Date('2026-03-15T13:15:00'),
            days_of_week: [],
            days_of_month: [],
            time_utc: null,
            enabled: true
        });

        component.save();

        expect(component.feedback()).toBe('Selecione uma instância cadastrada.');
        expect(apiService.createSchedule).not.toHaveBeenCalled();
    });

    it('shows validation feedback when group schedule is missing group selection', () => {
        component.setCreateTargetTab(1);
        component.form.setValue({
            target_type: 'group',
            instance: null,
            instance_id: '',
            group: null,
            group_id: '',
            type: 'one_time',
            action: 'start',
            run_at_utc: new Date('2026-03-15T00:00:00Z'),
            run_time_utc: new Date('2026-03-15T13:45:00Z'),
            days_of_week: [],
            days_of_month: [],
            time_utc: null,
            enabled: true
        });

        component.save();

        expect(component.feedback()).toBe('Selecione um grupo cadastrado.');
    });

    it('toggles and clears month day selections', () => {
        component.form.controls.type.setValue('monthly');

        component.toggleMonthDay(5);
        component.toggleMonthDay(20);

        expect(component.form.controls.days_of_month.value).toEqual([5, 20]);
        expect(component.isMonthDaySelected(5)).toBeTrue();

        component.clearMonthDays();

        expect(component.form.controls.days_of_month.value).toEqual([]);
    });

    it('formats monthly execution labels', () => {
        expect(
            component.executionLabel({
                ...weeklySchedule,
                type: 'monthly',
                days_of_week: null,
                days_of_month: [1, 15, 31],
                time_utc: '08:00'
            })
        ).toBe('Dias 1, 15, 31 - 08:00');
    });
});
