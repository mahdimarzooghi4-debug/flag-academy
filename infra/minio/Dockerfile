FROM golang:1.24-alpine AS build

RUN apk add --no-cache ca-certificates git build-base
ENV CGO_ENABLED=0
RUN GOBIN=/out go install github.com/minio/minio@latest

FROM alpine:3.22
RUN apk add --no-cache ca-certificates
COPY --from=build /out/minio /usr/local/bin/minio
ENTRYPOINT ["minio"]
CMD ["server", "/data", "--console-address", ":9001"]
