#!/usr/bin/env bash
# ==============================================================================
# UNIQ Smart Home Hub — Automated One-Click Updater (via curl)
# ==============================================================================
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${CYAN}======================================================${NC}"
echo -e "${BLUE}  ⚡ UNIQ Smart Home Hub — Updating to Latest Build... ${NC}"
echo -e "${CYAN}======================================================${NC}"

# Target destination
DEST="/opt/uniq-gateway"
if [ ! -d "$DEST" ]; then
    echo -e "${YELLOW}⚠️ Destination directory $DEST not found, creating it...${NC}"
    mkdir -p "$DEST"
fi

BASE_URL="https://raw.githubusercontent.com/Darkstar94s/uniq_thingsboard/bftech/uniq-4.3.1.4/uniq-gateway"

# Ensure subdirectories exist
mkdir -p "$DEST/connectors"
mkdir -p "$DEST/matter/web"

# List of files to update
FILES=(
    "uniq_gateway.py"
    "connectors/matter_connector.py"
    "matter/commission_service.py"
    "matter/device_mapper.py"
    "matter/web/index.html"
    "matter/web/uniq-logo-dark.png"
    "matter/web/uniq-logo-light.png"
    "matter/web/uniq-logo.png"
)

# Download each file directly
for file in "${FILES[@]}"; do
    echo -e "📥 Downloading ${YELLOW}$file${NC}..."
    mkdir -p "$(dirname "$DEST/$file")"
    if curl -fsSL --connect-timeout 15 "$BASE_URL/$file" -o "$DEST/$file"; then
        echo -e "   ${GREEN}✔ Updated $file${NC}"
    else
        echo -e "   ${RED}✖ Failed to download $file${NC}"
        exit 1
    fi
done

# Restart systemd service
echo -e "\n${BLUE}🔄 Restarting uniq-gateway service...${NC}"
if systemctl is-active --quiet uniq-gateway 2>/dev/null; then
    systemctl restart uniq-gateway
    echo -e "${GREEN}✔ Service uniq-gateway restarted successfully!${NC}"
elif systemctl list-unit-files | grep -q "uniq-gateway.service"; then
    systemctl restart uniq-gateway || systemctl start uniq-gateway
    echo -e "${GREEN}✔ Service uniq-gateway started successfully!${NC}"
else
    echo -e "${YELLOW}⚠️ Service uniq-gateway is not registered as systemd unit. Please restart manually if running in screen/tmux.${NC}"
fi

echo -e "\n${GREEN}======================================================${NC}"
echo -e "${GREEN}  🎉 UNIQ Hub Updated Successfully!                   ${NC}"
echo -e "${GREEN}======================================================${NC}"
echo -e "🌐 Web Dashboard: ${CYAN}http://localhost:8282${NC} (or your Pi IP)"
echo -e "🔑 Default PIN:    ${YELLOW}849201${NC}"
echo -e "🌓 Features:       Light & Dark Mode, Interactive Floorplan,"
echo -e "                   Rooms, Scenarios, Device Renaming & Cloud Sync"
echo -e "======================================================\n"
