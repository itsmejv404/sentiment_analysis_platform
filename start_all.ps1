$ErrorActionPreference = "Stop"

function Test-Cli {
	param([string]$CommandName)
	return [bool](Get-Command $CommandName -ErrorAction SilentlyContinue)
}

function Get-EnvVarValueFromFile {
	param(
		[string]$FilePath,
		[string]$Key
	)

	if (-not (Test-Path $FilePath)) {
		return $null
	}

	$line = Get-Content $FilePath | Where-Object { $_ -match "^\s*$Key\s*=" } | Select-Object -First 1
	if (-not $line) {
		return $null
	}

	return ($line -replace "^\s*$Key\s*=", "").Trim()
}

function Get-LocalPythonCommand {
	param(
		[string]$WorkingDir,
		[string]$Name
	)

	$fullDir = Join-Path $PSScriptRoot $WorkingDir
	$candidates = @(
		(Join-Path $fullDir "venv\Scripts\python.exe"),
		(Join-Path $fullDir ".venv\Scripts\python.exe")
	)

	foreach ($candidate in $candidates) {
		if (Test-Path $candidate) {
			return "`"$candidate`""
		}
	}

	if (Test-Cli "python") {
		Write-Host "[$Name] Local venv python not found; falling back to global python from PATH." -ForegroundColor Yellow
		return "python"
	}

	throw "[$Name] No local python executable found in venv/.venv and python is not in PATH."
}

function Start-SmsaProcess {
	param(
		[string]$Name,
		[string]$WorkingDir,
		[string]$Command
	)

	$fullDir = Join-Path $PSScriptRoot $WorkingDir
	if (-not (Test-Path $fullDir)) {
		throw "[$Name] Missing folder: $fullDir"
	}

	# Find and activate venv
	$venvActivate = $null
	$candidates = @(
		(Join-Path $PSScriptRoot "backend\.venv\Scripts\Activate.ps1"),
		(Join-Path $PSScriptRoot "backend\venv\Scripts\Activate.ps1"),
		(Join-Path $fullDir ".venv\Scripts\Activate.ps1"),
		(Join-Path $fullDir "venv\Scripts\Activate.ps1")
	)
	
	foreach ($candidate in $candidates) {
		if (Test-Path $candidate) {
			$venvActivate = $candidate
			break
		}
	}

	$activationCommand = if ($venvActivate) { ". `"$venvActivate`"" } else { "" }
	$shellCommand = "Set-Location `"$fullDir`"; $activationCommand; $Command"
	Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $shellCommand -WindowStyle Normal | Out-Null
	Write-Host "Started $Name" -ForegroundColor Green
}

Write-Host "Starting Social Media Sentiment Analysis" -ForegroundColor Cyan

$backendEnv = Join-Path $PSScriptRoot "backend\.env"
$razorpayKeyId = Get-EnvVarValueFromFile -FilePath $backendEnv -Key "RAZORPAY_KEY_ID"
$razorpayKeySecret = Get-EnvVarValueFromFile -FilePath $backendEnv -Key "RAZORPAY_KEY_SECRET"
if ([string]::IsNullOrWhiteSpace($razorpayKeyId) -or [string]::IsNullOrWhiteSpace($razorpayKeySecret)) {
	Write-Host "[Billing] Razorpay credentials are missing in backend/.env. Credit purchase flow will not work." -ForegroundColor Yellow
} else {
	Write-Host "[Billing] Razorpay credentials detected in backend/.env." -ForegroundColor Green
}

if (-not (Test-Cli "npm")) {
	throw "npm is required but not found in PATH."
}

$backendPython = Get-LocalPythonCommand -WorkingDir "backend" -Name "Backend"
$mlPython = Get-LocalPythonCommand -WorkingDir "ml" -Name "ML"
$producerPython = Get-LocalPythonCommand -WorkingDir "producer" -Name "Producer"

# 1. Backend API
Start-SmsaProcess -Name "Backend API" -WorkingDir "." -Command "$backendPython -m uvicorn backend.main:app --reload --port 8000"

# 2. Celery worker
Start-SmsaProcess -Name "Celery Worker" -WorkingDir "." -Command "$backendPython -m celery -A backend.celery.celery_worker.celery_app worker --loglevel=info -P gevent"

# 3. Alert cron
Start-SmsaProcess -Name "Alert Cron" -WorkingDir "." -Command "$backendPython -m backend.cron.alert_cron"

# 4. Billing cron
Start-SmsaProcess -Name "Billing Cron" -WorkingDir "." -Command "$backendPython -m backend.cron.billing_cron"

# 5. ML API
Start-SmsaProcess -Name "ML API" -WorkingDir "ml" -Command "$mlPython jv.py"

# 6. Reddit producer
Start-SmsaProcess -Name "Reddit Producer" -WorkingDir "producer" -Command "$producerPython reddit_producer.py"

# 7. Processing worker
Start-SmsaProcess -Name "Processing Worker" -WorkingDir "producer" -Command "$producerPython worker.py"

# 8. Frontend
Start-SmsaProcess -Name "Frontend" -WorkingDir "frontend" -Command "npm run dev"

Write-Host "" 
Write-Host "All 8 services launched." -ForegroundColor Cyan
Write-Host "Backend API : http://localhost:8000" -ForegroundColor White
Write-Host "ML NLP API  : http://localhost:8001" -ForegroundColor White
Write-Host "Frontend    : http://localhost:5173" -ForegroundColor White
Write-Host "MailHog UI  : http://localhost:8025" -ForegroundColor White
