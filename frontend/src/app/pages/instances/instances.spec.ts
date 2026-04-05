import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Observable, Subject, of, throwError } from 'rxjs';
import { ApiService } from '@/app/core/api.service';
import { InstanceImportPreviewModel } from '@/app/core/models';
import { InstancesPage } from './instances';

describe('InstancesPage', () => {
    let fixture: ComponentFixture<InstancesPage>;
    let component: InstancesPage;
    let apiService: jasmine.SpyObj<ApiService>;
    let clipboardWriteText: jasmine.Spy;

    const listedInstances = [
        {
            id: 'instance-1',
            name: 'Teste',
            ocid: 'ocid1.instance.oc1..example',
            compartment_id: 'compartment-1',
            enabled: true,
            vcpu: 2,
            memory_gbs: 16,
            public_ip: '129.10.10.10',
            private_ip: '10.0.0.10',
            created_at: '2026-03-12T00:00:00Z',
            updated_at: '2026-03-12T00:00:00Z'
        }
    ];

    const importPreview: InstanceImportPreviewModel = {
        name: 'Instance A1',
        ocid: 'ocid1.instance.oc1.sa-saopaulo-1.autoa1',
        compartment_ocid: 'ocid1.compartment.oc1..aaaa',
        compartment_name: 'Compartment A',
        vcpu: 2,
        memory_gbs: 12,
        vnic_id: 'ocid1.vnic.oc1..aaaavnic',
        public_ip: '129.1.1.1',
        private_ip: '10.0.0.10',
        oci_created_at: '2026-03-20T10:00:00Z',
        already_registered: false
    };

    beforeEach(async () => {
        apiService = jasmine.createSpyObj<ApiService>('ApiService', [
            'listInstances',
            'getInstanceImportPreview',
            'importInstance',
            'updateInstance',
            'startInstance',
            'stopInstance',
            'getInstanceStatus',
            'startImportAllCompartmentsInstancesJob',
            'getImportAllCompartmentsInstancesJob'
        ]);
        apiService.listInstances.and.returnValue(of(listedInstances));
        apiService.getInstanceImportPreview.and.returnValue(of(importPreview));
        apiService.importInstance.and.returnValue(
            of({
                id: 'instance-2',
                name: 'Instance A1',
                ocid: 'ocid1.instance.oc1.sa-saopaulo-1.autoa1',
                compartment_id: 'compartment-1',
                description: 'Importada',
                enabled: true,
                vcpu: 2,
                memory_gbs: 12,
                public_ip: '129.1.1.1',
                private_ip: '10.0.0.10',
                created_at: '2026-03-20T10:00:00Z',
                updated_at: '2026-03-20T10:00:00Z'
            })
        );
        apiService.updateInstance.and.returnValue(
            of({
                ...listedInstances[0],
                enabled: false
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
        apiService.startImportAllCompartmentsInstancesJob.and.returnValue(
            of({
                job_id: 'job-1',
                status: 'pending',
                started_at: '2026-04-05T18:00:00Z'
            })
        );
        apiService.getImportAllCompartmentsInstancesJob.and.returnValue(
            of({
                job_id: 'job-1',
                status: 'completed',
                started_at: '2026-04-05T18:00:00Z',
                finished_at: '2026-04-05T18:01:00Z',
                total_compartments: 2,
                processed_compartments: 2,
                total_instances: 3,
                processed_instances: 3,
                created: 1,
                updated: 1,
                unchanged: 1,
                failed: 0,
                current_compartment_name: null,
                current_instance_name: null,
                result: {
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
                        }
                    ]
                }
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

    it('starts with the registered instances tab selected and loads instances without calling status lookup', () => {
        expect(component.activeTab()).toBe(0);
        expect(apiService.listInstances).toHaveBeenCalled();
        expect(apiService.getInstanceStatus).not.toHaveBeenCalled();
    });

    it('renders the import tab label', () => {
        expect(fixture.nativeElement.textContent).toContain('Importação de instâncias');
    });

    it('keeps the import form invalid when ocid is empty', () => {
        component.form.setValue({ ocid: '', description: '', enabled: true });
        expect(component.form.invalid).toBeTrue();
        expect(component.canSaveImportedInstance()).toBeFalse();
    });

    it('does not query OCI automatically while the user types the ocid', () => {
        component.form.controls.ocid.setValue(importPreview.ocid);

        expect(apiService.getInstanceImportPreview).not.toHaveBeenCalled();
        expect(component.importPreview()).toBeNull();
    });

    it('loads a preview from OCI only when clicking search and shows read-only data', () => {
        component.form.controls.ocid.setValue(importPreview.ocid);

        component.lookupInstancePreview();
        fixture.detectChanges();

        expect(apiService.getInstanceImportPreview).toHaveBeenCalledWith(importPreview.ocid);
        expect(component.importPreview()).toEqual(importPreview);
        expect(fixture.nativeElement.textContent).toContain('Compartment A');
        expect(fixture.nativeElement.textContent).toContain('129.1.1.1');
    });

    it('blocks save when the preview says the instance is already registered', () => {
        apiService.getInstanceImportPreview.and.returnValue(
            of({
                ...importPreview,
                already_registered: true
            })
        );
        component.form.controls.ocid.setValue(importPreview.ocid);

        component.lookupInstancePreview();
        fixture.detectChanges();

        expect(component.canSaveImportedInstance()).toBeFalse();
        expect(fixture.nativeElement.textContent).toContain('já está cadastrada no banco local');
    });

    it('clears the preview when the ocid changes after a successful lookup', () => {
        component.form.controls.ocid.setValue(importPreview.ocid);
        component.lookupInstancePreview();

        component.form.controls.ocid.setValue('ocid1.instance.oc1.sa-saopaulo-1.other');

        expect(component.importPreview()).toBeNull();
    });

    it('imports a new instance with ocid, description and enabled only', () => {
        component.form.setValue({
            ocid: importPreview.ocid,
            description: 'Importada',
            enabled: false
        });
        component.importPreview.set(importPreview);
        component.activeTab.set(1);

        component.save();

        expect(apiService.importInstance).toHaveBeenCalledWith({
            ocid: importPreview.ocid,
            description: 'Importada',
            enabled: false
        });
        expect(component.activeTab()).toBe(0);
        expect(component.actionFeedback()).toBe('Instância importada com sucesso.');
    });

    it('shows lookup errors when OCI preview fails', () => {
        apiService.getInstanceImportPreview.and.returnValue(throwError(() => ({ error: { detail: 'instance_not_found' } })));
        component.form.controls.ocid.setValue(importPreview.ocid);

        component.lookupInstancePreview();

        expect(component.error()).toBe('instance_not_found');
        expect(component.importPreview()).toBeNull();
    });

    it('shows a discrete loading state on the first load and keeps the refresh button gray without spinner', async () => {
        const instancesSubject = new Subject<any[]>();
        apiService.listInstances.and.returnValue(instancesSubject.asObservable());

        const pendingFixture = TestBed.createComponent(InstancesPage);
        const pendingComponent = pendingFixture.componentInstance;
        pendingFixture.detectChanges();

        const refreshButton = pendingFixture.nativeElement.querySelector('.instances-refresh-button') as HTMLButtonElement;
        const loadingHint = pendingFixture.nativeElement.querySelector('.instances-loading-hint') as HTMLElement;
        const tableShell = pendingFixture.nativeElement.querySelector('.table-shell') as HTMLElement;

        expect(pendingComponent.showInitialLoadingHint()).toBeTrue();
        expect(pendingComponent.refreshButtonDisabled()).toBeTrue();
        expect(pendingComponent.refreshButtonLoading()).toBeFalse();
        expect(pendingComponent.refreshButtonSeverity()).toBe('secondary');
        expect(refreshButton.disabled).toBeTrue();
        expect(refreshButton.className).toContain('p-button-secondary');
        expect(refreshButton.className).not.toContain('p-button-loading');
        expect(loadingHint.textContent).toContain('Carregando instâncias');
        expect(pendingFixture.nativeElement.textContent.match(/Carregando instâncias\.\.\./g)?.length ?? 0).toBe(1);
        expect(tableShell.textContent).not.toContain('Carregando instâncias...');

        instancesSubject.next(listedInstances);
        instancesSubject.complete();
        pendingFixture.detectChanges();
        await pendingFixture.whenStable();

        expect(pendingComponent.showInitialLoadingHint()).toBeFalse();
        expect(pendingComponent.refreshButtonDisabled()).toBeFalse();
        expect(pendingComponent.refreshButtonLoading()).toBeFalse();
        expect(pendingComponent.refreshButtonSeverity()).toBe('success');
    });

    it('shows the empty table message only after the initial load finishes with no instances', async () => {
        const instancesSubject = new Subject<any[]>();
        apiService.listInstances.and.returnValue(instancesSubject.asObservable());

        const pendingFixture = TestBed.createComponent(InstancesPage);
        const pendingComponent = pendingFixture.componentInstance;
        pendingFixture.detectChanges();

        expect(pendingComponent.showInitialLoadingHint()).toBeTrue();
        expect(pendingFixture.nativeElement.textContent).not.toContain('Nenhuma instância cadastrada.');

        instancesSubject.next([]);
        instancesSubject.complete();
        pendingFixture.detectChanges();
        await pendingFixture.whenStable();

        expect(pendingComponent.showInitialLoadingHint()).toBeFalse();
        expect(pendingFixture.nativeElement.textContent).toContain('Nenhuma instância cadastrada.');
    });

    it('filters instances locally by name, ocid and ips', () => {
        component.instances.set([
            listedInstances[0],
            {
                id: 'instance-2',
                name: 'Banco',
                ocid: 'ocid1.instance.oc1..database',
                compartment_id: 'compartment-1',
                enabled: true,
                public_ip: null,
                private_ip: '10.0.0.20',
                created_at: '2026-03-12T00:00:00Z',
                updated_at: '2026-03-12T00:00:00Z'
            }
        ]);

        component.instanceSearchTerm.set('banco');
        expect(component.filteredInstances().length).toBe(1);
        expect(component.filteredInstances()[0].id).toBe('instance-2');

        component.instanceSearchTerm.set('129.10');
        expect(component.filteredInstances()[0].id).toBe('instance-1');
    });

    it('opens the confirmation dialog before refreshing statuses', () => {
        component.openRefreshConfirmation();

        expect(component.refreshConfirmationVisible()).toBeTrue();
        expect(apiService.getInstanceStatus).not.toHaveBeenCalled();
    });

    it('uses the spinner on the refresh button only during manual refresh', () => {
        component.refreshingStatuses.set(true);
        fixture.detectChanges();

        const refreshButton = fixture.nativeElement.querySelector('.instances-refresh-button') as HTMLButtonElement;

        expect(component.refreshButtonLoading()).toBeTrue();
        expect(component.refreshButtonDisabled()).toBeTrue();
        expect(refreshButton.className).toContain('p-button-loading');
    });

    it('refreshes only enabled instances sequentially and shows progress summary', async () => {
        component.instances.set([
            listedInstances[0],
            {
                id: 'instance-2',
                name: 'Desabilitada',
                ocid: 'ocid1.instance.oc1..disabled',
                compartment_id: 'compartment-1',
                enabled: false,
                created_at: '2026-03-12T00:00:00Z',
                updated_at: '2026-03-12T00:00:00Z'
            }
        ]);

        await component.confirmRefreshStatuses();

        expect(apiService.getInstanceStatus).toHaveBeenCalledTimes(1);
        expect(component.refreshProgressCount()).toBe(1);
        expect(component.actionFeedback()).toContain('Consulta concluída com sucesso');
    });

    it('shows feedback when there are no enabled instances to refresh', async () => {
        component.instances.set([
            {
                id: 'instance-2',
                name: 'Desabilitada',
                ocid: 'ocid1.instance.oc1..disabled',
                compartment_id: 'compartment-1',
                enabled: false,
                created_at: '2026-03-12T00:00:00Z',
                updated_at: '2026-03-12T00:00:00Z'
            }
        ]);

        await component.confirmRefreshStatuses();

        expect(apiService.getInstanceStatus).not.toHaveBeenCalled();
        expect(component.actionFeedback()).toBe('Não há instâncias habilitadas para consultar o status.');
    });

    it('runs automatic registration as a job and stores the summary result', () => {
        component.openAutomaticRegistrationConfirmation();
        component.autoRegisterConfirmationText.set('Estou ciente');

        component.confirmAutomaticRegistration();

        expect(apiService.startImportAllCompartmentsInstancesJob).toHaveBeenCalled();
        expect(apiService.getImportAllCompartmentsInstancesJob).toHaveBeenCalledWith('job-1');
        expect(component.autoRegisterProgressVisible()).toBeTrue();
        expect(component.autoRegisterCompleted()).toBeTrue();
        expect(component.autoRegisterResult()?.created).toBe(1);
    });

    it('shows the new confirmation warning before starting automatic registration', () => {
        component.openAutomaticRegistrationConfirmation();
        fixture.detectChanges();

        expect(fixture.nativeElement.textContent).toContain('Esta ação não pode ser cancelada, é demorada, e pode gerar lentidão. Deseja prosseguir.');
    });

    it('updates progress details while the automatic registration job is running', () => {
        apiService.getImportAllCompartmentsInstancesJob.and.returnValue(
            of({
                job_id: 'job-1',
                status: 'running',
                started_at: '2026-04-05T18:00:00Z',
                total_compartments: 2,
                processed_compartments: 1,
                total_instances: 4,
                processed_instances: 2,
                created: 1,
                updated: 0,
                unchanged: 1,
                failed: 0,
                current_compartment_name: 'Compartment A',
                current_instance_name: 'Instance A1'
            })
        );
        component.openAutomaticRegistrationConfirmation();
        component.autoRegisterConfirmationText.set('Estou ciente');

        component.confirmAutomaticRegistration();

        expect(component.autoRegisterCompleted()).toBeFalse();
        expect(component.autoRegisterCurrentCompartmentName()).toBe('Compartment A');
        expect(component.autoRegisterCurrentInstanceName()).toBe('Instance A1');
        expect(component.autoRegisterProgressPercent()).toBe(50);
        expect(component.autoRegisterProgressMessage()).toContain('2 / 4');
    });

    it('refreshes the status of a single row and updates the status column locally', () => {
        component.instances.set([
            {
                ...listedInstances[0],
                last_known_state: 'STOPPED'
            }
        ]);

        component.refreshInstanceStatus(component.instances()[0]);

        expect(apiService.getInstanceStatus).toHaveBeenCalledWith('instance-1');
        expect(component.instances()[0].last_known_state).toBe('RUNNING');
    });

    it('calls the api when starting and stopping an instance', () => {
        component.start('instance-1');
        component.stop('instance-1');

        expect(apiService.startInstance).toHaveBeenCalledWith('instance-1');
        expect(apiService.stopInstance).toHaveBeenCalledWith('instance-1');
    });
});
