#!/usr/bin/env bash
# Power log for a job on this machine.
#
#   bash powerlog.sh run <csv> <command...>     log while the command runs, then summarise
#   bash powerlog.sh sample <csv> [stage-file] [pid]
#                                               log until stopped (Ctrl-C or kill)
#   bash powerlog.sh summary <csv> [<csv>...]   print the summary again; several logs are added up
#
# 01-poses.sh and 02-train.sh call this themselves and write a new
# logs/power-*.csv on every run. Everything logged so far, in one table:
#   bash powerlog.sh summary ~/sshah_workspace/projects/*/logs/power-*.csv
#
# What is measured: each graphics card's draw as nvidia-smi reports it (good
# to about 5 W per card), and how busy the CPU was. The CPU's own energy
# counter is read too when this user is allowed to (normally root only).
# What is not measured: board, memory, drives, fans and power-supply losses.
# The "at the wall" line in the summary fills those in with the assumptions
# below, so treat it as an estimate. A plug-in meter is the only real check.
#
# The log covers the whole machine, including anyone else's work on it.
#
# Options (environment variables):
#   POWER_EVERY=5      seconds between samples
#   CPU_IDLE_W=10      assumed CPU draw when idle   (used only without the counter)
#   CPU_FULL_W=80      assumed CPU draw flat out    (used only without the counter)
#   REST_W=37          assumed draw of everything that is not CPU or graphics card
#   PSU_EFF=0.87       assumed power-supply efficiency
set -u
EVERY="${POWER_EVERY:-5}"
RAPL=/sys/class/powercap/intel-rapl:0
STAT=/proc/stat
SELF="$(readlink -f "$0")"

case "${1:-}" in
sample)
    csv="${2:?usage: powerlog.sh sample <csv> [stage-file] [pid]}"
    stagefile="${3:-}"   # a file holding the name of the step now running
    watch="${4:-}"       # stop by itself when this process is gone
    command -v nvidia-smi > /dev/null || { echo "powerlog: nvidia-smi not found" >&2; exit 1; }
    {
        echo "# gpus=$(nvidia-smi --query-gpu=name --format=csv,noheader | paste -sd'|' -)"
        [ -r "$RAPL/energy_uj" ] && echo "# rapl_max_uj=$(cat "$RAPL/max_energy_range_uj")"
        echo "epoch,stage,cpu_busy_pct,cpu_pkg_uj,gpu_watts"
    } > "$csv"
    pbusy=""; ptotal=""; sl=""
    one() {
        local stage="${POWER_STAGE:-run}" u=0 n=0 s=0 i=0 w=0 q=0 sq=0 st=0 rest busy total pct="" uj="" g
        if [ -n "$stagefile" ] && [ -r "$stagefile" ]; then stage=$(cat "$stagefile"); fi
        if [ -r "$STAT" ]; then
            # First line of /proc/stat: time spent in each state since boot.
            read -r _ u n s i w q sq st rest < "$STAT"
            busy=$((u + n + s + q + sq + st)); total=$((busy + i + w))
            if [ -n "$ptotal" ] && [ "$total" -gt "$ptotal" ]; then
                pct=$(( (busy - pbusy) * 100 / (total - ptotal) ))
            fi
            pbusy=$busy; ptotal=$total
        fi
        if [ -r "$RAPL/energy_uj" ]; then uj=$(cat "$RAPL/energy_uj"); fi
        g=$(nvidia-smi --query-gpu=power.draw --format=csv,noheader,nounits 2> /dev/null \
            | sed 's/[^0-9.]//g' | paste -sd, -)
        echo "$(date +%s),$stage,$pct,$uj,$g" >> "$csv"
    }
    # On stop, take one last sample so the final few seconds are counted.
    trap 'one; [ -n "$sl" ] && kill "$sl" 2> /dev/null; exit 0' TERM INT
    while :; do
        one
        if [ -n "$watch" ] && ! kill -0 "$watch" 2> /dev/null; then exit 0; fi
        sleep "$EVERY" & sl=$!
        wait "$sl"
    done
    ;;

