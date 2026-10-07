#!/usr/bin/env bash
# =============================================================================
# Quantum Portal — Production Deploy Script
# Usage: ./deploy.sh [--env prod|staging|dev] [--cloud gcp|aws|azure]
#        [--skip-terraform] [--skip-helm] [--dry-run]
# =============================================================================
set -euo pipefail

# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }
die()     { error "$*"; exit 1; }
header()  { echo -e "\n${BOLD}${BLUE}══════ $* ══════${NC}\n"; }

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
ENV="prod"
CLOUD="gcp"
NAMESPACE="quantum-portal"
HELM_RELEASE="quantum-portal"
HELM_CHART_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../helm/quantum-portal" && pwd)"
TERRAFORM_DIR_GCP="$(cd "$(dirname "${BASH_SOURCE[0]}")/../terraform/gcp" && pwd)"
TERRAFORM_DIR_AWS="$(cd "$(dirname "${BASH_SOURCE[0]}")/../terraform/aws" && pwd)"
TERRAFORM_DIR_AZURE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../terraform/azure" && pwd)"
SKIP_TERRAFORM=false
SKIP_HELM=false
DRY_RUN=false
SLACK_WEBHOOK_URL="${SLACK_WEBHOOK_URL:-}"
PORTAL_IMAGE="${PORTAL_IMAGE:-gcr.io/quantum-portal-prod/quantum-portal:latest}"
API_IMAGE="${API_IMAGE:-gcr.io/quantum-portal-prod/quantum-api:latest}"
WORKER_IMAGE="${WORKER_IMAGE:-gcr.io/quantum-portal-prod/quantum-worker:latest}"
DEPLOY_TIMEOUT="300s"
SMOKE_TEST_URL="${SMOKE_TEST_URL:-}"

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --env)              ENV="$2";              shift 2 ;;
    --cloud)            CLOUD="$2";            shift 2 ;;
    --namespace)        NAMESPACE="$2";        shift 2 ;;
    --portal-image)     PORTAL_IMAGE="$2";     shift 2 ;;
    --api-image)        API_IMAGE="$2";        shift 2 ;;
    --worker-image)     WORKER_IMAGE="$2";     shift 2 ;;
    --skip-terraform)   SKIP_TERRAFORM=true;   shift ;;
    --skip-helm)        SKIP_HELM=true;        shift ;;
    --dry-run)          DRY_RUN=true;          shift ;;
    --timeout)          DEPLOY_TIMEOUT="$2";   shift 2 ;;
    --smoke-url)        SMOKE_TEST_URL="$2";   shift 2 ;;
    --help)
      echo "Usage: $0 [--env prod|staging|dev] [--cloud gcp|aws|azure]"
      echo "          [--portal-image IMG] [--api-image IMG] [--worker-image IMG]"
      echo "          [--skip-terraform] [--skip-helm] [--dry-run]"
      echo "          [--timeout 300s] [--smoke-url https://...] [--namespace ns]"
      exit 0
      ;;
    *)
      die "Unknown argument: $1. Run '$0 --help' for usage."
      ;;
  esac
done

TERRAFORM_DIR=""
case "$CLOUD" in
  gcp)   TERRAFORM_DIR="$TERRAFORM_DIR_GCP"   ;;
  aws)   TERRAFORM_DIR="$TERRAFORM_DIR_AWS"   ;;
  azure) TERRAFORM_DIR="$TERRAFORM_DIR_AZURE" ;;
  *)     die "Unknown cloud: $CLOUD. Use gcp, aws, or azure." ;;
esac

DEPLOY_START=$(date +%s)
DEPLOY_ID="deploy-$(date +%Y%m%d-%H%M%S)-${ENV}"

# ---------------------------------------------------------------------------
# Slack notification helper
# ---------------------------------------------------------------------------
slack_notify() {
  local status="$1"
  local message="$2"
  if [[ -z "$SLACK_WEBHOOK_URL" ]]; then
    info "SLACK_WEBHOOK_URL not set — skipping Slack notification"
    return 0
  fi
  local color
  local icon
  case "$status" in
    success) color="#36a64f"; icon=":white_check_mark:" ;;
    failure) color="#ff0000"; icon=":x:" ;;
    info)    color="#2196f3"; icon=":information_source:" ;;
    *)       color="#cccccc"; icon=":bell:" ;;
  esac

  local elapsed=$(( $(date +%s) - DEPLOY_START ))
  curl -s -X POST "$SLACK_WEBHOOK_URL" \
    -H "Content-Type: application/json" \
    -d "{
      \"attachments\": [{
        \"color\": \"${color}\",
        \"title\": \"${icon} Quantum Portal Deployment — ${status^^}\",
        \"text\": \"${message}\",
        \"fields\": [
          { \"title\": \"Environment\", \"value\": \"${ENV}\", \"short\": true },
          { \"title\": \"Cloud\", \"value\": \"${CLOUD}\", \"short\": true },
          { \"title\": \"Deploy ID\", \"value\": \"${DEPLOY_ID}\", \"short\": true },
          { \"title\": \"Duration\", \"value\": \"${elapsed}s\", \"short\": true }
        ],
        \"footer\": \"Deployed by $(git config user.email 2>/dev/null || echo 'CI') | $(date -u +%Y-%m-%dT%H:%M:%SZ)\"
      }]
    }" || warn "Slack notification failed (curl error)"
}

