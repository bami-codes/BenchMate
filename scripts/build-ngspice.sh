#!/bin/sh
# Install the validated simulator into this checkout, without changing system tools.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
build="$root/.tools/ngspice-47-build"
prefix="$root/.tools/ngspice-47"
mkdir -p "$build"
cd "$build"
archive=ngspice-47.tar.gz
digest=894e649651f1838a14095e5a5439e7d3aa63e87ede14d283173fda4fcdef675f
if ! curl --fail --location --retry 2 "https://downloads.sourceforge.net/project/ngspice/ng-spice-rework/47/$archive" -o "$archive"; then
    curl --fail --location --retry 2 "https://downloads.sourceforge.net/project/ngspice/ng-spice-rework/old-releases/47/$archive" -o "$archive"
fi
python3 - "$archive" "$digest" <<'PY'
import hashlib, pathlib, sys
if hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest() != sys.argv[2]:
    raise SystemExit('ngspice source checksum mismatch')
PY
tar -xzf "$archive"
cd ngspice-47
./configure --prefix="$prefix" --without-x --with-readline=no --disable-xspice --disable-cider --disable-openmp
make -j2
make install
"$prefix/bin/ngspice" --version
