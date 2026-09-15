#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Package the already-built 4.3.1.4 application using the upstream Linux layout.
set -euo pipefail

target=$(realpath "${1:?Usage: package-uniq-deb.sh application/target output.deb}")
output=$(realpath -m "${2:?Output .deb path required}")
version=4.3.1.4
jar="$target/thingsboard-$version-boot.jar"
for required in "$jar" "$target/conf/thingsboard.conf" "$target/conf/thingsboard.yml" \
  "$target/control/template.service" "$target/bin/install/install.sh"; do
  test -s "$required" || { echo "Missing build output: $required" >&2; exit 1; }
done
command -v dpkg-deb >/dev/null
stage=$(mktemp -d /tmp/uniq-deb.XXXXXXXX)
base="$stage/usr/share/thingsboard"
mkdir -p "$base/bin/install" "$base/conf" "$base/data" "$base/extensions" \
  "$stage/DEBIAN" "$stage/etc/thingsboard" "$stage/lib/systemd/system"

install -m 0500 "$jar" "$base/bin/thingsboard.jar"
cp -a "$target/conf/." "$base/conf/"
cp -a "$target/data/." "$base/data/"
if [ -d "$target/extensions" ]; then cp -a "$target/extensions/." "$base/extensions/"; fi
for script in install.sh upgrade.sh; do
  install -m 0775 "$target/bin/install/$script" "$base/bin/install/$script"
done
install -m 0644 "$target/bin/install/logback.xml" "$base/bin/install/logback.xml"
install -m 0644 "$target/control/template.service" "$stage/lib/systemd/system/thingsboard.service"
for script in preinst postinst prerm postrm; do
  install -m 0755 "$target/control/deb/$script" "$stage/DEBIAN/$script"
  sed -i 's/\r$//' "$stage/DEBIAN/$script"
  sh -n "$stage/DEBIAN/$script"
done
# Windows-created source archives can contain CRLF. Normalize Linux text only.
find "$base/conf" "$base/bin/install" -type f -exec sed -i 's/\r$//' {} +
sed -i 's/\r$//' "$stage/lib/systemd/system/thingsboard.service"
sed -i 's/@pkg.platform@/deb/g' "$base/conf/thingsboard.conf"
if grep -RE '\$\{pkg\.|@pkg\.' "$base/conf" "$stage/DEBIAN" "$stage/lib/systemd/system"; then
  echo 'Unresolved Maven packaging tokens; build application resources first.' >&2
  exit 1
fi
find "$stage" -type d -exec chmod 0755 {} +
find "$base/conf" "$base/data" -type f -exec chmod 0754 {} +
ln -s /usr/share/thingsboard/conf/thingsboard.yml "$base/bin/thingsboard.yml"
ln -s /usr/share/thingsboard/conf "$stage/etc/thingsboard/conf"

cat > "$stage/DEBIAN/control" <<'CONTROL'
Package: thingsboard
Version: 4.3.1.4-1
Section: misc
Priority: optional
Architecture: all
Maintainer: UNIQ
Depends: adduser, openjdk-17-jre | java17-runtime | oracle-java17-installer | openjdk-17-jre-headless | openjdk-21-jre | java21-runtime | oracle-java21-installer | openjdk-21-jre-headless | openjdk-25-jre | java25-runtime | oracle-java25-installer | openjdk-25-jre-headless
Description: UNIQ IoT platform based on ThingsBoard Community Edition 4.3.1.4
 Custom UNIQ interface with the upstream server, service scripts and database code.
CONTROL
# Match CONFIG/NOREPLACE for the upstream configuration and bundled data files.
(cd "$stage"; find usr/share/thingsboard/conf usr/share/thingsboard/data -type f \
  | LC_ALL=C sort | sed 's|^|/|') > "$stage/DEBIAN/conffiles"
(cd "$stage"; find usr lib etc -type f -print0 | LC_ALL=C sort -z \
  | xargs -0 md5sum) > "$stage/DEBIAN/md5sums"
chmod 0644 "$stage/DEBIAN/control" "$stage/DEBIAN/conffiles" "$stage/DEBIAN/md5sums"
mkdir -p "$(dirname "$output")"
dpkg-deb --root-owner-group -Zgzip --build "$stage" "$output"
dpkg-deb -f "$output" Package Version Architecture
echo "Staging directory retained for inspection: $stage"
