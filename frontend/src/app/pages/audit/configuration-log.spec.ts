import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { ApiService } from '@/app/core/api.service';
import { AuditConfigurationPage } from './configuration-log';

describe('AuditConfigurationPage', () => {
    let fixture: ComponentFixture<AuditConfigurationPage>;
    let component: AuditConfigurationPage;
    let apiService: jasmine.SpyObj<ApiService>;

    const logs = [
        {
            id: 'config-1',
            event_type: 'schedule_updated',
            entity_type: 'schedule',
            actor_email: 'admin@local',
            summary: 'Schedule updated',
            created_at: '2026-04-10T12:00:01Z'
        },
        {
            id: 'config-2',
            event_type: 'instance_deleted',
            entity_type: 'instance',
            actor_email: null,
            summary: 'Instance deleted',
            created_at: '2026-04-10T12:05:01Z'
        }
    ];

    beforeEach(async () => {
        apiService = jasmine.createSpyObj<ApiService>('ApiService', ['listAuditConfigurations']);
        apiService.listAuditConfigurations.and.returnValue(of(logs));

        await TestBed.configureTestingModule({
            imports: [AuditConfigurationPage],
            providers: [{ provide: ApiService, useValue: apiService }]
        }).compileComponents();

        fixture = TestBed.createComponent(AuditConfigurationPage);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('loads configuration logs on init', () => {
        expect(apiService.listAuditConfigurations).toHaveBeenCalled();
        expect(component.items()).toEqual(logs);
        expect(component.itemCount()).toBe(2);
    });

    it('renders configuration rows and the loaded count', () => {
        const text = fixture.nativeElement.textContent;

        expect(text).toContain('schedule_updated');
        expect(text).toContain('Schedule updated');
        expect(text).toContain('admin@local');
    });

    it('renders an explicit empty state when there are no configuration logs', async () => {
        apiService.listAuditConfigurations.and.returnValue(of([]));

        fixture = TestBed.createComponent(AuditConfigurationPage);
        component = fixture.componentInstance;
        fixture.detectChanges();
        await fixture.whenStable();

        expect(component.itemCount()).toBe(0);
        expect(fixture.nativeElement.textContent).toContain('Nenhum registro de configuração encontrado.');
    });
});
