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

## Creating the primary instance (single deployment)

1. Ensure the AWS CLI is installed and configured. Run `aws configure` to setup installation. An access and secret key will be required. [Documentation for configuring AWS cli.](https://docs.aws.amazon.com/cli/latest/reference/configure/)

1. Log into the OCP cluster with `oc login`. Credentials can be retrieved via Openshift console.

1. Create a new terraform workspace. This is not required if deploying a single instance.

    ```
    $ terraform workspace new primary
    $ terraform workspace select primary
    ```

1. You need to set the following variables (as environment variables prefixed with `TF_VAR_` or variables in `terraform.tfvars`). Reference the example in `./envs/example-primary.env` and modify as needed.
    * `region` : AWS region to use for deployment (default `us-east-1`)
    * `deploy_type`: Should be set to `primary`
    * `quay_vpc_cidr`: Pick an unused private range CIDR of `172.16../16 - 172.29../16`. VPC where quay resources like DB, redis will be deployed. Will fail if a VPC already exists with this range.
    * `prefix` : Make sure it's unique or it will clash with other envs
    * `db_password` : The password that will be set on the quay and clair RDS DBs
    * `openshift_vpc_id` : VPC ID where openshift is deployed (used for creating peering)
    * `kube_context`: Local kuberenetes context containing authentication to the target cluster

   
   You could optionally set the following variables if required
    * `aws_profile`: Set this if you are not using the default account set with AWS CLI
    * `quay_image`: Overrides the image that is being used 
    * `dns_domain`: Alternative domain name to be created along with the default (default is `<prefix>.quaydev.org`)
    * `clair_image`: Overrides the image that being used
    * `builder_ssh_keypair`: SSH Keypair created to access the build VMs (should be created prior to deploy)
    * `builder_access_key`: AWS access key for builder. Used to createEC2 VMs for building
    * `builder_secret_key`: AWS Secret key for builder. Used to createEC2 VMs for building
    * `redis_azs`: List of Redis availability zones

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

## Creating the secondary instance

**NOTE** Creating the secondary instance requires completing the setup of the primary instance from the previous section first.

1. The secondary instance is readonly and requires service keys to be configured through the primary instance. The service keys are used for functions related to signing and token generation. Run the following script to generate the service key and update in the primary database:

  ```
  ./setup_service_keys.sh <primary_quay_db_password> <primary_quay_db_host>
  ```

1. The script will output the commands for setting the `service_key_kid_path` and `service_key_pem_path` Terraform variables similar to below. Run those commands to set both of the variables.

```
export TF_VAR_service_key_kid_path='./service-key-generator/quay-readonly.kid'"
export TF_VAR_service_key_jwt_path='./service-key-generator/quay-readonly.jwk'"
```

1. Ensure the AWS CLI is installed and configured with the access and secret keys. Update the region to `us-east-2` by modifying the `~/.aws/config` file.

1. Log into the OCP cluster in the secondary region via `oc login`. Credentials can be retrieved via Openshift console.

1. Create a new terraform workspace.

    ```
    $ terraform workspace new secondary
    $ terraform workspace select secondary
    ```

1. You need to set the following variables (as environment variables prefixed with `TF_VAR_` or variables in `terraform.tfvars`). Reference the example in `./envs/example-secondary.env` and modify as needed. Note additional parameters specific to the secondary environment are required.
    * `region` : Should be set to `us-east-2` (default `us-east-1`)
    * `deploy_type`: Should be set to `secondary`
    * `quay_vpc_cidr`: Pick an unused private range CIDR of `172.16../16 - 172.29../16`. VPC where quay resources like DB, redis will be deployed. Will fail if a VPC already exists with this range.
    * `prefix` : Make sure it's unique else, it will clash with other envs including the primary deployment
    * `db_password` : The password that will be set on the quay and clair RDS DBs
    * `openshift_vpc_id` : VPC ID where the openshift in the secondary region is deployed (used for creating peering)
    * `kube_context`: Local kuberenetes context containing authentication to the target cluster
    * `primary_s3_bucket_arn`: The Amazon resource name of the primary S3 bucket, used for replication
    * `primary_db_arn`: The Amazon resource name of the primary database, used for replication
    * `service_key_kid_path`: Path to the file containing the file containing the service key kid (Run `setup_service_keys.sh` script to generate keys, details in step 1)
    * `service_key_pem_path`: Path to the file containing the service key pem (Run `setup_service_keys.sh` script to generate keys, details in step 1)

   
   You could optionally set the following variables if required
    * `aws_profile`: Set this if you are not using the default account set with AWS CLI
    * `quay_image`: Overrides the image that is being used 
    * `dns_domain`: Alternative domain name to be created along with the default (default is `<prefix>.quaydev.org`)
    * `clair_image`: Overrides the image that being used
    * `builder_ssh_keypair`: SSH Keypair created to access the build VMs (should be created prior to deploy)
    * `builder_access_key`: AWS access key for builder. Used to createEC2 VMs for building
    * `builder_secret_key`: AWS Secret key for builder. Used to createEC2 VMs for building
    * `redis_azs`: List of Redis availability zones

1. Initialize Terraform `terraform init`

1. Create the resources `terraform apply`
    > **NOTE** Terraform also generates a statefile `terraform.tfstate`. DO NOT DELETE this file or commit it. This file keeps track of all the resources on AWS associated with your workspace.

1. Create the deployment with `oc apply -f <prefix>-quay-deployment.yaml`

1. Once you get quay running, you can access the secondary instance directly with.

    ```
    $ oc project <prefix>-quay
    $ oc get route
    ```

1. Now any content created or pushed to the primary instance will be replicated to the secondary instance in readonly mode.
    
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
$ vim ~/.aws/config # reset back to us-east-1
$ oc login --token="" --server="" # login back in to OCP in primary region
$ source envs/examply-primary.env # Set the correct variables for primary region
$ terraform destroy
```

