import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { ConfirmationService } from 'primeng/api';
import { ApiService } from '@/app/core/api.service';
import { GroupModel, InstanceModel, ScheduleModel } from '@/app/core/models';
import { SchedulesPage } from './schedules';

describe('SchedulesPage', () => {
    let fixture: ComponentFixture<SchedulesPage>;
    let component: SchedulesPage;
    let apiService: jasmine.SpyObj<ApiService>;
    let confirmationService: ConfirmationService;

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

    const schedule: ScheduleModel = {
        id: 'schedule-1',
        target_type: 'instance',
        instance_id: 'instance-1',
        instance_name: 'VM Principal',
        type: 'recurring',
        action: 'restart',
        days_of_week: [0, 1, 2],
        time_utc: '14:30',
        enabled: true
    };

    beforeEach(async () => {
        apiService = jasmine.createSpyObj<ApiService>('ApiService', ['listSchedules', 'listInstances', 'listGroups', 'createSchedule', 'updateSchedule', 'deleteSchedule']);
        apiService.listSchedules.and.returnValue(of([schedule]));
        apiService.listInstances.and.returnValue(of(instances));
        apiService.listGroups.and.returnValue(of(groups));
        apiService.createSchedule.and.returnValue(of({ ...schedule, id: 'schedule-2', type: 'one_time', action: 'start', run_at_utc: '2026-03-15T13:45:00.000Z', days_of_week: null, time_utc: null }));
        apiService.updateSchedule.and.returnValue(of({ ...schedule, enabled: false }));
        apiService.deleteSchedule.and.returnValue(of(void 0));

        await TestBed.configureTestingModule({
            imports: [SchedulesPage],
            providers: [{ provide: ApiService, useValue: apiService }]
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
        expect(component.isRecurring()).toBeFalse();
    });

    it('shows recurring fields only for recurring type', () => {
        component.form.controls.type.setValue('recurring');

        expect(component.isRecurring()).toBeTrue();
        expect(component.isOneTime()).toBeFalse();
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
        component.onRecurringTimeInputChange('29:88');

        expect(component.recurringTimeInput()).toBe('29:88');
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
            time_utc: null
        });
        expect(component.activeTab()).toBe(0);
    });

    it('creates a recurring schedule with selected weekdays and 24h time', () => {
        const time = new Date();
        time.setHours(21, 45, 0, 0);

        component.form.setValue({
            target_type: 'instance',
            instance: instances[1],
            instance_id: 'instance-2',
            group: null,
            group_id: '',
            type: 'recurring',
            action: 'restart',
            run_at_utc: null,
            run_time_utc: null,
            days_of_week: [6, 0, 2],
            time_utc: time,
            enabled: true
        });

        component.save();

        expect(apiService.createSchedule).toHaveBeenCalledWith({
            target_type: 'instance',
            instance_id: 'instance-2',
            type: 'recurring',
            action: 'restart',
            enabled: true,
            run_at_utc: null,
            days_of_week: [6, 0, 2],
            time_utc: '21:45'
        });
    });

    it('loads a schedule into the form for editing and navigates to the form tab', () => {
        component.editSchedule(schedule);

        expect(component.editingScheduleId()).toBe('schedule-1');
        expect((component.form.controls.instance.value as InstanceModel | null)?.id).toBe('instance-1');
        expect(component.form.controls.instance_id.value).toBe('instance-1');
        expect(component.form.controls.action.value).toBe('restart');
        expect(component.form.controls.days_of_week.value).toEqual([0, 1, 2]);
        expect(component.activeTab()).toBe(1);
    });

    it('filters groups by name for autocomplete', () => {
        component.filterGroups({ query: 'banco', originalEvent: new Event('input') });

        expect(component.groupSuggestions().length).toBe(1);
        expect(component.groupSuggestions()[0].name).toBe('Grupo Banco');
    });

    it('creates a group schedule with target_type group', () => {
        component.activeTab.set(1);
        component.setCreateTargetTab(1);
        component.form.setValue({
            target_type: 'group',
            instance: null,
            instance_id: '',
            group: groups[0],
            group_id: 'group-1',
            type: 'recurring',
            action: 'stop',
            run_at_utc: null,
            run_time_utc: null,
            days_of_week: [0, 2],
            time_utc: new Date('2026-03-15T21:30:00Z'),
            enabled: true
        });

        component.save();

        expect(apiService.createSchedule).toHaveBeenCalledWith({
            target_type: 'group',
            group_id: 'group-1',
            type: 'recurring',
            action: 'stop',
            enabled: true,
            run_at_utc: null,
            days_of_week: [0, 2],
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
        const actions = component.rowMenuActions(schedule);

        actions[0].command?.({ originalEvent: new MouseEvent('click'), item: actions[0] });

        expect(component.editingScheduleId()).toBe('schedule-1');
        expect(component.activeTab()).toBe(1);
    });

    it('updates the edited schedule and returns to the schedules tab', () => {
        component.editSchedule(schedule);
        component.form.patchValue({
            action: 'stop',
            enabled: false
        });

        component.save();

        expect(apiService.updateSchedule).toHaveBeenCalledWith('schedule-1', {
            target_type: 'instance',
            instance_id: 'instance-1',
            group_id: null,
            type: 'recurring',
            action: 'stop',
            enabled: false,
            run_at_utc: null,
            days_of_week: [0, 1, 2],
            time_utc: '14:30'
        });
        expect(component.activeTab()).toBe(0);
        expect(component.schedules()[0].enabled).toBeFalse();
    });

    it('clears instance_id when editing and switching the target from instance to group', () => {
        component.editSchedule(schedule);
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
            type: 'recurring',
            action: 'restart',
            enabled: true,
            run_at_utc: null,
            days_of_week: [0, 1, 2],
            time_utc: '14:30'
        });
    });

    it('returns to the schedules tab when cancelling an edit', () => {
        component.editSchedule(schedule);

        component.resetForm();

        expect(component.editingScheduleId()).toBeNull();
        expect(component.activeTab()).toBe(0);
    });

    it('toggles a schedule on or off from the splitbutton primary action', () => {
        component.toggleSchedule(schedule);

        expect(apiService.updateSchedule).toHaveBeenCalledWith('schedule-1', { enabled: false });
        expect(component.schedules()[0].enabled).toBeFalse();
    });

    it('keeps edit and delete options in the splitbutton menu', () => {
        const actions = component.rowMenuActions(schedule);

        expect(actions.map((item) => item.label)).toEqual(['Editar', 'Excluir']);
    });

    it('requests confirmation before deleting a schedule', () => {
        const confirmSpy = spyOn(confirmationService, 'confirm');

        component['confirmDelete'](schedule);

        expect(confirmSpy).toHaveBeenCalled();
    });

    it('runs the delete command from the splitbutton menu', () => {
        const confirmSpy = spyOn(confirmationService, 'confirm');
        const actions = component.rowMenuActions(schedule);

        actions[1].command?.({ originalEvent: new MouseEvent('click'), item: actions[1] });

        expect(confirmSpy).toHaveBeenCalled();
    });

    it('deletes a schedule after confirmation', () => {
        component['deleteSchedule'](schedule);

        expect(apiService.deleteSchedule).toHaveBeenCalledWith('schedule-1');
        expect(component.schedules().length).toBe(0);
    });

    it('shows a utc clock display', () => {
        expect(component.utcClockDisplay()).toMatch(/^\d{2}:\d{2}:\d{2}$/);
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

        component.form.controls.type.setValue('recurring');
        fixture.detectChanges();
        text = fixture.nativeElement.textContent;
        expect(text).toContain('Horário UTC');
    });

    it('shows validation feedback when recurring schedule is missing time', () => {
        component.form.setValue({
            target_type: 'instance',
            instance: instances[0],
            instance_id: 'instance-1',
            group: null,
            group_id: '',
            type: 'recurring',
            action: 'start',
            run_at_utc: null,
            run_time_utc: null,
            days_of_week: [0],
            time_utc: null,
            enabled: true
        });

        component.save();

        expect(component.feedback()).toBe('Informe o horário UTC do agendamento recorrente.');
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
            time_utc: null,
            enabled: true
        });

        component.save();

        expect(component.feedback()).toBe('Selecione um grupo cadastrado.');
    });
});
