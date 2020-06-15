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

# create_user <user>
create_user() {
  path="/superuser/users/"
  data={\"email\":\"$1@test.com\",\"username\":\"$1\"}
  curl -H "Content-Type: application/json" -k -X POST -d $data -H "Authorization: Bearer $token" ${url}${version}${path}
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

create_team test_team6
create_user test_user6
create_repo test_repo6
add_user_to_team test_team6 test_user6
add_team_to_repo test_repo6 test_team6
