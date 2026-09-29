$ErrorActionPreference = "Continue"

$startTime = Get-Date
$durationMinutes = 75
$endTime = $startTime.AddMinutes($durationMinutes)

# ---------------------------------------------------------------------------
# Model/Provider Configuration
# ---------------------------------------------------------------------------
# Each entry defines a model with its provider-specific invocation properties.
# Models are ordered strongest-first for preferred cycling.
#
# Properties:
#   id           - exact agy --model identifier
#   provider     - runtime provider (currently only "antigravity")
#   effort       - value for --effort flag, or $null if unsupported
#   timeout      - value for --print-timeout
#   extraArgs    - array of additional CLI arguments (or empty)
#   capability   - human label for logging
# ---------------------------------------------------------------------------

$models = @(
    @{
        id         = "claude-opus-4-6-thinking"
        provider   = "antigravity"
        effort     = "high"
        timeout    = "20m"
        extraArgs  = @()
        capability = "Claude Opus 4.6 (Thinking) -- strongest reasoning"
    },
    @{
        id         = "gemini-3.1-pro-high"
        provider   = "antigravity"
        effort     = $null          # effort is baked into the model identifier
        timeout    = "20m"
        extraArgs  = @()
        capability = "Gemini 3.1 Pro (High) -- strong general coding"
    },
    @{
        id         = "claude-sonnet-4-6"
        provider   = "antigravity"
        effort     = $null          # --effort is NOT supported for this model
        timeout    = "20m"
        extraArgs  = @()
        capability = "Claude Sonnet 4.6 -- fast strong coding"
    },
    @{
        id         = "gpt-oss-120b-medium"
        provider   = "antigravity"
        effort     = $null          # effort is baked into the model identifier
        timeout    = "20m"
        extraArgs  = @()
        capability = "GPT-OSS 120B (Medium) -- capable fallback"
    },
    @{
        id         = "gemini-3.8-flash-high"
        provider   = "antigravity"
        effort     = $null
        timeout    = "20m"
        extraArgs  = @()
        capability = "Gemini 3.8 Flash (High) -- fast fallback"
    },
    @{
        id         = "gemini-3.7-flash-high"
        provider   = "antigravity"
        effort     = $null
        timeout    = "20m"
        extraArgs  = @()
        capability = "Gemini 3.7 Flash (High) -- fast fallback"
    },
    @{
        id         = "gemini-3.1-pro-low"
        provider   = "antigravity"
        effort     = $null
        timeout    = "20m"
        extraArgs  = @()
        capability = "Gemini 3.1 Pro (Low) -- low-effort fallback"
    }
)

# ---------------------------------------------------------------------------
# Failure Tracking / Cooldown State
# ---------------------------------------------------------------------------
# Track consecutive failures and cooldown expiry per model.
# A model that fails is given an escalating cooldown before retry.
# This prevents pathological rapid retries against exhausted/broken models
# while allowing recovery when quota refreshes or transient errors clear.
# ---------------------------------------------------------------------------

$modelState = @{}
foreach ($m in $models) {
    $modelState[$m.id] = @{
        consecutiveFailures = 0
        cooldownUntil       = [datetime]::MinValue
    }
}

# Cooldown escalation: 30s, 2m, 5m, 10m, 15m (capped)
$cooldownSeconds = @(30, 120, 300, 600, 900)

function Get-CooldownSeconds([int]$failures) {
    $idx = [math]::Min($failures - 1, $cooldownSeconds.Length - 1)
    if ($idx -lt 0) { return 0 }
    return $cooldownSeconds[$idx]
}

# ---------------------------------------------------------------------------
# Provider Invocation
# ---------------------------------------------------------------------------
# Abstracted so future runtimes (Gemini CLI, etc.) can be added without
# rewriting the main loop.  Each provider implements:
#   Invoke-<Provider>Agent -Config <model> -Prompt <string>
# and returns the process exit code.
# ---------------------------------------------------------------------------

