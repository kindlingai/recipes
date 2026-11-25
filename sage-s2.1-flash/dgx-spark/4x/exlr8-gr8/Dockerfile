# Sage-S2.1-Flash on four GB10 boxes: gr8 (the gr8/ submodule) with only the engine this recipe runs, g6m4_flash-int4 at
# TP=4, plus the front end, the loader and the launcher. linux/arm64, CUDA 13, sm_121a. All four boxes run this image.
#
#   docker buildx build --platform linux/arm64 -t sage-4x-spark .      (compose.yaml builds it the same way)
#
# The stages are gr8's own Dockerfile cut down to one engine: gr8's builds every engine for every TP width, which takes
# far longer. Keep the two in step when the submodule moves (toolchain, Rust pin, XGrammar, runtime packages).
#
# ENGINE_SRC says where the binaries come from:
#   build  (the default) the stages below compile them from the gr8/ submodule
#   image  they are copied from GR8_IMAGE, gr8's published image of the same commit (ghcr.io/kindlingai/gr8@sha256:...),
#          and nothing compiles. Its g6m4_flash-int4 runs TP widths 1 to 4, with the same kernels at each width as a
#          one-width build. CI takes this path when gr8 publishes an image of the submodule's commit
#          (.github/workflows/image.yml)
# Either way the runtime stage gets the same files at the same paths, from the bins stage.
ARG CUDA_VERSION=13.0.1
ARG UBUNTU=ubuntu24.04
ARG ENGINE_SRC=build
# scratch stands in when ENGINE_SRC=build, which never reads it
ARG GR8_IMAGE=scratch

FROM nvidia/cuda:${CUDA_VERSION}-devel-${UBUNTU} AS toolchain
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
# hadolint ignore=DL3008
RUN apt-get update \
 && apt-get install -y --no-install-recommends g++ binutils libibverbs-dev ca-certificates curl \
 && rm -rf /var/lib/apt/lists/*

FROM toolchain AS rust
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
# gr8/frontend/g6front-rs/rust-toolchain.toml pins the compiler: keep RUST_VERSION equal to it
ARG RUST_VERSION=1.94.1
ENV RUSTUP_HOME=/opt/rustup CARGO_HOME=/opt/cargo PATH=/opt/cargo/bin:$PATH
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \
    | sh -s -- -y --no-modify-path --profile minimal --default-toolchain "$RUST_VERSION"
WORKDIR /src

FROM rust AS libs
COPY gr8/engine/knobs-rs engine/knobs-rs
COPY gr8/knobs knobs
COPY gr8/engine/loader-rs engine/loader-rs
COPY gr8/engine/Cargo.toml gr8/engine/Cargo.lock engine/
COPY gr8/engine/hostcore-rs engine/hostcore-rs
COPY gr8/engine/kvman-rs engine/kvman-rs
COPY gr8/engine/scheduler-rs engine/scheduler-rs
RUN mkdir -p /out \
 && cargo build --release --locked --manifest-path engine/loader-rs/Cargo.toml \
 && cargo build --release --locked --manifest-path engine/Cargo.toml \
 && cargo build --release --locked --features capi --manifest-path engine/knobs-rs/Cargo.toml \
 && cargo rustc --release --locked --features capi --lib --crate-type cdylib --manifest-path engine/knobs-rs/Cargo.toml \
 && cp engine/loader-rs/target/release/libg6load.a engine/loader-rs/target/release/g6load \
       engine/target/release/libg6host.a engine/target/release/kvman-remote \
       engine/knobs-rs/target/release/libgr8knobs.a engine/knobs-rs/target/release/libgr8knobs.so /out/ \
 && rm -rf engine/target engine/*/target