# ---------------------------------------------------------------------------
# Cleanup / error trap
# ---------------------------------------------------------------------------
on_error() {
  local exit_code=$?
  local line_num=$1
  error "Deploy failed at line ${line_num} (exit code ${exit_code})"
  slack_notify "failure" "Deploy FAILED at step: ${CURRENT_STEP:-unknown}\nCheck CI logs for details."
  exit "$exit_code"
}
trap 'on_error $LINENO' ERR

# ---------------------------------------------------------------------------
# Step 0: Prerequisites check
# ---------------------------------------------------------------------------
CURRENT_STEP="prerequisites"
header "Step 0 — Prerequisites Check"

check_cmd() {
  local cmd="$1"
  local install_hint="${2:-}"
  if ! command -v "$cmd" &>/dev/null; then
    die "Required command '$cmd' not found.${install_hint:+ Install: $install_hint}"
  fi
  success "$cmd found: $(command -v "$cmd")"
}

check_cmd kubectl   "https://kubernetes.io/docs/tasks/tools/"
check_cmd helm      "https://helm.sh/docs/intro/install/"
check_cmd terraform "https://developer.hashicorp.com/terraform/downloads"
check_cmd curl      "apt install curl"
check_cmd jq        "apt install jq"

case "$CLOUD" in
  gcp)   check_cmd gcloud "https://cloud.google.com/sdk/docs/install" ;;
  aws)   check_cmd aws    "https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html" ;;
  azure) check_cmd az     "https://learn.microsoft.com/en-us/cli/azure/install-azure-cli" ;;
esac

# Verify cluster context is reachable
info "Checking kubectl cluster connectivity..."
if ! kubectl cluster-info &>/dev/null; then
  die "kubectl cannot reach cluster. Check your kubeconfig / cloud auth."
fi
success "kubectl: cluster reachable"

# Verify helm chart directory exists
if [[ ! -f "${HELM_CHART_DIR}/Chart.yaml" ]]; then
  die "Helm chart not found at: ${HELM_CHART_DIR}/Chart.yaml"
fi
success "Helm chart found: ${HELM_CHART_DIR}"

if [[ "$DRY_RUN" == "true" ]]; then
  warn "DRY RUN mode — no changes will be applied"
fi

info "Deploy config:"
info "  Environment : ${ENV}"
info "  Cloud       : ${CLOUD}"
info "  Namespace   : ${NAMESPACE}"
info "  Portal image: ${PORTAL_IMAGE}"
info "  API image   : ${API_IMAGE}"
info "  Worker image: ${WORKER_IMAGE}"
info "  Deploy ID   : ${DEPLOY_ID}"

# ---------------------------------------------------------------------------
# Step 1: Terraform — init, plan, apply
# ---------------------------------------------------------------------------
CURRENT_STEP="terraform"
header "Step 1 — Terraform (${CLOUD^^})"

if [[ "$SKIP_TERRAFORM" == "true" ]]; then
  warn "Skipping Terraform (--skip-terraform flag set)"
else
  if [[ ! -d "$TERRAFORM_DIR" ]]; then
    die "Terraform directory not found: ${TERRAFORM_DIR}"
  fi

  pushd "$TERRAFORM_DIR" > /dev/null

  info "terraform init..."
  if [[ "$DRY_RUN" == "true" ]]; then
    info "[DRY RUN] would run: terraform init -input=false"
  else
    terraform init -input=false -upgrade 2>&1 | tail -5
    success "Terraform init complete"
  fi

  info "terraform plan..."
  PLAN_FILE="/tmp/${DEPLOY_ID}-tf.plan"
  if [[ "$DRY_RUN" == "true" ]]; then
    info "[DRY RUN] would run: terraform plan -var env=${ENV} -out=${PLAN_FILE}"
  else
    terraform plan \
      -var "env=${ENV}" \
      -input=false \
      -detailed-exitcode \
      -out="$PLAN_FILE" 2>&1 | tail -20 || {
        TF_EXIT=$?
        if [[ "$TF_EXIT" -eq 2 ]]; then
          info "Terraform plan shows changes — proceeding to apply"
        elif [[ "$TF_EXIT" -eq 0 ]]; then
          info "Terraform: no changes — infrastructure up to date"
          popd > /dev/null
          SKIP_TF_APPLY=true
        else
          die "Terraform plan failed (exit ${TF_EXIT})"
        fi
      }
    SKIP_TF_APPLY="${SKIP_TF_APPLY:-false}"
  fi

  if [[ "$DRY_RUN" == "false" && "${SKIP_TF_APPLY:-false}" == "false" ]]; then
    # Approval gate for production
    if [[ "$ENV" == "prod" ]]; then
      echo -e "\n${YELLOW}${BOLD}>>> PRODUCTION APPLY — Review the plan above.${NC}"
      read -r -p "Type 'yes' to apply to PRODUCTION: " CONFIRM
      if [[ "$CONFIRM" != "yes" ]]; then
        die "Deployment cancelled by user at Terraform production approval gate."
      fi
    fi

    info "terraform apply..."
    terraform apply -input=false -auto-approve "$PLAN_FILE"
    success "Terraform apply complete"
  fi

  popd > /dev/null
