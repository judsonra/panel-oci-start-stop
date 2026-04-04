import { ComponentFixture, TestBed } from '@angular/core/testing';
import { convertToParamMap, provideRouter, ActivatedRoute, Router } from '@angular/router';
import { of } from 'rxjs';
import { ApiService } from '@/app/core/api.service';
import { GroupFormPage } from './group-form';

describe('GroupFormPage', () => {
    let fixture: ComponentFixture<GroupFormPage>;
    let component: GroupFormPage;
    let apiService: jasmine.SpyObj<ApiService>;
    let router: Router;

    beforeEach(async () => {
        apiService = jasmine.createSpyObj<ApiService>('ApiService', ['getGroupTree', 'getGroup', 'createGroup', 'updateGroup']);
        apiService.getGroupTree.and.returnValue(
            of([
                {
                    id: 'compartment-1',
                    name: 'Compartment A',
                    instances: [
                        { id: 'instance-1', name: 'App A', ocid: 'ocid1.instance.oc1..a' },
                        { id: 'instance-2', name: 'App B', ocid: 'ocid1.instance.oc1..b' }
                    ]
                }
            ])
        );
        apiService.createGroup.and.returnValue(
            of({
                id: 'group-1',
                name: 'Grupo A',
                instance_count: 1,
                instances: [{ id: 'instance-1', name: 'App A', ocid: 'ocid1.instance.oc1..a', compartment_id: 'compartment-1' }],
                created_at: '2026-04-03T00:00:00Z',
                updated_at: '2026-04-03T00:00:00Z'
            })
        );

        await TestBed.configureTestingModule({
            imports: [GroupFormPage],
            providers: [
                { provide: ApiService, useValue: apiService },
                provideRouter([]),
                {
                    provide: ActivatedRoute,
                    useValue: {
                        snapshot: {
                            paramMap: convertToParamMap({})
                        }
                    }
                }
            ]
        }).compileComponents();

        router = TestBed.inject(Router);
        spyOn(router, 'navigate').and.resolveTo(true);
        fixture = TestBed.createComponent(GroupFormPage);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('loads the group tree on init', () => {
        expect(apiService.getGroupTree).toHaveBeenCalled();
        expect(component.treeNodes().length).toBe(1);
    });

    it('creates a group with the selected instances', () => {
        component.form.controls.name.setValue('Grupo A');
        component.onSelectionChange([
            {
                key: 'instance-1',
                label: 'App A',
                data: { id: 'instance-1', name: 'App A', ocid: 'ocid1.instance.oc1..a' },
                leaf: true
            }
        ]);
        component.activeStep.set(2);

        component.save();

        expect(apiService.createGroup).toHaveBeenCalledWith({
            name: 'Grupo A',
            instance_ids: ['instance-1']
        });
        expect(router.navigate).toHaveBeenCalledWith(['/groups'], {
            state: { feedback: 'Grupo criado com sucesso.' }
        });
    });
});
