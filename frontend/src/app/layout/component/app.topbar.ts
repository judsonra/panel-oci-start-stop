import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { RouterModule } from '@angular/router';
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
            <div class="layout-topbar-status">
                <span class="status-dot"></span>
                <span>Backend FastAPI + OCI CLI</span>
            </div>
        </div>
    </div>`
})
export class AppTopbar {
    readonly layoutService = inject(LayoutService);
}
