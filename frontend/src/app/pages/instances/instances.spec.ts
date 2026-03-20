import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { ApiService } from '@/app/core/api.service';
import { InstancesPage } from './instances';

describe('InstancesPage', () => {
    let fixture: ComponentFixture<InstancesPage>;
    let component: InstancesPage;
    let apiService: jasmine.SpyObj<ApiService>;
    let clipboardWriteText: jasmine.Spy;

    beforeEach(async () => {
        apiService = jasmine.createSpyObj<ApiService>('ApiService', ['listInstances', 'createInstance', 'updateInstance', 'startInstance', 'stopInstance', 'getInstanceStatus']);
        apiService.listInstances.and.returnValue(
            of([
                {
                    id: 'instance-1',
                    name: 'Teste',
                    ocid: 'ocid1.instance.oc1..example',
                    enabled: true,
                    created_at: '2026-03-12T00:00:00Z',
                    updated_at: '2026-03-12T00:00:00Z'
                }
            ])
        );
        apiService.createInstance.and.returnValue(
            of({
                id: 'instance-1',
                name: 'Teste',
                ocid: 'ocid1.instance.oc1..example',
                enabled: true,
                created_at: '2026-03-12T00:00:00Z',
                updated_at: '2026-03-12T00:00:00Z'
            })
        );
        apiService.updateInstance.and.returnValue(
            of({
                id: 'instance-1',
                name: 'Teste',
                ocid: 'ocid1.instance.oc1..example',
                enabled: false,
                created_at: '2026-03-12T00:00:00Z',
                updated_at: '2026-03-12T00:00:00Z'
            })
        );
        apiService.startInstance.and.returnValue(
            of({
                id: 'exec-1',
                instance_id: 'instance-1',
                action: 'start',
                source: 'manual',
                status: 'success',
                started_at: '2026-03-12T00:00:00Z'
            })
        );
        apiService.stopInstance.and.returnValue(
            of({
                id: 'exec-2',
                instance_id: 'instance-1',
                action: 'stop',
                source: 'manual',
                status: 'success',
                started_at: '2026-03-12T00:00:00Z'
            })
        );
        apiService.getInstanceStatus.and.returnValue(
            of({
                id: 'exec-status-1',
                instance_id: 'instance-1',
                instance_state: 'RUNNING',
                action: 'status',
                source: 'manual',
                status: 'success',
                started_at: '2026-03-12T00:00:00Z'
            })
        );
        clipboardWriteText = jasmine.createSpy('writeText').and.resolveTo();
        Object.defineProperty(navigator, 'clipboard', {
            configurable: true,
            value: {
                writeText: clipboardWriteText
            }
        });

        await TestBed.configureTestingModule({
            imports: [InstancesPage],
            providers: [{ provide: ApiService, useValue: apiService }]
        }).compileComponents();

        fixture = TestBed.createComponent(InstancesPage);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('starts with the registered instances tab selected', () => {
        expect(component.activeTab()).toBe(0);
    });

    it('keeps the form invalid when required fields are empty', () => {
        component.form.setValue({ name: '', ocid: '', description: '', enabled: true });
        expect(component.form.invalid).toBeTrue();
    });

    it('saves a valid payload and returns to the first tab', () => {
        component.activeTab.set(1);
        component.form.setValue({
            name: 'App Financeiro',
            ocid: 'ocid1.instance.oc1.sa-saopaulo-1.example',
            description: 'Descrição',
            enabled: true
        });

        component.save();

        expect(apiService.createInstance).toHaveBeenCalledWith({
            name: 'App Financeiro',
            ocid: 'ocid1.instance.oc1.sa-saopaulo-1.example',
            description: 'Descrição',
            enabled: true
        });
        expect(component.activeTab()).toBe(0);
    });

    it('surfaces a loading error when listing instances fails', () => {
        apiService.listInstances.and.returnValue(throwError(() => new Error('boom')));
        component.loadInstances();
        expect(component.error()).toContain('Não foi possível carregar as instâncias');
    });

    it('opens the confirmation dialog before refreshing statuses', () => {
        component.openRefreshConfirmation();

        expect(component.refreshConfirmationVisible()).toBeTrue();
        expect(apiService.getInstanceStatus).not.toHaveBeenCalled();
    });

    it('cancels status refresh when the user aborts the confirmation', () => {
        component.openRefreshConfirmation();
        component.cancelRefreshConfirmation();

        expect(component.refreshConfirmationVisible()).toBeFalse();
        expect(apiService.getInstanceStatus).not.toHaveBeenCalled();
    });

    it('refreshes only enabled instances sequentially and shows progress summary', async () => {
        component.instances.set([
            component.instances()[0],
            {
                id: 'instance-2',
                name: 'Desabilitada',
                ocid: 'ocid1.instance.oc1..disabled',
                enabled: false,
                created_at: '2026-03-12T00:00:00Z',
                updated_at: '2026-03-12T00:00:00Z'
            }
        ]);

        await component.confirmRefreshStatuses();

        expect(apiService.getInstanceStatus).toHaveBeenCalledTimes(1);
        expect(apiService.getInstanceStatus).toHaveBeenCalledWith('instance-1');
        expect(component.refreshProgressCount()).toBe(1);
        expect(component.refreshProgressTotal()).toBe(1);
        expect(component.refreshProgressVisible()).toBeFalse();
        expect(component.actionFeedback()).toContain('Consulta concluída com sucesso');
        expect(component.actionFeedbackSeverity()).toBe('success');
    });

    it('continues the batch when one status refresh fails and reports partial failure', async () => {
        component.instances.set([
            component.instances()[0],
            {
                id: 'instance-2',
                name: 'Segundo Nó',
                ocid: 'ocid1.instance.oc1..second',
                enabled: true,
                created_at: '2026-03-12T00:00:00Z',
                updated_at: '2026-03-12T00:00:00Z'
            }
        ]);
        apiService.getInstanceStatus.and.returnValues(
            throwError(() => ({ error: { detail: 'OCI indisponível' } })),
            of({
                id: 'exec-status-2',
                instance_id: 'instance-2',
                instance_state: 'RUNNING',
                action: 'status',
                source: 'manual',
                status: 'success',
                started_at: '2026-03-12T00:00:00Z'
            })
        );

        await component.confirmRefreshStatuses();

        expect(apiService.getInstanceStatus).toHaveBeenCalledTimes(2);
        expect(component.refreshProgressCount()).toBe(2);
        expect(component.actionFeedback()).toBe('Consulta concluída: 1 com sucesso e 1 com falha.');
        expect(component.actionFeedbackSeverity()).toBe('error');
    });

    it('shows feedback when there are no enabled instances to refresh', async () => {
        component.instances.set([
            {
                id: 'instance-2',
                name: 'Desabilitada',
                ocid: 'ocid1.instance.oc1..disabled',
                enabled: false,
                created_at: '2026-03-12T00:00:00Z',
                updated_at: '2026-03-12T00:00:00Z'
            }
        ]);

        await component.confirmRefreshStatuses();

        expect(apiService.getInstanceStatus).not.toHaveBeenCalled();
        expect(component.actionFeedback()).toBe('Não há instâncias habilitadas para consultar o status.');
        expect(component.actionFeedbackSeverity()).toBe('error');
    });

    it('refreshes the status of a single row and updates the status column locally', () => {
        component.instances.set([
            {
                ...component.instances()[0],
                last_known_state: 'STOPPED'
            }
        ]);

        component.refreshInstanceStatus(component.instances()[0]);

        expect(apiService.getInstanceStatus).toHaveBeenCalledWith('instance-1');
        expect(component.instances()[0].last_known_state).toBe('RUNNING');
        expect(component.actionFeedback()).toBe('Status da instância Teste atualizado com sucesso.');
        expect(component.actionFeedbackSeverity()).toBe('success');
        expect(component.isRefreshingRow('instance-1')).toBeFalse();
    });

    it('keeps the previous row status when the single-row refresh fails', () => {
        component.instances.set([
            {
                ...component.instances()[0],
                last_known_state: 'STOPPED'
            }
        ]);
        apiService.getInstanceStatus.and.returnValue(throwError(() => ({ error: { detail: 'Falha OCI' } })));

        component.refreshInstanceStatus(component.instances()[0]);

        expect(component.instances()[0].last_known_state).toBe('STOPPED');
        expect(component.actionFeedback()).toBe('Falha OCI');
        expect(component.actionFeedbackSeverity()).toBe('error');
        expect(component.isRefreshingRow('instance-1')).toBeFalse();
    });

    it('calls the api when starting and stopping an instance', () => {
        component.start('instance-1');
        component.stop('instance-1');
        expect(apiService.startInstance).toHaveBeenCalledWith('instance-1');
        expect(apiService.stopInstance).toHaveBeenCalledWith('instance-1');
    });

    it('updates the instance enabled state when toggled off', () => {
        component.toggleEnabled(component.instances()[0], false);

        expect(apiService.updateInstance).toHaveBeenCalledWith('instance-1', { enabled: false });
        expect(component.instances()[0].enabled).toBeFalse();
        expect(component.actionFeedback()).toContain('desabilitada com sucesso');
    });

    it('reverts the instance enabled state when the toggle update fails', () => {
        apiService.updateInstance.and.returnValue(throwError(() => ({ error: { detail: 'Erro ao atualizar' } })));

        component.toggleEnabled(component.instances()[0], false);

        expect(component.instances()[0].enabled).toBeTrue();
        expect(component.actionFeedback()).toBe('Erro ao atualizar');
        expect(component.actionFeedbackSeverity()).toBe('error');
    });

    it('formats long ocids with ellipsis and the last ten characters', () => {
        expect(component.formatOcid('ocid1.instance.oc1.sa-saopaulo-1.abcdefghij')).toBe('...abcdefghij');
    });

    it('does not truncate short ocids', () => {
        expect(component.formatOcid('1234567890')).toBe('1234567890');
    });

    it('copies the full ocid and shows success feedback', async () => {
        await component.copyOcid('ocid1.instance.oc1.sa-saopaulo-1.fullvalue');

        expect(clipboardWriteText).toHaveBeenCalledWith('ocid1.instance.oc1.sa-saopaulo-1.fullvalue');
        expect(component.actionFeedback()).toBe('OCID copiado com sucesso.');
        expect(component.actionFeedbackSeverity()).toBe('success');
    });

    it('shows an error when clipboard copy fails', async () => {
        clipboardWriteText.and.rejectWith(new Error('clipboard error'));

        await component.copyOcid('ocid1.instance.oc1.sa-saopaulo-1.fullvalue');

        expect(component.actionFeedback()).toBe('Não foi possível copiar o OCID.');
        expect(component.actionFeedbackSeverity()).toBe('error');
    });

    it('shows success feedback after a stop command', () => {
        component.stop('instance-1');
        expect(component.actionFeedback()).toContain('desligamento');
        expect(component.actionFeedbackSeverity()).toBe('success');
    });

    it('shows error feedback when the backend rejects a stop command', () => {
        apiService.stopInstance.and.returnValue(throwError(() => ({ error: { detail: 'Erro OCI' } })));
        component.stop('instance-1');
        expect(component.actionFeedback()).toBe('Erro OCI');
        expect(component.actionFeedbackSeverity()).toBe('error');
    });
});
