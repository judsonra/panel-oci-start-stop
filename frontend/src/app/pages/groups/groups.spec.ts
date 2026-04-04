import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { of } from 'rxjs';
import { ApiService } from '@/app/core/api.service';
import { GroupsPage } from './groups';

describe('GroupsPage', () => {
    let fixture: ComponentFixture<GroupsPage>;
    let component: GroupsPage;
    let apiService: jasmine.SpyObj<ApiService>;
    let router: Router;

    beforeEach(async () => {
        apiService = jasmine.createSpyObj<ApiService>('ApiService', ['listGroups', 'deleteGroup']);
        apiService.listGroups.and.returnValue(
            of([
                {
                    id: 'group-1',
                    name: 'Aplicação Financeira',
                    instance_count: 2,
                    instances: [],
                    created_at: '2026-04-03T00:00:00Z',
                    updated_at: '2026-04-03T00:00:00Z'
                }
            ])
        );
        apiService.deleteGroup.and.returnValue(of(void 0));

        await TestBed.configureTestingModule({
            imports: [GroupsPage],
            providers: [{ provide: ApiService, useValue: apiService }, provideRouter([])]
        }).compileComponents();

        router = TestBed.inject(Router);
        spyOn(router, 'navigate').and.resolveTo(true);
        fixture = TestBed.createComponent(GroupsPage);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('loads groups on init', () => {
        expect(apiService.listGroups).toHaveBeenCalled();
        expect(component.groups()[0].name).toBe('Aplicação Financeira');
    });

    it('navigates to the new group route', () => {
        component.openNewGroup();

        expect(router.navigate).toHaveBeenCalledWith(['/groups/new']);
    });
});
