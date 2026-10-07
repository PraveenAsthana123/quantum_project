#!/usr/bin/env bash
# VS Code Extension Cleanup — Quantum Workspace
# Removes 100+ duplicate/redundant extensions that cause crashes
# Run: bash scripts/vscode-cleanup.sh

echo "=== VS Code Extension Cleanup ==="
echo "Removing duplicate Ollama, Gemini, ChatGPT, and Java extensions..."
echo ""

# ── 20+ DUPLICATE OLLAMA EXTENSIONS (keep none — Continue.dev is better) ──
OLLAMA_DUPES=(
  10nates.ollama-autocoder
  alejandrog.ollama-copilot-bridge
  ashishalex.ollama-chat
  binief.ollama-editor
  cgaspard.ollama-code
  dartyushin.ollama-participant
  datnguye.ollama-code-pilot
  denraskovalov.ollama-free-coder
  desislavarashev.ollama-commit
  diegoomal.ollama-connection
  easyonewebllc.easy-ollama
  guzmandrade-dev.ollama-fim
  herzcthu.ollama-vscode
  internetics.mcp-ollama-extension
  josephgodwinke.vscode-ollama-assistant
  namdang.ollama-copilot-vscode
  nejahillc.ai-assistant-ollama
  ntprogress.ollama-ntpro
  ntpro.ntpro-ollama
  ollama-agentz.ollama-agentz
  ollama-architect.ollama-architect-vsx
  ollama-cloud-usage.ollama-cloud-usage
  ollamascriptcode.ollama-script-code
  oswaldodantas.ollama-view
  profanterdev.ollama-code-completions
  rajputrajat1990.ollama-agent-rajputrajat1990
  rivanmota.ollama-ai
  technovangelist.ollamamodelfile
  vaibhavrathod.ollama-vscode-chat
  vinsg.ollama-agent
  vinhnguyen-vincent.ollama-code-review
  warm3snow.vscode-ollama
  warm3snow.vscode-ollama-modelfile
)

# ── 15+ DUPLICATE GEMINI EXTENSIONS (keep only google.geminicodeassist) ───
GEMINI_DUPES=(
  aaronduino.gemini
  abdullahaltaheri.gemini-ai-codeing-assistant
  acebunny00.gemini-cli-launcher
  boonboonsiri.gemini-autocomplete
  bini.vscode-gemini-assistant
  codegemini.gemini-theme
  d3j.gemini-cli-on-vscode
  edp1097.vscode-hello-gemini
  floopy-potato.gemini-commit-message
  galacticgit.gemini-chat
  imigueldiaz.gemini-glow
  liamlee.run-gemini-with-terminal-right
  printfn.gemini-improved
  rafalusworks.gemini-python-color-theme
  shawnchee.vscode-gemini-commit-writer
  shishirregmi.generate-code-gemini
  tcchan.gemini-code
  theolin-nadasen.gemini-coder-pro
  wizz.gemini-agent
  yechielby.gemini-code-assist-rtl
  zazmic.palm-api-test-generator
  zhigang.vscode-gemini-sidebar
)

# ── 5+ DUPLICATE CHATGPT EXTENSIONS (keep openai.chatgpt only) ────────────
CHATGPT_DUPES=(
  colourafredi.chatgpt-dev
  easycodeai.chatgpt-gpt4-gpt3-vscode
  feiskyer.chatgpt-copilot
  yalehuang.chatgpt-ai
)

# ── DUPLICATE CLAUDE EXTENSIONS (keep anthropic.claude-code only) ─────────
CLAUDE_DUPES=(
  saoudrizwan.claude-dev
  growthjack.claude-code-usage
)

# ── JAVA/GRADLE (no .java or .gradle files in quantum workspace) ───────────
JAVA_DUPES=(
  redhat.java
  vscjava.vscode-gradle
  vscjava.vscode-java-debug
  vscjava.vscode-java-dependency
  vscjava.vscode-java-pack
  vscjava.vscode-java-test
  vscjava.vscode-maven
)

# ── OTHER UNUSED/REDUNDANT ─────────────────────────────────────────────────
OTHER_DUPES=(
  openai.codex-audio
  woozy-masta.codex-switch
  martinortiz.codex-stats
  ms-vscode.cmake-tools
  ms-vscode.cpp-devtools
  ms-vscode.cpptools
  ms-vscode.cpptools-extension-pack
  ms-vscode.cpptools-themes
  github.codespaces
  googlecloudtools.cloudcode
  googlecloudtools.datacloud
  ms-azure-devops.azure-pipelines
  ms-azuretools.vscode-containers
)

uninstall_list=(
  "${OLLAMA_DUPES[@]}"
  "${GEMINI_DUPES[@]}"
  "${CHATGPT_DUPES[@]}"
  "${CLAUDE_DUPES[@]}"
  "${JAVA_DUPES[@]}"
  "${OTHER_DUPES[@]}"
)

total=${#uninstall_list[@]}
done=0
skipped=0

for ext in "${uninstall_list[@]}"; do
  if code --list-extensions 2>/dev/null | grep -q "^${ext}$"; then
    echo "  Removing: $ext"
    code --uninstall-extension "$ext" --force 2>/dev/null && ((done++)) || ((skipped++))
  else
    echo "  Already gone: $ext"
    ((skipped++))
  fi
done

echo ""
echo "=== Done ==="
echo "  Removed : $done"
echo "  Skipped : $skipped (not installed)"
echo "  Total   : $total"
echo ""
echo "KEPT (useful):"
echo "  anthropic.claude-code    — Claude Code"
echo "  continue.continue        — Ollama/local LLM (replaces all ollama-* dupes)"
echo "  google.geminicodeassist  — Gemini (official Google only)"
echo "  github.copilot           — Copilot"
echo "  ms-python.*              — Python"
echo "  ms-toolsai.jupyter*      — Jupyter"
echo "  eamodio.gitlens          — Git"
echo ""
echo "Reload VS Code: Ctrl+Shift+P → Developer: Reload Window"
