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
rate=50
prefix=joetaleric-test
uuid=$(uuidgen)
elastic=search-cloud-perf-lqrf3jjtaqo7727m7ynd2xyt4y.us-west-2.es.amazonaws.com
es_port=80
snafu="python3.6 /root/snafu/run_snafu.py"
db=mysql57
quay_version=3

# Elasticsearch params
export es=$elastic
export es_port=$es_port
export es_index=ripsaw-vegeta
export clustername=quay${quay_version}_${db}

# create_user count
create_user() {
  path="/superuser/users/"
  URL=${url}${version}${path}
  echo "+-----------------------+ Generating Users +-----------------------+"
  /usr/bin/jq  --arg token $token -ncM '.=1 | while(. < '${1}'; .+1 ) | {method: "POST", url: "'$URL'", body: {email: ("'${prefix}'_user_" + (.|tostring) +"@test.com"),username: ("'${prefix}'_user_" + (.|tostring))}| @base64, "header":{"Authorization": ["Bearer " + $token], "Content-Type":["application/json"]}}' | ./vegeta attack -lazy -format=json -rate $rate -insecure > create_user-performance-${uuid}-result.log
  cat create_user-performance-${uuid}-result.log | ./vegeta report
  cat create_user-performance-${uuid}-result.log | ./vegeta report --every=1s --type=json --output=vegeta-create_user-performance-${uuid}-result.json
  $snafu -t vegeta -r vegeta-create_user-performance-${uuid}-result.json -u ${uuid} --target_name ${path} -w ${rate}
  echo "+---------------------+ End Generating Users +---------------------+"
}

# update_password count
# default password: password
update_password() {
  path="/superuser/users"
  URL=${url}${version}${path}/${prefix}_user_
  echo "+-----------------------+ Update Passwords +-----------------------+"
  /usr/bin/jq  --arg token $token -ncM '.=1 | while(. < '${1}'; .+1 ) | {method: "PUT", url: ("'${URL}'"+(.|tostring)), body: {password:"'$password'"}| @base64, "header":{"Authorization": ["Bearer " + $token], "Content-Type":["application/json"]}}' | ./vegeta attack -lazy -format=json -rate $rate -insecure > update_password-performance-${uuid}-result.log
  cat update_password-performance-${uuid}-result.log | ./vegeta report
  cat update_password-performance-${uuid}-result.log | ./vegeta report --every=1s --type=json --output=vegeta-update_password-performance-${uuid}-result.json
  $snafu -t vegeta -r vegeta-update_password-performance-${uuid}-result.json -u ${uuid} --target_name ${path} -w ${rate}
  echo "+---------------------+ End Update Passwords +---------------------+"
}

# create_team count
create_team() {
  path=/organization/${org}/team/${prefix}_team_
  URL=${url}${version}${path}
  echo "+-----------------------+ Generating Teams +-----------------------+"
  /usr/bin/jq  --arg token $token -ncM '.=1 | while(. < '${1}'; .+1 ) | {method: "PUT", url: ("'${URL}'"+(.|tostring)), body: {name: ("'${prefix}'_team_" + (.|tostring)),role:"member"}| @base64, "header":{"Authorization": ["Bearer " + $token], "Content-Type":["application/json"]}}' | ./vegeta attack -lazy -format=json -rate $rate -insecure > create_team-performance-${uuid}-result.log
  cat create_team-performance-${uuid}-result.log | ./vegeta report
  cat create_team-performance-${uuid}-result.log | ./vegeta report --every=1s --type=json --output=vegeta-create_team-performance-${uuid}-result.json
  $snafu -t vegeta -r vegeta-create_team-performance-${uuid}-result.json -u ${uuid} --target_name ${path} -w ${rate}
  echo "+---------------------+ End Generating Teams +---------------------+"
}

# create_repo count
create_repo() {
  path="/repository"
  URL=${url}${version}${path}
  echo "+-----------------------+ Generating Repos +-----------------------+"
  /usr/bin/jq  --arg token $token -ncM '.=1 | while(. < '${1}'; .+1 ) | {method: "POST", url: "'${URL}'", body: {description:"test",repo_kind:"image",namespace:"'$org'",repository: ("'${prefix}'_repo_" + (.|tostring)),visibility:"public"}| @base64, "header":{"Authorization": ["Bearer " + $token], "Content-Type":["application/json"]}}' | ./vegeta attack -lazy -format=json -rate $rate -insecure > create_repo-performance-${uuid}-result.log
  cat create_repo-performance-${uuid}-result.log | ./vegeta report
  cat create_repo-performance-${uuid}-result.log | ./vegeta report --every=1s --type=json --output=vegeta-create_repo-performance-${uuid}-result.json
  $snafu -t vegeta -r vegeta-create_repo-performance-${uuid}-result.json -u ${uuid} --target_name ${path} -w ${rate}
  echo "+---------------------+ End Generating Repos +---------------------+"
}

# add_user_to_team count
add_user_to_team() {
  path=/organization/$org/team/
  URL=${url}${version}${path}
  echo "+-----------------------+ Linking User to Team +-----------------------+"
  /usr/bin/jq  --arg token $token -ncM '.=1 | while(. < '${1}'; .+1 ) | {method: "PUT", url: ("'${URL}''${prefix}'_team_"+(.|tostring)+"/members/'${prefix}'_user_"+(.|tostring)), body: {}| @base64, "header":{"Authorization": ["Bearer " + $token], "Content-Type":["application/json"]}}' | ./vegeta attack -lazy -format=json -rate $rate -insecure > add_user_to_repo-performance-${uuid}-result.log
  cat add_user_to_repo-performance-${uuid}-result.log | ./vegeta report
  cat add_user_to_repo-performance-${uuid}-result.log | ./vegeta report --every=1s --type=json --output=vegeta-add_user_to_repo-performance-${uuid}-result.json
  $snafu -t vegeta -r vegeta-add_user_to_repo-performance-${uuid}-result.json -u ${uuid} --target_name ${path} -w ${rate}
  echo "+---------------------+ End Linking User to Team +---------------------+"
}

# add_team_to_repo count
add_team_to_repo() {
  path=/repository/$org/
  URL=${url}${version}${path}
  echo "+-----------------------+ Linking Repo to Team +-----------------------+"
  /usr/bin/jq  --arg token $token -ncM '.=1 | while(. < '${1}'; .+1 ) | {method: "PUT", url: ("'${URL}''${prefix}'_repo_"+(.|tostring)+"/permissions/team/'${prefix}'_team_"+(.|tostring)), body: {role:"admin"}| @base64, "header":{"Authorization": ["Bearer " + $token], "Content-Type":["application/json"]}}' | ./vegeta attack -lazy -format=json -rate $rate -insecure > add_team_to_repo-performance-${uuid}-result.log
  cat add_team_to_repo-performance-${uuid}-result.log | ./vegeta report
  cat add_team_to_repo-performance-${uuid}-result.log | ./vegeta report --every=1s --type=json --output=vegeta-add_user_to_repo-performance-${uuid}-result.json
  $snafu -t vegeta -r vegeta-add_user_to_repo-performance-${uuid}-result.json -u ${uuid} --target_name ${path} -w ${rate}
  echo "+---------------------+ End Linking Repo to Team +---------------------+"
}

create_user $target_num
update_password $target_num
create_team $target_num
create_repo $target_num
add_user_to_team $target_num
add_team_to_repo $target_num