fi

# ---------------------------------------------------------------------------
# Step 2: Helm upgrade --install
# ---------------------------------------------------------------------------
CURRENT_STEP="helm"
header "Step 2 — Helm Deploy"

if [[ "$SKIP_HELM" == "true" ]]; then
  warn "Skipping Helm (--skip-helm flag set)"
else
  # Ensure namespace exists
  if ! kubectl get namespace "$NAMESPACE" &>/dev/null; then
    info "Creating namespace ${NAMESPACE}..."
    if [[ "$DRY_RUN" == "false" ]]; then
      kubectl create namespace "$NAMESPACE"
    else
      info "[DRY RUN] would create namespace ${NAMESPACE}"
    fi
  fi

  # Determine values file for environment
  VALUES_FILE="${HELM_CHART_DIR}/values.yaml"
  ENV_VALUES_FILE="${HELM_CHART_DIR}/values-${ENV}.yaml"
  VALUES_ARGS="-f ${VALUES_FILE}"
  if [[ -f "$ENV_VALUES_FILE" ]]; then
    VALUES_ARGS="${VALUES_ARGS} -f ${ENV_VALUES_FILE}"
    info "Using env-specific values: ${ENV_VALUES_FILE}"
  fi

  HELM_CMD=(
    helm upgrade --install "$HELM_RELEASE" "$HELM_CHART_DIR"
    --namespace "$NAMESPACE"
    ${VALUES_ARGS}
    --set "portal.image=${PORTAL_IMAGE}"
    --set "api.image=${API_IMAGE}"
    --set "worker.image=${WORKER_IMAGE}"
    --set "global.env=${ENV}"
    --atomic
    --wait
    --timeout "$DEPLOY_TIMEOUT"
    --history-max 5
    --description "deploy-id=${DEPLOY_ID}"
  )

  info "Running: ${HELM_CMD[*]}"

  if [[ "$DRY_RUN" == "true" ]]; then
    info "[DRY RUN] would run helm upgrade --install with above flags"
    helm upgrade --install "$HELM_RELEASE" "$HELM_CHART_DIR" \
      --namespace "$NAMESPACE" \
      ${VALUES_ARGS} \
      --set "global.env=${ENV}" \
      --dry-run 2>&1 | head -50
  else
    "${HELM_CMD[@]}"
    success "Helm upgrade complete"
  fi
fi

# ---------------------------------------------------------------------------
# Step 3: kubectl rollout status check
# ---------------------------------------------------------------------------
CURRENT_STEP="rollout-status"
header "Step 3 — Rollout Status"

if [[ "$DRY_RUN" == "false" ]]; then
  DEPLOYMENTS=(
    "deployment/${HELM_RELEASE}-portal"
    "deployment/${HELM_RELEASE}-api"
    "deployment/${HELM_RELEASE}-worker"
  )

  for deployment in "${DEPLOYMENTS[@]}"; do
    info "Checking rollout: ${deployment}..."
    if kubectl get "$deployment" -n "$NAMESPACE" &>/dev/null; then
      kubectl rollout status "$deployment" -n "$NAMESPACE" --timeout="$DEPLOY_TIMEOUT"
      success "${deployment} rolled out successfully"
    else
      warn "${deployment} not found — skipping (may be disabled in values)"
    fi
  done

  # Show pod status
  info "Current pod status in namespace ${NAMESPACE}:"
  kubectl get pods -n "$NAMESPACE" -o wide --sort-by='.status.startTime' 2>/dev/null | tail -20
else
  info "[DRY RUN] skipping rollout status check"
fi

# ---------------------------------------------------------------------------
# Step 4: Smoke Tests
# ---------------------------------------------------------------------------
CURRENT_STEP="smoke-tests"
header "Step 4 — Smoke Tests"

