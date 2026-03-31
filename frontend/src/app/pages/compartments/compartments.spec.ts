import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { ApiService } from '@/app/core/api.service';
import { CompartmentsPage } from './compartments';

describe('CompartmentsPage', () => {
    let fixture: ComponentFixture<CompartmentsPage>;
    let component: CompartmentsPage;
    let apiService: jasmine.SpyObj<ApiService>;
    let clipboardWriteText: jasmine.Spy;

    const persistedCompartments = [
        {
            id: 'compartment-1',
            name: 'Aplicações',
            ocid: 'ocid1.compartment.oc1..aaaaaaaaaaaa',
            active: true,
            created_at: '2026-03-30T00:00:00Z',
            updated_at: '2026-03-30T00:00:00Z'
        },
        {
            id: 'compartment-2',
            name: 'Legado',
            ocid: 'ocid1.compartment.oc1..bbbbbbbbbbbb',
            active: false,
            created_at: '2026-03-30T00:00:00Z',
            updated_at: '2026-03-30T00:00:00Z'
        }
    ];

    beforeEach(async () => {
        apiService = jasmine.createSpyObj<ApiService>('ApiService', ['listCompartments', 'listAndUpdateCompartments']);
        apiService.listCompartments.and.returnValue(of(persistedCompartments));
        apiService.listAndUpdateCompartments.and.returnValue(of(persistedCompartments));
        clipboardWriteText = jasmine.createSpy('writeText').and.resolveTo();
        Object.defineProperty(navigator, 'clipboard', {
            configurable: true,
            value: {
                writeText: clipboardWriteText
            }
        });

        await TestBed.configureTestingModule({
            imports: [CompartmentsPage],
            providers: [{ provide: ApiService, useValue: apiService }]
        }).compileComponents();

        fixture = TestBed.createComponent(CompartmentsPage);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('loads persisted compartments on init', () => {
        expect(apiService.listCompartments).toHaveBeenCalled();
        expect(component.compartments().length).toBe(2);
    });

    it('refreshes compartments from the sync endpoint', () => {
        const refreshedCompartments = [
            {
                id: 'compartment-1',
                name: 'Aplicações',
                ocid: 'ocid1.compartment.oc1..aaaaaaaaaaaa',
                active: true,
                created_at: '2026-03-30T00:00:00Z',
                updated_at: '2026-03-30T00:00:00Z'
            }
        ];
        apiService.listAndUpdateCompartments.and.returnValue(of(refreshedCompartments));

        component.refreshCompartments();

        expect(apiService.listAndUpdateCompartments).toHaveBeenCalled();
        expect(component.compartments()).toEqual(refreshedCompartments);
        expect(component.feedback()).toBe('Compartimentos atualizados com sucesso.');
    });

    it('filters active and inactive compartments locally', () => {
        component.setStatusFilter('active');
        expect(component.filteredCompartments().length).toBe(1);
        expect(component.filteredCompartments()[0].active).toBeTrue();

        component.setStatusFilter('inactive');
        expect(component.filteredCompartments().length).toBe(1);
        expect(component.filteredCompartments()[0].active).toBeFalse();

        component.setStatusFilter('all');
        expect(component.filteredCompartments().length).toBe(2);
    });

    it('formats and copies the full ocid', async () => {
        expect(component.formatOcid('ocid1.compartment.oc1..aaaaaaaaaaaa')).toBe('...aaaaaaaaaa');

        await component.copyOcid('ocid1.compartment.oc1..aaaaaaaaaaaa');

        expect(clipboardWriteText).toHaveBeenCalledWith('ocid1.compartment.oc1..aaaaaaaaaaaa');
        expect(component.feedback()).toBe('OCID copiado com sucesso.');
    });

    it('shows an error when the initial load fails', () => {
        apiService.listCompartments.and.returnValue(throwError(() => new Error('boom')));

        component.loadCompartments();

        expect(component.error()).toBe('Não foi possível carregar os compartimentos.');
    });

    it('shows an error when the refresh fails', () => {
        apiService.listAndUpdateCompartments.and.returnValue(throwError(() => ({ error: { detail: 'Falha OCI' } })));

        component.refreshCompartments();

        expect(component.feedback()).toBe('Falha OCI');
        expect(component.feedbackSeverity()).toBe('error');
    });

    it('renders the empty state message when there are no compartments', () => {
        component.compartments.set([]);
        fixture.detectChanges();

        expect(fixture.nativeElement.textContent).toContain('Nenhum compartimento encontrado.');
    });
});
