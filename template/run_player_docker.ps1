param(
    [Parameter(Mandatory=$true)]
    [string]$PlayerPath,
    [int]$Seed = 0
)

$resolved = Resolve-Path -LiteralPath $PlayerPath
$playerDir = Split-Path -Parent $resolved
$playerFile = Split-Path -Leaf $resolved

docker run --rm -i `
    --network none `
    --read-only `
    --cpus "0.5" `
    --memory "128m" `
    -v "${playerDir}:/player:ro" `
    python:3.12-slim `
    python "/player/$playerFile" --seed $Seed
