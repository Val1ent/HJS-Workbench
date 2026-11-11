#!/usr/bin/env bash
# HJS-Workbench CLI installer: cross-platform terminal script.
#
# Runs under bash on Ubuntu, WSL, and macOS, invoked with a one-line
# command such as:
#
#     curl -fsSL <release-url>/install.sh | bash
#
# Flow (fixed order):
#   1. Language selection first: a short numbered list of the supported
#      languages; the choice selects the language of the script's own
#      messages. Nothing else is asked before this step.
#   2. Only then the install explanation and the install-directory
#      prompt, defaulting to ~/.local/bin (user-writable, no root).
#   3. Download the CLI binary matching the running platform from the
#      project release, place it in the chosen directory, set the
#      executable bit.
#   4. If the directory is not on PATH, print a clear instruction for
#      adding it. A system-wide directory may be chosen by the user and
#      is the only case that may need elevated privileges.
#   5. Failures report specific messages: unsupported platform, failed
#      download, or a directory that cannot be written.
#
# Honest scope: the script is delivered now. The Windows CLI binary is
# published; the Linux and macOS binaries follow once those platforms'
# builds are published to a release. The script reports a "not published
# yet" message for a missing binary instead of pretending it exists.

set -u

APP_NAME="HJSWorkbench-CLI"
VERSION="0.6.2"
BASE_URL="${HJS_INSTALL_BASE_URL:-https://github.com/Val1ent/HJS-Workbench/releases/download/v${VERSION}}"

lang="en"

# ----------------------------------------------------------------------
# Read one line, also when stdin is the curl pipe instead of a terminal.
# ----------------------------------------------------------------------
ask() {
    answer=""
    if [ -t 0 ]; then
        read -r answer
    elif [ -t 1 ]; then
        read -r answer < /dev/tty 2>/dev/null || read -r answer
    else
        read -r answer
    fi
    # Windows text-mode pipes deliver CRLF; drop a trailing carriage
    # return so the choice matches the case patterns exactly.
    answer="${answer%$'\r'}"
}

