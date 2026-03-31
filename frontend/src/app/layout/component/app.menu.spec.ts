import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { AppMenu } from './app.menu';

describe('AppMenu', () => {
    let fixture: ComponentFixture<AppMenu>;
    let component: AppMenu;
    let router: Router;

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [AppMenu],
            providers: [provideRouter([])]
        }).compileComponents();

        router = TestBed.inject(Router);
        spyOnProperty(router, 'url', 'get').and.returnValue('/compartiments');
        fixture = TestBed.createComponent(AppMenu);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('includes Compartimentos below Agendamentos in the instances menu', () => {
        const instancesGroup = component.model.find((item) => item.label === 'Instâncias');
        const labels = (instancesGroup?.items ?? []).map((item) => item.label);

        expect(labels).toEqual(['Instâncias', 'Agendamentos', 'Compartimentos']);
        expect(instancesGroup?.expanded).toBeTrue();
    });
});
