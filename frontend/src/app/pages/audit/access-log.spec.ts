import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { ApiService } from '@/app/core/api.service';
import { AuditAccessPage } from './access-log';

describe('AuditAccessPage', () => {
    let fixture: ComponentFixture<AuditAccessPage>;
    let component: AuditAccessPage;
    let apiService: jasmine.SpyObj<ApiService>;

    const logs = [
        {
            id: 'audit-1',
            event_type: 'api_access',
            auth_source: 'local-dev',
            email: 'local@example.com',
            path: '/api/instances',
            method: 'GET',
            status_code: 200,
            started_at: '2026-04-10T12:00:00Z',
            finished_at: '2026-04-10T12:00:01Z',
            duration_ms: 1000,
            created_at: '2026-04-10T12:00:01Z'
        },
        {
            id: 'audit-2',
            event_type: 'api_access',
            auth_source: null,
            email: null,
            path: '/api/legacy',
            method: 'POST',
            status_code: 500,
            message: 'erro',
            started_at: null,
            finished_at: null,
            duration_ms: null,
            created_at: '2026-04-10T12:00:02Z'
        }
    ];

    beforeEach(async () => {
        apiService = jasmine.createSpyObj<ApiService>('ApiService', ['listAuditAccess']);
        apiService.listAuditAccess.and.returnValue(of(logs));

        await TestBed.configureTestingModule({
            imports: [AuditAccessPage],
            providers: [{ provide: ApiService, useValue: apiService }]
        }).compileComponents();

        fixture = TestBed.createComponent(AuditAccessPage);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('loads access logs on init', () => {
        expect(apiService.listAuditAccess).toHaveBeenCalled();
        expect(component.items()).toEqual(logs);
    });

    it('renders timing fields and legacy fallback values', () => {
        const text = fixture.nativeElement.textContent;

        expect(text).toContain('1000 ms');
        expect(text).toContain('/api/instances');
        expect(text).toContain('GET');
        expect(text).toContain('/api/legacy');
    });
});