# ----------------------------------------------------------------------
# Message table: every prompt of the script in the five app languages.
# ----------------------------------------------------------------------
set_messages() {
    case "$lang" in
        fr)
            M_TITLE="Installateur CLI HJS-Workbench"
            M_SELECT="Choisissez la langue (1-5) : "
            M_EXPLAIN="L'installateur télécharge le binaire CLI officiel et l'installe dans le répertoire choisi."
            M_DIR_PROMPT="Répertoire d'installation (Entrée = %s) : "
            M_CHECKING="Vérification de %s ..."
            M_DOWNLOADING="Téléchargement de %s ..."
            M_DONE="Installé : %s"
            M_RUN="Lancez la CLI avec : %s"
            M_FIRST_RUN="La CLI demandera sa propre langue au premier lancement."
            M_PATH_NOTE="Le répertoire d'installation n'est pas dans PATH. Pour l'ajouter, exécutez :"
            M_UNSUPPORTED_OS="Plateforme non prise en charge : %s. Utilisez le programme d'installation Windows ou construisez le binaire pour cette plateforme."
            M_UNSUPPORTED_ARCH="Architecture non prise en charge : %s. Aucun binaire publié pour cette architecture."
            M_NEED_CURL="La commande curl est requise ; installez curl puis réessayez."
            M_NOT_PUBLISHED="Le binaire CLI pour %s n'est pas encore publié ; il le sera une fois le build de cette plateforme publié dans une release."
            M_DOWNLOAD_FAILED="Échec du téléchargement de %s (code HTTP %s)."
            M_WRITE_FAILED="Impossible d'écrire dans le répertoire : %s"
            ;;
        de)
            M_TITLE="HJS-Workbench CLI-Installationsprogramm"
            M_SELECT="Sprache wählen (1-5): "
            M_EXPLAIN="Das Installationsprogramm lädt das offizielle CLI-Binary herunter und installiert es im gewählten Verzeichnis."
            M_DIR_PROMPT="Installationsverzeichnis (Enter = %s): "
            M_CHECKING="Prüfe %s ..."
            M_DOWNLOADING="Lade %s herunter ..."
            M_DONE="Installiert: %s"
            M_RUN="CLI starten mit: %s"
            M_FIRST_RUN="Die CLI fragt beim ersten Start nach ihrer eigenen Sprache."
            M_PATH_NOTE="Das Installationsverzeichnis ist nicht im PATH. Zum Hinzufügen ausführen:"
            M_UNSUPPORTED_OS="Nicht unterstützte Plattform: %s. Verwenden Sie das Windows-Installationsprogramm oder erstellen Sie das Binary für diese Plattform."
            M_UNSUPPORTED_ARCH="Nicht unterstützte Architektur: %s. Kein Binary für diese Architektur veröffentlicht."
            M_NEED_CURL="Der Befehl curl wird benötigt; installieren Sie curl und versuchen Sie es erneut."
            M_NOT_PUBLISHED="Das CLI-Binary für %s ist noch nicht veröffentlicht; es folgt, sobald der Build dieser Plattform in einem Release veröffentlicht ist."
            M_DOWNLOAD_FAILED="Herunterladen von %s fehlgeschlagen (HTTP-Code %s)."
            M_WRITE_FAILED="Verzeichnis nicht beschreibbar: %s"
            ;;
        zh_CN)
            M_TITLE="HJS-Workbench CLI 安装程序"
            M_SELECT="请选择语言（1-5）："
            M_EXPLAIN="安装程序将下载官方 CLI 二进制文件，并安装到所选目录。"
            M_DIR_PROMPT="安装目录（回车默认 %s）："
            M_CHECKING="正在检查 %s ..."
            M_DOWNLOADING="正在下载 %s ..."
            M_DONE="已安装：%s"
            M_RUN="启动 CLI：%s"
            M_FIRST_RUN="CLI 首次启动时会询问应用自身语言。"
            M_PATH_NOTE="安装目录不在 PATH 中。请执行以下命令将其加入："
            M_UNSUPPORTED_OS="不支持的操作系统：%s。请使用 Windows 安装程序，或为该平台构建二进制文件。"
            M_UNSUPPORTED_ARCH="不支持的架构：%s。尚未发布该架构的二进制文件。"
            M_NEED_CURL="需要 curl 命令；请先安装 curl 再重试。"
            M_NOT_PUBLISHED="%s 平台的 CLI 二进制文件尚未发布；待该平台的构建发布到 release 后即可使用。"
            M_DOWNLOAD_FAILED="下载 %s 失败（HTTP 状态码 %s）。"
            M_WRITE_FAILED="无法写入目录：%s"
            ;;
        zh_TW)
            M_TITLE="HJS-Workbench CLI 安裝程式"
            M_SELECT="請選擇語言（1-5）："
            M_EXPLAIN="安裝程式將下載官方 CLI 二進位檔，並安裝到所選目錄。"
            M_DIR_PROMPT="安裝目錄（按 Enter 預設 %s）："
            M_CHECKING="正在檢查 %s ..."
            M_DOWNLOADING="正在下載 %s ..."
            M_DONE="已安裝：%s"
            M_RUN="啟動 CLI：%s"
            M_FIRST_RUN="CLI 首次啟動時會詢問應用程式自身語言。"
            M_PATH_NOTE="安裝目錄不在 PATH 中。請執行以下指令將其加入："
            M_UNSUPPORTED_OS="不支援的作業系統：%s。請使用 Windows 安裝程式，或為該平台建置二進位檔。"
            M_UNSUPPORTED_ARCH="不支援的架構：%s。尚未發佈該架構的二進位檔。"
            M_NEED_CURL="需要 curl 指令；請先安裝 curl 再重試。"
            M_NOT_PUBLISHED="%s 平台的 CLI 二進位檔尚未發佈；待該平台的建置發佈到 release 後即可使用。"
            M_DOWNLOAD_FAILED="下載 %s 失敗（HTTP 狀態碼 %s）。"
            M_WRITE_FAILED="無法寫入目錄：%s"
            ;;
        *)
            M_TITLE="HJS-Workbench CLI installer"
            M_SELECT="Select language (1-5): "
            M_EXPLAIN="The installer downloads the official CLI binary and installs it into the chosen directory."
            M_DIR_PROMPT="Install directory (Enter defaults to %s): "
            M_CHECKING="Checking %s ..."
            M_DOWNLOADING="Downloading %s ..."
            M_DONE="Installed: %s"
            M_RUN="Run the CLI with: %s"
            M_FIRST_RUN="The CLI asks for its own language on the first run."
            M_PATH_NOTE="The install directory is not on PATH. To add it, run:"
            M_UNSUPPORTED_OS="Unsupported platform: %s. Use the Windows Setup installer or build the binary for this platform."
            M_UNSUPPORTED_ARCH="Unsupported architecture: %s. No binary is published for this architecture."
            M_NEED_CURL="The curl command is required; install curl and retry."
            M_NOT_PUBLISHED="The CLI binary for %s is not published yet; it becomes available once that platform's build is published in a release."
            M_DOWNLOAD_FAILED="Downloading %s failed (HTTP status %s)."
            M_WRITE_FAILED="Cannot write to the directory: %s"
            ;;
    esac
}

