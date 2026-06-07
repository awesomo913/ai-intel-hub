# install_ps_banner.ps1
# Run ONCE to add the AI Intel Hub terminal banner to your PowerShell profile.
# After this, any breakthrough alert will print a colored banner at the next prompt.

$alertFile = "$env:USERPROFILE\.claude\tmp\alerts\latest.json"

$hook = @"

# ── AI Intel Hub terminal banner ────────────────────────────────────────────
function _aih_check_banner {
    `$f = '$alertFile'
    if (-not (Test-Path `$f)) { return }
    try {
        `$a = Get-Content `$f -Raw | ConvertFrom-Json
        if (-not `$a.seen) {
            Write-Host ""
            Write-Host "  ★ AI INTEL HUB ALERT ★" -ForegroundColor Cyan
            Write-Host "  `$(`$a.title)" -ForegroundColor Yellow
            if (`$a.message) { Write-Host "  `$(`$a.message)" -ForegroundColor White }
            if (`$a.url)     { Write-Host "  `$(`$a.url)"     -ForegroundColor DarkGray }
            Write-Host ""
            `$a.seen = `$true
            `$a | ConvertTo-Json | Set-Content `$f -Encoding utf8
        }
    } catch { Write-Warning "AI Intel Hub banner error: $_" }
}
`$origPrompt = if (Test-Path Function:\Prompt) { (Get-Item Function:\Prompt).ScriptBlock } else { { "PS> " } }
function global:Prompt {
    _aih_check_banner
    & `$origPrompt
}
# ────────────────────────────────────────────────────────────────────────────
"@

# Create profile file if it doesn't exist
if (-not (Test-Path $PROFILE)) {
    New-Item -ItemType File -Path $PROFILE -Force | Out-Null
}

# Don't double-install
if ((Get-Content $PROFILE -Raw) -match "AI Intel Hub terminal banner") {
    Write-Host "Banner hook already installed in `$PROFILE" -ForegroundColor Yellow
} else {
    Add-Content -Path $PROFILE -Value $hook -Encoding utf8
    Write-Host "Banner hook installed in `$PROFILE" -ForegroundColor Green
    Write-Host "Restart your PowerShell session (or `. `$PROFILE`) to activate." -ForegroundColor Cyan
}
