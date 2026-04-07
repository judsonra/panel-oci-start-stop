import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';
import { ApiService } from '@/app/core/api.service';
import { AuthService } from '@/app/core/auth.service';
import { AppTopbar } from './app.topbar';

describe('AppTopbar', () => {
    let fixture: ComponentFixture<AppTopbar>;
    let component: AppTopbar;
    let apiService: jasmine.SpyObj<ApiService>;
    let authService: jasmine.SpyObj<AuthService> & { currentUser: ReturnType<typeof signal> };

    beforeEach(async () => {
        jasmine.clock().install();
        apiService = jasmine.createSpyObj<ApiService>('ApiService', ['getBackendHealth', 'getReportsHealth', 'getBackendDocsUrl', 'getReportsDocsUrl']);
        authService = Object.assign(jasmine.createSpyObj<AuthService>('AuthService', ['logout']), {
            currentUser: signal({
                subject: 'local-admin',
                email: 'admin@example.com',
                groups: ['local_admin'],
                permissions: ['*'],
                auth_source: 'local_admin',
                is_superadmin: true,
                access_user_id: null
            })
        });
        apiService.getBackendHealth.and.returnValue(
            of({
                status: 'ok',
                timestamp: '2026-03-26T12:00:00Z',
                database: 'ok',
                oci_cli: 'ok',
                oci_config: 'ok',
                details: {}
            })
        );
        apiService.getReportsHealth.and.returnValue(of({ status: 'ok' }));
        apiService.getBackendDocsUrl.and.returnValue('http://localhost:8000/docs#');
        apiService.getReportsDocsUrl.and.returnValue('http://localhost:8010/docs#');

        await TestBed.configureTestingModule({
            imports: [AppTopbar],
            providers: [provideRouter([]), { provide: ApiService, useValue: apiService }, { provide: AuthService, useValue: authService }]
        }).compileComponents();
    });

    afterEach(() => {
        jasmine.clock().uninstall();
    });

    function createComponent(): void {
        fixture = TestBed.createComponent(AppTopbar);
        component = fixture.componentInstance;
        jasmine.clock().tick(0);
        fixture.detectChanges();
    }

    it('renders both services as online when healthchecks succeed', () => {
        createComponent();

        expect(component.backendStatus().status).toBe('online');
        expect(component.reportsStatus().status).toBe('online');
        expect(component.backendStatus().docsUrl).toBe('http://localhost:8000/docs#');
        expect(component.reportsStatus().docsUrl).toBe('http://localhost:8010/docs#');

        const labels = Array.from(fixture.nativeElement.querySelectorAll('.layout-topbar-status span:nth-of-type(2)')).map((element) =>
            (element as HTMLElement).textContent?.trim()
        );
        expect(labels).toEqual(['Backend', 'Reports']);
    });

    it('renders the service badges as external docs links', () => {
        createComponent();

        const links = fixture.nativeElement.querySelectorAll('.layout-topbar-status');

        expect(links[0].getAttribute('href')).toBe('http://localhost:8000/docs#');
        expect(links[0].getAttribute('target')).toBe('_blank');
        expect(links[0].getAttribute('rel')).toBe('noopener noreferrer');

        expect(links[1].getAttribute('href')).toBe('http://localhost:8010/docs#');
        expect(links[1].getAttribute('target')).toBe('_blank');
        expect(links[1].getAttribute('rel')).toBe('noopener noreferrer');
    });

    it('marks backend as degraded when the health payload is not ok', () => {
        apiService.getBackendHealth.and.returnValue(
            of({
                status: 'degraded',
                timestamp: '2026-03-26T12:00:00Z',
                database: 'ok',
                oci_cli: 'error',
                oci_config: 'ok',
                details: {}
            })
        );

        createComponent();

        expect(component.backendStatus().status).toBe('degraded');
        expect(component.backendStatus().online).toBeFalse();
        expect(component.reportsStatus().status).toBe('online');
    });

    it('marks reports as offline when its healthcheck fails', () => {
        apiService.getReportsHealth.and.returnValue(throwError(() => new Error('reports down')));

        createComponent();

        expect(component.backendStatus().status).toBe('online');
        expect(component.reportsStatus().status).toBe('offline');
        expect(component.reportsStatus().online).toBeFalse();
    });

    it('marks backend as offline when its healthcheck fails', () => {
        apiService.getBackendHealth.and.returnValue(throwError(() => new Error('backend down')));

        createComponent();

        expect(component.backendStatus().status).toBe('offline');
        expect(component.reportsStatus().status).toBe('online');
    });

    it('polls healthchecks every 30 seconds', () => {
        createComponent();

        expect(apiService.getBackendHealth).toHaveBeenCalledTimes(1);
        expect(apiService.getReportsHealth).toHaveBeenCalledTimes(1);

        jasmine.clock().tick(30000);
        fixture.detectChanges();

        expect(apiService.getBackendHealth).toHaveBeenCalledTimes(2);
        expect(apiService.getReportsHealth).toHaveBeenCalledTimes(2);
    });

    it('renders current user email in the topbar', () => {
        createComponent();

        expect(fixture.nativeElement.querySelector('.layout-topbar-user')?.textContent?.trim()).toBe('admin@example.com');
    });
});
