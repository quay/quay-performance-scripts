# Infrastructure scripts for setting up Quay.io environments

These scripts create a working quay.io infrastructure on AWS for development.

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

1. Ensure the AWS CLI is installed and configured. Run `aws configure` to setup installation. An access and secret key will be required. [Documentation for configuring AWS cli.](https://docs.aws.amazon.com/cli/latest/reference/configure/)

1. Log into the OCP cluster with `oc login`. Credentials can be retrieved via Openshift console.

1. (optional) Create a new terraform workspace. If creating a secondary instance use a new workspace.

    ```
    $ terraform workspace new primary
    $ terraform workspace select primary
    ```

1. You need to set the following **REQUIRED** variables (as environment variables prefixing with `TF_VAR_` or variables in `terraform.tfvars`)
    * `prefix` : Make sure it's unique else, it will clash with other envs
    * `rds_vpc_cidr` : Pick an unused CIDR in the range `172.16.. - 172.29..` (defaults to `172.31.0.0/16`)
    * `db_password` : The password that will be set on the quay and clair RDS DBs
    * `deploy_type`: `primary` or `secondary` this is useful for multi-region setup (default `primary`)
    * `region` : AWS region to use for deployment (default `us-east-1`)
    * `openshift_vpc_id` : VPC ID where openshift is deployed (used for creating peering)
    * `openshift_cidrs`: CIDRs for openshift access to RDS (check the Openshift VPC to get this value)

1. If you are deploying a **secondary** region you'll also have to add the following **REQUIRED** variables
    * `primary_s3_bucket_arn`: ARN of the S3 bucket created in primary region. This will be used for setting up replication
    * `primary_db_arn`: ARM of the DB created in the primary region. This will be used for setting up replication
    * `primary_db_hostname`: Hostname of the primary DB, used for setting up the service key when using the secondary deployment
    * `primary_db_password`: Password of the primary DB, used for setting up the service key when using the secondary deployment
   
1. You could optionally set the following variables if required 
    * `aws_profile`: Set this if you are not using the default account set with AWS CLI
    * `quay_image`: Overrides the image that is being used 
    * `clair_image`: Overrides the image that being used
    * `quay_vpc_cidr`: CIDR of VPC where quay resources like DB, redis will be deployed
    * `builder_ssh_keypair`: SSH Keypair created to access the build VMs (should be created prior to deploy)
    * `builder_access_key`: AWS access key for builder. Used to createEC2 VMs for building
    * `builder_secret_key`: AWS Secret key for builder. Used to createEC2 VMs for building

1. If using an env file like the examples given, set the environment variables in the current shell `source envs/example-primary.env`.
    > **NOTE** The example env file sets the `kube_context` with the command `oc config current-context` so the OCP cluster needs to be logged into first before sourcing the environment file.

1. Initialize Terraform `terraform init`

1. Create the resources `terraform apply`
    > **NOTE** Terraform also generates a statefile `terraform.tfstate`. DO NOT DELETE this file or commit it. This file keeps track of all the resources on AWS associated with your workspace.

1. This command generates all the resources required and outputs `<prefix>_quay_deployment.yaml` file which you can deploy to openshift.

    ```
    oc apply -f <prefix>-quay-deployment.yaml
    ```

    This will generate all the deployments for Quay.


1. Once you get quay running, you can get the quay endpoint by running

    ```
    $ oc project <prefix>-quay
    $ oc get route
    ```
    
## Cleaning up

If using only the primary region the resources can be deleted with.

```
$ terraform destroy
```

If using both the primary and secondary region the secondary region **must** be cleaned up fist.

```
$ terraform workspace select secondary
$ terraform destroy
$ terraform workspace select primary
$ oc login --token="" --server="" # login back in to OCP in primary region
$ source envs/examply-primary.env # Set the correct variables for primary region
$ terraform destroy
```

## Troubleshooting

- Invalid service key in OCP logs in secondary region
    - Check `terraform apply` logs to ensure the `null_resource.update_service_key` script ran correctly
