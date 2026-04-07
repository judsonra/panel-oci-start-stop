import { computed, inject, Injectable, signal } from '@angular/core';
import { Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { ApiService } from './api.service';
import { AuthConfigModel, CurrentUserModel } from './models';

@Injectable({ providedIn: 'root' })
export class AuthService {
    private readonly api = inject(ApiService);
    private readonly router = inject(Router);
    private readonly tokenKey = 'oci.auth.token';
    private readonly stateKey = 'oci.auth.entra.state';
    private readonly verifierKey = 'oci.auth.entra.verifier';
    private readonly targetKey = 'oci.auth.entra.target';

    readonly config = signal<AuthConfigModel | null>(null);
    readonly currentUser = signal<CurrentUserModel | null>(null);
    readonly ready = signal(false);
    readonly isAuthenticated = computed(() => this.currentUser() !== null);

    async loadConfig(): Promise<AuthConfigModel> {
        if (this.config()) {
            return this.config() as AuthConfigModel;
        }
        const config = await firstValueFrom(this.api.getAuthConfig());
        this.config.set(config);
        return config;
    }

    async restoreSession(): Promise<CurrentUserModel | null> {
        const token = this.getToken();
        if (!token) {
            const config = await this.loadConfig();
            if (!config.entra_enabled && !config.local_enabled) {
                try {
                    const currentUser = await firstValueFrom(this.api.getCurrentUser());
                    this.currentUser.set(currentUser);
                    this.ready.set(true);
                    return currentUser;
                } catch {
                    this.currentUser.set(null);
                }
            }
            this.ready.set(true);
            return null;
        }
        try {
            const currentUser = await firstValueFrom(this.api.getCurrentUser());
            this.currentUser.set(currentUser);
            this.ready.set(true);
            return currentUser;
        } catch {
            this.clearSession();
            this.ready.set(true);
            return null;
        }
    }

    async ensureAuthenticated(targetUrl: string): Promise<boolean> {
        if (this.currentUser()) {
            return true;
        }
        await this.restoreSession();
        if (this.currentUser()) {
            return true;
        }
        const config = await this.loadConfig();
        if (!config.entra_enabled && !config.local_enabled) {
            return true;
        }
        if (config.entra_enabled) {
            await this.startEntraLogin(targetUrl);
            return false;
        }
        await this.router.navigate(['/404']);
        return false;
    }

    async ensureLocalAccessPage(): Promise<boolean> {
        const config = await this.loadConfig();
        if (!config.local_enabled) {
            await this.router.navigate(['/404']);
            return false;
        }
        return true;
    }

    async loginLocal(email: string, password: string): Promise<void> {
        const token = await firstValueFrom(this.api.loginLocal({ email, password }));
        this.setToken(token.access_token);
        const currentUser = await firstValueFrom(this.api.getCurrentUser());
        this.currentUser.set(currentUser);
    }

    async startEntraLogin(targetUrl: string): Promise<void> {
        const config = await this.loadConfig();
        if (!config.entra_enabled || !config.authority || !config.client_id || !config.redirect_uri) {
            await this.router.navigate(['/404']);
            return;
        }
        const state = crypto.randomUUID();
        const verifier = this.generateCodeVerifier();
        const challenge = await this.generateCodeChallenge(verifier);
        sessionStorage.setItem(this.stateKey, state);
        sessionStorage.setItem(this.verifierKey, verifier);
        sessionStorage.setItem(this.targetKey, targetUrl);
        const scopes = encodeURIComponent((config.scopes ?? []).join(' '));
        const authorizeUrl =
            `${config.authority.replace(/\/$/, '')}/oauth2/v2.0/authorize` +
            `?client_id=${encodeURIComponent(config.client_id)}` +
            `&response_type=code` +
            `&redirect_uri=${encodeURIComponent(config.redirect_uri)}` +
            `&response_mode=query` +
            `&scope=${scopes}` +
            `&state=${encodeURIComponent(state)}` +
            `&code_challenge=${encodeURIComponent(challenge)}` +
            `&code_challenge_method=S256`;
        window.location.assign(authorizeUrl);
    }

    async handleEntraCallback(code: string, state: string | null): Promise<void> {
        const expectedState = sessionStorage.getItem(this.stateKey);
        const verifier = sessionStorage.getItem(this.verifierKey);
        const config = await this.loadConfig();
        if (!expectedState || !verifier || !state || state !== expectedState || !config.redirect_uri) {
            throw new Error('Invalid Entra callback state');
        }
        const token = await firstValueFrom(
            this.api.exchangeEntraCode({
                code,
                code_verifier: verifier,
                redirect_uri: config.redirect_uri
            })
        );
        this.setToken(token.access_token);
        const currentUser = await firstValueFrom(this.api.getCurrentUser());
        this.currentUser.set(currentUser);
        const nextUrl = sessionStorage.getItem(this.targetKey) || '/';
        sessionStorage.removeItem(this.stateKey);
        sessionStorage.removeItem(this.verifierKey);
        sessionStorage.removeItem(this.targetKey);
        await this.router.navigateByUrl(nextUrl);
    }

    async logout(): Promise<void> {
        const config = await this.loadConfig();
        try {
            await firstValueFrom(this.api.logout());
        } catch {
            // noop
        }
        this.clearSession();
        if (config.entra_enabled && config.authority && config.post_logout_redirect_uri) {
            const logoutUrl =
                `${config.authority.replace(/\/$/, '')}/oauth2/v2.0/logout` +
                `?post_logout_redirect_uri=${encodeURIComponent(config.post_logout_redirect_uri)}`;
            window.location.assign(logoutUrl);
            return;
        }
        await this.router.navigate(['/404']);
    }

    async recordPageAccess(path: string): Promise<void> {
        if (!this.currentUser()) {
            return;
        }
        try {
            await firstValueFrom(this.api.registerPageAccess(path));
        } catch {
            // noop
        }
    }

    hasPermission(permission: string): boolean {
        const currentUser = this.currentUser();
        if (!currentUser) {
            return false;
        }
        return currentUser.is_superadmin || currentUser.permissions.includes('*') || currentUser.permissions.includes(permission);
    }

    getToken(): string | null {
        return localStorage.getItem(this.tokenKey);
    }

    private setToken(token: string): void {
        localStorage.setItem(this.tokenKey, token);
    }

    private clearSession(): void {
        localStorage.removeItem(this.tokenKey);
        this.currentUser.set(null);
    }

    private generateCodeVerifier(): string {
        return Array.from(crypto.getRandomValues(new Uint8Array(32)))
            .map((value) => value.toString(16).padStart(2, '0'))
            .join('');
    }

    private async generateCodeChallenge(verifier: string): Promise<string> {
        const data = new TextEncoder().encode(verifier);
        const digest = await crypto.subtle.digest('SHA-256', data);
        return btoa(String.fromCharCode(...new Uint8Array(digest)))
            .replace(/\+/g, '-')
            .replace(/\//g, '_')
            .replace(/=+$/, '');
    }
}
