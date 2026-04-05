import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ApiService } from './api.service';

describe('ApiService', () => {
    let service: ApiService;
    let httpMock: HttpTestingController;
    const originalConfig = window.__APP_CONFIG__;

    beforeEach(() => {
        window.__APP_CONFIG__ = {
            apiBaseUrl: 'http://localhost:8000/api',
            reportsApiBaseUrl: 'http://localhost:8010/api'
        };

        TestBed.configureTestingModule({
            imports: [HttpClientTestingModule],
            providers: [ApiService]
        });

        service = TestBed.inject(ApiService);
        httpMock = TestBed.inject(HttpTestingController);
    });

    afterEach(() => {
        httpMock.verify();
        window.__APP_CONFIG__ = originalConfig;
    });

    it('derives docs URLs from the configured API base URLs', () => {
        expect(service.getBackendDocsUrl()).toBe('http://localhost:8000/docs#');
        expect(service.getReportsDocsUrl()).toBe('http://localhost:8010/docs#');
    });

    it('keeps reports endpoints under the api prefix', () => {
        service.getCostByCompartment(2026, 3).subscribe();

        const request = httpMock.expectOne('http://localhost:8010/api/reports/cost-by-compartment?year=2026&month=3');
        expect(request.request.method).toBe('GET');
        request.flush({
            year: 2026,
            month: 3,
            source: 'cache',
            sync_status: 'ok',
            available: true,
            total_amount: 0,
            daily_totals: [],
            compartments: [],
            detailed_items: []
        });
    });

    it('keeps reports refresh endpoints under reportsApiBaseUrl only', () => {
        service.refreshCostByCompartment({ year: 2026, month: 3 }).subscribe();

        const request = httpMock.expectOne('http://localhost:8010/api/reports/cost-by-compartment/refresh');
        expect(request.request.method).toBe('POST');
        expect(request.request.body).toEqual({ year: 2026, month: 3 });
        request.flush({
            year: 2026,
            month: 3,
            source: 'oci',
            sync_status: 'ready',
            available: true,
            total_amount: 0,
            daily_totals: [],
            compartments: [],
            detailed_items: []
        });

        expect(httpMock.match((candidate) => candidate.url.startsWith('http://localhost:8000/api/reports')).length).toBe(0);
    });

    it('builds reports export URLs from reportsApiBaseUrl only', () => {
        expect(service.getCostByCompartmentCsvUrl(2026, 3)).toBe('http://localhost:8010/api/reports/cost-by-compartment.csv?year=2026&month=3');
    });

    it('uses the backend api prefix for compartment endpoints', () => {
        service.listCompartments().subscribe();
        service.listAndUpdateCompartments().subscribe();

        const listRequest = httpMock.expectOne('http://localhost:8000/api/compartiments/list');
        expect(listRequest.request.method).toBe('GET');
        listRequest.flush([]);

        const syncRequest = httpMock.expectOne('http://localhost:8000/api/compartiments/listandupdate');
        expect(syncRequest.request.method).toBe('GET');
        syncRequest.flush([]);
    });

    it('uses the backend api prefix for group endpoints', () => {
        service.listGroups().subscribe();
        service.getGroupTree().subscribe();

        const listRequest = httpMock.expectOne('http://localhost:8000/api/groups');
        expect(listRequest.request.method).toBe('GET');
        listRequest.flush([]);

        const treeRequest = httpMock.expectOne('http://localhost:8000/api/groups/tree');
        expect(treeRequest.request.method).toBe('GET');
        treeRequest.flush([]);
    });

    it('uses the backend api prefix for instance import preview and import endpoints', () => {
        service.getInstanceImportPreview('ocid1.instance.oc1..preview').subscribe();
        service.importInstance({ ocid: 'ocid1.instance.oc1..preview', description: 'desc', enabled: true }).subscribe();

        const previewRequest = httpMock.expectOne('http://localhost:8000/api/instances/import-preview/ocid1.instance.oc1..preview');
        expect(previewRequest.request.method).toBe('GET');
        previewRequest.flush({
            name: 'Instance A1',
            ocid: 'ocid1.instance.oc1..preview',
            compartment_ocid: 'ocid1.compartment.oc1..aaaa',
            compartment_name: 'Compartment A',
            already_registered: false
        });

        const importRequest = httpMock.expectOne('http://localhost:8000/api/instances/import');
        expect(importRequest.request.method).toBe('POST');
        expect(importRequest.request.body).toEqual({ ocid: 'ocid1.instance.oc1..preview', description: 'desc', enabled: true });
        importRequest.flush({
            id: 'instance-1',
            name: 'Instance A1',
            ocid: 'ocid1.instance.oc1..preview',
            enabled: true,
            created_at: '2026-03-12T00:00:00Z',
            updated_at: '2026-03-12T00:00:00Z'
        });
    });
});
