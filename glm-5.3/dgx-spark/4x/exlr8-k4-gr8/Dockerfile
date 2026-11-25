# GLM-5.3 on four GB10 boxes at K4: gr8 (the gr8/ submodule) with only the engine this recipe runs, g6m4-int4 at TP=4,
# plus the front end, the loader and the launcher. linux/arm64, CUDA 13, sm_121a.
#
#   docker buildx build --platform linux/arm64 -t glm53-k4-4x-spark .      (compose.yaml builds it the same way)
#
# The stages are gr8's own Dockerfile cut down to one engine: gr8's builds every engine for every TP width, which takes
# far longer. Keep the two in step when the submodule moves (toolchain, Rust pin, XGrammar, runtime packages).
#
# ENGINE_SRC says where the binaries come from:
#   build  (the default) the stages below compile them from the gr8/ submodule
#   image  they are copied from GR8_IMAGE, gr8's published image of the same commit (ghcr.io/kindlingai/gr8@sha256:...),
#          and nothing compiles. CI takes this path when gr8 publishes an image of the submodule's commit
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

# g6m4-int4: GLM-5.3 with the 4-bit KV latent row (gr8's default KV format at TP=4), TP=4 only
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
RUN --mount=type=cache,id=gr8-nvcc-glm-int4-w4,target=/var/cache/gr8-nvcc \
    touch "$GR8_NVCC_CACHE_DIR/.start" \
 && KV_FORMAT=int4 GR8_WIDTHS=4 GR8_TESTS=0 scripts/build.sh /out/bin \
 && if grep -qF 'touch -c "$C"' engine/runtime/nvcc_cache.sh; then \
      find "$GR8_NVCC_CACHE_DIR" -type f ! -newer "$GR8_NVCC_CACHE_DIR/.start" -delete; fi \
 && find /out/bin -mindepth 1 -maxdepth 1 ! -name g6m4-int4 -exec rm -rf {} +

# The binaries the runtime stage copies, at the paths it copies them from: built above, or from gr8's image
FROM scratch AS bins-build
COPY --from=engine /out/bin/g6m4-int4 /bin/
COPY --from=libs /out/g6load /out/kvman-remote /bin/
COPY --from=libs /out/libgr8knobs.so /bin/lib/
COPY --from=front /out/g6front-rs /bin/

FROM ${GR8_IMAGE} AS gr8-image

FROM scratch AS bins-image
COPY --from=gr8-image /opt/gr8/bin/g6m4-int4 /opt/gr8/bin/g6load /opt/gr8/bin/kvman-remote /opt/gr8/bin/g6front-rs /bin/
COPY --from=gr8-image /opt/gr8/bin/lib/libgr8knobs.so /bin/lib/

FROM bins-${ENGINE_SRC} AS bins

FROM nvidia/cuda:${CUDA_VERSION}-runtime-${UBUNTU} AS runtime
# python3 for the launcher and the shim, curl + jq for the smoke test, libibverbs for the RoCE fabric between the boxes
# hadolint ignore=DL3008
RUN apt-get update \
 && apt-get install -y --no-install-recommends libibverbs1 ibverbs-providers python3 python3-yaml curl jq \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /opt/gr8
COPY gr8/ .
COPY --from=bins /bin/ bin/
COPY manifests/exlr8-manifest-bit387.json /etc/gr8/exlr8-manifest-bit387.json
# The container runs as uid 1000 on a read-only image. Its writable state is two volumes (compose.yaml): the model cache
# and GR8_WORK_DIR, which docker fills from these empty, uid-1000 directories on first use.
RUN mkdir -p /var/lib/gr8/home /var/lib/gr8/cache \
 && chown 1000:1000 /var/lib/gr8/home /var/lib/gr8/cache
ENV PATH=/opt/gr8/bin:$PATH PYTHONPATH=/opt/gr8/frontend HOME=/tmp GR8_CONTAINER=1 GR8_MODEL=glm53 \
    GR8_WORK_DIR=/var/lib/gr8/home MODEL_CACHE=/var/lib/gr8/cache PY=/usr/bin/python3 FRONT_BIN=/opt/gr8/bin/g6front-rs
# The recipe: four boxes, the release's bit387 profile, pinned to a Hugging Face commit (the model cache is keyed by
# commit, so a new commit on the repo changes nothing until MODEL moves). bit387 is every routed expert at K4 but the
# gate, up and down of layers 3-12 at K3 (layer 78, the MTP layer, is stored at K3 only). Its KL against BF16 is
# statistically identical to all-K4 bit400 (0.0385 against 0.0381 on model-written text, 1.5 SE) in 12 GB less. The
# recipe carries a copy of the release's manifest (manifests/exlr8-manifest-bit387.json) and boots it by path. Every
# other option is gr8's launcher default (gr8/KNOBS.md); set one in .env to change it.
# DISPRAM=1: the 2 GiB display carveout of each box, lent by Kindling OS's dispramd (compose.yaml mounts its socket),
# holds attention KV; without dispramd the engine allocates as usual.
# The K4 experts leave no room for gr8's TP=4 decode graphs and a KV pool, so the recipe trades some decode speed for
# memory. DEC_BK=16384 with DEC_BK_MAX=32768 captures the step graphs for three context sizes (16K, 32K and the cap)
# in place of eight, about 1.4 GiB a box each. S2_ADAPT=0 fixes the MTP draft count, which drops the graphs for the
# other counts. The launcher sizes the KV pool for the release's default widths, which leaves the K4 boxes no memory,
# so the recipe sets it. Every box holds a copy of each session's first SHARE_LIMIT tokens and a quarter of the rest.
# SHARE_LIMIT=16384 lets four sessions of about 74K tokens share the pool without evicting each other's cached
# prefixes. CAP=442368 is the longest one session can be: 1,920 pages of 64 tokens on each box, about 2.5 GiB free
# while it serves.
# This K4 recipe prioritizes exactness: gr8 v1.1.0 enables eight bit-exact decode/prefill/DFlash2 kernels (KL=0) and
# defaults MOE_UNION_CAP=48 at TP=4; we explicitly set MOE_UNION_CAP=0 here so K4 stays 100% uncapped/lossless.
# .env.example also sets DEC_BK=2048 DEC_BK_MAX=2048 for extra memory headroom (about 4.3 GiB free after boot).
ENV TP=4 VARIANT=/etc/gr8/exlr8-manifest-bit387.json DISPRAM=1 DEC_BK=16384 DEC_BK_MAX=32768 S2_ADAPT=0 CAP=442368 \
    SHARE_LIMIT=16384 MOE_UNION_CAP=0 \
    MODEL=https://huggingface.co/kindlingai/glm-5.3-exlr8-k2-k3-k4@9e25c28a2e8808d8b2599d780521fd6af24e7558
USER 1000:1000
ENTRYPOINT ["/opt/gr8/docker/entrypoint.sh"]
