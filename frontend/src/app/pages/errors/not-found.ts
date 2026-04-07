import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';

@Component({
    selector: 'app-not-found-page',
    standalone: true,
    imports: [CommonModule],
    template: `
        <section class="error-shell">
            <div class="error-panel">
                <span class="section-kicker">Erro de navegação</span>
                <h1>404</h1>
                <h2>Página não encontrada</h2>
                <p>A rota solicitada não está disponível ou a autenticação não foi configurada neste ambiente.</p>
            </div>
        </section>
    `
})
export class NotFoundPage {}
