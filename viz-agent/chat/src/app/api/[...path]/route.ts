const BACKEND_API_URL =
  process.env.BACKEND_API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://127.0.0.1:8000";

type RouteContext = {
  params: {
    path: string[];
  };
};

async function proxy(request: Request, context: RouteContext) {
  const path = context.params.path.join("/");
  const incomingUrl = new URL(request.url);
  const backendUrl = new URL(`/${path}${incomingUrl.search}`, BACKEND_API_URL);

  const headers = new Headers(request.headers);
  headers.delete("host");

  const response = await fetch(backendUrl, {
    method: request.method,
    headers,
    body: ["GET", "HEAD"].includes(request.method) ? undefined : await request.arrayBuffer(),
    cache: "no-store",
  });

  const responseHeaders = new Headers(response.headers);
  responseHeaders.delete("content-encoding");
  responseHeaders.delete("content-length");

  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: responseHeaders,
  });
}

export async function GET(request: Request, context: RouteContext) {
  return proxy(request, context);
}

export async function POST(request: Request, context: RouteContext) {
  return proxy(request, context);
}
