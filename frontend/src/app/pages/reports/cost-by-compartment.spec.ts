import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { ApiService } from '@/app/core/api.service';
import { CostByCompartmentPage } from './cost-by-compartment';

describe('CostByCompartmentPage', () => {
    let fixture: ComponentFixture<CostByCompartmentPage>;
    let component: CostByCompartmentPage;
    let apiService: jasmine.SpyObj<ApiService>;

    const reportResponse = {
        year: 2026,
        month: 4,
        currency: 'USD',
        source: 'cache' as const,
        sync_status: 'ready',
        available: true,
        last_refreshed_at: '2026-04-05T12:00:00Z',
        total_amount: 127.5,
        daily_totals: [{ date: '2026-04-01', amount: 27.5 }],
        compartments: [
            {
                compartment_id: 'compartment-1',
                compartment_name: 'Aplicacoes',
                total_amount: 127.5,
                daily_costs: [{ date: '2026-04-01', amount: 27.5 }],
                resources: [
                    {
                        service: 'Compute',
                        sku_name: 'VM.Standard',
                        resource_id: 'resource-1',
                        resource_name: 'Instance A',
                        total_amount: 120.5
                    }
                ]
            }
        ],
        detailed_items: [
            {
                date: '2026-04-01',
                compartment_id: 'compartment-1',
                compartment_name: 'Aplicacoes',
                service: 'Compute',
                sku_name: 'VM.Standard',
                resource_id: 'resource-1',
                resource_name: 'Instance A',
                total_amount: 20.5
            },
            {
                date: '2026-04-01',
                compartment_id: 'compartment-1',
                compartment_name: 'Aplicacoes',
                service: 'Block Storage',
                sku_name: 'Volume',
                resource_id: 'resource-2',
                resource_name: 'Volume A',
                total_amount: 5
            },
            {
                date: '2026-04-01',
                compartment_id: 'compartment-1',
                compartment_name: 'Aplicacoes',
                service: 'Load Balancer',
                sku_name: 'LB',
                resource_id: 'resource-3',
                resource_name: 'ocid1.resource.oc1.sa-saopaulo-1.abcdefghijklmnopqrstuvxyz12345',
                total_amount: 2
            }
        ]
    };

    beforeEach(async () => {
        apiService = jasmine.createSpyObj<ApiService>('ApiService', [
            'getCostByCompartment',
            'refreshCostByCompartment',
            'getCostByCompartmentCsvUrl',
            'listInstances',
            'listGroups',
            'listSchedules',
            'listExecutions',
            'listCompartments',
            'getBackendHealth'
        ]);
        apiService.getCostByCompartment.and.returnValue(of(reportResponse));
        apiService.refreshCostByCompartment.and.returnValue(of({ ...reportResponse, source: 'oci' as const }));
        apiService.getCostByCompartmentCsvUrl.and.returnValue('http://localhost:8010/api/reports/cost-by-compartment.csv?year=2026&month=4');

        await TestBed.configureTestingModule({
            imports: [CostByCompartmentPage],
            providers: [{ provide: ApiService, useValue: apiService }]
        }).compileComponents();

        fixture = TestBed.createComponent(CostByCompartmentPage);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('loads the report on init using only reports methods', () => {
        expect(apiService.getCostByCompartment).toHaveBeenCalled();
        expect(component.report()).toEqual(reportResponse);
        expect(apiService.listInstances).not.toHaveBeenCalled();
        expect(apiService.listGroups).not.toHaveBeenCalled();
        expect(apiService.listSchedules).not.toHaveBeenCalled();
        expect(apiService.listExecutions).not.toHaveBeenCalled();
        expect(apiService.listCompartments).not.toHaveBeenCalled();
        expect(apiService.getBackendHealth).not.toHaveBeenCalled();
    });

    it('refreshes the report using the reports service only', () => {
        component.refreshReport();

        expect(apiService.refreshCostByCompartment).toHaveBeenCalledWith({ year: component.selectedYear(), month: component.selectedMonth() });
        expect(component.report()?.source).toBe('oci');
        expect(apiService.listInstances).not.toHaveBeenCalled();
        expect(apiService.listGroups).not.toHaveBeenCalled();
        expect(apiService.listSchedules).not.toHaveBeenCalled();
        expect(apiService.listExecutions).not.toHaveBeenCalled();
        expect(apiService.listCompartments).not.toHaveBeenCalled();
    });

    it('builds the export URL from the reports service helper', () => {
        expect(component.csvUrl()).toBe('http://localhost:8010/api/reports/cost-by-compartment.csv?year=2026&month=4');
        expect(apiService.getCostByCompartmentCsvUrl).toHaveBeenCalledWith(component.selectedYear(), component.selectedMonth());
    });

    it('uses a month picker period initialized with a valid month and year', () => {
        expect(component.selectedPeriodDate()).toEqual(jasmine.any(Date));
        expect(component.selectedMonth()).toBeGreaterThanOrEqual(1);
        expect(component.selectedMonth()).toBeLessThanOrEqual(12);
        expect(component.selectedYear()).toBeGreaterThanOrEqual(2020);
    });

    it('updates month and year when the selected period changes', () => {
        component.setSelectedPeriod(new Date(2026, 3, 1));

        expect(component.selectedMonth()).toBe(4);
        expect(component.selectedYear()).toBe(2026);
        expect(component.csvUrl()).toBe('http://localhost:8010/api/reports/cost-by-compartment.csv?year=2026&month=4');
    });

    it('ignores invalid selected period values', () => {
        const previousMonth = component.selectedMonth();
        const previousYear = component.selectedYear();

        component.setSelectedPeriod(null);

        expect(component.selectedMonth()).toBe(previousMonth);
        expect(component.selectedYear()).toBe(previousYear);
    });

    it('renders the advanced composition table controls', () => {
        expect(fixture.nativeElement.textContent).toContain('Composição detalhada');
        expect(fixture.nativeElement.textContent).toContain('Limpar filtros');
        expect(fixture.nativeElement.textContent).toContain('Colunas');

        const searchInput = fixture.nativeElement.querySelector('input[placeholder*="Buscar em Data"]');
        expect(searchInput).not.toBeNull();
    });

    it('keeps the detailed items available for the advanced table', () => {
        expect(component.detailedItems().length).toBe(3);
        expect(component.detailedGlobalFilterFields).toEqual([
            'date_label',
            'compartment_label',
            'service_label',
            'sku_label',
            'resource_label'
        ]);
    });

    it('keeps data and total always visible while allowing optional columns to toggle', () => {
        expect(component.visibleDetailedColumnCount()).toBe(6);

        component.setVisibleColumnFields(['service_label']);

        expect(component.isColumnVisible('service_label')).toBeTrue();
        expect(component.isColumnVisible('compartment_label')).toBeFalse();
        expect(component.isColumnVisible('sku_label')).toBeFalse();
        expect(component.isColumnVisible('resource_label')).toBeFalse();
        expect(component.visibleDetailedColumnCount()).toBe(3);
    });

    it('renders the empty state message when there are no detailed items', () => {
        apiService.getCostByCompartment.and.returnValue(
            of({
                ...reportResponse,
                detailed_items: []
            })
        );

        component.loadReport();
        fixture.detectChanges();

        expect(fixture.nativeElement.textContent).toContain('Nenhum item encontrado.');
    });

    it('builds daily composition with all services and percentage labels', () => {
        const row = component.dailyCompositionRows()[0];

        expect(row.composition.length).toBe(3);
        expect(row.composition.map((item) => item.label)).toEqual(['Compute 74,5%', 'Block Storage 18,2%', 'Load Balancer 7,3%']);
        expect(row.composition.every((item) => !('icon' in item))).toBeTrue();
        expect(row.composition.map((item) => item.tooltip)).toEqual([
            'Serviço: Compute | Percentual: 74,5%',
            'Serviço: Block Storage | Percentual: 18,2%',
            'Serviço: Load Balancer | Percentual: 7,3%'
        ]);
    });

    it('renders only the custom percentage label for meter items', () => {
        expect(fixture.nativeElement.textContent).toContain('Compute 74,5%');
        expect(fixture.nativeElement.textContent).not.toContain('Compute 74,5% (100%)');
    });

    it('shows 100 percent when a day has a single service', () => {
        apiService.getCostByCompartment.and.returnValue(
            of({
                ...reportResponse,
                detailed_items: [
                    {
                        date: '2026-04-01',
                        compartment_id: 'compartment-1',
                        compartment_name: 'Aplicacoes',
                        service: 'Compute',
                        sku_name: 'VM.Standard',
                        resource_id: 'resource-1',
                        resource_name: 'Instance A',
                        total_amount: 27.5
                    }
                ]
            })
        );

        component.loadReport();

        expect(component.dailyCompositionRows()[0].composition.map((item) => item.label)).toEqual(['Compute 100,0%']);
    });

    it('keeps fallback composition by compartment when detailed items are missing', () => {
        apiService.getCostByCompartment.and.returnValue(
            of({
                ...reportResponse,
                detailed_items: []
            })
        );

        component.loadReport();

        expect(component.dailyCompositionRows()[0].composition.map((item) => item.label)).toEqual(['Aplicacoes 100,0%']);
    });

    it('builds hover details for fallback composition items too', () => {
        apiService.getCostByCompartment.and.returnValue(
            of({
                ...reportResponse,
                detailed_items: []
            })
        );

        component.loadReport();

        expect(component.dailyCompositionRows()[0].composition[0].tooltip).toBe('Serviço: Aplicacoes | Percentual: 100,0%');
    });

    it('truncates long resource labels visually and keeps short ones unchanged', () => {
        expect(component.formatResourceLabel('ocid1.resource.oc1.sa-saopaulo-1.abcdefghijklmnopqrstuvxyz12345')).toBe(
            'ocid1.resource.oc1.s...12345'
        );
        expect(component.formatResourceLabel('Instance A')).toBe('Instance A');
        expect(component.formatResourceLabel('-')).toBe('-');
    });
});
