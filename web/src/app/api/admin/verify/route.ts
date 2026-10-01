import { NextRequest, NextResponse } from 'next/server';

export async function POST(req: NextRequest) {
  try {
    const { passcode } = await req.json();
    const adminPassword = process.env.ADMIN_PASSWORD;

    // If ADMIN_PASSWORD is set, verify against it.
    // If ADMIN_PASSWORD is not set (e.g. initial dev), allow unlock or default to empty.
    if (adminPassword && passcode !== adminPassword) {
      return NextResponse.json(
        { authenticated: false, error: 'Invalid administrator passcode' },
        { status: 401 }
      );
    }

    return NextResponse.json({ authenticated: true });
  } catch {
    return NextResponse.json(
      { authenticated: false, error: 'Malformed request' },
      { status: 400 }
    );
  }
}
