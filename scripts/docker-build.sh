#!/usr/bin/env bash
# Build and push multi-platform Docker image to GHCR via docker buildx.
#
# Usage: scripts/docker-build.sh [--image IMAGE] [--dry-run] [--test]
#
# Image name is auto-derived from git remote origin:
#   https://github.com/owner/repo.git  →  ghcr.io/owner/repo
#   git@github.com:owner/repo.git      →  ghcr.io/owner/repo
#
# Version is read from git tag on HEAD:
#   v1.2.3     → :1  :1.2  :1.2.3  :latest
#   v0.3.1     → :0.3  :0.3.1  :latest
#   v1.0.0-rc1 → :1.0.0-rc1
#   (no tag)   → :sha-<hash>
#
# Prerequisites: docker buildx, logged in to ghcr.io via `docker login ghcr.io`

set -euo pipefail

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Build and push a multi-platform Docker image (linux/amd64, linux/arm64) to GHCR.

OPTIONS:
  --image IMAGE   Override auto-derived image name (default: derived from git remote origin)
  --dry-run       Print what would be executed without running docker buildx
  --test          Run self-tests on pure-logic functions and exit
  -h, --help      Show this help message

EXAMPLES:
  $(basename "$0")
  $(basename "$0") --image ghcr.io/other-org/other-name
  $(basename "$0") --dry-run
EOF
}