function Invoke-AntigravityAgent {
    param(
        [hashtable]$Config,
        [string]$Prompt
    )

    $args_list = @(
        "--continue",
        "--dangerously-skip-permissions",
        "--model", $Config.id,
        "--print-timeout", $Config.timeout,
        "--print", $Prompt
    )

    # Only add --effort when the model actually supports it
    if ($Config.effort) {
        $args_list = @(
            "--continue",
            "--dangerously-skip-permissions",
            "--effort", $Config.effort,
            "--model", $Config.id,
            "--print-timeout", $Config.timeout,
            "--print", $Prompt
        )
    }

    # Append any model-specific extra arguments
    foreach ($extra in $Config.extraArgs) {
        $args_list += $extra
    }

    Write-Host "  Command: agy $($args_list -join ' ')" -ForegroundColor DarkGray

    & agy @args_list
    return $LASTEXITCODE
}

function Invoke-RuntimeAgent {
    param(
        [hashtable]$Config,
        [string]$Prompt
    )

    switch ($Config.provider) {
        "antigravity" {
            return Invoke-AntigravityAgent -Config $Config -Prompt $Prompt
        }
        default {
            Write-Host "  ERROR: Unknown provider '$($Config.provider)'" -ForegroundColor Red
            return 1
        }
    }
}

# ---------------------------------------------------------------------------
# System Prompt (unchanged from working version)
# ---------------------------------------------------------------------------

$sysPrompt = @"
---
CONTINUE AUTONOMOUS DEVELOPMENT OF BIOCATALYST.

You are operating as the autonomous lead software engineer, biotech quantitative
analyst, QA engineer and methodology reviewer for BioCatalyst.

This is NOT a request for a progress report.

Inspect the current repository state, Git history/diff, tests,
QUALITY_SCORECARD.md, development/review documentation and work produced by
previous autonomous cycles.

Determine the highest-value remaining weakness and work on it immediately.

Use this recurring process:

INSPECT
-> CRITIQUE
-> SELECT HIGHEST-VALUE WEAKNESS
-> IMPLEMENT
-> TEST
-> VALIDATE
-> UPDATE QUALITY/DEVELOPMENT RECORDS
-> REASSESS
-> BEGIN NEXT IMPROVEMENT

Priority:

1. Incorrect or misleading clinical, financial or scientific analysis
2. Silent data failures and invalid assumptions
3. Financial and catalyst methodology
4. Data acquisition and reliability
5. Multi-agent synthesis and scoring
6. Missing adversarial/regression tests
7. Architecture and maintainability
8. Evidence provenance and uncertainty
9. UX/UI and product polish
10. Lower-value improvements

Do not merely recommend improvements. Implement them when appropriate.

Do not stop because:
- tests pass
- one task is complete
- the application works
- the quality score improved
- the UI looks acceptable
- no obvious bugs remain

Critically reassess previous agent changes.

Passing tests demonstrate that implementation behaves as expected; they do NOT
prove that the underlying clinical, biological, statistical or financial
methodology is valid.

Specifically challenge:
- fixed catalyst timing delays
- burn-rate calculations
- cash-runway assumptions
- dilution thresholds
- composite scoring
- score clamps
- biological heuristics
- arbitrary numerical constants
- false precision

Preserve meaningful distinctions between:
- efficacy
- statistical evidence
- solvency
- catalyst timing
- confidence
- uncertainty

Generate adversarial edge cases.

When a weakness is fixed, add an appropriate regression test whenever practical.

Avoid feature bloat.

Correctness and methodological validity take priority over adding features.

When one improvement is complete, immediately begin another worthwhile
improvement within the remaining execution time.

Do not ask whether you should continue.

If the current agent turn ends, leave the repository stable so the external
controller can immediately start another continuation turn.

BioCatalyst has no normal completion condition during this autonomous session.
---
"@

# ---------------------------------------------------------------------------
# Select Next Available Model
# ---------------------------------------------------------------------------
# Returns the index of the best available model (first model not on cooldown),
# or -1 if all models are currently on cooldown.
# ---------------------------------------------------------------------------

