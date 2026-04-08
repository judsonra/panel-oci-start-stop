import { Routes } from '@angular/router';
import { authGuard, localAccessGuard, permissionGuard } from './app/core/auth.guards';
import { AppLayout } from './app/layout/component/app.layout';
import { AdminAccessGroupsPage } from './app/pages/admin/access-groups';
import { AdminDirectPermissionsPage } from './app/pages/admin/direct-permissions';
import { AdminUsersPage } from './app/pages/admin/users';
import { AuditAccessPage } from './app/pages/audit/access-log';
import { AuditConfigurationPage } from './app/pages/audit/configuration-log';
import { AccessPage } from './app/pages/auth/access';
import { AuthCallbackPage } from './app/pages/auth/callback';
import { CompartmentsPage } from './app/pages/compartments/compartments';
import { Dashboard } from './app/pages/dashboard/dashboard';
import { DeskManagerCreateTicketPage } from './app/pages/deskmanager/create-ticket';
import { ExecutionsPage } from './app/pages/executions/executions';
import { GroupFormPage } from './app/pages/groups/group-form';
import { GroupsPage } from './app/pages/groups/groups';
import { InstancesPage } from './app/pages/instances/instances';
import { NotFoundPage } from './app/pages/errors/not-found';
import { CostByCompartmentPage } from './app/pages/reports/cost-by-compartment';
import { SchedulesPage } from './app/pages/schedules/schedules';

export const appRoutes: Routes = [
    {
        path: 'access',
        component: AccessPage,
        canActivate: [localAccessGuard]
    },
    {
        path: 'auth/callback',
        component: AuthCallbackPage
    },
    {
        path: '404',
        component: NotFoundPage
    },
    {
        path: '',
        component: AppLayout,
        canActivate: [authGuard],
        children: [
            { path: '', component: Dashboard },
            {
                path: 'deskmanager/create-ticket',
                component: DeskManagerCreateTicketPage,
                canActivate: [permissionGuard],
                data: { permission: 'deskmanager.create_ticket' }
            },
            {
                path: 'instances',
                component: InstancesPage,
                canActivate: [permissionGuard],
                data: { permission: 'instances.view' }
            },
            {
                path: 'groups',
                component: GroupsPage,
                canActivate: [permissionGuard],
                data: { permission: 'groups.view' }
            },
            {
                path: 'groups/new',
                component: GroupFormPage,
                canActivate: [permissionGuard],
                data: { permission: 'groups.manage' }
            },
            {
                path: 'groups/:groupId/edit',
                component: GroupFormPage,
                canActivate: [permissionGuard],
                data: { permission: 'groups.manage' }
            },
            {
                path: 'schedules',
                component: SchedulesPage,
                canActivate: [permissionGuard],
                data: { permission: 'schedules.view' }
            },
            {
                path: 'compartiments',
                component: CompartmentsPage,
                canActivate: [permissionGuard],
                data: { permission: 'compartments.view' }
            },
            {
                path: 'executions',
                component: ExecutionsPage,
                canActivate: [permissionGuard],
                data: { permission: 'audit.executions.view' }
            },
            {
                path: 'audit/access',
                component: AuditAccessPage,
                canActivate: [permissionGuard],
                data: { permission: 'audit.access.view' }
            },
            {
                path: 'audit/configurations',
                component: AuditConfigurationPage,
                canActivate: [permissionGuard],
                data: { permission: 'audit.settings.view' }
            },
            {
                path: 'admin/users',
                component: AdminUsersPage,
                canActivate: [permissionGuard],
                data: { permission: 'admin.users.view' }
            },
            {
                path: 'admin/groups',
                component: AdminAccessGroupsPage,
                canActivate: [permissionGuard],
                data: { permission: 'admin.access_groups.view' }
            },
            {
                path: 'admin/permissions',
                component: AdminDirectPermissionsPage,
                canActivate: [permissionGuard],
                data: { permission: 'admin.permissions.view' }
            },
            {
                path: 'reports/cost-by-compartment',
                component: CostByCompartmentPage,
                canActivate: [permissionGuard],
                data: { permission: 'reports.view' }
            }
        ]
    },
    { path: '**', redirectTo: '/404' }
];
