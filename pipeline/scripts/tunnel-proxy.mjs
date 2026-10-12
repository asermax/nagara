// usage: node scripts/tunnel-proxy.mjs [listen-port] [dev-server-port]
//
// Cloudflare's edge answers every /cdn-cgi/ path on a quick tunnel itself, so the tunnel carries
// /s3/<bucket>/<key> and this restores the local S3 endpoint's path and the localhost host the PUT
// URL was signed for. Every other path passes through unchanged.
import http from "node:http";

const [listen = 8792, target = 5173] = process.argv.slice(2).map(Number);

http
  .createServer((request, response) => {
    const path = request.url.startsWith("/s3/")
      ? `/cdn-cgi/local/r2/s3/${request.url.slice("/s3/".length)}`
      : request.url;
    const upstream = http.request(
      {
        host: "localhost",
        port: target,
        method: request.method,
        path,
        headers: { ...request.headers, host: `localhost:${target}` },
      },
      (answer) => {
        response.writeHead(answer.statusCode, answer.headers);
        answer.pipe(response);
      },
    );

    upstream.on("error", (error) => {
      response.writeHead(502);
      response.end(String(error));
    });
    request.pipe(upstream);
  })
  .listen(listen, "127.0.0.1", () => {
    console.log(`tunnel proxy on http://127.0.0.1:${listen} -> http://localhost:${target}`);
  });
