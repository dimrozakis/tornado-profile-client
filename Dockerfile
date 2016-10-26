FROM alpine

RUN apk add --update python py-pip && \
    rm -rf /var/cache/apk/*

ADD requirements.txt /opt/tornado-profile-client/

RUN pip install --no-cache-dir \
        -r /opt/tornado-profile-client/requirements.txt && \
    find / -name '*.pyc' -delete

ADD . /opt/tornado-profile-client/

RUN pip install --no-cache-dir /opt/tornado-profile-client/ && \
    find / -name '*.pyc' -delete

CMD ["/usr/local/bin/tornado-profile-client"]