run_smoke_test() {
  local label="$1"
  local url="$2"
  local expected_code="${3:-200}"
  local max_attempts=5
  local attempt=0
  local delay=10

  while [[ $attempt -lt $max_attempts ]]; do
    attempt=$(( attempt + 1 ))
    info "  [${label}] attempt ${attempt}/${max_attempts}: ${url}"
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 "$url" 2>/dev/null || echo "000")
    if [[ "$HTTP_CODE" == "$expected_code" ]]; then
      success "  [${label}] HTTP ${HTTP_CODE} — PASS"
      return 0
    fi
    warn "  [${label}] HTTP ${HTTP_CODE} — retrying in ${delay}s..."
    sleep "$delay"
    delay=$(( delay * 2 ))
  done
  die "[${label}] smoke test FAILED after ${max_attempts} attempts (last code: ${HTTP_CODE})"
}

if [[ "$DRY_RUN" == "false" ]]; then
  # Determine base URL for smoke tests
  if [[ -n "$SMOKE_TEST_URL" ]]; then
    BASE_URL="$SMOKE_TEST_URL"
  else
    # Try to resolve via kubectl service
    SVC_IP=$(kubectl get svc "${HELM_RELEASE}-api" -n "$NAMESPACE" \
              -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
    SVC_HOSTNAME=$(kubectl get svc "${HELM_RELEASE}-api" -n "$NAMESPACE" \
                    -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "")
    BASE_URL="http://${SVC_IP:-$SVC_HOSTNAME}"
    if [[ -z "$SVC_IP" && -z "$SVC_HOSTNAME" ]]; then
      warn "Could not resolve API service external IP — using port-forward for smoke test"
      kubectl port-forward "svc/${HELM_RELEASE}-api" 8999:8000 -n "$NAMESPACE" &
      PF_PID=$!
      sleep 5
      BASE_URL="http://localhost:8999"
    fi
  fi

  run_smoke_test "API /health"   "${BASE_URL}/health"   200
  run_smoke_test "API /ready"    "${BASE_URL}/ready"    200
  run_smoke_test "API /version"  "${BASE_URL}/version"  200

  # Kill port-forward if we started one
  if [[ -n "${PF_PID:-}" ]]; then
    kill "$PF_PID" 2>/dev/null || true
  fi

  success "All smoke tests passed"
else
  info "[DRY RUN] skipping smoke tests"
fi

# ---------------------------------------------------------------------------
# Step 5: Record deploy metadata
# ---------------------------------------------------------------------------
CURRENT_STEP="record"
header "Step 5 — Recording Deploy"

ELAPSED=$(( $(date +%s) - DEPLOY_START ))
DEPLOY_SUMMARY=$(cat <<EOF
{
  "deploy_id": "${DEPLOY_ID}",
  "env": "${ENV}",
  "cloud": "${CLOUD}",
  "portal_image": "${PORTAL_IMAGE}",
  "api_image": "${API_IMAGE}",
  "worker_image": "${WORKER_IMAGE}",
  "namespace": "${NAMESPACE}",
  "duration_seconds": ${ELAPSED},
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "deployer": "$(git config user.email 2>/dev/null || echo 'ci')",
  "git_commit": "$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')",
  "git_branch": "$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'unknown')"
}
EOF
)

DEPLOY_LOG_DIR="${HOME}/.quantum-deploys"
mkdir -p "$DEPLOY_LOG_DIR"
echo "$DEPLOY_SUMMARY" > "${DEPLOY_LOG_DIR}/${DEPLOY_ID}.json"
info "Deploy log written to: ${DEPLOY_LOG_DIR}/${DEPLOY_ID}.json"

# ---------------------------------------------------------------------------
# Final: Success notification
# ---------------------------------------------------------------------------
header "Deployment Complete"
success "Deploy ${DEPLOY_ID} finished in ${ELAPSED}s"
echo ""
echo -e "  ${BOLD}Environment:${NC}  ${ENV}"
echo -e "  ${BOLD}Cloud:${NC}        ${CLOUD}"
echo -e "  ${BOLD}Namespace:${NC}    ${NAMESPACE}"
echo -e "  ${BOLD}Portal image:${NC} ${PORTAL_IMAGE}"
echo -e "  ${BOLD}API image:${NC}    ${API_IMAGE}"
echo -e "  ${BOLD}Worker image:${NC} ${WORKER_IMAGE}"
echo -e "  ${BOLD}Duration:${NC}     ${ELAPSED}s"
echo ""

slack_notify "success" "Deployment ${DEPLOY_ID} completed successfully in ${ELAPSED}s.\nImages: portal=${PORTAL_IMAGE}\nAPI=${API_IMAGE}"

exit 0