run)
    csv="${2:?usage: powerlog.sh run <csv> <command...>}"; shift 2
    [ $# -gt 0 ] || { echo "usage: powerlog.sh run <csv> <command...>" >&2; exit 2; }
    POWER_STAGE="$(basename "$1")" bash "$SELF" sample "$csv" "" $$ & s=$!
    rc=0; "$@" || rc=$?
    kill "$s" 2> /dev/null; wait "$s" 2> /dev/null
    bash "$SELF" summary "$csv"
    exit "$rc"
    ;;

summary)
    shift
    [ $# -gt 0 ] || { echo "usage: powerlog.sh summary <csv> [<csv>...]" >&2; exit 2; }
    for f in "$@"; do [ -r "$f" ] || { echo "powerlog: cannot read $f" >&2; exit 1; }; done
    awk -F, \
        -v idle="${CPU_IDLE_W:-10}" -v full="${CPU_FULL_W:-80}" \
        -v restw="${REST_W:-37}" -v eff="${PSU_EFF:-0.87}" '
    function hms(t) { return t >= 90 ? sprintf("%.1f min", t / 60) : sprintf("%d s", t) }
    FNR == 1          { files++; n = 0 }
    /^# gpus=/        { sub(/^# gpus=/, ""); ng = split($0, name, "|"); next }
    /^# rapl_max_uj=/ { sub(/^# rapl_max_uj=/, ""); raplmax = $0 + 0; next }
    /^#/ || $1 == "epoch" { next }
    {
        n++; samples++
        dt = $1 - pt
        if (n > 1 && dt > 0) {
            # Each stretch between two samples belongs to the step it ended in.
            st = $2
            if (!(st in T)) order[++ns] = st
            T[st] += dt; Ttot += dt
            for (g = 5; g <= NF; g++) if ($g != "" && pg[g] != "") {
                e = dt * ($g + pg[g]) / 2          # joules
                E[st, g] += e; Eg[g] += e; Est[st] += e; Egpu += e
                ET[st, g] += dt; EgT[g] += dt
                if (g > maxg) maxg = g
            }
            if ($3 != "") { B[st] += dt * $3; BT[st] += dt; Btot += dt * $3; BTtot += dt }
            # CPU energy for this stretch: the counter if there is one,
            # otherwise worked out from how busy the CPU was.
            if ($4 != "" && puj != "") {
                d = $4 - puj; if (d < 0) d += raplmax
                Jcpu += d / 1e6; Tcpu += dt
            } else if ($3 != "") {
                Jest += (idle + (full - idle) * $3 / 100) * dt; Test += dt
            } else {
                Jest += (idle + full) / 2 * dt; Test += dt
            }
        }
        pt = $1; puj = $4
        for (g = 5; g <= NF; g++) pg[g] = $g
    }
    END {
        src = FILENAME; sub(/^.*\//, "", src); if (files > 1) src = files " logs"
        if (Ttot == 0) { print "### power: not enough samples in " src; exit }
        printf "### power while this ran  (%d samples over %s, %s)\n", samples, hms(Ttot), src
        printf "%-22s %9s", "step", "time"
        for (g = 5; g <= maxg; g++) {
            nm = ((g - 4) in name) ? name[g - 4] : "GPU " (g - 5)
            sub(/^NVIDIA /, "", nm); sub(/^GeForce /, "", nm)
            printf " %12s", substr(nm, 1, 12)
        }
        printf " %9s %10s\n", "CPU busy", "GPU energy"
        for (k = 1; k <= ns + 1; k++) {
            if (k > ns && ns == 1) break
            st = k <= ns ? order[k] : "total"
            t = k <= ns ? T[st] : Ttot
            printf "%-22s %9s", st, hms(t)
            for (g = 5; g <= maxg; g++) {
                gt = k <= ns ? ET[st, g] : EgT[g]      # time with a reading from this card
                if (gt > 0) printf " %10.0f W", (k <= ns ? E[st, g] : Eg[g]) / gt; else printf " %12s", "-"
            }
            bt = k <= ns ? BT[st] : BTtot; b = k <= ns ? B[st] : Btot
            if (bt > 0) printf " %8.0f%%", b / bt; else printf " %9s", "-"
            printf " %7.1f Wh\n", (k <= ns ? Est[st] : Egpu) / 3600
        }
        printf "Graphics cards: %.1f Wh, measured (nvidia-smi, about 5 W accuracy per card).\n", Egpu / 3600
        cpu = Jcpu + Jest
        if (Test == 0)
            printf "CPU: %.1f Wh, measured (the processor energy counter).\n", cpu / 3600
        else if (BTtot == 0)
            printf "CPU: about %.1f Wh, a guess: the log has no CPU readings, so %.0f W is assumed.\n", cpu / 3600, (idle + full) / 2
        else if (Tcpu == 0)
            printf "CPU: about %.1f Wh, estimated from how busy it was (%s W idle to %s W flat out).\n", cpu / 3600, idle, full
        else
            printf "CPU: about %.1f Wh, of which %.1f Wh measured and the rest estimated from how busy it was.\n", cpu / 3600, Jcpu / 3600
        wall = (Egpu + cpu + restw * Ttot) / eff
        printf "At the wall: about %.1f Wh (%.3f kWh), average %.0f W. Estimate: assumes %s W for the rest of the machine and a power supply at %.0f%% efficiency.\n", \
            wall / 3600, wall / 3.6e6, wall / Ttot, restw, eff * 100
    }' "$@"
    ;;

*)
    sed -n '2,7p' "$SELF" | sed 's/^# \{0,1\}//'
    exit 2
    ;;
esac
