import { CommonModule } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { MessageModule } from 'primeng/message';
import { PasswordModule } from 'primeng/password';
import { AuthService } from '@/app/core/auth.service';

@Component({
    selector: 'app-access-page',
    standalone: true,
    imports: [CommonModule, ReactiveFormsModule, ButtonModule, InputTextModule, MessageModule, PasswordModule],
    template: `
        <section class="auth-shell">
            <form class="form-panel auth-panel" [formGroup]="form" (ngSubmit)="login()">
                <div class="page-header">
                    <div>
                        <span class="section-kicker">Acesso administrativo</span>
                        <h2>Login local</h2>
                        <p>Use a rota oculta apenas para acesso administrativo total do sistema.</p>
                    </div>
                </div>

                @if (error()) {
                    <p-message severity="error" [text]="error() || ''"></p-message>
                }

                <label>
                    <span>Email</span>
                    <input pInputText type="email" formControlName="email" />
                </label>

                <label>
                    <span>Senha</span>
                    <p-password formControlName="password" [feedback]="false" [toggleMask]="true"></p-password>
                </label>

                <div class="form-actions">
                    <button pButton type="submit" label="Entrar" icon="pi pi-sign-in" [disabled]="submitting()"></button>
                </div>
            </form>
        </section>
    `
})
export class AccessPage {
    private readonly auth = inject(AuthService);
    private readonly formBuilder = inject(FormBuilder);
    private readonly router = inject(Router);

    readonly error = signal<string | null>(null);
    readonly submitting = signal(false);
    readonly form = this.formBuilder.nonNullable.group({
        email: ['', [Validators.required, Validators.email]],
        password: ['', [Validators.required]]
    });

    async login(): Promise<void> {
        if (this.form.invalid) {
            this.form.markAllAsTouched();
            return;
        }
        this.submitting.set(true);
        this.error.set(null);
        try {
            await this.auth.loginLocal(this.form.controls.email.value, this.form.controls.password.value);
            await this.router.navigateByUrl('/');
        } catch {
            this.error.set('Não foi possível autenticar com o acesso local.');
        } finally {
            this.submitting.set(false);
        }
    }
}
