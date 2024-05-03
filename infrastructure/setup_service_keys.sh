set -euo pipefail

# Verify arguments
if [ $# -eq 0 || -z "$1" || -z "$2"]; then
    echo "Missing required arguments, run script with the following arguments: ./setup_service_keys.sh <quay_db_password> <quay_db_host>"
    exit 1
fi

# Setup working directory
rm -rf service-key-generator
mkdir service-key-generator
cd service-key-generator

# Setup python environment, pull generatekeypair.py script, and install dependencies
python -m venv venv
source venv/bin/activate
curl https://raw.githubusercontent.com/quay/quay/master/tools/generatekeypair.py -o generatekeypair.py
cat << EOF > requirements-generatekeys.txt
cryptography==3.4.7
pycparser==2.19
pycryptodome==3.9.4
pycryptodomex==3.9.4
pyjwkest==1.4.2
PyJWT==1.7.1
Authlib==1.0.0a2
EOF
pip install -r requirements-generatekeys.txt

# Generate quay-readonly.pem, quay-readonly.kid, and quay-readonly.jwk
python generatekeypair.py quay-readonly

# Write out SQL commands for updating service keys
cat << EOF > update_service_keys.sql
INSERT INTO servicekey (name, service, metadata, kid, jwk, created_date, expiration_date) 
    VALUES ('quay-readonly', 
                'quay', 
                '{}', 
                'QUAY_READONLY_KID',   
                'QUAY_READONLY_JWK',
                '2024-01-01 00:00:00', 
                '2025-01-01 00:00:00');

INSERT INTO servicekeyapproval (approved_date, approval_type, notes)
    VALUES ('2024-01-01 00:00:00', 'Quay Readonly Service Key', 'approval notes');

UPDATE servicekey SET approval_id=servicekeyapproval.id FROM servicekeyapproval 
    WHERE servicekey.name = 'quay-readonly' AND servicekeyapproval.approval_type='Quay Readonly Service Key';
EOF
sed -i -e "s/QUAY_READONLY_KID/$(cat quay-readonly.kid)/g"  update_service_keys.sql
sed -i -e "s/QUAY_READONLY_JWK/$(cat quay-readonly.jwk)/g"  update_service_keys.sql

# Run script to update service keys
PGPASSWORD=$1 psql -U quay -h $2 < update_service_keys.sql

deactivate

echo "Service key generated and applied to the primary environment successfully, db host: ($2)"
echo "Create the terraform variables for the secondary environment with the following:"
echo "export TF_VAR_service_key_kid_path='$(pwd)/quay-readonly.kid'"
echo "export TF_VAR_service_key_jwt_path='$(pwd)/quay-readonly.jwk'"
