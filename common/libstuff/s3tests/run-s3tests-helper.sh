#!/bin/bash

usage() {
  cat <<EOF
usage: $0 <ARGUMENTS> [OPTIONS] [TESTS]

ARGUMENTS:
  --host HOST
  --port PORT
  --path PATH   S3-tests Path
  --suite NAME  S3-tests suite

OPTIONS:
  --collect     Collect tests
  --help        This message
EOF

}

host=
port=
s3tests_path=
suite=
collect=0
test=()

while [[ $# -gt 0 ]]; do
  case $1 in
  --host)
    host=$2
    shift 1
    ;;
  --port)
    port=$2
    shift 1
    ;;
  --path)
    s3tests_path=$2
    shift 1
    ;;
  --suite)
    suite=$2
    shift 1
    ;;
  --collect)
    collect=1
    ;;
  --help)
    usage
    exit 0
    ;;
  --*)
    usage
    exit 1
    ;;
  *)
    tests=(${tests[@]} $1)
    ;;
  esac
  shift 1
done

[[ -z "${host}" || -z "${port}" || -z "${s3tests_path}" || -z "${suite}" ]] &&
  echo "missing arguments" && usage && exit 1

if [[ ! -d "${s3tests_path}" ]]; then
  echo "missing s3tests directory"
  exit 1
fi

cd ${s3tests_path}

if [[ ! -d "venv" ]]; then
  python3.8 -m venv venv || exit 1
  source venv/bin/activate
  pip install -r requirements.txt || exit 1
  deactivate
fi

source venv/bin/activate

tconf=$(mktemp)
cat >${tconf} <<EOF
[DEFAULT]
host = ${host}
port = ${port}
is_secure = False
ssl_verify = False

[fixtures]
bucket prefix = s3gwtest-{random}-

[s3 main]
display_name = M. Tester
user_id = testid
email = tester@ceph.com
api_name = default
access_key = test
secret_key = test

[s3 alt]
display_name = john.doe
email = john.doe@example.com
user_id = testid
access_key = test
secret_key = test

[s3 tenant]
display_name = testx
user_id = testid
access_key = test
secret_key = test
email = tenanteduser@example.com

[iam]
email = s3@example.com
user_id = testid
access_key = test
secret_key = test
display_name = youruseridhere
EOF

cleanup() {
  rm ${tconf}
}

trap cleanup EXIT

args=
if [[ $collect -eq 1 ]]; then
  args="${args} --collect-only"
fi

suite_tests=()
if [[ ${#tests} -gt 0 ]]; then
  for t in ${tests[@]}; do
    suite_tests=(${suite_tests[@]} ${suite}:${t})
  done
else
  suite_tests=(${suite})
fi

(S3TEST_CONF=${tconf} venv/bin/nosetests -v -s \
  -a '!fails_on_rgw,!lifecycle_expiration,!fails_strict_rfc2616' \
  ${args} ${suite_tests[@]}) || exit 1
