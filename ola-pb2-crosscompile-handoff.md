# Handoff: Cross-compiling OLA for PocketBeagle 2

## Goal
Get a current build of [OLA (Open Lighting Architecture)](https://github.com/OpenLightingProject/ola/) running on a PocketBeagle 2, without rebuilding the OS image.

## Target hardware / OS
- Board: BeagleBoard PocketBeagle 2, Rev A1 (TI **AM6254**, quad-core 64-bit ARM Cortex-A53, GPU present)
- RAM: 512 MB — this is why native on-board builds are painful (swap-thrashing, not CPU-bound)
- OS image: [PocketBeagle 2 Debian 13.6 2026-07-24 IoT (v6.18.x-k3)](https://www.beagleboard.org/distros/pocketbeagle-2-debian-13-6-2026-07-24-iot-v6-18-x-k3)
  - This is a **plain Debian 13 "trixie" arm64 userland** — nothing Yocto-specific about it as far as apt/dpkg and userspace builds are concerned. (meta-ti/Yocto is only relevant if you want to build a *custom OS image/BSP*, which is not the goal here — the current Debian base is fine and shouldn't need to be rebuilt.)
  - Image file referenced in other project docs: `pocketbeagle2-debian-13-base-v6.12-arm64-2025-09-05-8gb.img.xz` (verify against the actual 2026-07-24 image link above before use)

## Status / decisions so far
- On-board native compile attempt: aborted after 4h, too slow / likely RAM-starved (512 MB).
- Found that Debian/apt already ships an OLA package — but it's ~3 years old. A newer release is "in the pipeline" upstream but not out yet.
- **Current plan**: don't wait for the next release or rely on the stale packaged version.
  1. First, quickly test locally (on a normal dev machine, native, not cross) whether current OLA `master` from git builds cleanly. This is a fast sanity check before investing in cross-compile setup.
  2. If master builds cleanly → proceed to cross-compile for arm64/PocketBeagle 2.
  3. If master does *not* build cleanly → investigate/report upstream before spending time on cross-compile plumbing.

## Prior art
- User has done this kind of cross-compile before (~11 years ago), for a different board: https://github.com/s-light/acme_ola_crosscompile
- Forum thread where this was discussed: https://forum.beagleboard.org/t/how-to-temporary-disable-all-not-really-needed-things/44393/3
  - One reply suggested "PocketBeagle 2 is in meta-ti, a Yocto image is the best way to go." — Assessed as **not necessary** for this specific goal (cross-compiling one userspace package against an existing, working Debian rootfs). Yocto would mean rebuilding the whole OS image, which the user explicitly wants to avoid.

## Recommended cross-compile approach (once master build is confirmed clean)

### Option A — QEMU user-mode chroot against the real Debian release (recommended, matches prior approach)
1. On an x86_64 Linux host: `apt install qemu-user-static binfmt-support debootstrap`
2. Get an arm64 **trixie** rootfs — either:
   - `debootstrap --arch=arm64 trixie /srv/pb2-rootfs http://deb.debian.org/debian`, or
   - loop-mount the actual PocketBeagle 2 `.img` and chroot into its rootfs partition directly (closest to "use the image I already have")
3. Copy `/usr/bin/qemu-aarch64-static` into the rootfs; bind-mount `/proc /sys /dev`; `chroot` in.
4. Inside the chroot (now transparently running arm64 via qemu-user, but using host RAM/cores/disk):
   - `apt install` OLA build deps: build-essential, autoconf, automake, libtool, protobuf-compiler, libprotobuf-dev, libcppunit-dev, libusb-1.0-0-dev, libftdi1-dev, uuid-dev, libmicrohttpd-dev, bison, flex, python3, pkg-config (cross-check against OLA's actual `configure.ac`/README for the current master)
   - `git clone` OLA, `autoreconf -i`, `./configure`, `make -j$(nproc)`
5. Package the result as a `.deb` (via `dpkg-buildpackage` if OLA ships debian/ packaging, or `checkinstall`) for clean install/removal on the board, or `make install DESTDIR=` + rsync.

**Why this over on-device build:** identical package versions/ABI as the board (same Debian release), no manual sysroot/toolchain wrangling, full host RAM/cores — should turn a 4h+ (likely swap-bound) build into minutes.

### Option B — True cross-compilation via Debian multiarch (faster, more setup)
- `dpkg --add-architecture arm64` on the x86_64 host, install `crossbuild-essential-arm64` + `:arm64` dev packages side by side, `./configure --host=aarch64-linux-gnu`.
- No QEMU emulation, native compiler speed.
- More fragile: some autotools `AC_TRY_RUN` checks can't execute target binaries directly and may need manual cache variables or a qemu-based test runner.
- Worth trying only if Option A's build time is unsatisfying for repeated iteration.

### Watch-outs
- Match the `protoc` version used to generate code against the `libprotobuf` runtime version on the target — Option A avoids this automatically since apt versions match the board.
- OLA has USB (libusb/libftdi) and RDM-related dependencies — check current `configure.ac` / README for the exact list on current master, since it may have changed since older guides.

## Open questions for next session
- Result of the local `master` build test (clean or not — any errors?)
- Confirm exact current OLA dependency list against master's `configure.ac`
- Decide: debootstrap fresh rootfs vs. loop-mount the real board image for the chroot
