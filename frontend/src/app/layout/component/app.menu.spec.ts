import { ComponentFixture, TestBed } from '@angular/core/testing';
import { signal } from '@angular/core';
import { provideRouter, Router } from '@angular/router';
import { AuthService } from '@/app/core/auth.service';
import { AppMenu } from './app.menu';

describe('AppMenu', () => {
    let fixture: ComponentFixture<AppMenu>;
    let component: AppMenu;
    let router: Router;
    let authService: jasmine.SpyObj<AuthService> & { currentUser: ReturnType<typeof signal> };

    beforeEach(async () => {
        authService = Object.assign(jasmine.createSpyObj<AuthService>('AuthService', ['hasPermission']), {
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
        authService.hasPermission.and.returnValue(true);

        await TestBed.configureTestingModule({
            imports: [AppMenu],
            providers: [provideRouter([]), { provide: AuthService, useValue: authService }]
        }).compileComponents();

        router = TestBed.inject(Router);
        spyOnProperty(router, 'url', 'get').and.returnValue('/compartiments');
        fixture = TestBed.createComponent(AppMenu);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('includes Grupos in the instances menu', () => {
        const instancesGroup = component.model.find((item) => item.label === 'Instâncias');
        const labels = (instancesGroup?.items ?? []).map((item) => item.label);

        expect(labels).toEqual(['Instâncias', 'Grupos', 'Agendamentos', 'Compartimentos']);
        expect(instancesGroup?.expanded).toBeTrue();
    });

    it('includes DeskManager with the criar chamado entry', () => {
        const deskManagerGroup = component.model.find((item) => item.label === 'DeskManager');
        const labels = (deskManagerGroup?.items ?? []).map((item) => item.label);

        expect(labels).toEqual(['Criar chamado']);
        expect(deskManagerGroup?.items?.[0].routerLink).toEqual(['/deskmanager/create-ticket']);
    });

    it('includes Administracao above Auditoria when permissions are available', () => {
        const labels = component.model.map((item) => item.label);

        expect(labels.indexOf('Administração')).toBeGreaterThan(-1);
        expect(labels.indexOf('Administração')).toBeLessThan(labels.indexOf('Auditoria'));
    });

    it('includes Permissoes Diretas inside Administracao', () => {
        const administrationGroup = component.model.find((item) => item.label === 'Administração');
        const labels = (administrationGroup?.items ?? []).map((item) => item.label);

        expect(labels).toContain('Permissões Diretas');
    });
});
