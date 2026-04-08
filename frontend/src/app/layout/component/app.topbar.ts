import { CommonModule } from '@angular/common';
import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { RouterModule } from '@angular/router';
import { catchError, forkJoin, map, of, switchMap, timer } from 'rxjs';
import { ApiService } from '@/app/core/api.service';
import { AuthService } from '@/app/core/auth.service';
import { TopbarServiceStatusModel } from '@/app/core/models';
import { LayoutService } from '@/app/layout/service/layout.service';

@Component({
    selector: 'app-topbar',
    standalone: true,
    imports: [CommonModule, RouterModule],
    template: `<div class="layout-topbar">
        <div class="layout-topbar-start">
            <button class="layout-menu-button layout-topbar-action" type="button" (click)="layoutService.onMenuToggle()">
                <i class="pi pi-bars"></i>
            </button>
            <a class="layout-topbar-logo" routerLink="/">
                <span class="layout-topbar-logo-mark">OCI</span>
                <span class="layout-topbar-logo-copy">
                    <strong>Automação de Instâncias</strong>
                </span>
            </a>
        </div>

        <div class="layout-topbar-actions">
            @for (service of services(); track service.label) {
                <a
                    class="layout-topbar-status"
                    [class.is-online]="service.status === 'online'"
                    [class.is-degraded]="service.status === 'degraded'"
                    [class.is-offline]="service.status === 'offline'"
                    [href]="service.docsUrl"
                    target="_blank"
                    rel="noopener noreferrer"
                    [attr.aria-label]="'Abrir documentação de ' + service.label"
                >
                    <span class="status-dot"></span>
                    <span>{{ service.label }}</span>
                    <i class="pi pi-external-link layout-topbar-status-icon" aria-hidden="true"></i>
                </a>
            }

            @if (auth.currentUser(); as currentUser) {
                <div class="layout-topbar-auth">
                    <span class="layout-topbar-user">{{ currentUser.email || currentUser.subject }}</span>
                    <button class="layout-topbar-action" type="button" (click)="logout()">
                        <i class="pi pi-sign-out"></i>
                        <span>Sair</span>
                    </button>
                </div>
            }
        </div>
    </div>`
})
export class AppTopbar {
    readonly layoutService = inject(LayoutService);
    private readonly api = inject(ApiService);
    readonly auth = inject(AuthService);
    private readonly destroyRef = inject(DestroyRef);
    private readonly backendLabel = 'Backend';
    private readonly reportsLabel = 'Reports';
    private readonly backendDocsUrl = this.api.getBackendDocsUrl();
    private readonly reportsDocsUrl = this.api.getReportsDocsUrl();

    readonly backendStatus = signal<TopbarServiceStatusModel>({
        label: this.backendLabel,
        status: 'offline',
        online: false,
        docsUrl: this.backendDocsUrl
    });
    readonly reportsStatus = signal<TopbarServiceStatusModel>({
        label: this.reportsLabel,
        status: 'offline',
        online: false,
        docsUrl: this.reportsDocsUrl
    });
    readonly services = computed(() => [this.backendStatus(), this.reportsStatus()]);

    constructor() {
        timer(0, 30000)
            .pipe(
                switchMap(() =>
                    forkJoin({
                        backend: this.api.getBackendHealth().pipe(
                            map((response) =>
                                this.mapStatus(this.backendLabel, response.status === 'ok' ? 'online' : 'degraded', this.backendDocsUrl)
                            ),
                            catchError(() => of(this.mapStatus(this.backendLabel, 'offline', this.backendDocsUrl)))
                        ),
                        reports: this.api.getReportsHealth().pipe(
                            map(() => this.mapStatus(this.reportsLabel, 'online', this.reportsDocsUrl)),
                            catchError(() => of(this.mapStatus(this.reportsLabel, 'offline', this.reportsDocsUrl)))
                        )
                    })
                ),
                takeUntilDestroyed(this.destroyRef)
            )
            .subscribe(({ backend, reports }) => {
                this.backendStatus.set(backend);
                this.reportsStatus.set(reports);
            });
    }

    logout(): void {
        void this.auth.logout();
    }

    private mapStatus(label: string, status: TopbarServiceStatusModel['status'], docsUrl: string): TopbarServiceStatusModel {
        return {
            label,
            status,
            online: status === 'online',
            docsUrl
        };
    }
}
