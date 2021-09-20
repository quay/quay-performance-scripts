# Infrastructure scripts for setting up Quay.io environments

These scripts create a working quay.io infrastructre on AWS for development.

## Prerequisites

1. AWS Account
1. OSD or a ROSA cluster
1. Terraform


## Setup

Before running the infra scripts, you need to:

* Install the Openshift CLI
* Make sure you have access to an OSD or a ROSA cluster and are logged in as `Cluster Admin` (you can do this via the `oc login` command)
* Install the AWS CLI
* Login to the AWS account from the CLI

## Installation

1. (Optional) Create a terraform workspace that you will be working on. This is useful if you are creating multiple environments.

```
$ terraform workspace new dev-py3
```

2. You need to set the following **REQUIRED** variables (as environment variables prefixing with `TF_VAR_` or variables in `terraform.tfvars`)
    * `prefix` : Make sure it's unique else, it will clash with other envs
    * `rds_vpc_cidr` : Pick an unused CIDR (defaults to `172.33.0.0/16`)
    * `db_password` : The password that will be set on the quay and clair RDS DBs
    
3. You could optionally set the following variables if required
    * `aws_profile`: Set this if you are not using the default account set with AWS CLI
    * `quay_image`: Overrides the image that is being used
    * `clair_image`: Overrides the image that being used

## Python2 or Python3 

By default the automation will start a python3 version of quay. If you want to setup a python2 (quayio) version of quay you need to update the `quay_image` to point to a python2 quay (`quay.io/app-sre/quay:3c9b9c1` for example) Before running `kubectl apply`



## Running

The following gives an example of creating a new environment from scratch

```bash
$ terraform workspace new syed-py3
$ export TF_VAR_prefix="syed-py3"
$ export TF_VAR_rds_vpc_cidr="172.38.0.0/16"
$ export TF_VAR_db_password="mydbpassword"
$ terraform apply
```

This command generates a `<prefix>-quay-deployment.yaml` file which you can deploy to openshift

```
kubectl apply -f <prefix>-quay-deployment.yaml
```

This should generate all the deployments for quay.

**NOTE** Terraform also generates a statefile `terraform.tfstate`. DO NOT DELETE this file or commit it. This file keeps track of all the resources on AWS assosiated with your workspace.

**NOTE for python 2 deployment** When you create the deployment for python2 quay, it may not start correctly because it expects a user to be present in the DB. This has to be done manually. 

```
  File "/opt/rh/python27/root/usr/lib/python2.7/site-packages/pymysql/err.py", line 109, in raise_mysql_exception
    raise errorclass(errno, errval)
peewee.IntegrityError: (1048, u"Column 'account_id' cannot be null")
```

Run the following query on the quay RDS to fix the above error

```
$ mysql -h <quay-rds-host> -P 3306 -p<db-password> -u quay <  quay-py2-setup.sql
```

You can get the Quay RDS host from the `terraform output` command

Once you get quay running, you can get the quay endpoint by running

```
$ oc project <prefix>-quay
$ kubectl get route
```

## Cleaning up

You need to cleanup both openshift and terraform. 

```
$ kubectl delete namespace <prefix>-quay
$ terraform destroy
```

