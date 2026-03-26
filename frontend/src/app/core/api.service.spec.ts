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
            compartments: []
        });
    });
});
