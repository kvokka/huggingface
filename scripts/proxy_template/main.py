import importlib
import os

httpx = importlib.import_module("httpx")
fastapi = importlib.import_module("fastapi")
fastapi_cors = importlib.import_module("fastapi.middleware.cors")
fastapi_responses = importlib.import_module("fastapi.responses")

FastAPI = fastapi.FastAPI
Request = fastapi.Request
Response = fastapi.Response
CORSMiddleware = fastapi_cors.CORSMiddleware
StreamingResponse = fastapi_responses.StreamingResponse

TARGET_URL = os.environ.get("TARGET_URL", "http://localhost:8000")
HF_TOKEN = os.environ.get("HF_TOKEN", "").strip()

allow_origins_raw = os.environ.get("ALLOW_ORIGINS", "*").strip()
ALLOW_ORIGINS = (
    ["*"]
    if allow_origins_raw == "*"
    else [o.strip() for o in allow_origins_raw.split(",") if o.strip()]
)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = httpx.AsyncClient(base_url=TARGET_URL, timeout=60.0, follow_redirects=True)


@app.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
)
async def proxy(request, path: str):
    if request.method == "OPTIONS":
        return Response(status_code=200)

    url = httpx.URL(path=request.url.path, query=request.url.query.encode("utf-8"))

    headers: dict[str, str] = {}
    for k, v in request.headers.items():
        lk = k.lower()
        if lk in {"host", "connection", "content-length", "accept-encoding"}:
            continue
        if lk == "authorization":
            headers["x-forwarded-authorization"] = v
            continue
        headers[k] = v

    if HF_TOKEN:
        headers["Authorization"] = f"Bearer {HF_TOKEN}"
    elif request.headers.get("authorization"):
        headers["Authorization"] = request.headers["authorization"]

    body = await request.body()

    upstream_request = client.build_request(
        method=request.method,
        url=url,
        headers=headers,
        content=body,
    )

    try:
        upstream_response = await client.send(upstream_request, stream=True)
    except httpx.RequestError as exc:
        return Response(content=f"Proxy error: {exc}", status_code=502)

    response_headers = {
        k: v
        for k, v in upstream_response.headers.items()
        if k.lower()
        not in {"content-encoding", "transfer-encoding", "content-length", "connection"}
    }

    return StreamingResponse(
        upstream_response.aiter_raw(),
        status_code=upstream_response.status_code,
        headers=response_headers,
        background=upstream_response.aclose,
    )
