set -euo pipefail
hatch build -t sdist
scp -i "$SSH_KEY_FILE" dist/*.tar.gz scp://"$SSH_SERVER"//home/malinedo/malinedo/
