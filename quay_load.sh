#!/bin/bash
set -x
if [ "$#" -ne 2 ]; then
  echo "Usage: "
  echo "        ./script <URL> <TOKEN>"
  exit 1
fi

token=$2
url=$1
version="/api/v1"
org=test
password=password
target_num=1000
concurrent_users=100

# create_user <user>
create_user() {
  path="/superuser/users/"
  data={\"email\":\"$1@test.com\",\"username\":\"$1\",\"password\":\"password\"}
  curl -H "Content-Type: application/json" -k -X POST -d $data -H "Authorization: Bearer $token" ${url}${version}${path}
  update_password $1
}

# update_password <user>
# default password: password
update_password() {
  path="/superuser/users/$1"
  data={\"password\":\"$password\"}
  curl -H "Content-Type: application/json" -k -X PUT -d $data -H "Authorization: Bearer $token" ${url}${version}${path}
}

# create_team <team>
create_team() {
  path="/organization/test/team/$1"
  data={\"name\":\"$1\",\"role\":\"member\"}
  curl -H "Content-Type: application/json" -k -X PUT -d $data -H "Authorization: Bearer $token" ${url}${version}${path}
}

# add_user_to_team <team> <user>
add_user_to_team() {
  path="/organization/$org/team/$1/members/$2"
  data={}
  curl -H "Content-Type: application/json" -k -X PUT -d $data -H "Authorization: Bearer $token" ${url}${version}${path}
}

# add_team_to_repo <team> <repo>
add_team_to_repo() {
  path="/repository/$org/$1/permissions/team/$2"
  data={\"role\":\"admin\"}
  curl -H "Content-Type: application/json" -k -X PUT -d $data -H "Authorization: Bearer $token" ${url}${version}${path}
}

# create_repo <repo_name>
create_repo() {
  path="/repository"
  data={\"description\":\"$1\",\"repo_kind\":\"image\",\"namespace\":\"${org}\",\"repository\":\"$1\",\"visibility\":\"public\"}
  curl -H "Content-Type: application/json" -k -X POST -d $data -H "Authorization: Bearer $token" ${url}${version}${path}
}

# gen_account <num> <prefix_for_assets>
# Builds the accounts and creates associations.
gen_account(){
    prefix=$2
    create_team ${prefix}_team_$1
    create_user ${prefix}_user_$1
    create_repo ${prefix}_repo_$1
    add_user_to_team ${prefix}_team_$1 ${prefix}_user_$1
    add_team_to_repo ${prefix}_repo_$1 ${prefix}_team_$1
}

count=1
for iter in $(seq 1 $target_num); do
    if [[ $count -lt $concurrent_users ]]; then
        gen_account $iter perf-test &
        ((count=count+1))
    else
        sleep 60
        count=1
    fi
done
