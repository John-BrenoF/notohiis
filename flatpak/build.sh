set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_ID="io.github.JohnBrenoF.notohiis"
RUNTIME="25.08"
STAGE="$RAIZ/flatpak/.stage"
BUILD_DIR="$RAIZ/flatpak/build-dir"

cd "$RAIZ"

instala_se_precisa() {
    local ref="$1"
    if flatpak info --user "$ref" >/dev/null 2>&1; then
        return 0
    fi
    if flatpak info --system "$ref" >/dev/null 2>&1; then
        return 0
    fi
    echo "[INFO] Instalando $ref (Flathub, usuário)..."
    flatpak install --user -y flathub "$ref"
}

echo "[1/4] Checando ferramentas..."
instala_se_precisa "org.flatpak.Builder"
instala_se_precisa "org.freedesktop.Platform//$RUNTIME"
instala_se_precisa "org.freedesktop.Sdk//$RUNTIME"
instala_se_precisa "org.freedesktop.Sdk.Extension.rust-stable//$RUNTIME"

echo "[2/4] Montando árvore de fontes limpa (flatpak/.stage)..."
rm -rf "$STAGE"
mkdir -p "$STAGE"
git -C "$RAIZ" ls-files -z --cached --others --exclude-standard \
    | (cd "$RAIZ" && tar --null --verbatim-files-from --ignore-failed-read -T - -cf -) \
    | tar -xf - -C "$STAGE"
printf '%s\n' "$(git -C "$RAIZ" describe --always --dirty 2>/dev/null || echo dev) ($(date -u +%Y-%m-%dT%H:%M:%SZ))" \
    > "$STAGE/.flatpak-version"

if [ ! -f "$RAIZ/flatpak/python3-requirements.json" ] \
   || [ ! -f "$RAIZ/flatpak/cargo-sources-core.json" ] \
   || [ ! -f "$RAIZ/flatpak/cargo-sources-tool-nth.json" ]; then
    echo "[INFO] Fontes geradas ausentes — rodando flatpak/update-sources.sh..."
    bash "$RAIZ/flatpak/update-sources.sh"
fi

echo "[3/4] Buildando $APP_ID (flatpak-builder)..."
flatpak run org.flatpak.Builder \
    --user \
    --force-clean \
    --install \
    --disable-rofiles-fuse \
    --jobs="$(nproc)" \
    "$BUILD_DIR" \
    "flatpak/$APP_ID.yml" \
    "$@"

echo "[4/4] Pronto!"
echo
echo "  GUI:      flatpak run $APP_ID [arquivo]"
echo "  Terminal: flatpak run --command=notohiis-tui $APP_ID [arquivo]"
echo "  Alias:    alias nth='flatpak run $APP_ID'"
echo "             alias ntht='flatpak run --command=notohiis-tui $APP_ID'"
