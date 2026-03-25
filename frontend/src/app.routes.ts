import { Routes } from '@angular/router';
import { AppLayout } from './app/layout/component/app.layout';
import { Dashboard } from './app/pages/dashboard/dashboard';
import { ExecutionsPage } from './app/pages/executions/executions';
import { InstancesPage } from './app/pages/instances/instances';
import { CostByCompartmentPage } from './app/pages/reports/cost-by-compartment';
import { SchedulesPage } from './app/pages/schedules/schedules';

export const appRoutes: Routes = [
    {
        path: '',
        component: AppLayout,
        children: [
            { path: '', component: Dashboard },
            { path: 'instances', component: InstancesPage },
            { path: 'schedules', component: SchedulesPage },
            { path: 'executions', component: ExecutionsPage },
            { path: 'reports/cost-by-compartment', component: CostByCompartmentPage }
        ]
    },
    { path: '**', redirectTo: '/' }
];
