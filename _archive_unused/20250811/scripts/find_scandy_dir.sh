#!/bin/bash

#####################################################################
# Finde Scandy-Verzeichnis
# Sucht nach dem richtigen Scandy-Verzeichnis
#####################################################################

set -e

# Farben für bessere Lesbarkeit
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo "Suche nach Scandy-Verzeichnissen..."

# Mögliche Verzeichnisse
POSSIBLE_DIRS=(
    "/Scandy2"
    "/scandy2"
    "/Scandy"
    "/scandy"
    "/home/scandy/Scandy2"
    "/root/Scandy2"
    "/opt/scandy2"
    "/usr/local/scandy2"
)

# Aktuelles Verzeichnis
CURRENT_DIR=$(pwd)
echo "Aktuelles Verzeichnis: $CURRENT_DIR"

# Prüfe ob wir bereits in einem Scandy-Verzeichnis sind
if [ -d "app" ] && [ -f "docker-compose.yml" ]; then
    log_success "Scandy-Verzeichnis gefunden: $CURRENT_DIR"
    echo "export SCANDY_SOURCE_DIR=\"$CURRENT_DIR\"" > /tmp/scandy_dir.sh
    echo "Verzeichnis gespeichert in /tmp/scandy_dir.sh"
    exit 0
fi

# Prüfe bekannte Verzeichnisse
for dir in "${POSSIBLE_DIRS[@]}"; do
    if [ -d "$dir" ] && [ -d "$dir/app" ]; then
        log_success "Scandy-Verzeichnis gefunden: $dir"
        echo "export SCANDY_SOURCE_DIR=\"$dir\"" > /tmp/scandy_dir.sh
        echo "Verzeichnis gespeichert in /tmp/scandy_dir.sh"
        exit 0
    fi
done

# Suche mit find
echo "Suche mit find..."
FOUND_DIRS=$(find / -name "*scandy*" -type d 2>/dev/null | grep -E "(Scandy|scandy)" | head -10)

if [ -n "$FOUND_DIRS" ]; then
    echo "Gefundene Verzeichnisse:"
    echo "$FOUND_DIRS"
    
    # Prüfe jedes gefundene Verzeichnis
    while IFS= read -r dir; do
        if [ -d "$dir/app" ] && [ -f "$dir/docker-compose.yml" ]; then
            log_success "Scandy-Verzeichnis gefunden: $dir"
            echo "export SCANDY_SOURCE_DIR=\"$dir\"" > /tmp/scandy_dir.sh
            echo "Verzeichnis gespeichert in /tmp/scandy_dir.sh"
            exit 0
        fi
    done <<< "$FOUND_DIRS"
fi

log_error "Kein Scandy-Verzeichnis gefunden!"
echo "Bitte führen Sie dieses Script im Scandy-Verzeichnis aus oder geben Sie den Pfad manuell an."
echo
echo "Mögliche Aktionen:"
echo "1. cd /path/to/scandy && ./find_scandy_dir.sh"
echo "2. export SCANDY_SOURCE_DIR=\"/path/to/scandy\""
echo "3. ./update_scandy_lxc.sh" 