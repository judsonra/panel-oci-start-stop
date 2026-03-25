import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { ConfirmationService } from 'primeng/api';
import { ApiService } from '@/app/core/api.service';
import { InstanceModel, ScheduleModel } from '@/app/core/models';
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

    const schedule: ScheduleModel = {
        id: 'schedule-1',
        instance_id: 'instance-1',
        instance_name: 'VM Principal',
        type: 'recurring',
        action: 'restart',
        days_of_week: [0, 1, 2],
        time_utc: '14:30',
        enabled: true
    };

    beforeEach(async () => {
        apiService = jasmine.createSpyObj<ApiService>('ApiService', ['listSchedules', 'listInstances', 'createSchedule', 'updateSchedule', 'deleteSchedule']);
        apiService.listSchedules.and.returnValue(of([schedule]));
        apiService.listInstances.and.returnValue(of(instances));
        apiService.createSchedule.and.returnValue(of({ ...schedule, id: 'schedule-2', type: 'one_time', action: 'start', run_at_utc: '2026-03-15T00:00:00.000Z', days_of_week: null, time_utc: null }));
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

    it('creates a one-time schedule with UTC start-of-day date and returns to list tab', () => {
        component.activeTab.set(1);
        component.form.setValue({
            instance: instances[0],
            instance_id: 'instance-1',
            type: 'one_time',
            action: 'start',
            run_at_utc: new Date('2026-03-15T13:00:00'),
            days_of_week: [],
            time_utc: null,
            enabled: true
        });

        component.save();

        expect(apiService.createSchedule).toHaveBeenCalledWith({
            instance_id: 'instance-1',
            type: 'one_time',
            action: 'start',
            enabled: true,
            run_at_utc: '2026-03-15T00:00:00.000Z',
            days_of_week: null,
            time_utc: null
        });
        expect(component.activeTab()).toBe(0);
    });

    it('creates a recurring schedule with selected weekdays and 24h time', () => {
        const time = new Date();
        time.setHours(21, 45, 0, 0);

        component.form.setValue({
            instance: instances[1],
            instance_id: 'instance-2',
            type: 'recurring',
            action: 'restart',
            run_at_utc: null,
            days_of_week: [6, 0, 2],
            time_utc: time,
            enabled: true
        });

        component.save();

        expect(apiService.createSchedule).toHaveBeenCalledWith({
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
            instance_id: 'instance-1',
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

    it('renders the tabs and form labels in the template', () => {
        let text = fixture.nativeElement.textContent;
        expect(text).toContain('Agendamentos');
        expect(text).toContain('Novo agendamento');

        component.activeTab.set(1);
        component.form.controls.type.setValue('one_time');
        fixture.detectChanges();
        text = fixture.nativeElement.textContent;
        expect(text).toContain('Instância');
        expect(text).toContain('Data');
        expect(text).toContain('Hora UTC');

        component.form.controls.type.setValue('recurring');
        fixture.detectChanges();
        text = fixture.nativeElement.textContent;
        expect(text).toContain('Horário UTC');
    });

    it('shows validation feedback when recurring schedule is missing time', () => {
        component.form.setValue({
            instance: instances[0],
            instance_id: 'instance-1',
            type: 'recurring',
            action: 'start',
            run_at_utc: null,
            days_of_week: [0],
            time_utc: null,
            enabled: true
        });

        component.save();

        expect(component.feedback()).toBe('Informe o horário UTC do agendamento recorrente.');
        expect(apiService.createSchedule).not.toHaveBeenCalled();
    });

    it('surfaces save errors from the api', () => {
        apiService.createSchedule.and.returnValue(throwError(() => ({ error: { detail: 'Erro ao salvar' } })));
        component.form.setValue({
            instance: instances[0],
            instance_id: 'instance-1',
            type: 'one_time',
            action: 'start',
            run_at_utc: new Date('2026-03-15T13:00:00'),
            days_of_week: [],
            time_utc: null,
            enabled: true
        });

        component.save();

        expect(component.feedback()).toBe('Erro ao salvar');
    });

    it('shows validation feedback when no instance is selected', () => {
        component.form.setValue({
            instance: null,
            instance_id: '',
            type: 'one_time',
            action: 'start',
            run_at_utc: new Date('2026-03-15T13:00:00'),
            days_of_week: [],
            time_utc: null,
            enabled: true
        });

        component.save();

        expect(component.feedback()).toBe('Selecione uma instância cadastrada.');
        expect(apiService.createSchedule).not.toHaveBeenCalled();
    });
});
