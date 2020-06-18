#!/bin/bash
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
rate=10
prefix=perf-test

# create_user count
create_user() {
  path="/superuser/users/"
  URL=${url}${version}${path}
  echo "+-----------------------+ Generating Users +-----------------------+"
  /usr/bin/jq  --arg token $token -ncM '.=1 | while(. < '${1}'; .+1 ) | {method: "POST", url: "'$URL'", body: {email: ("'${prefix}'_user_" + (.|tostring) +"@test.com"),username: ("'${prefix}'_user_" + (.|tostring))}| @base64, "header":{"Authorization": ["Bearer " + $token], "Content-Type":["application/json"]}}' | ./vegeta attack -lazy -format=json -rate $rate -insecure | ./vegeta report | tee create_user-performance.log
  echo "+---------------------+ End Generating Users +---------------------+"
}

# update_password count
# default password: password
update_password() {
  path="/superuser/users"
  URL=${url}${version}${path}/${prefix}_user_
  echo "+-----------------------+ Update Passwords +-----------------------+"
  /usr/bin/jq  --arg token $token -ncM '.=1 | while(. < '${1}'; .+1 ) | {method: "PUT", url: ("'${URL}'"+(.|tostring)), body: {password:"'$password'"}| @base64, "header":{"Authorization": ["Bearer " + $token], "Content-Type":["application/json"]}}' | ./vegeta attack -lazy -format=json -rate $rate -insecure | ./vegeta report | tee update_password-performance.log
  echo "+---------------------+ End Update Passwords +---------------------+"
}

# create_team count
create_team() {
  path=/organization/test/team/${prefix}_team_
  URL=${url}${version}${path}
  echo "+-----------------------+ Generating Teams +-----------------------+"
  /usr/bin/jq  --arg token $token -ncM '.=1 | while(. < '${1}'; .+1 ) | {method: "PUT", url: ("'${URL}'"+(.|tostring)), body: {name: ("'${prefix}'_team_" + (.|tostring)),role:"member"}| @base64, "header":{"Authorization": ["Bearer " + $token], "Content-Type":["application/json"]}}' | ./vegeta attack -lazy -format=json -rate $rate -insecure | ./vegeta report | tee create_team-performance.log

  echo "+---------------------+ End Generating Teams +---------------------+"
}

# create_repo count
create_repo() {
  path="/repository"
  URL=${url}${version}${path}
  echo "+-----------------------+ Generating Repos +-----------------------+"
  /usr/bin/jq  --arg token $token -ncM '.=1 | while(. < '${1}'; .+1 ) | {method: "POST", url: "'${URL}'", body: {description:"test",repo_kind:"image",namespace:"'$org'",repository: ("'${prefix}'_repo_" + (.|tostring)),visibility:"public"}| @base64, "header":{"Authorization": ["Bearer " + $token], "Content-Type":["application/json"]}}' | ./vegeta attack -lazy -format=json -rate $rate -insecure | ./vegeta report | tee create_repo-performance.log
  echo "+---------------------+ End Generating Repos +---------------------+"
}

# add_user_to_team count
add_user_to_team() {
  path=/organization/$org/team/
  URL=${url}${version}${path}
  echo "+-----------------------+ Linking User to Team +-----------------------+"
  /usr/bin/jq  --arg token $token -ncM '.=1 | while(. < '${1}'; .+1 ) | {method: "PUT", url: ("'${URL}''${prefix}'_team_"+(.|tostring)+"/members/'${prefix}'_user_"+(.|tostring)), body: {}| @base64, "header":{"Authorization": ["Bearer " + $token], "Content-Type":["application/json"]}}' | ./vegeta attack -lazy -format=json -rate $rate -insecure | ./vegeta report | tee add_user_to_repo-performance.log
  echo "+---------------------+ End Linking User to Team +---------------------+"
}

# add_team_to_repo count
add_team_to_repo() {
  path=/repository/$org/
  URL=${url}${version}${path}
  echo "+-----------------------+ Linking Repo to Team +-----------------------+"
  /usr/bin/jq  --arg token $token -ncM '.=1 | while(. < '${1}'; .+1 ) | {method: "PUT", url: ("'${URL}''${prefix}'_repo_"+(.|tostring)+"/permissions/team/'${prefix}'_team_"+(.|tostring)), body: {role:"admin"}| @base64, "header":{"Authorization": ["Bearer " + $token], "Content-Type":["application/json"]}}' | ./vegeta attack -lazy -format=json -rate $rate -insecure | ./vegeta report | tee add_team_to_repo-performance.log
  echo "+---------------------+ End Linking Repo to Team +---------------------+"

}

create_user $target_num
update_password $target_num
create_team $target_num
create_repo $target_num
add_user_to_team $target_num
add_team_to_repo $target_num
