import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideAnimations } from '@angular/platform-browser/animations';
import { AutoCompleteCompleteEvent } from 'primeng/autocomplete';
import { DeskManagerCreateTicketPage } from './create-ticket';

describe('DeskManagerCreateTicketPage', () => {
    let fixture: ComponentFixture<DeskManagerCreateTicketPage>;
    let component: DeskManagerCreateTicketPage;
    let httpMock: HttpTestingController;

    beforeEach(async () => {
        window.__APP_CONFIG__ = {
            apiBaseUrl: 'http://localhost:8000/api',
            reportsApiBaseUrl: 'http://localhost:8010/api'
        };

        await TestBed.configureTestingModule({
            imports: [HttpClientTestingModule, DeskManagerCreateTicketPage],
            providers: [provideAnimations()]
        }).compileComponents();

        fixture = TestBed.createComponent(DeskManagerCreateTicketPage);
        component = fixture.componentInstance;
        httpMock = TestBed.inject(HttpTestingController);
        fixture.detectChanges();

        httpMock.expectOne('http://localhost:8000/api/deskmanager/users').flush([{ id: '2572', name: 'Eduardo' }]);
        httpMock.expectOne('http://localhost:8000/api/deskmanager/categories').flush([{ id: '9679', name: 'Categoria A' }]);
        fixture.detectChanges();
    });

    afterEach(() => {
        httpMock.verify();
    });

    it('adds a pending row and submits the batch to the backend', () => {
        component.form.setValue({
            user: { id: '2572', name: 'Eduardo' },
            category: { id: '9679', name: 'Categoria A' },
            description: 'Problema no ambiente'
        });

        component.addPendingTicket();

        expect(component.tickets().length).toBe(1);
        expect(component.tickets()[0].status).toBe('pending');

        component.submitTickets();

        const request = httpMock.expectOne('http://localhost:8000/api/deskmanager/criarchamado');
        expect(request.request.method).toBe('POST');
        expect(request.request.body).toEqual({
            items: [{ user_id: '2572', category_id: '9679', description: 'Problema no ambiente' }]
        });
        request.flush({
            total: 1,
            success_count: 1,
            failed_count: 0,
            results: [
                {
                    user_id: '2572',
                    category_id: '9679',
                    description: 'Problema no ambiente',
                    status: 'success',
                    message: 'Chamado criado com sucesso!'
                }
            ]
        });

        expect(component.tickets()[0].status).toBe('success');
        expect(component.feedback()).toContain('Sucesso: 1');
    });

    it('filters categories against the deskmanager endpoint', () => {
        component.filterCategories({ query: 'vpn' } as AutoCompleteCompleteEvent);

        const request = httpMock.expectOne('http://localhost:8000/api/deskmanager/categories?search=vpn');
        expect(request.request.method).toBe('GET');
        request.flush([{ id: '9896', name: 'PAS - VPN' }]);

        expect(component.categorySuggestions()[0].name).toBe('PAS - VPN');
    });

    it('renders Abrir chamado before Adicionar inside form actions and keeps it disabled without pending items', () => {
        const element: HTMLElement = fixture.nativeElement;
        const buttons = Array.from(element.querySelectorAll('.form-actions button'));
        const labels = buttons.map((button) => button.textContent?.trim() ?? '');

        expect(labels).toEqual(['Abrir chamado', 'Adicionar']);
        expect(buttons[0].hasAttribute('disabled')).toBeTrue();
    });
});
