# Saved fixture media API — step 1.12

The local API serves saved fixture results by job ID and media kind:

```text
GET /jobs/{job_id}/artifacts/{kind}
GET /jobs/{job_id}/artifacts/{kind}?download=true
```

`job_id` must be a positive signed 64-bit integer. `kind` is `image`, `audio`,
or `video`. The optional boolean `download` defaults to false; unknown query
fields, including `path`, are rejected. The result is raw media with a fixed
MIME type (`image/png`, `audio/wav`, or `video/mp4`). `Content-Disposition`
is `inline` by default or `attachment` for downloads, with a safe filename
such as `job-1-video.mp4`. Responses use `X-Content-Type-Options: nosniff`
and `Cache-Control: private, no-store`.

After Generate sample completes, use its job ID. For example, for job 1:

```bash
curl --fail 'http://127.0.0.1:8000/jobs/1/artifacts/video?download=true' \
  --output /tmp/job-1-video.mp4
```

| Status | Meaning |
| --- | --- |
| 200 | The saved media bytes, verified against the stored SHA-256 hash |
| 404 | Unknown job, no saved result yet, or an error outcome with no media |
| 422 | Invalid job ID, kind, boolean, or unexpected query field |
| 409 | Disallowed saved path/symlink, non-regular/empty/oversized file, or hash mismatch |
| 410 | A saved fixture file or its directory is missing |
| 500 | Stored result JSON/schema is corrupt; same handling as the result endpoint |
| 503 | The saved file cannot currently be read, for example a permission error |

Media errors have fixed Bangla messages without filesystem paths. Other database
failures retain the existing API's server-error handling. A completed legacy demo
job may have no outcome and therefore returns 404. An error outcome never causes
a fixture fallback. Saved result metadata remains available from
`GET /jobs/{job_id}/result` even when its file has disappeared.

The allowlist contains only the default fixture provider's `sample_image.png`,
`silent_audio.wav`, and `sample_video.mp4` under `tests/fixtures`. Both the kind
and exact saved path must match. Directory-relative Linux opens reject symlinks;
regular-file checks and a 16 MiB read limit avoid unbounded reads. The response
uses the same byte snapshot whose hash was checked. A later file replacement
cannot substitute content between validation and response delivery.

Reads do not invoke a provider, tick, retry, cancel, create jobs, or change saved
outcomes/media. As with existing result reads, repository construction applies
outstanding database migrations. Files remain shared fixtures; they are not copied
into each job and must still exist at their saved location after restart.

This is the owner-only local API and has no new authentication/public deployment
support. Alternate `FakeConfig.fixture_dir` paths used by isolated provider tests
are not production serving roots. Real provider storage will need a separate
allowlist/ownership contract before integration. Tiny sample files use full HTTP
200 responses, including for Range requests; partial streaming is not implemented.
The browser preview/download integration added in step 1.13 reads these responses
into temporary blob URLs; see the [web usage notes](../apps/web/README.md#sample-generation-and-media).

Validation and current status: [artifact API checkpoint](artifact-api-checkpoint.md)
and [build ledger](current-build-status.md).
