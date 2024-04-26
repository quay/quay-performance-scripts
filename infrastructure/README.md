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

1. The secondary instance is readonly and requires service keys to be configured through the primary instance. The service keys are used for functions related to signing and token generation. First we need to generate those keys via a script in the Quay repository.

```
$ git clone https://github.com/quay/quay  # clone the Quay repository
$ python -m venv venv # Create a python virtual environment
$ source venv/bin/activate # Activate the python virtual environment
$ pip install -r requirements-generatekeys.txt # Install the dependencies required for key generation
$ cd tools # Change to the tools directory
$ python generatekeypair.py quay-readonly # Run the script to generate the keys
$ ls | grep 'quay-readonly' # The following files should be generated
quay-readonly.jwk
quay-readonly.kid
quay-readonly.pem
```

1. Install the key's to the primary instance. Replace the values of `$QUAY_READONLY_KID` and `$QUAY_READONLY_JWT` with the contents of `quay-readonly.kid` and `quay-readonly.jwk`respectively in the `update_service_keys.sql` script.

1. Execute the script against the primary database created in the previous section. The database host can be found in the terraform output when creating the primary instance or through the AWS console. 
```
PGPASSWORD=$TF_VAR_db_password psql -U quay -h $QUAY_PRIMARY_DB_HOST < update_service_keys.sql
```

1. We can now create the secondary instances through Terraform. Ensure the AWS CLI is installed and configured with the access and secret keys. Update the region to `us-east-2` by modifying the `~/.aws/config` file.

1. Log into the OCP cluster in the secondary region via `oc login`. Credentials can be retrieved via Openshift console.

1. Create a new terraform workspace.

    ```
    $ terraform workspace new secondary
    $ terraform workspace select secondary
    ```

1. You need to set the following variables (as environment variables prefixed with `TF_VAR_` or variables in `terraform.tfvars`). Reference the example in `./envs/example-secondary.env` and modify as needed. Note `primary_s3_bucket_arn` and `primary_db_arn` are now required.
    * `region` : Should be set to `us-east-2` (default `us-east-1`)
    * `deploy_type`: Should be set to `secondary`
    * `quay_vpc_cidr`: Pick an unused private range CIDR of `172.16../16 - 172.29../16`. VPC where quay resources like DB, redis will be deployed. Will fail if a VPC already exists with this range.
    * `prefix` : Make sure it's unique else, it will clash with other envs including the primary deployment
    * `db_password` : The password that will be set on the quay and clair RDS DBs
    * `openshift_vpc_id` : VPC ID where the openshift in the secondary region is deployed (used for creating peering)
    * `kube_context`: Local kuberenetes context containing authentication to the target cluster
    * `primary_s3_bucket_arn`: The Amazon resource name of the primary S3 bucket, used for replication
    * `primary_db_arn`: The Amazon resource name of the primary database, used for replication

   
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

1. This command generates all the resources required and outputs `<prefix>_quay_deployment.yaml` file. Before applying this file we first need to add the service keys to Quay config secret. Modify the `quay-config-secret` in the `<prefix>_quay_deployment.yaml` file with the following:
```
apiVersion: v1
kind: Secret
metadata:
  name: quay-config-secret
  namespace: secondary-quay
stringData:
  default-cloudfront-signing-key.pem: |
    ...
    
  ssl.cert: |
    ...
    
  ssl.key: |
    ...

  quay-readonly.kid: |                       # Add this
    <contents of quay-readonly.kid>

  quay-readonly.jwt: |                       # Add this
    <contents of quay-readonly.jwt>
  
  config.yaml: |
    INSTANCE_SERVICE_KEY_KID_LOCATION: 'conf/stack/quay-readonly.kid' # Add this
    INSTANCE_SERVICE_KEY_LOCATION: 'conf/stack/quay-readonly.pem' # Add this
    ...rest of config
```

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