# ----------------------------------------------------------------------
# 1. Language selection first, before any other prompt.
# ----------------------------------------------------------------------
ask_language() {
    echo "$M_TITLE"
    echo "  [1] English"
    echo "  [2] Français"
    echo "  [3] Deutsch"
    echo "  [4] 简体中文"
    echo "  [5] 繁體中文"
    printf "%s" "$M_SELECT"
    ask
    case "$answer" in
        1|en|EN|En) lang="en" ;;
        2|fr|FR|Fr) lang="fr" ;;
        3|de|DE|De) lang="de" ;;
        4|zh_CN|zh-cn|zh) lang="zh_CN" ;;
        5|zh_TW|zh-tw) lang="zh_TW" ;;
        *) lang="en" ;;
    esac
    set_messages
}

fail() {
    printf "%s\n" "$1" >&2
    exit 1
}

# ----------------------------------------------------------------------
# Platform detection: Ubuntu/WSL report Linux; macOS reports Darwin.
# ----------------------------------------------------------------------
detect_platform() {
    os_name="$(uname -s)"
    arch_name="$(uname -m)"
    case "$os_name" in
        Linux) os="linux" ;;
        Darwin) os="macos" ;;
        *)
            fail "$(printf "$M_UNSUPPORTED_OS" "$os_name")" ;;
    esac
    case "$arch_name" in
        x86_64|amd64) arch="x86_64" ;;
        arm64|aarch64) arch="arm64" ;;
        *)
            fail "$(printf "$M_UNSUPPORTED_ARCH" "$arch_name")" ;;
    esac
    asset="${APP_NAME}-${os}-${arch}"
}

main() {
    set_messages
    ask_language

    command -v curl > /dev/null 2>&1 || fail "$M_NEED_CURL"

    # 2. Install explanation and directory prompt, after the language.
    echo "$M_EXPLAIN"
    default_dir="$HOME/.local/bin"
    printf "$M_DIR_PROMPT" "$default_dir"
    ask
    dir="${answer:-$default_dir}"
    case "$dir" in
        "~"|"~/"*) dir="${HOME}/${dir#~/}" ;;
    esac
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir" 2>/dev/null \
            || fail "$(printf "$M_WRITE_FAILED" "$dir")"
    fi
    if [ ! -w "$dir" ]; then
        fail "$(printf "$M_WRITE_FAILED" "$dir")"
    fi

    # 3. Download the matching platform binary and install it.
    detect_platform
    url="$BASE_URL/$asset"
    printf "$M_CHECKING" "$url"
    printf "\n"
    http_code="$(curl -s -o /dev/null -w '%{http_code}' "$url")" || true
    if [ "$http_code" = "404" ]; then
        fail "$(printf "$M_NOT_PUBLISHED" "$asset")"
    fi
    tmp="$(mktemp)"
    printf "$M_DOWNLOADING" "$url"
    printf "\n"
    if ! curl -fsSL -o "$tmp" "$url"; then
        rm -f "$tmp"
        fail "$(printf "$M_DOWNLOAD_FAILED" "$url" "$http_code")"
    fi
    cp "$tmp" "$dir/$asset" || {
        rm -f "$tmp"
        fail "$(printf "$M_WRITE_FAILED" "$dir")"
    }
    chmod +x "$dir/$asset" || {
        rm -f "$tmp"
        fail "$(printf "$M_WRITE_FAILED" "$dir")"
    }
    rm -f "$tmp"

    printf "$M_DONE" "$dir/$asset"
    printf "\n"
    printf "$M_RUN" "$dir/$asset"
    printf "\n"
    echo "$M_FIRST_RUN"

    # 4. PATH instruction when the chosen directory is not on PATH.
    case ":$PATH:" in
        *":$dir:"*) ;;
        *)
            echo "$M_PATH_NOTE"
            if [ "$os" = "macos" ]; then
                printf 'export PATH="$PATH:%s"\n' "$dir"
            else
                printf 'echo '\''export PATH="$PATH:%s"'\'' >> ~/.bashrc && source ~/.bashrc\n' "$dir"
            fi
            ;;
    esac
}

main "$@"
