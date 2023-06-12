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
$ terraform workspace select dev-py3
```

2. You need to set the following **REQUIRED** variables (as environment variables prefixing with `TF_VAR_` or variables in `terraform.tfvars`)
    * `prefix` : Make sure it's unique else, it will clash with other envs
    * `rds_vpc_cidr` : Pick an unused CIDR in the range `172.16.. - 172.29..` (defaults to `172.31.0.0/16`)
    * `db_password` : The password that will be set on the quay and clair RDS DBs
    * `deploy_type`: `primary` or `secondary` this is useful for multi-region setup (default `primary`)
    * `region` : AWS region to use for deployment (default `us-east-1`)
    * `openshift_vpc_id` : VPC ID where openshift is deployed (used for creating peering)
    * `openshift_cidrs`: CIDRs for openshift access to RDS (check the Openshift VPC to get this value)

3. If you are deploying a **secondary** region you'll also have to add the following **REQUIRED** variables
    * `primary_s3_bucket_arn`: ARN of the S3 bucket created in primary region. This will be used for setting up replication
    * `primary_db_arn`: ARM of the DB created in the primary region. This will be used for setting up replication

   
4. You could optionally set the following variables if required 
    * `aws_profile`: Set this if you are not using the default account set with AWS CLI
    * `quay_image`: Overrides the image that is being used 
    * `clair_image`: Overrides the image that being used
    * `quay_vpc_cidr`: CIDR of VPC where quay resources like DB, redis will be deployed
    * `builder_ssh_keypair`: SSH Keypair created to access the build VMs (should be created prior to deploy)
    * `builder_access_key`: AWS access key for builder. Used to createEC2 VMs for building
    * `builder_secret_key`: AWS Secret key for builder. Used to createEC2 VMs for building

The easiest way to get started is to use the provided environment variable samples in the `envs` directory

## Running

The following gives an example of creating a new environment from scratch

```bash
$ terraform workspace new syed-py3
$ terraform workspace select syed-py3
$ oc login <login token>
$ source envs/syed-py3.env
$ terraform apply
```

This command generates all the resources required and outputs `<prefix>-quay-deployment.yaml` file which you can deploy to openshift

```
kubectl apply -f <prefix>-quay-deployment.yaml
```

This should generate all the deployments for quay.

**NOTE** Terraform also generates a statefile `terraform.tfstate`. DO NOT DELETE this file or commit it. This file keeps track of all the resources on AWS assosiated with your workspace.

Once you get quay running, you can get the quay endpoint by running

```
$ oc project <prefix>-quay
$ kubectl get route
```


## Cleaning up

You need to cleanup both openshift and terraform. 

```
$ terraform destroy
```