FROM rust AS front
# hadolint ignore=DL3008
RUN apt-get update \
 && apt-get install -y --no-install-recommends cmake clang libclang-dev \
 && rm -rf /var/lib/apt/lists/*
COPY gr8/engine/knobs-rs engine/knobs-rs
COPY gr8/knobs knobs
COPY gr8/frontend/g6front-rs frontend/g6front-rs
WORKDIR /src/frontend/g6front-rs
RUN mkdir -p /out \
 && cargo build --release --locked \
 && cp target/release/g6front-rs /out/ \
 && rm -rf target \
 && cp -a "$(ls -d /opt/cargo/registry/src/*/xgrammar-*/thirdparty/xgrammar | head -1)" /out-xgrammar

# XGrammar, for the engine's request grammars (gr8/engine/runtime/grammar.h): the sources the front end's crate pins
FROM toolchain AS xgrammar
# hadolint ignore=DL3008
RUN apt-get update \
 && apt-get install -y --no-install-recommends cmake \
 && rm -rf /var/lib/apt/lists/*
COPY gr8/engine/runtime/xgrammar_build.sh /xgrammar_build.sh
COPY --from=front /out-xgrammar /opt/xgrammar
RUN /xgrammar_build.sh /opt/xgrammar /xb && mkdir -p /out && cp /xb/libxgrammar.a /out/ && rm -rf /xb

# g6m4_flash-int4: Flash architecture with the 4-bit KV latent row, TP=4 only
FROM toolchain AS engine
WORKDIR /src
COPY gr8/engine engine
COPY gr8/tools/health/gpuprobe.cu tools/health/gpuprobe.cu
COPY gr8/scripts/build.sh scripts/build.sh
COPY --from=libs /out/libg6load.a engine/loader-rs/target/release/libg6load.a
COPY --from=libs /out/libg6host.a engine/target/release/libg6host.a
COPY --from=libs /out/libgr8knobs.a engine/knobs-rs/target/release/libgr8knobs.a
COPY --from=front /out-xgrammar /opt/xgrammar
COPY --from=xgrammar /out/libxgrammar.a /opt/xgrammar-lib/libxgrammar.a
ENV GR8_XGRAMMAR=/opt/xgrammar GR8_XGRAMMAR_LIB=/opt/xgrammar-lib/libxgrammar.a
# The compile cache (gr8/docs/BUILD-CACHE.md) is a cache mount, which CI keeps between runs (image.yml), so a
# rebuild compiles only what changed.
ENV GR8_NVCC_CACHE_DIR=/var/cache/gr8-nvcc
RUN --mount=type=cache,id=gr8-nvcc-flash-int4-w4,target=/var/cache/gr8-nvcc \
    touch "$GR8_NVCC_CACHE_DIR/.start" \
 && MODEL=flash KV_FORMAT=int4 GR8_WIDTHS=4 scripts/build.sh /out/bin \
 && if grep -qF 'touch -c "$C"' engine/runtime/nvcc_cache.sh; then \
      find "$GR8_NVCC_CACHE_DIR" -type f ! -newer "$GR8_NVCC_CACHE_DIR/.start" -delete; fi \
 && find /out/bin -mindepth 1 -maxdepth 1 ! -name g6m4_flash-int4 -exec rm -rf {} +

# The binaries the runtime stage copies, at the paths it copies them from: built above, or from gr8's image
FROM scratch AS bins-build
COPY --from=engine /out/bin/g6m4_flash-int4 /bin/
COPY --from=libs /out/g6load /out/kvman-remote /bin/
COPY --from=libs /out/libgr8knobs.so /bin/lib/
COPY --from=front /out/g6front-rs /bin/

FROM ${GR8_IMAGE} AS gr8-image

FROM scratch AS bins-image
COPY --from=gr8-image /opt/gr8/bin/g6m4_flash-int4 /opt/gr8/bin/g6load /opt/gr8/bin/kvman-remote /opt/gr8/bin/g6front-rs /bin/
COPY --from=gr8-image /opt/gr8/bin/lib/libgr8knobs.so /bin/lib/

FROM bins-${ENGINE_SRC} AS bins

FROM nvidia/cuda:${CUDA_VERSION}-runtime-${UBUNTU} AS runtime
# python3 for the launcher and the shim (python3-yaml for the KV store file), curl + jq for the smoke test.
# libibverbs1 and ibverbs-providers (libmlx5) for the ConnectX fabric between the four boxes.
# hadolint ignore=DL3008
RUN apt-get update \
 && apt-get install -y --no-install-recommends libibverbs1 ibverbs-providers python3 python3-yaml curl jq \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /opt/gr8
COPY gr8/ .
COPY --from=bins /bin/ bin/
COPY kv-store.yaml /etc/gr8/kv-store.yaml
COPY entrypoint.sh knobs.sh /opt/sage-4x/
COPY bin/gr8 /opt/sage-4x/bin/gr8
# The container runs as uid 1000 on a read-only image. Its writable state is three volumes (compose.yaml): the model
# cache, the prompt cache and GR8_WORK_DIR, which docker fills from these empty, uid-1000 directories on first use.
RUN mkdir -p /var/lib/gr8/home /var/lib/gr8/cache /var/lib/gr8/prompts \
 && chown 1000:1000 /var/lib/gr8/home /var/lib/gr8/cache /var/lib/gr8/prompts
ENV PATH=/opt/sage-4x/bin:/opt/gr8/bin:$PATH PYTHONPATH=/opt/gr8/frontend HOME=/tmp GR8_CONTAINER=1 GR8_MODEL=glm53f \
    GR8_WORK_DIR=/var/lib/gr8/home MODEL_CACHE=/var/lib/gr8/cache PY=/usr/bin/python3 FRONT_BIN=/opt/gr8/bin/g6front-rs
# The recipe's knobs (README.md, "Knobs"). Set any of them in .env, or with docker run -e, to override.
#   TUNE           speed, context or quality: sets VARIANT, SESS, CAP, MAX_MODEL_LEN, MTP and S2_SHARED_WATERFILL
#                  unless set (knobs.sh), plus context-parallel KV for context
#   CAP            the KV pool in tokens, shared by the sessions: 262,208 for speed/quality, 2,097,152 for context
#   MAX_MODEL_LEN  the longest single request, prompt and output together: 262,144, or 1,048,576 for context
#   SESS           the requests that decode at once: 8
#   VARIANT        the release's width manifest: k4
#   DFLASH         0 by default (MTP only; no drafter configured by default)
#   MENTAT         0: the four boxes in PEERS; 1: find each other through mentat (knobs.sh)
#   EXTRA_ENV      engine variables; text-only by default (GR8_GLM53F_VISION=1 opts into untested vision weights)
ENV TUNE=speed DFLASH=0 MENTAT=0
# The rest of the recipe, as gr8's launcher options (gr8/KNOBS.md)
#   MODEL: pinned to a fixed Hugging Face commit. The model cache is keyed by commit, so a new commit on the repo
#   changes nothing until MODEL moves. The fetch hard-links unchanged files from a cached commit.
# PEERS (and IPS, IPS2, or SHAPE=ring) have no default: they name the four boxes (knobs.sh, .env.example).
ENV TP=4 GROUP=gr8-sage-4x KV_FORMAT=int4 FLASH_CACHE=aligned KV_STORE=@/etc/gr8/kv-store.yaml \
    MODEL=https://huggingface.co/kindlingai/sage-s2.1-flash-exlr8-k4@e55da4682c090821efcac7f5fb85622cb06d1c54
# A request with no max_tokens gets 32,768 (or the room the context leaves, if less).
# A call to a tool the request did not declare comes back as a tool call so an agent can answer with an unknown-tool error.
ENV DEFAULT_MAX_TOKENS=32768 UNDECLARED_TOOL_CALLS=emit
USER 1000:1000
ENTRYPOINT ["/opt/sage-4x/entrypoint.sh"]
