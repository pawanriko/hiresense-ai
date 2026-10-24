import { NextResponse } from "next/server";
import { auth } from "@/auth";

// Protect the app areas; landing page and login stay public.
// Unauthenticated visitors are redirected to /login.
export default auth((req) => {
  if (!req.auth) {
    const loginUrl = new URL("/login", req.nextUrl.origin);
    loginUrl.searchParams.set("callbackUrl", req.nextUrl.pathname);
    return NextResponse.redirect(loginUrl);
  }
  return NextResponse.next();
});

export const config = {
  matcher: ["/dashboard/:path*", "/resume-lab/:path*", "/jd-match/:path*", "/interview/:path*"],
};
