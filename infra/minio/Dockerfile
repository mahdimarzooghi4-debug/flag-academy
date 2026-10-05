FROM golang:1.24.8-alpine AS build

ARG MINIO_VERSION=RELEASE.2025-10-15T17-29-55Z

RUN apk add --no-cache ca-certificates git build-base
ENV CGO_ENABLED=0

RUN set -eux; \
    for attempt in 1 2 3; do \
      GODEBUG=http2client=0 GOBIN=/out go install "github.com/minio/minio@${MINIO_VERSION}" && exit 0; \
      if [ "$attempt" -eq 3 ]; then exit 1; fi; \
      sleep "$((attempt * 5))"; \
    done

FROM alpine:3.22
RUN apk add --no-cache ca-certificates
COPY --from=build /out/minio /usr/local/bin/minio
ENTRYPOINT ["minio"]
CMD ["server", "/data", "--console-address", ":9001"]
