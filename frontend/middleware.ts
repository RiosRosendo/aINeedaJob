import { NextRequest, NextResponse } from 'next/server';

// Protected routes that require authentication
const PROTECTED_ROUTES = ['/dashboard', '/jobs', '/approvals', '/applications', '/profile', '/onboarding'];

// Public auth routes (should redirect to dashboard if already authenticated)
const AUTH_ROUTES = ['/auth', '/login', '/register'];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Get access_token from cookies
  const token = request.cookies.get('access_token')?.value;

  // Check if current route is protected
  const isProtectedRoute = PROTECTED_ROUTES.some(route => pathname.startsWith(route));

  // Check if current route is an auth route
  const isAuthRoute = AUTH_ROUTES.some(route => pathname.startsWith(route));

  // If no token and trying to access protected route, redirect to auth
  if (isProtectedRoute && !token) {
    return NextResponse.redirect(new URL('/auth', request.url));
  }

  // Let all routes through - client-side will handle redirects for authenticated users on /auth
  return NextResponse.next();
}

// Configure which routes to apply middleware to
export const config = {
  matcher: [
    // Protected routes
    '/dashboard/:path*',
    '/jobs/:path*',
    '/approvals/:path*',
    '/applications/:path*',
    '/profile/:path*',
    '/onboarding/:path*',
    // Auth routes
    '/auth',
    '/auth/:path*',
    '/login',
    '/login/:path*',
    '/register',
    '/register/:path*',
  ],
};
