import { NextRequest, NextResponse } from 'next/server';

// Protected routes that require authentication
const PROTECTED_ROUTES = ['/dashboard', '/jobs', '/approvals', '/applications', '/profile', '/onboarding'];

// Public auth routes (should redirect to dashboard if already authenticated)
const AUTH_ROUTES = ['/login', '/register'];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Get access_token from cookies
  const token = request.cookies.get('access_token')?.value;

  // Check if current route is protected
  const isProtectedRoute = PROTECTED_ROUTES.some(route => pathname.startsWith(route));

  // Check if current route is an auth route
  const isAuthRoute = AUTH_ROUTES.some(route => pathname.startsWith(route));

  // If no token and trying to access protected route, redirect to login
  if (isProtectedRoute && !token) {
    return NextResponse.redirect(new URL('/login', request.url));
  }

  // If token exists and trying to access auth routes, redirect to dashboard
  if (isAuthRoute && token) {
    return NextResponse.redirect(new URL('/dashboard', request.url));
  }

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
    '/login/:path*',
    '/register/:path*',
  ],
};
