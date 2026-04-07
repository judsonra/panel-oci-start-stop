import { CommonModule } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { AuthService } from '@/app/core/auth.service';

@Component({
    selector: 'app-auth-callback-page',
    standalone: true,
    imports: [CommonModule],
    template: `
        <section class="auth-shell">
            <div class="form-panel auth-panel">
                <span class="section-kicker">Microsoft Entra ID</span>
                <h2>Finalizando autenticação</h2>
                <p>{{ message() }}</p>
            </div>
        </section>
    `
})
export class AuthCallbackPage {
    private readonly route = inject(ActivatedRoute);
    private readonly auth = inject(AuthService);
    readonly message = signal('Processando retorno do provedor...');

    constructor() {
        void this.handle();
    }

    private async handle(): Promise<void> {
        const code = this.route.snapshot.queryParamMap.get('code');
        const state = this.route.snapshot.queryParamMap.get('state');
        if (!code) {
            this.message.set('Código de autenticação não encontrado.');
            return;
        }
        try {
            await this.auth.handleEntraCallback(code, state);
        } catch {
            this.message.set('Falha ao concluir a autenticação no Entra ID.');
        }
    }
}
