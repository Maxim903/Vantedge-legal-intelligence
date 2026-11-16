import { NextResponse, type NextRequest } from "next/server";
import { updateSession } from "@/lib/supabase/update-session";

export async function proxy(request: NextRequest) {
  if (
    ["/mentions-legales", "/cgu", "/confidentialite"].includes(
      request.nextUrl.pathname,
    )
  ) {
    return NextResponse.next();
  }
  return updateSession(request);
}

export const config = {
  matcher: [
    "/((?!api/stripe/webhook|_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
