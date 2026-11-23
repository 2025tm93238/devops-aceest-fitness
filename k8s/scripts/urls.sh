#!/usr/bin/env bash
# Print the endpoint URL of every deployment strategy.
source "$(dirname "$0")/common.sh"
banner "ACEest endpoints (node IP $(node_ip))"
printf '%-12s %s\n' "Rolling" "$(url_for rolling)/version"
printf '%-12s %s\n' "Blue-Green" "$(url_for bluegreen)/version"
printf '%-12s %s\n' "Canary" "$(url_for canary)/version"
printf '%-12s %s\n' "A/B testing" "$(url_for ab)/version   (header X-Variant: B for group B)"
printf '%-12s %s\n' "Shadow" "$(url_for shadow)/version   (mirrored to the shadow release)"
