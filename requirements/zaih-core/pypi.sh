#! /usr/bin/env bash
set -e

if [ -z "$VIRTUAL_ENV" ]; then
    echo 'Please wrap this test in a virtualenv.' >&2
    exit 2
fi

export PIP_INDEX_URL="http://pypi.iguokr.com/guokr/dev/+simple"

echo -e "[easy_install]\nindex_url = $PIP_INDEX_URL" > $VIRTUAL_ENV/.pydistutils.cfg


sh ./test.sh

pip install -r requirements.txt -i http://pypi.douban.com/simple
pip install devpi-client
devpi use http://pypi.iguokr.com/guokr/dev/+simple
devpi login guokr --password guokr
devpi upload

exit $?
