# Quay Perf Testing
## Assumptions
The Quay Operator has been deployed.

## Additionall Tooling
This script assumes the Vegeta binary is colocated with the scripts.

### To install Vegeta simply

```
$ wget https://github.com/tsenart/vegeta/releases/download/v12.8.3/vegeta-12.8.3-linux-amd64.tar.gz
$ tar -xzf vegeta-12.8.3-linux-amd64.tar.gz
```

This will drop in an binary which we will execute with the scripts.

## Database
The database provided here is a dump from psql with a token generated for organization `test`

## Token
The default token is `opiqq6KJpCnn4YWqS4kkPku7pohjfzKX10EOGrUi`, after running the `quay_init.sh` script run the following

```
$ curl -k -X GET -H "Authorization: Bearer opiqq6KJpCnn4YWqS4kkPku7pohjfzKX10EOGrUi"  https://rook-quay-quay-openshift-quay.apps.rook43quay.perf-testing.devcluster.openshift.com/api/v1/superuser/users/
{"users": [{"username": "quay", "kind": "user", "verified": true, "name": "quay", "super_user": true, "enabled": true, "email": "changeme@example.com", "avatar": {"color": "#8c6d31", "kind": "user", "hash": "5cc105f67a24cab8379ad1cfd5dfdebb", "name": "quay"}}]}
```

## targeted-build-script.sh
Script that will create 4 repos by default, each with different amount of tags:

- Repo with 10 tags
- Repo with 100 tags
- Repo with 500 tags
- Repo with 1000 tags

This script will choose a random user to build all the above with.

