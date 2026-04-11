import { Component, effect, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NavigationEnd, Router } from '@angular/router';
import { MenuItem } from 'primeng/api';
import { PanelMenu } from 'primeng/panelmenu';
import { filter } from 'rxjs';
import { AuthService } from '@/app/core/auth.service';

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
    auth = inject(AuthService);

    model: MenuItem[] = [];

    constructor() {
        this.syncMenuState(this.router.url);

        this.router.events.pipe(filter((event) => event instanceof NavigationEnd)).subscribe((event) => {
            const navEvent = event as NavigationEnd;
            this.syncMenuState(navEvent.urlAfterRedirects);
        });

        effect(() => {
            this.auth.currentUser();
            this.syncMenuState(this.router.url);
        });
    }

    private syncMenuState(activeUrl: string) {
        const normalizedPath = activeUrl.split('?')[0].split('#')[0] || '/';
        const hasPermission = (permission: string) => this.auth.hasPermission(permission);
        const compactItems = (items: Array<MenuItem | null>): MenuItem[] => items.filter((item): item is MenuItem => item !== null);
        const menuItems: Array<MenuItem | null> = [
            hasPermission('dashboard.view') || hasPermission('reports.view')
                ? ({
                    label: 'Dashboard',
                    icon: 'pi pi-chart-bar',
                    expanded: normalizedPath === '/' || normalizedPath.startsWith('/reports/cost-by-compartment'),
                    items: compactItems([
                        hasPermission('dashboard.view')
                            ? {
                                  label: 'Visão Geral',
                                  icon: 'pi pi-home',
                                  routerLink: ['/']
                              }
                            : null,
                        hasPermission('reports.view')
                            ? {
                                  label: 'Custo',
                                  icon: 'pi pi-wallet',
                                  routerLink: ['/reports/cost-by-compartment']
                              }
                            : null
                    ])
                } satisfies MenuItem)
                : null,
            hasPermission('instances.view') ||
            hasPermission('groups.view') ||
            hasPermission('schedules.view') ||
            hasPermission('compartments.view')
                ? ({
                    label: 'Instâncias',
                    icon: 'pi pi-desktop',
                    expanded:
                        normalizedPath.startsWith('/instances') ||
                        normalizedPath.startsWith('/groups') ||
                        normalizedPath.startsWith('/schedules') ||
                        normalizedPath.startsWith('/compartiments'),
                    items: compactItems([
                        hasPermission('instances.view')
                            ? {
                                  label: 'Instâncias',
                                  icon: 'pi pi-server',
                                  routerLink: ['/instances']
                              }
                            : null,
                        hasPermission('groups.view')
                            ? {
                                  label: 'Grupos',
                                  icon: 'pi pi-objects-column',
                                  routerLink: ['/groups']
                              }
                            : null,
                        hasPermission('schedules.view')
                            ? {
                                  label: 'Agendamentos',
                                  icon: 'pi pi-calendar',
                                  routerLink: ['/schedules']
                              }
                            : null,
                        hasPermission('compartments.view')
                            ? {
                                  label: 'Compartimentos',
                                  icon: 'pi pi-sitemap',
                                  routerLink: ['/compartiments']
                              }
                            : null
                    ])
                } satisfies MenuItem)
                : null,
            hasPermission('deskmanager.view')
                ? ({
                    label: 'DeskManager',
                    icon: 'pi pi-ticket',
                    expanded: normalizedPath.startsWith('/deskmanager'),
                    items: compactItems([
                        hasPermission('deskmanager.create_ticket')
                            ? {
                                  label: 'Criar chamado',
                                  icon: 'pi pi-plus-circle',
                                  routerLink: ['/deskmanager/create-ticket']
                              }
                            : null
                    ])
                } satisfies MenuItem)
                : null,
            hasPermission('admin.view') || hasPermission('admin.users.view') || hasPermission('admin.access_groups.view') || hasPermission('admin.permissions.view')
                ? ({
                    label: 'Administração',
                    icon: 'pi pi-shield',
                    expanded: normalizedPath.startsWith('/admin'),
                    items: compactItems([
                        hasPermission('admin.users.view')
                            ? {
                                  label: 'Usuários',
                                  icon: 'pi pi-users',
                                  routerLink: ['/admin/users']
                              }
                            : null,
                        hasPermission('admin.access_groups.view')
                            ? {
                                  label: 'Grupos',
                                  icon: 'pi pi-id-card',
                                  routerLink: ['/admin/groups']
                              }
                            : null,
                        hasPermission('admin.permissions.view')
                            ? {
                                  label: 'Permissões Diretas',
                                  icon: 'pi pi-key',
                                  routerLink: ['/admin/permissions']
                              }
                            : null
                    ])
                } satisfies MenuItem)
                : null,
            hasPermission('audit.executions.view') || hasPermission('audit.access.view') || hasPermission('audit.settings.view')
                ? ({
                    label: 'Auditoria',
                    icon: 'pi pi-history',
                    expanded: normalizedPath.startsWith('/executions') || normalizedPath.startsWith('/audit'),
                    items: compactItems([
                        hasPermission('audit.executions.view')
                            ? {
                                  label: 'Execuções',
                                  icon: 'pi pi-list-check',
                                  routerLink: ['/executions']
                              }
                            : null,
                        hasPermission('audit.access.view')
                            ? {
                                  label: 'Acessos',
                                  icon: 'pi pi-sign-in',
                                  routerLink: ['/audit/access']
                              }
                            : null,
                        hasPermission('audit.settings.view')
                            ? {
                                  label: 'Configurações',
                                  icon: 'pi pi-cog',
                                  routerLink: ['/audit/configurations']
                              }
                            : null
                    ])
                } satisfies MenuItem)
                : null
        ];

        this.model = menuItems.filter((item): item is MenuItem => item !== null);
    }
}
