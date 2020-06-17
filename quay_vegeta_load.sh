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
target_num=100
rate=10
prefix=perftest

# create_user count
create_user() {
  path="/superuser/users/"
  URL=${url}${version}${path}
  echo "+-----------------------+ Generating Users +-----------------------+"
  /usr/bin/jq  --arg token $token -ncM '.=1 | while(. < '${1}'; .+1 ) | {method: "POST", url: "'$URL'", body: {email: ("'${prefix}'_user_" + (.|tostring) +"@test.com"),username: ("'${prefix}'_user_" + (.|tostring))}| @base64, "header":{"Authorization": ["Bearer " + $token], "Content-Type":["application/json"]}}' | ./vegeta attack -lazy -format=json -rate $rate -insecure | ./vegeta report
  echo "+---------------------+ End Generating Users +---------------------+"
}

# update_password count
# default password: password
update_password() {
  path="/superuser/users"
  URL=${url}${version}${path}/${prefix}_user_
  echo "+-----------------------+ Update Passwords +-----------------------+"
  /usr/bin/jq  --arg token $token -ncM '.=1 | while(. < '${1}'; .+1 ) | {method: "PUT", url: ("'${URL}'"+(.|tostring)), body: {password:"'$password'"}| @base64, "header":{"Authorization": ["Bearer " + $token], "Content-Type":["application/json"]}}' | ./vegeta attack -lazy -format=json -rate $rate -insecure | ./vegeta report
  echo "+---------------------+ End Update Passwords +---------------------+"
}

# create_team count
create_team() {
  path=/organization/test/team/${prefix}_team_
  URL=${url}${version}${path}
  echo "+-----------------------+ Generating Teams +-----------------------+"
  /usr/bin/jq  --arg token $token -ncM '.=1 | while(. < '${1}'; .+1 ) | {method: "POST", url: ("'${URL}'"+(.|tostring)), body: {name: ("'${prefix}'_team_" + (.|tostring)),role:member}| @base64, "header":{"Authorization": ["Bearer " + $token], "Content-Type":["application/json"]}}' | ./vegeta attack -lazy -format=json -rate $rate -insecure | ./vegeta report
  echo "+---------------------+ End Generating Teams +---------------------+"
}

# create_repo <repo_name>
create_repo() {
  path="/repository"
  data={\"description\":\"$1\",\"repo_kind\":\"image\",\"namespace\":\"${org}\",\"repository\":\"$1\",\"visibility\":\"public\"}
  curl -H "Content-Type: application/json" -k -X POST -d $data -H "Authorization: Bearer $token" ${url}${version}${path}
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



#create_user 100
#update_password 100
create_team 100

#count=1
#for iter in $(seq 1 $target_num); do
#    if [[ $count -lt $concurrent_users ]]; then
#        gen_account $iter perf-test &
#        ((count=count+1))
#    else
#        sleep 60
#        count=1
#    fi
#done
