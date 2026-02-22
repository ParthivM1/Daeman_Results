param(
  [Parameter(Mandatory=$true)][string]$ApiToken,
  [string]$Backend = 'ibm_torino'
)

python -u src/validation3.py `
  --mode runtime `
  --backend $Backend `
  --api-token $ApiToken `
  --n-qubits 6 `
  --times 3200,4912,6400,8000 `
  --anchors 800,1600,2400,3200,4000,4800,5600,6400 `
  --arms BASE,X,XY4,BB1,CONTOUR `
  --shots-map 256 `
  --shots-stress 512 `
  --max-seconds 1800 `
  --output data/torino/validation3_torino_full_q6_runtime.json

python -u src/validation3.py `
  --mode runtime `
  --backend $Backend `
  --api-token $ApiToken `
  --n-qubits 8 `
  --times 3200,4912,6400,8000 `
  --anchors 800,1600,2400,3200,4000,4800,5600,6400 `
  --arms BASE,X,XY4,BB1,CONTOUR `
  --shots-map 256 `
  --shots-stress 512 `
  --max-seconds 1800 `
  --output data/torino/validation3_torino_full_q8_runtime.json

python -u src/validation3.py `
  --mode runtime `
  --backend $Backend `
  --api-token $ApiToken `
  --n-qubits 12 `
  --times 3200,4912,6400,8000 `
  --anchors 800,1600,2400,3200,4000,4800,5600,6400 `
  --arms BASE,X,XY4,BB1,CONTOUR `
  --shots-map 256 `
  --shots-stress 512 `
  --max-seconds 1800 `
  --output data/torino/validation3_torino_full_q12_runtime.json
