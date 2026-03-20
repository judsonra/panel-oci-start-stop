import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NavigationEnd, Router } from '@angular/router';
import { MenuItem } from 'primeng/api';
import { PanelMenu } from 'primeng/panelmenu';
import { filter } from 'rxjs';

@Component({
    selector: 'app-menu',
    standalone: true,
    imports: [CommonModule, PanelMenu],
    template: `<div class="layout-menu-brand">
            <span class="layout-menu-kicker">Painel Operacional</span>
            <h1>OCI Automation</h1>
        </div>
        <p-panelmenu [model]="model" styleClass="app-panel-menu"></p-panelmenu>`
})
export class AppMenu {
    router = inject(Router);

    model: MenuItem[] = [];

    constructor() {
        this.syncMenuState(this.router.url);

        this.router.events.pipe(filter((event) => event instanceof NavigationEnd)).subscribe((event) => {
            const navEvent = event as NavigationEnd;
            this.syncMenuState(navEvent.urlAfterRedirects);
        });
    }

    private syncMenuState(activeUrl: string) {
        const normalizedPath = activeUrl.split('?')[0].split('#')[0] || '/';

        this.model = [
            {
                label: 'Dashboard',
                icon: 'pi pi-chart-bar',
                expanded: normalizedPath === '/',
                items: [
                    {
                        label: 'Visão Geral',
                        icon: 'pi pi-home',
                        routerLink: ['/']
                    }
                ]
            },
            {
                label: 'Instâncias',
                icon: 'pi pi-desktop',
                expanded: normalizedPath.startsWith('/instances') || normalizedPath.startsWith('/schedules'),
                items: [
                    {
                        label: 'Instâncias',
                        icon: 'pi pi-server',
                        routerLink: ['/instances']
                    },
                    {
                        label: 'Agendamentos',
                        icon: 'pi pi-calendar',
                        routerLink: ['/schedules']
                    }
                ]
            },
            {
                label: 'Auditoria',
                icon: 'pi pi-history',
                expanded: normalizedPath.startsWith('/executions'),
                items: [
                    {
                        label: 'Execuções',
                        icon: 'pi pi-list-check',
                        routerLink: ['/executions']
                    }
                ]
            }
        ];
    }
}