function Select-NextModel {
    param([int]$preferredStart)

    $now = Get-Date
    $count = $models.Length

    # Try from preferred start, then wrap around
    for ($i = 0; $i -lt $count; $i++) {
        $idx = ($preferredStart + $i) % $count
        $mid = $models[$idx].id
        $state = $modelState[$mid]

        if ($now -ge $state.cooldownUntil) {
            return $idx
        }
    }
    return -1
}

function Get-EarliestCooldownExpiry {
    $earliest = [datetime]::MaxValue
    foreach ($m in $models) {
        $until = $modelState[$m.id].cooldownUntil
        if ($until -lt $earliest) {
            $earliest = $until
        }
    }
    return $earliest
}

# ---------------------------------------------------------------------------
# Main Loop
# ---------------------------------------------------------------------------

$currentModelIndex = 0
$cycleNumber = 0

while ((Get-Date) -lt $endTime) {
    $remaining = $endTime - (Get-Date)
    $remainingMinutes = [math]::Round($remaining.TotalMinutes, 1)

    if ($remainingMinutes -le 0.5) {
        Write-Host "Less than 30 seconds remaining. Ending session." -ForegroundColor Yellow
        break
    }

    # Select the next non-cooled-down model
    $selectedIndex = Select-NextModel -preferredStart $currentModelIndex

    if ($selectedIndex -eq -1) {
        # All models on cooldown -- wait for the earliest to expire
        $earliest = Get-EarliestCooldownExpiry
        $waitSeconds = [math]::Ceiling(($earliest - (Get-Date)).TotalSeconds)

        if ($waitSeconds -gt 0) {
            # Don't wait past the overall deadline
            $remainSeconds = [math]::Ceiling(($endTime - (Get-Date)).TotalSeconds)
            $waitSeconds = [math]::Min($waitSeconds, $remainSeconds)

            if ($waitSeconds -le 0) { break }

            Write-Host ""
            Write-Host "All models on cooldown. Waiting $waitSeconds seconds..." -ForegroundColor Yellow
            Start-Sleep -Seconds $waitSeconds
        }
        continue
    }

    $currentModelIndex = $selectedIndex
    $config = $models[$currentModelIndex]
    $cycleNumber++

    Write-Host ""
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host "Autonomous Cycle #$cycleNumber" -ForegroundColor Green
    Write-Host "Time Remaining: $remainingMinutes minutes" -ForegroundColor Yellow
    Write-Host "Model: $($config.id)" -ForegroundColor Yellow
    Write-Host "  ($($config.capability))" -ForegroundColor DarkYellow
    Write-Host "Provider: $($config.provider)" -ForegroundColor Yellow
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host ""

    $exitCode = Invoke-RuntimeAgent -Config $config -Prompt $sysPrompt

    $state = $modelState[$config.id]

    if ($exitCode -ne 0) {
        $state.consecutiveFailures++
        $cd = Get-CooldownSeconds $state.consecutiveFailures
        $state.cooldownUntil = (Get-Date).AddSeconds($cd)

        Write-Host ""
        Write-Host "WARNING: $($config.id) exited with code $exitCode (failure #$($state.consecutiveFailures))" -ForegroundColor Red
        Write-Host "  Cooldown: $cd seconds (until $($state.cooldownUntil.ToString('HH:mm:ss')))" -ForegroundColor Red
        Write-Host "  Advancing to next available model..." -ForegroundColor Yellow

        # Advance preferred index so next iteration tries the next model
        $currentModelIndex = ($currentModelIndex + 1) % $models.Length

        # Brief pause before trying next model (avoids tight error loops)
        Start-Sleep -Seconds 3
    } else {
        # Success -- reset failure state for this model
        $state.consecutiveFailures = 0
        $state.cooldownUntil = [datetime]::MinValue

        Write-Host ""
        Write-Host "Cycle #$cycleNumber completed successfully." -ForegroundColor Green

        # Stay on the same model for the next cycle (it's working)
        Start-Sleep -Seconds 2
    }
}

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "Autonomous Session Completed ($durationMinutes minutes reached)." -ForegroundColor Green
Write-Host "Total cycles attempted: $cycleNumber" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Cyan
