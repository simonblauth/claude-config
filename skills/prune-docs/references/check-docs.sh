#!/usr/bin/env bash
# Mechanical rows of the prune-docs verification set (SKILL.md, Phase 7).
#
#   check-docs.sh [-s SRC_DIR]... [-y SYMBOLS] [-r OLD_PATH]... [-p PROBES] [-c CLAIMS] FILE.md...
#
#   -s DIR      source or test dir searched by -y and -r (repeatable)
#   -y FILE     symbols, one per line; each must appear in some -s dir
#   -r PATH     a renamed or deleted page; no doc or -s file may still name it (repeatable)
#   -p FILE     duplication probes, one verbatim line each; each must hit exactly one doc
#   -c FILE     pre-state claims, one grep -E pattern each; each must hit at least one doc
#
# Links and anchors are always checked. Exit 1 if any row fails.
# Anchor slugs follow github-slugger: lowercase, spaces to hyphens, punctuation
# other than - and _ dropped, duplicate headings suffixed -1, -2, ...
set -u

src=() symbols= old=() probes= claims=
while getopts 's:y:r:p:c:' opt; do
	case $opt in
		s) src+=("$OPTARG") ;;
		y) symbols=$OPTARG ;;
		r) old+=("$OPTARG") ;;
		p) probes=$OPTARG ;;
		c) claims=$OPTARG ;;
		*) exit 2 ;;
	esac
done
shift $((OPTIND - 1))
docs=("$@")
[ ${#docs[@]} -gt 0 ] || { echo "usage: check-docs.sh [opts] FILE.md..." >&2; exit 2; }

fails=0
fail() { printf 'FAIL %s\n' "$*"; fails=$((fails + 1)); }
row() { printf '\n== %s\n' "$*"; }

# Heading slugs of one file, github-slugger style, with -N suffixes for repeats.
slugs() {
	sed -nE 's/^#{1,6}[[:space:]]+//p' "$1" \
		| sed -E 's/`//g; s/\[([^]]*)\]\([^)]*\)/\1/g' \
		| tr '[:upper:]' '[:lower:]' \
		| sed -E 's/[^a-z0-9 _-]//g; s/ /-/g' \
		| awk '{ n = seen[$0]++; print (n ? $0 "-" n : $0) }'
}

# Every inline link target in a file: the text between ]( and the closing paren,
# minus any "title" part. Reference-style [x]: links are not covered.
targets() {
	grep -oE '\]\([^)[:space:]]+' "$1" | sed 's/^\](//'
}

row "links and anchors"
for doc in "${docs[@]}"; do
	dir=$(dirname "$doc")
	while IFS= read -r t; do
		case $t in *://*|mailto:*) continue ;; esac
		path=${t%%#*}
		frag=${t#"$path"}; frag=${frag#\#}
		if [ -n "$path" ]; then
			target="$dir/$path"
			[ -e "$target" ] || { fail "$doc -> $t (missing file)"; continue; }
		else
			target=$doc
		fi
		if [ -n "$frag" ] && [ -f "$target" ]; then
			slugs "$target" | grep -qxF -- "$frag" || fail "$doc -> $t (no such heading)"
		fi
	done < <(targets "$doc")
done

if [ -n "$symbols" ]; then
	row "symbols in ${src[*]:-<no -s dirs>}"
	while IFS= read -r sym; do
		[ -n "$sym" ] || continue
		grep -rqF -- "$sym" "${src[@]}" 2>/dev/null || fail "symbol not in source: $sym"
	done < "$symbols"
fi

if [ ${#old[@]} -gt 0 ]; then
	row "stale paths"
	for p in "${old[@]}"; do
		grep -rnF -- "$p" "${docs[@]}" "${src[@]}" 2>/dev/null | sed "s/^/FAIL still names $p: /"
		grep -rqF -- "$p" "${docs[@]}" "${src[@]}" 2>/dev/null && fails=$((fails + 1))
	done
fi

if [ -n "$probes" ]; then
	row "duplication (files per probe line, want 1)"
	while IFS= read -r line; do
		[ -n "$line" ] || continue
		n=$(grep -lF -- "$line" "${docs[@]}" | wc -l)
		printf '%4d  %s\n' "$n" "$line"
		[ "$n" -eq 1 ] || fail "probe hits $n files: $line"
	done < "$probes"
fi

if [ -n "$claims" ]; then
	row "absence check (pre-state claims with no hit)"
	while IFS= read -r pat; do
		[ -n "$pat" ] || continue
		grep -qE -- "$pat" "${docs[@]}" || fail "claim gone: $pat"
	done < "$claims"
fi

printf '\n%d failure(s)\n' "$fails"
[ "$fails" -eq 0 ]
