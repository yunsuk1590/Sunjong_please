# send_keys.ps1 - USB 선으로 W/A/S/D 를 컨트롤러처럼 「누르고 있는 것처럼」 반복해서 보내고, 차 보드의 로그를 시간과 함께 보여 줍니다.
# 윈도우 PowerShell 5.1 에서 씁니다. 라이브러리 설치가 필요 없습니다.
#
# 쓰는 법 (차를 바닥에 놓고, 앞뒤 1 m 를 비운 뒤):
#   powershell -ExecutionPolicy Bypass -File send_keys.ps1 -Port COM5
#   powershell -ExecutionPolicy Bypass -File send_keys.ps1 -Port COM5 -Plan "W:1000;W+A:1500;A:500;S:800"
#
# -Plan 은 「글자:누르는 시간(ms)」 를 ; 로 이은 것입니다. 글자를 + 로 이으면 동시에 누른 것입니다(W+A = 앞 + 왼쪽).
# 각 단계가 끝나면 글자를 보내지 않고 0.9초 기다립니다. 그때 차가 스스로 서는지(0.3초 시간 제한) 로그로 볼 수 있습니다.
# 포트를 열면 보드가 다시 켜집니다. 약 2.5초 기다린 뒤 보내기 시작합니다.
# COM 포트는 한 번에 한 프로그램만 열 수 있습니다. 아두이노 프로그램의 시리얼 모니터를 닫고 쓰세요.
param(
    [Parameter(Mandatory = $true)][string]$Port,
    [string]$Plan = 'W:1000;W+A:1000;A:500;D:500;S:800',
    [int]$IntervalMs = 150
)
$ErrorActionPreference = 'Stop'
$rd = New-Object System.IO.Ports.SerialPort $Port, 9600, 'None', 8, 'One'
$rd.Encoding = [System.Text.Encoding]::UTF8
$rd.DtrEnable = $true
$sw = [System.Diagnostics.Stopwatch]::StartNew()
$script:buf = ''

# 보드가 보낸 줄을 시간과 함께 보여 줍니다.
function Pump([int]$ms) {
    $end = $sw.ElapsedMilliseconds + $ms
    while ($sw.ElapsedMilliseconds -lt $end) {
        $t = $rd.ReadExisting()
        if ($t) {
            $script:buf += $t
            while ($script:buf.Contains("`n")) {
                $i = $script:buf.IndexOf("`n")
                '{0,6} ms  <- {1}' -f $sw.ElapsedMilliseconds, $script:buf.Substring(0, $i).TrimEnd("`r")
                $script:buf = $script:buf.Substring($i + 1)
            }
        }
        Start-Sleep -Milliseconds 2
    }
}

try {
    $rd.Open()
    "--- $Port 열림 (보드가 다시 켜집니다) ---"
    Pump 2500
    foreach ($step in $Plan.Split(';')) {
        $p = $step.Split(':')
        $keys = $p[0].Split('+')
        $ms = [int]$p[1]
        '{0,6} ms  === {1} 를 {2} ms 동안 누름 ===' -f $sw.ElapsedMilliseconds, $p[0], $ms
        $end = $sw.ElapsedMilliseconds + $ms
        $next = $sw.ElapsedMilliseconds
        while ($sw.ElapsedMilliseconds -lt $end) {
            if ($sw.ElapsedMilliseconds -ge $next) {
                foreach ($k in $keys) { $rd.Write($k) }
                $next += $IntervalMs
            }
            Pump 5
        }
        '{0,6} ms  === 뗌 (글자를 안 보냄) ===' -f $sw.ElapsedMilliseconds
        Pump 900
    }
    '--- 끝 ---'
}
finally {
    if ($rd.IsOpen) { $rd.Close() }
}
