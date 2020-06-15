#!/bin/bash
if [ "$#" -ne 2 ]; then
  echo "Usage: "
  echo "	./script <URL> <TOKEN>"
  exit 1
fi

token=$2
url=$1
version="/api/v1"

create_user() {
  path="/organization/test/team/$1"
  data='{"name":"$1","role":"member"}'
  curl -H "Content-Type: application/json" -k -X PUT -d $data -H "Authorization: Bearer $2" ${3}${4}${path}
}

create_user test1 $token $url $version
