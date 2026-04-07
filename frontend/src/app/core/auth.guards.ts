import { inject } from '@angular/core';
import { CanActivateFn, Router, ActivatedRouteSnapshot, RouterStateSnapshot } from '@angular/router';
import { AuthService } from './auth.service';

export const authGuard: CanActivateFn = async (_route: ActivatedRouteSnapshot, state: RouterStateSnapshot) => {
    const auth = inject(AuthService);
    return auth.ensureAuthenticated(state.url);
};

export const localAccessGuard: CanActivateFn = async () => {
    const auth = inject(AuthService);
    return auth.ensureLocalAccessPage();
};

export const permissionGuard: CanActivateFn = async (route: ActivatedRouteSnapshot) => {
    const auth = inject(AuthService);
    const router = inject(Router);
    const permission = route.data['permission'] as string | undefined;
    const isAllowed = await auth.ensureAuthenticated(route.routeConfig?.path ? `/${route.routeConfig.path}` : '/');
    if (!isAllowed) {
        return false;
    }
    if (!permission || auth.hasPermission(permission)) {
        return true;
    }
    return router.parseUrl('/');
};
