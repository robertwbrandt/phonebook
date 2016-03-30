#!/bin/bash
pushd /opt/opw/password
java -classpath ./lib/ExpirationNotification.jar:./lib/mail.jar:./lib/jsse.jar:./lib/activation.jar identity.ExpirationNotification
popd