# ---------------------------------------------------------------------------
# derive_image_name
#
# Reads git remote origin URL and converts it to a ghcr.io image name.
# Supports HTTPS and SSH remote URL formats.
# ---------------------------------------------------------------------------
derive_image_name() {
    local remote_url
    remote_url=$(git remote get-url origin 2>/dev/null) || {
        echo "error: no git remote 'origin' found — set one or use --image" >&2
        return 1
    }

    local owner_repo
    # HTTPS: https://github.com/owner/repo.git
    if [[ "$remote_url" =~ ^https?://[^/]+/([^/]+/[^/]+)$ ]]; then
        owner_repo="${BASH_REMATCH[1]}"
    # SSH: git@github.com:owner/repo.git
    elif [[ "$remote_url" =~ ^[^@]+@[^:]+:([^/]+/[^/]+)$ ]]; then
        owner_repo="${BASH_REMATCH[1]}"
    else
        echo "error: cannot parse git remote URL: ${remote_url}" >&2
        return 1
    fi

    # Strip .git suffix
    owner_repo="${owner_repo%.git}"

    # Docker image names must be lowercase
    owner_repo=$(tr '[:upper:]' '[:lower:]' <<< "$owner_repo")

    printf 'ghcr.io/%s' "$owner_repo"
}

# ---------------------------------------------------------------------------
# detect_version
#
# Returns the version string to use for tagging.
# Prefers an exact git tag on HEAD; falls back to sha-<short-hash>.
# Strips leading 'v' from tag names.
# ---------------------------------------------------------------------------
detect_version() {
    local tag
    if tag=$(git describe --tags --exact-match HEAD 2>/dev/null); then
        # Strip 'v' prefix if present
        printf '%s' "${tag#v}"
    else
        local hash
        hash=$(git rev-parse --short=7 HEAD)
        printf 'sha-%s' "$hash"
    fi
}

# ---------------------------------------------------------------------------
# expand_tags IMAGE VERSION
#
# Outputs one fully-qualified image:tag per line.
#
# Rules:
#   sha-*        → IMAGE:sha-*
#   M.N.P-pre    → IMAGE:M.N.P-pre
#   M.N.P (M≥1) → IMAGE:M  IMAGE:M.N  IMAGE:M.N.P  IMAGE:latest
#   M.N.P (M=0) → IMAGE:M.N  IMAGE:M.N.P  IMAGE:latest
#   other        → IMAGE:VERSION
# ---------------------------------------------------------------------------
expand_tags() {
    local image="$1"
    local version="$2"

    # Commit hash fallback — no latest
    if [[ "$version" =~ ^sha- ]]; then
        printf '%s:%s\n' "$image" "$version"
        return
    fi

    # Parse semver: M.N.P or M.N.P-prerelease
    local major minor patch prerelease
    if [[ "$version" =~ ^([0-9]+)\.([0-9]+)\.([0-9]+)(-(.+))?$ ]]; then
        major="${BASH_REMATCH[1]}"
        minor="${BASH_REMATCH[2]}"
        patch="${BASH_REMATCH[3]}"
        prerelease="${BASH_REMATCH[5]:-}"
    else
        # Non-semver tag — output as-is
        printf '%s:%s\n' "$image" "$version"
        return
    fi

    if [[ -n "$prerelease" ]]; then
        # Pre-release: full version tag only, no latest
        printf '%s:%s\n' "$image" "$version"
    else
        # Stable release: expand shorthand tags + latest
        if [[ "$major" -ge 1 ]]; then
            printf '%s:%s\n' "$image" "$major"
        fi
        printf '%s:%s.%s\n'     "$image" "$major" "$minor"
        printf '%s:%s.%s.%s\n'  "$image" "$major" "$minor" "$patch"
        printf '%s:latest\n'    "$image"
    fi
}

# ---------------------------------------------------------------------------
# ensure_builder
#
# Ensures a docker buildx builder with multi-platform support exists and is
# selected. Creates one if it does not already exist.
# ---------------------------------------------------------------------------
ensure_builder() {
    local builder_name="dprs-multiplatform"

    if docker buildx inspect "$builder_name" &>/dev/null; then
        docker buildx use "$builder_name"
        return 0
    fi

    echo "[buildx] Creating multi-platform builder: ${builder_name}"
    docker buildx create \
        --name "$builder_name" \
        --driver docker-container \
        --platform linux/amd64,linux/arm64 \
        --bootstrap
    docker buildx use "$builder_name"
}

# ---------------------------------------------------------------------------
# _run_tests
#
# Inline self-tests for pure-logic functions (no docker/git required).
# Run with: scripts/docker-build.sh --test
# ---------------------------------------------------------------------------
_run_tests() {
    local passed=0
    local failed=0

    _assert_eq() {
        local label="$1" expected="$2" actual="$3"
        if [[ "$expected" == "$actual" ]]; then
            echo "  PASS  $label"
            (( passed++ )) || true
        else
            echo "  FAIL  $label"
            echo "        expected: $expected"
            echo "        actual:   $actual"
            (( failed++ )) || true
        fi
    }

    echo "=== expand_tags tests ==="

    local image="ghcr.io/fhcst/dprs"

    _assert_eq "stable major>=1" \
        "$(printf '%s:1\n%s:1.2\n%s:1.2.3\n%s:latest' "$image" "$image" "$image" "$image")" \
        "$(expand_tags "$image" "1.2.3")"

    _assert_eq "stable major=0" \
        "$(printf '%s:0.3\n%s:0.3.1\n%s:latest' "$image" "$image" "$image")" \
        "$(expand_tags "$image" "0.3.1")"

    _assert_eq "stable v2.0.0" \
        "$(printf '%s:2\n%s:2.0\n%s:2.0.0\n%s:latest' "$image" "$image" "$image" "$image")" \
        "$(expand_tags "$image" "2.0.0")"

    _assert_eq "pre-release rc" \
        "${image}:1.0.0-rc1" \
        "$(expand_tags "$image" "1.0.0-rc1")"

    _assert_eq "pre-release beta" \
        "${image}:0.5.0-beta.2" \
        "$(expand_tags "$image" "0.5.0-beta.2")"

    _assert_eq "sha fallback" \
        "${image}:sha-abc1234" \
        "$(expand_tags "$image" "sha-abc1234")"

    echo ""
    echo "=== derive_image_name tests (mocked) ==="

    # Mock git to test URL parsing
    _test_derive() {
        local label="$1" url="$2" expected="$3"
        local actual
        # Override git for this test
        git() {
            if [[ "$*" == "remote get-url origin" ]]; then
                printf '%s' "$url"
                return 0
            fi
            command git "$@"
        }
        actual=$(derive_image_name)
        unset -f git
        _assert_eq "$label" "$expected" "$actual"
    }

    _test_derive "HTTPS with .git" \
        "https://github.com/fhcst/dprs.git" \
        "ghcr.io/fhcst/dprs"

    _test_derive "SSH with .git" \
        "git@github.com:fhcst/dprs.git" \
        "ghcr.io/fhcst/dprs"

    _test_derive "HTTPS without .git" \
        "https://github.com/fhcst/dprs" \
        "ghcr.io/fhcst/dprs"

    _test_derive "uppercase owner" \
        "https://github.com/FHCST/DPRS.git" \
        "ghcr.io/fhcst/dprs"

    echo ""
    echo "=== Results: ${passed} passed, ${failed} failed ==="
    [[ "$failed" -eq 0 ]]
}

# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
main() {
    local image_override=""
    local dry_run=false

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --image)
                shift
                image_override="${1:?--image requires a value}"
                ;;
            --dry-run)
                dry_run=true
                ;;
            --test)
                _run_tests
                exit $?
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                echo "error: unknown option: $1" >&2
                usage >&2
                exit 1
                ;;
        esac
        shift
    done

    # Resolve image name
    local image
    if [[ -n "$image_override" ]]; then
        image="$image_override"
    else
        image=$(derive_image_name)
    fi

    # Detect version
    local version
    version=$(detect_version)

    # Collect tags
    local -a tags
    tags=()
    while IFS= read -r line; do
        [[ -n "$line" ]] && tags+=("$line")
    done < <(expand_tags "$image" "$version")

    # Build --tag arguments array
    local -a tag_args
    tag_args=()
    for t in "${tags[@]}"; do
        tag_args+=(--tag "$t")
    done

    echo "Image:   ${image}"
    echo "Version: ${version}"
    echo "Tags:"
    for t in "${tags[@]}"; do
        echo "  ${t}"
    done

    if [[ "$dry_run" == "true" ]]; then
        echo ""
        echo "[dry-run] docker buildx build --platform linux/amd64,linux/arm64 --push ${tag_args[*]} ."
        return 0
    fi

    ensure_builder

    docker buildx build \
        --platform linux/amd64,linux/arm64 \
        --push \
        "${tag_args[@]}" \
        .
}

main "$@"
