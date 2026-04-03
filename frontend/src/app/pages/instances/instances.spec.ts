import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Observable, of, throwError } from 'rxjs';
import { ApiService } from '@/app/core/api.service';
import { InstancesPage } from './instances';

describe('InstancesPage', () => {
    let fixture: ComponentFixture<InstancesPage>;
    let component: InstancesPage;
    let apiService: jasmine.SpyObj<ApiService>;
    let clipboardWriteText: jasmine.Spy;

    beforeEach(async () => {
        apiService = jasmine.createSpyObj<ApiService>('ApiService', [
            'listInstances',
            'createInstance',
            'updateInstance',
            'startInstance',
            'stopInstance',
            'getInstanceStatus',
            'importAllCompartmentsInstances'
        ]);
        apiService.listInstances.and.returnValue(
            of([
                {
                    id: 'instance-1',
                    name: 'Teste',
                    ocid: 'ocid1.instance.oc1..example',
                    enabled: true,
                    vcpu: 2,
                    memory_gbs: 16,
                    public_ip: '129.10.10.10',
                    private_ip: '10.0.0.10',
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
        apiService.importAllCompartmentsInstances.and.returnValue(
            of({
                total_compartments: 2,
                processed_compartments: 2,
                total_instances: 3,
                created: 1,
                updated: 1,
                unchanged: 1,
                failed: 0,
                compartments: [
                    {
                        compartment_ocid: 'ocid1.compartment.oc1..aaaa',
                        compartment_name: 'Compartment A',
                        total_instances: 2,
                        created: 1,
                        updated: 1,
                        unchanged: 0,
                        failed: 0,
                        instances: []
                    },
                    {
                        compartment_ocid: 'ocid1.compartment.oc1..bbbb',
                        compartment_name: 'Compartment B',
                        total_instances: 1,
                        created: 0,
                        updated: 0,
                        unchanged: 1,
                        failed: 0,
                        instances: []
                    }
                ]
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

    it('requests cancellation and closes the progress dialog immediately', () => {
        component.refreshProgressVisible.set(true);
        component.refreshingStatuses.set(true);

        component.requestRefreshCancellation();

        expect(component.refreshCancellationRequested()).toBeTrue();
        expect(component.refreshProgressVisible()).toBeFalse();
        expect(component.refreshProgressMessage()).toContain('Cancelamento solicitado');
    });

    it('stops after the current status request finishes when cancellation is requested', async () => {
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

        let releaseFirstRequest: (() => void) | null = null;
        apiService.getInstanceStatus.and.callFake(
            () =>
                new Observable((subscriber) => {
                    releaseFirstRequest = () => {
                        subscriber.next({
                            id: 'exec-status-1',
                            instance_id: 'instance-1',
                            instance_state: 'RUNNING',
                            action: 'status',
                            source: 'manual',
                            status: 'success',
                            started_at: '2026-03-12T00:00:00Z'
                        });
                        subscriber.complete();
                    };
                })
        );

        const refreshPromise = component.confirmRefreshStatuses();
        component.requestRefreshCancellation();
        releaseFirstRequest?.();
        await refreshPromise;

        expect(apiService.getInstanceStatus).toHaveBeenCalledTimes(1);
        expect(component.refreshingStatuses()).toBeFalse();
        expect(component.actionFeedback()).toBe('Atualização cancelada após 1 instância(s) processada(s).');
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

    it('opens the automatic registration confirmation dialog', () => {
        component.openAutomaticRegistrationConfirmation();

        expect(component.autoRegisterConfirmationVisible()).toBeTrue();
        expect(component.autoRegisterCanConfirm()).toBeFalse();
    });

    it('enables automatic registration only when the user types the confirmation text', () => {
        component.openAutomaticRegistrationConfirmation();
        component.autoRegisterConfirmationText.set('Estou ciente');

        expect(component.autoRegisterCanConfirm()).toBeTrue();
    });

    it('runs automatic registration and stores the summary result', () => {
        component.openAutomaticRegistrationConfirmation();
        component.autoRegisterConfirmationText.set('Estou ciente');

        component.confirmAutomaticRegistration();

        expect(apiService.importAllCompartmentsInstances).toHaveBeenCalled();
        expect(component.autoRegisterProgressVisible()).toBeTrue();
        expect(component.autoRegisterCompleted()).toBeTrue();
        expect(component.autoRegisterResult()?.created).toBe(1);
        expect(component.actionFeedback()).toContain('Registro automático concluído');
    });

    it('shows an error when automatic registration fails', () => {
        apiService.importAllCompartmentsInstances.and.returnValue(throwError(() => ({ error: { detail: 'Falha OCI' } })));
        component.openAutomaticRegistrationConfirmation();
        component.autoRegisterConfirmationText.set('Estou ciente');

        component.confirmAutomaticRegistration();

        expect(component.autoRegisterCompleted()).toBeTrue();
        expect(component.actionFeedback()).toBe('Falha OCI');
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
});
